"""Test telemetry emission from workflow commands (implement, review) and planning commands.

Bug: ExecutionEvents are not emitted when agents use spec-kitty implement/review
commands OR planning commands (create-feature, setup-plan, finalize-tasks).
The telemetry foundation (Feature 043) was completed but these commands don't emit
events, causing cost tracking gaps during both planning and implementation phases.

Expected: When workflow/planning commands complete, an ExecutionEvent is appended to
execution.events.jsonl with agent, model, tokens, cost, and duration.
"""

from pathlib import Path
import json
import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.workflow import app as workflow_app
from specify_cli.cli.commands.agent.feature import app as feature_app


@pytest.fixture
def feature_with_wp(tmp_path):
    """Create a minimal feature with one WP ready for implementation."""
    feature_dir = tmp_path / "kitty-specs" / "001-test-feature"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    
    # Create meta.json
    meta = {
        "slug": "001-test-feature",
        "friendly_name": "Test Feature",
        "mission": "software-dev",
        "target_branch": "main",
        "vcs": "git"
    }
    (feature_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    
    # Create WP01 in planned lane
    wp_content = """---
work_package_id: "WP01"
title: "Test Implementation"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
dependencies: []
subtasks: ["T001"]
history:
  - timestamp: "2026-02-16T00:00:00Z"
    lane: "planned"
    agent: "system"
    action: "Created"
---

# Work Package Prompt: WP01

## Goal
Test implementation.

## Subtasks
- [ ] T001 Write test code
"""
    (tasks_dir / "WP01-test.md").write_text(wp_content, encoding="utf-8")
    
    # Initialize git repo
    import subprocess
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "checkout", "-b", "main"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=tmp_path, check=True, capture_output=True)
    
    # Create .kittify directory for project metadata
    kittify_dir = tmp_path / ".kittify"
    kittify_dir.mkdir()
    
    return tmp_path, feature_dir


def test_implement_command_emits_execution_event(feature_with_wp, monkeypatch):
    """Bug test: spec-kitty implement should emit ExecutionEvent when agent starts work.
    
    Given: A feature with WP01 in planned lane
    When: Agent runs `spec-kitty agent workflow implement WP01 --agent claude --model claude-sonnet-4.5 --input-tokens 1000 --output-tokens 500 --cost-usd 0.015 --duration-ms 5000`
    Then: execution.events.jsonl contains ExecutionEvent with all telemetry fields
    
    Context: Feature 043 (telemetry) added ExecutionEvent but workflow commands
    don't emit them. Manual task transitions (move-task) emit events, but
    implement/review commands (the primary workflow) don't.
    
    BUG: This test will FAIL until emission is added to workflow.py
    """
    repo_root, feature_dir = feature_with_wp
    monkeypatch.chdir(repo_root)
    
    runner = CliRunner()
    
    # Run implement command with telemetry parameters
    result = runner.invoke(workflow_app, [
        "implement", "WP01",
        "--agent", "claude",
        "--feature", "001-test-feature",
        "--model", "claude-sonnet-4.5",
        "--input-tokens", "1000",
        "--output-tokens", "500",
        "--cost-usd", "0.015",
        "--duration-ms", "5000"
    ])
    
    # Command should succeed
    assert result.exit_code == 0, f"Command failed: {result.output}"
    
    # Verify ExecutionEvent was emitted
    events_file = feature_dir / "execution.events.jsonl"
    assert events_file.exists(), (
        "execution.events.jsonl not found - ExecutionEvent was not emitted. "
        "The implement command should emit ExecutionEvent when agent starts work."
    )
    
    # Parse events
    events = [json.loads(line) for line in events_file.read_text().splitlines()]
    assert len(events) == 1, f"Expected 1 event, found {len(events)}"
    
    event = events[0]
    
    # Verify event structure
    assert event["event_type"] == "ExecutionEvent", f"Wrong event type: {event.get('event_type')}"
    assert event["aggregate_id"] == "001-test-feature", "Wrong aggregate_id"
    
    # Check payload
    payload = event["payload"]
    assert payload["wp_id"] == "WP01"
    assert payload["agent"] == "claude"
    assert payload["role"] == "implementer"
    assert payload["model"] == "claude-sonnet-4.5"
    assert payload["input_tokens"] == 1000
    assert payload["output_tokens"] == 500
    assert payload["cost_usd"] == 0.015
    assert payload["duration_ms"] == 5000
    assert payload["success"] is True
    
    # Check event metadata
    assert "event_id" in event  # ULID or UUID
    assert "timestamp" in event  # ISO timestamp
    assert "lamport_clock" in event


