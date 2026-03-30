"""Scope: mock-boundary tests for review template dependency warning coverage — no real git."""

from __future__ import annotations

import pytest

from doctrine.templates.repository import CentralTemplateRepository
from doctrine.missions import MissionTemplateRepository

pytestmark = pytest.mark.fast

REQUIRED_KEYS = [
    "dependency_check",
    "dependent_check",
    "rebase_warning",
    "verify_instruction",
]


def _assert_required_keys_in_content(content: str, label: str) -> None:
    for key in REQUIRED_KEYS:
        assert key in content, f"{label} missing required warning key: {key}"


def test_base_review_template_dependency_warnings() -> None:
    """Base review template must include actionable dependency warnings."""
    repo = CentralTemplateRepository.default()
    path = repo.get("review.md")
    assert path is not None, "review.md not found via CentralTemplateRepository"
    assert path.exists(), f"Missing template: {path}"
    _assert_required_keys_in_content(path.read_text(), str(path))


def test_mission_review_template_dependency_warnings() -> None:
    """Software-dev review template must include dependency warnings too."""
    repo = MissionTemplateRepository(MissionTemplateRepository.default_missions_root())
    result = repo.get_command_template("software-dev", "review")
    assert result is not None, "mission review.md not found via MissionTemplateRepository"
    _assert_required_keys_in_content(result.content, result.origin)
