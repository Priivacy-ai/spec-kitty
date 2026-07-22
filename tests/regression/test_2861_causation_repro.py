"""#2861 causation repro — the PERSISTED proof that the "commit refused" block is closed.

coord-commit-integrity WP01 / T001 (NFR-002, red-first). FLIPPED by WP04 / T015.

Purpose
-------
#2861 reported that a manually-orchestrated coord-topology review was blocked by
a "commit refused". Two hypotheses were in play at planning time:

* FR-002 — the coord-commit path (misroute / empty-commit) refuses the commit.
* FR-006 — the ``--agent tool:model:profile:role`` actor payload is rejected as
  an "invalid value" and that rejection is what blocks the flow.

This module drives the REAL ``agent action review`` CLI against a materialized
coord mission seeded to ``for_review`` via REAL status events (the sanctioned
``coord_repo_for_review`` shape). It first PERSISTED the observed causation as
assertions (WP01), then — once WP04 eliminated the empty-second-commit — was
FLIPPED to assert the review now SUCCEEDS. WP02's US2 AC-3 gate reads this proof,
so it must go RED if the block ever regresses, not stay a prose note.

CAUSATION (WP01 verdict, now RESOLVED by WP04)
----------------------------------------------
The block was **FR-002 (coord-commit path), NOT FR-006 (actor)**. Concretely:

* The compact actor ``claude:opus:reviewer-renata:reviewer`` was ACCEPTED — it
  was never the blocker. Any dict-actor validator warning is a non-fatal
  SaaS-fanout warn-and-skip (Decision B), so FR-006 was excluded.
* The refusal was raised on the MODERN coordination-transaction path: the
  transactional status emit already committed the ``for_review -> in_review``
  transition to the coord worktree, so the follow-up workflow commit found
  "nothing to commit, working tree clean" → ``safe_commit: git commit failed``
  → refused. This is the **empty second commit** (distinct from the
  ``SafeCommitHeadMismatch`` *misroute* sub-mode exercised in
  ``test_coord_commit_integrity_e2e.py``).

RESOLUTION (WP04 / T015, FR-004 — single status write-authority)
----------------------------------------------------------------
WP04 made the coordination transaction's ``commit()`` idempotent: when the
staged paths already match HEAD (the transactional emit already committed the
transition), the follow-up commit is a clean no-op pinned at that HEAD instead
of an empty commit ``safe_commit`` rejects. ONE write authority = ONE commit.
The manual review claim therefore SUCCEEDS and this test now asserts
``exit_code == 0`` — the headline proof that #2861's block is closed.
"""

from __future__ import annotations

import enum
import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli import app as root_app
from tests.characterization.test_trio_json_envelope import _build_mission_repo

runner = CliRunner()

_COMPACT_ACTOR = "claude:opus:reviewer-renata:reviewer"


def _materialize_lane_worktree(repo_root: Path, mission_dirname: str, wp_id: str) -> None:
    """Create the lane-a branch + worktree for ``wp_id``.

    The shared ``_build_mission_repo`` fixture deliberately never materializes a
    lane worktree, but a REAL ``agent action review`` runs against a mission
    whose implementation lane already exists — the post-commit auto-rebase-lane
    sync (``sync_lane_after_coordination_commit``) operates on it. Reproduce
    that reality here using the SAME canonical naming the sync itself uses so
    the success path completes end-to-end.
    """
    from specify_cli.lanes.branch_naming import lane_branch_name, worktree_path
    from specify_cli.lanes.persistence import read_lanes_json

    feature_dir = repo_root / "kitty-specs" / mission_dirname
    manifest = read_lanes_json(feature_dir)
    assert manifest is not None, "fixture must write lanes.json"
    lane = manifest.lane_for_wp(wp_id)
    assert lane is not None, f"{wp_id} must be lane-owned in the fixture manifest"

    coord_branch = json.loads((feature_dir / "meta.json").read_text(encoding="utf-8"))[
        "coordination_branch"
    ]
    lane_branch = lane_branch_name(
        mission_dirname,
        lane.lane_id,
        planning_base_branch=manifest.target_branch,
        mission_id=manifest.mission_id,
    )
    # The sync resolves the worktree DIR with mission_id=None (legacy grammar);
    # match it exactly so the created path is the one the sync will look for.
    lane_wt = worktree_path(repo_root, mission_dirname, mission_id=None, lane_id=lane.lane_id)

    subprocess.run(
        ["git", "-C", str(repo_root), "branch", lane_branch, coord_branch],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "-C", str(repo_root), "worktree", "add", str(lane_wt), lane_branch],
        check=True,
        capture_output=True,
        text=True,
    )


class Causation(enum.Enum):
    """The classified cause of the #2861 "commit refused" block."""

    COORD_COMMIT_PATH_REFUSED = "FR-002: coord-commit path refused the commit"
    ACTOR_REJECTED = "FR-006: actor payload rejected as invalid"
    NOT_BLOCKED = "no block observed"
    UNKNOWN = "unclassified"


def _classify(exit_code: int, output: str) -> Causation:
    if exit_code == 0:
        return Causation.NOT_BLOCKED
    lowered = output.lower()
    actor_rejected = "invalid" in lowered and "actor" in lowered and "[refused]" not in output
    commit_refused = "bookkeepingtransaction" in lowered or "safe_commit" in lowered
    if commit_refused and "[refused]" in output:
        return Causation.COORD_COMMIT_PATH_REFUSED
    if actor_rejected:
        return Causation.ACTOR_REJECTED
    return Causation.UNKNOWN


@pytest.mark.git_repo
def test_2861_block_is_closed_manual_coord_review_succeeds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """PROOF (WP04/T015): the #2861 empty-second-commit block is closed.

    The same sanctioned coord fixture that WP01 recorded as ``exit_code == 1``
    (empty-second-commit refusal) now SUCCEEDS: a single write authority commits
    the ``for_review -> in_review`` transition exactly once, the follow-up
    workflow commit is an idempotent no-op, and the manual review claim returns
    ``exit_code == 0``.
    """
    repo_root, mission_slug = _build_mission_repo(
        tmp_path,
        monkeypatch,
        coord=True,
        mission_slug="trio-coord-review",
        wp_lane="for_review",
        materialize_coord=True,
    )
    # A real review runs against an existing implementation lane; the fixture
    # omits it, so materialize lane-a for the post-commit auto-rebase sync.
    _materialize_lane_worktree(repo_root, mission_slug, "WP01")

    result = runner.invoke(
        root_app,
        [
            "agent",
            "action",
            "review",
            "WP01",
            "--mission",
            mission_slug,
            "--agent",
            _COMPACT_ACTOR,
        ],
    )
    output = result.output

    # HEADLINE PROOF: the manual coord-topology review claim now SUCCEEDS
    # (the empty-second-commit no longer refuses the write).
    assert result.exit_code == 0, output

    # The causation classifier agrees: no block is observed.
    verdict = _classify(result.exit_code, output)
    assert verdict is Causation.NOT_BLOCKED, (
        f"#2861 regressed: expected {Causation.NOT_BLOCKED} but classified "
        f"{verdict}.\n--- output ---\n{output}"
    )

    # The empty-second-commit refusal is GONE: neither the BookkeepingTransaction
    # refusal nor the "git commit failed" sub-mode may appear on the success path.
    assert "[refused]" not in output, output
    assert "git commit failed" not in output, output
    assert "SafeCommitHeadMismatch" not in output, output

    # The compact actor is still accepted (FR-006 was never the blocker) and the
    # review claim is confirmed in the output.
    assert _COMPACT_ACTOR in output, output
    assert "Claimed WP01 for review" in output, output
