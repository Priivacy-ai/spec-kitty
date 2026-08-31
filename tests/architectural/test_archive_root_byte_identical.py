"""Archive-root byte-identity gate (M1, NFR-002/SC-004, squad B3).

The four fixed exclusion roots (``DM-01M0P6C8C7Q6SPBT412V39RPN0``) are immutable
historical-record surfaces:

* ``kitty-specs/`` — archived mission dossiers,
* ``.kittify/migrations/mission-state/quarantine/`` — quarantined migration state,
* ``kitty-ops/`` — repo-ops history,
* ``.kittify/missions/`` — mission-state history.

Mission ``charter-authority-flip-01M14RB3`` (wave M1) must not touch a single
byte of any file that already existed under those roots when this port branched
from this repository's ``main``. Editing an archived artifact to "fix" a stale
line is forbidden (the correction belongs in the live mission dossier, not the
archive — see this mission's DD-10). M1 is free to ADD new content under its own
new archive dir (``kitty-specs/charter-authority-flip-01M14RB3/``); only
*pre-existing* files are frozen.

This gate compares the port's merge-base with ``origin/main`` to the working
tree via a single ``git diff --name-status`` scoped to the four roots and asserts
that every reported entry is an ADD of a path that did not exist at that base.
Any Modify or Delete of a pre-existing archived file is a real NFR-002 violation
to surface, never to mask.
"""

from __future__ import annotations

import subprocess

import pytest

from tests.utils import REPO_ROOT

pytestmark = [pytest.mark.architectural, pytest.mark.git_repo]

# The mission base commit (pre-WP01 opening state).
_MISSION_BASE_REV = "fc4acaa897"

# The convergence-port base ref. The upstream mission base is not an ancestor of
# this repository's main, so comparing it directly would blame pre-existing fork
# deletions on M1. The merge-base with main is the exact pre-port EXP tree.
_PORT_BASE_REF = "origin/main"

# The four fixed exclusion / immutable-archive roots.
_ARCHIVE_ROOTS: tuple[str, ...] = (
    "kitty-specs/",
    ".kittify/migrations/mission-state/quarantine/",
    "kitty-ops/",
    ".kittify/missions/",
)

# Append-only exceptions carved out of the immutable-archive freeze
# (2026-08-28, mission charter-authority-flip-01M14RB3 landing pass, #3664):
# the canonical rename-reconcile spine (``scripts/docs/rename_reconcile.py``'s
# ``DEFAULT_OCCURRENCE_MAP``) lives under ``kitty-specs/`` but is a *living*
# cross-mission registry, NOT a frozen proof artifact — every doc-rename
# mission is REQUIRED to append its move here or the ``build`` job's
# rename-reconcile gate reds (see main's own ``docs(landing): declare docs/plans
# curation moves on the reconcile spine`` and ``docs(plans): register the
# domains/ plan moves on the canonical rename-reconcile spine``). Appending a
# new move line is this file's designed use, not the "editing an archived
# artifact to fix a stale line" that NFR-002 forbids, so it is exempt from the
# byte-freeze while every other pre-existing archived file stays frozen.
# NOTE: the exemption is a whole-path carve-out (any mutation of this one file
# passes, not strictly an append) -- its content integrity is independently
# policed by the build job's rename-reconcile gate, so a destructive rewrite
# here would red there, not slip through silently.
_APPEND_ONLY_SPINE_EXCEPTIONS: frozenset[str] = frozenset(
    {"kitty-specs/common-docs-convergence-01KZMTR9/occurrence_map.yaml"}
)


def _run_git(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _baseline_is_reachable() -> bool:
    return _run_git(["cat-file", "-e", f"{_MISSION_BASE_REV}^{{commit}}"]).returncode == 0


def _files_under_roots_at(rev: str) -> set[str]:
    """Every tracked file under an archive root at ``rev``."""
    result = _run_git(["ls-tree", "-r", "--name-only", rev])
    if result.returncode != 0:
        raise RuntimeError(f"git ls-tree failed for {rev!r}: {result.stderr!r}")
    return {
        path
        for path in result.stdout.splitlines()
        if any(path.startswith(root) for root in _ARCHIVE_ROOTS)
    }


def _port_base_rev() -> str:
    result = _run_git(["merge-base", "HEAD", _PORT_BASE_REF])
    if result.returncode != 0:
        raise RuntimeError(f"git merge-base failed for HEAD and {_PORT_BASE_REF!r}: {result.stderr!r}")
    return result.stdout.strip()


@pytest.mark.skipif(
    not _baseline_is_reachable(),
    reason=f"mission base commit {_MISSION_BASE_REV} not reachable in this checkout",
)
def test_no_preexisting_archived_file_was_modified() -> None:
    """No file that existed under an archive root at the mission base may be
    Modified or Deleted in the working tree — only new files may be added."""
    port_base_rev = _port_base_rev()
    baseline_files = _files_under_roots_at(port_base_rev)

    diff = _run_git(
        ["diff", "--name-status", port_base_rev, "--", *_ARCHIVE_ROOTS]
    )
    if diff.returncode != 0:
        raise RuntimeError(f"git diff failed: {diff.stderr!r}")

    violations: list[str] = []
    for line in diff.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status, path = parts[0], parts[-1]
        # The append-only rename-reconcile spine is exempt: appending a move
        # line to it is a required repo-wide contract, not an archive edit.
        if path in _APPEND_ONLY_SPINE_EXCEPTIONS:
            continue
        # An ADD of a path that did not exist at the base is M1's own new
        # content and is allowed. Anything else touching a pre-existing file
        # (Modify, Delete, Rename source) is a violation.
        if status.startswith("A") and path not in baseline_files:
            continue
        if path in baseline_files:
            violations.append(f"{status}\t{path}")
        else:
            # A non-add status on a path absent from the base (e.g. a rename
            # into a root) is also unexpected under an immutable archive.
            violations.append(f"{status}\t{path} (unexpected non-add on new path)")

    assert not violations, (
        "M1 modified/deleted pre-existing archived file(s) under the four "
        "immutable exclusion roots (NFR-002 violation). Archive artifacts are "
        "byte-frozen; corrections belong in the live mission dossier, not the "
        "archive:\n  " + "\n  ".join(sorted(violations))
    )


@pytest.mark.skipif(
    not _baseline_is_reachable(),
    reason=f"mission base commit {_MISSION_BASE_REV} not reachable in this checkout",
)
def test_archive_baseline_is_non_empty() -> None:
    """Anti-vacuity floor: the archive roots are non-empty at the base, so the
    byte-identity assertion above is scanning real content, not nothing."""
    assert _files_under_roots_at(_MISSION_BASE_REV), (
        "no tracked files found under the archive roots at the mission base — "
        "the byte-identity gate would pass vacuously"
    )
