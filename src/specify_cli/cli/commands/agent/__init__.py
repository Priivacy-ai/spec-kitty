"""Agent command namespace for AI agents to execute spec-kitty mission actions programmatically."""

import typer
from typing_extensions import Annotated

from . import config, mission, tasks, context, release, workflow, status, tests
from specify_cli.cli.commands.decision import decision_app

app = typer.Typer(
    name="agent",
    help="Commands for AI agents to execute spec-kitty mission actions programmatically",
    no_args_is_help=True
)

# Register sub-apps for each command module.
# `mission` and `action` are the canonical command namespaces.
app.add_typer(config.app, name="config")
app.add_typer(mission.app, name="mission", help="Mission lifecycle commands for AI agents")
app.add_typer(tasks.app, name="tasks")
app.add_typer(context.app, name="context")
app.add_typer(release.app, name="release")
app.add_typer(workflow.app, name="action", help="Mission action commands that display prompts and instructions for agents")
app.add_typer(status.app, name="status")
app.add_typer(tests.app, name="tests")
app.add_typer(decision_app, name="decision")


@app.command(name="check-prerequisites", hidden=True)
def check_prerequisites_alias(
    mission_slug: Annotated[
        str | None,
        typer.Option("--mission", help="Mission slug")
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
