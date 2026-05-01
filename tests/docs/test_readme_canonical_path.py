"""Regression tests for README canonical workflow path.

Ensures the README names `spec-kitty next` as the canonical agent loop
and does not teach `/spec-kitty.implement` or `spec-kitty implement WP##`
as canonical steps in any of the prominent workflow sections.

FR-501, FR-502 (WP06 — Track 6 de-emphasis)
Post-079 review findings: extend coverage to all workflow sections, not just
the first 30 lines.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_readme_canonical_workflow_does_not_name_implement() -> None:
    """The first 30 lines of README must not teach bare 'spec-kitty implement WP'."""
    readme = (REPO_ROOT / "README.md").read_text()
    first_30_lines = "\n".join(readme.split("\n")[:30])
    assert "spec-kitty implement WP" not in first_30_lines, (
        "README canonical workflow line (top 30 lines) still names 'spec-kitty implement WP##'. Replace with 'spec-kitty next'."
    )


def test_readme_names_spec_kitty_next() -> None:
    """README must reference 'spec-kitty next' as the canonical agent loop."""
    readme = (REPO_ROOT / "README.md").read_text()
    assert "spec-kitty next" in readme, "README does not mention 'spec-kitty next'. The canonical agent loop command must be documented."


def test_readme_workflow_table_uses_spec_kitty_next() -> None:
    """The numbered workflow table (around line 1000+) must not list
    /spec-kitty.implement as a numbered lifecycle step.

    Post-079 review: the first-30-lines test missed this table.
    """
    readme = (REPO_ROOT / "README.md").read_text()
    # Find the "Core Commands" / numbered workflow table section
    # Look for any table row that has a step number AND /spec-kitty.implement
    # Pattern: | N | `/spec-kitty.implement` | ...
    bad_row = re.search(
        r"^\|\s*\d+\s*\|\s*`/spec-kitty\.implement`",
        readme,
        re.MULTILINE,
    )
    assert bad_row is None, (
        f"README workflow table at line {readme[: bad_row.start()].count(chr(10)) + 1} "
        "still lists `/spec-kitty.implement` as a numbered lifecycle step. "
        "Replace with 'spec-kitty next'."
    )


def test_readme_lifecycle_list_does_not_name_implement_as_step() -> None:
    """Numbered lifecycle lists (1. /spec-kitty.specify, 2. /spec-kitty.plan ...)
    must not include /spec-kitty.implement as a numbered step.

    Post-079 review: Phase 5 section and Lifecycle section both had this.
    """
    readme = (REPO_ROOT / "README.md").read_text()
    # Pattern: N. `/spec-kitty.implement` OR N. /spec-kitty.implement
    bad = re.search(
        r"^\d+\.\s*`?/spec-kitty\.implement`?",
        readme,
        re.MULTILINE,
    )
    assert bad is None, (
        f"README lifecycle list at line {readme[: bad.start()].count(chr(10)) + 1} "
        "still names `/spec-kitty.implement` as a numbered step. "
        "Replace with 'spec-kitty next' or 'spec-kitty agent action implement'."
    )