def test_review_command_emits_execution_event(feature_with_wp, monkeypatch):
    """Bug test: spec-kitty review should emit ExecutionEvent when reviewer starts.
    
    Given: A feature with WP01 in for_review lane
    When: Reviewer runs `spec-kitty agent workflow review WP01 --agent codex --model gpt-4.1 --input-tokens 2000 --output-tokens 300 --cost-usd 0.02 --duration-ms 3000`
    Then: execution.events.jsonl contains ExecutionEvent with role="reviewer"
    
    BUG: This test will FAIL until emission is added to workflow.py review command
    """
    repo_root, feature_dir = feature_with_wp
    monkeypatch.chdir(repo_root)
    
    # Move WP01 to for_review lane first
    wp_file = feature_dir / "tasks" / "WP01-test.md"
    content = wp_file.read_text()
    content = content.replace('lane: "planned"', 'lane: "for_review"')
    wp_file.write_text(content)
    
    runner = CliRunner()
    
    # Run review command with telemetry parameters
    result = runner.invoke(workflow_app, [
        "review", "WP01",
        "--agent", "codex",
        "--feature", "001-test-feature",
        "--model", "gpt-4.1",
        "--input-tokens", "2000",
        "--output-tokens", "300",
        "--cost-usd", "0.02",
        "--duration-ms", "3000"
    ])
    
    # Command should succeed
    assert result.exit_code == 0, f"Command failed: {result.output}"
    
    # Verify ExecutionEvent was emitted
    events_file = feature_dir / "execution.events.jsonl"
    assert events_file.exists(), (
        "execution.events.jsonl not found - ExecutionEvent was not emitted. "
        "The review command should emit ExecutionEvent when reviewer starts work."
    )
    
    # Parse events
    events = [json.loads(line) for line in events_file.read_text().splitlines()]
    assert len(events) == 1, f"Expected 1 event, found {len(events)}"
    
    event = events[0]
    
    # Verify event structure (reviewer role is key difference)
    assert event["event_type"] == "ExecutionEvent"
    assert event["aggregate_id"] == "001-test-feature"
    
    # Check payload
    payload = event["payload"]
    assert payload["wp_id"] == "WP01"
    assert payload["agent"] == "codex"
    assert payload["role"] == "reviewer"  # NOT implementer
    assert payload["model"] == "gpt-4.1"
    assert payload["input_tokens"] == 2000
    assert payload["output_tokens"] == 300
    assert payload["cost_usd"] == 0.02
    assert payload["duration_ms"] == 3000


def test_create_feature_emits_execution_event(tmp_path, monkeypatch):
    """Test that create-feature (specify workflow) emits ExecutionEvent with role='planner'.
    
    Planning commands should emit ExecutionEvents because they consume significant
    tokens during specification creation. The role should be 'planner' (not 'implementer').
    
    BUG: This test will FAIL until emission is added to feature.py create_feature()
    """
    monkeypatch.chdir(tmp_path)
    
    # Setup minimal git repo
    import subprocess
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "checkout", "-b", "main"], cwd=tmp_path, check=True, capture_output=True)
    
    # Create config and constitution (required by create-feature)
    kittify_dir = tmp_path / ".kittify"
    kittify_dir.mkdir()
    config = kittify_dir / "config.yaml"
    config.write_text("version: 0.11.0\nproject_name: test\n")
    
    constitution_dir = kittify_dir / "constitution"
    constitution_dir.mkdir()
    (constitution_dir / "constitution.md").write_text("# Constitution\n")
    
    # Create kitty-specs directory
    specs_dir = tmp_path / "kitty-specs"
    specs_dir.mkdir()
    
    runner = CliRunner()
    
    # Run create-feature with telemetry parameters
    result = runner.invoke(
        feature_app,
        [
            "create-feature",
            "test-feature",
            "--agent", "claude",
            "--model", "claude-sonnet-4.5",
            "--input-tokens", "5000",
            "--output-tokens", "2500",
            "--cost-usd", "0.08",
            "--duration-ms", "15000",
        ],
        catch_exceptions=False,
    )
    
    assert result.exit_code == 0, f"Command failed: {result.stdout}"
    
    # Verify execution event was created
    feature_dir = specs_dir / "001-test-feature"
    event_file = feature_dir / "execution.events.jsonl"
    assert event_file.exists(), "execution.events.jsonl not created by create-feature"
    
    # Parse and validate event
    events = [json.loads(line) for line in event_file.read_text().strip().split("\n")]
    assert len(events) == 1, f"Expected 1 event, got {len(events)}"
    
    event = events[0]
    assert event["event_type"] == "ExecutionEvent"
    assert event["aggregate_id"] == "001-test-feature"
    
    payload = event["payload"]
    assert payload["agent"] == "claude"
    assert payload["role"] == "planner"  # Planning role, not implementer
    assert payload["model"] == "claude-sonnet-4.5"
    assert payload["input_tokens"] == 5000
    assert payload["output_tokens"] == 2500
    assert payload["cost_usd"] == 0.08
    assert payload["duration_ms"] == 15000


