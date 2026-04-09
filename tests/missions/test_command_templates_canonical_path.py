"""Regression tests for command template canonical path.

Ensures source templates under software-dev/command-templates/ do not teach
bare `spec-kitty implement WP##` as the canonical workflow command.

FR-504, FR-505 (WP06 — Track 6 de-emphasis)
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_DIR = REPO_ROOT / "src" / "specify_cli" / "missions" / "software-dev" / "command-templates"


def test_command_templates_do_not_teach_bare_implement() -> None:
    """No source template may contain 'spec-kitty implement WP'.

    The canonical pattern is 'spec-kitty agent action implement <WP> --agent <name>'.
    """
    assert TEMPLATE_DIR.exists(), f"Template directory not found: {TEMPLATE_DIR}"
    for template in TEMPLATE_DIR.glob("*.md"):
        content = template.read_text()
        assert "spec-kitty implement WP" not in content, (
            f"{template.name} still teaches bare 'spec-kitty implement WP##'. "
            f"Replace with 'spec-kitty agent action implement <WP> --agent <name>'."
        )
