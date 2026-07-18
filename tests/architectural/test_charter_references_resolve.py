"""Durable no-dangling-reference invariant for charter.md (FR-009 / WP06).

Guards against dangling ``→ `token`` `` doctrine citations recurring
*anywhere* in ``.kittify/charter/charter.md`` -- not merely the Standing
Orders section, which is all the pre-existing, narrower WP05 coverage
(``tests/charter/test_model_task_routing_resolves.py``) checked. That
narrower coverage is exactly why the ``model-task-routing`` /
``autonomous-operation-protocol`` dangling references (in the Agent
Operating Discipline section) went unnoticed for a full charter revision.

Token discovery is derived entirely from the live charter.md text at test
time -- there is intentionally no hardcoded token list, so a *new* dangling
reference introduced by any future charter edit, in any section, is caught
by this same test without modification.

Resolution semantics mirror ``tests/charter/test_model_task_routing_resolves.py``:
a cited token only resolves if it is present as the id-suffix of a
reference the real charter compiler (:func:`charter.compiler.compile_charter`)
produces for this project's own interview answers and doctrine service --
never merely because the string appears somewhere on disk. Presence in the
compiled reference set is itself proof of directive/DRG reachability (or,
for paradigms, of interview selection), matching the resolution WP05 proved
correct.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from charter.compiler import compile_charter
from charter.interview import read_interview_answers
from charter.pack_context import PackContext
from doctrine.service import DoctrineService

pytestmark = [pytest.mark.fast, pytest.mark.doctrine]

REPO_ROOT = Path(__file__).resolve().parents[2]
CHARTER_PATH = REPO_ROOT / ".kittify" / "charter" / "charter.md"
ANSWERS_PATH = REPO_ROOT / ".kittify" / "charter" / "interview" / "answers.yaml"

# The two doctrine tokens this mission (model-discipline-dispatch-binding /
# #2364) exists to make resolve. They MUST NOT be baselined and MUST resolve
# on the lane -- that is the whole point of WP05, guarded belt-and-suspenders
# in ``test_mission_tokens_resolve_and_are_not_baselined`` below.
_MISSION_TOKENS = frozenset({"model-task-routing", "autonomous-operation-protocol"})

# Frozen-baseline shrink-only ratchet (mirrors the dead-module allowlist
# pattern in ``tests/architectural/``). It is SHRINK-ONLY: any token added
# back here without provably still dangling would let the baseline mask a
# regression that happens to reuse the same name; :func:`test_dangling_baseline_is_shrink_only`
# below enforces that invariant on whatever this set currently holds.
#
# #2380 CLOSED (WP03, unify-charter-activation-surfaces): all three tokens
# that used to live in this baseline now resolve, so the baseline is empty.
# WP02 (T026) made ``.kittify/config.yaml`` ``activated_*`` the direct
# activation root for styleguides/toolguides/tactics/procedures/agent
# profiles (not just directive-transitive-closure reachable), and paradigms
# are read directly from ``config.activated_paradigms`` rather than the
# retired ``interview.selected_paradigms``:
# - `domain-driven-design` now resolves: the paradigm is listed in
#   ``config.activated_paradigms`` and is loaded as a direct root.
# - `aggregate-design-rules` / `contextive` now resolve: both are listed in
#   ``config.activated_styleguides`` / ``config.activated_toolguides`` and
#   are seeded as direct roots (WP02 T026), independent of directive
#   transitive-closure reachability.
PRE_EXISTING_DANGLING_BASELINE: frozenset[str] = frozenset()

# The charter's citation marker: a bare arrow introduces a doctrine reference,
# e.g. "... enforced. → `DIRECTIVE_044`, `canonical-source-unification`."
_ARROW = "→"  # "→"
_BACKTICK_SPAN_RE = re.compile(r"`([^`\n]*)`")
_BULLET_START_RE = re.compile(r"(?:^|\n)[ \t]*(?:[-*]|\d+\.)[ \t]+")
# Doctrine artifact ids are bare identifiers: `DIRECTIVE_NNN` or a kebab-case
# slug. This excludes shapes that are never doctrine ids (a CLI flag like
# `--mission`, a dotted filename, a snake_case field name) without pinning
# any specific token.
_ARTIFACT_TOKEN_SHAPE_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]*")


def _backtick_spans(text: str) -> list[tuple[int, int]]:
    """Return the (start, end) span of every inline-code span in *text*."""
    return [match.span() for match in _BACKTICK_SPAN_RE.finditer(text)]


def _inside_any_span(position: int, spans: list[tuple[int, int]]) -> bool:
    return any(start <= position < end for start, end in spans)


def _citation_clause_end(charter_text: str, clause_start: int) -> int:
    """Return the end offset of the citation clause opened at *clause_start*.

    A citation clause ends at whichever comes first: the next arrow, a
    blank line, the next bullet/numbered list item, or the next ``:``/``;``.
    This keeps a citation from leaking into unrelated prose later in the
    same paragraph -- e.g. a rename note like
    "The `--feature` → `--mission` rename has been a persistent source of
    regressions." (the ``.`` after "regressions" is *not* reached; the
    clause is bounded well before any later bullet list), or a flow
    description like "red→green: the test was RED ... `planning_base_branch`
    ..." (the ``:`` right after "green" ends the clause before the later,
    unrelated backticked token is ever reached).
    """
    boundaries = [len(charter_text)]

    bullet_match = _BULLET_START_RE.search(charter_text, clause_start)
    if bullet_match is not None:
        boundaries.append(bullet_match.start())

    blank_line_match = re.search(r"\n[ \t]*\n", charter_text[clause_start:])
    if blank_line_match is not None:
        boundaries.append(clause_start + blank_line_match.start())

    next_arrow_match = re.search(_ARROW, charter_text[clause_start:])
    if next_arrow_match is not None:
        boundaries.append(clause_start + next_arrow_match.start())

    terminator_match = re.search(r"[:;]", charter_text[clause_start:])
    if terminator_match is not None:
        boundaries.append(clause_start + terminator_match.start())

    return min(boundaries)


def extract_charter_reference_tokens(charter_text: str) -> set[str]:
    """Derive every doctrine-reference token cited by charter.md prose.

    A reference is any backticked token that follows a bare ``→`` arrow,
    anywhere in the document. A single arrow may introduce a comma/plus
    -separated list of backticked tokens (e.g. ``→ `DIRECTIVE_043`,
    `architectural-gate-non-vacuity`.``) -- every backticked token in that
    citation clause counts; non-backticked prose in between (e.g. "the
    Architecture sections below") does not.

    An arrow embedded *inside* an existing inline-code span (e.g. the
    literal string `` `directive→artifact` `` describing an edge shape, not
    citing one) is excluded -- it is prose *about* the notation, not a
    citation.

    This function derives tokens purely from *charter_text*; it never
    hardcodes a token list, so it remains correct across future charter
    edits and across every section of the document (not just Standing
    Orders).
    """
    spans = _backtick_spans(charter_text)
    tokens: set[str] = set()

    for arrow_match in re.finditer(_ARROW, charter_text):
        if _inside_any_span(arrow_match.start(), spans):
            continue  # arrow is part of an inline-code example, not a citation

        clause_start = arrow_match.end()
        clause_end = _citation_clause_end(charter_text, clause_start)
        clause = charter_text[clause_start:clause_end]

        for token_match in _BACKTICK_SPAN_RE.finditer(clause):
            token = token_match.group(1).strip()
            if token and _ARTIFACT_TOKEN_SHAPE_RE.fullmatch(token):
                tokens.add(token)

    return tokens


def _compiled_reference_id_suffixes() -> set[str]:
    """Return every reference id-suffix the real charter compiler resolves.

    Mirrors ``tests/charter/test_model_task_routing_resolves.py``: uses the
    project's own interview answers and a real :class:`DoctrineService`
    rooted at ``src/doctrine`` so a resolved suffix is proof the reference
    is DRG/interview reachable, never merely a string dropped by hand into
    ``references.yaml``.

    WP03 (IC-01 consequence): the activation source is
    ``.kittify/config.yaml`` ``activated_*`` (FR-001/FR-002), not
    ``interview.selected_*`` -- ``pack_context`` is built explicitly here
    (mirroring the same explicit construction ``charter generate`` performs,
    see ``specify_cli.cli.commands.charter.generate.generate``) rather than
    left for :func:`compile_charter` to build implicitly from *repo_root*,
    so the config-sourced derivation this guard depends on is visible at the
    call site, not just an internal default.
    """
    interview = read_interview_answers(ANSWERS_PATH)
    assert interview is not None, "expected the project's real interview answers to load"

    doctrine_service = DoctrineService(built_in_root=REPO_ROOT / "src" / "doctrine")
    pack_context = PackContext.from_config(REPO_ROOT)
    compiled = compile_charter(
        mission=interview.mission,
        interview=interview,
        repo_root=REPO_ROOT,
        doctrine_service=doctrine_service,
        pack_context=pack_context,
    )

    return {reference.id.split(":", 1)[-1] for reference in compiled.references}


def test_charter_reference_extraction_is_non_vacuous() -> None:
    """Guard the guard: the parser must actually find citations in the real
    charter.md, spanning more than just the Standing Orders section -- a
    parser that silently finds nothing (or only one section's worth) would
    make the invariant below a vacuous, non-guarding gate."""
    charter_text = CHARTER_PATH.read_text(encoding="utf-8")
    tokens = extract_charter_reference_tokens(charter_text)

    assert len(tokens) > 10, (
        f"expected many charter reference citations across all sections, found only {sorted(tokens)}"
    )
    # Spot-check tokens from sections other than Standing Orders, proving the
    # scan is not scoped to that one section.
    assert "DIRECTIVE_001" in tokens, "Governing Principles section citation not found"
    assert "model-task-routing" in tokens, "Agent Operating Discipline section citation not found"


def _actual_dangling_tokens() -> set[str]:
    """Return every `→ `token`` citation in charter.md that does not resolve.

    Tokens are derived from the live charter.md text and checked against the
    live compiled reference set -- no literal token-to-check list is pinned,
    so a NEW dangling reference introduced by any future charter edit, in any
    section, appears here.
    """
    charter_text = CHARTER_PATH.read_text(encoding="utf-8")
    cited_tokens = extract_charter_reference_tokens(charter_text)
    resolved_suffixes = _compiled_reference_id_suffixes()
    return cited_tokens - resolved_suffixes


def test_no_new_charter_reference_danglers() -> None:
    """FR-009 / SC-004: no NEW dangling `→ `token`` citation may appear in
    charter.md, across every section.

    Frozen-baseline shrink-only ratchet: the actual dangling set must be a
    subset of :data:`PRE_EXISTING_DANGLING_BASELINE`. Any token that dangles
    and is NOT baselined -- a fresh dangling reference, or a regression of
    the mission's own ``model-task-routing`` / ``autonomous-operation-protocol``
    tokens -- fails this test. Tokens are derived from the live charter.md
    text (never hardcoded), so the guard tracks future charter edits
    automatically.
    """
    new_danglers = sorted(_actual_dangling_tokens() - PRE_EXISTING_DANGLING_BASELINE)
    assert not new_danglers, (
        "charter.md cites the following doctrine reference token(s) via a "
        "`→ `token`` citation, but none resolves to a compiled charter "
        f"reference (NEW dangling, not in the #2380 baseline): {new_danglers}. "
        "Wire the reference into DRG/interview reachability, or (if this is a "
        "pre-existing offender tracked elsewhere) file it -- do NOT widen the "
        "baseline to mask a regression."
    )


def test_dangling_baseline_is_shrink_only() -> None:
    """The #2380 baseline is shrink-only: every token in it must still
    actually dangle. Once #2380 wires one into reachability so it resolves,
    this test fails until the token is removed from
    :data:`PRE_EXISTING_DANGLING_BASELINE` -- keeping the ratchet honest so a
    stale baseline entry can never silently mask a future regression that
    reuses the same name.
    """
    now_resolving = sorted(PRE_EXISTING_DANGLING_BASELINE - _actual_dangling_tokens())
    assert not now_resolving, (
        "the following token(s) are in PRE_EXISTING_DANGLING_BASELINE but now "
        f"resolve: {now_resolving}. Remove them from the baseline (#2380 "
        "progress -- the ratchet is shrink-only)."
    )


def test_mission_tokens_resolve_and_are_not_baselined() -> None:
    """Belt-and-suspenders for the mission's own fix (WP05): the two tokens
    this mission makes resolve must NOT be baselined and MUST resolve on the
    lane. If WP05 regresses, both the subset guard above and this test fail.
    """
    baselined_mission_tokens = sorted(_MISSION_TOKENS & PRE_EXISTING_DANGLING_BASELINE)
    assert not baselined_mission_tokens, (
        "the mission's own tokens must never be baselined as pre-existing "
        f"danglers: {baselined_mission_tokens}"
    )

    still_dangling = sorted(_MISSION_TOKENS & _actual_dangling_tokens())
    assert not still_dangling, (
        "the mission's own doctrine tokens must resolve on the lane (WP05), "
        f"but these still dangle: {still_dangling}"
    )
