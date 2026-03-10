from __future__ import annotations

import json
import pytest
import ssl
import subprocess
import sys
from pathlib import Path

from tests.utils import REPO_ROOT, run, run_tasks_cli, write_wp
from task_helpers import locate_work_package


def assert_success(result) -> None:
    if result.returncode != 0:
        raise AssertionError(f"Command failed: {result.stderr}\nSTDOUT: {result.stdout}")


def test_update_and_rollback(feature_repo: Path, feature_slug: str) -> None:
    """Test updating WP lane and rolling back."""
    result = run_tasks_cli(["update", feature_slug, "WP01", "doing"], cwd=feature_repo)
    assert_success(result)
    run(["git", "commit", "-am", "Update to doing"], cwd=feature_repo)

    updated_wp = locate_work_package(feature_repo, feature_slug, "WP01")
    assert updated_wp.current_lane == "doing"
    assert 'lane: "doing"' in updated_wp.frontmatter

    # File should still be in same location (flat tasks/)
    assert updated_wp.path.parent.name == "tasks", "WP file should stay in tasks/ directory"

    rollback_result = run_tasks_cli(["rollback", feature_slug, "WP01", "--force"], cwd=feature_repo)
    assert_success(rollback_result)

    rolled_wp = locate_work_package(feature_repo, feature_slug, "WP01")
    assert rolled_wp.current_lane == "planned"


def test_update_modifies_frontmatter_only(feature_repo: Path, feature_slug: str) -> None:
    """Test that update only modifies frontmatter, not file location."""
    wp_path = feature_repo / "kitty-specs" / feature_slug / "tasks" / "WP01.md"
    original_text = wp_path.read_text(encoding="utf-8")
    wp_path.write_text(original_text + "\n<!-- reviewer note -->\n", encoding="utf-8")

    result = run_tasks_cli(["update", feature_slug, "WP01", "doing"], cwd=feature_repo)
    assert_success(result)

    # File should still be in same location
    assert wp_path.exists(), "WP file should stay in same location"

    content = wp_path.read_text(encoding="utf-8")
    assert "<!-- reviewer note -->" in content, "Custom content should be preserved"
    assert 'lane: "doing"' in content, "Lane should be updated in frontmatter"


def test_list_command_output(feature_repo: Path, feature_slug: str) -> None:
    result = run_tasks_cli(["list", feature_slug], cwd=feature_repo)
    assert_success(result)
    assert "Lane" in result.stdout
    assert "planned" in result.stdout


def test_history_appends_entry(feature_repo: Path, feature_slug: str) -> None:
    result = run_tasks_cli(
        [
            "history",
            feature_slug,
            "WP01",
            "--note",
            "Follow-up",
            "--lane",
            "planned",
        ],
        cwd=feature_repo,
    )
    assert_success(result)
    wp = locate_work_package(feature_repo, feature_slug, "WP01")
    assert "Follow-up" in wp.body


def test_acceptance_commands(feature_repo: Path, feature_slug: str) -> None:
    # Update to done lane to satisfy acceptance checks.
    run_tasks_cli(["update", feature_slug, "WP01", "doing", "--force"], cwd=feature_repo)
    run(["git", "commit", "-am", "Update to doing"], cwd=feature_repo)
    run_tasks_cli(["update", feature_slug, "WP01", "done", "--force"], cwd=feature_repo)
    run(["git", "commit", "-am", "Update to done"], cwd=feature_repo)

    status = run_tasks_cli(["status", "--feature", feature_slug, "--json"], cwd=feature_repo)
    assert_success(status)
    data = json.loads(status.stdout)
    assert data["feature"] == feature_slug

    verify = run_tasks_cli(["verify", "--feature", feature_slug, "--json", "--lenient"], cwd=feature_repo)
    assert_success(verify)
    verify_data = json.loads(verify.stdout)
    assert "lanes" in verify_data

    accept = run_tasks_cli(
        [
            "accept",
            "--feature",
            feature_slug,
            "--mode",
            "checklist",
            "--json",
            "--no-commit",
            "--allow-fail",
        ],
        cwd=feature_repo,
    )
    assert_success(accept)
    accept_payload = json.loads(accept.stdout)
    assert accept_payload.get("feature") == feature_slug


