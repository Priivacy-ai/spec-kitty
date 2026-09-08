"""Entry-point ownership-barrier tests for the workflow rollback (spec-kitty #4072).

The operator acceptance on PR #4072 (2026-09-08) demonstrated two schedules
against the round-1 head, using the real store/rollback modules, the real
workflow restore function, real temporary git repositories and the real
mission lock:

1. A snapshots and emits; writer B acquires the same lock, appends and
   commits; A captures the tail OUTSIDE any lock and adopts B's event as
   "expected" -- A's later rollback then cuts B's committed event.
2. B appends/commits after A's capture. The tail rollback correctly refuses
   and preserves the rows, but the restore path IGNORES the refusal and
   restores the obsolete ``status.json`` bytes anyway.

The correction attaches the ownership record to the lock-held write window
(``owned_emission_window`` spans snapshot -> emit -> capture) and makes the
derived-snapshot restore share the rollback's ownership decision. These
tests drive the REAL entry points (``agent action implement`` /
``agent action review``) over real git repos and the real mission lock and
prove both barriers:

* schedule 1 is now physically impossible -- writer B (another thread, real
  ``feature_status_lock`` take) is locked out for the whole window, so the
  capture can only name this operation's rows;
* schedule 2's refusal outcome holds -- B's row landing after the capture
  survives the failed commit's rollback, the derived snapshot is preserved
  at its newer coherent state, and an explicit recoverable diagnostic is
  printed;
* the review shell's existing L1 (which spans emit AND commit) is preserved
  -- B is locked out through the commit there too, and a failed commit rolls
  the log back to its verified pre-emit state.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

import specify_cli.cli.commands.agent.workflow as workflow
import specify_cli.status as status_facade
from specify_cli import app as root_app
from specify_cli.status.locking import (
    FeatureStatusLockTimeoutError,
    _get_thread_locks,
    feature_status_lock,
    feature_status_lock_path,
)
from tests.characterization.test_trio_json_envelope import _build_mission_repo

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

runner = CliRunner()

_B_TIMEOUT_SECONDS = 0.4


def _events_rows(feature_dir: Path) -> list[dict[str, Any]]:
    events_path = feature_dir / "status.events.jsonl"
    if not events_path.exists():
        return []
    return [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _b_can_acquire_lock(repo_root: Path, feature_dir: Path, timeout: float = _B_TIMEOUT_SECONDS) -> bool:
    """True when writer B -- another THREAD -- acquires the mission lock.

    The real lock, the real lock-root resolution, the real bounded-wait
    contract: a ``False`` here means B is locked out for the whole window.
    """
    acquired: list[bool] = []

    def _b() -> None:
        try:
            with feature_status_lock(repo_root, feature_dir.name, timeout=timeout):
                acquired.append(True)
        except FeatureStatusLockTimeoutError:
            acquired.append(False)

    thread = threading.Thread(target=_b, name="writer-B")
    thread.start()
    thread.join(timeout=timeout + 5)
    assert not thread.is_alive(), "writer B never finished its lock attempt"
    return bool(acquired and acquired[0])


def _assert_lock_held_by_this_thread(repo_root: Path, feature_dir: Path, where: str) -> None:
    """The schedule-1 barrier: the entry point holds the mission L1 at *where*."""
    lock_key = str(feature_status_lock_path(repo_root, feature_dir.name))
    assert lock_key in _get_thread_locks(), (
        f"the mission status lock must be held by the claim thread at {where} "
        "(owned_emission_window / the review shell's L1) -- otherwise a "
        "concurrent writer can be adopted into the rollback's expected ids"
    )


def _patch_claim_emit_with_barrier(
    monkeypatch: pytest.MonkeyPatch,
    facade_name: str,
    repo_root: Path,
    feature_dir: Path,
    b_locked_out: list[bool],
) -> None:
    """Wrap the real claim emit: prove L1 is held across it and B is locked out."""
    real_emit = getattr(status_facade, facade_name)

    def _barrier_probe(**kwargs: Any) -> Any:
        _assert_lock_held_by_this_thread(repo_root, feature_dir, f"{facade_name} (emit)")
        b_locked_out.append(not _b_can_acquire_lock(repo_root, feature_dir))
        return real_emit(**kwargs)

    monkeypatch.setattr(status_facade, facade_name, _barrier_probe)


def _patch_safe_commit(
    monkeypatch: pytest.MonkeyPatch,
    trigger_message_fragment: str,
    on_trigger: Any,
) -> None:
    """Patch ``workflow.safe_commit``; the *on_trigger* callable fires only for
    the claim's own commit (every other commit delegates to the real seam)."""
    real_safe_commit = workflow.safe_commit

    def _patched(**kwargs: Any) -> Any:
        if trigger_message_fragment in str(kwargs.get("message", "")):
            return on_trigger(**kwargs)
        return real_safe_commit(**kwargs)

    monkeypatch.setattr(workflow, "safe_commit", _patched)


