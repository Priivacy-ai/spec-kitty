"""CLI coverage for workflow portability commands."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

pytestmark = [pytest.mark.unit, pytest.mark.fast]

from specify_cli.cli.commands.workflow import app

runner = CliRunner()


def test_workflow_import_validates_and_copies_to_project_overrides(tmp_path: Path) -> None:
    source = tmp_path / "solo-fast.yaml"
    source.write_text(
        """
workflow_id: solo-fast
description: Portable workflow.
version: 1
initial: specify
actions:
  - action_name: specify
    description: Create a mission specification
    terminal: true
""".lstrip(),
        encoding="utf-8",
    )
    project_root = tmp_path / "project"

    result = runner.invoke(app, ["import", str(source), "--project-root", str(project_root)])

    assert result.exit_code == 0, result.output
    destination = project_root / ".kittify" / "overrides" / "workflows" / "solo-fast.yaml"
    assert destination.exists()
    assert destination.read_text(encoding="utf-8") == source.read_text(encoding="utf-8")
    assert str(destination) in result.output


def test_workflow_export_uses_project_override_precedence(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    workflow_dir = project_root / ".kittify" / "overrides" / "workflows"
    workflow_dir.mkdir(parents=True)
    source = workflow_dir / "software-dev-default.yaml"
    source.write_text(
        """
workflow_id: software-dev-default
description: Project default workflow.
version: 1
initial: specify
actions:
  - action_name: specify
    description: Create a mission specification
    terminal: true
""".lstrip(),
        encoding="utf-8",
    )
    exported = tmp_path / "exported.yaml"

    result = runner.invoke(
        app,
        [
            "export",
            "software-dev-default",
            str(exported),
            "--project-root",
            str(project_root),
        ],
    )

    assert result.exit_code == 0, result.output
    assert exported.read_text(encoding="utf-8") == source.read_text(encoding="utf-8")
    assert str(exported) in result.output


def test_workflow_import_refuses_overwrite_without_force(tmp_path: Path) -> None:
    source = tmp_path / "solo-fast.yaml"
    source.write_text(
        """
workflow_id: solo-fast
description: Portable workflow.
version: 1
initial: specify
actions:
  - action_name: specify
    description: Create a mission specification
    terminal: true
""".lstrip(),
        encoding="utf-8",
    )
    project_root = tmp_path / "project"
    destination = project_root / ".kittify" / "overrides" / "workflows" / "solo-fast.yaml"
    destination.parent.mkdir(parents=True)
    destination.write_text("existing", encoding="utf-8")

    result = runner.invoke(app, ["import", str(source), "--project-root", str(project_root)])

    assert result.exit_code != 0
    assert destination.read_text(encoding="utf-8") == "existing"


def test_workflow_list_omits_invalid_project_files(tmp_path: Path) -> None:
    workflow_dir = tmp_path / ".kittify" / "overrides" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "bad name.yaml").write_text(
        """
workflow_id: bad name
description: Invalid slug.
version: 1
initial: specify
actions:
  - action_name: specify
    description: Create a mission specification
    terminal: true
""".lstrip(),
        encoding="utf-8",
    )
    (workflow_dir / "valid.yaml").write_text(
        """
workflow_id: valid
description: Valid project workflow.
version: 1
initial: specify
actions:
  - action_name: specify
    description: Create a mission specification
    terminal: true
""".lstrip(),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["list", "--project-root", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert "valid" in result.output
    assert "bad name" not in result.output
