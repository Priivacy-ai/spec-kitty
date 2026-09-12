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
import subprocess
import threading
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner
from ulid import ULID

import specify_cli.cli.commands.agent.workflow as workflow
import specify_cli.status as status_facade
from specify_cli import app as root_app
from specify_cli.status.locking import (
    FeatureStatusLockTimeoutError,
    _get_thread_locks,
    feature_status_lock,
    feature_status_lock_path,
)
from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.reducer import materialize, materialize_snapshot, materialize_to_json
from specify_cli.status.store import append_event_verified
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


# ---------------------------------------------------------------------------
# spec-kitty #4087 (operator acceptance follow-up): the
# successful-truncation -> unlocked snapshot-restoration race.
# ---------------------------------------------------------------------------

_B_WRITE_TIMEOUT_SECONDS = 20.0


def _git_ok(cwd: Path, *args: str) -> str:
    return (
        subprocess.check_output(  # noqa: S603 -- fixed argv, test-only
            ["git", "-C", str(cwd), *args], stderr=subprocess.PIPE
        )
        .decode()
        .strip()
    )


def _writer_b(
    repo_root: Path,
    feature_dir: Path,
    *,
    to_lane: Any,
    proof: dict[str, Any],
    errors: list[BaseException],
) -> None:
    """A separately locked, canonically materialized, Git-committed writer B.

    Mirrors the operator's witness (#4087): B takes the REAL mission lock,
    appends a valid event, canonically materializes ``status.json``, and
    Git-commits BOTH artifacts -- so the state B leaves behind is
    acknowledged at a real commit, not a synthetic uncommitted row. The
    bytes B observes at lock entry are recorded first: they prove B entered
    only AFTER A's restore had already landed (never between A's successful
    truncation and its snapshot restore).
    """
    events_path = feature_dir / "status.events.jsonl"
    status_path = feature_dir / "status.json"
    try:
        with feature_status_lock(repo_root, feature_dir.name, timeout=_B_WRITE_TIMEOUT_SECONDS):
            proof["b_acquired_lock"] = True
            proof["b_status_at_entry"] = status_path.read_bytes() if status_path.exists() else None
            current = materialize_snapshot(feature_dir).work_packages["WP01"]["lane"]
            meta = json.loads((feature_dir / "meta.json").read_text(encoding="utf-8"))
            event = StatusEvent(
                event_id=str(ULID()),
                mission_slug=feature_dir.name,
                mission_id=str(meta["mission_id"]),
                wp_id="WP01",
                from_lane=Lane(current),
                to_lane=to_lane,
                at="2026-09-08T23:20:00Z",
                actor="independent-writer-B",
                force=False,
                execution_mode="direct_repo",
            )
            append_event_verified(feature_dir, event)
            materialize(feature_dir)
            proof["b_event_id"] = event.event_id
            proof["b_snapshot"] = status_path.read_bytes()
            assert proof["b_snapshot"] == materialize_to_json(materialize_snapshot(feature_dir)).encode()
            paths = [str(p.relative_to(repo_root)) for p in (events_path, status_path)]
            _git_ok(repo_root, "add", "--", *paths)
            _git_ok(repo_root, "commit", "--only", "-m", "Acknowledge independent writer B", "--", *paths)
            proof["b_commit"] = _git_ok(repo_root, "rev-parse", "HEAD")
    except BaseException as exc:  # noqa: BLE001 -- recorded and re-raised to the main thread
        errors.append(exc)


def _patch_snapshot_restore_write_with_lock_probe(
    monkeypatch: pytest.MonkeyPatch,
    repo_root: Path,
    feature_dir: Path,
    proof: dict[str, Any],
) -> None:
    """Probe the derived-snapshot RESTORE write: it must happen inside the L1.

    ``Path.write_bytes`` is the one seam both the pre-#4087 code (the restore
    wrote ``status.json`` AFTER the rollback helper's lock had released) and
    the fixed code (the restore writes inside ``rollback_status_artifacts``'s
    single hold) share for the restore write. The canonical materialization
    path does NOT use ``write_bytes`` (``write_text`` + ``os.replace``), so
    only the restore write is intercepted. Every intercepted write records
    whether the writing thread holds the mission L1 at that moment: the
    pre-#4087 schedule's restore write held no lock, so a ``False`` here is
    the race, caught deterministically.
    """
    status_path_resolved = (feature_dir / "status.json").resolve()
    real_write_bytes = Path.write_bytes

    def _probing_write_bytes(self: Path, data: bytes) -> int:
        try:
            is_restore_write = self.resolve() == status_path_resolved
        except OSError:
            is_restore_write = False
        if is_restore_write:
            lock_key = str(feature_status_lock_path(repo_root, feature_dir.name))
            proof.setdefault("restore_write_lock_held", []).append(lock_key in _get_thread_locks())
        return real_write_bytes(self, data)

    monkeypatch.setattr(Path, "write_bytes", _probing_write_bytes)


