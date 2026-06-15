"""Agent context management commands."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, cast

import typer
from rich.console import Console
from typing_extensions import Annotated

from specify_cli.cli.selector_resolution import resolve_mission_handle
from specify_cli.core.paths import locate_project_root
from mission_runtime import (
    ACTION_NAMES,
    ActionName,
    ActionContextError,
    resolve_action_context,
)

app = typer.Typer(
    name="context",
    help="Agent context management commands",
    no_args_is_help=True
)

console = Console()


def _find_feature_directory(
    repo_root: Path,
    cwd: Path,  # noqa: ARG001 -- kept for signature compatibility
    explicit_mission: str | None = None,
) -> Path:
    """Find the mission directory from an explicit mission handle.

    Routes through the single read primitive
    (:func:`specify_cli.missions._read_path_resolver.resolve_mission_read_path`),
    so a ``--mission <mid8>`` handle resolves to the same directory as the full
    slug (F-001/F-003/F-004). There is **no silent fallback** to a
    wrong-but-plausible primary-checkout path: an unresolvable handle raises a
    structured :class:`ActionContextError` (``FEATURE_CONTEXT_UNRESOLVED``) and
    an ambiguous handle raises ``MISSION_AMBIGUOUS_SELECTOR`` (C-CTX-4 / C-009).

    Args:
        repo_root: Repository root path
        cwd: Current working directory (unused — kept for signature compatibility)
        explicit_mission: Mission handle provided explicitly (required)

    Returns:
        Path to mission directory

    Raises:
        ActionContextError: If no handle is provided, the handle is ambiguous, or
            it resolves to no existing mission directory (structured error).
    """
    from specify_cli.lanes.branch_naming import mid8_from_slug
    from specify_cli.missions._read_path_resolver import (
        MissionSelectorAmbiguous,
        StatusReadPathNotFound,
        resolve_mission_read_path,
    )

    raw_handle = explicit_mission.strip() if explicit_mission else None
    if not raw_handle:
        raise ActionContextError(
            "FEATURE_CONTEXT_UNRESOLVED", "--mission <slug> is required"
        )
    try:
        feature_dir: Path = cast(
            Path,
            resolve_mission_read_path(
                repo_root,
                raw_handle,
                mid8_from_slug(raw_handle),
                require_exists=True,
            ),
        )
    except MissionSelectorAmbiguous as exc:
        raise ActionContextError(exc.error_code, str(exc)) from exc
    except StatusReadPathNotFound as exc:
        raise ActionContextError(
            "FEATURE_CONTEXT_UNRESOLVED",
            f"Mission not found for handle {raw_handle!r}; checked the "
            f"coordination worktree and the primary checkout. {exc}",
        ) from exc
    return feature_dir


@app.command(name="resolve")
def resolve_context(
    action: Annotated[
        str,
        typer.Option(
            "--action",
            help=(
                "Action to resolve context for "
                f"({', '.join(ACTION_NAMES)})"
            ),
        ),
    ],
    mission: Annotated[str | None, typer.Option("--mission", help="Mission slug (e.g., '020-my-mission')")] = None,
    wp_id: Annotated[str | None, typer.Option("--wp-id", help="Work package ID (e.g., WP01)")] = None,
    agent: Annotated[str | None, typer.Option("--agent", help="Agent name for exact command rendering")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output results as JSON")] = False,
) -> None:
    """Resolve canonical feature/work-package/action context for prompt execution."""
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

        raw_handle = mission.strip() if mission else None
        if not raw_handle:
            raise ActionContextError("MISSING_MISSION", "--mission <slug> is required")
        mission_resolved = resolve_mission_handle(raw_handle, repo_root, json_mode=json_output)
        mission_slug = mission_resolved.mission_slug

        context = resolve_action_context(
            repo_root,
            action=cast(ActionName, action),
            feature=mission_slug,
            wp_id=wp_id,
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
        raise typer.Exit(1)



# update-context command removed — agent_context.py was deleted in WP10.
# Agent command files are now thin shims generated by shims/generator.py.