def test_setup_plan_emits_execution_event(tmp_path, monkeypatch):
    """Test that setup-plan (plan workflow) emits ExecutionEvent with role='planner'.
    
    Planning commands should emit events to track token consumption during
    implementation plan creation.
    
    BUG: This test will FAIL until emission is added to feature.py setup_plan()
    """
    monkeypatch.chdir(tmp_path)
    
    # Setup minimal git repo
    import subprocess
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "checkout", "-b", "main"], cwd=tmp_path, check=True, capture_output=True)
    
    # Create config and feature directory
    kittify_dir = tmp_path / ".kittify"
    kittify_dir.mkdir()
    config = kittify_dir / "config.yaml"
    config.write_text("version: 0.11.0\nproject_name: test\n")
    
    specs_dir = tmp_path / "kitty-specs"
    specs_dir.mkdir()
    feature_dir = specs_dir / "001-test-feature"
    feature_dir.mkdir()
    
    # Create spec.md (required before plan)
    (feature_dir / "spec.md").write_text("# Spec\n")
    
    # Create meta.json with target_branch
    meta = {"target_branch": "main", "feature_number": "001"}
    (feature_dir / "meta.json").write_text(json.dumps(meta))
    
    runner = CliRunner()
    
    # Run setup-plan with telemetry parameters
    result = runner.invoke(
        feature_app,
        [
            "setup-plan",
            "--feature", "001-test-feature",
            "--agent", "claude",
            "--model", "claude-sonnet-4.5",
            "--input-tokens", "8000",
            "--output-tokens", "4000",
            "--cost-usd", "0.12",
            "--duration-ms", "20000",
        ],
        catch_exceptions=False,
    )
    
    assert result.exit_code == 0, f"Command failed: {result.stdout}"
    
    # Verify execution event was created
    event_file = feature_dir / "execution.events.jsonl"
    assert event_file.exists(), "execution.events.jsonl not created by setup-plan"
    
    # Parse and validate event
    events = [json.loads(line) for line in event_file.read_text().strip().split("\n")]
    assert len(events) == 1, f"Expected 1 event, got {len(events)}"
    
    event = events[0]
    assert event["event_type"] == "ExecutionEvent"
    assert event["aggregate_id"] == "001-test-feature"
    
    payload = event["payload"]
    assert payload["agent"] == "claude"
    assert payload["role"] == "planner"
    assert payload["model"] == "claude-sonnet-4.5"
    assert payload["input_tokens"] == 8000
    assert payload["output_tokens"] == 4000
    assert payload["cost_usd"] == 0.12
    assert payload["duration_ms"] == 20000


def test_finalize_tasks_emits_execution_event(tmp_path, monkeypatch):
    """Test that finalize-tasks (tasks workflow) emits ExecutionEvent with role='planner'.
    
    Task finalization is part of the planning workflow and should emit events
    to track token consumption during task generation.
    
    BUG: This test will FAIL until emission is added to feature.py finalize_tasks()
    """
    # Setup minimal git repo
    import subprocess
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "checkout", "-b", "main"], cwd=tmp_path, check=True, capture_output=True)
    
    # Create config and feature directory with tasks
    kittify_dir = tmp_path / ".kittify"
    kittify_dir.mkdir()
    config = kittify_dir / "config.yaml"
    config.write_text("version: 0.11.0\nproject_name: test\n")
    
    specs_dir = tmp_path / "kitty-specs"
    specs_dir.mkdir()
    feature_dir = specs_dir / "001-test-feature"
    feature_dir.mkdir()
    
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir()
    
    # Create minimal WP file with frontmatter
    wp_content = """---
work_package_id: "WP01"
title: "Test WP"
lane: "planned"
---

# WP01 - Test WP
"""
    (tasks_dir / "WP01-test.md").write_text(wp_content)
    
    # Create tasks.md (no dependencies)
    (feature_dir / "tasks.md").write_text("# Tasks\n\n## WP01 - Test WP\n")
    
    # Create meta.json
    meta = {"target_branch": "main", "feature_number": "001"}
    (feature_dir / "meta.json").write_text(json.dumps(meta))
    
    monkeypatch.chdir(feature_dir)  # Run from feature directory
    
    runner = CliRunner()
    
    # Run finalize-tasks with telemetry parameters
    result = runner.invoke(
        feature_app,
        [
            "finalize-tasks",
            "--agent", "claude",
            "--model", "claude-sonnet-4.5",
            "--input-tokens", "10000",
            "--output-tokens", "5000",
            "--cost-usd", "0.15",
            "--duration-ms", "25000",
        ],
        catch_exceptions=False,
    )
    
    assert result.exit_code == 0, f"Command failed: {result.stdout}"
    
    # Verify execution event was created
    event_file = feature_dir / "execution.events.jsonl"
    assert event_file.exists(), "execution.events.jsonl not created by finalize-tasks"
    
    # Parse and validate event
    events = [json.loads(line) for line in event_file.read_text().strip().split("\n")]
    assert len(events) == 1, f"Expected 1 event, got {len(events)}"
    
    event = events[0]
    assert event["event_type"] == "ExecutionEvent"
    assert event["aggregate_id"] == "001-test-feature"
    
    payload = event["payload"]
    assert payload["agent"] == "claude"
    assert payload["role"] == "planner"
    assert payload["model"] == "claude-sonnet-4.5"
    assert payload["input_tokens"] == 10000
    assert payload["output_tokens"] == 5000
    assert payload["cost_usd"] == 0.15
    assert payload["duration_ms"] == 25000
