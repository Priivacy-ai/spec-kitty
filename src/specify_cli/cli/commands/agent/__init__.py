"""Agent command namespace for AI agents to execute spec-kitty workflows programmatically."""

from typing import Annotated

import typer

from specify_cli.cli.commands._flag_utils import resolve_mission_or_feature
from . import config, context, feature, profile, release, status, tasks, workflow

app = typer.Typer(
    name="agent", help="Commands for AI agents to execute spec-kitty workflows programmatically", no_args_is_help=True
)

# Register sub-apps for each command module
app.add_typer(config.app, name="config")
app.add_typer(feature.app, name="mission")
app.add_typer(feature.app, name="feature")  # backward-compat alias
app.add_typer(tasks.app, name="tasks")
app.add_typer(context.app, name="context")
app.add_typer(profile.app, name="profile")
app.add_typer(release.app, name="release")
app.add_typer(workflow.app, name="workflow")
app.add_typer(status.app, name="status")


@app.command(name="check-prerequisites", hidden=True)
def check_prerequisites_alias(
    feature_slug: Annotated[str | None, typer.Option("--mission", help="Mission slug")] = None,
    feature_slug_deprecated: Annotated[str | None, typer.Option("--feature", hidden=True, help="[Deprecated] Use --mission")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON format")] = False,
    paths_only: Annotated[bool, typer.Option("--paths-only", help="Only output path variables")] = False,
    include_tasks: Annotated[bool, typer.Option("--include-tasks", help="Include tasks.md in validation")] = False,
    require_tasks: Annotated[
        bool,
        typer.Option("--require-tasks", hidden=True, help="Deprecated alias for --include-tasks"),
    ] = False,
) -> None:
    """Deprecated compatibility alias forwarding to agent feature check-prerequisites."""
    resolved = resolve_mission_or_feature(feature_slug, feature_slug_deprecated)
    feature.check_prerequisites(
        feature=resolved,
        json_output=json_output,
        paths_only=paths_only,
        include_tasks=include_tasks,
        require_tasks=require_tasks,
    )


__all__ = ["app"]
