"""Scope: mock-boundary tests for charter generator — no real git."""

from pathlib import Path

import pytest

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
