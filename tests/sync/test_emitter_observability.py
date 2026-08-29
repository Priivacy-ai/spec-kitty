"""Observable emitter capture failure + resolve-before-UoW cutover seam (WP05).

IC-05 (plan.md:179-185) / FR-001 + FR-010, folding #3391. Two orthogonal
guarantees the emitter must uphold at once when a capture cannot land:

* **Non-fatal** — no exception escapes any public ``emit_*`` call (or the two
  helper capture sites) when the inner write raises. ``_emit`` is contractually
  "never raises" (``emitter.py`` docstring) and is the sole body behind ~30
  ``emit_*`` methods; raising would crash the whole status/build/mission surface.
* **Observable** — a *process-level* captured-failure surface (``captured_failures``
  / ``reset_captured_failures``) is incremented, readable without a filesystem
  rescan (mirrors ``AgentProfileRepository.skipped_profiles``). This is the
  machine-observable half; the human warning is the complementary, throttled half.

Both swallow sites are covered: ``_capture_to_journal`` (site 1) and
``_emit_for_project_context`` (site 2, the live-reproduced site — ``mission
create`` printed it five times authoring this mission). The loud warning is
rate-limited so a residual systemic fault is loud-once-and-counted-fully, never a
per-event storm.

**Part B (resolve-before-UoW).** WP03 proved the layout lock is not re-entrant:
``resolve_layout_for_write`` invoked *inside* an open write unit-of-work cannot
complete the cutover copy (the store lock is held), so a legacy-with-data root
surfaced ``LayoutCutoverIncompleteError`` on the live emit path. ``_queue_event_locally``
now resolves/drives the layout *before* opening its own UoW, so the common
legacy-with-data case COMPLETES and the event lands in the project store.

**Isolation is safety-critical (plan Risk MINOR-8).** This dev box is itself a
live legacy root; every store/emit test pins BOTH ``SPEC_KITTY_HOME`` and
``HOME`` to ``tmp_path`` so a stray cutover can never touch the real
machine-global ``~/.spec-kitty``.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace

import pytest

from specify_cli.event_journal.journal import EventJournal
from specify_cli.sync import emitter as emitter_mod
from specify_cli.sync.emitter import EventEmitter
from specify_cli.sync.layout_generation import LayoutMode
from specify_cli.sync.project_store import ProjectSyncStore

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

OWNER = "eeeeeeee-0000-0000-0000-000000000005"


class _RecordingConsole:
    """A stand-in for the module stderr console that counts warnings."""

    def __init__(self) -> None:
        self.messages: list[str] = []

    def print(self, message: str = "", *args: object, **kwargs: object) -> None:
        self.messages.append(str(message))


@pytest.fixture(autouse=True)
def _clean_surface() -> Iterator[None]:
    """Guarantee a clean process-level surface around every test (reset pin)."""
    emitter_mod.reset_captured_failures()
    yield
    emitter_mod.reset_captured_failures()


def _isolate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Pin the runtime + home to temp; return the runtime root (== spec_kitty_dir)."""
    runtime = tmp_path / "runtime"
    monkeypatch.setenv("SPEC_KITTY_HOME", str(runtime))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("SPEC_KITTY_SYNC_DISABLE", "1")
    monkeypatch.delenv("SPEC_KITTY_NO_AUTO_CUTOVER", raising=False)
    return runtime


def _seed_queue(path: Path, rows: tuple[tuple[str, dict[str, object]], ...]) -> None:
    """Seed a legacy queue DB with ``(event_id, data_dict)`` rows."""
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute(
        "CREATE TABLE queue (id INTEGER PRIMARY KEY, event_id TEXT UNIQUE, "
        "event_type TEXT, data TEXT, timestamp INTEGER, retry_count INTEGER)"
    )
    for index, (event_id, data) in enumerate(rows, start=1):
        connection.execute(
            "INSERT INTO queue VALUES (?, ?, 'MissionCreated', ?, ?, 0)",
            (index, event_id, json.dumps(data, sort_keys=True), index),
        )
    connection.commit()
    connection.close()


def _journal_ids(store: ProjectSyncStore) -> set[str]:
    with store.unit_of_work() as unit:
        journal = EventJournal(unit, store.layout_generation())
        return {event.event_id for event in journal.read_all()}


