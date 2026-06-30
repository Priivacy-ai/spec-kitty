#!/usr/bin/env python3
"""Sync root ``CHANGELOG.md`` from the canonical ``docs/changelog/CHANGELOG.md``.

The canonical file is the single source of truth for changelog content.
The root ``CHANGELOG.md`` is a generated artifact consumed by release tooling
(``scripts/release/extract_changelog.py``).  It contains the canonical body
with the YAML frontmatter stripped.

Usage::

    python scripts/docs/sync_changelog.py --check   # exit 1 if diverged
    python scripts/docs/sync_changelog.py --write   # regenerate root

The ``--check`` mode is wired into ``.github/workflows/docs-freshness.yml``
so CI blocks on drift (FR-007 / C-002 / SC-003).

D-5 encoding note: the root file is written with ``utf-8-sig`` (BOM prefix)
because ``scripts/release/extract_changelog.py:76`` reads it with that
encoding.  A mismatch corrupts release-notes extraction.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Final

_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
_CANONICAL_PATH: Final[Path] = _REPO_ROOT / "docs" / "changelog" / "CHANGELOG.md"
_ROOT_PATH: Final[Path] = _REPO_ROOT / "CHANGELOG.md"

_FRONTMATTER_OPEN: Final[str] = "---\n"
_FRONTMATTER_CLOSE: Final[str] = "\n---\n"
_DRIFT_MESSAGE: Final[str] = (
    "CHANGELOG drift detected: {root} differs from generate_root({canonical}).\n"
    "Fix: python scripts/docs/sync_changelog.py --write"
)


def generate_root(canonical_text: str) -> str:
    """Strip YAML frontmatter from canonical changelog text, returning the body.

    The body begins at ``# Changelog`` with no leading blank lines.
    Files without a frontmatter block are returned verbatim.
    ``<!-- tool-surface: ignore -->`` markers pass through unchanged.
    """
    if canonical_text.startswith(_FRONTMATTER_OPEN):
        rest = canonical_text[len(_FRONTMATTER_OPEN):]
        closing = rest.find(_FRONTMATTER_CLOSE)
        if closing != -1:
            body = rest[closing + len(_FRONTMATTER_CLOSE):]
            return body.lstrip("\n")
    return canonical_text


def _check() -> int:
    """Exit 0 if root matches generated form; exit 1 if diverged."""
    canonical = _CANONICAL_PATH.read_text(encoding="utf-8")
    root = _ROOT_PATH.read_text(encoding="utf-8-sig")
    expected = generate_root(canonical)
    if root == expected:
        return 0
    print(
        _DRIFT_MESSAGE.format(root=_ROOT_PATH, canonical=_CANONICAL_PATH),
        file=sys.stderr,
    )
    return 1


def _write() -> int:
    """Regenerate root ``CHANGELOG.md`` from canonical (written utf-8-sig)."""
    canonical = _CANONICAL_PATH.read_text(encoding="utf-8")
    body = generate_root(canonical)
    _ROOT_PATH.write_text(body, encoding="utf-8-sig")
    print(f"Written: {_ROOT_PATH}")
    return 0


def main() -> int:
    """Entry point for ``--check`` / ``--write`` CLI."""
    parser = argparse.ArgumentParser(
        description="Sync root CHANGELOG.md from docs/changelog/CHANGELOG.md."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if root diverges from canonical; exit 0 if synced.",
    )
    group.add_argument(
        "--write",
        action="store_true",
        help="Regenerate root CHANGELOG.md from canonical (utf-8-sig).",
    )
    args = parser.parse_args()
    if args.check:
        return _check()
    return _write()


if __name__ == "__main__":
    sys.exit(main())