def _prepare_done_work_package(feature_repo: Path, feature_slug: str) -> None:
    run_tasks_cli(["update", feature_slug, "WP01", "doing", "--force"], cwd=feature_repo)
    run(["git", "commit", "-am", "Update to doing"], cwd=feature_repo)
    run_tasks_cli(["update", feature_slug, "WP01", "done", "--force"], cwd=feature_repo)
    run(["git", "commit", "-am", "Update to done"], cwd=feature_repo)


def test_accept_command_encoding_error_without_normalize(feature_repo: Path, feature_slug: str) -> None:
    _prepare_done_work_package(feature_repo, feature_slug)

    plan_path = feature_repo / "kitty-specs" / feature_slug / "plan.md"
    plan_path.write_bytes(plan_path.read_bytes() + b"\x92")

    result = run_tasks_cli(
        [
            "accept",
            "--feature",
            feature_slug,
            "--mode",
            "checklist",
            "--json",
            "--no-commit",
        ],
        cwd=feature_repo,
    )
    assert result.returncode != 0
    assert "Invalid UTF-8 encoding" in result.stderr


def test_accept_command_with_normalize_flag(feature_repo: Path, feature_slug: str) -> None:
    _prepare_done_work_package(feature_repo, feature_slug)

    plan_path = feature_repo / "kitty-specs" / feature_slug / "plan.md"
    plan_path.write_bytes(plan_path.read_bytes() + b"\x92")

    result = run_tasks_cli(
        [
            "accept",
            "--feature",
            feature_slug,
            "--mode",
            "checklist",
            "--json",
            "--no-commit",
            "--allow-fail",
            "--normalize-encoding",
        ],
        cwd=feature_repo,
    )
    assert result.returncode != 0
    assert "Normalized artifact encoding" in result.stderr
    plan_path.read_text(encoding="utf-8")


def test_scenario_replay(feature_repo: Path, feature_slug: str) -> None:
    # Simulate an agent resolving an unknown, updating through lanes, and finishing back in done.
    run_tasks_cli(["update", feature_slug, "WP01", "doing", "--force"], cwd=feature_repo)
    run(["git", "commit", "-am", "Update to doing"], cwd=feature_repo)
    run_tasks_cli(
        [
            "history",
            feature_slug,
            "WP01",
            "--note",
            "Prototype complete",
            "--lane",
            "doing",
        ],
        cwd=feature_repo,
    )
    run(["git", "commit", "-am", "Add history"], cwd=feature_repo)
    run_tasks_cli(["update", feature_slug, "WP01", "for_review", "--force"], cwd=feature_repo)
    run(["git", "commit", "-am", "Update to review"], cwd=feature_repo)
    run_tasks_cli(["update", feature_slug, "WP01", "done", "--force"], cwd=feature_repo)

    summary = run_tasks_cli(["status", "--feature", feature_slug, "--json"], cwd=feature_repo)
    assert_success(summary)
    data = json.loads(summary.stdout)
    assert data["lanes"]["done"] == ["WP01"]


def test_merge_command_basic(merge_repo: tuple[Path, Path, str]) -> None:
    repo_root, worktree_dir, feature = merge_repo
    result = run_tasks_cli(["merge", "--target", "main"], cwd=worktree_dir)
    assert_success(result)

    assert not worktree_dir.exists()
    branches = run(["git", "branch"], cwd=repo_root)
    assert feature not in branches.stdout
    main_log = run(["git", "log", "--oneline"], cwd=repo_root)
    assert "feature work" in main_log.stdout


def test_merge_command_requires_clean_tree(merge_repo: tuple[Path, Path, str]) -> None:
    repo_root, worktree_dir, feature = merge_repo
    (worktree_dir / "dirty.txt").write_text("dirty", encoding="utf-8")
    result = run_tasks_cli(["merge", "--target", "main"], cwd=worktree_dir)
    assert result.returncode != 0
    assert "uncommitted changes" in result.stderr
    assert worktree_dir.exists()
    branches = run(["git", "branch"], cwd=repo_root)
    assert feature in branches.stdout


def test_merge_command_dry_run(merge_repo: tuple[Path, Path, str]) -> None:
    repo_root, worktree_dir, feature = merge_repo
    result = run_tasks_cli(["merge", "--target", "main", "--dry-run"], cwd=worktree_dir)
    assert_success(result)
    assert worktree_dir.exists()
    branches = run(["git", "branch"], cwd=repo_root)
    assert feature in branches.stdout


