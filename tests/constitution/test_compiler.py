"""Scope: mock-boundary tests for constitution compiler bundle generation — no real git."""

from pathlib import Path

import pytest

from specify_cli.constitution.compiler import compile_constitution, write_compiled_constitution
from specify_cli.constitution.interview import default_interview

pytestmark = pytest.mark.fast


def test_compile_constitution_contains_governance_activation_block() -> None:
    """Compiled constitution includes mission metadata and governance activation section."""
    # Arrange
    interview = default_interview(mission="software-dev", profile="minimal")

    # Assumption check
    assert interview.mission == "software-dev", "interview must be for software-dev"

    # Act
    compiled = compile_constitution(mission="software-dev", interview=interview)

    # Assert
    assert compiled.mission == "software-dev"
    assert compiled.template_set == "software-dev-default"
    assert "## Governance Activation" in compiled.markdown
    assert "selected_directives" in compiled.markdown
    assert len(compiled.references) >= 2


def test_write_compiled_constitution_writes_bundle(tmp_path: Path) -> None:
    """write_compiled_constitution creates constitution.md, references.yaml, and library files."""
    # Arrange
    interview = default_interview(mission="software-dev", profile="minimal")
    compiled = compile_constitution(mission="software-dev", interview=interview)

    # Assumption check
    assert not (tmp_path / "constitution.md").exists(), "target directory must be empty"

    # Act
    result = write_compiled_constitution(tmp_path, compiled, force=True)

    # Assert
    assert "constitution.md" in result.files_written
    assert "references.yaml" in result.files_written
    assert (tmp_path / "constitution.md").exists()
    assert (tmp_path / "references.yaml").exists()

    library_files = sorted((tmp_path / "library").glob("*.md"))
    assert library_files


def test_write_compiled_constitution_requires_force_when_existing(tmp_path: Path) -> None:
    """Writing to an existing bundle raises FileExistsError when force=False."""
    # Arrange
    interview = default_interview(mission="software-dev", profile="minimal")
    compiled = compile_constitution(mission="software-dev", interview=interview)
    write_compiled_constitution(tmp_path, compiled, force=True)

    # Assumption check
    assert (tmp_path / "constitution.md").exists(), "first write must have succeeded"

    # Act / Assert
    with pytest.raises(FileExistsError):
        write_compiled_constitution(tmp_path, compiled, force=False)
