"""Task workflow commands for AI agents."""

from __future__ import annotations

import json
import logging
import re
import subprocess
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Tuple, List

import typer
from rich.console import Console
from typing_extensions import Annotated

from specify_cli.sync.events import (
    emit_history_added,
    emit_error_logged,
)

from specify_cli.status.emit import emit_status_transition, TransitionError
from specify_cli.status.transitions import resolve_lane_alias
from specify_cli.status.store import read_events

from specify_cli.core.dependency_graph import build_dependency_graph, get_dependents
from specify_cli.core.paths import locate_project_root, get_main_repo_root, is_worktree_context
from specify_cli.core.feature_detection import (
    detect_feature_slug,
    FeatureDetectionError,
)
from specify_cli.mission import get_feature_mission_key
from specify_cli.git import safe_commit
from specify_cli.tasks_support import (
    LANES,
    append_activity_log,
    build_document,
    ensure_lane,
    extract_scalar,
    locate_work_package,
    set_scalar,
    split_frontmatter,
)


def resolve_primary_branch(repo_root: Path) -> str:
    """Resolve the primary branch name (main, master, etc.).

    Delegates to the centralized implementation in core.git_ops.

    Returns:
        Detected primary branch name.
    """
    from specify_cli.core.git_ops import resolve_primary_branch as _resolve
    return _resolve(repo_root)

logger = logging.getLogger(__name__)

app = typer.Typer(
    name="tasks",
    help="Task workflow commands for AI agents",
    no_args_is_help=True
)

console = Console()


