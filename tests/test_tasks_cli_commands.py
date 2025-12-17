from __future__ import annotations

import json
import ssl
import subprocess
import sys
from pathlib import Path

from tests.utils import REPO_ROOT, run, run_tasks_cli, write_wp
from task_helpers import locate_work_package


def assert_success(result) -> None:
    if result.returncode != 0:
        raise AssertionError(f"Command failed: {result.stderr}\nSTDOUT: {result.stdout}")


def test_move_and_rollback(feature_repo: Path, feature_slug: str) -> None:
    result = run_tasks_cli(["move", feature_slug, "WP01", "doing"], cwd=feature_repo)
    assert_success(result)
    run(["git", "commit", "-am", "Move to doing"], cwd=feature_repo)

    moved_wp = locate_work_package(feature_repo, feature_slug, "WP01")
    assert moved_wp.current_lane == "doing"
    assert 'lane: "doing"' in moved_wp.frontmatter

    rollback_result = run_tasks_cli(["rollback", feature_slug, "WP01", "--force"], cwd=feature_repo)
    assert_success(rollback_result)

    rolled_wp = locate_work_package(feature_repo, feature_slug, "WP01")
    assert rolled_wp.current_lane == "planned"


def test_move_stages_dirty_source(feature_repo: Path, feature_slug: str) -> None:
    wp_path = feature_repo / "kitty-specs" / feature_slug / "tasks" / "planned" / "WP01.md"
    original_text = wp_path.read_text(encoding="utf-8")
    wp_path.write_text(original_text + "\n<!-- reviewer note -->\n", encoding="utf-8")

    result = run_tasks_cli(["move", feature_slug, "WP01", "doing"], cwd=feature_repo)
    assert_success(result)

    planned_copy = feature_repo / "kitty-specs" / feature_slug / "tasks" / "planned" / "WP01.md"
    doing_copy = feature_repo / "kitty-specs" / feature_slug / "tasks" / "doing" / "WP01.md"
    assert not planned_copy.exists()
    assert doing_copy.exists()
    moved_content = doing_copy.read_text(encoding="utf-8")
    assert "<!-- reviewer note -->" in moved_content


def test_move_cleans_stale_target_copy(feature_repo: Path, feature_slug: str) -> None:
    # Move into for_review so the work package lives there.
    assert_success(run_tasks_cli(["move", feature_slug, "WP01", "doing", "--force"], cwd=feature_repo))
    assert_success(run_tasks_cli(["move", feature_slug, "WP01", "for_review", "--force"], cwd=feature_repo))

    wp_for_review = locate_work_package(feature_repo, feature_slug, "WP01")
    assert wp_for_review.current_lane == "for_review"

    planned_path = (
        feature_repo
        / "kitty-specs"
        / feature_slug
        / "tasks"
        / "planned"
        / wp_for_review.relative_subpath
    )
    doing_path = (
        feature_repo
        / "kitty-specs"
        / feature_slug
        / "tasks"
        / "doing"
        / wp_for_review.relative_subpath
    )
    for_review_path = wp_for_review.path

    # Simulate an aborted move that left a duplicate in planned/.
    planned_path.parent.mkdir(parents=True, exist_ok=True)
    planned_path.write_text(for_review_path.read_text(encoding="utf-8"), encoding="utf-8")
    run(["git", "add", str(planned_path.relative_to(feature_repo))], cwd=feature_repo)

    # Update the current file so it has modifications that need staging.
    for_review_path.write_text(
        for_review_path.read_text(encoding="utf-8") + "\n<!-- adjustments -->\n",
        encoding="utf-8",
    )

    # Leave a staged duplicate in doing/ as well.
    doing_path.parent.mkdir(parents=True, exist_ok=True)
    doing_path.write_text(for_review_path.read_text(encoding="utf-8"), encoding="utf-8")
    run(["git", "add", str(doing_path.relative_to(feature_repo))], cwd=feature_repo)

    result = run_tasks_cli(["move", feature_slug, "WP01", "planned"], cwd=feature_repo)
    assert_success(result)

    assert planned_path.exists()
    assert "<!-- adjustments -->" in planned_path.read_text(encoding="utf-8")
    assert not doing_path.exists()
    assert not for_review_path.exists()


