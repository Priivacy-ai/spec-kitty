"""Scope: mock-boundary tests for constitution generator — no real git."""

from pathlib import Path

import pytest

from specify_cli.constitution.generator import build_constitution_draft, write_constitution

pytestmark = pytest.mark.fast


def test_build_constitution_draft_defaults() -> None:
    """Draft built with defaults selects expected template set, directives, and paradigms."""
    # Arrange
    # (no precondition)

    # Assumption check
    # (no precondition)

    # Act
    draft = build_constitution_draft(mission="software-dev")

    # Assert
    assert draft.template_set == "software-dev-default"
    assert "TEST_FIRST" in draft.selected_directives
    assert "test-first" in draft.selected_paradigms
    assert "selected_directives" in draft.markdown


def test_build_constitution_draft_invalid_template_set_raises() -> None:
    """Requesting an unknown template set raises ValueError."""
    # Arrange
    # (no precondition)

    # Assumption check
    # (no precondition)

    # Act / Assert
    with pytest.raises(ValueError):
        build_constitution_draft(mission="software-dev", template_set="not-real")


def test_write_constitution_respects_force(tmp_path: Path) -> None:
    """write_constitution raises FileExistsError when force=False and file exists."""
    # Arrange
    path = tmp_path / "constitution.md"
    write_constitution(path, "# One", force=False)

    # Assumption check
    assert path.exists(), "first write must have created the file"

    # Act / Assert
    with pytest.raises(FileExistsError):
        write_constitution(path, "# Two", force=False)

    write_constitution(path, "# Two", force=True)

    # Assert
    assert path.read_text(encoding="utf-8") == "# Two"