def test_implement_claim_ownership_barrier_preserves_a_post_capture_writer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Schedule 1 + schedule 2 on the implement entry point.

    The claim's snapshot, emits and capture run inside ONE lock-held window
    (B is locked out there); B then lands a row AFTER the capture (before the
    commit, exactly the operator's schedule-2 interleave); the commit fails;
    the rollback refuses to cut B's row, the derived snapshot is preserved at
    its newer coherent state, and the recoverable diagnostic is printed.
    """
    monkeypatch.setenv("SPEC_KITTY_SYNC_MINIMAL_IMPORT", "1")
    repo_root, mission_dirname = _build_mission_repo(
        tmp_path,
        monkeypatch,
        coord=False,
        mission_slug="ownership-barrier-implement",
        wp_lane="planned",
    )
    feature_dir = repo_root / "kitty-specs" / mission_dirname
    events_path = feature_dir / "status.events.jsonl"
    status_path = feature_dir / "status.json"
    rows_before = len(_events_rows(feature_dir))

    b_locked_out: list[bool] = []
    _patch_claim_emit_with_barrier(monkeypatch, "start_implementation_status", repo_root, feature_dir, b_locked_out)

    status_bytes_at_commit: list[bytes] = []
    b_acquired_after_window: list[bool] = []

    def _fail_claim_commit(**_kwargs: Any) -> None:
        # The window has closed by now: writer B CAN take the lock and land a
        # row after A's capture (the operator's schedule-2 interleave).
        status_bytes_at_commit.append(status_path.read_bytes())
        b_acquired_after_window.append(_b_can_acquire_lock(repo_root, feature_dir, timeout=5))
        with feature_status_lock(repo_root, feature_dir.name), events_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"event_id": "foreign-B", "wp_id": "WP01"}) + "\n")
        raise RuntimeError("commit failed after writer B landed")

    _patch_safe_commit(monkeypatch, "Start WP01 implementation", _fail_claim_commit)

    result = runner.invoke(
        root_app,
        ["agent", "action", "implement", "WP01", "--mission", mission_dirname, "--agent", "tester"],
    )

    assert result.exit_code == 1, result.output
    # Schedule-1 barrier: B was locked out for the whole snapshot -> emit ->
    # capture window, so the capture named only this claim's rows.
    assert b_locked_out and all(b_locked_out), "writer B must be locked out while the claim's ownership window is open"
    # B landed AFTER the capture (the window had closed) -- and its row
    # SURVIVED the failed commit's rollback.
    assert b_acquired_after_window == [True]
    rows_after = _events_rows(feature_dir)
    row_ids = {row.get("event_id") for row in rows_after}
    assert "foreign-B" in row_ids, "writer B's durable row must survive the refused rollback"
    assert any(row.get("to_lane") == "in_progress" for row in rows_after), (
        "the claim's own emitted transition must also survive the refusal (stranded, recoverable)"
    )
    assert len(rows_after) >= rows_before + 2, "both this claim's emitted rows and B's row must be present after the refusal"
    # Schedule-2 fix: the derived snapshot is preserved at its newer coherent
    # state -- never restored to the obsolete pre-emit bytes.
    assert status_path.read_bytes() == status_bytes_at_commit[0], "status.json must stay at its newer coherent state when the rollback refuses"
    # The explicit recoverable diagnostic is printed on the failing path.
    assert "Event-log rollback REFUSED" in result.output, result.output


def test_review_claim_ownership_barrier_spans_emit_and_commit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The review entry point keeps its existing L1 across emit AND commit.

    B is locked out for the whole window including the commit; a failed commit
    rolls the event log back to its verified pre-emit state (the tail is
    exactly this claim's rows, so nothing is refused) and restores the
    pre-emit derived snapshot.
    """
    monkeypatch.setenv("SPEC_KITTY_SYNC_MINIMAL_IMPORT", "1")
    repo_root, mission_dirname = _build_mission_repo(
        tmp_path,
        monkeypatch,
        coord=False,
        mission_slug="ownership-barrier-review",
        wp_lane="for_review",
    )
    feature_dir = repo_root / "kitty-specs" / mission_dirname
    events_path = feature_dir / "status.events.jsonl"
    status_path = feature_dir / "status.json"

    events_before = events_path.read_bytes() if events_path.exists() else None
    status_before = status_path.read_bytes() if status_path.exists() else None

    b_locked_out: list[bool] = []
    _patch_claim_emit_with_barrier(monkeypatch, "start_review_status", repo_root, feature_dir, b_locked_out)

    def _fail_review_commit(**_kwargs: Any) -> None:
        # The review shell's L1 spans the commit too: B is STILL locked out
        # here, so nothing can interleave between capture and rollback.
        _assert_lock_held_by_this_thread(repo_root, feature_dir, "the review commit")
        b_locked_out.append(not _b_can_acquire_lock(repo_root, feature_dir))
        raise RuntimeError("review commit failed")

    _patch_safe_commit(monkeypatch, "Start WP01 review", _fail_review_commit)

    result = runner.invoke(
        root_app,
        ["agent", "action", "review", "WP01", "--mission", mission_dirname, "--agent", "tester"],
    )

    assert result.exit_code == 1, result.output
    # B was locked out across the emit window AND across the commit -- the
    # review shell's L1 covers the whole snapshot -> emit -> capture -> commit
    # -> rollback span, so the capture names exactly this claim's rows.
    assert len(b_locked_out) >= 1 and all(b_locked_out), "writer B must be locked out across the review claim's emit and commit"
    # The verified rollback: the log is back to its exact pre-emit bytes.
    assert (events_path.read_bytes() if events_path.exists() else None) == events_before, (
        "the review claim's emitted rows must be cut back on the verified rollback"
    )
    # The derived snapshot restore shared the (successful) ownership decision.
    assert (status_path.read_bytes() if status_path.exists() else None) == status_before, (
        "status.json must be restored to its pre-emit state on the verified rollback"
    )
