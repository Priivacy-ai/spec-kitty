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
