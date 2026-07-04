#!/usr/bin/env python3
"""Guard the root ``CHANGELOG.md`` symlink to ``docs/changelog/CHANGELOG.md``.

The canonical file is the single source of truth for changelog content.  The
root ``CHANGELOG.md`` is a **symlink** to it — there is no generated copy and
therefore no drift to sync.  (Before 2026-07-04 the root file was a generated
frontmatter-stripped mirror; the two-file model made every contributor edit
the wrong copy and trip docs-freshness, so the mirror was retired.)

Release tooling (``scripts/release/extract_changelog.py``,
``scripts/release/validate_release.py``) reads through the symlink and
tolerates the canonical YAML frontmatter: both scan for ``## [...]`` headings.
``extract_changelog.py`` reads ``utf-8-sig``, which decodes BOM-less UTF-8
unchanged.

Usage::

    python scripts/docs/sync_changelog.py --check   # exit 1 unless root is the symlink
    python scripts/docs/sync_changelog.py --write   # (re)create the symlink

The ``--check`` mode is wired into ``.github/workflows/docs-freshness.yml``
so CI blocks when the symlink is replaced by a regular file (FR-007 / C-002 /
SC-003).

Windows note: checkouts without ``core.symlinks`` materialize the symlink as
a text file containing the target path.  Nothing in the Windows-critical test
set reads the root changelog, and release tooling runs on Linux runners.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Final

_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
_CANONICAL_PATH: Final[Path] = _REPO_ROOT / "docs" / "changelog" / "CHANGELOG.md"
_ROOT_PATH: Final[Path] = _REPO_ROOT / "CHANGELOG.md"

#: The exact link target the root symlink must carry (relative, POSIX form).
SYMLINK_TARGET: Final[str] = "docs/changelog/CHANGELOG.md"

_DRIFT_MESSAGE: Final[str] = (
    "CHANGELOG layout drift: {root} must be a symlink to {target}.\n"
    "Fix: python scripts/docs/sync_changelog.py --write"
)


def check(root: Path | None = None, canonical: Path | None = None) -> int:
    """Exit 0 if ``root`` is a symlink resolving to ``canonical``; else 1."""
    root = _ROOT_PATH if root is None else root
    canonical = _CANONICAL_PATH if canonical is None else canonical
    if root.is_symlink() and root.resolve() == canonical.resolve():
        return 0
    print(
        _DRIFT_MESSAGE.format(root=root, target=SYMLINK_TARGET),
        file=sys.stderr,
    )
    return 1


def write(root: Path | None = None, target: str | None = None) -> int:
    """(Re)create ``root`` as a symlink pointing at ``target``."""
    root = _ROOT_PATH if root is None else root
    target = SYMLINK_TARGET if target is None else target
    root.unlink(missing_ok=True)
    root.symlink_to(target)
    print(f"Symlinked: {root} -> {target}")
    return 0


def main() -> int:
    """Entry point for ``--check`` / ``--write`` CLI."""
    parser = argparse.ArgumentParser(
        description="Guard the root CHANGELOG.md symlink to docs/changelog/CHANGELOG.md."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 unless root CHANGELOG.md is the canonical symlink.",
    )
    group.add_argument(
        "--write",
        action="store_true",
        help="(Re)create the root CHANGELOG.md symlink.",
    )
    args = parser.parse_args()
    if args.check:
        return check()
    return write()


if __name__ == "__main__":
    sys.exit(main())
