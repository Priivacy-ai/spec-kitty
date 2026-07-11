"""Regression test for #2508 (coord-authority-trio-degod-01KX7094, WP02/T006).

``_load_coord_branch_meta`` (``workflow.py:276``) reads ``meta.json`` off
whatever ``feature_dir`` its caller passes it. ``_commit_workflow_change``
(``workflow.py:571``) passes it the SEAM-resolved, topology-aware
``feature_dir`` -- which for a coord-topology mission is the COORD
WORKTREE, not the primary checkout (``_canonical_status_feature_dir`` ->
``resolve_handle_to_read_path``, a STATUS-partition read). ``meta.json`` is
``PRIMARY_METADATA`` -- a PRIMARY-partition kind (see
``worktree_allocator._read_coordination_branch`` and the dozen other
``MissionArtifactKind.PRIMARY_METADATA`` call sites in the codebase) -- so
when the coord worktree's checked-out copy of ``meta.json`` is stale,
missing, or was materialized before ``coordination_branch`` was known
locally, ``_load_coord_branch_meta`` silently returns ``(None, None,
None)`` and ``_commit_workflow_change`` takes the LEGACY ``safe_commit``
fallback -- even though the mission genuinely has a coordination branch.

This is a concrete instance of the #2160 artifact-authority split-brain
class: an identity read anchored on the wrong partition.

**Observed misfire** (confirmed empirically against pre-fix code before
writing this assertion): the legacy fallback calls ``_commit_via_legacy_
safe_commit(..., worktree_root=repo_root)`` — i.e. it tries to run
``safe_commit`` from the PRIMARY checkout's working tree, whose ``HEAD`` is
the mission's ``target_branch``, NOT the coordination branch the resolved
``CommitTarget`` demands. ``safe_commit`` refuses ("worktree HEAD is
'<target_branch>', expected '<coord_branch>'"), the claim commit is
refused, and the WP01 claim silently rolls back its status-event log
while reporting a "[refused]" commit receipt to the operator -- through
the REAL ``agent action implement`` command entry point, not a synthetic
unit call into ``_commit_workflow_change``.

Ownership note (DIRECTIVE_024 leeway, no-overlap guard): WP02's
``owned_files`` lists ``tests/specify_cli/cli/commands/agent/
test_workflow_cores.py`` for pure-core unit tests. This is a full
CLI-entry-point regression repro (git subprocess + CliRunner over the real
Typer app), which belongs with the project's other numbered-issue
regression repros (``tests/regression/test_issue_1348.py``). No other WP
in this mission owns ``tests/regression/`` (confirmed via the mission's
``tasks/WP0{1,3,4,5}-*.md`` ownership maps) -- there is no overlap.

Marker: integration + git_repo (CliRunner over a real git repository, one
real ``git worktree add`` for the coordination worktree).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli import app as root_app
from specify_cli.analysis_report import write_analysis_report
from tests.lane_test_utils import derive_mission_id, write_single_lane_manifest
from tests.specify_cli.charter_preflight._fixtures import (
    seed_bundle_files,
    seed_charter,
    seed_graph,
    seed_manifest,
    write_metadata,
)
from tests.utils import write_wp

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

runner = CliRunner()

MISSION_SLUG = "issue-2508-repro"


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=str(cwd), check=True, capture_output=True, text=True)


def _build_coord_mission_with_drifted_husk(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, str, str, str]:
    """Build a coord-topology mission whose MATERIALIZED coord worktree's
    ``meta.json`` does not carry the mission identity triple.

    Returns ``(repo_root, mission_dirname, coord_branch, target_branch)``.

    Mirrors ``tests/characterization/test_trio_json_envelope.py``'s
    ``_build_mission_repo(coord=True, materialize_coord=True)`` fixture
    (same charter-preflight scaffolding, same VERBATIM coord-branch
    grammar), with one deliberate deviation: after the coordination
    worktree is materialized, its checked-out ``meta.json`` is removed --
    modelling the real drift where a coord worktree's identity-metadata
    snapshot is stale/absent relative to the PRIMARY checkout (the
    ``PRIMARY_METADATA`` partition, per ``worktree_allocator.
    _read_coordination_branch``'s "the coord husk has none / a STATUS-only
    one" comment). The PRIMARY checkout's own ``meta.json`` is untouched.
    """
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _git(repo_root, "init", "-q", "-b", "main")
    _git(repo_root, "config", "user.email", "issue-2508@example.invalid")
    _git(repo_root, "config", "user.name", "Issue 2508 Regression")
    _git(repo_root, "config", "commit.gpgsign", "false")
    (repo_root / ".kittify").mkdir()
    (repo_root / "README.md").write_text("seed\n", encoding="utf-8")

    charter_path, metadata_path = seed_charter(repo_root)
    write_metadata(metadata_path, charter_path)
    seed_bundle_files(repo_root)
    seed_manifest(repo_root, built_in_only=False)
    seed_graph(repo_root)

    _git(repo_root, "add", "-A")
    _git(repo_root, "commit", "-q", "-m", "seed")

    # ``main`` is protected; missions run on a dedicated target branch.
    target_branch = "trio-integration"
    _git(repo_root, "checkout", "-q", "-b", target_branch)

    for path_dir in ("src", "tests", "docs"):
        (repo_root / path_dir).mkdir(exist_ok=True)

    mission_id = derive_mission_id(MISSION_SLUG)
    mid8 = mission_id[:8]
    mission_dirname = f"{MISSION_SLUG}-{mid8}"

    feature_dir = repo_root / "kitty-specs" / mission_dirname
    feature_dir.mkdir(parents=True)
    (feature_dir / "contracts").mkdir(exist_ok=True)
    (feature_dir / "spec.md").write_text("# Spec\n\nFR-001: Demo spec for #2508 regression.\n", encoding="utf-8")
    (feature_dir / "plan.md").write_text("# Plan\n", encoding="utf-8")
    (feature_dir / "tasks.md").write_text("## WP01\n\n- [x] T001 Placeholder task\n", encoding="utf-8")
    (feature_dir / "quickstart.md").write_text("# Quickstart\n", encoding="utf-8")
    (feature_dir / "data-model.md").write_text("# Data model\n", encoding="utf-8")
    (feature_dir / "research.md").write_text("# Research\n", encoding="utf-8")

    coord_branch = f"kitty/mission-{MISSION_SLUG}-{mid8}"
    meta: dict[str, object] = {
        "mission_id": mission_id,
        "mid8": mid8,
        "mission_slug": MISSION_SLUG,
        "slug": MISSION_SLUG,
        "mission_type": "software-dev",
        "target_branch": target_branch,
        "friendly_name": "Issue #2508 regression fixture",
        "created_at": "2026-01-01T00:00:00+00:00",
        "coordination_branch": coord_branch,
    }
    (feature_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    write_single_lane_manifest(
        feature_dir, wp_ids=("WP01",), target_branch=target_branch, mission_id=mission_id,
    )
    write_wp(repo_root, mission_dirname, "planned", "WP01")

    from specify_cli.acceptance.matrix import AcceptanceCriterion, AcceptanceMatrix, write_acceptance_matrix

    write_acceptance_matrix(
        feature_dir,
        AcceptanceMatrix(
            mission_slug=MISSION_SLUG,
            criteria=[
                AcceptanceCriterion(
                    criterion_id="AC-01",
                    description="Issue #2508 regression fixture is self-consistent",
                    proof_type="automated_test",
                    pass_fail="pass",
                )
            ],
        ),
    )

    write_analysis_report(
        feature_dir=feature_dir,
        repo_root=repo_root,
        body="# Analysis\n\nCritical Issues Count: 0\nHigh Issues Count: 0\nPASS\n",
        analyzer_agent="test",
    )

    _git(repo_root, "add", "-A")
    _git(repo_root, "commit", "-q", "-m", "seed mission scaffold")

    # Branch the coord ref from the fully-populated mission commit -- real
    # missions branch coord off the seeded scaffold too.
    _git(repo_root, "branch", coord_branch)

    from specify_cli.coordination.workspace import CoordinationWorkspace

    coord_worktree_root = CoordinationWorkspace.resolve(repo_root, mission_dirname, mid8)
    coord_meta_path = coord_worktree_root / "kitty-specs" / mission_dirname / "meta.json"
    assert coord_meta_path.exists(), "sanity: coord worktree checkout should carry the branched-in meta.json"

    # The drift under test: the coord worktree's own meta.json copy does
    # not carry the identity triple (stale / never-synced husk). The
    # PRIMARY checkout's meta.json (asserted below) is untouched.
    coord_meta_path.unlink()

    primary_meta_path = feature_dir / "meta.json"
    assert primary_meta_path.exists()
    primary_meta = json.loads(primary_meta_path.read_text(encoding="utf-8"))
    assert primary_meta.get("coordination_branch") == coord_branch

    monkeypatch.setenv("SPECIFY_REPO_ROOT", str(repo_root))
    monkeypatch.chdir(repo_root)
    return repo_root, mission_dirname, coord_branch, target_branch


class TestIssue2508IdentityReadAnchorsOnPrimary:
    """The identity-meta read (``coordination_branch``/``mission_id``/
    ``mid8``) that decides whether ``_commit_workflow_change`` routes
    through ``BookkeepingTransaction`` must anchor on the PRIMARY checkout,
    never on a coord worktree's possibly-drifted ``meta.json`` snapshot."""

    def test_claim_succeeds_through_coordination_transaction_despite_drifted_coord_husk(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        repo_root, mission_dirname, coord_branch, target_branch = _build_coord_mission_with_drifted_husk(
            tmp_path, monkeypatch,
        )

        # Sanity: the primary checkout's own HEAD is on target_branch, not
        # the coordination branch -- exactly the state that lets the
        # legacy fallback's worktree-HEAD mismatch manifest.
        head = subprocess.run(
            ["git", "-C", str(repo_root), "symbolic-ref", "--short", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        assert head == target_branch

        result = runner.invoke(
            root_app,
            ["agent", "action", "implement", "WP01", "--mission", mission_dirname, "--agent", "claude"],
        )

        # THE FIX: the claim commit must succeed via the coordination
        # transaction -- not misfire into the legacy safe_commit fallback,
        # which tries (and, pre-fix, fails) to commit from the PRIMARY
        # worktree while targeting the coordination branch.
        assert result.exit_code == 0, result.output
        assert "Failed to commit workflow status update" not in result.output
        assert "[refused]" not in result.output
        assert "✓ Claimed WP01" in result.output

        # The claim commit must land on the coordination branch (via
        # BookkeepingTransaction), and the primary checkout's target
        # branch must be untouched by this write.
        coord_log = subprocess.run(
            ["git", "-C", str(repo_root), "log", "--oneline", coord_branch],
            capture_output=True, text=True, check=True,
        ).stdout
        assert "Start WP01 implementation" in coord_log

        target_log = subprocess.run(
            ["git", "-C", str(repo_root), "log", "--oneline", target_branch],
            capture_output=True, text=True, check=True,
        ).stdout
        assert "Start WP01 implementation" not in target_log
