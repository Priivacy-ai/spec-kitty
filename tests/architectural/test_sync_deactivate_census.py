"""FR-013 — the sync-deactivation gated test set is frozen (#3799).

Mission ``sync-deactivate-by-default-01M16M1P`` (WP05) applied a per-file
``skipif`` guard carrying one canonical reason string to every sync-coupled test
module, so those tests only run when ``SPEC_KITTY_ENABLE_SAAS_SYNC=1`` is set.

This census guard closes the "deleted test = 0 failures = green" loophole. It
recomputes the **live set** of gated files (every test module whose SOURCE TEXT
contains the canonical reason string) and pins it to the **frozen set** produced
in WP01 (``census/sync_deactivate_test_census.txt``). Comparing a SET of paths —
not a count — catches BOTH failure modes (BINDING plan item 5b):

1. **Deletion / un-skip** — a frozen path no longer carries the marker (the
   file was deleted or its ``skipif`` reason string was removed) → it drops out
   of the live set → ``missing`` is non-empty → red.
2. **Unauthorized addition** — a file gained the marker but was never frozen
   (e.g. a rename dropped a new path into the tree) → ``unexpected`` is
   non-empty → red.

Detection is a **TEXT-marker match**, not an AST module-level ``pytestmark``
scan: #2809's two tests are guarded per-test rather than module-level, which an
AST module-level scan would miss (post-tasks squad correction, BINDING). The
text match catches both shapes.

This guard inspects source, not runtime behavior, so it runs on the default push
path and is intentionally NOT sync-gated (no ``skipif`` on this module).
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [pytest.mark.fast]

#: Repo root: ``tests/architectural/test_sync_deactivate_census.py`` → parents[2].
_REPO_ROOT = Path(__file__).resolve().parents[2]

#: The frozen SET of gated file paths, produced in WP01 (T004).
_CENSUS_FILE = _REPO_ROOT / "tests" / "architectural" / "census" / "sync_deactivate_test_census.txt"

#: The tree the live scan walks.
_TESTS_ROOT = _REPO_ROOT / "tests"

#: The exact canonical reason string WP05 standardized on. Keeping this identical
#: to WP05's marker is what prevents the two work packages from drifting.
_CANONICAL_REASON = (
    "sync deactivated by default (#3799); "
    "set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run"
)

#: Files the live scan must never count as gated modules: the census document
#: itself (it quotes the reason string in its header) and this guard module
#: (its docstring quotes it too).
_SELF_EXCLUSIONS: frozenset[Path] = frozenset({_CENSUS_FILE, Path(__file__).resolve()})


def load_frozen(path: Path) -> set[str]:
    """Load the frozen SET of repo-root-relative paths from the census file.

    Leading ``#`` header comment lines and blank lines are skipped; every
    remaining line is one repo-root-relative path. Order-independent.
    """
    frozen: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        frozen.add(line)
    return frozen


def collect_marker_files(root: Path) -> set[str]:
    """Return every ``*.py`` under ``root`` whose SOURCE TEXT carries the marker.

    Paths are normalized to POSIX repo-root-relative strings so the comparison is
    stable across platforms and independent of walk order / locale sort.
    """
    live: set[str] = set()
    for path in root.rglob("*.py"):
        resolved = path.resolve()
        if resolved in _SELF_EXCLUSIONS:
            continue
        if "__pycache__" in resolved.parts:
            continue
        if _CANONICAL_REASON in resolved.read_text(encoding="utf-8"):
            live.add(resolved.relative_to(_REPO_ROOT).as_posix())
    return live


def test_live_marker_set_equals_frozen_census() -> None:
    """FR-013 / SC-003: the gated file set matches the WP01 frozen set exactly.

    ``missing`` (frozen but no longer gated) reds on deletion or un-skip;
    ``unexpected`` (gated but not frozen) reds on an unauthorized addition.
    """
    frozen = load_frozen(_CENSUS_FILE)
    live = collect_marker_files(_TESTS_ROOT)

    missing = sorted(frozen - live)
    unexpected = sorted(live - frozen)

    assert live == frozen, (
        "Sync-deactivation gated test set drifted from the WP01 frozen census "
        f"({_CENSUS_FILE.relative_to(_REPO_ROOT).as_posix()}).\n"
        f"missing (frozen but no longer gated — deleted or skipif reason "
        f"removed): {missing}\n"
        f"unexpected (gated but not frozen — new/renamed file gained the "
        f"marker): {unexpected}\n"
        "Fix the source (restore the skipif / revert the rename) or, for a "
        "deliberate change, update the frozen census file in the same commit."
    )


def test_frozen_census_paths_all_exist() -> None:
    """Deletion guard: every path in the frozen SET still exists on disk."""
    frozen = load_frozen(_CENSUS_FILE)
    absent = sorted(p for p in frozen if not (_REPO_ROOT / p).is_file())
    assert not absent, (
        "Frozen census path(s) no longer exist on disk (file deleted): "
        f"{absent}. Restore the file(s) or update the frozen census "
        f"({_CENSUS_FILE.relative_to(_REPO_ROOT).as_posix()}) deliberately."
    )
