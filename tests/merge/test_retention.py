"""Tests for mission retention-contract enforcement."""

from __future__ import annotations

from pathlib import Path

from specify_cli.merge.retention import (
    MissionRetention,
    load_mission_retention,
    retention_cleanup_conflicts,
)
from tests.reliability.fixtures import create_mission_fixture
from tests.reliability.fixtures.mission import MissionFixture


def _write_spec(tmp_path: Path, constraint: str, status: str) -> MissionFixture:
    mission = create_mission_fixture(tmp_path)
    (mission.mission_dir / "spec.md").write_text(
        "\n".join(
            [
                "# Mission",
                "",
                "## Constraints",
                "",
                "| ID | Title | Constraint | Category | Priority | Status |",
                "|----|-------|------------|----------|----------|--------|",
                f"| C-005 | Retention | {constraint} | Operational | High | {status} |",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return mission


def test_load_mission_retention_reads_only_accepted_constraints(
    tmp_path: Path,
) -> None:
    mission = _write_spec(
        tmp_path,
        "Keep branches and worktrees after merge unless separately directed.",
        "Open",
    )
    assert load_mission_retention(mission.repo_root, mission.mission_slug) is None


def test_load_mission_retention_ignores_negated_retention(
    tmp_path: Path,
) -> None:
    mission = _write_spec(
        tmp_path,
        "Do not keep branches and worktrees after merge.",
        "Accepted",
    )
    assert load_mission_retention(mission.repo_root, mission.mission_slug) is None


def test_retention_cleanup_conflicts_requires_each_explicit_choice() -> None:
    retention = MissionRetention(
        constraint_id="C-005",
        constraint="Keep branches and worktrees after merge.",
    )
    assert (
        retention_cleanup_conflicts(
            None,
            delete_branch=None,
            remove_worktree=None,
        )
        == ()
    )
    assert retention_cleanup_conflicts(
        retention,
        delete_branch=None,
        remove_worktree=None,
    ) == ("branch", "worktree")
    assert retention_cleanup_conflicts(
        retention,
        delete_branch=True,
        remove_worktree=None,
    ) == ("worktree",)
    assert (
        retention_cleanup_conflicts(
            retention,
            delete_branch=False,
            remove_worktree=True,
        )
        == ()
    )
