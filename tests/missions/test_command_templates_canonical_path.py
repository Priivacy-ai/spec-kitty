"""Regression tests for canonical mission step prompts.

Ensures source prompts under doctrine mission steps do not teach
bare `spec-kitty implement WP##` as the canonical workflow command.

FR-504, FR-505 (WP06 — Track 6 de-emphasis)
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.fast]

REPO_ROOT = Path(__file__).resolve().parents[2]
PROMPT_DIR = REPO_ROOT / "src" / "doctrine" / "missions" / "mission-steps" / "software-dev"


def test_command_templates_do_not_teach_bare_implement() -> None:
    """No source template may contain 'spec-kitty implement WP'.

    The canonical pattern is 'spec-kitty agent action implement <WP> --agent <name>'.
    """
    assert PROMPT_DIR.exists(), f"Prompt directory not found: {PROMPT_DIR}"
    for prompt in PROMPT_DIR.glob("*/prompt.md"):
        content = prompt.read_text(encoding="utf-8")
        assert "spec-kitty implement WP" not in content, (
            f"{prompt} still teaches bare 'spec-kitty implement WP##'. "
            f"Replace with 'spec-kitty agent action implement <WP> --agent <name>'."
        )