def test_move_handles_staged_duplicates(feature_repo: Path, feature_slug: str) -> None:
    # Bring work package into for_review.
    assert_success(run_tasks_cli(["move", feature_slug, "WP01", "doing", "--force"], cwd=feature_repo))
    assert_success(run_tasks_cli(["move", feature_slug, "WP01", "for_review", "--force"], cwd=feature_repo))

    repo_root = feature_repo
    base = repo_root / "kitty-specs" / feature_slug / "tasks"
    for_review_path = base / "for_review" / "WP01.md"
    doing_path = base / "doing" / "WP01.md"

    # Create staged duplicates in doing/ to mimic a half-completed move.
    doing_path.parent.mkdir(parents=True, exist_ok=True)
    doing_path.write_text(for_review_path.read_text(encoding="utf-8"), encoding="utf-8")
    run(["git", "add", str(doing_path.relative_to(repo_root))], cwd=repo_root)
    run(["git", "add", str(for_review_path.relative_to(repo_root))], cwd=repo_root)

    result = run_tasks_cli(["move", feature_slug, "WP01", "done"], cwd=repo_root)
    assert_success(result)

    done_path = base / "done" / "WP01.md"
    assert done_path.exists()
    assert not doing_path.exists()
    assert not for_review_path.exists()

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
    # Move to done lane to satisfy acceptance checks.
    run_tasks_cli(["move", feature_slug, "WP01", "doing", "--force"], cwd=feature_repo)
    run(["git", "commit", "-am", "Move to doing"], cwd=feature_repo)
    run_tasks_cli(["move", feature_slug, "WP01", "done", "--force"], cwd=feature_repo)
    run(["git", "commit", "-am", "Move to done"], cwd=feature_repo)

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
    run_tasks_cli(["move", feature_slug, "WP01", "doing", "--force"], cwd=feature_repo)
    run(["git", "commit", "-am", "Move to doing"], cwd=feature_repo)
    run_tasks_cli(["move", feature_slug, "WP01", "done", "--force"], cwd=feature_repo)
    run(["git", "commit", "-am", "Move to done"], cwd=feature_repo)


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
    # Simulate an agent resolving an unknown, moving through lanes, and finishing back in done.
    run_tasks_cli(["move", feature_slug, "WP01", "doing", "--force"], cwd=feature_repo)
    run(["git", "commit", "-am", "Move to doing"], cwd=feature_repo)
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
    run_tasks_cli(["move", feature_slug, "WP01", "for_review", "--force"], cwd=feature_repo)
    run(["git", "commit", "-am", "Move to review"], cwd=feature_repo)
    run_tasks_cli(["move", feature_slug, "WP01", "done", "--force"], cwd=feature_repo)

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

    # Seed minimal feature in project path using helper.
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
    scripts_root = temp_repo / ".kittify" / "scripts"
    legacy_tasks_dir = scripts_root / "tasks"
    legacy_tasks_dir.mkdir(parents=True, exist_ok=True)

    old_cli = legacy_tasks_dir / "tasks_cli.py"
    old_cli.write_text(
        'from specify_cli.acceptance import perform_acceptance\nprint("legacy")\n',
        encoding="utf-8",
    )

    refresh_script = REPO_ROOT / "scripts" / "bash" / "refresh-kittify-tasks.sh"
    result = subprocess.run(
        [str(refresh_script), str(temp_repo)],
        cwd=temp_repo,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr

    new_cli = legacy_tasks_dir / "tasks_cli.py"
    assert new_cli.exists()
    new_content = new_cli.read_text(encoding="utf-8")
    assert "specify_cli" not in new_content
    assert (legacy_tasks_dir / "task_helpers.py").exists()


# ============================================================================
# Tests for WP ID exact matching (WP04 vs WP04b bug fix)
# ============================================================================

def test_exact_wp_id_matching_not_prefix(feature_repo: Path, feature_slug: str) -> None:
    """Test: WP04 should NOT match WP04b (prefix matching bug).

    GIVEN: Both WP04 and WP04b exist in planned/
    WHEN: Moving WP04 to doing
    THEN: Only WP04 should move, WP04b should stay in planned
    """
    # Create WP04b alongside WP01 (which acts like WP04 for this test)
    write_wp(feature_repo, feature_slug, "planned", "WP04")
    write_wp(feature_repo, feature_slug, "planned", "WP04b")
    run(["git", "add", "."], cwd=feature_repo)
    run(["git", "commit", "-m", "Add WP04 and WP04b"], cwd=feature_repo)

    # Move WP04
    result = run_tasks_cli(["move", feature_slug, "WP04", "doing", "--force"], cwd=feature_repo)
    assert_success(result)

    # WP04 should be in doing
    wp04_doing = feature_repo / "kitty-specs" / feature_slug / "tasks" / "doing" / "WP04.md"
    wp04_planned = feature_repo / "kitty-specs" / feature_slug / "tasks" / "planned" / "WP04.md"
    assert wp04_doing.exists(), "WP04 should be in doing/"
    assert not wp04_planned.exists(), "WP04 should NOT be in planned/"

    # WP04b should still be in planned (not moved)
    wp04b_planned = feature_repo / "kitty-specs" / feature_slug / "tasks" / "planned" / "WP04b.md"
    wp04b_doing = feature_repo / "kitty-specs" / feature_slug / "tasks" / "doing" / "WP04b.md"
    assert wp04b_planned.exists(), "WP04b should still be in planned/"
    assert not wp04b_doing.exists(), "WP04b should NOT be moved to doing/"


def test_exact_wp_id_matching_with_slug(feature_repo: Path, feature_slug: str) -> None:
    """Test: WP04 matches WP04-slug.md but not WP04b-slug.md.

    GIVEN: WP04-feature.md and WP04b-other.md exist
    WHEN: Moving WP04
    THEN: Only WP04-feature.md should move
    """
    # Create WP files with slugs
    planned_dir = feature_repo / "kitty-specs" / feature_slug / "tasks" / "planned"
    write_wp(feature_repo, feature_slug, "planned", "WP04")
    # Rename to have a slug
    (planned_dir / "WP04.md").rename(planned_dir / "WP04-feature-name.md")

    write_wp(feature_repo, feature_slug, "planned", "WP04b")
    (planned_dir / "WP04b.md").rename(planned_dir / "WP04b-other-feature.md")

    run(["git", "add", "."], cwd=feature_repo)
    run(["git", "commit", "-m", "Add slugged WP files"], cwd=feature_repo)

    # Move WP04
    result = run_tasks_cli(["move", feature_slug, "WP04", "doing", "--force"], cwd=feature_repo)
    assert_success(result)

    # WP04-feature-name.md should be in doing
    doing_files = list((feature_repo / "kitty-specs" / feature_slug / "tasks" / "doing").glob("WP04*.md"))
    planned_wp04b = list((feature_repo / "kitty-specs" / feature_slug / "tasks" / "planned").glob("WP04b*.md"))

    assert len(doing_files) == 1, f"Should have exactly one WP04 file in doing. Found: {doing_files}"
    assert "WP04-feature-name.md" in doing_files[0].name, "WP04-feature-name.md should be in doing"
    assert len(planned_wp04b) == 1, "WP04b should still be in planned"


# ============================================================================
# Tests for cleanup not leaving staged deletions
# ============================================================================

def test_cleanup_does_not_leave_staged_deletions(feature_repo: Path, feature_slug: str) -> None:
    """Test: Cleanup should not leave staged deletions that block subsequent moves.

    GIVEN: A WP file exists with a stale copy in another lane
    WHEN: Moving the WP (which triggers cleanup)
    THEN: Git status should be clean after the move (no staged deletions blocking)
    """
    # Move to for_review first
    assert_success(run_tasks_cli(["move", feature_slug, "WP01", "doing", "--force"], cwd=feature_repo))
    run(["git", "commit", "-am", "Move to doing"], cwd=feature_repo)
    assert_success(run_tasks_cli(["move", feature_slug, "WP01", "for_review", "--force"], cwd=feature_repo))
    run(["git", "commit", "-am", "Move to for_review"], cwd=feature_repo)

    # Create a stale copy in planned/ (simulating partial move failure)
    planned_dir = feature_repo / "kitty-specs" / feature_slug / "tasks" / "planned"
    for_review_dir = feature_repo / "kitty-specs" / feature_slug / "tasks" / "for_review"
    planned_dir.mkdir(exist_ok=True)

    stale_copy = planned_dir / "WP01.md"
    original = for_review_dir / "WP01.md"
    stale_copy.write_text(original.read_text(), encoding="utf-8")
    run(["git", "add", str(stale_copy.relative_to(feature_repo))], cwd=feature_repo)

    # Move again - this should trigger cleanup
    result = run_tasks_cli(["move", feature_slug, "WP01", "done", "--force"], cwd=feature_repo)
    assert_success(result)

    # Check git status - should not have staged deletions blocking
    status_result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=feature_repo,
        capture_output=True,
        text=True
    )

    # Filter for WP01-related staged deletions (D in first column)
    staged_deletions = [
        line for line in status_result.stdout.strip().split('\n')
        if line and line[0] == 'D' and 'WP01' in line
    ]

    assert len(staged_deletions) == 0, \
        f"Cleanup should not leave staged deletions. Found: {staged_deletions}"


