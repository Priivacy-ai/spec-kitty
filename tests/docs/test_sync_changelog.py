"""Tests for :mod:`scripts.docs.sync_changelog` (symlink model, 2026-07-04).

Root ``CHANGELOG.md`` is a symlink to the canonical
``docs/changelog/CHANGELOG.md`` — there is no generated mirror and no drift.
:func:`test_live_root_is_canonical_symlink` is the permanent CI gate; it fails
whenever the symlink is replaced by a regular file, and
``python scripts/docs/sync_changelog.py --write`` restores it.

The release-tooling compatibility tests pin the consumer contract that made
the symlink safe: ``extract_changelog_section`` must parse the canonical text
*with* its YAML frontmatter, because release tooling now reads the canonical
content through the symlink.

Marker discipline: all tests carry ``@pytest.mark.fast`` via ``pytestmark``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# conftest.py (tests/docs/conftest.py) inserts _REPO_ROOT into sys.path before
# this module is imported, making both scripts.docs and scripts.release importable.
from scripts.docs.sync_changelog import SYMLINK_TARGET, check, write
from scripts.release.extract_changelog import extract_changelog_section

pytestmark = pytest.mark.fast

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CANONICAL_PATH = _REPO_ROOT / "docs" / "changelog" / "CHANGELOG.md"
_ROOT_PATH = _REPO_ROOT / "CHANGELOG.md"


def test_live_root_is_canonical_symlink() -> None:
    """Permanent CI invariant: root CHANGELOG.md is a symlink to canonical.

    If this test fails, run::

        python scripts/docs/sync_changelog.py --write

    then commit the restored symlink.
    """
    assert _ROOT_PATH.is_symlink(), (
        "Root CHANGELOG.md must be a symlink to docs/changelog/CHANGELOG.md "
        "(the two-file generated-mirror model was retired 2026-07-04).\n"
        "Fix: python scripts/docs/sync_changelog.py --write"
    )
    assert _ROOT_PATH.resolve() == _CANONICAL_PATH.resolve(), (
        f"Root CHANGELOG.md symlink resolves to {_ROOT_PATH.resolve()}, "
        f"expected {_CANONICAL_PATH.resolve()}.\n"
        "Fix: python scripts/docs/sync_changelog.py --write"
    )


def test_live_check_passes() -> None:
    """``--check`` returns 0 on the live repository."""
    assert check() == 0


def test_check_fails_on_regular_file(tmp_path: Path) -> None:
    """A regular file where the symlink should be is layout drift (SC-003)."""
    canonical = tmp_path / "docs" / "CHANGELOG.md"
    canonical.parent.mkdir(parents=True)
    canonical.write_text("# Changelog\n", encoding="utf-8")
    root = tmp_path / "CHANGELOG.md"
    root.write_text("# Changelog\n", encoding="utf-8")
    assert check(root=root, canonical=canonical) == 1


def test_check_fails_on_wrong_symlink_target(tmp_path: Path) -> None:
    """A symlink pointing anywhere but the canonical file is layout drift."""
    canonical = tmp_path / "docs" / "CHANGELOG.md"
    canonical.parent.mkdir(parents=True)
    canonical.write_text("# Changelog\n", encoding="utf-8")
    other = tmp_path / "OTHER.md"
    other.write_text("# Other\n", encoding="utf-8")
    root = tmp_path / "CHANGELOG.md"
    root.symlink_to(other.name)
    assert check(root=root, canonical=canonical) == 1


def test_write_creates_symlink(tmp_path: Path) -> None:
    """``--write`` creates the symlink where none exists."""
    canonical = tmp_path / "docs" / "CHANGELOG.md"
    canonical.parent.mkdir(parents=True)
    canonical.write_text("# Changelog\n", encoding="utf-8")
    root = tmp_path / "CHANGELOG.md"
    assert write(root=root, target="docs/CHANGELOG.md") == 0
    assert root.is_symlink()
    assert check(root=root, canonical=canonical) == 0


def test_write_repairs_regular_file(tmp_path: Path) -> None:
    """``--write`` replaces a stale regular file with the symlink."""
    canonical = tmp_path / "docs" / "CHANGELOG.md"
    canonical.parent.mkdir(parents=True)
    canonical.write_text("# Changelog\n", encoding="utf-8")
    root = tmp_path / "CHANGELOG.md"
    root.write_text("# Stale mirror\n", encoding="utf-8")
    assert write(root=root, target="docs/CHANGELOG.md") == 0
    assert root.is_symlink()
    assert check(root=root, canonical=canonical) == 0


def test_symlink_target_is_relative() -> None:
    """The link target must stay relative so clones relocate cleanly."""
    assert not SYMLINK_TARGET.startswith("/")
    assert _ROOT_PATH.is_symlink()
    assert not Path(_ROOT_PATH.readlink()).is_absolute()


def test_canonical_with_frontmatter_parseable_by_extract_changelog() -> None:
    """Release tooling reads the canonical text through the symlink (C-002).

    ``extract_changelog_section`` must find version sections despite the
    canonical YAML frontmatter — this is the contract that made retiring the
    frontmatter-stripped mirror safe.
    """
    canonical = _CANONICAL_PATH.read_text(encoding="utf-8")
    assert canonical.startswith("---"), (
        "Precondition: canonical changelog carries YAML frontmatter — if this "
        "changed, re-examine whether the symlink model still needs this pin."
    )
    section = extract_changelog_section(canonical, "3.2.3")
    assert section, (
        "extract_changelog_section returned empty string for version 3.2.3 — "
        "the canonical CHANGELOG.md does not have a 3.2.3 entry (C-002 violation)."
    )
    fallback_prefix = "Release 3.2.3\n\nNo changelog entry"
    assert not section.startswith(fallback_prefix), (
        "extract_changelog_section returned the fallback message for 3.2.3 — "
        "the canonical CHANGELOG format (with frontmatter) is not parseable "
        "by release tooling (C-002 violation)."
    )


def test_root_read_through_symlink_matches_canonical() -> None:
    """Reading the root path yields the canonical bytes (utf-8-sig tolerant).

    ``extract_changelog.py`` reads ``CHANGELOG.md`` with ``utf-8-sig``; a
    BOM-less canonical file must round-trip unchanged through that decode.
    """
    via_root = _ROOT_PATH.read_text(encoding="utf-8-sig")
    canonical = _CANONICAL_PATH.read_text(encoding="utf-8")
    assert via_root == canonical
