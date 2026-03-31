"""Regression guard: no active template may teach the deprecated frontmatter-lane model.

Templates under src/specify_cli/missions/ and src/doctrine/ generate WP prompt
files. After feature 060 (canonical status model cleanup), none of them should
contain:

- ``lane:`` inside YAML frontmatter (between ``---`` markers)
- ``lane=`` in activity-log format strings
- ``history[].lane`` entries in frontmatter history examples

Status is now managed exclusively via ``status.events.jsonl``.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# Root of the source tree relative to repo root
REPO_ROOT = Path(__file__).resolve().parents[2]

TEMPLATE_DIRS = [
    REPO_ROOT / "src" / "specify_cli" / "missions",
    REPO_ROOT / "src" / "doctrine" / "templates",
    REPO_ROOT / "src" / "doctrine" / "missions",
]


def _collect_template_files() -> list[Path]:
    """Collect all .md files from template directories."""
    files: list[Path] = []
    for d in TEMPLATE_DIRS:
        if d.exists():
            files.extend(d.rglob("*.md"))
    return sorted(files)


def _extract_frontmatter(text: str) -> str | None:
    """Return text between the first pair of ``---`` markers, or None."""
    parts = text.split("---", 2)
    if len(parts) >= 3:
        return parts[1]
    return None


def _has_lane_in_frontmatter(text: str) -> list[str]:
    """Check for ``lane:`` inside YAML frontmatter blocks.

    Returns list of offending lines.
    """
    violations: list[str] = []
    frontmatter = _extract_frontmatter(text)
    if frontmatter is None:
        return violations
    for line in frontmatter.splitlines():
        stripped = line.strip()
        # Match ``lane:`` as a YAML key (with optional value)
        if re.match(r"^lane\s*:", stripped):
            violations.append(f"frontmatter lane: {stripped}")
        # Match ``lane:`` inside a history entry
        if re.match(r"^\s*lane\s*:", line) and "history" not in stripped:
            # already caught above
            pass
        if re.match(r"^lane\s*:", stripped):
            # already caught
            pass
    # Also check history entries for lane: field
    for line in frontmatter.splitlines():
        stripped = line.strip()
        if re.match(r"lane\s*:", stripped) and stripped != "":
            if f"frontmatter lane: {stripped}" not in violations:
                violations.append(f"history lane field: {stripped}")
    return violations


def _has_lane_in_activity_log(text: str) -> list[str]:
    """Check for ``lane=`` in activity log format strings.

    We look for the pattern ``lane=`` which appears in format strings
    like ``lane=<lane>`` or ``lane=planned``.  We skip occurrences that
    are clearly inside code-block examples showing what NOT to do (but
    our templates should not have these either after cleanup).
    """
    violations: list[str] = []
    for i, line in enumerate(text.splitlines(), 1):
        # Match lane= in activity log format strings
        if re.search(r"lane=", line):
            violations.append(f"line {i}: {line.strip()}")
    return violations


# Parametrize over all template files for clear per-file reporting
_template_files = _collect_template_files()


@pytest.mark.parametrize(
    "template_path",
    _template_files,
    ids=[str(p.relative_to(REPO_ROOT)) for p in _template_files],
)
def test_no_lane_in_frontmatter(template_path: Path) -> None:
    """No template should contain ``lane:`` in YAML frontmatter."""
    text = template_path.read_text(encoding="utf-8")
    violations = _has_lane_in_frontmatter(text)
    assert not violations, (
        f"{template_path.relative_to(REPO_ROOT)} has lane in frontmatter:\n"
        + "\n".join(f"  - {v}" for v in violations)
    )


@pytest.mark.parametrize(
    "template_path",
    _template_files,
    ids=[str(p.relative_to(REPO_ROOT)) for p in _template_files],
)
def test_no_lane_in_activity_log(template_path: Path) -> None:
    """No template should contain ``lane=`` in activity log format strings."""
    text = template_path.read_text(encoding="utf-8")
    violations = _has_lane_in_activity_log(text)
    assert not violations, (
        f"{template_path.relative_to(REPO_ROOT)} has lane= in activity log:\n"
        + "\n".join(f"  - {v}" for v in violations)
    )


def test_guard_catches_reintroduction(tmp_path: Path) -> None:
    """Verify the guard actually catches lane if reintroduced (not a no-op stub)."""
    # Create a fake template with lane in frontmatter
    fake = "---\nlane: planned\ntitle: test\n---\n# Test\n"
    assert _has_lane_in_frontmatter(fake), "Guard should catch lane: in frontmatter"

    # Create a fake template with lane= in activity log
    fake_log = "- 2026-01-12T10:00:00Z – system – lane=planned – Prompt created\n"
    assert _has_lane_in_activity_log(fake_log), "Guard should catch lane= in activity log"

    # Verify clean content passes
    clean_fm = "---\ntitle: test\nwork_package_id: WP01\n---\n# Test\n"
    assert not _has_lane_in_frontmatter(clean_fm), "Clean frontmatter should pass"

    clean_log = "- 2026-01-12T10:00:00Z – system – Prompt created\n"
    assert not _has_lane_in_activity_log(clean_log), "Clean activity log should pass"


def test_template_files_found() -> None:
    """Ensure we actually found template files to scan (guard against empty glob)."""
    assert len(_template_files) >= 10, (
        f"Expected at least 10 template files but found {len(_template_files)}. "
        f"Directories checked: {[str(d) for d in TEMPLATE_DIRS]}"
    )
