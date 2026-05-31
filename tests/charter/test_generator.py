"""Scope: mock-boundary tests for charter generator — no real git."""

import os
from pathlib import Path

import pytest

from charter.compiler import CompiledCharter, write_compiled_charter
from charter.generator import build_charter_draft, write_charter

pytestmark = pytest.mark.fast


def test_build_charter_draft_defaults() -> None:
    """Draft built with defaults keeps packaged doctrine selections neutral."""
    # Arrange
    # (no precondition)

    # Assumption check
    # (no precondition)

    # Act
    draft = build_charter_draft(mission="software-dev")

    # Assert
    assert draft.template_set == "software-dev-default"
    assert draft.selected_directives == []
    assert draft.selected_paradigms == []
    assert "selected_directives" in draft.markdown


def test_build_charter_draft_invalid_template_set_raises() -> None:
    """Requesting an unknown template set raises ValueError."""
    # Arrange
    # (no precondition)

    # Assumption check
    # (no precondition)

    # Act / Assert
    with pytest.raises(ValueError):
        build_charter_draft(mission="software-dev", template_set="not-real")


def test_write_charter_respects_force(tmp_path: Path) -> None:
    """write_charter raises FileExistsError when force=False and file exists."""
    # Arrange
    path = tmp_path / "charter.md"
    write_charter(path, "# One", force=False)

    # Assumption check
    assert path.exists(), "first write must have created the file"

    # Act / Assert
    with pytest.raises(FileExistsError):
        write_charter(path, "# Two", force=False)

    write_charter(path, "# Two", force=True)

    # Assert
    assert path.read_text(encoding="utf-8") == "# Two"


@pytest.mark.requires_symlinks
def test_write_charter_rejects_symlink_even_with_force(tmp_path: Path) -> None:
    target = tmp_path / "outside.md"
    target.write_text("# Outside\n", encoding="utf-8")
    path = tmp_path / "charter.md"
    try:
        os.symlink(target, path)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported on this platform")

    with pytest.raises(FileExistsError, match="is a symlink"):
        write_charter(path, "# Two", force=True)

    assert target.read_text(encoding="utf-8") == "# Outside\n"


@pytest.mark.requires_symlinks
def test_write_compiled_charter_rejects_symlink_even_with_force(tmp_path: Path) -> None:
    target = tmp_path / "outside.md"
    target.write_text("# Outside\n", encoding="utf-8")
    output_dir = tmp_path / ".kittify" / "charter"
    output_dir.mkdir(parents=True)
    try:
        os.symlink(target, output_dir / "charter.md")
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported on this platform")
    compiled = CompiledCharter(
        mission="software-dev",
        template_set="software-dev-default",
        selected_paradigms=[],
        selected_directives=[],
        available_tools=[],
        markdown="# Generated\n",
        references=[],
    )

    with pytest.raises(FileExistsError, match="is a symlink"):
        write_compiled_charter(output_dir, compiled, force=True)

    assert target.read_text(encoding="utf-8") == "# Outside\n"