def test_move_succeeds_after_cleanup_of_duplicate(feature_repo: Path, feature_slug: str) -> None:
    """Test: Move should succeed even when cleanup removes duplicates.

    GIVEN: Duplicates exist across multiple lanes
    WHEN: Moving to a new lane
    THEN: Move succeeds and only one copy exists in target lane
    """
    # Setup: move through lanes
    assert_success(run_tasks_cli(["move", feature_slug, "WP01", "doing", "--force"], cwd=feature_repo))
    run(["git", "commit", "-am", "Move to doing"], cwd=feature_repo)

    # Create duplicates in planned/ and for_review/
    base = feature_repo / "kitty-specs" / feature_slug / "tasks"
    doing_wp = base / "doing" / "WP01.md"
    content = doing_wp.read_text(encoding="utf-8")

    # Duplicate in planned
    planned_dup = base / "planned" / "WP01.md"
    planned_dup.parent.mkdir(exist_ok=True)
    planned_dup.write_text(content, encoding="utf-8")

    # Duplicate in for_review
    review_dup = base / "for_review" / "WP01.md"
    review_dup.parent.mkdir(exist_ok=True)
    review_dup.write_text(content, encoding="utf-8")

    # Stage them
    run(["git", "add", "."], cwd=feature_repo)

    # Move to done - should clean up all duplicates
    result = run_tasks_cli(["move", feature_slug, "WP01", "done", "--force"], cwd=feature_repo)
    assert_success(result)

    # Verify only one copy exists
    all_wp01_files = list(base.rglob("WP01.md"))
    assert len(all_wp01_files) == 1, f"Should have exactly one WP01.md. Found: {all_wp01_files}"
    assert all_wp01_files[0].parent.name == "done", "WP01 should be in done/"


