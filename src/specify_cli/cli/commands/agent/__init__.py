"""Agent command namespace for AI agents to execute spec-kitty workflows programmatically."""

import typer
from typing_extensions import Annotated

from . import feature, tasks, context, release, workflow

app = typer.Typer(
    name="agent",
    help="Commands for AI agents to execute spec-kitty workflows programmatically",
    no_args_is_help=True
)

# Register sub-apps for each command module
app.add_typer(feature.app, name="feature")
app.add_typer(tasks.app, name="tasks")
app.add_typer(context.app, name="context")
app.add_typer(release.app, name="release")
app.add_typer(workflow.app, name="workflow")

__all__ = ["app"]
