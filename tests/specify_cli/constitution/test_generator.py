"""Tests for deterministic constitution generator."""

from pathlib import Path

import pytest

from specify_cli.constitution.generator import build_constitution_draft, write_constitution


def test_build_constitution_draft_defaults() -> None:
    draft = build_constitution_draft(mission="software-dev")
    assert draft.template_set == "software-dev-default"
    assert "TEST_FIRST" in draft.selected_directives
    assert "test-first" in draft.selected_paradigms
    assert "selected_directives" in draft.markdown


def test_build_constitution_draft_invalid_template_set_raises() -> None:
    with pytest.raises(ValueError):
        build_constitution_draft(mission="software-dev", template_set="not-real")


def test_write_constitution_respects_force(tmp_path: Path) -> None:
    path = tmp_path / "constitution.md"
    write_constitution(path, "# One", force=False)

    with pytest.raises(FileExistsError):
        write_constitution(path, "# Two", force=False)

    write_constitution(path, "# Two", force=True)
    assert path.read_text(encoding="utf-8") == "# Two"
