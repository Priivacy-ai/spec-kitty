"""Integration tests for move-task delegation to canonical emit pipeline.

Tests that move_task correctly delegates state mutation to
emit_status_transition() while retaining all existing pre-validation
logic and backward compatibility.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.tasks import app
from specify_cli.status.store import read_events, EVENTS_FILENAME
from specify_cli.status.reducer import SNAPSHOT_FILENAME
from specify_cli.tasks_support import split_frontmatter, extract_scalar

runner = CliRunner()


@pytest.fixture
def task_repo(tmp_path: Path) -> Path:
    """Create a temporary repository with task structure and git init."""
    repo = tmp_path / "test-repo"
    repo.mkdir()

    # Initialize git repo
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Create .kittify marker
    (repo / ".kittify").mkdir()

    # Create feature structure
    feature_dir = repo / "kitty-specs" / "001-test-feature"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    # Create initial task file
    task_file = tasks_dir / "WP01-test-task.md"
    task_file.write_text("""---
work_package_id: "WP01"
title: "Test Task"
lane: "planned"
subtasks: ["T001", "T002"]
phase: "Phase 1"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
---

# Work Package: WP01 - Test Task

Test implementation content.

## Activity Log

- 2025-01-01T00:00:00Z – system – lane=planned – Initial creation
""")

    # Create spec.md (needed for feature detection)
    (feature_dir / "spec.md").write_text("# Spec\n")

    # Git commit
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    return repo


class TestMoveTaskProducesJsonlEvent:
    """T047: test_move_task_produces_jsonl_event"""

    def test_move_task_produces_jsonl_event(self, task_repo: Path, monkeypatch):
        """Moving a task should produce a JSONL event in status.events.jsonl."""
        monkeypatch.chdir(task_repo)

        result = runner.invoke(
            app,
            [
                "move-task",
                "WP01",
                "--to",
                "doing",
                "--feature",
                "001-test-feature",
                "--agent",
                "test-agent",
                "--json",
            ],
        )

        assert result.exit_code == 0, f"stdout: {result.stdout}"

        # Verify JSONL event file was created
        feature_dir = task_repo / "kitty-specs" / "001-test-feature"
        events_file = feature_dir / EVENTS_FILENAME
        assert events_file.exists(), "status.events.jsonl should exist after move-task"

        # Read and verify event content
        events = read_events(feature_dir)
        assert len(events) >= 1, "At least one event should be recorded"

        last_event = events[-1]
        assert last_event.wp_id == "WP01"
        assert str(last_event.to_lane) == "in_progress"
        assert last_event.actor == "test-agent"
        assert last_event.feature_slug == "001-test-feature"


class TestMoveTaskProducesStatusJson:
    """T047: test_move_task_produces_status_json"""

    def test_move_task_produces_status_json(self, task_repo: Path, monkeypatch):
        """Moving a task should materialize a status.json snapshot."""
        monkeypatch.chdir(task_repo)

        result = runner.invoke(
            app,
            [
                "move-task",
                "WP01",
                "--to",
                "doing",
                "--feature",
                "001-test-feature",
                "--agent",
                "test-agent",
                "--json",
            ],
        )

        assert result.exit_code == 0, f"stdout: {result.stdout}"

        # Verify status.json snapshot was created
        feature_dir = task_repo / "kitty-specs" / "001-test-feature"
        snapshot_file = feature_dir / SNAPSHOT_FILENAME
        assert snapshot_file.exists(), "status.json should exist after move-task"

        # Read and verify snapshot content
        snapshot = json.loads(snapshot_file.read_text(encoding="utf-8"))
        assert snapshot["feature_slug"] == "001-test-feature"
        assert "WP01" in snapshot["work_packages"]
        wp_state = snapshot["work_packages"]["WP01"]
        assert wp_state["lane"] == "in_progress"


class TestMoveTaskFrontmatterStillUpdated:
    """T047: test_move_task_frontmatter_still_updated"""

    def test_move_task_frontmatter_still_updated(self, task_repo: Path, monkeypatch):
        """Moving a task should still update the WP file's frontmatter."""
        monkeypatch.chdir(task_repo)

        result = runner.invoke(
            app,
            [
                "move-task",
                "WP01",
                "--to",
                "doing",
                "--feature",
                "001-test-feature",
                "--agent",
                "test-agent",
                "--assignee",
                "claude",
                "--shell-pid",
                "12345",
                "--json",
            ],
        )

        assert result.exit_code == 0, f"stdout: {result.stdout}"

        # Verify WP file frontmatter was updated
        wp_file = task_repo / "kitty-specs" / "001-test-feature" / "tasks" / "WP01-test-task.md"
        content = wp_file.read_text(encoding="utf-8")
        front, body, _ = split_frontmatter(content)

        # Lane should be set to canonical name
        assert extract_scalar(front, "lane") == "in_progress"

        # Metadata fields should be present
        assert extract_scalar(front, "agent") == "test-agent"
        assert extract_scalar(front, "assignee") == "claude"
        assert extract_scalar(front, "shell_pid") == "12345"

        # Activity log should have entry
        assert "Moved to in_progress" in body
        assert "test-agent" in body


