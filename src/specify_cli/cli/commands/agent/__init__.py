"""Agent command namespace for AI agents to execute spec-kitty mission actions programmatically."""

import typer
from typing_extensions import Annotated

from . import config, mission, tasks, context, release, workflow, status
from specify_cli.cli.commands import shim as shim_module

app = typer.Typer(
    name="agent",
    help="Commands for AI agents to execute spec-kitty mission actions programmatically",
    no_args_is_help=True
)

# Register sub-apps for each command module.
# `mission` / `action` are canonical. `feature` / `workflow` remain compatibility aliases.
app.add_typer(config.app, name="config")
app.add_typer(mission.app, name="mission", help="Mission lifecycle commands for AI agents")
app.add_typer(mission.app, name="feature", help="Legacy compatibility alias for `agent mission`")
app.add_typer(tasks.app, name="tasks")
app.add_typer(context.app, name="context")
app.add_typer(release.app, name="release")
app.add_typer(workflow.app, name="action", help="Mission action commands that display prompts and instructions for agents")
app.add_typer(workflow.app, name="workflow", help="Legacy compatibility alias for `agent action`")
app.add_typer(status.app, name="status")
app.add_typer(shim_module.app, name="shim")


@app.command(name="check-prerequisites", hidden=True)
def check_prerequisites_alias(
    mission_slug: Annotated[
        str | None,
        typer.Option("--feature", help="Mission slug (legacy flag name)")
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON format")] = False,
    paths_only: Annotated[bool, typer.Option("--paths-only", help="Only output path variables")] = False,
    include_tasks: Annotated[bool, typer.Option("--include-tasks", help="Include tasks.md in validation")] = False,
    require_tasks: Annotated[
        bool,
        typer.Option("--require-tasks", hidden=True, help="Deprecated alias for --include-tasks"),
    ] = False,
) -> None:
    """Deprecated compatibility alias forwarding to agent mission check-prerequisites."""
    mission.check_prerequisites(
        feature=mission_slug,
        json_output=json_output,
        paths_only=paths_only,
        include_tasks=include_tasks,
        require_tasks=require_tasks,
    )


__all__ = ["app"]
