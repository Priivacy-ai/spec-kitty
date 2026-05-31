"""Workflow portability commands."""

from __future__ import annotations

import shutil
from pathlib import Path

import typer

from specify_cli.next._internal_runtime.workflow_registry import (
    list_available_workflows,
    load_workflow_file,
    resolve_workflow_path,
)

app = typer.Typer(name="workflow", help="Manage mission workflow definitions")


@app.command(name="list")
def list_workflows(
    project_root: Path = typer.Option(
        Path("."),
        "--project-root",
        help="Project root used for .kittify workflow discovery.",
    ),
) -> None:
    """List workflow ids available to a project."""
    for workflow_id in list_available_workflows(project_root=project_root.resolve()):
        typer.echo(workflow_id)


@app.command(name="export")
def export_workflow(
    workflow_id: str = typer.Argument(..., help="Workflow id to export."),
    output: Path = typer.Argument(..., help="Destination file or directory."),
    project_root: Path = typer.Option(
        Path("."),
        "--project-root",
        help="Project root used for .kittify workflow discovery.",
    ),
    force: bool = typer.Option(False, "--force", help="Overwrite an existing destination file."),
) -> None:
    """Export a resolvable workflow YAML file."""
    source = resolve_workflow_path(workflow_id, project_root=project_root.resolve())
    load_workflow_file(source, requested_workflow_id=workflow_id)
    destination = _destination_path(output, workflow_id=workflow_id)
    _copy_workflow(source, destination, force=force)
    typer.echo(str(destination))


@app.command(name="import")
def import_workflow(
    source: Path = typer.Argument(..., help="Workflow YAML file to import."),
    project_root: Path = typer.Option(
        Path("."),
        "--project-root",
        help="Project root that receives the workflow override.",
    ),
    force: bool = typer.Option(False, "--force", help="Overwrite an existing workflow file."),
) -> None:
    """Import a workflow YAML into `.kittify/overrides/workflows`."""
    workflow = load_workflow_file(source)
    destination = (
        project_root.resolve()
        / ".kittify"
        / "overrides"
        / "workflows"
        / f"{workflow.workflow_id}.yaml"
    )
    _copy_workflow(source, destination, force=force)
    typer.echo(str(destination))


def _destination_path(output: Path, *, workflow_id: str) -> Path:
    if output.exists() and output.is_dir():
        return output / f"{workflow_id}.yaml"
    if str(output).endswith(("/", "\\")):
        return output / f"{workflow_id}.yaml"
    return output


def _copy_workflow(source: Path, destination: Path, *, force: bool) -> None:
    if destination.exists() and not force:
        raise typer.BadParameter(f"Destination exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
