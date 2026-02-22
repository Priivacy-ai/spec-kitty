"""Tests for constitution compiler bundle generation."""

from pathlib import Path

import pytest

from specify_cli.constitution.compiler import compile_constitution, write_compiled_constitution
from specify_cli.constitution.interview import default_interview


def test_compile_constitution_contains_governance_activation_block() -> None:
    interview = default_interview(mission="software-dev", profile="minimal")

    compiled = compile_constitution(mission="software-dev", interview=interview)

    assert compiled.mission == "software-dev"
    assert compiled.template_set == "software-dev-default"
    assert "## Governance Activation" in compiled.markdown
    assert "selected_directives" in compiled.markdown
    assert len(compiled.references) >= 2


def test_write_compiled_constitution_writes_bundle(tmp_path: Path) -> None:
    interview = default_interview(mission="software-dev", profile="minimal")
    compiled = compile_constitution(mission="software-dev", interview=interview)

    result = write_compiled_constitution(tmp_path, compiled, force=True)

    assert "constitution.md" in result.files_written
    assert "references.yaml" in result.files_written
    assert (tmp_path / "constitution.md").exists()
    assert (tmp_path / "references.yaml").exists()

    library_files = sorted((tmp_path / "library").glob("*.md"))
    assert library_files


def test_write_compiled_constitution_requires_force_when_existing(tmp_path: Path) -> None:
    interview = default_interview(mission="software-dev", profile="minimal")
    compiled = compile_constitution(mission="software-dev", interview=interview)

    write_compiled_constitution(tmp_path, compiled, force=True)

    with pytest.raises(FileExistsError):
        write_compiled_constitution(tmp_path, compiled, force=False)