def _patch_truncate_with_restore_window_barrier(
    monkeypatch: pytest.MonkeyPatch,
    repo_root: Path,
    feature_dir: Path,
    proof: dict[str, Any],
    errors: list[BaseException],
    *,
    to_lane: Any,
) -> None:
    """Wrap the store truncate primitive with the restore-window barrier.

    The probe fires INSIDE ``rollback_status_artifacts``'s single lock hold,
    right after A's REAL verified cut landed and right BEFORE A restores the
    derived snapshot: (1) the mission L1 is held by A's thread, (2) writer B
    (another thread, real bounded lock take) is locked OUT of the window, and
    (3) the full writer B is started -- it blocks on the L1 until A's whole
    rollback-restore window (not just the log half) has completed.
    """
    import specify_cli.status.rollback as rollback_module

    real_truncate = rollback_module.truncate_events_log
    events_path = feature_dir / "status.events.jsonl"

    def _probe(fd: Path, *, pre_emit_event_size: int) -> None:
        size_before = events_path.stat().st_size
        real_truncate(fd, pre_emit_event_size=pre_emit_event_size)
        proof["truncated_bytes"] = size_before - events_path.stat().st_size
        assert proof["truncated_bytes"] > 0, "A must successfully cut its own tail before B begins"
        # A still holds the mission L1: the rollback decision, the truncation
        # AND the snapshot restore share one hold (#4087).
        _assert_lock_held_by_this_thread(repo_root, feature_dir, "the restore window (post-truncate, pre-restore)")
        proof["b_locked_out_during_window"] = not _b_can_acquire_lock(repo_root, feature_dir)
        worker = threading.Thread(
            target=_writer_b,
            name="independent-writer-B",
            kwargs={"repo_root": repo_root, "feature_dir": feature_dir, "to_lane": to_lane, "proof": proof, "errors": errors},
        )
        worker.start()
        proof["b_thread"] = worker

    monkeypatch.setattr(rollback_module, "truncate_events_log", _probe)