class TestMoveTaskDoingAliasMapsToInProgress:
    """T047: test_move_task_doing_alias_maps_to_in_progress"""

    def test_move_task_doing_alias_maps_to_in_progress(self, task_repo: Path, monkeypatch):
        """--to doing should resolve to in_progress in both event and frontmatter."""
        monkeypatch.chdir(task_repo)

        result = runner.invoke(
            app,
            [
                "move-task",
                "WP01",
                "--to",
                "doing",
                "--feature",
                "001-test-feature",
                "--agent",
                "test-agent",
                "--json",
            ],
        )

        assert result.exit_code == 0, f"stdout: {result.stdout}"

        # Parse JSON output
        json_line = None
        for line in result.stdout.strip().split("\n"):
            if line.strip().startswith("{"):
                json_line = line.strip()
                break
        assert json_line is not None
        output = json.loads(json_line)

        # Output should show resolved lane name
        assert output["new_lane"] == "in_progress"

        # Event should record canonical lane
        feature_dir = task_repo / "kitty-specs" / "001-test-feature"
        events = read_events(feature_dir)
        assert len(events) >= 1
        assert str(events[-1].to_lane) == "in_progress"

        # Frontmatter should have canonical lane
        wp_file = feature_dir / "tasks" / "WP01-test-task.md"
        content = wp_file.read_text(encoding="utf-8")
        front, _, _ = split_frontmatter(content)
        assert extract_scalar(front, "lane") == "in_progress"


class TestMoveTaskPreValidationStillWorks:
    """T047: test_move_task_pre_validation_still_works"""

    def test_agent_ownership_check_still_works(self, task_repo: Path, monkeypatch):
        """Agent ownership check should fire BEFORE emit pipeline."""
        monkeypatch.chdir(task_repo)

        # First, assign WP01 to agent-a
        result1 = runner.invoke(
            app,
            [
                "move-task",
                "WP01",
                "--to",
                "doing",
                "--feature",
                "001-test-feature",
                "--agent",
                "agent-a",
                "--json",
            ],
        )
        assert result1.exit_code == 0, f"stdout: {result1.stdout}"

        # Now try to move as agent-b (should fail without --force)
        result2 = runner.invoke(
            app,
            [
                "move-task",
                "WP01",
                "--to",
                "for_review",
                "--feature",
                "001-test-feature",
                "--agent",
                "agent-b",
                "--json",
            ],
        )
        assert result2.exit_code == 1

        # Verify error mentions agent mismatch
        json_line = None
        for line in result2.stdout.strip().split("\n"):
            if line.strip().startswith("{"):
                json_line = line.strip()
                break
        assert json_line is not None
        output = json.loads(json_line)
        assert "agent-a" in output.get("error", "")

    def test_invalid_lane_still_rejected(self, task_repo: Path, monkeypatch):
        """Invalid lane names should be rejected before reaching emit pipeline."""
        monkeypatch.chdir(task_repo)

        result = runner.invoke(
            app,
            [
                "move-task",
                "WP01",
                "--to",
                "bogus_lane",
                "--feature",
                "001-test-feature",
                "--json",
            ],
        )
        assert result.exit_code == 1

        # Verify no events were created (validation failed before emit)
        feature_dir = task_repo / "kitty-specs" / "001-test-feature"
        events_file = feature_dir / EVENTS_FILENAME
        if events_file.exists():
            events = read_events(feature_dir)
            # No new events should exist for this failed transition
            for ev in events:
                assert ev.wp_id != "WP01" or str(ev.to_lane) != "bogus_lane"