# ============================================================================
# Tests for multi-agent race condition handling
# ============================================================================

def test_move_ignores_other_wp_modifications(feature_repo: Path, feature_slug: str) -> None:
    """Test: Moving WP01 should not be blocked by modifications to WP02.

    GIVEN: WP02 has uncommitted modifications (simulating another agent's work)
    WHEN: Moving WP01
    THEN: Move should succeed (not blocked by WP02 changes)
    """
    # Create WP02
    write_wp(feature_repo, feature_slug, "planned", "WP02")
    run(["git", "add", "."], cwd=feature_repo)
    run(["git", "commit", "-m", "Add WP02"], cwd=feature_repo)

    # Modify WP02 (simulating another agent editing it)
    wp02_path = feature_repo / "kitty-specs" / feature_slug / "tasks" / "planned" / "WP02.md"
    original_content = wp02_path.read_text(encoding="utf-8")
    wp02_path.write_text(original_content + "\n<!-- Agent B editing WP02 -->\n", encoding="utf-8")

    # Move WP01 - should NOT be blocked by WP02 modifications
    result = run_tasks_cli(["move", feature_slug, "WP01", "doing", "--force"], cwd=feature_repo)
    assert_success(result)

    # Verify WP01 moved
    wp01_doing = feature_repo / "kitty-specs" / feature_slug / "tasks" / "doing" / "WP01.md"
    assert wp01_doing.exists(), "WP01 should have moved to doing/"

    # Verify WP02 still has its modifications
    wp02_content = wp02_path.read_text(encoding="utf-8")
    assert "Agent B editing WP02" in wp02_content, "WP02 modifications should be preserved"


