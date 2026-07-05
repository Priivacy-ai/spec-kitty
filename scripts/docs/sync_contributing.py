#!/usr/bin/env python3
"""Guard the root ``CONTRIBUTING.md`` symlink to ``docs/guides/contributing.md``.

The canonical file is the single source of truth for contributor-guide
content.  The root ``CONTRIBUTING.md`` is a **symlink** to it — there is no
generated copy and therefore no drift to sync.  (This mirrors the
``CHANGELOG.md`` symlink model: see ``scripts/docs/sync_changelog.py``.)

Usage::

    python scripts/docs/sync_contributing.py --check   # exit 1 unless root is the symlink
    python scripts/docs/sync_contributing.py --write   # (re)create the symlink

The ``--check`` mode is wired into ``.github/workflows/docs-freshness.yml``
so CI blocks when the symlink is replaced by a regular file.

Windows note: checkouts without ``core.symlinks`` materialize the symlink as
a text file containing the target path.  Nothing in the Windows-critical test
set reads the root CONTRIBUTING file.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Final

_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
_CANONICAL_PATH: Final[Path] = _REPO_ROOT / "docs" / "guides" / "contributing.md"
_ROOT_PATH: Final[Path] = _REPO_ROOT / "CONTRIBUTING.md"

#: The exact link target the root symlink must carry (relative, POSIX form).
SYMLINK_TARGET: Final[str] = "docs/guides/contributing.md"

_DRIFT_MESSAGE: Final[str] = (
    "CONTRIBUTING layout drift: {root} must be a symlink to {target}.\n"
    "Fix: python scripts/docs/sync_contributing.py --write"
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
        description="Guard the root CONTRIBUTING.md symlink to docs/guides/contributing.md."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 unless root CONTRIBUTING.md is the canonical symlink.",
    )
    group.add_argument(
        "--write",
        action="store_true",
        help="(Re)create the root CONTRIBUTING.md symlink.",
    )
    args = parser.parse_args()
    if args.check:
        return check()
    return write()


if __name__ == "__main__":
    sys.exit(main())
