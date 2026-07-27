"""Landing fold (#3012) — best-effort and recovery paths degrade on a DELETED coord branch.

PR #3012 routes mission reads through the kind-aware placement seam. COORD-partition
kinds (``STATUS_STATE``, ``LANE_STATE``) now fail loud with
:class:`~specify_cli.coordination.surface_resolver.CoordinationBranchDeleted` when the
declared ``coordination_branch`` is absent from git — a shape the old kind-blind
resolver could never raise. Three paths propagated that exception where they must not:

1. ``workflow_executor.review_compute_dependents_warning`` — explicitly best-effort
   (it only computes an advisory warning), but the seam call sat OUTSIDE the existing
   ``try/except``, so ``agent workflow review`` aborted while computing a warning.
2. ``lanes.recovery.scan_recovery_state`` — ``spec-kitty implement --recover`` is the
   operator's designated escape hatch, so it must REPORT the broken topology, not
   crash on it.
3. ``merge.executor._run_lane_based_merge`` — a traceback mid-merge is the worst UX in
   the set; it must exit cleanly with the remediation the exception already carries.

``CoordinationBranchDeleted`` subclasses ``StatusReadPathNotFound``, which subclasses
``Exception`` — so the pre-existing bare ``except Exception`` in (1) does catch it once
the raising call is moved inside the guard. (2) and (3) catch the specific type.

Each test drives the real DELETED shape through a real git repo (the canonical fixture
from ``tests/status/test_aggregate_coord_deleted_contract.py``: ``coordination_branch``
recorded in ``meta.json`` while the branch exists in NO local ref and NO remote, and no
coord worktree is materialized) and asserts the degrade/report/message behaviour rather
than a traceback.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
import typer

from specify_cli.frontmatter import write_frontmatter

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

# Production-shaped identity: a real 26-char ULID, mid8 = first 8 chars
# (Mission Identity Model 083+), matching the on-disk composed dir name.
_MISSION_ID = "01KW7COORDDELETED3012LAND0"[:26]
_MID8 = _MISSION_ID[:8]
_MISSION_SLUG = "coord-deleted-degrade-mission"
_SLUG_WITH_MID8 = f"{_MISSION_SLUG}-{_MID8}"
_COORD_BRANCH = f"kitty/mission-{_SLUG_WITH_MID8}"

# The remediation string the exception carries; every degrade path must propagate it
# rather than discard it.
_REMEDIATION = "spec-kitty doctor coordination --fix"


def _git(repo_root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _write_wp(tasks_dir: Path, wp_id: str, dependencies: list[str]) -> None:
    write_frontmatter(
        tasks_dir / f"{wp_id}-test.md",
        {
            "work_package_id": wp_id,
            "title": f"Test {wp_id}",
            "dependencies": dependencies,
            "subtasks": [],
            "phase": "Test Phase",
        },
        f"# Test WP: {wp_id}\n\nTest content.\n",
    )


def _build_coord_deleted_mission(repo_root: Path) -> Path:
    """Real git repo whose mission declares a coordination branch that does not exist.

    This is the narrow shape that actually reproduces the crash: the branch must be
    absent locally AND from every remote (``_coord_branch_exists`` consults
    ``refs/remotes/`` too), and no coord worktree may be registered. Normal post-merge
    state yields UNMATERIALIZED (→ PRIMARY) instead, which is why this fixture never
    creates the branch at all.
    """
    _git(repo_root, "init", "-q")
    _git(repo_root, "config", "user.email", "coord-deleted-3012@example.test")
    _git(repo_root, "config", "user.name", "Coord Deleted Degrade")

    feature_dir = repo_root / "kitty-specs" / _SLUG_WITH_MID8
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(
        json.dumps(
            {
                "mission_id": _MISSION_ID,
                "mission_slug": _MISSION_SLUG,
                "slug": _SLUG_WITH_MID8,
                "friendly_name": _MISSION_SLUG,
                "mission_type": "software-dev",
                "coordination_branch": _COORD_BRANCH,
                "topology": "coord",
            }
        ),
        encoding="utf-8",
    )
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    (feature_dir / "plan.md").write_text("# Plan\n", encoding="utf-8")

    # WP02 depends on WP01 so the dependents warning actually reaches the STATUS read
    # (the helper returns early when a WP has no dependents).
    _write_wp(tasks_dir, "WP01", [])
    _write_wp(tasks_dir, "WP02", ["WP01"])

    _git(repo_root, "add", "-A")
    _git(repo_root, "commit", "-qm", "init mission declaring a nonexistent coord branch")
    return feature_dir


def test_coord_branch_deleted_is_actually_raised_by_the_seam(tmp_path: Path) -> None:
    """Anchor: the fixture really produces the DELETED shape, and the type is catchable.

    Without this, the three degrade tests below could pass vacuously on a fixture that
    silently resolves to PRIMARY. It also pins the inheritance chain the best-effort
    handler in ``review_compute_dependents_warning`` relies on: catching ``Exception``
    is sufficient there ONLY because ``CoordinationBranchDeleted`` is an ``Exception``.
    """
    from mission_runtime import MissionArtifactKind, placement_seam
    from specify_cli.coordination.surface_resolver import CoordinationBranchDeleted
    from specify_cli.missions._read_path_resolver import StatusReadPathNotFound

    _build_coord_deleted_mission(tmp_path)

    assert issubclass(CoordinationBranchDeleted, StatusReadPathNotFound)
    assert issubclass(CoordinationBranchDeleted, Exception)

    seam = placement_seam(tmp_path, _SLUG_WITH_MID8)
    with pytest.raises(CoordinationBranchDeleted) as excinfo:
        seam.read_dir(MissionArtifactKind.STATUS_STATE)

    assert _REMEDIATION in excinfo.value.next_step


def test_dependents_warning_degrades_instead_of_aborting_review(tmp_path: Path) -> None:
    """FINDING 1: the best-effort warning helper must not abort on a warning computation.

    Red-first: with the ``read_dir(STATUS_STATE)`` call outside the existing
    ``try/except Exception``, this raises ``CoordinationBranchDeleted`` and
    ``agent workflow review`` dies. With the call moved inside the guard, lanes degrade
    to ``{}`` — every dependent is treated as ``planned`` — and the advisory warning is
    still produced.
    """
    from specify_cli.cli.commands.agent.workflow_executor import (
        review_compute_dependents_warning,
    )

    _build_coord_deleted_mission(tmp_path)

    warning = review_compute_dependents_warning(tmp_path, _SLUG_WITH_MID8, "WP01")

    assert warning, "the helper must still emit its advisory warning after degrading"
    assert any("WP02" in line for line in warning), (
        f"degraded lanes default dependents to planned, so WP02 must be flagged; got {warning}"
    )


def test_scan_recovery_state_reports_finding_instead_of_raising(tmp_path: Path) -> None:
    """FINDING 2: the recovery escape hatch must report the topology it exists to repair.

    Red-first: the unguarded ``read_dir(STATUS_STATE)`` in ``scan_recovery_state`` makes
    ``spec-kitty implement --recover`` traceback on a deleted coord branch. After the
    fix the scan completes and returns a synthetic finding carrying the exception's own
    ``doctor coordination --fix`` remediation.
    """
    from specify_cli.lanes.recovery import (
        COORD_BRANCH_DELETED_ACTION,
        COORD_FINDING_WP_ID,
        scan_recovery_state,
    )

    _build_coord_deleted_mission(tmp_path)

    states = scan_recovery_state(tmp_path, _SLUG_WITH_MID8)

    findings = [s for s in states if s.recovery_action == COORD_BRANCH_DELETED_ACTION]
    assert len(findings) == 1, f"expected exactly one coord-deleted finding, got {states}"
    finding = findings[0]
    assert finding.wp_id == COORD_FINDING_WP_ID
    assert finding.branch_name == _COORD_BRANCH
    assert _REMEDIATION in finding.resolution_note, (
        "the finding must propagate the exception's remediation, not discard it; "
        f"got {finding.resolution_note!r}"
    )


def test_run_recovery_surfaces_finding_without_treating_it_as_a_wp(tmp_path: Path) -> None:
    """FINDING 2 (caller leg): ``run_recovery`` reports the finding, repairs nothing.

    The synthetic finding has no worktree, context or status to reconcile, so it must
    NOT enter the repair loop or land in ``recovered_wps`` — but its remediation must
    reach the operator through ``report.errors``.
    """
    from specify_cli.lanes.recovery import COORD_FINDING_WP_ID, run_recovery

    _build_coord_deleted_mission(tmp_path)

    report = run_recovery(tmp_path, _SLUG_WITH_MID8)

    assert COORD_FINDING_WP_ID not in report.recovered_wps, (
        "a deleted coord branch is a finding, not a repaired WP"
    )
    assert any(_REMEDIATION in err for err in report.errors), (
        f"the recovery report must carry the remediation; got {report.errors}"
    )
    assert report.worktrees_recreated == 0
    assert report.contexts_recreated == 0


def test_lane_based_merge_exits_cleanly_instead_of_tracebacking(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """FINDING 3: ``spec-kitty merge`` must not traceback mid-run.

    Red-first: with no typed handler the ``read_dir(STATUS_STATE)`` call at the top of
    ``_run_lane_based_merge`` propagates ``CoordinationBranchDeleted`` straight out of
    the command. After the fix it becomes a rendered error plus ``typer.Exit(1)``,
    matching the handler shape already used in ``agent/status.py`` and
    ``mission_finalize.py``. The failure happens before any state change.
    """
    from specify_cli.merge.executor import _run_lane_based_merge

    _build_coord_deleted_mission(tmp_path)

    with pytest.raises(typer.Exit) as excinfo:
        _run_lane_based_merge(
            repo_root=tmp_path,
            mission_slug=_SLUG_WITH_MID8,
            push=False,
            delete_branch=False,
            remove_worktree=False,
        )

    assert excinfo.value.exit_code == 1
    # Rich hard-wraps console output at the terminal width, so collapse whitespace
    # before matching — the assertion is about content, not line breaks.
    output = " ".join(capsys.readouterr().out.split())
    assert _COORD_BRANCH in output, f"the error must name the missing branch; got: {output!r}"
    assert "doctor coordination --fix" in output, (
        f"the error must carry the remediation guidance; got: {output!r}"
    )
    assert "Merge aborted before any state change" in output, (
        f"the operator must be told the merge is a clean no-op; got: {output!r}"
    )
