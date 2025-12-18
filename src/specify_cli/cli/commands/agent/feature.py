"""Feature lifecycle commands for AI agents."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from typing_extensions import Annotated

from specify_cli.core.paths import locate_project_root, is_worktree_context
from specify_cli.core.worktree import (
    create_feature_worktree,
    get_next_feature_number,
    validate_feature_structure,
)

app = typer.Typer(
    name="feature",
    help="Feature lifecycle commands for AI agents",
    no_args_is_help=True
)

console = Console()


def _find_feature_directory(repo_root: Path, cwd: Path) -> Path:
    """Find the current feature directory.

    Handles three contexts:
    1. Worktree root (cwd contains kitty-specs/)
    2. Inside feature directory (walk up to find kitty-specs/)
    3. Main repo (find latest feature in kitty-specs/)

    Args:
        repo_root: Repository root path
        cwd: Current working directory

    Returns:
        Path to feature directory

    Raises:
        ValueError: If feature directory cannot be determined
    """
    # Check if we're in a worktree
    if is_worktree_context(cwd):
        # Get the current git branch name to match feature directory
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=cwd,
                capture_output=True,
                text=True,
                check=True
            )
            branch_name = result.stdout.strip()
        except subprocess.CalledProcessError:
            branch_name = None

        # Strategy 1: Check if cwd contains kitty-specs/ (we're at worktree root)
        kitty_specs_candidate = cwd / "kitty-specs"
        if kitty_specs_candidate.exists() and kitty_specs_candidate.is_dir():
            kitty_specs = kitty_specs_candidate
        else:
            # Strategy 2: Walk up to find kitty-specs directory
            kitty_specs = cwd
            while kitty_specs != kitty_specs.parent:
                if kitty_specs.name == "kitty-specs":
                    break
                kitty_specs = kitty_specs.parent

            if kitty_specs.name != "kitty-specs":
                raise ValueError("Could not locate kitty-specs directory in worktree")

        # Find the ###-* feature directory that matches the branch name
        if branch_name:
            # First try exact match with branch name
            branch_feature_dir = kitty_specs / branch_name
            if branch_feature_dir.exists() and branch_feature_dir.is_dir():
                return branch_feature_dir

        # Fallback: Find any ###-* feature directory (for older worktrees)
        for item in kitty_specs.iterdir():
            if item.is_dir() and len(item.name) >= 3 and item.name[:3].isdigit():
                return item

        raise ValueError("Could not find feature directory in worktree")
    else:
        # We're in main repo - find latest feature
        specs_dir = repo_root / "kitty-specs"
        if not specs_dir.exists():
            raise ValueError("No kitty-specs directory found in repository")

        # Find the highest numbered feature
        max_num = 0
        feature_dir = None
        for item in specs_dir.iterdir():
            if item.is_dir() and len(item.name) >= 3 and item.name[:3].isdigit():
                try:
                    num = int(item.name[:3])
                    if num > max_num:
                        max_num = num
                        feature_dir = item
                except ValueError:
                    continue

        if feature_dir is None:
            raise ValueError("No feature directories found in kitty-specs/")

        return feature_dir


@app.command(name="create-feature")
def create_feature(
    feature_slug: Annotated[str, typer.Argument(help="Feature slug (e.g., 'user-auth')")],
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON format")] = False,
) -> None:
    """Create new feature with worktree and directory structure.

    This command is designed for AI agents to call programmatically.

    Examples:
        spec-kitty agent create-feature "new-dashboard" --json
    """
    try:
        repo_root = locate_project_root()
        if repo_root is None:
            error_msg = "Could not locate project root. Run from within spec-kitty repository."
            if json_output:
                print(json.dumps({"error": error_msg}))
            else:
                console.print(f"[red]Error:[/red] {error_msg}")
            raise typer.Exit(1)

        worktree_path, feature_dir = create_feature_worktree(repo_root, feature_slug)

        if json_output:
            print(json.dumps({
                "result": "success",
                "feature": feature_dir.name,
                "worktree_path": str(worktree_path),
                "feature_dir": str(feature_dir)
            }))
        else:
            console.print(f"[green]✓[/green] Feature created: {feature_dir.name}")
            console.print(f"   Worktree: {worktree_path}")
            console.print(f"   Directory: {feature_dir}")

    except Exception as e:
        if json_output:
            print(json.dumps({"error": str(e)}))
        else:
            console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command(name="check-prerequisites")
def check_prerequisites(
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON format")] = False,
    paths_only: Annotated[bool, typer.Option("--paths-only", help="Only output path variables")] = False,
    include_tasks: Annotated[bool, typer.Option("--include-tasks", help="Include tasks.md in validation")] = False,
) -> None:
    """Validate feature structure and prerequisites.

    This command is designed for AI agents to call programmatically.

    Examples:
        spec-kitty agent check-prerequisites --json
        spec-kitty agent check-prerequisites --paths-only --json
    """
    try:
        repo_root = locate_project_root()
        if repo_root is None:
            error_msg = "Could not locate project root. Run from within spec-kitty repository."
            if json_output:
                print(json.dumps({"error": error_msg}))
            else:
                console.print(f"[red]Error:[/red] {error_msg}")
            raise typer.Exit(1)

        # Determine feature directory (main repo or worktree)
        cwd = Path.cwd().resolve()
        feature_dir = _find_feature_directory(repo_root, cwd)

        validation_result = validate_feature_structure(feature_dir, check_tasks=include_tasks)

        if json_output:
            if paths_only:
                print(json.dumps(validation_result["paths"]))
            else:
                print(json.dumps(validation_result))
        else:
            if validation_result["valid"]:
                console.print("[green]✓[/green] Prerequisites check passed")
                console.print(f"   Feature: {feature_dir.name}")
            else:
                console.print("[red]✗[/red] Prerequisites check failed")
                for error in validation_result["errors"]:
                    console.print(f"   • {error}")

            if validation_result["warnings"]:
                console.print("\n[yellow]Warnings:[/yellow]")
                for warning in validation_result["warnings"]:
                    console.print(f"   • {warning}")

    except Exception as e:
        if json_output:
            print(json.dumps({"error": str(e)}))
        else:
            console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command(name="setup-plan")
def setup_plan(
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON format")] = False,
) -> None:
    """Scaffold implementation plan template.

    This command is designed for AI agents to call programmatically.

    Examples:
        spec-kitty agent setup-plan --json
    """
    try:
        repo_root = locate_project_root()
        if repo_root is None:
            error_msg = "Could not locate project root. Run from within spec-kitty repository."
            if json_output:
                print(json.dumps({"error": error_msg}))
            else:
                console.print(f"[red]Error:[/red] {error_msg}")
            raise typer.Exit(1)

        # Determine feature directory (main repo or worktree)
        cwd = Path.cwd().resolve()
        feature_dir = _find_feature_directory(repo_root, cwd)

        # Find plan template
        plan_template_candidates = [
            repo_root / ".kittify" / "templates" / "plan-template.md",
            repo_root / "templates" / "plan-template.md",
        ]

        plan_template = None
        for candidate in plan_template_candidates:
            if candidate.exists():
                plan_template = candidate
                break

        if plan_template is None:
            raise FileNotFoundError("Plan template not found in repository")

        plan_file = feature_dir / "plan.md"

        # Copy template to plan.md
        shutil.copy2(plan_template, plan_file)

        if json_output:
            print(json.dumps({
                "result": "success",
                "plan_file": str(plan_file),
                "feature_dir": str(feature_dir)
            }))
        else:
            console.print(f"[green]✓[/green] Plan scaffolded: {plan_file}")

    except Exception as e:
        if json_output:
            print(json.dumps({"error": str(e)}))
        else:
            console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

def _find_latest_feature_worktree(repo_root: Path) -> Optional[Path]:
    """Find the latest feature worktree by number.

    Migrated from find_latest_feature_worktree() in common.sh

    Args:
        repo_root: Repository root directory

    Returns:
        Path to latest worktree, or None if no worktrees exist
    """
    worktrees_dir = repo_root / ".worktrees"
    if not worktrees_dir.exists():
        return None

    latest_num = 0
    latest_worktree = None

    for worktree_dir in worktrees_dir.iterdir():
        if not worktree_dir.is_dir():
            continue

        # Match pattern: 001-feature-name
        match = re.match(r"^(\d{3})-", worktree_dir.name)
        if match:
            num = int(match.group(1))
            if num > latest_num:
                latest_num = num
                latest_worktree = worktree_dir

    return latest_worktree


def _get_current_branch(repo_root: Path) -> str:
    """Get current git branch name.

    Args:
        repo_root: Repository root directory

    Returns:
        Current branch name, or 'main' if not in a git repo
    """
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False
    )
    return result.stdout.strip() if result.returncode == 0 else "main"


@app.command(name="accept")
def accept_feature(
    feature: Annotated[
        Optional[str],
        typer.Option(
            "--feature",
            help="Feature directory slug (auto-detected if not specified)"
        )
    ] = None,
    mode: Annotated[
        str,
        typer.Option(
            "--mode",
            help="Acceptance mode: auto, pr, local, checklist"
        )
    ] = "auto",
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Output results as JSON for agent parsing"
        )
    ] = False,
    lenient: Annotated[
        bool,
        typer.Option(
            "--lenient",
            help="Skip strict metadata validation"
        )
    ] = False,
    no_commit: Annotated[
        bool,
        typer.Option(
            "--no-commit",
            help="Skip auto-commit (report only)"
        )
    ] = False,
) -> None:
    """Perform feature acceptance workflow.

    This command:
    1. Validates all tasks are in 'done' lane
    2. Runs acceptance checks from checklist files
    3. Creates acceptance report
    4. Marks feature as ready for merge

    Delegates to existing tasks_cli.py accept implementation.

    Examples:
        # Run acceptance workflow
        spec-kitty agent feature accept

        # With JSON output for agents
        spec-kitty agent feature accept --json

        # Lenient mode (skip strict validation)
        spec-kitty agent feature accept --lenient --json
    """
    try:
        repo_root = locate_project_root()
        if repo_root is None:
            error = "Could not locate project root"
            if json_output:
                print(json.dumps({"error": error, "success": False}))
            else:
                console.print(f"[red]Error:[/red] {error}")
            sys.exit(1)

        # Build command to call tasks_cli.py
        tasks_cli = repo_root / "scripts" / "tasks" / "tasks_cli.py"
        if not tasks_cli.exists():
            error = f"tasks_cli.py not found: {tasks_cli}"
            if json_output:
                print(json.dumps({"error": error, "success": False}))
            else:
                console.print(f"[red]Error:[/red] {error}")
            sys.exit(1)

        cmd = ["python3", str(tasks_cli), "accept"]
        if feature:
            cmd.extend(["--feature", feature])
        cmd.extend(["--mode", mode])
        if json_output:
            cmd.append("--json")
        if lenient:
            cmd.append("--lenient")
        if no_commit:
            cmd.append("--no-commit")

        # Execute accept command
        result = subprocess.run(
            cmd,
            cwd=repo_root,
            capture_output=True,
            text=True,
        )

        # Pass through output
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr and not json_output:
            print(result.stderr, end="", file=sys.stderr)

        sys.exit(result.returncode)

    except Exception as e:
        if json_output:
            print(json.dumps({"error": str(e), "success": False}))
        else:
            console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


@app.command(name="merge")
def merge_feature(
    feature: Annotated[
        Optional[str],
        typer.Option(
            "--feature",
            help="Feature directory slug (auto-detected if not specified)"
        )
    ] = None,
    target: Annotated[
        str,
        typer.Option(
            "--target",
            help="Target branch to merge into"
        )
    ] = "main",
    strategy: Annotated[
        str,
        typer.Option(
            "--strategy",
            help="Merge strategy: merge, squash, rebase"
        )
    ] = "merge",
    push: Annotated[
        bool,
        typer.Option(
            "--push",
            help="Push to origin after merging"
        )
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Show actions without executing"
        )
    ] = False,
    keep_branch: Annotated[
        bool,
        typer.Option(
            "--keep-branch",
            help="Keep feature branch after merge (default: delete)"
        )
    ] = False,
    keep_worktree: Annotated[
        bool,
        typer.Option(
            "--keep-worktree",
            help="Keep worktree after merge (default: remove)"
        )
    ] = False,
    auto_retry: Annotated[
        bool,
        typer.Option(
            "--auto-retry/--no-auto-retry",
            help="Auto-navigate to latest worktree if in wrong location"
        )
    ] = True,
) -> None:
    """Merge feature branch into target branch.

    This command:
    1. Validates feature is accepted
    2. Merges feature branch into target (usually 'main')
    3. Cleans up worktree
    4. Deletes feature branch

    Auto-retry logic (from merge-feature.sh):
    If current branch doesn't match feature pattern (XXX-name) and auto-retry is enabled,
    automatically finds and navigates to latest worktree.

    Delegates to existing tasks_cli.py merge implementation.

    Examples:
        # Merge into main branch
        spec-kitty agent feature merge

        # Merge into specific branch with push
        spec-kitty agent feature merge --target develop --push

        # Dry-run mode
        spec-kitty agent feature merge --dry-run

        # Keep worktree and branch after merge
        spec-kitty agent feature merge --keep-worktree --keep-branch
    """
    try:
        repo_root = locate_project_root()
        if repo_root is None:
            error = "Could not locate project root"
            print(json.dumps({"error": error, "success": False}))
            sys.exit(1)

        # Auto-retry logic: Check if we're on a feature branch
        if auto_retry and not os.environ.get("SPEC_KITTY_AUTORETRY"):
            current_branch = _get_current_branch(repo_root)
            is_feature_branch = re.match(r"^\d{3}-", current_branch)

            if not is_feature_branch:
                # Try to find latest worktree and retry there
                latest_worktree = _find_latest_feature_worktree(repo_root)
                if latest_worktree:
                    console.print(
                        f"[yellow]Auto-retry:[/yellow] Not on feature branch ({current_branch}). "
                        f"Running merge in {latest_worktree.name}"
                    )

                    # Set env var to prevent infinite recursion
                    env = os.environ.copy()
                    env["SPEC_KITTY_AUTORETRY"] = "1"

                    # Re-run command in worktree
                    retry_cmd = ["spec-kitty", "agent", "feature", "merge"]
                    if feature:
                        retry_cmd.extend(["--feature", feature])
                    retry_cmd.extend(["--target", target, "--strategy", strategy])
                    if push:
                        retry_cmd.append("--push")
                    if dry_run:
                        retry_cmd.append("--dry-run")
                    if keep_branch:
                        retry_cmd.append("--keep-branch")
                    if keep_worktree:
                        retry_cmd.append("--keep-worktree")
                    retry_cmd.append("--no-auto-retry")

                    result = subprocess.run(
                        retry_cmd,
                        cwd=latest_worktree,
                        env=env,
                    )
                    sys.exit(result.returncode)

        # Build command to call tasks_cli.py
        tasks_cli = repo_root / "scripts" / "tasks" / "tasks_cli.py"
        if not tasks_cli.exists():
            error = f"tasks_cli.py not found: {tasks_cli}"
            print(json.dumps({"error": error, "success": False}))
            sys.exit(1)

        cmd = ["python3", str(tasks_cli), "merge"]
        if feature:
            cmd.extend(["--feature", feature])
        cmd.extend(["--target", target, "--strategy", strategy])
        if push:
            cmd.append("--push")
        if dry_run:
            cmd.append("--dry-run")
        if keep_branch:
            cmd.append("--keep-branch")
        else:
            cmd.append("--delete-branch")
        if keep_worktree:
            cmd.append("--keep-worktree")
        else:
            cmd.append("--remove-worktree")

        # Execute merge command
        result = subprocess.run(
            cmd,
            cwd=repo_root,
            capture_output=True,
            text=True,
        )

        # Pass through output
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)

        sys.exit(result.returncode)

    except Exception as e:
        print(json.dumps({"error": str(e), "success": False}))
        sys.exit(1)
