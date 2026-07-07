"""Regression tests for /spec-kitty.tasks ownership metadata guidance."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.fast]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_TASKS_PROMPT_SURFACES = (
    _REPO_ROOT
    / "src"
    / "doctrine"
    / "missions"
    / "mission-steps"
    / "software-dev"
    / "tasks"
    / "prompt.md",
    _REPO_ROOT
    / ".kittify"
    / "overrides"
    / "missions"
    / "software-dev"
    / "command-templates"
    / "tasks.md",
)


def _ownership_metadata_section(prompt_path: Path) -> str:
    text = prompt_path.read_text(encoding="utf-8")
    marker = "**OWNERSHIP METADATA (required by finalize-tasks)**"
    start = text.index(marker)
    next_heading = text.index("**Ownership rules**", start)
    return text[start:next_heading]


@pytest.mark.parametrize("prompt_path", _TASKS_PROMPT_SURFACES, ids=lambda path: path.as_posix())
def test_tasks_prompt_documents_create_intent_with_required_ownership_fields(prompt_path: Path) -> None:
    section = _ownership_metadata_section(prompt_path)

    for field in ("`execution_mode`", "`owned_files`", "`authoritative_surface`", "`create_intent`"):
        assert field in section


@pytest.mark.parametrize("prompt_path", _TASKS_PROMPT_SURFACES, ids=lambda path: path.as_posix())
def test_tasks_prompt_explains_create_intent_for_planned_new_owned_files(prompt_path: Path) -> None:
    section = _ownership_metadata_section(prompt_path)

    assert "planned-new" in section or "planned new" in section
    assert "zero-match" in section or "zero match" in section


@pytest.mark.parametrize("prompt_path", _TASKS_PROMPT_SURFACES, ids=lambda path: path.as_posix())
def test_tasks_prompt_prevents_duplicate_create_intent_stubs(prompt_path: Path) -> None:
    section = _ownership_metadata_section(prompt_path)

    assert "single `create_intent` key" in section
    assert "stub `create_intent: []`" in section
    assert "replace it instead of adding a duplicate block" in section