@pytest.mark.parametrize("resume", [False, True], ids=["implement", "bare-resume"])
def test_successful_truncation_restore_window_blocks_an_independent_committed_writer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    resume: bool,
) -> None:
    """The #4087 schedule on BOTH real entry points: A's verified tail cut and
    A's derived-snapshot restore share ONE lock-held window, so a separately
    locked writer B that appends, canonically materializes and Git-commits
    BOTH artifacts can only land AFTER A's restore -- never between the
    successful truncation and the restore (the schedule that left the working
    snapshot byte-identical to A's obsolete pre-emission bytes, differing
    from both B's committed snapshot and canonical replay).
    """
    monkeypatch.setenv("SPEC_KITTY_SYNC_MINIMAL_IMPORT", "1")
    mission_slug = "restore-window-resume" if resume else "restore-window-implement"
    repo_root, mission_dirname = _build_mission_repo(
        tmp_path,
        monkeypatch,
        coord=False,
        mission_slug=mission_slug,
        wp_lane="in_progress" if resume else "planned",
    )
    if resume:
        # The bare-resume branch needs the canonical in_progress state (the
        # lane is event-log-only), so first drive the real implement command
        # once, unpatched, exactly as the operator's witness does.
        from specify_cli.cli.commands.implement import implement as top_level_implement

        top_level_implement(
            wp_id="WP01",
            mission=mission_dirname,
            json_output=False,
            recover=False,
            acknowledge_not_bulk_edit=False,
            actor="system",
        )
    feature_dir = repo_root / "kitty-specs" / mission_dirname
    status_path = feature_dir / "status.json"

    proof: dict[str, Any] = {}
    errors: list[BaseException] = []
    # Record A's ACTUAL restore reference (the bytes its owned_emission_window
    # captured at entry -- for the implement entry point the CLI legitimately
    # emits and commits baseline rows BEFORE the claim window opens, so the
    # window's own capture, not a pre-invoke disk read, is A's pre-emit state).
    real_restore = workflow._restore_status_artifacts

    def _restore_spy(**kwargs: Any) -> bool:
        proof["a_restore_pre_emit_bytes"] = kwargs["pre_emit_status_bytes"]
        return real_restore(**kwargs)

    monkeypatch.setattr(workflow, "_restore_status_artifacts", _restore_spy)

    commit_fragment = "Refresh WP01 implementation liveness" if resume else "Start WP01 implementation"
    to_lane = Lane.FOR_REVIEW if resume else Lane.CLAIMED
    _patch_snapshot_restore_write_with_lock_probe(monkeypatch, repo_root, feature_dir, proof)
    _patch_truncate_with_restore_window_barrier(monkeypatch, repo_root, feature_dir, proof, errors, to_lane=to_lane)

    attempted: list[str] = []

    def _fail_a_commit(**kwargs: Any) -> None:
        attempted.append(str(kwargs.get("message", "")))
        raise RuntimeError("injected A commit failure")

    _patch_safe_commit(monkeypatch, commit_fragment, _fail_a_commit)

    args = ["agent", "action", "implement", "WP01", "--mission", mission_dirname] + ([] if resume else ["--agent", "tester"])
    result = runner.invoke(root_app, args)

    assert result.exit_code == 1, result.output
    assert attempted, f"A's commit was never reached: {result.output}"
    # A's tail-verified rollback SUCCEEDED -- it cut exactly its own rows.
    assert proof["truncated_bytes"] > 0
    # The deterministic #4087 guard: the derived-snapshot RESTORE write
    # happened INSIDE the mission L1 (the pre-fix code wrote it after the
    # rollback helper's lock had released -- the seam writer B entered).
    assert proof.get("restore_write_lock_held"), "A's snapshot restore write never fired"
    assert all(proof["restore_write_lock_held"]), (
        "A restored the derived snapshot OUTSIDE the mission status lock -- the #4087 successful-truncation/snapshot-restore race"
    )
    # The barrier: writer B was locked out of the whole restore window (A
    # held the mission L1 across the truncation AND the snapshot restore).
    assert proof["b_locked_out_during_window"] is True, (
        "writer B entered between A's successful truncation and A's snapshot restore -- the #4087 successful-truncation/snapshot-restore race"
    )
    worker: threading.Thread = proof["b_thread"]
    worker.join(timeout=_B_WRITE_TIMEOUT_SECONDS + 10)
    assert not worker.is_alive(), "writer B never finished its locked window (deadlocked on the mission L1?)"
    assert not errors, f"writer B failed: {errors!r}"
    assert proof["b_acquired_lock"] is True
    assert proof.get("b_commit"), "writer B must Git-commit both artifacts"
    # B entered only AFTER A's restore had landed: the bytes B observed at
    # lock entry are exactly the pre-emit bytes A restored inside the window
    # (the resume case's pre-emit snapshot; the implement case's window-entry
    # snapshot), never the un-restored post-emit state.
    assert proof["b_status_at_entry"] == proof["a_restore_pre_emit_bytes"], (
        "writer B observed a snapshot other than A's restored pre-emit state at lock entry -- B entered inside A's restore window (the #4087 race)"
    )
    # B's event survives in the working log.
    assert proof["b_event_id"] in {row.get("event_id") for row in _events_rows(feature_dir)}
    # The acceptance itself: the working snapshot equals B's acknowledged
    # committed snapshot AND the current canonical replay -- A's restored
    # pre-emit bytes were built on coherently, never left clobbering B.
    current = status_path.read_bytes()
    assert current == proof["b_snapshot"], "A's restore clobbered writer B's acknowledged committed snapshot (the #4087 race)"
    assert current == materialize_to_json(materialize_snapshot(feature_dir)).encode()
    if proof["a_restore_pre_emit_bytes"] is not None:
        assert current != proof["a_restore_pre_emit_bytes"], "A's restored pre-emit snapshot was left standing over writer B's committed state"
