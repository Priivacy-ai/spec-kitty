"""Architectural test: forbidden legacy terminology must not reappear.

Locks in the rename performed by mission 01KSPN6C
(rename-[forbidden]-to-status-commit). If either forbidden term
reappears in the active-source surface (`src/`, `tests/`, `docs/`),
CI fails and the PR is rejected.

The forbidden terms are constructed via string concatenation in this
module so the test file does not flag itself.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

# Architectural invariant scan that shells out to ``git grep`` over the live
# repo, so it carries both the architectural-gate marker and ``git_repo``
# (Rule 1 of test_pytest_marker_correctness: git subprocess users must be
# visible to CI's ``-m git_repo`` filter).
pytestmark = [pytest.mark.architectural, pytest.mark.git_repo]


# Build forbidden terms from fragments so this test file does not contain
# the literal strings (otherwise the test would flag itself).
_FORBIDDEN_TERMS: tuple[str, ...] = (
    "cere" + "mony",
    "status" + "-writing",
)


_SCAN_ROOTS: tuple[str, ...] = ("src", "tests", "docs")
_EXTENSIONS: tuple[str, ...] = ("*.py", "*.md", "*.yaml", "*.yml")

# Paths excluded from the scan. kitty-specs/ contains historical mission
# artifacts that are explicitly out of scope per spec C-001. Worktrees and
# vendor directories are operational state.
_EXCLUDED_PATH_FRAGMENTS: tuple[str, ...] = (
    "kitty-specs/",
    # docs/adr/ holds immutable historical decision records whose bodies are
    # preserved byte-for-byte (NFR-001/C-002). Legacy terms in those snapshots
    # are quoted history, not active prose — same historical-artifact rationale
    # as the kitty-specs/ exemption above. The narrowness of this exemption
    # (docs/adr/ only, not the rest of docs/) is pinned by
    # test_docs_adr_exemption_is_narrow below.
    "docs/adr/",
    ".worktrees/",
    ".venv/",
    "node_modules/",
    ".git/",
    # The test file itself is excluded as a belt-and-suspenders measure;
    # the string-fragment construction above is the primary self-flag defense.
    "tests/architectural/test_no_legacy_terminology.py",
)


def _line_is_excluded(line: str) -> bool:
    """True when a ``git grep`` hit line falls under an excluded path fragment.

    A hit line has the form ``<path>:<line-number>:<content>``; a match is
    excluded when any excluded fragment appears anywhere in it. Extracted as a
    pure seam so the exclusion policy (including the narrow docs/adr/ exemption)
    is testable without shelling out to git.
    """
    return any(fragment in line for fragment in _EXCLUDED_PATH_FRAGMENTS)


def _repo_root() -> Path:
    """Resolve the repository root by walking up to a .kittify/ marker."""
    here = Path(__file__).resolve()
    for parent in (here, *here.parents):
        if (parent / ".kittify").is_dir():
            return parent
    raise RuntimeError("Could not locate repo root (no .kittify/ marker found).")


def _grep_for(term: str) -> list[str]:
    """Return all matching `<file>:<line>:<content>` lines for `term`.

    Uses `git grep` so .gitignore exclusions apply automatically (excludes
    .venv/, node_modules/, etc.). If git is unavailable, falls back to a
    manual walk; this is a best-effort fallback for environments where the
    test runs outside a checkout.
    """
    root = _repo_root()
    cmd = [
        "git",
        "-C",
        str(root),
        "grep",
        "--line-number",
        "--fixed-strings",
        term,
        "--",
        *(f"{r}/" for r in _SCAN_ROOTS),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    # git grep exits 1 when no matches, 0 when matches found, >1 on error.
    if result.returncode == 1:
        return []
    if result.returncode != 0:
        raise RuntimeError(
            f"git grep failed for term {term!r}: exit={result.returncode} "
            f"stderr={result.stderr!r}"
        )
    return [line for line in result.stdout.splitlines() if not _line_is_excluded(line)]


@pytest.mark.parametrize("term", _FORBIDDEN_TERMS)
def test_forbidden_term_does_not_appear(term: str) -> None:
    """Each forbidden legacy term must have zero occurrences in active source.

    Excluded surfaces: kitty-specs/ historical artifacts, worktrees, vendor
    directories. The test file itself is excluded via _EXCLUDED_PATH_FRAGMENTS
    and via the string-fragment construction of _FORBIDDEN_TERMS.
    """
    hits = _grep_for(term)
    if hits:
        formatted = "\n  ".join(hits)
        pytest.fail(
            f"Forbidden legacy term {term!r} reappeared in active source.\n"
            f"Canonical term is 'status commit' (see "
            f".kittify/glossaries/spec_kitty_core.yaml).\n"
            f"Hits ({len(hits)}):\n  {formatted}"
        )


def test_docs_adr_exemption_is_narrow() -> None:
    """docs/adr/ is exempt as historical snapshots, but the rest of docs/ is not.

    Regression for WP06 (mission 01KW3SBK): 117 historical ADRs moved from the
    unscanned ``architecture/`` tree into the scanned ``docs/adr/`` tree. Their
    bodies are immutable, byte-for-byte snapshots (NFR-001/C-002), so quoted
    legacy terms inside them must not trip the guard — mirroring the existing
    kitty-specs/ historical-artifact exemption.

    This test pins the exemption as *narrow*: only ``docs/adr/`` is excluded.
    Any other docs/ path (guides, architecture, a top-level docs page) must
    still be scanned, so a real regression there is caught.
    """
    forbidden = _FORBIDDEN_TERMS[0]

    # A hit inside docs/adr/ is treated as an immutable historical snapshot.
    adr_hit = f"docs/adr/3.x/2026-04-17-1-some-decision.md:103:No inheritance {forbidden}."
    assert _line_is_excluded(adr_hit), (
        "docs/adr/ hits must be exempt — historical decision records are "
        "immutable snapshots (NFR-001/C-002)."
    )

    # The rest of docs/ must remain in scope: an exemption here would be a
    # blanket docs/ carve-out and a regression.
    still_scanned = (
        f"docs/guides/onboarding.md:7:Run the {forbidden} before merging.",
        f"docs/architecture/overview.md:12:The {forbidden} step is required.",
        f"docs/status-model.md:3:Avoid the legacy {forbidden} wording.",
    )
    for hit in still_scanned:
        assert not _line_is_excluded(hit), (
            f"Non-ADR docs path must still be scanned for legacy terms: {hit!r}. "
            "The docs/adr/ exemption must not blanket-exempt all of docs/."
        )