def _live_event(event_id: str) -> dict[str, object]:
    return {
        "event_id": event_id,
        "event_type": "MissionCreated",
        "aggregate_id": "M-1",
        "aggregate_type": "Mission",
        "project_uuid": OWNER,
        "payload": {"n": 1},
        "created_at": "2026-08-15T00:00:00+00:00",
        "occurred_at": "2026-08-15T00:00:00+00:00",
    }


# --- T022 / T025: non-fatal + observable, both sites --------------------------


def test_public_emit_never_raises_when_capture_fails_and_is_observed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-fatal + observable pin driven through a public ``emit_*`` method."""
    _isolate(tmp_path, monkeypatch)
    # Drive the PUBLIC emit path, which since #3799 short-circuits before capture
    # unless sync is armed. Arm it (``_isolate`` sets SYNC_DISABLE=1) so ``_emit``
    # actually reaches the ``_queue_event_locally`` seam this test forces to fail.
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    monkeypatch.delenv("SPEC_KITTY_SYNC_DISABLE", raising=False)
    monkeypatch.setattr(emitter_mod, "_console", _RecordingConsole())

    emitter = EventEmitter()

    def _boom(_event: dict[str, object]) -> bool:
        raise RuntimeError("forced queue append failure")

    monkeypatch.setattr(emitter, "_queue_event_locally", _boom)

    # Non-fatal: the public call returns normally, no exception escapes.
    result = emitter.emit_history_added("WP01", "note", "hello")
    assert result is None or isinstance(result, dict)

    # Observable: the process-level surface saw the capture failure, no rescan.
    failures = emitter_mod.captured_failures()
    assert failures, "unrecoverable capture failure must be boundary-observable"
    assert any("journal" in f.site.lower() for f in failures)


def test_capture_to_journal_site_records_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Site 1 (``_capture_to_journal``) records into the surface and stays non-fatal."""
    monkeypatch.setattr(emitter_mod, "_console", _RecordingConsole())
    emitter = EventEmitter()

    def _boom(_event: dict[str, object]) -> bool:
        raise RuntimeError("forced journal append failure")

    monkeypatch.setattr(emitter, "_queue_event_locally", _boom)

    # No exception escapes the helper (its ``-> None`` non-raising contract).
    emitter._capture_to_journal(
        event_id="E1",
        event_type="MissionCreated",
        event={"event_id": "E1"},
        occurred_at="2026-08-15T00:00:00+00:00",
        team_slug=None,
    )

    failures = emitter_mod.captured_failures()
    assert len(failures) == 1
    assert "journal" in failures[0].site.lower()
    # The record carries a site label + exception summary, never the envelope.
    assert "forced journal append failure" in failures[0].summary


def test_explicit_context_site_records_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Site 2 (``_emit_for_project_context``) records and still returns ``None``."""
    monkeypatch.setattr(emitter_mod, "_console", _RecordingConsole())
    # Bypass the authority validation so the mismatched-identity guard raises
    # inside the try body, exercising the live-reproduced except handler.
    monkeypatch.setattr(
        "specify_cli.sync.project_context.validate_project_sync_context_authority",
        lambda _ctx: None,
    )
    emitter = EventEmitter()

    context = SimpleNamespace(
        store_identity=object(),
        project_uuid=SimpleNamespace(storage_token=OWNER),
    )
    unit = SimpleNamespace(store_identity=object())  # deliberately different identity

    result = emitter._emit_for_project_context(
        event_type="MissionCreated",
        aggregate_id="M-1",
        aggregate_type="Mission",
        payload={"n": 1},
        causation_id=None,
        envelope_fields=None,
        occurred_at=None,
        project_context=context,
        project_unit=unit,
        project_layout=object(),
    )

    # Explicit-context contract: a refused capture yields ``None`` (non-fatal).
    assert result is None
    failures = emitter_mod.captured_failures()
    assert len(failures) == 1
    assert "explicit" in failures[0].site.lower()


def test_reset_clears_surface_between_cases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``reset_captured_failures`` leaves a clean slate (per-invocation isolation)."""
    monkeypatch.setattr(emitter_mod, "_console", _RecordingConsole())
    emitter = EventEmitter()

    def _boom(_event: dict[str, object]) -> bool:
        raise RuntimeError("boom")

    monkeypatch.setattr(emitter, "_queue_event_locally", _boom)
    emitter._capture_to_journal(
        event_id="E1",
        event_type="MissionCreated",
        event={"event_id": "E1"},
        occurred_at="2026-08-15T00:00:00+00:00",
        team_slug=None,
    )
    assert emitter_mod.captured_failures()

    emitter_mod.reset_captured_failures()
    assert emitter_mod.captured_failures() == ()


