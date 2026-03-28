"""Agent context management commands."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import cast

import typer
from rich.console import Console
from typing import Annotated

from specify_cli.cli.commands._flag_utils import resolve_mission_or_feature
from specify_cli.core.paths import locate_project_root
from specify_cli.core.agent_context import (
    parse_plan_for_tech_stack,
    update_agent_context as update_context_file,
    get_supported_agent_types,
    get_agent_file_path,
)
from specify_cli.core.mission_detection import (
    detect_mission_directory,
    MissionDetectionError,
)
from specify_cli.core.execution_context import (
    ACTION_NAMES,
    ActionName,
    ActionContextError,
    resolve_action_context,
)

app = typer.Typer(name="context", help="Agent context management commands", no_args_is_help=True)

console = Console()


def _find_mission_directory(repo_root: Path, cwd: Path, explicit_mission: str | None = None) -> Path:
    """Find the current mission directory using centralized detection.

    This function now uses the centralized mission detection module
    to provide deterministic, consistent behavior across all commands.

    Args:
        repo_root: Repository root path
        cwd: Current working directory
        explicit_mission: Optional explicit mission slug from --mission flag

    Returns:
        Path to mission directory

    Raises:
        ValueError: If mission directory cannot be determined
        MissionDetectionError: If detection fails
    """
    try:
        return detect_mission_directory(
            repo_root,
            explicit_mission=explicit_mission,
            cwd=cwd,
            mode="strict",  # Raise error if ambiguous
        )
    except MissionDetectionError as e:
        # Convert to ValueError for backward compatibility
        raise ValueError(str(e)) from e


@app.command(name="resolve")
def resolve_context(
    action: Annotated[
        str,
        typer.Option(
            "--action",
            help=(f"Action to resolve context for ({', '.join(ACTION_NAMES)})"),
        ),
    ],
    mission: Annotated[str | None, typer.Option("--mission", help="Mission slug (e.g., '020-my-mission')")] = None,
    feature: Annotated[str | None, typer.Option("--feature", hidden=True, help="[Deprecated] Use --mission")] = None,
    wp_id: Annotated[str | None, typer.Option("--wp-id", help="Work package ID (e.g., WP01)")] = None,
    base: Annotated[str | None, typer.Option("--base", help="Explicit base WP for implement")] = None,
    agent: Annotated[str | None, typer.Option("--agent", help="Agent name for exact command rendering")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output results as JSON")] = False,
) -> None:
    """Resolve canonical mission/work-package/action context for prompt execution."""
    mission_flag = resolve_mission_or_feature(mission, feature)
    try:
        repo_root = locate_project_root()
        if repo_root is None:
            raise ActionContextError(
                "PROJECT_ROOT_UNRESOLVED",
                "Could not locate project root.",
            )

        if action not in ACTION_NAMES:
            raise ActionContextError(
                "INVALID_ACTION",
                f"Invalid action '{action}'. Expected one of: {', '.join(ACTION_NAMES)}.",
            )

        context = resolve_action_context(
            repo_root,
            action=cast(ActionName, action),
            mission=mission_flag,
            wp_id=wp_id,
            base=base,
            agent=agent,
            cwd=Path.cwd(),
        )

        if json_output:
            print(json.dumps({"success": True, **context.to_dict()}, indent=2))
        else:
            console.print(f"[green]✓[/green] Resolved {action} context")
            console.print(f"  Mission: {context.mission_slug} ({context.detection_method})")
            console.print(f"  Target branch: {context.target_branch}")
            if context.wp_id:
                console.print(f"  Work package: {context.wp_id} ({context.lane})")
            if context.workspace_path:
                console.print(f"  Workspace: {context.workspace_path}")
            for name, command in context.commands.items():
                console.print(f"  {name}: {command}")
    except ActionContextError as exc:
        if json_output:
            print(json.dumps({"success": False, "error_code": exc.code, "error": str(exc)}, indent=2))
        else:
            console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc


@app.command(name="update-context")
def update_context(
    mission: Annotated[str | None, typer.Option("--mission", help="Mission slug (e.g., '020-my-mission')")] = None,
    feature: Annotated[str | None, typer.Option("--feature", hidden=True, help="[Deprecated] Use --mission")] = None,
    agent_type: Annotated[
        str | None,
        typer.Option(
            "--agent-type",
            "-a",
            help=f"Agent type to update. Supported: {', '.join(get_supported_agent_types())}. Defaults to 'claude'.",
        ),
    ] = "claude",
    json_output: Annotated[bool, typer.Option("--json", help="Output results as JSON for agent parsing")] = False,
) -> None:
    """Update agent context file with tech stack from plan.md.

    This command:
    1. Detects current mission directory (worktree or main repo)
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
        cd .worktrees/008-mission
        spec-kitty agent update-context
    """
    mission_flag = resolve_mission_or_feature(mission, feature)
    try:
        # Locate repository root
        repo_root = locate_project_root()
        if repo_root is None:
            error_msg = "Could not locate project root"
            if json_output:
                print(json.dumps({"error": error_msg, "success": False}))
            else:
                console.print(f"[red]Error:[/red] {error_msg}")
            sys.exit(1)
        cwd = Path.cwd()

        # Narrow agent_type: fall back to "claude" if None
        resolved_agent_type: str = agent_type if agent_type is not None else "claude"

        # Find mission directory using centralized detection
        try:
            mission_dir = _find_mission_directory(repo_root, cwd, explicit_mission=mission_flag)
        except ValueError as e:
            if json_output:
                print(json.dumps({"error": str(e), "success": False}))
            else:
                console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)

        # Get plan path
        plan_path = mission_dir / "plan.md"
        if not plan_path.exists():
            error_msg = f"Plan file not found: {plan_path}"
            if json_output:
                print(json.dumps({"error": error_msg, "success": False}))
            else:
                console.print(f"[red]Error:[/red] {error_msg}")
                console.print("[yellow]Hint:[/yellow] Run /spec-kitty.plan to create plan.md first")
            sys.exit(1)

        # Verify agent file exists
        agent_file_path = get_agent_file_path(resolved_agent_type, repo_root)
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

        # Extract mission slug from directory name
        mission_slug = mission_dir.name

        # Update agent context file
        update_context_file(
            agent_type=resolved_agent_type,
            tech_stack=tech_stack,
            mission_slug=mission_slug,
            repo_root=repo_root,
            mission_dir=mission_dir,
        )

        # Output result
        if json_output:
            result = {
                "success": True,
                "agent_type": agent_type,
                "agent_file": str(agent_file_path),
                "mission": mission_slug,
                "tech_stack": {k: v for k, v in tech_stack.items() if v},
            }
            print(json.dumps(result, indent=2))
        else:
            console.print(f"[green]✓[/green] Updated {agent_file_path.name}")
            console.print(f"  Mission: {mission_slug}")
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