class TestMoveTaskNoCommitStillEmitsEvent:
    """T047: test_move_task_no_commit_still_emits_event"""

    def test_move_task_no_commit_still_emits_event(self, task_repo: Path, monkeypatch):
        """--no-auto-commit should still produce JSONL event and status.json."""
        monkeypatch.chdir(task_repo)

        result = runner.invoke(
            app,
            [
                "move-task",
                "WP01",
                "--to",
                "doing",
                "--feature",
                "001-test-feature",
                "--agent",
                "test-agent",
                "--no-auto-commit",
                "--json",
            ],
        )

        assert result.exit_code == 0, f"stdout: {result.stdout}"

        # Verify JSONL event was still created
        feature_dir = task_repo / "kitty-specs" / "001-test-feature"
        events_file = feature_dir / EVENTS_FILENAME
        assert events_file.exists(), "Events should be created even without auto-commit"

        events = read_events(feature_dir)
        assert len(events) >= 1

        # Verify status.json snapshot was still created
        snapshot_file = feature_dir / SNAPSHOT_FILENAME
        assert snapshot_file.exists(), "Snapshot should be created even without auto-commit"


class TestMoveTaskBehaviorMatchesPreRefactor:
    """T047: test_move_task_behavior_matches_pre_refactor"""

    def test_full_lane_progression_still_works(self, task_repo: Path, monkeypatch):
        """Full lane progression planned -> doing -> for_review -> done
        should still work end-to-end."""
        monkeypatch.chdir(task_repo)

        # planned -> doing (in_progress)
        result1 = runner.invoke(
            app,
            [
                "move-task",
                "WP01",
                "--to",
                "doing",
                "--feature",
                "001-test-feature",
                "--agent",
                "test-agent",
                "--json",
            ],
        )
        assert result1.exit_code == 0, f"step 1 stdout: {result1.stdout}"

        # doing -> for_review
        result2 = runner.invoke(
            app,
            [
                "move-task",
                "WP01",
                "--to",
                "for_review",
                "--feature",
                "001-test-feature",
                "--agent",
                "test-agent",
                "--json",
            ],
        )
        assert result2.exit_code == 0, f"step 2 stdout: {result2.stdout}"

        # for_review -> done
        result3 = runner.invoke(
            app,
            [
                "move-task",
                "WP01",
                "--to",
                "done",
                "--feature",
                "001-test-feature",
                "--agent",
                "test-agent",
                "--approval-ref",
                "PR#42",
                "--json",
            ],
        )
        assert result3.exit_code == 0, f"step 3 stdout: {result3.stdout}"

        # Verify final state in frontmatter
        wp_file = task_repo / "kitty-specs" / "001-test-feature" / "tasks" / "WP01-test-task.md"
        content = wp_file.read_text(encoding="utf-8")
        front, body, _ = split_frontmatter(content)
        assert extract_scalar(front, "lane") == "done"

        # Verify canonical progression events are in the JSONL log
        feature_dir = task_repo / "kitty-specs" / "001-test-feature"
        events = read_events(feature_dir)
        wp01_events = [e for e in events if e.wp_id == "WP01"]
        assert len(wp01_events) == 4

        lanes = [str(e.to_lane) for e in wp01_events]
        assert lanes == ["claimed", "in_progress", "for_review", "done"]

    def test_done_auto_populates_approval_reference(self, task_repo: Path, monkeypatch):
        """for_review -> done auto-populates approval reference when omitted."""
        monkeypatch.chdir(task_repo)

        runner.invoke(
            app,
            [
                "move-task",
                "WP01",
                "--to",
                "doing",
                "--feature",
                "001-test-feature",
                "--agent",
                "test-agent",
                "--json",
            ],
        )
        runner.invoke(
            app,
            [
                "move-task",
                "WP01",
                "--to",
                "for_review",
                "--feature",
                "001-test-feature",
                "--agent",
                "test-agent",
                "--json",
            ],
        )
        result = runner.invoke(
            app,
            [
                "move-task",
                "WP01",
                "--to",
                "done",
                "--feature",
                "001-test-feature",
                "--agent",
                "test-agent",
                "--json",
            ],
        )
        assert result.exit_code == 0
        feature_dir = task_repo / "kitty-specs" / "001-test-feature"
        events = read_events(feature_dir)
        done_events = [e for e in events if str(e.to_lane) == "done"]
        assert done_events
        assert done_events[-1].evidence is not None
        assert done_events[-1].evidence.review.reference.startswith("auto-approval:")

    def test_json_output_format_preserved(self, task_repo: Path, monkeypatch):
        """JSON output should have the same fields as before refactoring."""
        monkeypatch.chdir(task_repo)

        result = runner.invoke(
            app,
            [
                "move-task",
                "WP01",
                "--to",
                "doing",
                "--feature",
                "001-test-feature",
                "--agent",
                "test-agent",
                "--json",
            ],
        )

        assert result.exit_code == 0, f"stdout: {result.stdout}"

        # Find JSON output line
        json_line = None
        for line in result.stdout.strip().split("\n"):
            if line.strip().startswith("{"):
                json_line = line.strip()
                break
        assert json_line is not None
        output = json.loads(json_line)

        # Verify required fields exist
        assert "result" in output
        assert "task_id" in output
        assert "old_lane" in output
        assert "new_lane" in output
        assert "path" in output

        assert output["result"] == "success"
        assert output["task_id"] == "WP01"
        assert output["old_lane"] == "planned"

    def test_activity_log_still_appended(self, task_repo: Path, monkeypatch):
        """Activity log entries should still be appended to the WP body."""
        monkeypatch.chdir(task_repo)

        result = runner.invoke(
            app,
            [
                "move-task",
                "WP01",
                "--to",
                "doing",
                "--feature",
                "001-test-feature",
                "--agent",
                "my-agent",
                "--shell-pid",
                "9999",
                "--note",
                "Starting implementation",
                "--json",
            ],
        )

        assert result.exit_code == 0, f"stdout: {result.stdout}"

        wp_file = task_repo / "kitty-specs" / "001-test-feature" / "tasks" / "WP01-test-task.md"
        content = wp_file.read_text(encoding="utf-8")

        # Verify activity log entry format
        assert "my-agent" in content
        assert "shell_pid=9999" in content
        assert "Starting implementation" in content
        assert "lane=in_progress" in content

    def test_new_canonical_lanes_work(self, task_repo: Path, monkeypatch):
        """New canonical lanes (claimed, blocked, canceled) should work."""
        monkeypatch.chdir(task_repo)

        # Move to blocked (new canonical lane)
        result = runner.invoke(
            app,
            [
                "move-task",
                "WP01",
                "--to",
                "blocked",
                "--feature",
                "001-test-feature",
                "--agent",
                "test-agent",
                "--json",
            ],
        )

        assert result.exit_code == 0, f"stdout: {result.stdout}"

        # Verify frontmatter
        wp_file = task_repo / "kitty-specs" / "001-test-feature" / "tasks" / "WP01-test-task.md"
        content = wp_file.read_text(encoding="utf-8")
        front, _, _ = split_frontmatter(content)
        assert extract_scalar(front, "lane") == "blocked"

        # Verify event was recorded
        feature_dir = task_repo / "kitty-specs" / "001-test-feature"
        events = read_events(feature_dir)
        assert any(str(e.to_lane) == "blocked" for e in events)
