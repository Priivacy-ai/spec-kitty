"""Architectural test: phantom 'agent worktree repair' must not appear in src/.

The command ``spec-kitty agent worktree repair`` was removed post-#2135. Any
surviving reference in the product source (``src/``) or the SOURCE doctrine
under ``src/doctrine/`` misleads operators with a dead-end recovery command.
The real recovery surface is ``spec-kitty doctor workspaces --fix``.

Scope: ``src/`` ONLY.

Out of scope (immutable / unowned by WP05):
  - ``docs/``         — historical engineering notes (7 files)
  - ``architecture/`` — immutable ADR snapshot
  - ``kitty-specs/``  — mission planning prose
  - ``tests/``        — the two test-side assertions re-pinned by T055

The guard is count-agnostic: it fails closed on ANY surviving occurrence;
it does not pin an "exactly N" count.

FR-007 / #1890 / WP05.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

pytestmark = [pytest.mark.architectural, pytest.mark.git_repo]

# Build the phantom string from fragments so this test file does not flag
# itself (otherwise the grep-guard would fail against its own source).
_PHANTOM = "agent" + " " + "worktree" + " " + "repair"

# Scan only ``src/`` — product code + SOURCE doctrine.  Historical /
# immutable / unowned surfaces outside ``src/`` are explicitly excluded.
_SCAN_ROOT = "src/"


def _repo_root() -> Path:
    """Resolve the repository root by walking up to a .kittify/ marker."""
    here = Path(__file__).resolve()
    for parent in (here, *here.parents):
        if (parent / ".kittify").is_dir():
            return parent
    raise RuntimeError("Could not locate repo root (no .kittify/ marker found).")


def _grep_phantom() -> list[str]:
    """Return all ``<file>:<line>:<content>`` hits for the phantom string in src/.

    Uses ``git grep`` so ``.gitignore`` exclusions apply automatically.
    """
    root = _repo_root()
    cmd = [
        "git",
        "-C",
        str(root),
        "grep",
        "--line-number",
        "--fixed-strings",
        _PHANTOM,
        "--",
        _SCAN_ROOT,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    # git grep exits 1 when no matches found (success for this guard),
    # 0 when matches found (failure for this guard), >1 on error.
    if result.returncode == 1:
        return []
    if result.returncode != 0:
        raise RuntimeError(
            f"git grep failed for phantom string {_PHANTOM!r}: "
            f"exit={result.returncode} stderr={result.stderr!r}"
        )
    return result.stdout.splitlines()


def test_no_phantom_worktree_repair_in_src() -> None:
    """The phantom ``agent worktree repair`` string must not appear in ``src/``.

    The command was removed post-#2135; surviving references mislead operators
    with a non-existent recovery path. The real command is:
    ``spec-kitty doctor workspaces --fix``.

    Scope: ``src/`` only (product code + SOURCE doctrine under src/doctrine/).
    Historical engineering notes (docs/), an immutable ADR snapshot
    (architecture/), mission prose (kitty-specs/), and the test-side assertions
    re-pinned by T055 (tests/) are excluded from this guard.
    """
    hits = _grep_phantom()
    if hits:
        formatted = "\n  ".join(hits)
        pytest.fail(
            f"Phantom recovery command {_PHANTOM!r} survived in src/.\n\n"
            "The command 'spec-kitty agent worktree repair' was removed post-#2135 "
            "and does not exist. Replace every occurrence with the real command:\n\n"
            "    spec-kitty doctor workspaces --fix\n\n"
            f"Surviving occurrences in src/ ({len(hits)}):\n  {formatted}\n\n"
            "FR-007 / #1890 — do NOT add an allow-list; fix the production string."
        )
