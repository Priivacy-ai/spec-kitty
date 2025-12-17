"""Feature lifecycle commands for AI agents."""

from __future__ import annotations

import json
import shutil
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

        # Check if we're in a worktree
        if is_worktree_context(cwd):
            # We're in a worktree - find the feature directory
            # Look for kitty-specs/###-* directory
            kitty_specs = cwd
            while kitty_specs != kitty_specs.parent:
                if kitty_specs.name == "kitty-specs":
                    break
                kitty_specs = kitty_specs.parent

            if kitty_specs.name == "kitty-specs":
                # Find the ###-* feature directory
                for item in kitty_specs.iterdir():
                    if item.is_dir() and len(item.name) >= 3 and item.name[:3].isdigit():
                        feature_dir = item
                        break
                else:
                    raise ValueError("Could not find feature directory in worktree")
            else:
                raise ValueError("Could not locate kitty-specs directory in worktree")
        else:
            # We're in main repo - find latest feature or use CWD
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

        # Check if we're in a worktree
        if is_worktree_context(cwd):
            # We're in a worktree - find the feature directory
            kitty_specs = cwd
            while kitty_specs != kitty_specs.parent:
                if kitty_specs.name == "kitty-specs":
                    break
                kitty_specs = kitty_specs.parent

            if kitty_specs.name == "kitty-specs":
                # Find the ###-* feature directory
                for item in kitty_specs.iterdir():
                    if item.is_dir() and len(item.name) >= 3 and item.name[:3].isdigit():
                        feature_dir = item
                        break
                else:
                    raise ValueError("Could not find feature directory in worktree")
            else:
                raise ValueError("Could not locate kitty-specs directory in worktree")
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