# --- T026: rate-limit the loud path, exact count ------------------------------


def test_warning_is_rate_limited_but_count_is_exact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A burst of identical failures warns at most once but counts every one."""
    console = _RecordingConsole()
    monkeypatch.setattr(emitter_mod, "_console", console)
    emitter = EventEmitter()

    def _boom(_event: dict[str, object]) -> bool:
        raise RuntimeError("systemic capture fault")

    monkeypatch.setattr(emitter, "_queue_event_locally", _boom)

    for _ in range(50):
        emitter._capture_to_journal(
            event_id="E",
            event_type="MissionCreated",
            event={"event_id": "E"},
            occurred_at="2026-08-15T00:00:00+00:00",
            team_slug=None,
        )

    # Counter is exact (INV-1 sees the true count) ...
    assert len(emitter_mod.captured_failures()) == 50
    # ... but the human warning fired at most once for this distinct failure.
    assert len(console.messages) == 1


def test_mixed_burst_across_sites_is_bounded_not_doubled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A mixed burst across both sites is bounded (one warning per site), not per-event."""
    console = _RecordingConsole()
    monkeypatch.setattr(emitter_mod, "_console", console)
    monkeypatch.setattr(
        "specify_cli.sync.project_context.validate_project_sync_context_authority",
        lambda _ctx: None,
    )
    emitter = EventEmitter()

    def _boom(_event: dict[str, object]) -> bool:
        raise RuntimeError("systemic capture fault")

    monkeypatch.setattr(emitter, "_queue_event_locally", _boom)

    context = SimpleNamespace(
        store_identity=object(),
        project_uuid=SimpleNamespace(storage_token=OWNER),
    )
    unit = SimpleNamespace(store_identity=object())

    for _ in range(50):
        emitter._capture_to_journal(
            event_id="E",
            event_type="MissionCreated",
            event={"event_id": "E"},
            occurred_at="2026-08-15T00:00:00+00:00",
            team_slug=None,
        )
        emitter._emit_for_project_context(
            event_type="MissionCreated",
            aggregate_id="M-1",
            aggregate_type="Mission",
            payload={"n": 1},
            causation_id=None,
            envelope_fields=None,
            occurred_at=None,
            project_context=context,
            project_unit=unit,
            project_layout=object(),
        )

    # Every failure counted (100), warnings bounded to one-per-distinct-site (2).
    assert len(emitter_mod.captured_failures()) == 100
    assert len(console.messages) == 2


# --- Part B: resolve-before-UoW completes a legacy-with-data cutover ----------


def test_emit_completes_legacy_with_data_cutover_on_live_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A live emit on a legacy-with-data root COMPLETES the cutover and lands.

    RED before the resolve-before-UoW seam: ``queue_event`` drives
    ``resolve_layout_for_write`` inside its own open unit-of-work, the cutover
    copy contends on the held store lock and cannot complete, and the write
    surfaces ``LayoutCutoverIncompleteError``. GREEN after: the emitter resolves
    the layout before opening the UoW, so the cutover completes where the lock is
    free and the event lands in the project store, legacy events conserved.
    """
    spec_dir = _isolate(tmp_path, monkeypatch)
    _seed_queue(
        spec_dir / "queue.db",
        (("evt-legacy-a", {"payload": {"n": 1}}), ("evt-legacy-b", {"payload": {"n": 2}})),
    )
    emitter = EventEmitter()

    # This is the live path (transient store; ``queue is None``): it must not raise.
    landed = emitter._queue_event_locally(_live_event("evt-live-new"))
    assert landed is True

    store = ProjectSyncStore(OWNER)
    authority = store.layout_generation()
    # The cutover COMPLETED — the machine layout is project-only, not stuck pending.
    assert authority.peek_state().mode is LayoutMode.PROJECT_ONLY
    # The new event landed AND the pre-existing legacy events were conserved.
    assert _journal_ids(store) == {"evt-legacy-a", "evt-legacy-b", "evt-live-new"}
