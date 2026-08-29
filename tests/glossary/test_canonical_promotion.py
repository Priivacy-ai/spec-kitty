"""AC-11 / C-010 / NFR-004: Slice F glossary terms are canonical.

covers: AC-11, FR-302, C-010 — expected GREEN at: WP12 final commit after T065 promotion

RED on planning base (and after WP08): the 10 Slice F terms land as
``Status: candidate`` per WP08. WP12/T065 promotes each to ``canonical``.

The glossary uses a Markdown table format:
    | **Status** | canonical |
"""
from __future__ import annotations

import functools
import re
import subprocess
from pathlib import Path

import pytest

from scripts.docs.related_validator import validate_related

pytestmark = [pytest.mark.unit, pytest.mark.fast]

SLICE_F_TERMS = [
    "Three-layer DRG",
    "Organisation Tier",
    "CharterScope",
    "Workflow Sequence",
    "Workflow ID",
    "Ratchet Baseline",
    "Cat-7 Grandfathered Orphan",
    "Symbol-level Dead Code",
    "Catalog Miss",
    "`__all__` Declaration Convention",
]


def test_all_slice_f_terms_are_canonical_in_doctrine_context() -> None:
    """All 10 Slice F terms must have Status: canonical in docs/context/charter.md."""
    repo_root = Path(__file__).resolve().parents[2]
    glossary_path = repo_root / "docs" / "context" / "charter.md"
    assert glossary_path.exists(), f"glossary not found: {glossary_path}"
    glossary = glossary_path.read_text()

    offenders: list[str] = []
    for term in SLICE_F_TERMS:
        # Escape the term for regex; handle backtick-quoted terms
        term_escaped = re.escape(term)
        # Find the section heading (### <term>) then look for the Status table row
        # within the next ~20 lines (the entry is short)
        pattern = re.compile(
            r"###\s+" + term_escaped + r"\s*\n"
            r".*?"
            r"\|\s*\*\*Status\*\*\s*\|\s*(\w+)\s*\|",
            re.DOTALL | re.IGNORECASE,
        )
        match = pattern.search(glossary)
        if not match:
            offenders.append(f"{term}: missing entry or malformed Status row")
        elif match.group(1).lower() != "canonical":
            offenders.append(
                f"{term}: Status={match.group(1)!r} (expected 'canonical')"
            )

    assert not offenders, (
        "Glossary canonical-promotion failures (C-010 binding):\n  "
        + "\n  ".join(offenders)
    )


# ---------------------------------------------------------------------------
# WP02 (charter-authority-flip-01M14RB3) / T007 / FR-002: external referrer
# re-point closure. WP01 renamed docs/context/charter.offering.md -> charter.md; WP02
# re-points the 40 external referrers (path token only -- the term CONTENT
# those referrers carry is owned by later waves M2/M4/M5 per
# occurrence_map.yaml's referrer exceptions block).
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
_WP02_BASE_COMMIT = "73609a064a444fbec6d1bd45d350574151017e1d"


