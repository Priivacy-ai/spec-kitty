"""T005 / FR-005: an empty selection must name its real cause (#3030).

`sync now` printed an all-zero dispatch summary and nothing else:

    Event sync (TEAMSPACE): delivered 0  duplicate 0  pending 0  rejected 0
    transient 0  terminal-failed 0  (selected 0)

An operator with three events on disk cannot tell from that whether the journal is
empty, none of their projects has consented, every row's identity is unresolved, or
the rows are simply already delivered. This mission multiplied those reasons, so
"selected 0" now conflates four distinct situations with four different remedies —
and one of them ("nobody consented") means the operator's data is never going to
ship until they act.

This file is also **SC-003's missing fifth fail-closed test**. The other four
(unresolvable routing FR-003, absent consent FR-002, unresolvable identity FR-011,
multi-project batch FR-004) exist; empty selection FR-005 did not, so SC-003 was
not closed.

Scope correction recorded here because the requirement text is now out of date:
FR-005 cites `sync/batch.py:1484-1488` and a `{"events": []}` POST. Neither is
reachable from `sync now` any more. That message lives in `sync_all_queued_events`,
the legacy queue drain FR-012 retired — `sync/__init__.py` deliberately stops
re-exporting it and `sync now` calls `_run_event_sync_dispatch` instead. And
`dispatcher._post` already returns early on an empty batch, so no empty POST is
issued. Measured before writing this file: the no-Private-Teamspace string does not
appear in `sync now`'s output, the receiver records zero POSTs, and the exit code is
already 0. What was genuinely missing is the *cause*, which is what these tests pin.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands import sync as sync_command
from specify_cli.cli.commands.sync import app
from specify_cli.delivery.receivers import StubReceiver
from specify_cli.event_journal.journal import EventJournal
from specify_cli.event_journal.models import Event
from specify_cli.sync.feature_flags import SAAS_SYNC_ENV_VAR
from specify_cli.sync.project_store import ProjectSyncStore

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

runner = CliRunner()

CONSENTED = "aaaaaaaa-0000-0000-0000-00000000000a"
NEVER_OPTED_IN = "bbbbbbbb-0000-0000-0000-00000000000b"


class _OkPreflight:
    ok = True

    def render(self, console: object) -> None:  # pragma: no cover - never called
        return None


class _SpyReceiver(StubReceiver):  # type: ignore[misc]
    """Records every batch handed to it, so "no network request" is observable."""

    def __init__(self, sink: list[tuple[str, ...]]) -> None:
        super().__init__()
        self._sink = sink

    def deliver(self, batch):  # type: ignore[no-untyped-def]  # noqa: ANN001, ANN201 - matches the receiver protocol
        self._sink.append(tuple(event.event_id for event in batch))
        return super().deliver(batch)


@pytest.fixture(autouse=True)
def _now_machinery(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, ...]]:
    """Isolate the home and neutralise everything `sync now` gates on but this test.

    The dispatch path itself is NOT stubbed — the point is what the real drain
    reports — but the receiver is a spy so an empty selection can be shown to issue
    no request at all (SC-003's "denies with no network request").
    """
    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home))
    monkeypatch.setenv("HOME", str(tmp_path / "user-home"))
    monkeypatch.setenv(SAAS_SYNC_ENV_VAR, "1")
    monkeypatch.setenv("COLUMNS", "220")
    monkeypatch.setattr(sync_command, "is_saas_sync_enabled", lambda: True)
    monkeypatch.setattr(sync_command, "enforce_teamspace_mission_state_ready", lambda **_: None)
    monkeypatch.setattr("specify_cli.sync.preflight.run_preflight", lambda **_: _OkPreflight())

    class _EmptyQueue:
        def size(self) -> int:
            return 0

    class _Service:
        queue = _EmptyQueue()

        def drain_body_uploads_only(self) -> None:
            return None

    monkeypatch.setattr("specify_cli.sync.background.get_sync_service", lambda: _Service())

    posted: list[tuple[str, ...]] = []
    monkeypatch.setattr(
        sync_command,
        "_resolve_active_receiver",
        lambda *_a, **_k: _SpyReceiver(posted),
    )
    from specify_cli.event_journal.journal import reset_journal_cache
    import specify_cli.sync.routing as routing

    reset_journal_cache()
    store = ProjectSyncStore(NEVER_OPTED_IN)
    authority = store.layout_generation()
    authority.begin_cutover("sync-now-empty-selection")
    authority.publish_project_only("sync-now-empty-selection", verify_exact=lambda: True)
    with store.unit_of_work():
        pass
    with store.unit_of_work() as unit:
        unit.execute(
            "INSERT INTO project_target_admissions "
            "(project_uuid, target_identity, account_identity, private_teamspace_id, "
            "configuration_generation, admission_state, admission_generation, binding_audience) "
            "VALUES (?, 'https://app.spec-kitty.ai', 'account-test', 'team-test', 1, "
            "'admitted', '1', 'private-teamspace:team-test')",
            (NEVER_OPTED_IN,),
        )
    routed = SimpleNamespace(
        project_uuid=store.project_uuid,
        project_slug="empty-selection-test",
        repo_slug="acme/app",
        build_id="empty-selection",
        repo_root=tmp_path,
    )
    monkeypatch.setattr(routing, "resolve_checkout_sync_routing_readonly", lambda *_a, **_k: routed)
    monkeypatch.setattr(routing, "resolve_checkout_sync_routing", lambda *_a, **_k: routed)
    monkeypatch.setattr(sync_command, "_current_event_sync_scope", lambda: SimpleNamespace(user_id=None, team_slug=None))
    monkeypatch.setattr(sync_command, "_assert_event_sync_runtime_authority", lambda **_: None)
    return posted


def _event(event_id: str, uuid: str | None, created_at: str, **kwargs: object) -> Event:
    return Event(
        event_id=event_id,
        event_type="WorkPackageApproved",
        payload=json.dumps({"event_id": event_id}).encode(),
        occurred_at=created_at,
        created_at=created_at,
        project_uuid=uuid,
        **kwargs,
    )


class _ProjectJournalFixture:
    def __init__(self) -> None:
        self.store = ProjectSyncStore(NEVER_OPTED_IN)
        self.authority = self.store.layout_generation()

    def append(self, event: Event) -> None:
        with self.store.unit_of_work() as unit:
            EventJournal(unit, self.authority).append(event)


def _journal() -> _ProjectJournalFixture:
    return _ProjectJournalFixture()


def _flat(output: str) -> str:
    """Rich wraps at the console width; assertions are about words, not layout."""
    return " ".join(output.split())


# --- the four causes ---------------------------------------------------------


def test_sync_now_names_absent_consent_as_the_cause(
    _now_machinery: list[tuple[str, ...]],
) -> None:
    """The incident's own shape, and the one with an actionable remedy.

    Red before the fix: the entire output was the all-zero summary ending
    ``(selected 0)``. Nothing named consent, nothing named the project, and an
    operator had no way to learn that their data will never ship until they opt in.
    """
    journal = _journal()
    for index in range(3):
        journal.append(
            _event(
                f"evt-{index}",
                NEVER_OPTED_IN,
                f"2026-07-01T00:00:0{index}+00:00",
                repo_slug="acme/app",
            )
        )

    result = runner.invoke(app, ["now"])

    assert result.exit_code == 1, result.output
    out = _flat(result.output)
    assert "nothing to deliver" in out.lower(), "an empty selection must say so in words, not only as `(selected 0)`"
    assert "consent" in out.lower(), "the cause is that no project has consented; the operator cannot act on a bare zero"
    assert "acme/app" in out, "name the project whose rows are being withheld"
    assert "3" in out, "and how many of its events are affected"


def test_sync_now_says_the_journal_is_empty_when_that_is_the_truth(
    _now_machinery: list[tuple[str, ...]],
) -> None:
    """A genuinely empty store must NOT be reported as a consent problem.

    Conflating "you have no data" with "your data is being withheld" sends an
    operator to change consent settings that were never the issue.
    """
    _journal()  # create the schema, add no rows

    result = runner.invoke(app, ["now"])

    assert result.exit_code == 0, result.output
    out = _flat(result.output).lower()
    assert "nothing to deliver" in out
    assert "journal is empty" in out or "no events" in out
    assert "consent" not in out, "an empty journal is not a consent problem and must not be described as one"


def test_sync_now_names_unresolved_identity_when_that_is_why(
    _now_machinery: list[tuple[str, ...]],
) -> None:
    """FR-011's population, with the remedy H4 wired rather than `purge`."""
    journal = _journal()
    with pytest.raises(ValueError, match="project UUID"):
        journal.append(_event("evt-anon-0", None, "2026-07-01T00:00:00+00:00"))

    result = runner.invoke(app, ["now"])

    assert result.exit_code == 0, result.output
    out = _flat(result.output)
    assert "nothing to deliver" in out.lower()
    assert "journal is empty" in out.lower() or "no events" in out.lower()


def test_sync_now_does_not_claim_a_cause_it_cannot_prove(
    _now_machinery: list[tuple[str, ...]],
) -> None:
    """The residual case, and the one most likely to produce a false diagnosis.

    Here a project HAS consented and its rows are simply already delivered. The
    report cannot distinguish "already delivered" from "terminally drain-blocked"
    without ledger state, so the message must state what is known and stop. Naming
    consent here would be the same wrong-and-actionable diagnosis that the
    no-Private-Teamspace message was.
    """
    from specify_cli.sync.consent import record_project_opt_in

    record_project_opt_in(NEVER_OPTED_IN, actor="sync-now-empty-selection-test")
    journal = _journal()
    journal.append(_event("evt-ok-0", NEVER_OPTED_IN, "2026-07-01T00:00:00+00:00"))

    first = runner.invoke(app, ["now"])
    assert first.exit_code == 0, first.output
    assert "delivered 1" in _flat(first.output), first.output

    second = runner.invoke(app, ["now"])

    assert second.exit_code == 1, second.output
    out = _flat(second.output)
    assert "nothing to deliver" in out.lower()
    assert "has not consented" not in out.lower(), "this project DID consent — claiming otherwise is a false cause"
    assert "journal is empty" not in out.lower(), "the journal holds a row"
    # Both candidate reasons must be offered, neither asserted as the answer.
    assert "already been delivered" in out.lower()
    assert "drain-blocked" in out.lower()


# --- SC-003: the fail-closed properties -------------------------------------


def test_an_empty_selection_issues_no_network_request(
    _now_machinery: list[tuple[str, ...]],
) -> None:
    """SC-003's shared requirement: each fail-closed path denies with no request.

    Already true via ``dispatcher._post``'s early return; pinned here because
    SC-003 requires it per path and this was the path without a test.
    """
    journal = _journal()
    for index in range(3):
        journal.append(_event(f"evt-{index}", NEVER_OPTED_IN, f"2026-07-01T00:00:0{index}+00:00"))

    result = runner.invoke(app, ["now"])

    assert result.exit_code == 1, result.output
    assert _now_machinery == [], f"no batch may be built or POSTed for an empty selection, got {_now_machinery}"


def test_an_empty_selection_exits_zero(_now_machinery: list[tuple[str, ...]]) -> None:
    """Historical node name; strict mode now fails closed on retained work.

    Default strict returns 1 when retained rows cannot progress; the explicit
    ``--no-strict`` operator choice retains the diagnostic exit-zero behavior.
    """
    journal = _journal()
    journal.append(_event("evt-0", NEVER_OPTED_IN, "2026-07-01T00:00:00+00:00"))

    strict = runner.invoke(app, ["now"])
    assert strict.exit_code == 1, strict.output

    lenient = runner.invoke(app, ["now", "--no-strict"])
    assert lenient.exit_code == 0, lenient.output


def test_a_healthy_drain_does_not_print_the_empty_diagnosis(
    _now_machinery: list[tuple[str, ...]],
) -> None:
    """The guard against over-firing: a real delivery must stay quiet about causes."""
    from specify_cli.sync.consent import record_project_opt_in

    record_project_opt_in(NEVER_OPTED_IN, actor="sync-now-empty-selection-test")
    journal = _journal()
    journal.append(_event("evt-ok-0", NEVER_OPTED_IN, "2026-07-01T00:00:00+00:00"))

    result = runner.invoke(app, ["now"])

    assert result.exit_code == 0, result.output
    out = _flat(result.output)
    assert "delivered 1" in out
    assert "nothing to deliver" not in out.lower()
    assert _now_machinery == [("evt-ok-0",)]
