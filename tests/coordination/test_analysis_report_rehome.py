"""FR-003 re-home proof: ANALYSIS_REPORT is PRIMARY, with no coord copy.

coord-commit-integrity WP03 / T011. Two layers of proof:

1. **Classifier + partition (unit)** — the PUBLIC file→kind classifier still maps
   ``analysis-report.md`` to ``ANALYSIS_REPORT`` (the ``_COORD_RESIDUE_FILENAMES``
   entry was KEPT), AND ``ANALYSIS_REPORT`` is now a PRIMARY-partition kind. The
   pair catches BOTH failure modes the re-home could introduce: deleting the
   classifier entry (→ ``None`` → mis-route) and failing to move the kind
   (→ still COORD). ``assert_partition_invariant`` stays green (disjoint-and-total).

2. **Committed-ref proof (real git, NON-fakeable)** — on a real coord-topology
   fixture (real ``git init`` + real ``git worktree add`` via the production
   ``CoordinationWorkspace.resolve``), the REAL ``commit_for_mission`` (no stubbed
   ``safe_commit`` — NFR-001) commits the report and ``git show`` proves it exists
   on the PRIMARY ref and is ABSENT on the coordination ref. This is a
   committed-tree proof, not a config/frozenset assertion.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from mission_runtime import (
    MissionArtifactKind,
    is_primary_artifact_kind,
    kind_for_mission_file,
)
from mission_runtime.artifacts import assert_partition_invariant
from specify_cli.coordination.coherence import is_coord_residue_churn

from tests.integration.coord_topology_fixture import _build_coord_topology

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

_ANALYSIS_REPORT = "analysis-report.md"


def test_kind_for_mission_file_classifies_analysis_report_specifically() -> None:
    """The PUBLIC classifier maps ``analysis-report.md`` to ``ANALYSIS_REPORT``.

    References the public ``kind_for_mission_file`` classifier (NOT the private
    ``_COORD_RESIDUE_FILENAMES`` symbol, so it survives the optional rename), and
    asserts the SPECIFIC kind — not merely non-``None`` — so a classifier-entry
    deletion (which would return ``None`` and mis-route via the unrecognized-path
    fallback) fails LOUDLY here.
    """
    kind = kind_for_mission_file(
        f"kitty-specs/demo-01ABCDEF/{_ANALYSIS_REPORT}", mission_slug="demo-01ABCDEF"
    )
    assert kind is MissionArtifactKind.ANALYSIS_REPORT


def test_analysis_report_is_primary_partition_and_not_coord_residue() -> None:
    """``ANALYSIS_REPORT`` is a PRIMARY kind; its stale primary copy is not residue.

    The second half of the classifier/mis-move pair: the kind moved to the PRIMARY
    partition (``is_primary_artifact_kind`` True) and, consequently, a stale primary
    ``analysis-report.md`` is REAL dirt, NOT coordination residue. The partition
    stays disjoint-and-total.
    """
    assert is_primary_artifact_kind(MissionArtifactKind.ANALYSIS_REPORT)
    assert not is_coord_residue_churn(
        f"kitty-specs/demo-01ABCDEF/{_ANALYSIS_REPORT}", mission_slug="demo-01ABCDEF"
    )
    # A still-COORD kind remains residue — proves the re-home was narrow.
    assert is_coord_residue_churn(
        "kitty-specs/demo-01ABCDEF/acceptance-matrix.json", mission_slug="demo-01ABCDEF"
    )
    assert_partition_invariant()


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
    )


def _disable_branch_protection(repo: Path) -> None:
    """Commit an empty ``protected_branches`` so the primary commit can land.

    ``main`` is protected by default; a PRIMARY-kind commit onto a protected ref is
    refused. This is the ONLY config touch — the actual re-home proof is on the
    committed git trees below (``git show``), not this config.
    """
    config = repo / ".kittify" / "config.yaml"
    config.write_text("protection:\n  protected_branches: []\n", encoding="utf-8")
    assert _git(repo, "add", ".kittify/config.yaml").returncode == 0
    assert _git(repo, "commit", "-m", "test: unprotect main for re-home proof").returncode == 0


def test_analysis_report_commits_to_primary_ref_and_is_absent_on_coord(
    tmp_path: Path,
) -> None:
    """Committed-ref proof: the re-homed report lands on PRIMARY, absent on COORD.

    Drives the REAL ``commit_for_mission`` (real ``safe_commit``) on a real
    coord-topology fixture, then proves via committed trees:

    * ``git show <primary_ref>:kitty-specs/<slug>/analysis-report.md`` SUCCEEDS, and
    * ``git show <coord_ref>:kitty-specs/<slug>/analysis-report.md`` FAILS (absent) —

    i.e. NO second (coord) copy is made. Config-only assertions do not satisfy the
    contract; this reads the artifact out of the committed git trees.
    """
    from specify_cli.coordination.commit_router import commit_for_mission
    from specify_cli.git.protection_policy import ProtectionPolicy

    ctx = _build_coord_topology(tmp_path, write_husk_meta=False)
    _disable_branch_protection(ctx.repo)

    report = ctx.primary_feature_dir / _ANALYSIS_REPORT
    report.write_text("# Analysis\n\nNo blocking findings.\n", encoding="utf-8")

    result = commit_for_mission(
        repo_root=ctx.repo,
        mission_slug=ctx.slug,
        files=(report,),
        message=f"Add analysis report for mission {ctx.slug}",
        policy=ProtectionPolicy.resolve(ctx.repo),
        kind=MissionArtifactKind.ANALYSIS_REPORT,
        target_branch="main",
    )

    # The re-homed PRIMARY kind commits to the primary target branch, never coord.
    assert result.status == "committed", result
    assert result.placement_ref == "main", result

    rel = f"kitty-specs/{ctx.slug}/{_ANALYSIS_REPORT}"
    primary_show = _git(ctx.repo, "show", f"main:{rel}")
    assert primary_show.returncode == 0, (
        f"analysis-report.md is NOT on the primary ref 'main': {primary_show.stderr}"
    )
    assert "No blocking findings." in primary_show.stdout

    coord_show = _git(ctx.repo, "show", f"{ctx.coord_branch}:{rel}")
    assert coord_show.returncode != 0, (
        "analysis-report.md WAS committed to the coordination ref "
        f"{ctx.coord_branch!r} — a coord copy was made (re-home failed):\n"
        f"{coord_show.stdout}"
    )


def test_review_cycle_authored_lands_on_primary_ref_and_is_absent_on_coord(
    tmp_path: Path,
) -> None:
    """FR-001 committed-ref proof: an authored review-cycle lands PRIMARY, absent COORD.

    T009 / DoD line 141 (moved from WP01, renata). ``review-cycle-N.md`` is a
    ``WORK_PACKAGE_TASK`` artifact (PRIMARY partition), but the pre-fix write site
    resolved the mission dir via the kind-blind
    ``candidate_feature_dir_for_mission`` fold → the COORD husk under coord
    topology. The fix unifies read+write on ``_review_cycle_wp_dir`` (the kind-aware
    PRIMARY resolver). This drives the REAL write site
    (:func:`create_rejected_review_cycle`) on a real coord-topology git fixture and
    proves via COMMITTED TREES:

    * ``git show <primary_ref>:kitty-specs/<slug>/tasks/<wp>/review-cycle-1.md``
      SUCCEEDS, and
    * ``git show <coord_ref>:.../review-cycle-1.md`` FAILS (absent) —

    i.e. the review-cycle is authored into its PRIMARY home, never the coord husk.
    The commit uses the REAL router (``commit_for_mission`` with the PRIMARY
    ``WORK_PACKAGE_TASK`` kind — no stubbed ``safe_commit``, NFR-001). RED against
    the pre-fix coord-husk write (``git show <primary_ref>`` fails because the
    artifact was authored under ``.worktrees/<slug>-coord/``), GREEN after — the
    direction is pinned by the committed primary ref, not by "green".
    """
    from specify_cli.coordination.commit_router import commit_for_mission
    from specify_cli.git.protection_policy import ProtectionPolicy
    from specify_cli.review.cycle import create_rejected_review_cycle

    ctx = _build_coord_topology(tmp_path, write_husk_meta=False)
    _disable_branch_protection(ctx.repo)

    feedback = tmp_path / "review-feedback.md"
    feedback.write_text(
        "Reviewer feedback: WP01 needs the missing regression test before approval.\n",
        encoding="utf-8",
    )

    # Author the review-cycle through the REAL write site. Its placement decision
    # lives in ``_review_cycle_wp_dir`` (kind-aware, PRIMARY) — the fix under test.
    created = create_rejected_review_cycle(
        main_repo_root=ctx.repo,
        mission_slug=ctx.slug,
        wp_id="WP01",
        wp_slug="WP01",
        feedback_source=feedback,
        reviewer_agent="reviewer-renata",
    )

    # Post-fix, the artifact is authored under the PRIMARY tasks home, not the husk.
    rel = str(created.artifact_path.relative_to(ctx.repo))
    assert rel == f"kitty-specs/{ctx.slug}/tasks/WP01/review-cycle-1.md", rel

    # Commit through the REAL router as a PRIMARY WORK_PACKAGE_TASK kind.
    result = commit_for_mission(
        repo_root=ctx.repo,
        mission_slug=ctx.slug,
        files=(created.artifact_path,),
        message=f"Add review-cycle-1 for {ctx.slug} WP01",
        policy=ProtectionPolicy.resolve(ctx.repo),
        kind=MissionArtifactKind.WORK_PACKAGE_TASK,
        target_branch="main",
    )
    assert result.status == "committed", result
    assert result.placement_ref == "main", result

    primary_show = _git(ctx.repo, "show", f"main:{rel}")
    assert primary_show.returncode == 0, (
        f"review-cycle-1.md is NOT on the primary ref 'main': {primary_show.stderr}"
    )
    assert "Reviewer feedback:" in primary_show.stdout

    coord_rel = f"kitty-specs/{ctx.slug}/tasks/WP01/review-cycle-1.md"
    coord_show = _git(ctx.repo, "show", f"{ctx.coord_branch}:{coord_rel}")
    assert coord_show.returncode != 0, (
        "review-cycle-1.md WAS committed to the coordination ref "
        f"{ctx.coord_branch!r} — a coord husk copy was authored (write-in-home failed):\n"
        f"{coord_show.stdout}"
    )
