"""Scope: mock-boundary tests for review template dependency warning coverage — no real git."""

from __future__ import annotations

import pytest
from pathlib import Path

from doctrine.templates.repository import CentralTemplateRepository
from doctrine.missions.repository import MissionRepository

pytestmark = pytest.mark.fast

REQUIRED_KEYS = [
    "dependency_check",
    "dependent_check",
    "rebase_warning",
    "verify_instruction",
]


def _assert_required_keys(path: Path) -> None:
    assert path.exists(), f"Missing template: {path}"
    content = path.read_text()
    for key in REQUIRED_KEYS:
        assert key in content, f"{path} missing required warning key: {key}"


def test_base_review_template_dependency_warnings() -> None:
    """Base review template must include actionable dependency warnings."""
    repo = CentralTemplateRepository.default()
    path = repo.get("review.md")
    assert path is not None, "review.md not found via CentralTemplateRepository"
    _assert_required_keys(path)


def test_mission_review_template_dependency_warnings() -> None:
    """Software-dev review template must include dependency warnings too."""
    repo = MissionRepository(MissionRepository.default_missions_root())
    path = repo.get_command_template("software-dev", "review")
    assert path is not None, "mission review.md not found via MissionRepository"
    _assert_required_keys(path)