def test_packaged_copy_behaves_like_primary(temp_repo: Path) -> None:
    import types

    sys.modules.setdefault("readchar", types.ModuleType("readchar"))
    truststore_stub = types.ModuleType("truststore")
    truststore_stub.SSLContext = ssl.SSLContext
    sys.modules.setdefault("truststore", truststore_stub)
    if str(REPO_ROOT / "src") not in sys.path:
        sys.path.insert(0, str(REPO_ROOT / "src"))
    from src.specify_cli.template.manager import copy_specify_base_from_local

    project_path = temp_repo
    copy_specify_base_from_local(REPO_ROOT, project_path, "sh")

    embedded_cli = project_path / ".kittify" / "scripts" / "tasks" / "tasks_cli.py"
    assert embedded_cli.exists()

    # Seed minimal feature in project path using helper (flat structure).
    feature = "002-packaged"
    write_wp(project_path, feature, "planned", "WP01")
    result = subprocess.run(
        [sys.executable, str(embedded_cli), "list", feature],
        cwd=project_path,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0
    assert "WP01" in result.stdout


def test_refresh_script_upgrades_legacy_copy(temp_repo: Path) -> None:
    """OBSOLETE: Bash scripts removed in v0.10.0 Python rewrite."""
    pytest.skip("Bash scripts were removed in v0.10.0 - test no longer applicable")


# ============================================================================
# Tests for WP ID exact matching (WP04 vs WP04b bug fix)
# ============================================================================


def test_exact_wp_id_matching_not_prefix(feature_repo: Path, feature_slug: str) -> None:
    """Test: WP04 should NOT match WP04b (prefix matching bug).

    GIVEN: Both WP04 and WP04b exist in flat tasks/
    WHEN: Updating WP04 lane
    THEN: Only WP04 should change, WP04b should stay unchanged
    """
    # Create WP04 and WP04b (flat structure)
    write_wp(feature_repo, feature_slug, "planned", "WP04")
    write_wp(feature_repo, feature_slug, "planned", "WP04b")
    run(["git", "add", "."], cwd=feature_repo)
    run(["git", "commit", "-m", "Add WP04 and WP04b"], cwd=feature_repo)

    # Update WP04
    result = run_tasks_cli(["update", feature_slug, "WP04", "doing", "--force"], cwd=feature_repo)
    assert_success(result)

    # Verify WP04 is now "doing"
    wp04 = locate_work_package(feature_repo, feature_slug, "WP04")
    assert wp04.current_lane == "doing", "WP04 should be in doing"

    # Verify WP04b is still "planned"
    wp04b = locate_work_package(feature_repo, feature_slug, "WP04b")
    assert wp04b.current_lane == "planned", "WP04b should still be in planned"


def test_exact_wp_id_matching_with_slug(feature_repo: Path, feature_slug: str) -> None:
    """Test: WP04 matches WP04-slug.md but not WP04b-slug.md.

    GIVEN: WP04-feature.md and WP04b-other.md exist
    WHEN: Updating WP04
    THEN: Only WP04-feature.md should change
    """
    # Create WP files with slugs (flat structure)
    tasks_dir = feature_repo / "kitty-specs" / feature_slug / "tasks"
    write_wp(feature_repo, feature_slug, "planned", "WP04")
    # Rename to have a slug
    (tasks_dir / "WP04.md").rename(tasks_dir / "WP04-feature-name.md")

    write_wp(feature_repo, feature_slug, "planned", "WP04b")
    (tasks_dir / "WP04b.md").rename(tasks_dir / "WP04b-other-feature.md")

    run(["git", "add", "."], cwd=feature_repo)
    run(["git", "commit", "-m", "Add slugged WP files"], cwd=feature_repo)

    # Update WP04
    result = run_tasks_cli(["update", feature_slug, "WP04", "doing", "--force"], cwd=feature_repo)
    assert_success(result)

    # Verify via frontmatter
    wp04 = locate_work_package(feature_repo, feature_slug, "WP04")
    assert wp04.current_lane == "doing", "WP04-feature-name.md should be in doing"

    wp04b = locate_work_package(feature_repo, feature_slug, "WP04b")
    assert wp04b.current_lane == "planned", "WP04b should still be in planned"


# ============================================================================
# Tests for update stages changes properly
# ============================================================================


def test_update_stages_changes(feature_repo: Path, feature_slug: str) -> None:
    """Test: Update command stages the changes for commit."""
    result = run_tasks_cli(["update", feature_slug, "WP01", "doing", "--force"], cwd=feature_repo)
    assert_success(result)

    # Check that changes are staged
    status_result = subprocess.run(["git", "status", "--porcelain"], cwd=feature_repo, capture_output=True, text=True)

    # Should have WP01.md staged (M in first column for modified)
    staged_lines = [line for line in status_result.stdout.strip().split("\n") if line and "WP01" in line]
    assert len(staged_lines) > 0, "WP01 changes should be staged"


# ============================================================================
# Tests for multi-agent scenarios (frontmatter-based)
# ============================================================================


def test_update_ignores_other_wp_modifications(feature_repo: Path, feature_slug: str) -> None:
    """Test: Updating WP01 should not be blocked by modifications to WP02.

    GIVEN: WP02 has uncommitted modifications (simulating another agent's work)
    WHEN: Updating WP01
    THEN: Update should succeed (not blocked by WP02 changes)
    """
    # Create WP02
    write_wp(feature_repo, feature_slug, "planned", "WP02")
    run(["git", "add", "."], cwd=feature_repo)
    run(["git", "commit", "-m", "Add WP02"], cwd=feature_repo)

    # Modify WP02 (simulating another agent editing it)
    wp02_path = feature_repo / "kitty-specs" / feature_slug / "tasks" / "WP02.md"
    original_content = wp02_path.read_text(encoding="utf-8")
    wp02_path.write_text(original_content + "\n<!-- Agent B editing WP02 -->\n", encoding="utf-8")

    # Update WP01 - should NOT be blocked by WP02 modifications
    result = run_tasks_cli(["update", feature_slug, "WP01", "doing", "--force"], cwd=feature_repo)
    assert_success(result)

    # Verify WP01 updated
    wp01 = locate_work_package(feature_repo, feature_slug, "WP01")
    assert wp01.current_lane == "doing", "WP01 should have updated to doing"

    # Verify WP02 still has its modifications
    wp02_content = wp02_path.read_text(encoding="utf-8")
    assert "Agent B editing WP02" in wp02_content, "WP02 modifications should be preserved"


def test_update_with_staged_other_wp_changes(feature_repo: Path, feature_slug: str) -> None:
    """Test: Update succeeds even when other WP files are staged.

    GIVEN: WP02 is staged (modified and git added)
    WHEN: Updating WP01
    THEN: Update should succeed
    """
    # Create WP02
    write_wp(feature_repo, feature_slug, "planned", "WP02")
    run(["git", "add", "."], cwd=feature_repo)
    run(["git", "commit", "-m", "Add WP02"], cwd=feature_repo)

    # Modify and stage WP02
    wp02_path = feature_repo / "kitty-specs" / feature_slug / "tasks" / "WP02.md"
    original_content = wp02_path.read_text(encoding="utf-8")
    wp02_path.write_text(original_content + "\n<!-- Agent B staged WP02 -->\n", encoding="utf-8")
    run(["git", "add", str(wp02_path.relative_to(feature_repo))], cwd=feature_repo)

    # Update WP01 with --force
    result = run_tasks_cli(["update", feature_slug, "WP01", "doing", "--force"], cwd=feature_repo)
    assert_success(result)

    # Verify WP01 updated
    wp01 = locate_work_package(feature_repo, feature_slug, "WP01")
    assert wp01.current_lane == "doing", "WP01 should have updated to doing"


def test_sequential_updates_by_different_agents(feature_repo: Path, feature_slug: str) -> None:
    """Test: Two agents can update their WPs sequentially without conflicts.

    GIVEN: WP01 and WP02 both exist with lane=planned
    WHEN: Agent A updates WP01, then Agent B updates WP02
    THEN: Both updates succeed independently
    """
    # Create WP02
    write_wp(feature_repo, feature_slug, "planned", "WP02")
    run(["git", "add", "."], cwd=feature_repo)
    run(["git", "commit", "-m", "Add WP02"], cwd=feature_repo)

    # Agent A updates WP01
    result_a = run_tasks_cli(["update", feature_slug, "WP01", "doing", "--force"], cwd=feature_repo)
    assert_success(result_a)

    # Agent B updates WP02 (without committing WP01 update first - simulates race)
    result_b = run_tasks_cli(["update", feature_slug, "WP02", "doing", "--force"], cwd=feature_repo)
    assert_success(result_b)

    # Both should be in doing now
    wp01 = locate_work_package(feature_repo, feature_slug, "WP01")
    wp02 = locate_work_package(feature_repo, feature_slug, "WP02")
    assert wp01.current_lane == "doing", "WP01 should be in doing"
    assert wp02.current_lane == "doing", "WP02 should be in doing"
