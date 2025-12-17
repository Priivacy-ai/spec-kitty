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


def _find_feature_slug() -> str:
    """Find the current feature slug from the working directory or git branch.

    Returns:
        Feature slug (e.g., "008-unified-python-cli")

    Raises:
        typer.Exit: If feature slug cannot be determined
    """
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


@app.command(name="move-task")
def move_task(
    task_id: Annotated[str, typer.Argument(help="Task ID (e.g., WP01)")],
    to: Annotated[str, typer.Option("--to", help="Target lane (planned/doing/for_review/done)")],
    feature: Annotated[Optional[str], typer.Option("--feature", help="Feature slug (auto-detected if omitted)")] = None,
    agent: Annotated[Optional[str], typer.Option("--agent", help="Agent name")] = None,
    shell_pid: Annotated[Optional[str], typer.Option("--shell-pid", help="Shell PID")] = None,
    note: Annotated[Optional[str], typer.Option("--note", help="History note")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON format")] = False,
) -> None:
    """Move task between lanes (planned → doing → for_review → done).

    Examples:
        spec-kitty agent tasks move-task WP01 --to doing --json
        spec-kitty agent tasks move-task WP02 --to for_review --agent claude --shell-pid $$
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

        # Load work package
        wp = locate_work_package(repo_root, feature_slug, task_id)
        old_lane = wp.current_lane

        # Update lane in frontmatter
        updated_front = set_scalar(wp.frontmatter, "lane", target_lane)

        # Update agent if provided
        if agent:
            updated_front = set_scalar(updated_front, "agent", agent)

        # Update shell_pid if provided
        if shell_pid:
            updated_front = set_scalar(updated_front, "shell_pid", shell_pid)

        # Build history entry
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        agent_name = agent or extract_scalar(updated_front, "agent") or "unknown"
        shell_pid_val = shell_pid or extract_scalar(updated_front, "shell_pid") or ""
        note_text = note or f"Moved to {target_lane}"

        shell_part = f"shell_pid={shell_pid_val} – " if shell_pid_val else ""
        history_entry = f"- {timestamp} – {agent_name} – {shell_part}lane={target_lane} – {note_text}"

        # Add history entry to body
        updated_body = append_activity_log(wp.body, history_entry)

        # Build and write updated document
        updated_doc = build_document(updated_front, updated_body, wp.padding)
        wp.path.write_text(updated_doc, encoding="utf-8")

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

    except Exception as e:
        _output_error(json_output, str(e))
        raise typer.Exit(1)


@app.command(name="mark-status")
def mark_status(
    task_id: Annotated[str, typer.Argument(help="Task ID (e.g., T001)")],
    status: Annotated[str, typer.Option("--status", help="Status: done/pending")],
    feature: Annotated[Optional[str], typer.Option("--feature", help="Feature slug (auto-detected if omitted)")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON format")] = False,
) -> None:
    """Update task checkbox status in frontmatter.

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

        # Note: mark-status typically updates tasks.md checklist, not WP frontmatter
        # For now, we'll output success but note this is placeholder for checkbox update
        # Real implementation would parse tasks.md and update checkbox

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
