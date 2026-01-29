"""Integration tests for finalize-tasks JSON output improvements.

Tests that finalize-tasks provides clear information about commit status,
preventing agent confusion when unrelated files are dirty.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

# Get repo root for Python module invocation
REPO_ROOT = Path(__file__).resolve().parents[2]


def run_cli(project_path: Path, *args: str) -> subprocess.CompletedProcess:
    """Execute spec-kitty CLI using Python module invocation."""
    from tests.test_isolation_helpers import get_venv_python

    env = os.environ.copy()
    src_path = REPO_ROOT / "src"
    env["PYTHONPATH"] = f"{src_path}{os.pathsep}{env.get('PYTHONPATH', '')}".rstrip(
        os.pathsep
    )
    env.setdefault("SPEC_KITTY_TEMPLATE_ROOT", str(REPO_ROOT))
    command = [str(get_venv_python()), "-m", "specify_cli.__init__", *args]
    return subprocess.run(
        command,
        cwd=str(project_path),
        capture_output=True,
        text=True,
        env=env,
    )


def create_test_feature(repo: Path) -> Path:
    """Create minimal feature with tasks for testing."""
    import yaml

    # Create .kittify structure
    kittify = repo / ".kittify"
    kittify.mkdir(exist_ok=True)

    config = {
        "vcs": {"type": "git"},
        "agents": {"available": ["claude"]}
    }
    (kittify / "config.yaml").write_text(yaml.dump(config))

    metadata = {
        "spec_kitty": {"version": "0.13.8"}
    }
    (kittify / "metadata.yaml").write_text(yaml.dump(metadata))

    # Create feature
    feature_dir = repo / "kitty-specs/001-test-feature"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    # Create meta.json
    meta = {
        "feature_number": "001",
        "slug": "001-test-feature",
        "created_at": "2026-01-29T00:00:00Z",
        "target_branch": "main",
        "vcs": "git",
    }
    (feature_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")

    # Create tasks.md
    (feature_dir / "tasks.md").write_text(
        "# Tasks\n\n## WP01\n\nSetup\n\n## WP02\n\nDepends on WP01\n"
    )

    # Create WP files
    for wp_id in ["WP01", "WP02"]:
        wp_file = tasks_dir / f"{wp_id}-test.md"
        wp_file.write_text(
            f"---\n"
            f"work_package_id: {wp_id}\n"
            f"lane: planned\n"
            f"---\n\n"
            f"# {wp_id}\n"
        )

    # Commit base state
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial feature"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    return feature_dir


def test_finalize_tasks_json_includes_commit_hash(tmp_path):
    """Test that finalize-tasks JSON output includes commit hash.

    Validates:
    - JSON has "commit_hash" field
    - Hash is valid git SHA (40 chars hex)
    - Hash matches actual HEAD after command
    """
    repo = tmp_path / "repo"
    repo.mkdir()

    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    feature_dir = create_test_feature(repo)

    # Run finalize-tasks
    result = run_cli(repo, "agent", "feature", "finalize-tasks", "--json")
    assert result.returncode == 0, f"Failed: {result.stderr}"

    # Parse JSON output
    output = json.loads(result.stdout)

    # Verify commit_hash present
    assert "commit_hash" in output, "JSON output should include commit_hash"
    assert output["commit_hash"] is not None, "commit_hash should not be null"

    # Verify hash is valid SHA
    commit_hash = output["commit_hash"]
    assert len(commit_hash) == 40, "commit_hash should be 40-char SHA"
    assert all(c in "0123456789abcdef" for c in commit_hash), "commit_hash should be hex"

    # Verify hash matches actual HEAD
    result_head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    actual_head = result_head.stdout.strip()

    assert commit_hash == actual_head, "commit_hash should match git HEAD"


def test_finalize_tasks_json_includes_commit_created_flag(tmp_path):
    """Test that finalize-tasks JSON output includes commit_created boolean.

    Validates:
    - JSON has "commit_created" field
    - Value is true when files are committed
    - Value is false when nothing to commit
    """
    repo = tmp_path / "repo"
    repo.mkdir()

    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    feature_dir = create_test_feature(repo)

    # Run finalize-tasks (should create commit)
    result = run_cli(repo, "agent", "feature", "finalize-tasks", "--json")
    assert result.returncode == 0

    output = json.loads(result.stdout)

    # Verify commit_created is true
    assert "commit_created" in output, "JSON should include commit_created"
    assert isinstance(output["commit_created"], bool), "commit_created should be boolean"
    assert output["commit_created"] is True, "Should create commit on first run"

    # Run again (nothing to commit)
    result2 = run_cli(repo, "agent", "feature", "finalize-tasks", "--json")
    assert result2.returncode == 0

    output2 = json.loads(result2.stdout)

    # Should indicate no commit created
    assert output2["commit_created"] is False, "Should not create commit on second run"


def test_finalize_tasks_json_includes_files_committed(tmp_path):
    """Test that finalize-tasks JSON output lists files committed.

    Validates:
    - JSON has "files_committed" field
    - List includes tasks.md and WP files
    - Paths are relative to repo root
    """
    repo = tmp_path / "repo"
    repo.mkdir()

    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    feature_dir = create_test_feature(repo)

    # Run finalize-tasks
    result = run_cli(repo, "agent", "feature", "finalize-tasks", "--json")
    assert result.returncode == 0

    output = json.loads(result.stdout)

    # Verify files_committed present
    assert "files_committed" in output, "JSON should include files_committed"
    assert isinstance(output["files_committed"], list), "files_committed should be list"

    # Verify includes expected files
    files = output["files_committed"]
    assert any("tasks.md" in f for f in files), "Should include tasks.md"
    assert any("WP01" in f for f in files), "Should include WP01 file"
    assert any("WP02" in f for f in files), "Should include WP02 file"


def test_finalize_tasks_with_unrelated_dirty_files(tmp_path):
    """Test that finalize-tasks succeeds despite unrelated dirty files.

    This replicates the confusion from ~/tmp where template deletions
    made the agent think the commit failed.

    Validates:
    - Commit succeeds even with unrelated dirty files
    - JSON clearly shows commit_created: true
    - Agent can distinguish between committed tasks vs dirty templates
    """
    repo = tmp_path / "repo"
    repo.mkdir()

    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    feature_dir = create_test_feature(repo)

    # Create unrelated dirty files (simulating template deletions)
    templates_dir = repo / ".kittify/templates"
    templates_dir.mkdir(parents=True, exist_ok=True)

    # Add some files and commit them
    for i in range(5):
        (templates_dir / f"template{i}.md").write_text(f"Template {i}\n")

    subprocess.run(["git", "add", str(templates_dir)], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Add templates"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Now delete them (making them dirty - but don't commit)
    for i in range(5):
        (templates_dir / f"template{i}.md").unlink()

    # Verify git shows dirty files
    status_result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    assert " D " in status_result.stdout, "Should have deleted files"

    # Run finalize-tasks (should succeed despite dirty templates)
    result = run_cli(repo, "agent", "feature", "finalize-tasks", "--json")
    assert result.returncode == 0, "Should succeed despite unrelated dirty files"

    output = json.loads(result.stdout)

    # CRITICAL: Should clearly indicate commit was created
    assert output["commit_created"] is True, "Should create commit for tasks despite dirty templates"
    assert output["commit_hash"] is not None, "Should have commit hash"

    # Verify tasks are actually committed
    tasks_status = subprocess.run(
        ["git", "status", "kitty-specs/"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "nothing to commit" in tasks_status.stdout, "Tasks should be committed"

    # Verify templates are still dirty (unrelated)
    overall_status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    assert " D " in overall_status.stdout, "Templates should still be dirty (separate concern)"


def test_json_output_prevents_agent_confusion(tmp_path):
    """Test that improved JSON output prevents agent from committing twice.

    This test documents the fix for the confusion observed in ~/tmp.

    Before fix:
    - Agent ran finalize-tasks
    - JSON said "result": "success" (vague)
    - Agent saw dirty files in git status (unrelated)
    - Agent tried to commit again (redundant)

    After fix:
    - Agent runs finalize-tasks
    - JSON says "commit_created": true, "commit_hash": "abc123..."
    - Agent knows files are committed (explicit confirmation)
    - Agent doesn't commit again
    """
    repo = tmp_path / "repo"
    repo.mkdir()

    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    feature_dir = create_test_feature(repo)

    # Get HEAD before finalize-tasks
    result_before = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    head_before = result_before.stdout.strip()

    # Run finalize-tasks
    result = run_cli(repo, "agent", "feature", "finalize-tasks", "--json")
    assert result.returncode == 0

    output = json.loads(result.stdout)

    # Get HEAD after finalize-tasks
    result_after = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    head_after = result_after.stdout.strip()

    # Verify commit was created
    assert head_before != head_after, "HEAD should advance (commit created)"

    # Verify JSON clearly communicates this
    assert output["commit_created"] is True, "JSON should say commit_created: true"
    assert output["commit_hash"] == head_after, "commit_hash should match new HEAD"

    # Verify files listed
    assert len(output["files_committed"]) >= 2, "Should list tasks.md and WP files"

    # Agent can now check: if commit_created == true, don't commit again
    if output["commit_created"]:
        # Files are committed, verify with commit_hash
        verify_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=True,
        )
        assert verify_result.stdout.strip() == output["commit_hash"]
        # Don't run git commit again!


def test_json_output_schema_complete(tmp_path):
    """Test that JSON output has all expected fields for agent decision-making.

    Required fields:
    - result: "success" | "error"
    - commit_created: boolean (did commit happen?)
    - commit_hash: string | null (SHA if committed)
    - files_committed: list[str] (relative paths)
    - updated_wp_count: int (how many WPs updated)
    - tasks_dir: string (for reference)
    """
    repo = tmp_path / "repo"
    repo.mkdir()

    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    feature_dir = create_test_feature(repo)

    # Run finalize-tasks
    result = run_cli(repo, "agent", "feature", "finalize-tasks", "--json")
    assert result.returncode == 0

    output = json.loads(result.stdout)

    # Verify all required fields present
    required_fields = [
        "result",
        "commit_created",
        "commit_hash",
        "files_committed",
        "updated_wp_count",
        "tasks_dir",
    ]

    for field in required_fields:
        assert field in output, f"JSON output should include '{field}'"

    # Verify types
    assert isinstance(output["result"], str)
    assert isinstance(output["commit_created"], bool)
    assert isinstance(output["commit_hash"], (str, type(None)))
    assert isinstance(output["files_committed"], list)
    assert isinstance(output["updated_wp_count"], int)
    assert isinstance(output["tasks_dir"], str)
