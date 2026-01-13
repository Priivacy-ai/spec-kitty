"""Task workflow commands for AI agents."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from typing_extensions import Annotated

from specify_cli.core.dependency_graph import build_dependency_graph, get_dependents
from specify_cli.core.paths import locate_project_root
from specify_cli.tasks_support import (
    LANES,
    WorkPackage,
    activity_entries,
    append_activity_log,
    build_document,
    ensure_lane,
    extract_scalar,
    locate_work_package,
    set_scalar,
    split_frontmatter,
)

app = typer.Typer(
    name="tasks",
    help="Task workflow commands for AI agents",
    no_args_is_help=True
)

console = Console()


def _get_main_repo_root(current_path: Path) -> Path:
    """Get the main repository root, even if called from a worktree.

    Args:
        current_path: Current project path (might be worktree)

    Returns:
        Path to main repository root

    Raises:
        RuntimeError: If main repo cannot be found
    """
    # Check if we're in a worktree by reading .git file
    git_file = current_path / ".git"

    if git_file.is_file():
        # We're in a worktree - .git is a file pointing to actual git dir
        git_content = git_file.read_text().strip()
        # Format: "gitdir: /path/to/.git/worktrees/worktree-name"
        if git_content.startswith("gitdir:"):
            gitdir = Path(git_content.split(":", 1)[1].strip())
            # gitdir is like: /main/.git/worktrees/name
            # Main repo .git is: /main/.git
            # Main repo root is: /main
            main_git_dir = gitdir.parent.parent
            main_repo_root = main_git_dir.parent
            return main_repo_root

    # Not a worktree, current path is the main repo
    return current_path


def _find_feature_slug() -> str:
    """Find the current feature slug from the working directory or git branch.

    Returns:
        Feature slug (e.g., "008-unified-python-cli")

    Raises:
        typer.Exit: If feature slug cannot be determined
    """
    import re
    cwd = Path.cwd().resolve()

    # Strategy 1: Check if cwd contains kitty-specs/###-feature-slug
    if "kitty-specs" in cwd.parts:
        parts_list = list(cwd.parts)
        try:
            idx = parts_list.index("kitty-specs")
            if idx + 1 < len(parts_list):
                potential_slug = parts_list[idx + 1]
                # Validate format: ###-slug
                if len(potential_slug) >= 3 and potential_slug[:3].isdigit():
                    return potential_slug
        except (ValueError, IndexError):
            pass

    # Strategy 2: Get from git branch name
    try:
        import subprocess
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True
        )
        branch_name = result.stdout.strip()

        # Strip -WPxx suffix if present (worktree branches)
        # Pattern: 012-documentation-mission-WP04 → 012-documentation-mission
        branch_name = re.sub(r'-WP\d+$', '', branch_name)

        # Validate format: ###-slug
        if len(branch_name) >= 3 and branch_name[:3].isdigit():
            return branch_name
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    raise typer.Exit(1)


def _output_result(json_mode: bool, data: dict, success_message: str = None):
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


def _output_error(json_mode: bool, error_message: str):
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
    feature_dir = repo_root / "kitty-specs" / feature_slug
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
    """Display warning when WP moves to for_review and has dependents in progress.

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

    feature_dir = repo_root / "kitty-specs" / feature_slug

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

    # Check if any dependents are in progress
    in_progress = []
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
                in_progress.append(dep_id)
        except Exception:
            # Skip if we can't read the dependent
            continue

    if in_progress:
        console.print(f"\n[yellow]⚠️  Dependency Alert[/yellow]")
        console.print(f"{', '.join(in_progress)} are in progress and depend on {wp_id}")
        console.print("\nIf changes are requested during review:")
        console.print("  1. Notify dependent WP agents")
        console.print("  2. Dependent WPs will need manual rebase after changes")
        for dep in in_progress:
            console.print(f"     cd .worktrees/{feature_slug}-{dep} && git rebase {feature_slug}-{wp_id}")
        console.print()


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
    reviewer: Annotated[Optional[str], typer.Option("--reviewer", help="Reviewer name (auto-detected from git if omitted)")] = None,
    force: Annotated[bool, typer.Option("--force", help="Force move even with unchecked subtasks or missing feedback")] = False,
    auto_commit: Annotated[bool, typer.Option("--auto-commit/--no-auto-commit", help="Automatically commit WP file changes to main branch")] = True,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON format")] = False,
) -> None:
    """Move task between lanes (planned → doing → for_review → done).

    Examples:
        spec-kitty agent tasks move-task WP01 --to doing --assignee claude --json
        spec-kitty agent tasks move-task WP02 --to for_review --agent claude --shell-pid $$
        spec-kitty agent tasks move-task WP03 --to done --note "Review passed"
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

        feature_slug = feature or _find_feature_slug()

        # Load work package first (needed for current_lane check)
        wp = locate_work_package(repo_root, feature_slug, task_id)
        old_lane = wp.current_lane

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
                error_msg += f"\nMark these complete first:\n"
                for task in unchecked[:3]:  # Show first 3 examples
                    task_clean = task.split()[0] if ' ' in task else task
                    error_msg += f"  spec-kitty agent tasks mark-status {task_clean} --status done\n"
                error_msg += f"\nOr use --force to override (not recommended)"
                _output_error(json_output, error_msg)
                raise typer.Exit(1)

        # Update lane in frontmatter
        updated_front = set_scalar(wp.frontmatter, "lane", target_lane)

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
        updated_body = wp.body
        if review_feedback_file and review_feedback_file.exists():
            # Read feedback content
            feedback_content = review_feedback_file.read_text(encoding="utf-8").strip()

            # Auto-detect reviewer if not provided
            if not reviewer:
                try:
                    import subprocess
                    result = subprocess.run(
                        ["git", "config", "user.name"],
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    reviewer = result.stdout.strip() or "unknown"
                except (subprocess.CalledProcessError, FileNotFoundError):
                    reviewer = "unknown"

            # Insert feedback into "## Review Feedback" section
            # Find the section and replace its content
            review_section_start = updated_body.find("## Review Feedback")
            if review_section_start != -1:
                # Find the next section (starts with ##) or end of document
                next_section_start = updated_body.find("\n##", review_section_start + 18)

                if next_section_start == -1:
                    # No next section, replace to end
                    before = updated_body[:review_section_start]
                    updated_body = before + f"## Review Feedback\n\n**Reviewed by**: {reviewer}\n**Status**: ❌ Changes Requested\n**Date**: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}\n\n{feedback_content}\n\n"
                else:
                    # Replace content between this section and next
                    before = updated_body[:review_section_start]
                    after = updated_body[next_section_start:]
                    updated_body = before + f"## Review Feedback\n\n**Reviewed by**: {reviewer}\n**Status**: ❌ Changes Requested\n**Date**: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}\n\n{feedback_content}\n\n" + after

            # Update frontmatter for review status
            updated_front = set_scalar(updated_front, "review_status", "has_feedback")
            updated_front = set_scalar(updated_front, "reviewed_by", reviewer)

        # Update reviewed_by when moving to done (approved)
        if target_lane == "done" and not extract_scalar(updated_front, "reviewed_by"):
            # Auto-detect reviewer if not provided
            if not reviewer:
                try:
                    import subprocess
                    result = subprocess.run(
                        ["git", "config", "user.name"],
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    reviewer = result.stdout.strip() or "unknown"
                except (subprocess.CalledProcessError, FileNotFoundError):
                    reviewer = "unknown"

            updated_front = set_scalar(updated_front, "reviewed_by", reviewer)
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

        # Build and write updated document
        updated_doc = build_document(updated_front, updated_body, wp.padding)
        wp.path.write_text(updated_doc, encoding="utf-8")

        # FIX B: Auto-commit to main branch (wp.path is symlinked to main's kitty-specs/)
        # This enables instant status sync across all worktrees (jujutsu-aligned)
        if auto_commit:
            import subprocess

            # Get the ACTUAL main repo root (not worktree path)
            main_repo_root = _get_main_repo_root(repo_root)

            # Commit to main (file is in main via symlink)
            commit_msg = f"chore: Move {task_id} to {target_lane}"
            if agent_name != "unknown":
                commit_msg += f" [{agent_name}]"

            try:
                # Resolve symlink to get the actual file path in main repo
                # wp.path might be: /worktrees/WP04/kitty-specs/... (via symlink)
                # We need: /main/kitty-specs/... (actual file)
                actual_file_path = wp.path.resolve()

                # Commit the specific WP file directly (bypasses staging area)
                # This works even if other files in main are modified
                commit_result = subprocess.run(
                    ["git", "commit", str(actual_file_path), "-m", commit_msg],
                    cwd=main_repo_root,
                    capture_output=True,
                    text=True,
                    check=False
                )

                if commit_result.returncode == 0:
                    if not json_output:
                        console.print(f"[cyan]→ Committed status change to main branch[/cyan]")
                else:
                    # Commit failed
                    if not json_output:
                        console.print(f"[yellow]Warning:[/yellow] Failed to auto-commit")
                        console.print(f"  stdout: {commit_result.stdout}")
                        console.print(f"  stderr: {commit_result.stderr}")

            except Exception as e:
                # Unexpected error
                if not json_output:
                    console.print(f"[yellow]Warning:[/yellow] Auto-commit exception: {e}")

        # Output result
        result = {
            "result": "success",
            "task_id": task_id,
            "old_lane": old_lane,
            "new_lane": target_lane,
            "path": str(wp.path)
        }

        _output_result(
            json_output,
            result,
            f"[green]✓[/green] Moved {task_id} from {old_lane} to {target_lane}"
        )

        # Check for dependent WP warnings when moving to for_review (T083)
        _check_dependent_warnings(repo_root, feature_slug, task_id, target_lane, json_output)

    except Exception as e:
        _output_error(json_output, str(e))
        raise typer.Exit(1)


@app.command(name="mark-status")
def mark_status(
    task_id: Annotated[str, typer.Argument(help="Task ID (e.g., T001)")],
    status: Annotated[str, typer.Option("--status", help="Status: done/pending")],
    feature: Annotated[Optional[str], typer.Option("--feature", help="Feature slug (auto-detected if omitted)")] = None,
    auto_commit: Annotated[bool, typer.Option("--auto-commit/--no-auto-commit", help="Automatically commit tasks.md changes to main branch")] = True,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON format")] = False,
) -> None:
    """Update task checkbox status in tasks.md.

    Examples:
        spec-kitty agent tasks mark-status T001 --status done --json
        spec-kitty agent tasks mark-status T002 --status pending
    """
    try:
        # Validate status
        if status not in ("done", "pending"):
            _output_error(json_output, f"Invalid status '{status}'. Must be 'done' or 'pending'.")
            raise typer.Exit(1)

        # Get repo root and feature slug
        repo_root = locate_project_root()
        if repo_root is None:
            _output_error(json_output, "Could not locate project root")
            raise typer.Exit(1)

        feature_slug = feature or _find_feature_slug()
        feature_dir = repo_root / "kitty-specs" / feature_slug
        tasks_md = feature_dir / "tasks.md"

        if not tasks_md.exists():
            _output_error(json_output, f"tasks.md not found: {tasks_md}")
            raise typer.Exit(1)

        # Read tasks.md content
        content = tasks_md.read_text(encoding="utf-8")
        lines = content.split('\n')
        updated = False
        new_checkbox = "[x]" if status == "done" else "[ ]"

        # Find and update the task checkbox
        # Look for patterns like: - [ ] T001 or - [x] T001
        for i, line in enumerate(lines):
            # Match checkbox lines with this task ID
            if re.search(rf'-\s*\[[ x]\]\s*{re.escape(task_id)}\b', line):
                # Replace the checkbox
                lines[i] = re.sub(r'-\s*\[[ x]\]', f'- {new_checkbox}', line)
                updated = True
                break

        if not updated:
            _output_error(json_output, f"Task ID '{task_id}' not found in tasks.md")
            raise typer.Exit(1)

        # Write updated content
        updated_content = '\n'.join(lines)
        tasks_md.write_text(updated_content, encoding="utf-8")

        # Auto-commit to main branch (tasks.md is symlinked to main's kitty-specs/)
        if auto_commit:
            import subprocess

            # Get the ACTUAL main repo root (not worktree path)
            main_repo_root = _get_main_repo_root(repo_root)

            commit_msg = f"chore: Mark {task_id} as {status}"

            try:
                # Resolve symlink to get the actual file path in main repo
                actual_tasks_path = tasks_md.resolve()

                # Commit the specific tasks.md file directly (bypasses staging area)
                # This works even if other files in main are modified
                commit_result = subprocess.run(
                    ["git", "commit", str(actual_tasks_path), "-m", commit_msg],
                    cwd=main_repo_root,
                    capture_output=True,
                    text=True,
                    check=False
                )

                if commit_result.returncode == 0:
                    if not json_output:
                        console.print(f"[cyan]→ Committed subtask change to main branch[/cyan]")
                elif "nothing to commit" not in commit_result.stdout:
                    # Real error, not just "nothing to commit"
                    if not json_output:
                        console.print(f"[yellow]Warning:[/yellow] Failed to auto-commit: {commit_result.stderr}")

            except Exception as e:
                # Unexpected error
                if not json_output:
                    console.print(f"[yellow]Warning:[/yellow] Auto-commit exception: {e}")

        result = {
            "result": "success",
            "task_id": task_id,
            "status": status,
            "note": "Checkbox status updated in tasks.md"
        }

        _output_result(
            json_output,
            result,
            f"[green]✓[/green] Marked {task_id} as {status}"
        )

    except Exception as e:
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

        feature_slug = feature or _find_feature_slug()

        # Find all task files
        tasks_dir = repo_root / "kitty-specs" / feature_slug / "tasks"
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

        feature_slug = feature or _find_feature_slug()

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
        _output_error(json_output, str(e))
        raise typer.Exit(1)


@app.command(name="rollback-task")
def rollback_task(
    task_id: Annotated[str, typer.Argument(help="Task ID (e.g., WP01)")],
    feature: Annotated[Optional[str], typer.Option("--feature", help="Feature slug (auto-detected if omitted)")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON format")] = False,
) -> None:
    """Undo last lane move using activity history.

    Examples:
        spec-kitty agent tasks rollback-task WP01 --json
    """
    try:
        # Get repo root and feature slug
        repo_root = locate_project_root()
        if repo_root is None:
            _output_error(json_output, "Could not locate project root")
            raise typer.Exit(1)

        feature_slug = feature or _find_feature_slug()

        # Load work package
        wp = locate_work_package(repo_root, feature_slug, task_id)

        # Get activity history
        entries = activity_entries(wp.body)

        if len(entries) < 2:
            _output_error(json_output, "Cannot rollback: Need at least 2 history entries")
            raise typer.Exit(1)

        # Get previous lane from second-to-last entry
        previous_lane = entries[-2]["lane"]
        current_lane = wp.current_lane

        # Update lane in frontmatter
        updated_front = set_scalar(wp.frontmatter, "lane", previous_lane)

        # Add rollback history entry
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        agent_name = extract_scalar(updated_front, "agent") or "unknown"
        shell_pid_val = extract_scalar(updated_front, "shell_pid") or ""

        shell_part = f"shell_pid={shell_pid_val} – " if shell_pid_val else ""
        history_entry = f"- {timestamp} – {agent_name} – {shell_part}lane={previous_lane} – Rolled back from {current_lane}"

        updated_body = append_activity_log(wp.body, history_entry)

        # Build and write updated document
        updated_doc = build_document(updated_front, updated_body, wp.padding)
        wp.path.write_text(updated_doc, encoding="utf-8")

        result = {
            "result": "success",
            "task_id": task_id,
            "previous_lane": current_lane,
            "new_lane": previous_lane
        }

        _output_result(
            json_output,
            result,
            f"[green]✓[/green] Rolled back {task_id} from {current_lane} to {previous_lane}"
        )

    except Exception as e:
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

        feature_slug = feature or _find_feature_slug()
        feature_dir = repo_root / "kitty-specs" / feature_slug
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
            updated_front = set_scalar(frontmatter, "dependencies", deps)

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

        feature_slug = feature or _find_feature_slug()

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
                console.print(f"\n[yellow]Warnings:[/yellow]")
                for warning in warnings:
                    console.print(f"  [yellow]•[/yellow] {warning}")

    except Exception as e:
        _output_error(json_output, str(e))
        raise typer.Exit(1)
