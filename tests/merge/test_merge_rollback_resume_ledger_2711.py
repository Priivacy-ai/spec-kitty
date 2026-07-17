"""RED-first P0 reproduction for #2711 — merge rollback/resume ledger split-brain.

NOTE:
    RED-FIRST P0 reproduction of #2711 per ADR 2026-07-17-1
    (docs/adr/3.x/2026-07-17-1-red-main-is-honest-ci-is-release-authority.md).
    Intentionally FAILS until the product bug is fixed — a red mainline is the honest
    signal of this release-blocking P0. Do NOT xfail/skip/quarantine to green; fix the
    product. Tracking issue: #2711.

Bug (#2711): When a multi-WP coordination merge advances the target *after*
``approved -> done`` events are transactionally committed, and the target
advancement then fails, the executor's rollback restores only the working-tree
bookkeeping *bytes* (``_restore_final_bookkeeping_snapshots``). The ``done``
events already committed to the durable event log survive that rollback, so the
committed append-only status ledger says ``done`` while the reverted working
status/merge-state say ``approved`` / ``0`` completed. On ``spec-kitty merge
--resume`` the reverted merge-state reports ``0/N already done`` and the
per-WP recording loop re-emits duplicate ``done`` transitions.

This test drives the *real* product rollback helpers
(``_capture_bookkeeping_snapshots`` / ``_restore_final_bookkeeping_snapshots``)
and the real target-ledger reducer (``_parse_target_lanes_by_wp``) over a
git-backed status event log. The durable ``git commit`` of the ``done`` event
stands in for ``emit_status_transition_transactional`` committing the transition
to the coordination branch — the byte-restore rollback cannot revert a commit,
which is the exact defect. It witnesses the ledger split-brain named in the
issue's Reproduction steps 3-4 and the ``0/N`` resume symptom.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from specify_cli.merge.bookkeeping_projection import (
    _capture_bookkeeping_snapshots,
    _restore_final_bookkeeping_snapshots,
)
from specify_cli.merge.done_bookkeeping import _parse_target_lanes_by_wp
from specify_cli.merge.state import (
    MergeState,
    get_state_path,
    load_state,
    save_state,
)

pytestmark = [pytest.mark.git_repo, pytest.mark.non_sandbox]  # non_sandbox: subprocess git

MISSION_ID = "067-rollback-resume-ledger"
MISSION_SLUG = MISSION_ID
_EVENTS_REL = f"kitty-specs/{MISSION_SLUG}/status.events.jsonl"


def _git(args: list[str], cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def _event(wp_id: str, from_lane: str, to_lane: str, event_id: str) -> str:
    """Serialize one status event line matching the append-only log schema."""
    return json.dumps(
        {
            "event_id": event_id,
            "mission_slug": MISSION_SLUG,
            "wp_id": wp_id,
            "from_lane": from_lane,
            "to_lane": to_lane,
            "at": "2026-07-17T12:00:00+00:00",
            "actor": "merge",
            "force": False,
            "execution_mode": "worktree",
        },
        sort_keys=True,
    )


@pytest.fixture
def merge_repo(tmp_path: Path) -> Path:
    """A git repo whose event log has WP01 committed at ``approved``."""
    _git(["init"], tmp_path)
    _git(["config", "user.email", "test@example.com"], tmp_path)
    _git(["config", "user.name", "Test User"], tmp_path)
    (tmp_path / "README.md").write_text("# Test\n", encoding="utf-8")

    feature_dir = tmp_path / "kitty-specs" / MISSION_SLUG
    feature_dir.mkdir(parents=True)
    events_file = feature_dir / "status.events.jsonl"
    events_file.write_text(
        _event("WP01", "for_review", "approved", "01REPRO2711APPROVED") + "\n",
        encoding="utf-8",
    )
    _git(["add", "."], tmp_path)
    _git(["commit", "-m", "mission at approved"], tmp_path)
    return tmp_path


@pytest.mark.regression
def test_merge_rollback_leaves_committed_done_opposed_to_reverted_status(
    merge_repo: Path,
) -> None:
    """Rollback must not leave a committed ``done`` event the working state reverted.

    Reproduces #2711: after the target-advance rollback, the committed event log
    still carries ``done`` while the restored working status/merge-state say the
    WP is not done — corrupting the append-only ledger (the sole authority) and
    driving ``--resume`` to report ``0/N already done`` and re-emit duplicates.
    """
    events_file = merge_repo / "kitty-specs" / MISSION_SLUG / "status.events.jsonl"

    # -- Pre-target merge-state: no WP recorded as done yet (real product API). --
    state = MergeState(
        mission_id=MISSION_ID,
        mission_slug=MISSION_SLUG,
        target_branch="main",
        wp_order=["WP01"],
        completed_wps=[],
    )
    save_state(state, merge_repo)
    state_path = get_state_path(merge_repo, MISSION_ID)

    # -- Capture the pre-target rollback snapshot with the REAL product helper. --
    snapshots = _capture_bookkeeping_snapshots(merge_repo, events_file, state_path)

    # -- Merge records WP01 done and COMMITS it durably. The git commit stands in
    #    for emit_status_transition_transactional committing to the coordination
    #    branch: the done transition is now in the durable append-only log. --
    with events_file.open("a", encoding="utf-8") as handle:
        handle.write(_event("WP01", "approved", "done", "01REPRO2711DONE") + "\n")
    state.mark_wp_complete("WP01")
    save_state(state, merge_repo)
    _git(["add", "."], merge_repo)
    _git(["commit", "-m", "record WP01 done (pre-target bookkeeping)"], merge_repo)

    # -- Target advancement fails; executor rolls back with the REAL helper, which
    #    restores working-tree bytes only (it cannot revert the git commit). --
    _restore_final_bookkeeping_snapshots(snapshots)

    # Working tree + merge-state reverted (this half works).
    working_lanes = _parse_target_lanes_by_wp(
        events_file.read_text(encoding="utf-8")
    )
    reverted_state = load_state(merge_repo, MISSION_ID)
    assert reverted_state is not None
    assert working_lanes == {"WP01": "approved"}, (
        "precondition: rollback should revert the working-tree event log to approved"
    )
    assert reverted_state.completed_wps == [], (
        "precondition: rollback should revert merge-state to 0 completed WPs "
        "(this is what makes --resume report '0/N already done')"
    )

    # The durable committed ledger still says done — the split-brain.
    committed_text = subprocess.run(
        ["git", "show", f"HEAD:{_EVENTS_REL}"],
        cwd=merge_repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    committed_lanes = _parse_target_lanes_by_wp(committed_text)

    # #2711: after a rollback the committed event log and the reverted working
    # status/merge-state MUST be coherent. On current main the committed ledger
    # retains done while the working status reverted to approved (and merge-state
    # to 0/N) — an incoherent append-only ledger. FAILS until the product fix
    # rolls back (or never durably commits) the done events on a target-advance
    # rollback.
    assert committed_lanes == working_lanes, (
        "#2711 split-brain: committed event log "
        f"({committed_lanes}) opposes reverted working status ({working_lanes}); "
        f"merge-state reports {len(reverted_state.completed_wps)}/"
        f"{len(reverted_state.wp_order)} already done. The rollback left committed "
        "done events the working state reverted — the append-only ledger is corrupt."
    )
