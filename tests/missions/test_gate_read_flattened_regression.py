"""WP10 / NFR-001: flattened/single-branch mission regression — behavior neutral.

The gate-read-surface mission re-partitioned planning reads onto the PRIMARY
surface for coord-topology missions. For a FLATTENED mission (no coordination
branch) there is no primary↔coord split: BOTH partitions must resolve the single
``target_branch`` feature dir — IDENTICAL to pre-mission behavior. This module
pins that neutrality across every gate-command read kind so the coord-topology
fix cannot silently change the flattened path.

Both the PRIMARY-partition reads (spec / tasks / WP-task / lane-state) and the
STATUS-partition reads (status-state / acceptance-matrix / analysis-report)
resolve the same flattened feature dir, and the real entry points
(``collect_feature_summary``, the write twin) behave as before. Identity is
production-shaped (26-char ULID, composed ``<slug>-<mid8>`` on-disk dir).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from mission_runtime import (
    MissionArtifactKind,
    resolve_placement_only,
)
from specify_cli.acceptance import collect_feature_summary
from specify_cli.core.git_ops import resolve_target_branch
from specify_cli.core.paths import get_feature_target_branch
from specify_cli.missions._read_path_resolver import (
    primary_feature_dir_for_mission,
    resolve_planning_read_dir,
)

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

# Production-shaped identity, composed on-disk layout. No coordination branch.
_MISSION_ID = "01KVW9B0XFXPKTBE77QT3KRSW8"  # 26 chars
_MID8 = _MISSION_ID[:8]  # "01KVW9B0"
_SLUG = "gate-read-surface-completion"
_HANDLE = f"{_SLUG}-{_MID8}"
_TARGET = "feat/gate-read-surface-completion"

_PLANNING_FILES = ("spec.md", "plan.md", "tasks.md", "research.md", "data-model.md")

# Every gate-command read kind — both partitions. On a FLATTENED mission they ALL
# resolve the single ``target_branch`` feature dir (NFR-001).
_ALL_READ_KINDS: dict[str, MissionArtifactKind] = {
    "setup_plan(spec)": MissionArtifactKind.SPEC,
    "accept(tasks)": MissionArtifactKind.TASKS_INDEX,
    "map_requirements(wp_task)": MissionArtifactKind.WORK_PACKAGE_TASK,
    "finalize_tasks(lane_state)": MissionArtifactKind.LANE_STATE,
    "accept(status_state)": MissionArtifactKind.STATUS_STATE,
    "accept(acceptance_matrix)": MissionArtifactKind.ACCEPTANCE_MATRIX,
    "record_analysis(analysis_report)": MissionArtifactKind.ANALYSIS_REPORT,
}

_STATUS_EVENT = {
    "actor": "claude",
    "at": "2026-06-24T12:00:00+00:00",
    "event_id": "01KVW9B0XFXPKTBE77QT3KRSWZ",
    "evidence": None,
    "execution_mode": "worktree",
    "feature_slug": _HANDLE,
    "force": False,
    "from_lane": "genesis",
    "reason": None,
    "review_ref": None,
    "to_lane": "planned",
    "wp_id": "WP01",
}


def _git(repo_root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo_root, check=True, capture_output=True)


@pytest.fixture
def flattened_mission(tmp_path: Path) -> tuple[Path, Path]:
    """A flattened/single-branch mission (NO coordination branch).

    Returns ``(repo_root, feature_dir)``. Both planning docs and the status event
    log live on the single feature dir; ``meta.json`` carries ``target_branch`` but
    NO ``coordination_branch`` — the topology is flattened.
    """
    repo_root = tmp_path
    _git(repo_root, "init", "-q")
    _git(repo_root, "config", "user.email", "t@example.invalid")
    _git(repo_root, "config", "user.name", "Test")
    _git(repo_root, "config", "commit.gpgsign", "false")

    feature_dir = repo_root / "kitty-specs" / _HANDLE
    feature_dir.mkdir(parents=True)
    meta: dict[str, object] = {
        "mission_id": _MISSION_ID,
        "mid8": _MID8,
        "mission_slug": _HANDLE,
        "mission_type": "software-dev",
        "target_branch": _TARGET,
        # No coordination_branch → flattened topology.
    }
    (feature_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    for name in _PLANNING_FILES:
        (feature_dir / name).write_text(f"# {name}\n\nContent.\n", encoding="utf-8")
    (feature_dir / "status.events.jsonl").write_text(
        json.dumps(_STATUS_EVENT) + "\n", encoding="utf-8"
    )
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (tasks_dir / "WP01-sample.md").write_text(
        "---\nwork_package_id: WP01\ntitle: Sample\nagent: claude\n"
        "assignee: claude\nshell_pid: '1'\n---\n\n# WP01\n",
        encoding="utf-8",
    )

    _git(repo_root, "add", "-A")
    _git(repo_root, "commit", "-q", "-m", "seed flattened mission")
    return repo_root, feature_dir


def test_all_reads_resolve_target_branch_dir(
    flattened_mission: tuple[Path, Path],
) -> None:
    """NFR-001: every gate-command read kind resolves the single feature dir.

    Both PRIMARY and STATUS partitions collapse to the same flattened
    ``target_branch`` dir — identical to pre-mission behavior (no split).
    """
    repo_root, feature_dir = flattened_mission

    for label, kind in _ALL_READ_KINDS.items():
        resolved = resolve_planning_read_dir(repo_root, _HANDLE, kind=kind).resolve()
        assert resolved == feature_dir.resolve(), (
            f"{label}: flattened read resolved {resolved} — expected the single "
            f"feature dir {feature_dir} (NFR-001 behavior neutrality)."
        )


def test_primary_anchor_is_the_flattened_dir(
    flattened_mission: tuple[Path, Path],
) -> None:
    """The primary anchor for a flattened mission IS the single feature dir."""
    repo_root, feature_dir = flattened_mission
    assert (
        primary_feature_dir_for_mission(repo_root, _HANDLE).resolve()
        == feature_dir.resolve()
    )


def test_accept_gate_passes_on_flattened_mission(
    flattened_mission: tuple[Path, Path],
) -> None:
    """Accept gate finds planning docs AND status on the single flattened surface."""
    repo_root, _feature_dir = flattened_mission

    summary = collect_feature_summary(
        repo_root, _HANDLE, strict_metadata=False, mutate_matrix=False
    )

    assert summary.missing_artifacts == [], (
        "Flattened accept gate mis-blocked planning artifacts (NFR-001 regression)."
    )
    assert not [
        issue for issue in summary.activity_issues if "No canonical state found" in issue
    ], "Flattened accept gate lost the status event log (NFR-001 regression)."


def test_write_twin_resolves_target_branch_on_flattened(
    flattened_mission: tuple[Path, Path],
) -> None:
    """Write twin resolves ``target_branch`` on a flattened mission (NFR-001)."""
    repo_root, _feature_dir = flattened_mission

    assert get_feature_target_branch(repo_root, _HANDLE) == _TARGET
    resolution = resolve_target_branch(
        _HANDLE, repo_root, current_branch="feat/other", respect_current=True
    )
    assert resolution.target == _TARGET
    placement = resolve_placement_only(
        repo_root, _HANDLE, kind=MissionArtifactKind.TASKS_INDEX
    )
    assert placement.ref == _TARGET
