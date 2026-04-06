"""Tests for WP04: workflow.py canonical status cleanup.

Verifies:
- implement body note does NOT contain lane=
- review body note does NOT contain lane=
- implement hard-fails when no canonical state for WP
- review hard-fails when no canonical state for WP
- implement succeeds when canonical state exists
- review succeeds when canonical state exists
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.lane_test_utils import lane_worktree_path, write_single_lane_manifest

from specify_cli.cli.commands.agent import workflow
from specify_cli.frontmatter import write_frontmatter
from specify_cli.status.models import StatusEvent, Lane
from specify_cli.status.store import append_event
from specify_cli.tasks_support import split_frontmatter

pytestmark = pytest.mark.fast


def _seed_wp_lane(feature_dir: Path, wp_id: str, lane: str) -> None:
    """Seed a WP into a specific lane in the event log."""
    _lane_alias = {"doing": "in_progress"}
    canonical_lane = _lane_alias.get(lane, lane)
    event = StatusEvent(
        event_id=f"test-{wp_id}-{canonical_lane}",
        mission_slug=feature_dir.name,
        wp_id=wp_id,
        from_lane=Lane.PLANNED,
        to_lane=Lane(canonical_lane),
        at="2026-01-01T00:00:00+00:00",
        actor="test",
        force=True,
        execution_mode="worktree",
    )
    append_event(feature_dir, event)


def _write_wp_file(path: Path, wp_id: str, lane: str) -> None:
    frontmatter = {
        "work_package_id": wp_id,
        "subtasks": ["T001"],
        "title": f"{wp_id} Test",
        "phase": "Phase 0",
        "lane": lane,
        "assignee": "",
        "agent": "",
        "shell_pid": "",
        "review_status": "",
        "reviewed_by": "",
        "dependencies": [],
        "history": [
            {
                "timestamp": "2026-01-01T00:00:00Z",
                "lane": lane,
                "agent": "system",
                "shell_pid": "",
                "action": "Prompt created",
            }
        ],
    }
    body = f"# {wp_id} Prompt\n\n## Activity Log\n- 2026-01-01T00:00:00Z - system - Prompt created.\n"
    write_frontmatter(path, frontmatter, body)


@pytest.fixture()
def workflow_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    repo_root = tmp_path
    (repo_root / ".kittify").mkdir()
    (repo_root / ".kittify" / "config.yaml").write_text(
        "vcs:\n  type: git\nproject:\n  uuid: test-project-uuid\n  slug: test-project\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("SPECIFY_REPO_ROOT", str(repo_root))
    monkeypatch.chdir(repo_root)
    monkeypatch.setattr(
        "specify_cli.cli.commands.agent.workflow._ensure_target_branch_checked_out",
        lambda repo_root, mission_slug: (repo_root, "main"),
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.agent.workflow.safe_commit",
        lambda **kwargs: True,
    )
    return repo_root


# ---------------------------------------------------------------------------
# T011: implement body note does NOT contain lane=
# ---------------------------------------------------------------------------

class TestImplementBodyNoteLaneFree:
    """Implement history entries must not contain lane= segments."""

    def test_implement_body_note_no_lane_from_planned(self, workflow_repo: Path) -> None:
        """When implementing from planned, body note should not contain lane=."""
        mission_slug = "060-test-feature"
        feature_dir = workflow_repo / "kitty-specs" / mission_slug
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        write_single_lane_manifest(feature_dir, wp_ids=("WP01",), predicted_surfaces=("workflow",))
        (feature_dir / "tasks.md").write_text(
            "## WP01 Test\n\n- [x] T001 Placeholder task\n", encoding="utf-8"
        )
        wp_path = tasks_dir / "WP01-test.md"
        _write_wp_file(wp_path, "WP01", lane="planned")
        # Seed canonical state so implement doesn't hard-fail
        _seed_wp_lane(feature_dir, "WP01", "planned")

        workspace = lane_worktree_path(workflow_repo, mission_slug)
        workspace.mkdir(parents=True)

        result = CliRunner().invoke(
            workflow.app,
            ["implement", "WP01", "--mission", mission_slug, "--agent", "test-agent"],
        )

        assert result.exit_code == 0, result.stdout
        content = wp_path.read_text(encoding="utf-8")
        _, body, _ = split_frontmatter(content)
        # Find the new history entry (not the seed entry)
        lines = [ln for ln in body.splitlines() if "test-agent" in ln]
        assert len(lines) >= 1, f"Expected history entry with test-agent, got: {body}"
        for line in lines:
            assert "lane=" not in line, f"Body note still contains lane=: {line}"

    def test_implement_body_note_no_lane_from_doing(self, workflow_repo: Path) -> None:
        """When re-entering doing, body note should not contain lane=."""
        mission_slug = "060-test-feature"
        feature_dir = workflow_repo / "kitty-specs" / mission_slug
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        write_single_lane_manifest(feature_dir, wp_ids=("WP01",), predicted_surfaces=("workflow",))
        (feature_dir / "tasks.md").write_text(
            "## WP01 Test\n\n- [x] T001 Placeholder task\n", encoding="utf-8"
        )
        wp_path = tasks_dir / "WP01-test.md"
        _write_wp_file(wp_path, "WP01", lane="doing")
        # Seed canonical state as in_progress (= doing)
        _seed_wp_lane(feature_dir, "WP01", "doing")

        workspace = lane_worktree_path(workflow_repo, mission_slug)
        workspace.mkdir(parents=True)

        result = CliRunner().invoke(
            workflow.app,
            ["implement", "WP01", "--mission", mission_slug, "--agent", "test-agent"],
        )

        assert result.exit_code == 0, result.stdout
        content = wp_path.read_text(encoding="utf-8")
        _, body, _ = split_frontmatter(content)
        lines = [ln for ln in body.splitlines() if "test-agent" in ln]
        assert len(lines) >= 1, f"Expected history entry with test-agent, got: {body}"
        for line in lines:
            assert "lane=" not in line, f"Body note still contains lane=: {line}"


# ---------------------------------------------------------------------------
# T012: review body note does NOT contain lane=
# ---------------------------------------------------------------------------

class TestReviewBodyNoteLaneFree:
    """Review history entries must not contain lane= segments."""

    def test_review_body_note_no_lane(self, workflow_repo: Path) -> None:
        """Review body note should not contain lane= segment."""
        mission_slug = "060-test-feature"
        feature_dir = workflow_repo / "kitty-specs" / mission_slug
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        write_single_lane_manifest(feature_dir, wp_ids=("WP01",), predicted_surfaces=("workflow",))
        (feature_dir / "tasks.md").write_text(
            "## WP01 Test\n\n- [x] T001 Placeholder task\n", encoding="utf-8"
        )
        wp_path = tasks_dir / "WP01-test.md"
        _write_wp_file(wp_path, "WP01", lane="for_review")
        # Seed canonical state
        _seed_wp_lane(feature_dir, "WP01", "for_review")

        result = CliRunner().invoke(
            workflow.app,
            ["review", "WP01", "--mission", mission_slug, "--agent", "test-reviewer"],
        )

        assert result.exit_code == 0, result.stdout
        content = wp_path.read_text(encoding="utf-8")
        _, body, _ = split_frontmatter(content)
        lines = [ln for ln in body.splitlines() if "test-reviewer" in ln]
        assert len(lines) >= 1, f"Expected history entry with test-reviewer, got: {body}"
        for line in lines:
            assert "lane=" not in line, f"Body note still contains lane=: {line}"


# ---------------------------------------------------------------------------
# T013: implement hard-fails when no canonical state
# ---------------------------------------------------------------------------

class TestImplementHardFailNoCanonical:
    """Implement must raise RuntimeError when WP has no canonical status."""

    def test_implement_hardfails_no_events(self, workflow_repo: Path) -> None:
        """Implement should fail when event log has no state for WP."""
        mission_slug = "060-test-feature"
        feature_dir = workflow_repo / "kitty-specs" / mission_slug
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        write_single_lane_manifest(feature_dir, wp_ids=("WP01",), predicted_surfaces=("workflow",))
        (feature_dir / "tasks.md").write_text(
            "## WP01 Test\n\n- [x] T001 Placeholder task\n", encoding="utf-8"
        )
        wp_path = tasks_dir / "WP01-test.md"
        _write_wp_file(wp_path, "WP01", lane="planned")
        # NO event seeding -- WP has no canonical state

        workspace = lane_worktree_path(workflow_repo, mission_slug)
        workspace.mkdir(parents=True)

        result = CliRunner().invoke(
            workflow.app,
            ["implement", "WP01", "--mission", mission_slug, "--agent", "test-agent"],
        )

        assert result.exit_code != 0, f"Expected failure, got exit_code=0: {result.stdout}"
        assert "no canonical status" in (result.stdout + str(result.exception or "")).lower(), (
            f"Expected 'no canonical status' in output, got: {result.stdout}"
        )
        assert "finalize-tasks" in (result.stdout + str(result.exception or "")), (
            f"Expected finalize-tasks guidance in output, got: {result.stdout}"
        )

    def test_implement_hardfails_events_exist_but_not_for_wp(self, workflow_repo: Path) -> None:
        """Implement should fail when event log has events for other WPs but not this one."""
        mission_slug = "060-test-feature"
        feature_dir = workflow_repo / "kitty-specs" / mission_slug
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        write_single_lane_manifest(feature_dir, wp_ids=("WP01",), predicted_surfaces=("workflow",))
        (feature_dir / "tasks.md").write_text(
            "## WP01 Test\n\n- [x] T001 Placeholder task\n", encoding="utf-8"
        )
        wp_path = tasks_dir / "WP01-test.md"
        _write_wp_file(wp_path, "WP01", lane="planned")
        # Seed events for WP02 only — WP01 has no canonical state
        _seed_wp_lane(feature_dir, "WP02", "planned")

        workspace = lane_worktree_path(workflow_repo, mission_slug)
        workspace.mkdir(parents=True)

        result = CliRunner().invoke(
            workflow.app,
            ["implement", "WP01", "--mission", mission_slug, "--agent", "test-agent"],
        )

        assert result.exit_code != 0, f"Expected failure, got exit_code=0: {result.stdout}"
        assert "no canonical status" in (result.stdout + str(result.exception or "")).lower()

    def test_implement_succeeds_with_canonical_state(self, workflow_repo: Path) -> None:
        """Implement should succeed when WP has canonical state in event log."""
        mission_slug = "060-test-feature"
        feature_dir = workflow_repo / "kitty-specs" / mission_slug
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        write_single_lane_manifest(feature_dir, wp_ids=("WP01",), predicted_surfaces=("workflow",))
        (feature_dir / "tasks.md").write_text(
            "## WP01 Test\n\n- [x] T001 Placeholder task\n", encoding="utf-8"
        )
        wp_path = tasks_dir / "WP01-test.md"
        _write_wp_file(wp_path, "WP01", lane="planned")
        # Seed canonical state
        _seed_wp_lane(feature_dir, "WP01", "planned")

        workspace = lane_worktree_path(workflow_repo, mission_slug)
        workspace.mkdir(parents=True)

        result = CliRunner().invoke(
            workflow.app,
            ["implement", "WP01", "--mission", mission_slug, "--agent", "test-agent"],
        )

        assert result.exit_code == 0, f"Expected success: {result.stdout}"


# ---------------------------------------------------------------------------
# T014: review hard-fails when no canonical state
# ---------------------------------------------------------------------------

class TestReviewHardFailNoCanonical:
    """Review must raise RuntimeError when WP has no canonical status."""

    def test_review_hardfails_no_events(self, workflow_repo: Path) -> None:
        """Review should fail when event log has no state for WP."""
        mission_slug = "060-test-feature"
        feature_dir = workflow_repo / "kitty-specs" / mission_slug
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        write_single_lane_manifest(feature_dir, wp_ids=("WP01",), predicted_surfaces=("workflow",))
        wp_path = tasks_dir / "WP01-test.md"
        _write_wp_file(wp_path, "WP01", lane="for_review")
        # NO event seeding -- WP has no canonical state

        result = CliRunner().invoke(
            workflow.app,
            ["review", "WP01", "--mission", mission_slug, "--agent", "test-reviewer"],
        )

        assert result.exit_code != 0, f"Expected failure, got exit_code=0: {result.stdout}"
        assert "no canonical status" in (result.stdout + str(result.exception or "")).lower(), (
            f"Expected 'no canonical status' in output, got: {result.stdout}"
        )
        assert "finalize-tasks" in (result.stdout + str(result.exception or "")), (
            f"Expected finalize-tasks guidance in output, got: {result.stdout}"
        )

    def test_review_hardfails_events_exist_but_not_for_wp(self, workflow_repo: Path) -> None:
        """Review should fail when event log has events for other WPs but not this one."""
        mission_slug = "060-test-feature"
        feature_dir = workflow_repo / "kitty-specs" / mission_slug
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        write_single_lane_manifest(feature_dir, wp_ids=("WP01",), predicted_surfaces=("workflow",))
        wp_path = tasks_dir / "WP01-test.md"
        _write_wp_file(wp_path, "WP01", lane="for_review")
        # Seed events for WP02 only
        _seed_wp_lane(feature_dir, "WP02", "for_review")

        result = CliRunner().invoke(
            workflow.app,
            ["review", "WP01", "--mission", mission_slug, "--agent", "test-reviewer"],
        )

        assert result.exit_code != 0, f"Expected failure, got exit_code=0: {result.stdout}"
        assert "no canonical status" in (result.stdout + str(result.exception or "")).lower()

    def test_review_succeeds_with_canonical_state(self, workflow_repo: Path) -> None:
        """Review should succeed when WP has canonical state in event log."""
        mission_slug = "060-test-feature"
        feature_dir = workflow_repo / "kitty-specs" / mission_slug
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        write_single_lane_manifest(feature_dir, wp_ids=("WP01",), predicted_surfaces=("workflow",))
        (feature_dir / "tasks.md").write_text(
            "## WP01 Test\n\n- [x] T001 Placeholder task\n", encoding="utf-8"
        )
        wp_path = tasks_dir / "WP01-test.md"
        _write_wp_file(wp_path, "WP01", lane="for_review")
        # Seed canonical state
        _seed_wp_lane(feature_dir, "WP01", "for_review")

        result = CliRunner().invoke(
            workflow.app,
            ["review", "WP01", "--mission", mission_slug, "--agent", "test-reviewer"],
        )

        assert result.exit_code == 0, f"Expected success: {result.stdout}"