@functools.lru_cache(maxsize=1)
def _resolve_wp02_base_commit() -> str | None:
    """The reachable integration-main commit immediately before WP02 landed.

    Used only to diff-check the SHAPE of this WP's own referrer edits below --
    not a live runtime dependency. Originally pinned to a literal SHA
    (``7b0c2d3ed53cd47ad50e4f75da84c7b9ca4c3044``), but a squash-merge onto a
    landing PR rewrites history and orphans any commit pinned before the
    squash -- that SHA is unreachable post-squash (``git show <sha>:...``
    exits 128). ``merge-base origin/main HEAD`` cannot replace it: on the PR
    lane it resolves to pre-mission main, but after landing it resolves to
    HEAD and empties the diff. The immediate pre-#854 integration commit is
    the stable, reachable pre-rename base in this repository's history.

    Returns ``None`` (rather than raising) if that historical commit is
    unavailable locally (e.g. a shallow clone) -- callers skip rather than
    false-red, mirroring
    ``tests/architectural/test_charter_owner_map_executed.py``'s
    ``_git_diff_is_empty`` shallow-clone guard.
    """
    result = subprocess.run(
        ["git", "cat-file", "-e", f"{_WP02_BASE_COMMIT}^{{commit}}"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return _WP02_BASE_COMMIT

_AGENT_PROFILE_NAMES = [
    "architect-alphonso",
    "curator-carla",
    "debugger-debbie",
    "designer-dagmar",
    "doctrine-daphne",
    "frontend-freddy",
    "generic-agent",
    "human-in-charge",
    "implementer-ivan",
    "java-jenny",
    "node-norris",
    "paula-patterns",
    "planner-priti",
    "python-pedro",
    "randy-reducer",
    "researcher-robbie",
    "retrospective-facilitator",
    "reviewer-renata",
]

#: The 20 WP02-owned pages carrying a ``related:`` frontmatter edge that used
#: to dangle on ``docs/context/charter.offering.md`` (checked live by
#: ``related_validator``; see ``test_wp02_owned_referrers_have_zero_dangling_related_edges``).
WP02_RELATED_FRONTMATTER_REFERRERS: tuple[str, ...] = (
    *(f"docs/api/agent_profiles/{name}.md" for name in _AGENT_PROFILE_NAMES),
    "docs/architecture/doctrine-kinds.md",
    "docs/development/how-to/create-a-doctrine-artifact.md",
)

#: The full WP02 hand-edit set (owned_files minus the 2 regenerated lockfiles,
#: which reformat the whole file rather than flip a token in place -- T010 --
#: and minus this test file itself, which gains real new coverage here, not
#: just a path-token flip). Used by the diff-shape / no-double-funding check.
WP02_PATH_TOKEN_ONLY_REFERRERS: tuple[str, ...] = (
    "docs/adr/3.x/2026-07-21-1-in-tension-with-drg-edge.md",
    *WP02_RELATED_FRONTMATTER_REFERRERS,
    "docs/plans/doctrine/org-doctrine-layer-architecture-review.md",
    "docs/plans/engineering-notes/drg-completeness-2843-research.md",
    "docs/plans/initiatives/2026-04-mission-nomenclature-reconciliation/README.md",
    "docs/plans/refactor/slice-f-mission-debrief.md",
    "src/charter/offering/README.md",
    "src/charter/offering/directives/README.md",
    "src/charter/offering/paradigms/README.md",
    "src/charter/offering/schemas/README.md",
    "src/charter/offering/tactics/README.md",
    "src/charter/offering/templates/README.md",
    "tests/architectural/test_no_dead_doctrine_paths.py",
)

def _git_show(rel_path: str, base_commit: str) -> str:
    """Return *rel_path*'s content at *base_commit* (WP02's pre-rename base)."""
    result = subprocess.run(
        ["git", "show", f"{base_commit}:{rel_path}"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def _flip_path_token(line: str) -> str:
    return line.replace("context/charter.offering.md", "context/charter.md")


@pytest.mark.architectural
def test_wp02_owned_referrers_have_zero_dangling_related_edges() -> None:
    """T007(a) / FR-002: the 20 WP02-owned ``related:`` frontmatter referrers
    no longer dangle on ``docs/context/charter.offering.md`` (``related_validator``).

    Scoped to what WP02 actually owns. Three sibling ``docs/context/*.md``
    pages (``governance.md``, ``orchestration.md``,
    ``configuration-project-structure.md``) still carry a dangling
    ``docs/context/charter.offering.md`` in their OWN ``related:`` frontmatter --
    those pages are WP01-owned (its T003 only re-pointed the inline
    'Related terms' TABLE links at specific line numbers, not the frontmatter
    ``related:`` list) and are out of WP02's scope (explicitly: "Do NOT
    touch ... docs/context/*.md (WP01)"). This is a real residual cross-WP
    gap, surfaced here as a named, pinned exception rather than silently
    fixed out-of-scope or silently swept under a passing assertion -- if it
    widens beyond the three known pages, this test reds.
    """
    report = validate_related(docs_root=REPO_ROOT / "docs", repo_root=REPO_ROOT)
    assert report.checked_count > 0, "non-vacuity: related_validator examined 0 related: edges"

    owned = set(WP02_RELATED_FRONTMATTER_REFERRERS)
    owned_dangling = [edge for edge in report.dangling_edges if edge.from_path in owned]
    assert not owned_dangling, "WP02-owned referrers still dangle on the pre-rename path:\n" + "\n".join(
        f"{edge.from_path} -> {edge.to_path}" for edge in owned_dangling
    )

    still_dangling_doctrine = {
        edge.from_path for edge in report.dangling_edges if edge.to_path == "docs/context/charter.offering.md"
    }
    known_wp01_gap = {
        "docs/context/configuration-project-structure.md",
        "docs/context/governance.md",
        "docs/context/orchestration.md",
    }
    unexpected = still_dangling_doctrine - known_wp01_gap
    assert not unexpected, (
        "New/unexpected docs/context/charter.offering.md dangling referrers outside WP02's "
        f"owned set and the known WP01 frontmatter gap: {sorted(unexpected)}"
    )


@pytest.mark.architectural
def test_wp02_referrer_diffs_are_exactly_the_path_token() -> None:
    """T007(b) / paula HIGH: each WP02-owned referrer's diff against its
    pre-rename base is EXACTLY the ``context/charter.offering.md`` ->
    ``context/charter.md`` path-token substitution on the lines that change
    -- no other doctrine-bearing content is touched (no double-funding the
    later-wave content classes M2/M4/M5 own; occurrence_map.yaml's referrer
    exceptions block)."""
    base_commit = _resolve_wp02_base_commit()
    if base_commit is None:
        pytest.skip(
            "WP02 base commit unavailable in this checkout (likely a shallow "
            "clone) -- cannot diff against the pre-rename base"
        )
    violations: list[str] = []
    for rel_path in WP02_PATH_TOKEN_ONLY_REFERRERS:
        old_lines = _git_show(rel_path, base_commit).splitlines()
        new_lines = (REPO_ROOT / rel_path).read_text(encoding="utf-8").splitlines()
        if len(old_lines) != len(new_lines):
            violations.append(f"{rel_path}: line count changed ({len(old_lines)} -> {len(new_lines)})")
            continue
        for lineno, (old, new) in enumerate(zip(old_lines, new_lines, strict=True), start=1):
            if old == new:
                continue
            if _flip_path_token(old) != new:
                violations.append(
                    f"{rel_path}:{lineno}: diff is not a pure path-token flip\n    old: {old!r}\n    new: {new!r}"
                )
    assert not violations, "Non-path-token referrer diffs (T007b):\n" + "\n".join(violations)


@pytest.mark.architectural
def test_wp02_owned_referrers_flip_at_least_one_line() -> None:
    """Self-mutation teeth for the diff-shape check above: every referrer in
    the hand-edit set must have actually changed."""
    base_commit = _resolve_wp02_base_commit()
    if base_commit is None:
        pytest.skip(
            "WP02 base commit unavailable in this checkout (likely a shallow "
            "clone) -- cannot diff against the pre-rename base"
        )
    unchanged: list[str] = []
    for rel_path in WP02_PATH_TOKEN_ONLY_REFERRERS:
        if _git_show(rel_path, base_commit) == (REPO_ROOT / rel_path).read_text(encoding="utf-8"):
            unchanged.append(rel_path)
    assert not unchanged, f"Expected a path-token flip that never landed: {unchanged}"
