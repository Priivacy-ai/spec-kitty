"""Scope: project resolver unit tests — no real git or subprocesses."""

import pytest
from specify_cli.core.project_resolver import (
    locate_project_root,
    resolve_template_path,
)

pytestmark = pytest.mark.fast


def test_locate_project_root_and_template_resolution(tmp_path):
    """locate_project_root finds .kittify root and resolve_template_path prefers mission-local template."""
    # Arrange
    project = tmp_path / "workspace"
    (project / ".kittify" / "missions" / "software-dev" / "templates").mkdir(parents=True)
    (project / ".kittify" / "templates").mkdir(parents=True)
    (project / ".kittify" / "missions" / "software-dev" / "templates" / "foo.txt").write_text(
        "mission template",
        encoding="utf-8",
    )
    (project / ".kittify" / "templates" / "foo.txt").write_text("fallback", encoding="utf-8")

    nested = project / "nested" / "deeper"
    nested.mkdir(parents=True)

    # Assumption check
    assert nested.exists(), "nested directory must exist for root search to traverse upward"

    # Act
    root = locate_project_root(nested)
    template_path = resolve_template_path(project, "software-dev", "foo.txt")

    # Assert
    assert root == project
    assert template_path == project / ".kittify" / "missions" / "software-dev" / "templates" / "foo.txt"
