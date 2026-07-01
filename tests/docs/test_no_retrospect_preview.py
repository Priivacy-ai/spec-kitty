"""Guard test: ``retrospect synthesize`` must never be paired with ``--preview``.

The ``spec-kitty agent retrospect synthesize`` command is dry-run by default and
takes ``--apply`` to mutate; it does NOT accept a ``--preview`` flag (see
``src/specify_cli/cli/commands/agent_retrospect.py::synthesize_cmd``).

Stale guidance that tells operators to run ``... synthesize ... --preview`` is a
documentation bug because the flag does not exist. This test scans the owned
source tree (``src/`` and ``docs/``) plus the repo-root mission-workflow file and
fails if any ``retrospect synthesize`` reference still pairs with ``--preview``.

Excluded from the scan:
- ``kitty-specs/`` (historical mission artifacts, intentionally frozen)
- generated agent copies under dot-directories (``.claude/``, ``.agents/``,
  ``.amazonq/``, etc.) which are produced from the source templates
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.fast]

REPO_ROOT = Path(__file__).resolve().parents[2]

# Directories whose markdown/source files we own and want to keep correct.
SCAN_ROOTS = (
    REPO_ROOT / "src",
    REPO_ROOT / "docs",
)

# Repo-root standalone files that document the workflow.
SCAN_FILES = (REPO_ROOT / "spec-kitty-mission-workflow.md",)

# File extensions worth scanning for command guidance.
SCAN_SUFFIXES = {".md", ".py", ".txt", ".rst"}

# Matches a ``retrospect synthesize`` invocation that also carries ``--preview``
# on the same logical command line (we scan line by line, which is how these
# guidance strings are authored).
_PATTERN = re.compile(r"retrospect\s+synthesize\b.*--preview\b")


def _is_excluded(path: Path) -> bool:
    """Return True for paths that must NOT be scanned.

    Skips ``kitty-specs/`` (historical) and any generated agent copy living
    under a dot-directory (``.claude``, ``.agents``, ``.amazonq``, ...).
    """
    try:
        rel_parts = path.relative_to(REPO_ROOT).parts
    except ValueError:
        rel_parts = path.parts
    for part in rel_parts:
        if part == "kitty-specs":
            return True
        # Generated agent copies live under dot-directories.
        if part.startswith(".") and part not in {".", ".."}:
            return True
    return False


def _iter_candidate_files() -> list[Path]:
    candidates: list[Path] = []
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() not in SCAN_SUFFIXES:
                continue
            if _is_excluded(path):
                continue
            candidates.append(path)
    for path in SCAN_FILES:
        if path.is_file() and not _is_excluded(path):
            candidates.append(path)
    return candidates


def test_no_retrospect_synthesize_preview_pairing() -> None:
    """No owned source/doc file may pair ``retrospect synthesize`` with ``--preview``."""
    offenders: list[str] = []
    for path in _iter_candidate_files():
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            if _PATTERN.search(line):
                rel = path.relative_to(REPO_ROOT)
                offenders.append(f"{rel}:{lineno}: {line.strip()}")

    assert not offenders, (
        "`retrospect synthesize` is dry-run by default and uses --apply to mutate; "
        "it does not accept --preview. Remove the stale --preview reference(s):\n"
        + "\n".join(offenders)
    )
