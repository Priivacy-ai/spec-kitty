"""Agent context management commands."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from typing_extensions import Annotated

from specify_cli.core.paths import locate_project_root
from specify_cli.core.agent_context import (
    parse_plan_for_tech_stack,
    update_agent_context as update_context_file,
    get_supported_agent_types,
    get_agent_file_path,
)
from specify_cli.core.feature_detection import (
    detect_feature_directory,
    FeatureDetectionError,
)

app = typer.Typer(
    name="context",
    help="Agent context management commands",
    no_args_is_help=True
)

console = Console()


def _find_feature_directory(repo_root: Path, cwd: Path, explicit_feature: str | None = None) -> Path:
    """Find the current feature directory using centralized detection.

    This function now uses the centralized feature detection module
    to provide deterministic, consistent behavior across all commands.

    Args:
        repo_root: Repository root path
        cwd: Current working directory
        explicit_feature: Optional explicit feature slug from --feature flag

    Returns:
        Path to feature directory

    Raises:
        ValueError: If feature directory cannot be determined
        FeatureDetectionError: If detection fails
    """
    try:
        return detect_feature_directory(
            repo_root,
            explicit_feature=explicit_feature,
            cwd=cwd,
            mode="strict"  # Raise error if ambiguous
        )
    except FeatureDetectionError as e:
        # Convert to ValueError for backward compatibility
        raise ValueError(str(e)) from e


@app.command(name="update-context")
def update_context(
    feature: Annotated[Optional[str], typer.Option("--feature", help="Feature slug (e.g., '020-my-feature')")] = None,
    agent_type: Annotated[
        Optional[str],
        typer.Option(
            "--agent-type",
            "-a",
            help=f"Agent type to update. Supported: {', '.join(get_supported_agent_types())}. Defaults to 'claude'."
        )
    ] = "claude",
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Output results as JSON for agent parsing"
        )
    ] = False,
) -> None:
    """Update agent context file with tech stack from plan.md.

    This command:
    1. Detects current feature directory (worktree or main repo)
    2. Parses plan.md to extract tech stack information
    3. Updates specified agent file (CLAUDE.md, GEMINI.md, etc.)
    4. Preserves manual additions between <!-- MANUAL ADDITIONS --> markers
    5. Updates Active Technologies and Recent Changes sections

    Examples:
        # Update Claude context (default)
        spec-kitty agent update-context

        # Update Gemini context with JSON output
        spec-kitty agent update-context --agent-type gemini --json

        # Update from within a worktree
        cd .worktrees/008-feature
        spec-kitty agent update-context
    """
    try:
        # Locate repository root
        repo_root = locate_project_root()
        cwd = Path.cwd()

        # Find feature directory using centralized detection
        try:
            feature_dir = _find_feature_directory(repo_root, cwd, explicit_feature=feature)
        except ValueError as e:
            if json_output:
                print(json.dumps({"error": str(e), "success": False}))
            else:
                console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)

        # Get plan path
        plan_path = feature_dir / "plan.md"
        if not plan_path.exists():
            error_msg = f"Plan file not found: {plan_path}"
            if json_output:
                print(json.dumps({"error": error_msg, "success": False}))
            else:
                console.print(f"[red]Error:[/red] {error_msg}")
                console.print(f"[yellow]Hint:[/yellow] Run /spec-kitty.plan to create plan.md first")
            sys.exit(1)

        # Verify agent file exists
        agent_file_path = get_agent_file_path(agent_type, repo_root)
        if not agent_file_path.exists():
            error_msg = f"Agent file not found: {agent_file_path}"
            if json_output:
                print(json.dumps({"error": error_msg, "success": False}))
            else:
                console.print(f"[red]Error:[/red] {error_msg}")
                console.print(f"[yellow]Hint:[/yellow] Create {agent_file_path.name} first")
            sys.exit(1)

        # Parse tech stack from plan.md
        tech_stack = parse_plan_for_tech_stack(plan_path)

        # Extract feature slug from directory name
        feature_slug = feature_dir.name

        # Update agent context file
        update_context_file(
            agent_type=agent_type,
            tech_stack=tech_stack,
            feature_slug=feature_slug,
            repo_root=repo_root,
            feature_dir=feature_dir,
        )

        # Output result
        if json_output:
            result = {
                "success": True,
                "agent_type": agent_type,
                "agent_file": str(agent_file_path),
                "feature": feature_slug,
                "tech_stack": {k: v for k, v in tech_stack.items() if v},
            }
            print(json.dumps(result, indent=2))
        else:
            console.print(f"[green]✓[/green] Updated {agent_file_path.name}")
            console.print(f"  Feature: {feature_slug}")
            if tech_stack.get("language"):
                console.print(f"  Language: {tech_stack['language']}")
            if tech_stack.get("dependencies"):
                console.print(f"  Dependencies: {tech_stack['dependencies']}")
            if tech_stack.get("storage"):
                console.print(f"  Storage: {tech_stack['storage']}")

    except Exception as e:
        if json_output:
            print(json.dumps({"error": str(e), "success": False}))
        else:
            console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
