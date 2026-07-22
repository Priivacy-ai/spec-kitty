"""Architectural test: docs must use glossary terms in their canonical form.

Standing check for FR-013 (see kitty-specs/docs-ia-onboarding-overhaul-01KY02JB/spec.md
and contracts/canonical-term-check-contract.md): loads the real, live
``.kittify/glossaries/spec_kitty_core.yaml`` seed (104 terms; ``surface`` is the
canonical spelling/casing) and flags any occurrence in ``docs/`` whose text matches a
term but with different casing/spelling.

This is a **sibling** to ``test_no_legacy_terminology.py``, not an extension of it — that
test enforces a small, unrelated, hardcoded 2-term denylist (forbidden legacy terms that
must have ZERO occurrences anywhere). This test sources 104 terms from the real glossary
seed and only checks *form* (is a term, when it appears, spelled/cased the way the
glossary says it should be) — it does not do alias/banned-synonym detection (deferred to
a follow-up issue per spec.md C-003; the seed has no ``aliases`` field yet). Conflating
the two would make failures from either concern harder to diagnose (research.md item 5).

Scope decision (precision over recall): only **multi-word** ``surface`` values are
scanned. Roughly a third of the 104 terms are single, very common English words
("mission", "build", "charter", "lane", "phase", "project", "scope", "skill", "tactic",
"repository", ...). A naive substring/word scan over those would flag enormous amounts of
unrelated prose (e.g. "Mission" used correctly per the charter's own Terminology Canon at
the start of a sentence, or "build" used as an ordinary verb) — noise that would drown out
genuine casing regressions on the multi-word phrases this check can actually adjudicate
precisely. See ``test_single_word_terms_are_excluded_from_scan`` below, which pins this
decision so a future change to the exclusion doesn't silently widen or narrow it.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

from glossary.scope import GlossaryScope, load_seed_file

# Architectural invariant scan that shells out to ``git grep``, so it carries both the
# architectural-gate marker and ``git_repo`` (git subprocess users must be visible to
# CI's ``-m git_repo`` filter — see test_pytest_marker_correctness).
# ``docs_scoped``: this test scans ``docs/`` content, so a docs-only PR could newly-red
# it — it MUST run on the arch pole's docs-only trim. Marker triple is byte-identical to
# test_no_legacy_terminology.py's.
pytestmark = [pytest.mark.architectural, pytest.mark.git_repo, pytest.mark.docs_scoped]


_SCAN_GLOB: str = ":(glob)docs/**/*.md"

# Mirrors test_no_legacy_terminology.py's _EXCLUDED_PATH_FRAGMENTS: kitty-specs/ and
# docs/adr/ are historical/immutable snapshots (NFR-001/C-002 rationale in that file
# applies identically here — quoted legacy casing inside an ADR body is quoted history,
# not active prose); worktrees/vendor dirs are operational state.
_EXCLUDED_PATH_FRAGMENTS: tuple[str, ...] = (
    "kitty-specs/",
    "docs/adr/",
    ".worktrees/",
    ".venv/",
    "node_modules/",
    ".git/",
)


def _line_is_excluded(line: str) -> bool:
    """True when a ``git grep`` hit line falls under an excluded path fragment.

    A hit line has the form ``<path>:<line-number>:<content>``; a match is excluded
    when any excluded fragment appears anywhere in it. Extracted as a pure seam,
    mirroring test_no_legacy_terminology.py's helper of the same name.
    """
    return any(fragment in line for fragment in _EXCLUDED_PATH_FRAGMENTS)


def _repo_root() -> Path:
    """Resolve the repository root by walking up to a .kittify/ marker."""
    here = Path(__file__).resolve()
    for parent in (here, *here.parents):
        if (parent / ".kittify").is_dir():
            return parent
    raise RuntimeError("Could not locate repo root (no .kittify/ marker found).")


def _load_canonical_surfaces() -> list[str]:
    """Load the real glossary seed and return its ``surface`` values, multi-word only.

    Uses the canonical loader (``glossary.scope.load_seed_file``) rather than
    hand-rolled YAML parsing, per repo policy of using canonical sources over
    improvised substitutes. Single-word surfaces are dropped — see module docstring.
    """
    senses = load_seed_file(GlossaryScope.SPEC_KITTY_CORE, _repo_root())
    return [sense.surface.surface_text for sense in senses if " " in sense.surface.surface_text.strip()]


def _normalize_ws(text: str) -> str:
    """Collapse any run of whitespace to a single space and strip the ends."""
    return re.sub(r"\s+", " ", text).strip()


def _term_pattern(term: str) -> re.Pattern[str]:
    """Case-insensitive, whitespace-flexible, word-bounded pattern for a phrase.

    Words are joined with ``\\s+`` so incidental double-spacing in prose doesn't by
    itself produce a false "misspelling" (whitespace is normalized before the
    casing/spelling comparison, per the contract), and the whole pattern is
    word-bounded so e.g. the term "action context" cannot match as a substring
    embedded inside unrelated longer words.
    """
    words = _normalize_ws(term).split(" ")
    body = r"\s+".join(re.escape(word) for word in words)
    return re.compile(rf"\b{body}\b", re.IGNORECASE)


def _flagged_occurrences(content: str, surface: str) -> list[str]:
    """Return the exact matched text for every non-canonically-cased occurrence.

    Case-sensitive comparison against ``surface`` after whitespace normalization, per
    the contract. A match whose normalized text equals the canonical surface exactly
    is NOT flagged (that's correct usage).
    """
    canonical = _normalize_ws(surface)
    pattern = _term_pattern(surface)
    return [actual for match in pattern.finditer(content) if (actual := _normalize_ws(match.group(0))) != canonical]


def _grep_candidate_lines(terms: list[str]) -> list[str]:
    """Return excluded-filtered ``<path>:<line>:<content>`` hits for any of ``terms``.

    A single ``git grep`` invocation with one ``-e <term>`` per term (OR-matched,
    case-insensitive, fixed-string) is used as a cheap candidate prefilter — mirroring
    test_no_legacy_terminology.py's git-grep-based scan mechanism. Fixed-string
    matching has no word-boundary awareness, so a hit line here is only a candidate;
    the real per-term, word-bounded casing check happens in Python
    (``_flagged_occurrences``) once the line is in hand.
    """
    if not terms:
        return []
    root = _repo_root()
    cmd = ["git", "-C", str(root), "grep", "--line-number", "--ignore-case", "--fixed-strings"]
    for term in terms:
        cmd += ["-e", term]
    cmd += ["--", _SCAN_GLOB]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    # git grep exits 1 when no matches, 0 when matches found, >1 on error.
    if result.returncode == 1:
        return []
    if result.returncode != 0:
        raise RuntimeError(f"git grep failed while scanning for glossary terms: exit={result.returncode} stderr={result.stderr!r}")
    return [line for line in result.stdout.splitlines() if not _line_is_excluded(line)]


def _scan_for_violations(terms: list[str]) -> list[str]:
    """Scan ``docs/`` for non-canonically-cased occurrences of any of ``terms``.

    Returns fully formatted ``{file}:{line}: found "{actual}", expected canonical
    form "{surface}"`` messages, one per flagged occurrence, in deterministic order.
    """
    violations: list[str] = []
    for line in _grep_candidate_lines(terms):
        path, lineno, content = line.split(":", 2)
        for surface in terms:
            for actual in _flagged_occurrences(content, surface):
                violations.append(f'{path}:{lineno}: found "{actual}", expected canonical form "{surface}"')
    return sorted(set(violations))


def test_glossary_terms_use_canonical_casing() -> None:
    """Every multi-word glossary surface, where it appears in docs/, is cased exactly.

    Sources terms from the live 104-term spec_kitty_core.yaml seed (not a hardcoded
    list — a future term addition/rename is picked up automatically).

    Enforces **zero** non-canonical occurrences directly: the introducing mission's
    baseline-ratchet escape hatch (``glossary_canonical_terms_baseline.txt``, 200
    pre-existing violations) was fully paid down and retired (#2830), so this is now a
    plain gate — any non-canonical usage anywhere in scanned docs/ fails the test.
    """
    terms = _load_canonical_surfaces()
    assert terms, "expected multi-word glossary surfaces to be loaded from the seed file"
    violations = _scan_for_violations(terms)
    if violations:
        formatted = "\n  ".join(violations)
        pytest.fail(
            "Documentation uses non-canonical glossary-term casing.\n"
            "Canonical forms are defined in .kittify/glossaries/spec_kitty_core.yaml.\n"
            f"Violations ({len(violations)}):\n  {formatted}"
        )


def test_docs_adr_exemption_is_narrow() -> None:
    """docs/adr/ is exempt as historical snapshots, but the rest of docs/ is not.

    Mirrors test_no_legacy_terminology.py's identically-named test: pins the
    exemption as narrow (only docs/adr/, not a blanket docs/ carve-out) so a real
    casing regression elsewhere in docs/ is still caught.
    """
    hit = "docs/adr/3.x/2026-04-17-1-some-decision.md:103:Uses Action Context here."
    assert _line_is_excluded(hit), "docs/adr/ hits must be exempt (immutable snapshots)."

    still_scanned = (
        "docs/guides/onboarding.md:7:Uses Action Context here.",
        "docs/architecture/overview.md:12:Uses Action Context here.",
    )
    for other_hit in still_scanned:
        assert not _line_is_excluded(other_hit), (
            f"Non-ADR docs path must still be scanned: {other_hit!r}. The docs/adr/ exemption must not blanket-exempt all of docs/."
        )


def test_single_word_terms_are_excluded_from_scan() -> None:
    """Pins the precision-over-recall scope decision documented in the module docstring.

    A single, very common English word ("mission") must not appear in the scanned
    term list even though it is a real glossary surface — scanning it would produce
    overwhelming prose noise. A genuine multi-word phrase must still be included.
    """
    terms = _load_canonical_surfaces()
    assert "mission" not in terms
    assert "action context" in terms


def test_term_pattern_does_not_flag_canonical_form() -> None:
    """A term used in its exact canonical casing must not be flagged.

    Direct unit test of the pure per-line matcher (no git/filesystem dependency) —
    proves the "correctly does NOT fire" half of this WP's DoD without needing to
    stage or revert a real docs/ fixture file.
    """
    content = "See the action context for details on how this is resolved."
    assert _flagged_occurrences(content, "action context") == []


def test_term_pattern_flags_miscased_occurrence() -> None:
    """A deliberately miscased occurrence of a canonical term must be flagged.

    Direct unit test of the pure per-line matcher — proves the "DOES fire on a
    deliberately miscased string" half of this WP's DoD. The miscased string is
    injected only into this test's local variable, never written to a real docs/
    file, so there is nothing to remove afterward.
    """
    content = "See the Action Context for details on how this is resolved."
    assert _flagged_occurrences(content, "action context") == ["Action Context"]


def test_term_pattern_does_not_match_inside_longer_words() -> None:
    """A phrase must not match as a substring embedded in unrelated longer words.

    Regression guard for the fixed-string git-grep prefilter's lack of word-boundary
    awareness: "reaction contextual" contains "action context" as a raw substring,
    but must not be treated as an occurrence of the "action context" term.
    """
    content = "A reaction contextual to the change was recorded."
    assert _flagged_occurrences(content, "action context") == []


def test_term_pattern_normalizes_internal_whitespace() -> None:
    """Extra whitespace between words is normalized before the casing comparison.

    Per the contract: "case-sensitive comparison after normalizing whitespace" — a
    canonically-cased term split across a double space is not itself a violation.
    """
    content = "See the action  context for details."
    assert _flagged_occurrences(content, "action context") == []
