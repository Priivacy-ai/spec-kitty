"""Scope: mock-boundary tests for review template dependency warning coverage — no real git."""

from __future__ import annotations

import pytest
from pathlib import Path

pytestmark = pytest.mark.fast

REPO_ROOT = Path(__file__).resolve().parents[2]
BASE_TEMPLATE = REPO_ROOT / "src" / "specify_cli" / "templates" / "command-templates" / "review.md"
MISSION_TEMPLATE = REPO_ROOT / "src" / "doctrine" / "missions" / "software-dev" / "command-templates" / "review.md"

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
    # Arrange
    # (no precondition)

    # Assumption check
    assert BASE_TEMPLATE.exists(), "base review template must be present on disk"

    # Act / Assert
    _assert_required_keys(BASE_TEMPLATE)


def test_mission_review_template_dependency_warnings() -> None:
    """Software-dev review template must include dependency warnings too."""
    # Arrange
    # (no precondition)

    # Assumption check
    assert MISSION_TEMPLATE.exists(), "mission review template must be present on disk"

    # Act / Assert
    _assert_required_keys(MISSION_TEMPLATE)