def test_move_with_staged_other_wp_changes(feature_repo: Path, feature_slug: str) -> None:
    """Test: Move succeeds even when other WP files are staged.

    GIVEN: WP02 is staged (modified and git added)
    WHEN: Moving WP01
    THEN: Move should succeed (force mode bypasses conflict check for other WPs)
    """
    # Create WP02
    write_wp(feature_repo, feature_slug, "planned", "WP02")
    run(["git", "add", "."], cwd=feature_repo)
    run(["git", "commit", "-m", "Add WP02"], cwd=feature_repo)

    # Modify and stage WP02
    wp02_path = feature_repo / "kitty-specs" / feature_slug / "tasks" / "planned" / "WP02.md"
    original_content = wp02_path.read_text(encoding="utf-8")
    wp02_path.write_text(original_content + "\n<!-- Agent B staged WP02 -->\n", encoding="utf-8")
    run(["git", "add", str(wp02_path.relative_to(feature_repo))], cwd=feature_repo)

    # Move WP01 with --force
    result = run_tasks_cli(["move", feature_slug, "WP01", "doing", "--force"], cwd=feature_repo)
    assert_success(result)

    # Verify WP01 moved
    wp01_doing = feature_repo / "kitty-specs" / feature_slug / "tasks" / "doing" / "WP01.md"
    assert wp01_doing.exists(), "WP01 should have moved to doing/"


def test_sequential_moves_by_different_agents(feature_repo: Path, feature_slug: str) -> None:
    """Test: Two agents can move their WPs sequentially without conflicts.

    GIVEN: WP01 and WP02 both exist in planned
    WHEN: Agent A moves WP01, then Agent B moves WP02
    THEN: Both moves succeed independently
    """
    # Create WP02
    write_wp(feature_repo, feature_slug, "planned", "WP02")
    run(["git", "add", "."], cwd=feature_repo)
    run(["git", "commit", "-m", "Add WP02"], cwd=feature_repo)

    # Agent A moves WP01
    result_a = run_tasks_cli(["move", feature_slug, "WP01", "doing", "--force"], cwd=feature_repo)
    assert_success(result_a)

    # Agent B moves WP02 (without committing WP01 move first - simulates race)
    result_b = run_tasks_cli(["move", feature_slug, "WP02", "doing", "--force"], cwd=feature_repo)
    assert_success(result_b)

    # Both should be in doing
    base = feature_repo / "kitty-specs" / feature_slug / "tasks"
    assert (base / "doing" / "WP01.md").exists(), "WP01 should be in doing/"
    assert (base / "doing" / "WP02.md").exists(), "WP02 should be in doing/"
    assert not (base / "planned" / "WP01.md").exists(), "WP01 should not be in planned/"
    assert not (base / "planned" / "WP02.md").exists(), "WP02 should not be in planned/"
