"""Regression tests for README canonical workflow path.

Ensures the README names `spec-kitty next` as the canonical agent loop
and does not teach `spec-kitty implement WP##` in the top-level workflow line.

FR-501, FR-502 (WP06 — Track 6 de-emphasis)
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_readme_canonical_workflow_does_not_name_implement() -> None:
    """The first 30 lines of README must not teach bare 'spec-kitty implement WP'."""
    readme = (REPO_ROOT / "README.md").read_text()
    first_30_lines = "\n".join(readme.split("\n")[:30])
    assert "spec-kitty implement WP" not in first_30_lines, (
        "README canonical workflow line (top 30 lines) still names "
        "'spec-kitty implement WP##'. Replace with 'spec-kitty next'."
    )


def test_readme_names_spec_kitty_next() -> None:
    """README must reference 'spec-kitty next' as the canonical agent loop."""
    readme = (REPO_ROOT / "README.md").read_text()
    assert "spec-kitty next" in readme, (
        "README does not mention 'spec-kitty next'. "
        "The canonical agent loop command must be documented."
    )
