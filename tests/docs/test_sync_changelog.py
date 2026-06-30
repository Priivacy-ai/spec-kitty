"""Tests for :mod:`scripts.docs.sync_changelog`.

All tests except :func:`test_live_files_are_synced` use ``tmp_path`` for
isolation.  The live-sync invariant is a permanent CI gate — it fails whenever
root ``CHANGELOG.md`` drifts from the canonical; running
``python scripts/docs/sync_changelog.py --write`` restores sync.

Marker discipline: all tests carry ``@pytest.mark.fast`` via ``pytestmark``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# conftest.py (tests/docs/conftest.py) inserts _REPO_ROOT into sys.path before
# this module is imported, making both scripts.docs and scripts.release importable.
from scripts.docs.sync_changelog import generate_root
from scripts.release.extract_changelog import extract_changelog_section

pytestmark = pytest.mark.fast

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CANONICAL_PATH = _REPO_ROOT / "docs" / "changelog" / "CHANGELOG.md"
_ROOT_PATH = _REPO_ROOT / "CHANGELOG.md"

# Synthetic canonical with YAML frontmatter (used by several tests below)
_SAMPLE_CANONICAL = """\
---
title: Changelog
doc_status: active
---
# Changelog

## [1.0.0] - 2024-01-01

- Initial release.
"""

# Synthetic file with no frontmatter (passthrough path)
_SAMPLE_NO_FRONTMATTER = """\
# Changelog

## [1.0.0] - 2024-01-01

- No frontmatter here.
"""

# Expected body after stripping the frontmatter from _SAMPLE_CANONICAL
_EXPECTED_BODY = """\
# Changelog

## [1.0.0] - 2024-01-01

- Initial release.
"""


def test_generate_root_strips_frontmatter() -> None:
    """Output must not begin with ``---`` and must begin with ``# Changelog``."""
    result = generate_root(_SAMPLE_CANONICAL)
    assert not result.startswith("---"), "YAML frontmatter must be stripped from output"
    assert result.startswith("# Changelog"), (
        f"Body must begin with '# Changelog', got: {result[:40]!r}"
    )


def test_generate_root_strips_frontmatter_exact_body() -> None:
    """Body after stripping must match the expected verbatim content."""
    result = generate_root(_SAMPLE_CANONICAL)
    assert result == _EXPECTED_BODY


def test_generate_root_no_frontmatter_passthrough() -> None:
    """A file with no YAML frontmatter block is returned unchanged."""
    result = generate_root(_SAMPLE_NO_FRONTMATTER)
    assert result == _SAMPLE_NO_FRONTMATTER


def test_check_fails_when_files_diverge(tmp_path: Path) -> None:
    """Diverged root content must not equal the generated form (SC-003)."""
    root = tmp_path / "root.md"
    # Write stale content that differs from generate_root(_SAMPLE_CANONICAL)
    root.write_text("# Changelog\n\n- Stale entry.\n", encoding="utf-8-sig")
    expected = generate_root(_SAMPLE_CANONICAL)
    actual = root.read_text(encoding="utf-8-sig")
    assert actual != expected, (
        "Diverged root must not match generate_root output — "
        "this test validates the divergence precondition."
    )


def test_check_passes_after_write(tmp_path: Path) -> None:
    """Round-trip: write generated text (utf-8-sig), read back — must match."""
    out = tmp_path / "root.md"
    expected = generate_root(_SAMPLE_CANONICAL)
    out.write_text(expected, encoding="utf-8-sig")
    actual = out.read_text(encoding="utf-8-sig")
    assert actual == expected


def test_tool_surface_ignore_markers_survive() -> None:
    """Both ``<!-- tool-surface: ignore -->`` markers must survive generate_root.

    Upstream ``ccd278061`` added 2 sanctioned markers to the canonical body
    as escape hatches for legacy skill paths in historical entries.  Since
    ``generate_root`` copies the canonical body verbatim (minus frontmatter),
    both markers must appear in the output so that
    ``test_docs_contract_lint`` keeps passing after regeneration.
    """
    canonical = _CANONICAL_PATH.read_text(encoding="utf-8")
    result = generate_root(canonical)
    count = result.count("<!-- tool-surface: ignore -->")
    assert count == 2, (
        f"Expected 2 '<!-- tool-surface: ignore -->' markers in generated root, "
        f"found {count}.  A generator change must not silently strip these markers."
    )


def test_generated_root_parseable_by_extract_changelog() -> None:
    """generate_root output must be parseable by extract_changelog_section (C-002)."""
    canonical = _CANONICAL_PATH.read_text(encoding="utf-8")
    root_text = generate_root(canonical)
    section = extract_changelog_section(root_text, "3.2.3")
    assert section, (
        "extract_changelog_section returned empty string for version 3.2.3 — "
        "root CHANGELOG.md does not have a 3.2.3 entry (C-002 violation)."
    )
    fallback_prefix = "Release 3.2.3\n\nNo changelog entry"
    assert not section.startswith(fallback_prefix), (
        "extract_changelog_section returned the fallback message for 3.2.3 — "
        "the generated CHANGELOG format is not Keep-a-Changelog-valid (C-002 violation)."
    )


def test_live_files_are_synced() -> None:
    """Permanent CI invariant: root CHANGELOG.md must equal generate_root(canonical).

    If this test fails, run::

        python scripts/docs/sync_changelog.py --write

    then commit the updated root ``CHANGELOG.md``.
    """
    canonical = _CANONICAL_PATH.read_text(encoding="utf-8")
    root = _ROOT_PATH.read_text(encoding="utf-8-sig")
    expected = generate_root(canonical)
    assert root == expected, (
        "Root CHANGELOG.md has drifted from docs/changelog/CHANGELOG.md.\n"
        "Fix: python scripts/docs/sync_changelog.py --write"
    )