def _ensure_target_branch_checked_out(
    repo_root: Path,
    feature_slug: str,
    json_output: bool,
) -> tuple[Path, str]:
    """Resolve branch context while respecting user's current branch.

    Returns:
        (main_repo_root, active_branch_for_commit)
    """
    from specify_cli.core.git_ops import resolve_target_branch

    from specify_cli.core.git_ops import get_current_branch

    main_repo_root = get_main_repo_root(repo_root)

    # Non-git/mocked contexts (common in unit tests): keep behavior permissive.
    if not (main_repo_root / ".git").exists():
        fallback_branch = "main"
        if not json_output:
            console.print(
                "[yellow]Warning:[/yellow] Git metadata not found; proceeding without branch routing."
            )
        return main_repo_root, fallback_branch

    # Check for detached HEAD using robust branch detection
    current_branch = get_current_branch(main_repo_root)
    if current_branch is None:
        # In edge cases where git metadata exists but branch resolution fails,
        # preserve command operability and let callers continue.
        if not json_output:
            console.print(
                "[yellow]Warning:[/yellow] Could not resolve current branch; using fallback branch routing."
            )
        return main_repo_root, resolve_primary_branch(main_repo_root)

    # Resolve branch routing (respect current branch when user is already on a
    # non-primary branch; allow target routing from primary branch).
    resolution = resolve_target_branch(feature_slug, main_repo_root, current_branch, respect_current=True)
    target_branch = resolution.target
    primary_branch = resolve_primary_branch(main_repo_root)

    # Already on target branch.
    if current_branch == target_branch:
        return main_repo_root, target_branch

    target_exists = subprocess.run(
        ["git", "rev-parse", "--verify", target_branch],
        cwd=main_repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    ).returncode == 0

    if not target_exists:
        if not json_output:
            console.print(
                f"[yellow]Warning:[/yellow] Target branch '{target_branch}' not found. "
                f"Operations will use '{current_branch}'."
            )
        return main_repo_root, current_branch

    # If user is on primary branch, route status operations to target branch.
    if current_branch == primary_branch:
        feature_exists_on_target = subprocess.run(
            ["git", "cat-file", "-e", f"{target_branch}:kitty-specs/{feature_slug}/meta.json"],
            cwd=main_repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        ).returncode == 0

        if not feature_exists_on_target:
            if not json_output:
                console.print(
                    f"[yellow]Warning:[/yellow] Feature '{feature_slug}' not found on "
                    f"target branch '{target_branch}'. Operations will use '{current_branch}'."
                )
            return main_repo_root, current_branch

        checkout = subprocess.run(
            ["git", "checkout", target_branch],
            cwd=main_repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if checkout.returncode == 0:
            if not json_output:
                console.print(f"[cyan]→ Switched to target branch '{target_branch}'[/cyan]")
            return main_repo_root, target_branch

        if not json_output:
            console.print(
                f"[yellow]Warning:[/yellow] Could not checkout target branch '{target_branch}'. "
                f"Operations will use '{current_branch}'."
            )
        return main_repo_root, current_branch

    if not json_output:
        console.print(
            f"[yellow]Note:[/yellow] You are on '{current_branch}', "
            f"feature targets '{target_branch}'. Operations will use '{current_branch}'."
        )
    return main_repo_root, current_branch


def _display_lane(lane: str) -> str:
    """Map canonical lane names to legacy-facing labels."""
    return "doing" if resolve_lane_alias(lane) == "in_progress" else lane


def _find_feature_slug(explicit_feature: str | None = None) -> str:
    """Find the current feature slug using centralized detection.

    Args:
        explicit_feature: Optional explicit feature slug from --feature flag

    Returns:
        Feature slug (e.g., "008-unified-python-cli")

    Raises:
        typer.Exit: If feature slug cannot be determined
    """
    cwd = Path.cwd().resolve()
    repo_root = locate_project_root(cwd)

    if repo_root is None:
        raise typer.Exit(1)

    try:
        return detect_feature_slug(
            repo_root,
            explicit_feature=explicit_feature,
            cwd=cwd,
            mode="strict"
        )
    except FeatureDetectionError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


def _output_result(
    json_mode: bool,
    data: dict[str, Any],
    success_message: str | None = None,
) -> None:
    """Output result in JSON or human-readable format.

    Args:
        json_mode: If True, output JSON; else use Rich console
        data: Data to output (used for JSON mode)
        success_message: Message to display in human mode
    """
    if json_mode:
        print(json.dumps(data))
    elif success_message:
        console.print(success_message)


def _output_error(json_mode: bool, error_message: str) -> None:
    """Output error in JSON or human-readable format.

    Args:
        json_mode: If True, output JSON; else use Rich console
        error_message: Error message to display
    """
    if json_mode:
        print(json.dumps({"error": error_message}))
    else:
        console.print(f"[red]Error:[/red] {error_message}")


def _check_unchecked_subtasks(
    repo_root: Path,
    feature_slug: str,
    wp_id: str,
    force: bool
) -> list[str]:
    """Check for unchecked subtasks in tasks.md for a given WP.

    Args:
        repo_root: Repository root path
        feature_slug: Feature slug (e.g., "010-workspace-per-wp")
        wp_id: Work package ID (e.g., "WP01")
        force: If True, only warn; if False, fail on unchecked tasks

    Returns:
        List of unchecked task IDs (empty if all checked or not found)

    Raises:
        typer.Exit: If unchecked tasks found and force=False
    """
    # Use planning repo root (worktrees have kitty-specs/ sparse-checked out)
    main_repo_root = get_main_repo_root(repo_root)
    feature_dir = main_repo_root / "kitty-specs" / feature_slug
    tasks_md = feature_dir / "tasks.md"

    if not tasks_md.exists():
        return []  # No tasks.md, can't check

    content = tasks_md.read_text(encoding="utf-8")

    # Find subtasks for this WP (looking for - [ ] or - [x] checkboxes under WP section)
    lines = content.split('\n')
    unchecked = []
    in_wp_section = False

    for line in lines:
        # Check if we entered this WP's section
        if re.search(rf'##.*{wp_id}\b', line):
            in_wp_section = True
            continue

        # Check if we entered a different WP section
        if in_wp_section and re.search(r'##.*WP\d{2}\b', line):
            break  # Left this WP's section

        # Look for unchecked tasks in this WP's section
        if in_wp_section:
            # Match patterns like: - [ ] T001 or - [ ] Task description
            unchecked_match = re.match(r'-\s*\[\s*\]\s*(T\d{3}|.*)', line.strip())
            if unchecked_match:
                task_id = unchecked_match.group(1).split()[0] if unchecked_match.group(1) else line.strip()
                unchecked.append(task_id)

    return unchecked


def _check_dependent_warnings(
    repo_root: Path,
    feature_slug: str,
    wp_id: str,
    target_lane: str,
    json_mode: bool
) -> None:
    """Display warning when WP moves to for_review and has incomplete dependents.

    Args:
        repo_root: Repository root path
        feature_slug: Feature slug (e.g., "010-workspace-per-wp")
        wp_id: Work package ID (e.g., "WP01")
        target_lane: Target lane being moved to
        json_mode: If True, suppress Rich console output
    """
    # Only warn when moving to for_review
    if target_lane != "for_review":
        return

    # Don't show warnings in JSON mode
    if json_mode:
        return

    # Use planning repo root (worktrees have kitty-specs/ sparse-checked out)
    main_repo_root = get_main_repo_root(repo_root)
    feature_dir = main_repo_root / "kitty-specs" / feature_slug

    # Build dependency graph
    try:
        graph = build_dependency_graph(feature_dir)
    except Exception:
        # If we can't build the graph, skip warnings
        return

    # Get dependents
    dependents = get_dependents(wp_id, graph)
    if not dependents:
        return  # No dependents, no warnings

    # Check if any dependents are incomplete (not yet done)
    incomplete = []
    for dep_id in dependents:
        try:
            # Find dependent WP file
            tasks_dir = feature_dir / "tasks"
            dep_files = list(tasks_dir.glob(f"{dep_id}-*.md"))
            if not dep_files:
                continue

            # Read frontmatter
            content = dep_files[0].read_text(encoding="utf-8-sig")
            frontmatter, _, _ = split_frontmatter(content)
            lane = extract_scalar(frontmatter, "lane") or "planned"

            if lane in ["planned", "doing"]:
                incomplete.append(dep_id)
        except Exception:
            # Skip if we can't read the dependent
            continue

    if incomplete:
        console.print("\n[yellow]⚠️  Dependency Alert[/yellow]")
        console.print(f"{', '.join(incomplete)} depend on {wp_id} (not yet done)")
        console.print("\nIf changes are requested during review:")
        console.print("  1. Notify dependent WP agents")
        console.print("  2. Dependent WPs will need manual rebase after changes")
        for dep in incomplete:
            console.print(f"     cd .worktrees/{feature_slug}-{dep} && git rebase {feature_slug}-{wp_id}")
        console.print()


def _behind_commits_touch_only_planning_artifacts(
    worktree_path: Path,
    check_branch: str,
    feature_slug: str,
) -> bool:
    """Return True when upstream commits only touch planning/status files.

    This prevents lane transitions from being blocked by commits that update
    task metadata on the planning branch (for example mark-status/move-task).
    """
    merge_base_result = subprocess.run(
        ["git", "merge-base", "HEAD", check_branch],
        cwd=worktree_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if merge_base_result.returncode != 0:
        return False

    merge_base = merge_base_result.stdout.strip()
    if not merge_base:
        return False

    # Compare merge-base..base to inspect only commits that HEAD is behind on.
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{merge_base}..{check_branch}"],
        cwd=worktree_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        return False

    changed_files = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not changed_files:
        return True

    allowed_prefixes = (
        f"kitty-specs/{feature_slug}/",
        ".kittify/workspaces/",
    )
    allowed_exact_paths = {
        ".kittify/config.yaml",
        ".kittify/config.yml",
    }
    return all(
        path.startswith(allowed_prefixes) or path in allowed_exact_paths
        for path in changed_files
    )


def _maybe_mirror_move_commit_to_wp_branch(
    cwd: Path,
    main_repo_root: Path,
    feature_slug: str,
    wp_id: str,
    main_wp_path: Path,
    updated_doc: str,
    commit_message: str,
) -> bool:
    """Mirror lane transition commit into active WP branch when in its worktree.

    Move-task updates planning artifacts on the planning branch by design.
    When agents run from a WP worktree, mirror the same status change commit
    into the active WP branch to keep branch history aligned with lane changes.
    """
    from specify_cli.core.git_ops import get_current_branch

    if not is_worktree_context(cwd):
        return False

    # Resolve enclosing worktree root from current directory.
    worktree_root: Path | None = None
    for candidate in [cwd, *cwd.parents]:
        if candidate == main_repo_root:
            break
        if (candidate / ".git").is_file():
            worktree_root = candidate
            break
    if worktree_root is None:
        return False

    expected_branch = f"{feature_slug}-{wp_id}"
    current_branch = get_current_branch(worktree_root)
    if current_branch != expected_branch:
        return False

    try:
        rel_wp_path = main_wp_path.resolve().relative_to(main_repo_root.resolve())
    except ValueError:
        return False

    checkout_result = subprocess.run(
        [
            "git",
            "checkout",
            "--ignore-skip-worktree-bits",
            "HEAD",
            "--",
            str(rel_wp_path),
        ],
        cwd=worktree_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if checkout_result.returncode != 0:
        return False

    wp_branch_path = worktree_root / rel_wp_path
    wp_branch_path.parent.mkdir(parents=True, exist_ok=True)
    wp_branch_path.write_text(updated_doc, encoding="utf-8")

    add_result = subprocess.run(
        ["git", "add", "--sparse", str(rel_wp_path)],
        cwd=worktree_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if add_result.returncode != 0:
        # Fallback for older Git versions without --sparse support.
        if "unknown option" in (add_result.stderr or "").lower():
            add_result = subprocess.run(
                ["git", "add", str(rel_wp_path)],
                cwd=worktree_root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
    if add_result.returncode != 0:
        subprocess.run(
            ["git", "restore", "--worktree", "--staged", str(rel_wp_path)],
            cwd=worktree_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        return False

    commit_result = subprocess.run(
        ["git", "commit", "-m", commit_message],
        cwd=worktree_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if commit_result.returncode == 0:
        return True
    if "nothing to commit" in (commit_result.stdout or "") or "nothing to commit" in (commit_result.stderr or ""):
        return True

    subprocess.run(
        ["git", "restore", "--worktree", "--staged", str(rel_wp_path)],
        cwd=worktree_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return False


def _validate_ready_for_review(
    repo_root: Path,
    feature_slug: str,
    wp_id: str,
    force: bool
) -> Tuple[bool, List[str]]:
    """Validate that WP is ready for review by checking for uncommitted changes.

    For research missions: Checks for uncommitted research artifacts in planning repo.
    For software-dev missions: Checks for uncommitted changes in worktree AND
    verifies at least one implementation commit exists.

    Args:
        repo_root: Repository root path (could be main or worktree)
        feature_slug: Feature slug (e.g., "010-workspace-per-wp")
        wp_id: Work package ID (e.g., "WP01")
        force: If True, skip validation (return success)

    Returns:
        Tuple of (is_valid, guidance_messages)
        - is_valid: True if ready for review, False if blocked
        - guidance_messages: List of actionable instructions if blocked
    """
    if force:
        return True, []

    guidance: List[str] = []
    main_repo_root = get_main_repo_root(repo_root)
    feature_dir = main_repo_root / "kitty-specs" / feature_slug

    # Detect mission type from feature's meta.json
    mission_key = get_feature_mission_key(feature_dir)

    # Check 1: Uncommitted research artifacts in planning repo (applies to ALL missions)
    # Research artifacts live in kitty-specs/ which is in the planning repo, not worktrees
    result = subprocess.run(
        ["git", "status", "--porcelain", str(feature_dir)],
        cwd=main_repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False
    )
    uncommitted_in_main = result.stdout.strip()

    if uncommitted_in_main:
        # Filter out WP status files (tasks/*.md) - those are auto-committed by move-task
        # We care about research artifacts: data-model.md, research/*.csv, etc.
        research_files = []
        for line in uncommitted_in_main.split("\n"):
            if not line.strip():
                continue
            # Extract filename from git status output (e.g., " M path/to/file" or "?? path")
            file_part = line[3:] if len(line) > 3 else line.strip()
            # Skip WP status files in tasks/ - move-task handles those
            if "/tasks/" in file_part and file_part.endswith(".md"):
                continue
            # Skip canonical status/telemetry artifacts - auto-generated by emit pipeline
            if file_part.endswith("status.events.jsonl") or file_part.endswith("status.json"):
                continue
            if file_part.endswith("execution.events.jsonl") or file_part.endswith(".telemetry-clock.json"):
                continue
            research_files.append(line)

        if research_files:
            guidance.append("Uncommitted research outputs detected in planning repo!")
            guidance.append("")
            guidance.append("Modified files in kitty-specs/:")
            for line in research_files[:5]:  # Show first 5 files
                guidance.append(f"  {line}")
            if len(research_files) > 5:
                guidance.append(f"  ... and {len(research_files) - 5} more")
            guidance.append("")
            guidance.append("You must commit these before moving to for_review:")
            guidance.append(f"  cd {main_repo_root}")
            guidance.append(f"  git add kitty-specs/{feature_slug}/")
            if mission_key == "research":
                guidance.append(f"  git commit -m \"research({wp_id}): <describe your research outputs>\"")
            else:
                guidance.append(f"  git commit -m \"docs({wp_id}): <describe your changes>\"")
            guidance.append("")
            guidance.append(f"Then retry: spec-kitty agent tasks move-task {wp_id} --to for_review")
            return False, guidance

    # Check 2: For software-dev missions, check worktree for implementation commits
    if mission_key == "software-dev":
        worktree_path = main_repo_root / ".worktrees" / f"{feature_slug}-{wp_id}"

        if worktree_path.exists():
            # Check for detached HEAD before other git status checks, but only
            # when this is a real git worktree (unit tests often use plain dirs).
            if (worktree_path / ".git").exists():
                from specify_cli.core.git_ops import get_current_branch as _get_branch
                wt_branch = _get_branch(worktree_path)
                if wt_branch is None:
                    guidance.append("Detached HEAD detected in worktree!")
                    guidance.append("")
                    guidance.append("Please reattach to a branch before review:")
                    guidance.append(f"  cd {worktree_path}")
                    guidance.append("  git checkout <your-branch>")
                    guidance.append("")
                    guidance.append(f"Then retry: spec-kitty agent tasks move-task {wp_id} --to for_review")
                    return False, guidance

            # Check for in-progress git operations (merge/rebase/cherry-pick)
            in_progress = []
            state_checks = {
                "MERGE_HEAD": "merge",
                "REBASE_HEAD": "rebase",
                "CHERRY_PICK_HEAD": "cherry-pick",
            }
            for ref, label in state_checks.items():
                state_result = subprocess.run(
                    ["git", "rev-parse", "-q", "--verify", ref],
                    cwd=worktree_path,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    check=False
                )
                if state_result.returncode == 0:
                    in_progress.append(label)

            if in_progress:
                guidance.append("In-progress git operation detected in worktree!")
                guidance.append("")
                guidance.append(f"Active operation(s): {', '.join(in_progress)}")
                guidance.append("")
                guidance.append("Resolve or abort before review:")
                guidance.append(f"  cd {worktree_path}")
                guidance.append("  git status")
                guidance.append("  git merge --abort   # if merge")
                guidance.append("  git rebase --abort  # if rebase")
                guidance.append("  git cherry-pick --abort  # if cherry-pick")
                guidance.append("")
                guidance.append(f"Then retry: spec-kitty agent tasks move-task {wp_id} --to for_review")
                return False, guidance

            # Check if worktree branch is behind its base branch
            # For stacked WPs (WP03 based on WP01), check against WP01's branch, not main
            from specify_cli.core.feature_detection import get_feature_target_branch
            from specify_cli.workspace_context import load_context
            target_branch = get_feature_target_branch(repo_root, feature_slug)

            # Resolve actual base: workspace context tracks the real base branch
            workspace_name = f"{feature_slug}-{wp_id}"
            ws_context = load_context(main_repo_root, workspace_name)
            check_branch = ws_context.base_branch if ws_context else target_branch

            result = subprocess.run(
                ["git", "rev-list", "--count", f"HEAD..{check_branch}"],
                cwd=worktree_path,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False
            )
            behind_count = 0
            if result.returncode == 0 and result.stdout.strip():
                try:
                    behind_count = int(result.stdout.strip())
                except ValueError:
                    behind_count = 0

            if behind_count > 0:
                # Allow status/planning-only commits to avoid repeated rebase friction.
                if not _behind_commits_touch_only_planning_artifacts(
                    worktree_path,
                    check_branch,
                    feature_slug,
                ):
                    guidance.append(f"{check_branch} branch has new commits not in this worktree!")
                    guidance.append("")
                    guidance.append(f"Your branch is behind {check_branch} by {behind_count} commit(s).")
                    guidance.append("Rebase before review:")
                    guidance.append(f"  cd {worktree_path}")
                    guidance.append(f"  git rebase {check_branch}")
                    guidance.append("")
                    guidance.append(f"Then retry: spec-kitty agent tasks move-task {wp_id} --to for_review")
                    return False, guidance

            # Check for uncommitted changes in worktree
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=worktree_path,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False
            )
            uncommitted_in_worktree = result.stdout.strip()

            if uncommitted_in_worktree:
                staged_lines = []
                unstaged_lines = []
                for line in uncommitted_in_worktree.split("\n"):
                    if not line.strip():
                        continue
                    if line.startswith("??"):
                        unstaged_lines.append(line)
                        continue
                    status = line[:2]
                    if status[0] != " ":
                        staged_lines.append(line)
                    if status[1] != " ":
                        unstaged_lines.append(line)

                if staged_lines and not unstaged_lines:
                    guidance.append("Staged but uncommitted changes in worktree!")
                elif staged_lines and unstaged_lines:
                    guidance.append("Staged and unstaged changes in worktree!")
                else:
                    guidance.append("Uncommitted implementation changes in worktree!")
                guidance.append("")
                guidance.append("Modified files:")
                for line in uncommitted_in_worktree.split("\n")[:5]:
                    guidance.append(f"  {line}")
                guidance.append("")
                guidance.append("Commit your work first:")
                guidance.append(f"  cd {worktree_path}")
                guidance.append("  git add -A")
                guidance.append(f"  git commit -m \"feat({wp_id}): <describe implementation>\"")
                guidance.append("")
                guidance.append(f"Then retry: spec-kitty agent tasks move-task {wp_id} --to for_review")
                return False, guidance

            # Check if branch has commits beyond base (use actual base, not target)
            result = subprocess.run(
                ["git", "rev-list", "--count", f"{check_branch}..HEAD"],
                cwd=worktree_path,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False
            )
            commit_count = 0
            if result.returncode == 0 and result.stdout.strip():
                try:
                    commit_count = int(result.stdout.strip())
                except ValueError:
                    pass

            if commit_count == 0:
                guidance.append("No implementation commits on WP branch!")
                guidance.append("")
                guidance.append(f"The worktree exists but has no commits beyond {check_branch}.")
                guidance.append("Either:")
                guidance.append("  1. Commit your implementation work to the worktree")
                guidance.append("  2. Or verify work is complete (use --force if nothing to commit)")
                guidance.append("")
                guidance.append(f"  cd {worktree_path}")
                guidance.append("  git add -A")
                guidance.append(f"  git commit -m \"feat({wp_id}): <describe implementation>\"")
                guidance.append("")
                guidance.append(f"Then retry: spec-kitty agent tasks move-task {wp_id} --to for_review")
                return False, guidance

    return True, []


@app.command(name="move-task")
def move_task(
    task_id: Annotated[str, typer.Argument(help="Task ID (e.g., WP01)")],
    to: Annotated[str, typer.Option("--to", help="Target lane (planned/doing/for_review/done)")],
    feature: Annotated[Optional[str], typer.Option("--feature", help="Feature slug (auto-detected if omitted)")] = None,
    agent: Annotated[Optional[str], typer.Option("--agent", help="Agent name")] = None,
    assignee: Annotated[Optional[str], typer.Option("--assignee", help="Assignee name (sets assignee when moving to doing)")] = None,
    shell_pid: Annotated[Optional[str], typer.Option("--shell-pid", help="Shell PID")] = None,
    note: Annotated[Optional[str], typer.Option("--note", help="History note")] = None,
    review_feedback_file: Annotated[Optional[Path], typer.Option("--review-feedback-file", help="Path to review feedback file (required when moving to planned from review)")] = None,
    approval_ref: Annotated[Optional[str], typer.Option("--approval-ref", help="Approval reference for done transitions (e.g., PR#42)")] = None,
    reviewer: Annotated[Optional[str], typer.Option("--reviewer", help="Reviewer name (auto-detected from git if omitted)")] = None,
    force: Annotated[bool, typer.Option("--force", help="Force move even with unchecked subtasks or missing feedback")] = False,
    auto_commit: Annotated[bool, typer.Option("--auto-commit/--no-auto-commit", help="Automatically commit WP file changes to target branch")] = True,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON format")] = False,
    # Telemetry options for ExecutionEvent emission
    model: Annotated[Optional[str], typer.Option("--model", help="LLM model used (for telemetry)")] = None,
    input_tokens: Annotated[Optional[int], typer.Option("--input-tokens", help="Input token count (for telemetry)")] = None,
    output_tokens: Annotated[Optional[int], typer.Option("--output-tokens", help="Output token count (for telemetry)")] = None,
    cost_usd: Annotated[Optional[float], typer.Option("--cost-usd", help="Cost in USD (for telemetry)")] = None,
    duration_ms: Annotated[Optional[int], typer.Option("--duration-ms", help="Execution duration in milliseconds (for telemetry)")] = None,
) -> None:
    """Move task between lanes (planned → doing → for_review → done).

    Emits ExecutionEvent for telemetry when moving to for_review (implementation)
    or done (review), enabling cost tracking even in human-in-the-loop workflows.

    Examples:
        spec-kitty agent tasks move-task WP01 --to doing --assignee claude --json
        spec-kitty agent tasks move-task WP02 --to for_review --agent claude --model claude-sonnet-4.5
        spec-kitty agent tasks move-task WP03 --to done --note "Review passed" --agent codex
        spec-kitty agent tasks move-task WP03 --to planned --review-feedback-file feedback.md
    """
    try:
        # Validate lane
        target_lane = ensure_lane(to)

        # Get repo root and feature slug
        repo_root = locate_project_root()
        if repo_root is None:
            _output_error(json_output, "Could not locate project root")
            raise typer.Exit(1)

        feature_slug = _find_feature_slug(explicit_feature=feature)

        # Ensure we operate on the target branch for this feature
        main_repo_root, target_branch = _ensure_target_branch_checked_out(repo_root, feature_slug, json_output)

        # Informational: Let user know we're using planning repo's kitty-specs
        cwd = Path.cwd().resolve()
        if is_worktree_context(cwd) and not json_output:
            if cwd != main_repo_root:
                # Check if worktree has its own kitty-specs (stale copy)
                worktree_kitty = None
                current = cwd
                while current != current.parent and ".worktrees" in str(current):
                    if (current / "kitty-specs").exists():
                        worktree_kitty = current / "kitty-specs"
                        break
                    current = current.parent

                if worktree_kitty and (worktree_kitty / feature_slug / "tasks").exists():
                    console.print(
                        f"[dim]Note: Using planning repo's kitty-specs/ on {target_branch} (worktree copy ignored)[/dim]"
                    )

        # Load work package first (needed for current_lane check)
        wp = locate_work_package(repo_root, feature_slug, task_id)
        old_lane = wp.current_lane

        # AGENT OWNERSHIP CHECK: Warn if agent doesn't match WP's current agent
        # This helps prevent agents from accidentally modifying WPs they don't own
        current_agent = extract_scalar(wp.frontmatter, "agent")
        if current_agent and agent and current_agent != agent and not force:
            if not json_output:
                console.print()
                console.print("[bold red]⚠️  AGENT OWNERSHIP WARNING[/bold red]")
                console.print(f"   {task_id} is currently assigned to: [cyan]{current_agent}[/cyan]")
                console.print(f"   You are trying to move it as: [yellow]{agent}[/yellow]")
                console.print()
                console.print("   If you are the correct agent, use --force to override.")
                console.print("   If not, you may be modifying the wrong WP!")
                console.print()
            _output_error(json_output, f"Agent mismatch: {task_id} is assigned to '{current_agent}', not '{agent}'. Use --force to override.")
            raise typer.Exit(1)

        # Validate review feedback when moving to planned (likely from review)
        if target_lane == "planned" and old_lane == "for_review" and not review_feedback_file and not force:
            error_msg = f"❌ Moving {task_id} from 'for_review' to 'planned' requires review feedback.\n\n"
            error_msg += "Please provide feedback:\n"
            error_msg += "  1. Create feedback file: echo '**Issue**: Description' > feedback.md\n"
            error_msg += f"  2. Run: spec-kitty agent tasks move-task {task_id} --to planned --review-feedback-file feedback.md\n\n"
            error_msg += "OR use --force to skip feedback (not recommended)"
            _output_error(json_output, error_msg)
            raise typer.Exit(1)

        # Validate subtasks are complete when moving to for_review or done (Issue #72)
        if target_lane in ("for_review", "done") and not force:
            unchecked = _check_unchecked_subtasks(repo_root, feature_slug, task_id, force)
            if unchecked:
                error_msg = f"Cannot move {task_id} to {target_lane} - unchecked subtasks:\n"
                for task in unchecked:
                    error_msg += f"  - [ ] {task}\n"
                error_msg += "\nMark these complete first:\n"
                for task in unchecked[:3]:  # Show first 3 examples
                    task_clean = task.split()[0] if ' ' in task else task
                    error_msg += f"  spec-kitty agent tasks mark-status {task_clean} --status done\n"
                error_msg += "\nOr use --force to override (not recommended)"
                _output_error(json_output, error_msg)
                raise typer.Exit(1)

        # Validate uncommitted changes when moving to for_review OR done
        # This catches the bug where agents edit artifacts but forget to commit
        if target_lane in ("for_review", "done"):
            is_valid, guidance = _validate_ready_for_review(repo_root, feature_slug, task_id, force)
            if not is_valid:
                error_msg = f"Cannot move {task_id} to {target_lane}\n\n"
                error_msg += "\n".join(guidance)
                if not force:
                    error_msg += "\n\nOr use --force to override (not recommended)"
                _output_error(json_output, error_msg)
                raise typer.Exit(1)

        # --- Canonical emit pipeline (WP09 delegation) ---
        # Build evidence dict for done transitions
        evidence_dict = None
        if target_lane == "done":
            # Auto-detect reviewer if not provided
            effective_reviewer = reviewer
            if not effective_reviewer:
                try:
                    git_user_result = subprocess.run(
                        ["git", "config", "user.name"],
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        check=True
                    )
                    effective_reviewer = git_user_result.stdout.strip() or "unknown"
                except (subprocess.CalledProcessError, FileNotFoundError):
                    effective_reviewer = "unknown"
            effective_approval_ref = approval_ref
            if not effective_approval_ref and note:
                effective_approval_ref = note
            if not effective_approval_ref:
                effective_approval_ref = (
                    f"auto-approval:{task_id}:{datetime.now(timezone.utc).strftime('%Y%m%d')}"
                )
            evidence_dict = {
                "review": {
                    "reviewer": effective_reviewer,
                    "verdict": "approved",
                    "reference": effective_approval_ref or "force-override",
                },
            }

        # Build review_ref for for_review -> in_progress transitions
        emit_review_ref = None
        if old_lane == "for_review" and resolve_lane_alias(target_lane) in ("in_progress", "planned"):
            if review_feedback_file and review_feedback_file.exists():
                emit_review_ref = str(review_feedback_file)
            elif force:
                emit_review_ref = "force-override"
            else:
                # Backward compatibility: allow rework moves without forcing users
                # to provide a file path. Keep an auditable reference in the event.
                emit_review_ref = note or "review-feedback:unspecified"

        # Map --agent to actor; default to "user" if not provided
        actor = agent or "user"

        # Build reason for emit (used by force transitions and some guards)
        emit_reason = note if note else None
        if force and not emit_reason:
            emit_reason = f"Force move to {target_lane}"

        # Resolve the canonical lane for the emit pipeline
        canonical_lane = resolve_lane_alias(target_lane)

        # Determine feature_dir for the event store
        feature_dir = main_repo_root / "kitty-specs" / feature_slug

        # Keep force semantics strict: only user-requested --force should bypass guards.
        emit_force = force
        if not emit_reason:
            if force:
                emit_reason = f"Force move to {target_lane}"
            else:
                emit_reason = f"move-task: {old_lane} -> {target_lane}"

        def _lane_targets_for_emit(current_lane: str, requested_lane: str) -> list[str]:
            current = resolve_lane_alias(current_lane)
            target = resolve_lane_alias(requested_lane)
            forward = ["planned", "claimed", "in_progress", "for_review", "done"]
            if current in forward and target in forward:
                current_idx = forward.index(current)
                target_idx = forward.index(target)
                if target_idx > current_idx:
                    return forward[current_idx + 1: target_idx + 1]
            return [target]

        transition_targets = [canonical_lane]
        if not emit_force:
            transition_targets = _lane_targets_for_emit(old_lane, canonical_lane)

        event = None
        current_canonical_lane = resolve_lane_alias(old_lane)
        current_event_lane = None
        for existing_event in reversed(read_events(feature_dir)):
            if existing_event.wp_id == task_id:
                current_event_lane = str(existing_event.to_lane)
                break
        if (
            current_event_lane is None
            and current_canonical_lane != "planned"
        ):
            # Seed canonical history from frontmatter so strict transitions can continue.
            emit_status_transition(
                feature_dir=feature_dir,
                feature_slug=feature_slug,
                wp_id=task_id,
                to_lane=current_canonical_lane,
                actor=actor,
                force=True,
                reason=(
                    "bootstrap from frontmatter lane "
                    f"{current_canonical_lane} before move-task transition"
                ),
                workspace_context=f"move-task:{main_repo_root}",
                subtasks_complete=True if current_canonical_lane == "for_review" else None,
                implementation_evidence_present=(
                    True if current_canonical_lane == "for_review" else None
                ),
                repo_root=main_repo_root,
            )

        for target in transition_targets:
            event = emit_status_transition(
                feature_dir=feature_dir,
                feature_slug=feature_slug,
                wp_id=task_id,
                to_lane=target,
                actor=actor,
                force=emit_force,
                reason=emit_reason,
                evidence=evidence_dict if target == "done" else None,
                review_ref=emit_review_ref,
                workspace_context=f"move-task:{main_repo_root}",
                subtasks_complete=(
                    True
                    if target == "for_review" and not emit_force
                    else None
                ),
                implementation_evidence_present=(
                    True
                    if target == "for_review" and not emit_force
                    else None
                ),
                repo_root=main_repo_root,
            )
            # review_ref only applies to rollback transitions, never to forward chain hops
            emit_review_ref = None

        if event is None:
            raise TransitionError("No status transition event was emitted")

        # --- Emit ExecutionEvent for telemetry (fire-and-forget) ---
        # Emit when moving to for_review (implementation) or done (review)
        try:
            from specify_cli.telemetry.emit import emit_execution_event

            effective_agent = agent or extract_scalar(wp.frontmatter, "agent") or "unknown"
            
            # Determine role and success based on transition
            role = None
            success = True
            
            if canonical_lane == "for_review" and old_lane == "in_progress":
                # Implementation complete
                role = "implementer"
                success = True
            elif canonical_lane == "done" and old_lane == "for_review":
                # Review complete (approval)
                role = "reviewer"
                success = True
            elif canonical_lane in ("in_progress", "planned") and old_lane == "for_review":
                # Review complete (changes requested) - still counts as review work
                role = "reviewer"
                success = False  # Changes requested, not approved
            
            # Only emit if we have a role (meaningful transition for telemetry)
            if role:
                emit_execution_event(
                    feature_dir=feature_dir,
                    feature_slug=feature_slug,
                    wp_id=task_id,
                    agent=effective_agent,
                    role=role,
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost_usd=cost_usd,
                    duration_ms=duration_ms or 0,
                    success=success,
                    error=None,
                    exit_code=0 if success else 1,
                )
        except Exception as e:
            # Fire-and-forget: log but don't fail the transition
            logger.warning(f"Failed to emit ExecutionEvent: {e}")

        # --- Post-emit: apply metadata fields to WP file ---
        # The emit pipeline (via legacy_bridge) may have updated the lane
        # in frontmatter. Re-read the file to get the current state,
        # then apply additional metadata fields that are NOT part of
        # the canonical event.
        wp_content = wp.path.read_text(encoding="utf-8-sig")
        updated_front, updated_body, updated_padding = split_frontmatter(wp_content)

        # Ensure lane is set (in case legacy_bridge didn't update it)
        updated_front = set_scalar(updated_front, "lane", canonical_lane)

        # Update assignee if provided
        if assignee:
            updated_front = set_scalar(updated_front, "assignee", assignee)

        # Update agent if provided
        if agent:
            updated_front = set_scalar(updated_front, "agent", agent)

        # Update shell_pid if provided
        if shell_pid:
            updated_front = set_scalar(updated_front, "shell_pid", shell_pid)

        # Handle review feedback insertion if moving to planned with feedback
        if review_feedback_file and review_feedback_file.exists():
            feedback_content = review_feedback_file.read_text(encoding="utf-8").strip()

            # Auto-detect reviewer if not provided
            effective_reviewer = reviewer
            if not effective_reviewer:
                try:
                    git_user_result = subprocess.run(
                        ["git", "config", "user.name"],
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        check=True
                    )
                    effective_reviewer = git_user_result.stdout.strip() or "unknown"
                except (subprocess.CalledProcessError, FileNotFoundError):
                    effective_reviewer = "unknown"

            # Insert feedback into "## Review Feedback" section
            review_section_start = updated_body.find("## Review Feedback")
            if review_section_start != -1:
                next_section_start = updated_body.find("\n##", review_section_start + 18)

                if next_section_start == -1:
                    before = updated_body[:review_section_start]
                    updated_body = before + f"## Review Feedback\n\n**Reviewed by**: {effective_reviewer}\n**Status**: ❌ Changes Requested\n**Date**: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}\n\n{feedback_content}\n\n"
                else:
                    before = updated_body[:review_section_start]
                    after = updated_body[next_section_start:]
                    updated_body = before + f"## Review Feedback\n\n**Reviewed by**: {effective_reviewer}\n**Status**: ❌ Changes Requested\n**Date**: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}\n\n{feedback_content}\n\n" + after

            updated_front = set_scalar(updated_front, "review_status", "has_feedback")
            updated_front = set_scalar(updated_front, "reviewed_by", effective_reviewer)

        # Update reviewed_by when moving to done (approved)
        if target_lane == "done" and not extract_scalar(updated_front, "reviewed_by"):
            effective_reviewer = reviewer
            if not effective_reviewer:
                try:
                    result = subprocess.run(
                        ["git", "config", "user.name"],
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        check=True
                    )
                    effective_reviewer = result.stdout.strip() or "unknown"
                except (subprocess.CalledProcessError, FileNotFoundError):
                    effective_reviewer = "unknown"

            updated_front = set_scalar(updated_front, "reviewed_by", effective_reviewer)
            updated_front = set_scalar(updated_front, "review_status", "approved")

        # Build history entry
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        agent_name = agent or extract_scalar(updated_front, "agent") or "unknown"
        shell_pid_val = shell_pid or extract_scalar(updated_front, "shell_pid") or ""
        note_text = note or f"Moved to {target_lane}"

        shell_part = f"shell_pid={shell_pid_val} – " if shell_pid_val else ""
        history_entry = f"- {timestamp} – {agent_name} – {shell_part}lane={target_lane} – {note_text}"

        # Add history entry to body
        updated_body = append_activity_log(updated_body, history_entry)

        # Build updated document and write
        updated_doc = build_document(updated_front, updated_body, updated_padding)

        file_written = False
        if auto_commit:
            spec_number = feature_slug.split('-')[0] if '-' in feature_slug else feature_slug
            commit_lane_label = _display_lane(target_lane)

            commit_msg = f"chore: Move {task_id} to {commit_lane_label} on spec {spec_number}"
            if agent_name != "unknown":
                commit_msg += f" [{agent_name}]"

            try:
                actual_file_path = wp.path.resolve()

                wp.path.write_text(updated_doc, encoding="utf-8")
                file_written = True

                # Commit only the WP file (preserves staging area)
                commit_success = safe_commit(
                    repo_path=main_repo_root,
                    files_to_commit=[actual_file_path],
                    commit_message=commit_msg,
                    allow_empty=True,  # OK if nothing changed
                )

                if commit_success:
                    # Mirror review/done lane transitions into active WP branch when
                    # command is run from its worktree context.
                    mirrored = False
                    if target_lane in ("for_review", "done"):
                        mirrored = _maybe_mirror_move_commit_to_wp_branch(
                            cwd=cwd,
                            main_repo_root=main_repo_root,
                            feature_slug=feature_slug,
                            wp_id=task_id,
                            main_wp_path=actual_file_path,
                            updated_doc=updated_doc,
                            commit_message=commit_msg,
                        )
                    if not json_output:
                        console.print(f"[cyan]→ Committed status change to {target_branch} branch[/cyan]")
                        if mirrored:
                            console.print(
                                "[cyan]→ Mirrored status change to active WP branch[/cyan]"
                            )
                else:
                    if not json_output:
                        console.print("[yellow]Warning:[/yellow] Failed to auto-commit")

            except Exception as e:
                if not file_written:
                    wp.path.write_text(updated_doc, encoding="utf-8")
                if not json_output:
                    console.print(f"[yellow]Warning:[/yellow] Auto-commit skipped: {e}")
        else:
            wp.path.write_text(updated_doc, encoding="utf-8")

        # Output result
        response_payload = {
            "result": "success",
            "task_id": task_id,
            "old_lane": old_lane,
            "new_lane": target_lane,
            "path": str(wp.path)
        }

        _output_result(
            json_output,
            response_payload,
            f"[green]✓[/green] Moved {task_id} from {old_lane} to {target_lane}"
        )

        # Check for dependent WP warnings when moving to for_review (T083)
        _check_dependent_warnings(repo_root, feature_slug, task_id, target_lane, json_output)

    except Exception as e:
        # Emit ErrorLogged event (T016)
        try:
            emit_error_logged(
                error_type="runtime",
                error_message=str(e),
                wp_id=task_id if 'task_id' in dir() else None,
                stack_trace=traceback.format_exc(),
                agent_id=agent if 'agent' in dir() else None,
            )
        except Exception:
            pass  # Don't block on error logging
        _output_error(json_output, str(e))
        raise typer.Exit(1)


@app.command(name="mark-status")
def mark_status(
    task_ids: Annotated[list[str], typer.Argument(help="Task ID(s) - space-separated (e.g., T001 T002 T003)")],
    status: Annotated[str, typer.Option("--status", help="Status: done/pending")],
    feature: Annotated[Optional[str], typer.Option("--feature", help="Feature slug (auto-detected if omitted)")] = None,
    auto_commit: Annotated[bool, typer.Option("--auto-commit/--no-auto-commit", help="Automatically commit tasks.md changes to target branch")] = True,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON format")] = False,
) -> None:
    """Update task checkbox status in tasks.md for one or more tasks.

    Accepts MULTIPLE task IDs separated by spaces. All tasks are updated
    in a single operation with one commit.

    Examples:
        # Single task:
        spec-kitty agent tasks mark-status T001 --status done

        # Multiple tasks (space-separated):
        spec-kitty agent tasks mark-status T001 T002 T003 --status done

        # Many tasks at once:
        spec-kitty agent tasks mark-status T040 T041 T042 T043 T044 T045 --status done --feature 001-my-feature

        # With JSON output:
        spec-kitty agent tasks mark-status T001 T002 --status done --json
    """
    try:
        # Validate status
        if status not in ("done", "pending"):
            _output_error(json_output, f"Invalid status '{status}'. Must be 'done' or 'pending'.")
            raise typer.Exit(1)

        # Validate we have at least one task
        if not task_ids:
            _output_error(json_output, "At least one task ID is required")
            raise typer.Exit(1)

        # Get repo root and feature slug
        repo_root = locate_project_root()
        if repo_root is None:
            _output_error(json_output, "Could not locate project root")
            raise typer.Exit(1)

        feature_slug = _find_feature_slug(explicit_feature=feature)
        # Ensure we operate on the target branch for this feature
        main_repo_root, target_branch = _ensure_target_branch_checked_out(repo_root, feature_slug, json_output)
        feature_dir = main_repo_root / "kitty-specs" / feature_slug
        tasks_md = feature_dir / "tasks.md"

        if not tasks_md.exists():
            _output_error(json_output, f"tasks.md not found: {tasks_md}")
            raise typer.Exit(1)

        # Read tasks.md content
        content = tasks_md.read_text(encoding="utf-8")
        lines = content.split('\n')
        new_checkbox = "[x]" if status == "done" else "[ ]"

        # Track which tasks were updated and which weren't found
        updated_tasks = []
        not_found_tasks = []

        # Update all requested tasks in a single pass
        for task_id in task_ids:
            task_found = False
            for i, line in enumerate(lines):
                # Match checkbox lines with this task ID
                if re.search(rf'-\s*\[[ x]\]\s*{re.escape(task_id)}\b', line):
                    # Replace the checkbox
                    lines[i] = re.sub(r'-\s*\[[ x]\]', f'- {new_checkbox}', line)
                    updated_tasks.append(task_id)
                    task_found = True
                    break

            if not task_found:
                not_found_tasks.append(task_id)

        # Fail if no tasks were updated
        if not updated_tasks:
            _output_error(json_output, f"No task IDs found in tasks.md: {', '.join(not_found_tasks)}")
            raise typer.Exit(1)

        # Write updated content (single write for all changes)
        updated_content = '\n'.join(lines)
        tasks_md.write_text(updated_content, encoding="utf-8")

        # Auto-commit to TARGET branch (detects from feature meta.json)
        if auto_commit:

            # Extract spec number from feature_slug (e.g., "014" from "014-feature-name")
            spec_number = feature_slug.split('-')[0] if '-' in feature_slug else feature_slug

            # Build commit message
            if len(updated_tasks) == 1:
                commit_msg = f"chore: Mark {updated_tasks[0]} as {status} on spec {spec_number}"
            else:
                commit_msg = f"chore: Mark {len(updated_tasks)} subtasks as {status} on spec {spec_number}"

            try:
                actual_tasks_path = tasks_md.resolve()

                # Commit only the tasks.md file (preserves staging area)
                commit_success = safe_commit(
                    repo_path=main_repo_root,
                    files_to_commit=[actual_tasks_path],
                    commit_message=commit_msg,
                    allow_empty=True,  # OK if nothing changed
                )

                if commit_success:
                    if not json_output:
                        console.print(f"[cyan]→ Committed subtask changes to {target_branch} branch[/cyan]")
                else:
                    if not json_output:
                        console.print("[yellow]Warning:[/yellow] Failed to auto-commit subtask changes")

            except Exception as e:
                if not json_output:
                    console.print(f"[yellow]Warning:[/yellow] Auto-commit exception: {e}")

        # Emit HistoryAdded event for subtask status changes (T014)
        try:
            task_list_str = ", ".join(updated_tasks)
            emit_history_added(
                wp_id=updated_tasks[0].replace("T", "WP")[:4] if updated_tasks else "WP00",
                entry_type="note",
                entry_content=f"Subtask(s) {task_list_str} marked as {status}",
                author="user",
            )
        except Exception as e:
            console.print(f"[yellow]Warning:[/yellow] Event emission failed: {e}")

        # Build result
        result = {
            "result": "success",
            "updated": updated_tasks,
            "not_found": not_found_tasks,
            "status": status,
            "count": len(updated_tasks)
        }

        # Output result
        if not_found_tasks and not json_output:
            console.print(f"[yellow]Warning:[/yellow] Not found: {', '.join(not_found_tasks)}")

        if len(updated_tasks) == 1:
            success_msg = f"[green]✓[/green] Marked {updated_tasks[0]} as {status}"
        else:
            success_msg = f"[green]✓[/green] Marked {len(updated_tasks)} subtasks as {status}: {', '.join(updated_tasks)}"

        _output_result(json_output, result, success_msg)

    except Exception as e:
        # Emit ErrorLogged event (T016)
        try:
            emit_error_logged(
                error_type="runtime",
                error_message=str(e),
                stack_trace=traceback.format_exc(),
            )
        except Exception:
            pass  # Don't block on error logging
        _output_error(json_output, str(e))
        raise typer.Exit(1)


@app.command(name="list-tasks")
def list_tasks(
    lane: Annotated[Optional[str], typer.Option("--lane", help="Filter by lane")] = None,
    feature: Annotated[Optional[str], typer.Option("--feature", help="Feature slug (auto-detected if omitted)")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON format")] = False,
) -> None:
    """List tasks with optional lane filtering.

    Examples:
        spec-kitty agent tasks list-tasks --json
        spec-kitty agent tasks list-tasks --lane doing --json
    """
    try:
        # Get repo root and feature slug
        repo_root = locate_project_root()
        if repo_root is None:
            _output_error(json_output, "Could not locate project root")
            raise typer.Exit(1)

        feature_slug = _find_feature_slug(explicit_feature=feature)

        # Ensure we operate on the target branch for this feature
        main_repo_root, _ = _ensure_target_branch_checked_out(repo_root, feature_slug, json_output)

        # Find all task files
        tasks_dir = main_repo_root / "kitty-specs" / feature_slug / "tasks"
        if not tasks_dir.exists():
            _output_error(json_output, f"Tasks directory not found: {tasks_dir}")
            raise typer.Exit(1)

        tasks = []
        for task_file in tasks_dir.glob("WP*.md"):
            if task_file.name.lower() == "readme.md":
                continue

            content = task_file.read_text(encoding="utf-8-sig")
            frontmatter, _, _ = split_frontmatter(content)

            task_lane = extract_scalar(frontmatter, "lane") or "planned"
            task_wp_id = extract_scalar(frontmatter, "work_package_id") or task_file.stem
            task_title = extract_scalar(frontmatter, "title") or ""

            # Filter by lane if specified
            if lane and task_lane != lane:
                continue

            tasks.append({
                "work_package_id": task_wp_id,
                "title": task_title,
                "lane": task_lane,
                "path": str(task_file)
            })

        # Sort by work package ID
        tasks.sort(key=lambda t: t["work_package_id"])

        if json_output:
            print(json.dumps({"tasks": tasks, "count": len(tasks)}))
        else:
            if not tasks:
                console.print(f"[yellow]No tasks found{' in lane ' + lane if lane else ''}[/yellow]")
            else:
                console.print(f"[bold]Tasks{' in lane ' + lane if lane else ''}:[/bold]\n")
                for task in tasks:
                    console.print(f"  {task['work_package_id']}: {task['title']} [{task['lane']}]")

    except Exception as e:
        _output_error(json_output, str(e))
        raise typer.Exit(1)


@app.command(name="add-history")
def add_history(
    task_id: Annotated[str, typer.Argument(help="Task ID (e.g., WP01)")],
    note: Annotated[str, typer.Option("--note", help="History note")],
    feature: Annotated[Optional[str], typer.Option("--feature", help="Feature slug (auto-detected if omitted)")] = None,
    agent: Annotated[Optional[str], typer.Option("--agent", help="Agent name")] = None,
    shell_pid: Annotated[Optional[str], typer.Option("--shell-pid", help="Shell PID")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON format")] = False,
) -> None:
    """Append history entry to task activity log.

    Examples:
        spec-kitty agent tasks add-history WP01 --note "Completed implementation" --json
    """
    try:
        # Get repo root and feature slug
        repo_root = locate_project_root()
        if repo_root is None:
            _output_error(json_output, "Could not locate project root")
            raise typer.Exit(1)

        feature_slug = _find_feature_slug(explicit_feature=feature)

        # Ensure we operate on the target branch for this feature
        _ensure_target_branch_checked_out(repo_root, feature_slug, json_output)

        # Load work package
        wp = locate_work_package(repo_root, feature_slug, task_id)

        # Get current lane from frontmatter
        current_lane = extract_scalar(wp.frontmatter, "lane") or "planned"

        # Build history entry
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        agent_name = agent or extract_scalar(wp.frontmatter, "agent") or "unknown"
        shell_pid_val = shell_pid or extract_scalar(wp.frontmatter, "shell_pid") or ""

        shell_part = f"shell_pid={shell_pid_val} – " if shell_pid_val else ""
        history_entry = f"- {timestamp} – {agent_name} – {shell_part}lane={current_lane} – {note}"

        # Add history entry to body
        updated_body = append_activity_log(wp.body, history_entry)

        # Build and write updated document
        updated_doc = build_document(wp.frontmatter, updated_body, wp.padding)
        wp.path.write_text(updated_doc, encoding="utf-8")

        # Emit HistoryAdded event (T015 - FR-021)
        try:
            emit_history_added(
                wp_id=task_id,
                entry_type="note",
                entry_content=note,
                author=agent or "user",
            )
        except Exception as e:
            console.print(f"[yellow]Warning:[/yellow] Event emission failed: {e}")

        result = {
            "result": "success",
            "task_id": task_id,
            "note": note
        }

        _output_result(
            json_output,
            result,
            f"[green]✓[/green] Added history entry to {task_id}"
        )

    except Exception as e:
        # Emit ErrorLogged event (T016)
        try:
            emit_error_logged(
                error_type="runtime",
                error_message=str(e),
                wp_id=task_id if 'task_id' in dir() else None,
                stack_trace=traceback.format_exc(),
                agent_id=agent if 'agent' in dir() else None,
            )
        except Exception:
            pass  # Don't block on error logging
        _output_error(json_output, str(e))
        raise typer.Exit(1)


@app.command(name="finalize-tasks")
def finalize_tasks(
    feature: Annotated[Optional[str], typer.Option("--feature", help="Feature slug (auto-detected if omitted)")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON format")] = False,
) -> None:
    """Parse tasks.md and inject dependencies into WP frontmatter.

    Scans tasks.md for "Depends on: WP##" patterns or phase groupings,
    builds dependency graph, validates for cycles, and writes dependencies
    field to each WP file's frontmatter.

    Examples:
        spec-kitty agent tasks finalize-tasks --json
        spec-kitty agent tasks finalize-tasks --feature 001-my-feature
    """
    try:
        # Get repo root and feature slug
        repo_root = locate_project_root()
        if repo_root is None:
            _output_error(json_output, "Could not locate project root")
            raise typer.Exit(1)

        feature_slug = _find_feature_slug(explicit_feature=feature)
        # Ensure we operate on the target branch for this feature
        main_repo_root, _ = _ensure_target_branch_checked_out(repo_root, feature_slug, json_output)
        feature_dir = main_repo_root / "kitty-specs" / feature_slug
        tasks_md = feature_dir / "tasks.md"
        tasks_dir = feature_dir / "tasks"

        if not tasks_md.exists():
            _output_error(json_output, f"tasks.md not found: {tasks_md}")
            raise typer.Exit(1)

        if not tasks_dir.exists():
            _output_error(json_output, f"Tasks directory not found: {tasks_dir}")
            raise typer.Exit(1)

        # Parse tasks.md for dependency patterns
        content = tasks_md.read_text(encoding="utf-8")
        dependencies_map: dict[str, list[str]] = {}

        # Strategy 1: Look for explicit "Depends on: WP##" patterns
        # Strategy 2: Look for phase groupings where later phases depend on earlier ones
        # For now, implement simple pattern matching

        wp_pattern = re.compile(r'WP(\d{2})')
        depends_pattern = re.compile(r'(?:depends on|dependency:|requires):\s*(WP\d{2}(?:,\s*WP\d{2})*)', re.IGNORECASE)

        current_wp = None
        for line in content.split('\n'):
            # Find WP headers
            wp_match = wp_pattern.search(line)
            if wp_match and ('##' in line or 'Work Package' in line):
                current_wp = f"WP{wp_match.group(1)}"
                if current_wp not in dependencies_map:
                    dependencies_map[current_wp] = []

            # Find dependency declarations for current WP
            if current_wp:
                dep_match = depends_pattern.search(line)
                if dep_match:
                    # Extract all WP IDs mentioned
                    dep_wps = re.findall(r'WP\d{2}', dep_match.group(1))
                    dependencies_map[current_wp].extend(dep_wps)
                    # Remove duplicates
                    dependencies_map[current_wp] = list(dict.fromkeys(dependencies_map[current_wp]))

        # Ensure all WP files in tasks/ dir are in the map (with empty deps if not mentioned)
        for wp_file in tasks_dir.glob("WP*.md"):
            wp_id = wp_file.stem.split('-')[0]  # Extract WP## from WP##-title.md
            if wp_id not in dependencies_map:
                dependencies_map[wp_id] = []

        # Update each WP file's frontmatter with dependencies
        updated_count = 0
        for wp_id, deps in sorted(dependencies_map.items()):
            # Find WP file
            wp_files = list(tasks_dir.glob(f"{wp_id}-*.md")) + list(tasks_dir.glob(f"{wp_id}.md"))
            if not wp_files:
                console.print(f"[yellow]Warning:[/yellow] No file found for {wp_id}")
                continue

            wp_file = wp_files[0]

            # Read current content
            content = wp_file.read_text(encoding="utf-8-sig")
            frontmatter, body, padding = split_frontmatter(content)

            # Update dependencies field
            updated_front = _set_string_list(frontmatter, "dependencies", deps)

            # Rebuild and write
            updated_doc = build_document(updated_front, body, padding)
            wp_file.write_text(updated_doc, encoding="utf-8")
            updated_count += 1

        # Validate dependency graph for cycles
        from specify_cli.core.dependency_graph import detect_cycles
        cycles = detect_cycles(dependencies_map)
        if cycles:
            _output_error(json_output, f"Circular dependencies detected: {cycles}")
            raise typer.Exit(1)

        result = {
            "result": "success",
            "updated": updated_count,
            "dependencies": dependencies_map,
            "feature": feature_slug
        }

        _output_result(
            json_output,
            result,
            f"[green]✓[/green] Updated {updated_count} WP files with dependencies"
        )

    except Exception as e:
        # Emit ErrorLogged event (T016)
        try:
            emit_error_logged(
                error_type="runtime",
                error_message=str(e),
                stack_trace=traceback.format_exc(),
            )
        except Exception:
            pass
        _output_error(json_output, str(e))
        raise typer.Exit(1)


@app.command(name="validate-workflow")
def validate_workflow(
    task_id: Annotated[str, typer.Argument(help="Task ID (e.g., WP01)")],
    feature: Annotated[Optional[str], typer.Option("--feature", help="Feature slug (auto-detected if omitted)")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON format")] = False,
) -> None:
    """Validate task metadata structure and workflow consistency.

    Examples:
        spec-kitty agent tasks validate-workflow WP01 --json
    """
    try:
        # Get repo root and feature slug
        repo_root = locate_project_root()
        if repo_root is None:
            _output_error(json_output, "Could not locate project root")
            raise typer.Exit(1)

        feature_slug = _find_feature_slug(explicit_feature=feature)

        # Ensure we operate on the target branch for this feature
        _ensure_target_branch_checked_out(repo_root, feature_slug, json_output)

        # Load work package
        wp = locate_work_package(repo_root, feature_slug, task_id)

        # Validation checks
        errors = []
        warnings = []

        # Check required fields
        required_fields = ["work_package_id", "title", "lane"]
        for field in required_fields:
            if not extract_scalar(wp.frontmatter, field):
                errors.append(f"Missing required field: {field}")

        # Check lane is valid
        lane_value = extract_scalar(wp.frontmatter, "lane")
        if lane_value and lane_value not in LANES:
            errors.append(f"Invalid lane '{lane_value}'. Must be one of: {', '.join(LANES)}")

        # Check work_package_id matches filename
        wp_id = extract_scalar(wp.frontmatter, "work_package_id")
        if wp_id and not wp.path.name.startswith(wp_id):
            warnings.append(f"Work package ID '{wp_id}' doesn't match filename '{wp.path.name}'")

        # Check for activity log
        if "## Activity Log" not in wp.body:
            warnings.append("Missing Activity Log section")

        # Determine validity
        is_valid = len(errors) == 0

        result = {
            "valid": is_valid,
            "errors": errors,
            "warnings": warnings,
            "task_id": task_id,
            "lane": lane_value or "unknown"
        }

        if json_output:
            print(json.dumps(result))
        else:
            if is_valid:
                console.print(f"[green]✓[/green] {task_id} validation passed")
            else:
                console.print(f"[red]✗[/red] {task_id} validation failed")
                for error in errors:
                    console.print(f"  [red]Error:[/red] {error}")

            if warnings:
                console.print("\n[yellow]Warnings:[/yellow]")
                for warning in warnings:
                    console.print(f"  [yellow]•[/yellow] {warning}")

    except Exception as e:
        # Emit ErrorLogged event (T016)
        try:
            emit_error_logged(
                error_type="validation",
                error_message=str(e),
                wp_id=task_id if 'task_id' in dir() else None,
                stack_trace=traceback.format_exc(),
            )
        except Exception:
            pass
        _output_error(json_output, str(e))
        raise typer.Exit(1)


@app.command(name="status")
def status(
    feature: Annotated[
        Optional[str],
        typer.Option("--feature", "-f", help="Feature slug (e.g., 012-documentation-mission). Auto-detected if not provided.")
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON")
    ] = False,
    stale_threshold: Annotated[
        int,
        typer.Option("--stale-threshold", help="Minutes of inactivity before a WP is considered stale")
    ] = 10,
) -> None:
    """Display kanban status board for all work packages in a feature.

    Shows a beautiful overview of work package statuses, progress metrics,
    and next steps based on dependencies.

    WPs in "doing" with no commits for --stale-threshold minutes are flagged
    as potentially stale (agent may have stopped).

    Example:
        spec-kitty agent tasks status
        spec-kitty agent tasks status --feature 012-documentation-mission
        spec-kitty agent tasks status --json
        spec-kitty agent tasks status --stale-threshold 15
    """
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from collections import Counter

    try:
        cwd = Path.cwd().resolve()
        repo_root = locate_project_root(cwd)

        if repo_root is None:
            raise typer.Exit(1)

        # Auto-detect or use provided feature slug
        feature_slug = _find_feature_slug(explicit_feature=feature)

        # Ensure we operate on the target branch for this feature
        main_repo_root, _ = _ensure_target_branch_checked_out(repo_root, feature_slug, json_output)

        # Locate feature directory
        feature_dir = main_repo_root / "kitty-specs" / feature_slug

        if not feature_dir.exists():
            console.print(f"[red]Error:[/red] Feature directory not found: {feature_dir}")
            raise typer.Exit(1)

        tasks_dir = feature_dir / "tasks"

        if not tasks_dir.exists():
            console.print(f"[red]Error:[/red] Tasks directory not found: {tasks_dir}")
            raise typer.Exit(1)

        # Collect all work packages
        work_packages: list[dict[str, Any]] = []
        for wp_file in sorted(tasks_dir.glob("WP*.md")):
            front, body, padding = split_frontmatter(wp_file.read_text(encoding="utf-8"))

            wp_id = extract_scalar(front, "work_package_id")
            title = extract_scalar(front, "title")
            lane = extract_scalar(front, "lane") or "unknown"
            phase = extract_scalar(front, "phase") or "Unknown Phase"
            agent = extract_scalar(front, "agent") or ""
            shell_pid = extract_scalar(front, "shell_pid") or ""

            work_packages.append({
                "id": wp_id,
                "title": title,
                "lane": lane,
                "phase": phase,
                "file": wp_file.name,
                "agent": agent,
                "shell_pid": shell_pid,
            })

        if not work_packages:
            console.print(f"[yellow]No work packages found in {tasks_dir}[/yellow]")
            raise typer.Exit(0)

        # JSON output
        if json_output:
            # Check for stale WPs first (need to do this before JSON output too)
            from specify_cli.core.stale_detection import check_doing_wps_for_staleness

            doing_wps = [wp for wp in work_packages if wp["lane"] == "doing"]
            stale_results = check_doing_wps_for_staleness(
                main_repo_root=main_repo_root,
                feature_slug=feature_slug,
                doing_wps=doing_wps,
                threshold_minutes=stale_threshold,
            )

            # Add staleness info to WPs
            for wp in work_packages:
                if wp["lane"] == "doing" and wp["id"] in stale_results:
                    stale_result = stale_results[wp["id"]]
                    wp["is_stale"] = stale_result.is_stale
                    wp["minutes_since_commit"] = stale_result.minutes_since_commit
                    wp["worktree_exists"] = stale_result.worktree_exists

            lane_counts = Counter(wp["lane"] for wp in work_packages)
            stale_count = sum(1 for wp in work_packages if wp.get("is_stale"))
            status_payload = {
                "feature": feature_slug,
                "total_wps": len(work_packages),
                "by_lane": dict(lane_counts),
                "work_packages": work_packages,
                "progress_percentage": round(lane_counts.get("done", 0) / len(work_packages) * 100, 1),
                "stale_wps": stale_count,
            }
            print(json.dumps(status_payload, indent=2))
            return

        # Rich table output
        # Group by lane
        by_lane: dict[str, list[dict[str, Any]]] = {
            "planned": [],
            "doing": [],
            "for_review": [],
            "done": [],
        }
        for wp in work_packages:
            lane = str(wp.get("lane", "unknown"))
            if lane in by_lane:
                by_lane[lane].append(wp)
            else:
                by_lane.setdefault("other", []).append(wp)

        # Check for stale WPs in "doing" lane
        from specify_cli.core.stale_detection import check_doing_wps_for_staleness

        stale_results = check_doing_wps_for_staleness(
            main_repo_root=main_repo_root,
            feature_slug=feature_slug,
            doing_wps=by_lane["doing"],
            threshold_minutes=stale_threshold,
        )

        # Add staleness info to WPs
        for wp in by_lane["doing"]:
            wp_id = wp["id"]
            if wp_id in stale_results:
                result = stale_results[wp_id]
                wp["is_stale"] = result.is_stale
                wp["minutes_since_commit"] = result.minutes_since_commit
                wp["worktree_exists"] = result.worktree_exists
            else:
                wp["is_stale"] = False

        # Calculate metrics
        total = len(work_packages)
        done_count = len(by_lane["done"])
        in_progress = len(by_lane["doing"]) + len(by_lane["for_review"])
        planned_count = len(by_lane["planned"])
        progress_pct = round((done_count / total * 100), 1) if total > 0 else 0

        # Create title panel
        title_text = Text()
        title_text.append("📊 Work Package Status: ", style="bold cyan")
        title_text.append(feature_slug, style="bold white")

        console.print()
        console.print(Panel(title_text, border_style="cyan"))

        # Progress bar
        progress_text = Text()
        progress_text.append("Progress: ", style="bold")
        progress_text.append(f"{done_count}/{total}", style="bold green")
        progress_text.append(f" ({progress_pct}%)", style="dim")

        # Create visual progress bar
        bar_width = 40
        filled = int(bar_width * progress_pct / 100)
        bar = "█" * filled + "░" * (bar_width - filled)
        progress_text.append(f"\n{bar}", style="green")

        console.print(progress_text)
        console.print()

        # Kanban board table
        table = Table(title="Kanban Board", show_header=True, header_style="bold magenta", border_style="dim")
        table.add_column("📋 Planned", style="yellow", no_wrap=False, width=25)
        table.add_column("🔄 Doing", style="blue", no_wrap=False, width=25)
        table.add_column("👀 For Review", style="cyan", no_wrap=False, width=25)
        table.add_column("✅ Done", style="green", no_wrap=False, width=25)

        # Find max length for rows
        max_rows = max(len(by_lane["planned"]), len(by_lane["doing"]),
                       len(by_lane["for_review"]), len(by_lane["done"]))

        # Add rows
        for i in range(max_rows):
            row = []
            for lane in ["planned", "doing", "for_review", "done"]:
                if i < len(by_lane[lane]):
                    wp = by_lane[lane][i]
                    title_truncated = wp['title'][:22] + "..." if len(wp['title']) > 22 else wp['title']

                    # Add stale indicator for doing WPs
                    if lane == "doing" and wp.get("is_stale"):
                        cell = f"[red]⚠️ {wp['id']}[/red]\n{title_truncated}"
                    else:
                        cell = f"{wp['id']}\n{title_truncated}"
                    row.append(cell)
                else:
                    row.append("")
            table.add_row(*row)

        # Add count row
        table.add_row(
            f"[bold]{len(by_lane['planned'])} WPs[/bold]",
            f"[bold]{len(by_lane['doing'])} WPs[/bold]",
            f"[bold]{len(by_lane['for_review'])} WPs[/bold]",
            f"[bold]{len(by_lane['done'])} WPs[/bold]",
            style="dim"
        )

        console.print(table)
        console.print()

        # Next steps section
        if by_lane["for_review"]:
            console.print("[bold cyan]👀 Ready for Review:[/bold cyan]")
            for wp in by_lane["for_review"]:
                console.print(f"  • {wp['id']} - {wp['title']}")
            console.print()

        if by_lane["doing"]:
            console.print("[bold blue]🔄 In Progress:[/bold blue]")
            stale_wps = []
            for wp in by_lane["doing"]:
                if wp.get("is_stale"):
                    mins = wp.get("minutes_since_commit", "?")
                    agent = wp.get("agent", "unknown")
                    console.print(f"  • [red]⚠️ {wp['id']}[/red] - {wp['title']} [dim](stale: {mins}m, agent: {agent})[/dim]")
                    stale_wps.append(wp)
                else:
                    console.print(f"  • {wp['id']} - {wp['title']}")
            console.print()

            # Show stale warning if any
            if stale_wps:
                console.print(f"[yellow]⚠️  {len(stale_wps)} stale WP(s) detected - agents may have stopped without transitioning[/yellow]")
                console.print("[dim]   Run: spec-kitty agent tasks move-task <WP_ID> --to for_review[/dim]")
                console.print()

        if by_lane["planned"]:
            console.print("[bold yellow]📋 Next Up (Planned):[/bold yellow]")
            # Show first 3 planned items
            for wp in by_lane["planned"][:3]:
                console.print(f"  • {wp['id']} - {wp['title']}")
            if len(by_lane["planned"]) > 3:
                console.print(f"  [dim]... and {len(by_lane['planned']) - 3} more[/dim]")
            console.print()

        # Summary metrics
        summary = Table.grid(padding=(0, 2))
        summary.add_column(style="bold")
        summary.add_column()
        summary.add_row("Total WPs:", str(total))
        summary.add_row("Completed:", f"[green]{done_count}[/green] ({progress_pct}%)")
        summary.add_row("In Progress:", f"[blue]{in_progress}[/blue]")
        summary.add_row("Planned:", f"[yellow]{planned_count}[/yellow]")

        console.print(Panel(summary, title="[bold]Summary[/bold]", border_style="dim"))
        console.print()

    except Exception as e:
        _output_error(json_output, str(e))
        raise typer.Exit(1)


@app.command(name="list-dependents")
def list_dependents(
    wp_id: Annotated[str, typer.Argument(help="Work package ID (e.g., WP01)")],
    feature: Annotated[Optional[str], typer.Option("--feature", help="Feature slug (auto-detected if omitted)")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON format")] = False,
) -> None:
    """Find all WPs that depend on a given WP (downstream dependents).

    This answers "who depends on me?" - useful when reviewing a WP to understand
    the impact of requested changes on downstream work packages.

    Also shows what the WP itself depends on (upstream dependencies).

    Examples:
        spec-kitty agent tasks list-dependents WP13
        spec-kitty agent tasks list-dependents WP01 --feature 001-my-feature --json
    """
    try:
        repo_root = locate_project_root()
        if repo_root is None:
            _output_error(json_output, "Could not locate project root")
            raise typer.Exit(1)

        feature_slug = _find_feature_slug(explicit_feature=feature)
        main_repo_root, _ = _ensure_target_branch_checked_out(repo_root, feature_slug, json_output)
        feature_dir = main_repo_root / "kitty-specs" / feature_slug

        if not feature_dir.exists():
            _output_error(json_output, f"Feature directory not found: {feature_dir}")
            raise typer.Exit(1)

        # Build dependency graph and find dependents
        graph = build_dependency_graph(feature_dir)
        dependents = get_dependents(wp_id, graph)

        # Also get this WP's own dependencies for context
        try:
            wp = locate_work_package(repo_root, feature_slug, wp_id)
            own_deps_raw = extract_scalar(wp.frontmatter, "dependencies")
            # Handle both list and string formats
            if isinstance(own_deps_raw, list):
                own_deps = own_deps_raw
            elif own_deps_raw:
                own_deps = [own_deps_raw]
            else:
                own_deps = []
        except Exception:
            own_deps = []

        if json_output:
            print(json.dumps({
                "wp_id": wp_id,
                "depends_on": own_deps,
                "dependents": dependents
            }))
        else:
            console.print(f"\n[bold]{wp_id} Dependency Info:[/bold]")
            console.print(f"  Depends on: {', '.join(own_deps) if own_deps else '[dim](none)[/dim]'}")
            console.print(f"  Depended on by: {', '.join(dependents) if dependents else '[dim](none)[/dim]'}")

            if dependents:
                console.print(f"\n[yellow]⚠️  Changes to {wp_id} may impact: {', '.join(dependents)}[/yellow]")
            console.print()

    except Exception as e:
        _output_error(json_output, str(e))
        raise typer.Exit(1)
def _set_string_list(frontmatter: str, key: str, values: list[str]) -> str:
    """Set a frontmatter key to a YAML inline list while preserving comments."""
    list_literal = "[" + ", ".join(f'"{value}"' for value in values) + "]"
    line_pattern = re.compile(rf"^(\s*{re.escape(key)}:\s*)(.*?)(\s*(#.*)?)$", re.MULTILINE)
    match = line_pattern.search(frontmatter)
    if match:
        prefix = match.group(1)
        comment = match.group(3) or ""
        return frontmatter[: match.start()] + f"{prefix}{list_literal}{comment}" + frontmatter[match.end() :]

    insertion = f"{key}: {list_literal}\n"
    history_match = re.search(r"^\s*history:\s*$", frontmatter, flags=re.MULTILINE)
    if history_match:
        idx = history_match.start()
        return frontmatter[:idx] + insertion + frontmatter[idx:]
    if frontmatter and not frontmatter.endswith("\n"):
        frontmatter += "\n"
    return frontmatter + insertion

