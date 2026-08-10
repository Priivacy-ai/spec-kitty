"""NFR-007 / FR-020 -- the verdict-seam census and its architectural check.

Three successive `review-cycle-verdict-seam-rebuild-01KZ2W7W` spec revisions
pinned a count of verdict WRITERS, location RESOLVERS, and frontmatter
READERS ("3 writers, 2 resolvers, 5 frontmatter readers") -- all three were
understated. NFR-007 exists because a number an implementer cannot re-derive
is not a requirement, it is folklore: this module builds the check that
*produces* the census. No numeral is pinned here in advance; every later WP's
reduction target is derived from this check's own output, not asserted in
prose.

Structure mirrors ``test_2093_authority_invariant.py``'s dual shape: an
AST-driven *derivation* pass over a concept-scoped module set
(:func:`_derive_census`), compared against a frozen *expected-set* fixture
(``tests/architectural/verdict_seam_census.yaml``, loaded at collection time
by :data:`_CENSUS_ROWS` below) that the check itself consults -- not a
parallel document nothing reads (FR-020).

**WP16/T071 update**: this file originally loaded
``tests/architectural/census/verdict_seam_IC01.yaml`` directly as its only
fixture, and separately re-loaded ``tests/architectural/census/verdict_seam_IC08.yaml``
just to prove the retire-row rule is non-vacuous against real data. Those were
WP01's and WP08's own per-concern fragments -- ``finalize-tasks``'s
``validate_no_overlap`` gate forbids two dependency-unordered WPs from
claiming the same ``owned_files`` entry, so each concern wrote its own
fragment rather than contending for one shared file. WP16 is the WP
positioned after every fragment-writing WP in the dependency graph, and its
job is the fold: ``tests/architectural/verdict_seam_census.yaml`` is now the
literal fixture this file consults (:data:`_CENSUS_FIXTURE_RELPATH` below),
folding WP01's 42 active rows and WP08's 5 retire rows into one document. The
two source fragments are NOT deleted (many other WPs' task/Activity-Log prose
and several ``src/``/``tests/`` docstrings cite them by path, outside this
WP's ``owned_files`` -- deleting them would orphan those citations); they
remain on disk as a frozen historical record, superseded only as this check's
expected-set fixture.

Reconciliation with ``test_2093_authority_invariant.py`` (T003)
-----------------------------------------------------------------
``test_2093_authority_invariant.py`` is a DIFFERENT concept: it is the
single-authority-per-runtime-field invariant (a WP's ``agent``/``assignee``/
``shell_pid``/... slot must have exactly one home -- the event log, never a
frontmatter fallback). Its ``_READER_AUTHORITY_ROOTS`` deliberately excludes
``review``, ``post_merge`` and ``agent_utils`` -- exactly the three packages
this census's readers live in -- because THIS census is about a different
question ("who reads a review-cycle artifact's persisted verdict, and with
what failure polarity"), not "which runtime field is event- vs.
frontmatter-authoritative". Widening ``test_2093``'s root tuple to cover this
census's packages would conflate the two concepts; this module does not do
that, and is not modified by this WP. Where this census needs to know whether
a *field* is event-authoritative (the "review" WPInnerStateDelta slot that
``_persist_review_artifact_override`` writes and
``_snapshot_review_override`` reads back), it imports ``_RUNTIME_SLOTS``
directly from ``specify_cli.status.reducer`` -- the same source
``test_2093_authority_invariant.py`` imports -- as :data:`_EVENT_SLOTS`,
rather than re-deriving or hand-typing an equivalent constant. See
``test_review_slot_is_event_authoritative_and_not_a_frontmatter_bypass``
below. Future maintainers: do not "helpfully" merge this file with
``test_2093_authority_invariant.py`` -- the two checks protect different
invariants that happen to share an AST-derivation *mechanism*.

Scope derivation (T004) -- concept, not a hand-typed allowlist
-----------------------------------------------------------------
The candidate module set is the UNION of two legs (:func:`_candidate_modules`),
because a single token grep proved insufficient in review (F2): a module can
construct the event-side ``ReviewResult``/``ReviewOverride`` record while
never mentioning "review-cycle" anywhere in its own text (the external
ingress in ``orchestrator_api/commands.py`` is the live instance -- see below).

* Leg 1 -- every ``*.py`` under ``src/`` referencing a `review-cycle` /
  `review_cycle` token (module text, string literals, docstrings, imports --
  :data:`_SCOPE_TOKEN_RE`).
* Leg 2 -- every ``*.py`` under ``src/`` calling ``ReviewResult(`` or
  ``ReviewOverride(`` as a constructor, OR either record's ``.from_dict(``
  FACTORY/classmethod form (:data:`_RECORD_CTOR_CALL_RE`; the ``.from_dict``
  half is T003/FR-010 -- a prior, now-closed blind spot: a record rehydrated
  via a factory call is exactly as much "construction" as a bare ``(...)``
  call), regardless of whether it also matches Leg 1.

Neither leg is a fixed module list -- both are re-derived from source text
each run. A small, growing set of named, reasoned exclusions is subtracted
from the union (:data:`_EXCLUDED_MODULE_REASONS`; the count has grown across
several WPs -- read the dict literal for the current, authoritative set
rather than trusting a number restated in prose here) -- by CONTENT (the
concept each file owns), not by filename. The original two:

* ``src/specify_cli/review/pre_review_gate.py`` -- its ``SOURCE_MISMATCH``
  outcome is a deliberate fail-open over baseline/head ``ScopeSource``
  identity divergence (FR-009/FR-011 of a different, already-landed
  mission), not a review-cycle verdict concept.
* ``src/specify_cli/review/verdict_aggregation.py`` -- aggregates
  ACCEPTANCE-CRITERION verdicts (the ``acceptance-verdict`` CLI command's
  domain), a different sense of "verdict" than a review cycle's
  approve/reject/override.

Honest note for the next reader: verified directly (``grep -n
"review-cycle\\|review_cycle"`` over both files, zero hits, and neither
constructs ``ReviewResult``/``ReviewOverride`` either), NEITHER file
currently matches EITHER leg, so today's candidate-scan does not actually
sweep either one in -- the exclusion is a FORWARD GUARD (T004's own edge
case: "if a future refactor moves a genuine review-cycle-verdict function
into pre_review_gate.py or verdict_aggregation.py ... the exclusion becomes
wrong silently"), proven live by
``test_pre_review_gate_and_verdict_aggregation_contribute_zero_rows`` and by
a synthetic-file proof that the NAME-based removal mechanism itself works
(``test_exclusion_mechanism_removes_a_synthetic_pre_review_gate_lookalike``).
If either file's purpose drifts toward this mission's review-cycle concept, a
reviewer must re-check this docstring, not assume the exclusion is inert
forever.

Why the token-grep leg alone is a blind spot (F2, live instance)
-----------------------------------------------------------------
``orchestrator_api/commands.py::_parse_review_result_json`` constructs
``ReviewResult(...)`` for the CLI's external ``--review-result-json``
ingress (spec.md's source-surface table: "EXTERNAL ingress; validates
ReviewResult at 4 fields"), but the module contains ZERO occurrences of
`review-cycle`/`review_cycle` (verified: ``grep -c`` returns 0). A
token-grep-only scope is blind to any writer that constructs the record
directly without ever mentioning the artifact's filename convention -- Leg 2
exists specifically to close that class of blind spot, not just this one
instance. (The same leg also picks up
``migration/backfill_runtime_state.py::_review_from_frontmatter``, a
backfill helper reconstructing a ``ReviewOverride`` from legacy WP
frontmatter -- an honest, independent finding of the same blind-spot class.)

Per-function classification is intentionally NOT a tidy partition: a function
that both resolves a review-cycle directory and reads its frontmatter (there
are some in this tree) is classified writer/resolver/reader independently --
each category has its own AST predicate and its own non-vacuity proof below,
so "adding a new resolver reds the resolver row-set specifically" (T004).

Resolver is ARTIFACT-anchored, not directory-anchored (F1)
-----------------------------------------------------------------
A resolver's job is to derive the location of a ``review-cycle-*.md``
artifact -- NOT merely to join a path through ``tasks/<wp>/``, which is a
directory several OTHER, deliberately different artifact kinds also share
(``baseline-tests.json`` -- PRIMARY per ADR 2026-08-03-1's own worked
example; ``tasks/WP*.md`` itself, a ``WORK_PACKAGE_TASK``;
``arbiter-override-N.json``). Per that ADR's own words (quoted in review):
"the rule must be filename-anchored (`review-cycle-*.md`), not
directory-anchored". :func:`_classify_resolver` therefore requires the
``tasks``-join + wp-identity-parameter shape AND rejects two concrete
non-review-cycle-artifact signals: a literal ``baseline-tests.json``
reference, or a ``.glob``/``.rglob`` call whose pattern does not itself
contain ``review-cycle`` (a bare ``{wp_id}*.md`` glob resolves the WP TASK
FILE, a different kind entirely). A function with no glob call at all (e.g.
``_review_cycle_wp_dir``, which returns a bare directory) is unaffected by
the glob leg -- its purpose is established by its callers, not a glob inside
itself.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path

import pytest
import yaml

from specify_cli.status.reducer import _RUNTIME_SLOTS

pytestmark = [pytest.mark.architectural, pytest.mark.corpus]

# ---------------------------------------------------------------------------
# T003 reconciliation -- import, never re-derive, the reducer's authority set.
# ---------------------------------------------------------------------------

#: Same import ``test_2093_authority_invariant.py`` uses (``_RUNTIME_SLOTS``
#: from ``status/reducer.py``); wrapped identically as a frozenset. NOT a
#: second read of a hand-typed field list -- see module docstring.
_EVENT_SLOTS: frozenset[str] = frozenset(_RUNTIME_SLOTS)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_MISSION_SLUG = "review-cycle-verdict-seam-rebuild-01KZ2W7W"
#: WP16/T071: re-pointed from the WP01-only fragment
#: (``tests/architectural/census/verdict_seam_IC01.yaml``) to the folded,
#: canonical census -- the ONE document this check now reads as its
#: expected-set fixture. See the module docstring's "WP16/T071 update" note.
_CENSUS_FIXTURE_RELPATH = "tests/architectural/verdict_seam_census.yaml"
#: The WP01 fragment this file's fixture was folded FROM -- still read
#: directly by :func:`test_wp01_fixture_retires_nothing` below, which checks
#: a property of WP01's OWN original fragment (that it retires nothing), not
#: of the post-fold document (which legitimately does carry retire rows
#: folded in from WP08's fragment).
_IC01_FRAGMENT_RELPATH = "tests/architectural/census/verdict_seam_IC01.yaml"


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "src" / "specify_cli").is_dir():
            return parent
    raise AssertionError("could not locate repo root from test file")


def _mission_spec_path(root: Path) -> Path:
    return root / "kitty-specs" / _MISSION_SLUG / "spec.md"


def _census_fixture_path(root: Path) -> Path:
    return root / _CENSUS_FIXTURE_RELPATH


# ---------------------------------------------------------------------------
# T004 -- scope derivation (subtractive, concept-scoped, never additive).
# ---------------------------------------------------------------------------

_SCOPE_TOKEN_RE: re.Pattern[str] = re.compile(r"review[-_]cycle")

#: Leg 2 (F2): a module that constructs the event-side record directly, OR
#: via a ``.from_dict(`` FACTORY/classmethod call (T003, FR-010) -- a
#: ``.from_dict``-shaped rehydration is exactly as much "construction" as a
#: bare ``ReviewResult(...)``/``ReviewOverride(...)`` call, just spelled as a
#: classmethod invocation -- is in scope even with zero
#: `review-cycle`/`review_cycle` text -- see module docstring's "blind spot"
#: section.
_RECORD_CTOR_CALL_RE: re.Pattern[str] = re.compile(
    r"\b(?:ReviewResult|ReviewOverride)(?:\(|\.from_dict\()"
)

_EXCLUDED_MODULE_REASONS: dict[str, str] = {
    "src/specify_cli/review/pre_review_gate.py": (
        "SOURCE_MISMATCH is a deliberate fail-open over baseline/head "
        "ScopeSource identity divergence (FR-009/FR-011 of a different, "
        "already-landed mission) -- not a review-cycle verdict concept."
    ),
    "src/specify_cli/review/verdict_aggregation.py": (
        "aggregates ACCEPTANCE-CRITERION verdicts (the acceptance-verdict "
        "CLI command's domain), a different sense of \"verdict\" than a "
        "review cycle's approve/reject/override."
    ),
    "src/specify_cli/cli/commands/_review_cycle_reconcile_doctor.py": (
        "WP08's FR-008 reconciliation detector deliberately REPLICATES the "
        "shape of the five resolvers this WP's own verdict_seam_IC08.yaml "
        "fragment marks retire (so the detector keeps working after WP10/12/13 "
        "rewrite or delete the live ones) -- its `_shape_*` helpers therefore "
        "structurally match the tasks-join + wp-identity-parameter resolver "
        "predicate. They are a detection MIRROR of those five resolvers, "
        "already named and reasoned about in IC08 by function name -- never a "
        "sixth live resolver participating in the writer/resolver/reader seam "
        "this census tracks (it never reads, writes, or fails closed on a "
        "review-cycle artifact; it only checks existence for a diagnostic "
        "report). Counting it here would double-count the same five retired "
        "resolvers under a different module path."
    ),
    # T004 (FR-010): the broadened `.from_dict` factory shape (T003) newly
    # matches these two modules' OWN `.from_dict`-based rehydration of an
    # ALREADY-REDUCED event snapshot's "review"/"review_result" slot back into
    # a typed `ReviewOverride`/`ReviewResult` -- the canonical event-authority
    # deserialization path (G2), not a NEW verdict construction. Both modules
    # contribute ZERO rows today (verified: no existing census row names
    # either path), so excluding them wholesale carries no shrinkage risk.
    # This is the census's negative control (US5 scenario 2): a genuine
    # event-authority deserializer stays excluded by a named reason, proving
    # T003's broadened predicate does not over-match every `.from_dict` call.
    # `status/models.py` -- home of BOTH the verified real gap
    # (`WPInnerStateDelta.from_dict`, T002) and its own event-log wire-format
    # decoder (`StatusEvent.from_dict`) -- is deliberately NOT added here: a
    # module-level exclusion cannot distinguish the two, and the gap must stay
    # counted, so `StatusEvent.from_dict` is instead disclosed as an honest,
    # non-hazardous new writer row directly in the fixture (see its `source`
    # comment there).
    "src/specify_cli/status/reducer.py": (
        "`review_result_from_state` rehydrates the reduced snapshot's "
        "`review_result` slot via `ReviewResult.from_dict` -- decoding the "
        "event log's OWN already-authoritative payload, not constructing a "
        "new verdict from a frontmatter/external source. Its same-module "
        "one-hop delegate `event_sourced_review_result` inherits the same "
        "reasoning, not a second finding."
    ),
    "src/specify_cli/status/wp_review.py": (
        "the canonical shared reader for the reduced-snapshot `review` slot "
        "(module docstring: single seam for the merge gate + CLI review-"
        "context resolution) reconstructs `ReviewOverride` via `.from_dict` "
        "from the reducer's own dict-shaped snapshot value -- event-authority "
        "rehydration, not a review-cycle-artifact reader/writer."
    ),
    # T004 forward-declared exclusion: authored HERE, by WP01, so WP04 never
    # needs to edit this census test -- no concurrent-edit race on the
    # exclusion list between dependency-unordered lanes (paula F2).
    # POST-MERGE UPDATE (verdict-seam-write-unification-01KZ9Q35
    # consolidation): the module NOW EXISTS on disk (WP04 landed
    # `verdict_vocab.py`), so this is no longer a vacuous forward guard -- the
    # exclusion was re-verified against the REAL module per the trip-wire in
    # `test_forward_declared_vocab_module_is_excluded` below: `verdict_vocab.py`
    # is a pure string->string vocabulary map (no artifact verdict I/O),
    # correctly excluded.
    #
    # WP03 (verdict-seam-boundary-hardening-01KZG179, #3236) UPDATE:
    # `migration/verdict_provenance_backfill.py` USED to carry a sibling entry
    # here, wholesale-excluding the whole module. That module-level exclusion
    # is now RETIRED in favour of the function-level mechanism above
    # (`_EXCLUDED_FUNCTIONS`): only `_backfill_event_for_wp` (the genuine
    # write-side helper) is excluded by name now, so the module's disclosed
    # #3236 reader blind spot -- `_legacy_frontmatter_verdict`, and its
    # same-module one-hop callers `terminal_review_artifact`/
    # `stranded_verdict_findings`/`backfill_verdict_provenance` -- surfaces as
    # real, classified reader (and resolver) rows in the fixture instead of
    # being silently suppressed. See `test_backfill_module_write_helper_is_
    # function_excluded_while_readers_surface` below for the live proof.
    "src/specify_cli/status/verdict_vocab.py": (
        "WP04's pure vocabulary-mapping surface bridges lane-transition verbs "
        "to `{approved, rejected}` `review_result` strings (D-PLAN-14: "
        "display-only for `arbiter_override`/`approved_after_orchestrator_fix` "
        "-- those never synthesize a `review_result` event). It maps strings "
        "to strings; it never reads, writes, or resolves a review-cycle "
        "verdict record."
    ),
}


# ---------------------------------------------------------------------------
# T011 (#3236 narrowing) -- function-level exclusion, the FUNCTION-scoped
# companion to `_EXCLUDED_MODULE_REASONS`. A module-level exclusion is
# all-or-nothing: it cannot express "this module's write-side migration
# mechanic is out of scope, but its genuine reader/resolver chain is not" --
# exactly the shape `verdict_provenance_backfill.py` needed (see its former
# module-level entry's own disclosed-blind-spot note, now retired in favour
# of this mechanism). Keyed on the SAME `(relpath, qualname)` identity a
# derived census pair uses, so a single function -- not a whole file --
# drops out of `_classify_module`'s base classification, and therefore out of
# the same-module one-hop closure's `base_by_name`/`call_names` too (an
# excluded function can no longer promote a caller into writer/resolver/
# reader by transitive closure, either).
# ---------------------------------------------------------------------------

_EXCLUDED_FUNCTIONS: dict[tuple[str, str], str] = {
    (
        "src/specify_cli/migration/verdict_provenance_backfill.py",
        "_backfill_event_for_wp",
    ): (
        "#3236 narrowing: the ONE write-side helper in this one-time "
        "provenance migration that hand-constructs the historical "
        "`ReviewResult`/`StatusEvent` (D-PLAN-10 -- deliberately NOT via "
        "`emit_status_transition`; see the module's own docstring). Excluding "
        "this ONE function -- not the whole module, as the prior "
        "`_EXCLUDED_MODULE_REASONS` entry did -- removes the writer signal "
        "from this migration, INCLUDING its transitive promotion into "
        "`backfill_verdict_provenance` via the same-module one-hop closure "
        "(that caller's own body contains no writer-shaped call itself; its "
        "writer status came entirely from calling this now-excluded helper). "
        "The module's genuine READ chain -- `_legacy_frontmatter_verdict` -> "
        "`terminal_review_artifact` -> `stranded_verdict_findings`/"
        "`backfill_verdict_provenance` -- is left fully classifiable, closing "
        "the #3236 blind spot the prior wholesale module exclusion caused."
    ),
}


def _candidate_modules(root: Path) -> list[Path]:
    """Grep-derived candidate module scope: every ``*.py`` under ``src/``
    matching EITHER the ``review-cycle``/``review_cycle`` token (Leg 1) OR a
    ``ReviewResult(``/``ReviewOverride(``/``.from_dict(`` constructor call
    (Leg 2), minus the named exclusions above. NOT a hand-typed allowlist --
    see module docstring."""
    candidates: list[Path] = []
    for path in sorted((root / "src").rglob("*.py")):
        relpath = path.relative_to(root).as_posix()
        if relpath in _EXCLUDED_MODULE_REASONS:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if _SCOPE_TOKEN_RE.search(text) or _RECORD_CTOR_CALL_RE.search(text):
            candidates.append(path)
    return candidates


# ---------------------------------------------------------------------------
# AST primitives (mirrors test_2093_authority_invariant.py's call-shape style)
# ---------------------------------------------------------------------------


def _iter_calls(node: ast.AST) -> Iterator[ast.Call]:
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            yield child


def _call_name(call: ast.Call) -> str | None:
    func = call.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return None


def _call_base_name(call: ast.Call) -> str | None:
    func = call.func
    if not isinstance(func, ast.Attribute):
        return None
    base = func.value
    if isinstance(base, ast.Name):
        return base.id
    if isinstance(base, ast.Attribute):
        return base.attr
    return None


def _arg_display_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _joined_string_literal(node: ast.AST) -> str | None:
    """Best-effort literal text of a ``Constant`` or an f-string's constant parts."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        parts = [
            part.value
            for part in node.values
            if isinstance(part, ast.Constant) and isinstance(part.value, str)
        ]
        return "".join(parts)
    return None


#: Calls whose arguments are human-DISPLAY text, not evidence of what a
#: function writes/resolves (F5: ``implement_try_render_fix_mode_prompt``
#: mentions ``review-cycle-{n}.md`` only inside a ``console.print(...)``
#: message -- it writes a PROMPT file, not a verdict record).
_DISPLAY_CALL_NAMES: frozenset[str] = frozenset({"print"})


def _iter_nodes_excluding_display_call_args(node: ast.AST) -> Iterator[ast.AST]:
    """Like ``ast.walk``, but does not descend into the arguments/keywords of
    a ``print``/``console.print``-shaped call -- literal text passed to a
    display call is human-facing output, not the path a function actually
    writes or resolves. The call node itself, and its ``func``, are still
    yielded."""
    stack: list[ast.AST] = [node]
    while stack:
        current = stack.pop()
        yield current
        if isinstance(current, ast.Call) and _call_name(current) in _DISPLAY_CALL_NAMES:
            stack.append(current.func)
            continue
        stack.extend(ast.iter_child_nodes(current))


def _collect_call_names(node: ast.AST) -> set[str]:
    """Bare-name and attribute call names reachable from *node* (for the
    same-module one-hop closure -- see :func:`_apply_same_module_one_hop_closure`)."""
    names: set[str] = set()
    for call in _iter_calls(node):
        func = call.func
        if isinstance(func, ast.Name):
            names.add(func.id)
        elif isinstance(func, ast.Attribute):
            names.add(func.attr)
    return names


def _function_param_names(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    args = node.args
    names = [a.arg for a in (*args.posonlyargs, *args.args, *args.kwonlyargs)]
    if args.vararg is not None:
        names.append(args.vararg.arg)
    if args.kwarg is not None:
        names.append(args.kwarg.arg)
    return names


# ---------------------------------------------------------------------------
# WRITER shape: creates/mutates a verdict record or the event's ReviewResult.
# ---------------------------------------------------------------------------

_WRITE_INDICATOR_SUBSTRINGS: tuple[str, ...] = ("write", "persist")
_RECORD_CTOR_NAMES: frozenset[str] = frozenset({"ReviewResult", "ReviewOverride"})


def _write_calls(node: ast.AST) -> list[ast.Call]:
    return [
        call
        for call in _iter_calls(node)
        if (name := _call_name(call)) and any(sub in name.lower() for sub in _WRITE_INDICATOR_SUBSTRINGS)
    ]


def _contains_mkdir_call(node: ast.AST) -> bool:
    return any(_call_name(call) == "mkdir" for call in _iter_calls(node))


def _has_artifact_named_arg(call: ast.Call) -> bool:
    return any(
        (name := _arg_display_name(arg)) and "artifact" in name.lower() for arg in call.args
    )


def _contains_review_cycle_filename_literal(node: ast.AST) -> bool:
    """True if a ``review-cycle-``-shaped literal appears OUTSIDE any
    ``print``/``console.print`` display call (F5) -- evidence the function
    itself builds/writes that filename, not merely mentions it in a message."""
    for child in _iter_nodes_excluding_display_call_args(node):
        if isinstance(child, (ast.Constant, ast.JoinedStr)):
            text = _joined_string_literal(child)
            if text and "review-cycle-" in text:
                return True
    return False


def _is_record_from_dict_call(call: ast.Call, names: frozenset[str]) -> bool:
    """T003 (FR-010): True for a ``<Record>.from_dict(...)`` FACTORY call --
    ``_call_name`` resolves such a call's own name to ``"from_dict"`` (the
    attribute), never the record name, so a direct ``in names`` check on
    ``_call_name`` alone is structurally blind to this shape (the pre-T003
    gap). Reuses ``_call_base_name`` (already shared with the reader
    predicate's ``ReviewCycleArtifact.from_file`` check) to resolve the
    callee's OWN base object instead."""
    return _call_name(call) == "from_dict" and _call_base_name(call) in names


def _contains_ctor(node: ast.AST, names: frozenset[str]) -> bool:
    return any(
        _call_name(call) in names or _is_record_from_dict_call(call, names)
        for call in _iter_calls(node)
    )


def _classify_writer(node: ast.AST, enclosing_class: str | None) -> bool:
    """A verdict WRITER: builds/writes a ``review-cycle-*.md``-shaped filename
    (F3: a ``mkdir`` call preparing that artifact's directory counts, not only
    an actual ``.write``/``.write_text`` -- ``workflow.py::review`` allocates
    the next cycle number and ``mkdir``s the sub-artifact dir without itself
    calling ``.write()``, deferring the physical write to a later command
    invocation, but the ALLOCATION is the FR-006 concern), is a
    ``.write``/``.persist``-shaped method on a ``ReviewCycle*``-named class,
    threads an artifact-named path into a write/persist call, or constructs
    the event-side ``ReviewResult``/``ReviewOverride``."""
    write_calls = _write_calls(node)
    has_mkdir = _contains_mkdir_call(node)
    if (write_calls or has_mkdir) and _contains_review_cycle_filename_literal(node):
        return True
    if enclosing_class is not None and "reviewcycle" in enclosing_class.lower().replace("_", "") and write_calls:
        return True
    if any(_has_artifact_named_arg(call) for call in write_calls):
        return True
    return _contains_ctor(node, _RECORD_CTOR_NAMES)


# ---------------------------------------------------------------------------
# RESOLVER shape: derives a review-cycle ARTIFACT's location from WP identity
# (F1: artifact-anchored, not merely directory-anchored -- see module
# docstring's "Resolver is ARTIFACT-anchored" section).
# ---------------------------------------------------------------------------

_WP_IDENTITY_PARAM_MARKERS: tuple[str, ...] = ("wp_id", "wp_slug", "task_id")

#: F1: a literal naming a DIFFERENT, deliberately-PRIMARY artifact kind that
#: happens to share the ``tasks/<wp>/`` directory with review-cycle records.
#: Referencing this filename is proof the function resolves THAT artifact,
#: not a review-cycle one -- ADR 2026-08-03-1's own worked example.
_NON_REVIEW_ARTIFACT_FILENAME_MARKERS: tuple[str, ...] = ("baseline-tests.json",)


def _is_tasks_constant(node: ast.expr) -> bool:
    return isinstance(node, ast.Constant) and node.value == "tasks"


def _tasks_join_present(node: ast.AST) -> bool:
    """True if a ``<expr> / "tasks"`` (or ``"tasks" / <expr>``) join appears --
    the shared shape of every named resolver (``_review_cycle_wp_dir``,
    ``_artifact_dirs_for_wp``, ``_resolve_wp_slug``, arbiter's
    ``_find_review_cycle_artifact``)."""
    for child in ast.walk(node):
        if (
            isinstance(child, ast.BinOp)
            and isinstance(child.op, ast.Div)
            and (_is_tasks_constant(child.left) or _is_tasks_constant(child.right))
        ):
            return True
    return False


def _has_wp_identity_param(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """True if a parameter name signals per-WP identity (``wp_id``/``wp_slug``/
    ``task_id``) -- the "from WP identity" half of the resolver concept, which
    excludes a feature-level ``tasks/`` lister (no WP identity input) from the
    resolver category even though it also joins a ``"tasks"`` literal."""
    lowered = [name.lower() for name in _function_param_names(node)]
    return any(marker in name for name in lowered for marker in _WP_IDENTITY_PARAM_MARKERS)


def _references_non_review_cycle_artifact(node: ast.AST) -> bool:
    """F1: True if a literal names a KNOWN, different artifact kind
    (``baseline-tests.json``) that shares the ``tasks/<wp>/`` directory but is
    deliberately not a review-cycle record."""
    for child in ast.walk(node):
        if isinstance(child, (ast.Constant, ast.JoinedStr)):
            text = _joined_string_literal(child)
            if text and any(marker in text for marker in _NON_REVIEW_ARTIFACT_FILENAME_MARKERS):
                return True
    return False


def _contains_review_cycle_glob(node: ast.AST) -> bool:
    for call in _iter_calls(node):
        if _call_name(call) in {"glob", "rglob"} and call.args:
            text = _joined_string_literal(call.args[0])
            if text and "review-cycle" in text:
                return True
    return False


def _has_non_review_cycle_glob(node: ast.AST) -> bool:
    """F1: True if the function calls ``.glob``/``.rglob`` at all AND NONE of
    those calls reference ``review-cycle`` -- e.g. a bare ``{wp_id}*.md`` glob
    resolves the WP's OWN task file (``WORK_PACKAGE_TASK``), a different
    artifact kind than a review-cycle record, even though it lives under the
    same ``tasks/<wp>/`` directory."""
    any_glob = False
    for call in _iter_calls(node):
        if _call_name(call) in {"glob", "rglob"} and call.args:
            any_glob = True
            text = _joined_string_literal(call.args[0])
            if text and "review-cycle" in text:
                return False
    return any_glob


def _classify_resolver(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    if not (_tasks_join_present(node) and _has_wp_identity_param(node)):
        return False
    if _references_non_review_cycle_artifact(node):
        return False
    return not _has_non_review_cycle_glob(node)


# ---------------------------------------------------------------------------
# READER shape: parses a review-cycle artifact's persisted frontmatter.
# ---------------------------------------------------------------------------

_FRONTMATTER_LOAD_NAMES: frozenset[str] = frozenset({"safe_load", "load"})


def _is_review_cycle_artifact_from_file_call(call: ast.Call) -> bool:
    func = call.func
    if not isinstance(func, ast.Attribute) or func.attr != "from_file":
        return False
    return _call_base_name(call) == "ReviewCycleArtifact"


def _is_extract_scalar_verdict_call(call: ast.Call) -> bool:
    if _call_name(call) != "extract_scalar" or len(call.args) < 2:
        return False
    field_arg = call.args[1]
    return isinstance(field_arg, ast.Constant) and field_arg.value == "verdict"


def _contains_manual_frontmatter_delimiter(node: ast.AST) -> bool:
    for child in ast.walk(node):
        if isinstance(child, (ast.Constant, ast.JoinedStr)):
            text = _joined_string_literal(child)
            if text and ("\n---" in text or text.startswith("^---") or text == "---"):
                return True
    return False


# ---------------------------------------------------------------------------
# T013 (#3217) -- the HELPER-CONSTRUCTED reader shape: a function that
# reconstructs a persisted verdict-override record from an ALREADY-PARSED
# frontmatter mapping's fields, rather than parsing raw text itself. The
# direct-parse shape above (``read_text`` + ``yaml.load`` + a frontmatter
# delimiter, all in ONE function body) is blind to this factoring --
# ``migration/backfill_runtime_state.py::_review_from_frontmatter`` never
# calls ``read_text``/``yaml.load`` itself; its caller (``read_legacy_runtime``)
# does the parse and hands this helper the resulting dict, which decodes the
# override-quartet fields back into a typed ``ReviewOverride``. That is
# exactly as much "reading a persisted verdict-override" as the direct shape,
# just split across a call boundary the direct-parse predicate cannot see.
# ---------------------------------------------------------------------------

#: The canonical frontmatter key PREFIX the write-side override quartet uses
#: (``review_artifact_override_at/_actor/_wp_id/_reason`` --
#: ``migration/backfill_runtime_state.py::_REVIEW_OVERRIDE_KEYS``,
#: ``review/artifacts.py``'s own ``to_dict``/``from_dict`` round-trip). A
#: ``.get(...)`` call keyed on this marker is evidence the value came from an
#: ALREADY-PARSED frontmatter mapping, not an unrelated dict -- e.g. the
#: external ``--review-result-json`` ingress's ``reviewer``/``verdict``/
#: ``reference`` keys (``orchestrator_api/commands.py::
#: _parse_review_result_json``), which never spell this marker.
_FRONTMATTER_OVERRIDE_KEY_MARKER = "review_artifact_override"


def _contains_frontmatter_override_get_call(node: ast.AST) -> bool:
    for call in _iter_calls(node):
        if _call_name(call) != "get" or not call.args:
            continue
        text = _joined_string_literal(call.args[0])
        if text and _FRONTMATTER_OVERRIDE_KEY_MARKER in text:
            return True
    return False


def _classify_helper_constructed_reader(node: ast.AST) -> bool:
    """True for a function that constructs ``ReviewResult``/``ReviewOverride``
    (reuses the writer predicate's own :func:`_contains_ctor`) AND extracts
    >=1 of its field values via a ``.get(...)`` call keyed on the canonical
    override-quartet frontmatter marker. Requiring BOTH keeps the predicate
    tight: a record built from a differently-shaped dict (no override-quartet
    key at all) stays writer-only, never promoted to reader by this branch --
    see the negative-control non-vacuity test below."""
    if not _contains_ctor(node, _RECORD_CTOR_NAMES):
        return False
    return _contains_frontmatter_override_get_call(node)


def _classify_reader(node: ast.AST) -> bool:
    """A verdict READER: parses a review-cycle artifact's persisted content --
    canonically via ``ReviewCycleArtifact.from_file``, or either hand-rolled
    equivalent this mission's own census exists to name: an
    ``extract_scalar(..., "verdict")`` read, or a manual ``read_text`` +
    ``---`` frontmatter-delimiter + YAML-load parse (mirrors
    ``test_2093_authority_invariant.py``'s own call-shape derivation pattern,
    T003). Deliberately NOT limited to the literal ``verdict`` attribute: the
    fold-97a9ecfae provenance scan (spec.md's own User Story 4 table) reads a
    prior cycle's ``.body``, and the arbiter override reader reads the whole
    frontmatter mapping to splice in ``arbiter_override`` -- both are readers
    of the same persisted record this census tracks, not a narrower field
    read. T013 (#3217) adds a THIRD shape: a helper-constructed reader (see
    :func:`_classify_helper_constructed_reader`) that reconstructs the same
    persisted record from an already-parsed frontmatter mapping, never
    calling ``read_text``/``yaml.load`` itself."""
    calls = list(_iter_calls(node))
    if any(_is_review_cycle_artifact_from_file_call(call) for call in calls):
        return True
    if any(_is_extract_scalar_verdict_call(call) for call in calls):
        return True
    if _classify_helper_constructed_reader(node):
        return True
    has_read_text = any(_call_name(call) == "read_text" for call in calls)
    if not has_read_text:
        return False
    has_yaml_load = any(_call_name(call) in _FRONTMATTER_LOAD_NAMES for call in calls)
    if not has_yaml_load:
        return False
    if _contains_manual_frontmatter_delimiter(node):
        return True
    return _contains_review_cycle_glob(node)


# ---------------------------------------------------------------------------
# Per-function classification: SAME-MODULE one-hop closure (never an
# iterated fixed point -- keeps a long orchestrator call chain, e.g.
# ``_do_move_task``, from cascading into "everything it transitively calls is
# a resolver", the exact failure mode F1 corrected for the base predicates),
# plus a SEPARATE, narrow, cross-module TRANSLATOR pass for readers only (F4).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _ClassifiedFunction:
    module: str
    qualname: str
    is_writer: bool
    is_resolver: bool
    is_reader: bool
    node: ast.FunctionDef | ast.AsyncFunctionDef


def _iter_functions(
    node: ast.AST, enclosing_class: str | None = None
) -> Iterator[tuple[ast.FunctionDef | ast.AsyncFunctionDef, str | None]]:
    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.ClassDef):
            yield from _iter_functions(child, child.name)
        elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield child, enclosing_class
            yield from _iter_functions(child, enclosing_class)


def _apply_same_module_one_hop_closure(
    results: list[_ClassifiedFunction],
    base_by_name: dict[str, _ClassifiedFunction],
    call_names: dict[str, set[str]],
) -> list[_ClassifiedFunction]:
    """Exactly one hop, frozen against the tier-1 base classification, SCOPED
    TO ONE MODULE (``base_by_name``/``call_names`` are built per-file by
    :func:`_classify_module`) -- never an iterated fixed point, so an
    orchestrator's whole call chain cannot cascade into "everything it calls,
    transitively, is a resolver." Promotes e.g. ``persist_arbiter_decision``
    (delegates entirely to ``_persist_in_artifact``, same file) to
    WRITER/READER without inventing a second, hand-typed allowlist of "known
    wrapper functions." Cross-FILE relationships (F4's translator case) are
    handled separately -- see :func:`_promote_cross_module_translators`."""
    promoted: list[_ClassifiedFunction] = []
    for classified in results:
        writer, resolver, reader = classified.is_writer, classified.is_resolver, classified.is_reader
        for called_name in call_names.get(classified.qualname, set()):
            callee = base_by_name.get(called_name)
            if callee is None or callee.qualname == classified.qualname:
                continue
            writer = writer or callee.is_writer
            resolver = resolver or callee.is_resolver
            reader = reader or callee.is_reader
        promoted.append(replace(classified, is_writer=writer, is_resolver=resolver, is_reader=reader))
    return promoted


def _classify_module(path: Path, root: Path) -> list[_ClassifiedFunction]:
    relpath = path.relative_to(root).as_posix()
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return []

    results: list[_ClassifiedFunction] = []
    base_by_name: dict[str, _ClassifiedFunction] = {}
    call_names: dict[str, set[str]] = {}

    for func_node, enclosing_class in _iter_functions(tree):
        qualname = f"{enclosing_class}.{func_node.name}" if enclosing_class else func_node.name
        if (relpath, qualname) in _EXCLUDED_FUNCTIONS:
            # T011: dropped BEFORE classification, base_by_name, and
            # call_names -- so this function contributes no row of its own
            # AND cannot promote a same-module caller via the one-hop closure
            # either (a caller's `call_names` lookup of this name resolves to
            # `base_by_name.get(...) is None`, which the closure loop skips).
            continue
        classified = _ClassifiedFunction(
            module=relpath,
            qualname=qualname,
            is_writer=_classify_writer(func_node, enclosing_class),
            is_resolver=_classify_resolver(func_node),
            is_reader=_classify_reader(func_node),
            node=func_node,
        )
        results.append(classified)
        base_by_name[func_node.name] = classified
        call_names[qualname] = _collect_call_names(func_node)

    return _apply_same_module_one_hop_closure(results, base_by_name, call_names)


# ---------------------------------------------------------------------------
# F4: the fail-closed TRANSLATOR shape -- a function two files (and,
# transitively, two calls) away from the literal frontmatter parse, whose OWN
# job is to catch a reader's ``ValueError``/``OSError`` and convert it into a
# declared-polarity result (a structured finding, here). This is
# DELIBERATELY NOT a general cross-module call-graph closure (that reopens
# F1's over-reach through any orchestrator with a wide fan-out, e.g.
# ``_do_move_task``): it requires the narrow, specific
# ``try: <call to an already-reader function> except (ValueError, OSError):``
# shape, which is exactly the polarity-declaring contract FR-012 / WP14's
# T066 cares about.
# ---------------------------------------------------------------------------

_TRANSLATOR_EXCEPT_NAMES: frozenset[str] = frozenset({"ValueError", "OSError"})


def _handler_catches_translator_exception(handler: ast.ExceptHandler) -> bool:
    exc_type = handler.type
    if exc_type is None:
        return False
    candidates = exc_type.elts if isinstance(exc_type, ast.Tuple) else [exc_type]
    return any(isinstance(c, ast.Name) and c.id in _TRANSLATOR_EXCEPT_NAMES for c in candidates)


def _wraps_a_reader_call_in_translator_except(node: ast.AST, reader_names: frozenset[str]) -> bool:
    for child in ast.walk(node):
        if not isinstance(child, ast.Try):
            continue
        if not any(_handler_catches_translator_exception(h) for h in child.handlers):
            continue
        for stmt in child.body:
            if any((_call_name(call) or "") in reader_names for call in _iter_calls(stmt)):
                return True
    return False


def _promote_cross_module_translators(functions: list[_ClassifiedFunction]) -> list[_ClassifiedFunction]:
    """Single, targeted pass (not iterated): promote a function to READER when
    it wraps a call to an ALREADY reader-classified function (post
    same-module closure, ACROSS any file) in a ``try/except
    (ValueError, OSError)`` translator shape. Uses bare call names -- a name
    shared by 2+ functions across the candidate set is excluded (ambiguous),
    same non-guessing discipline as the same-module closure."""
    by_bare_name: dict[str, list[_ClassifiedFunction]] = {}
    for func in functions:
        by_bare_name.setdefault(func.qualname.rsplit(".", 1)[-1], []).append(func)
    reader_names = frozenset(
        name for name, matches in by_bare_name.items() if len(matches) == 1 and matches[0].is_reader
    )

    promoted: list[_ClassifiedFunction] = []
    for func in functions:
        if not func.is_reader and _wraps_a_reader_call_in_translator_except(func.node, reader_names):
            promoted.append(replace(func, is_reader=True))
        else:
            promoted.append(func)
    return promoted


CensusPair = tuple[str, str]


@lru_cache(maxsize=8)
def _derive_census(root: Path) -> dict[str, frozenset[CensusPair]]:
    """The live writer/resolver/reader sets, derived fresh from *root* every
    call (cached only to avoid re-walking ``src/`` once per test function in
    the same run). Same-module one-hop closure runs inside
    :func:`_classify_module`; the cross-module translator promotion (F4) runs
    once, afterward, over the full candidate set."""
    all_functions: list[_ClassifiedFunction] = []
    for path in _candidate_modules(root):
        all_functions.extend(_classify_module(path, root))

    final = _promote_cross_module_translators(all_functions)

    writers: set[CensusPair] = set()
    resolvers: set[CensusPair] = set()
    readers: set[CensusPair] = set()
    for classified in final:
        pair = (classified.module, classified.qualname)
        if classified.is_writer:
            writers.add(pair)
        if classified.is_resolver:
            resolvers.add(pair)
        if classified.is_reader:
            readers.add(pair)
    return {"writer": frozenset(writers), "resolver": frozenset(resolvers), "reader": frozenset(readers)}


def _diff_sets(derived: frozenset[CensusPair], expected: frozenset[CensusPair]) -> tuple[
    frozenset[CensusPair], frozenset[CensusPair]
]:
    """Return ``(growth, shrinkage)``: members only in *derived* (a new,
    unclassified member), and members only in *expected* (one that vanished --
    e.g. a module deleted without updating the fixture)."""
    return derived - expected, expected - derived


# ---------------------------------------------------------------------------
# T005 -- the fixture is the check's LITERAL expected-set, loaded at
# collection time (not a separately-maintained Python constant).
# ---------------------------------------------------------------------------

_VALID_CATEGORIES: frozenset[str] = frozenset({"writer", "resolver", "reader"})
_VALID_STATUSES: frozenset[str] = frozenset({"active", "retire"})


@dataclass(frozen=True)
class _CensusRow:
    category: str
    module: str
    function: str
    status: str
    retiring_fr: str | None


def _load_census_rows(path: Path) -> list[_CensusRow]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise AssertionError(f"{path} must contain a YAML list of census rows")
    rows: list[_CensusRow] = []
    for entry in raw:
        if not isinstance(entry, dict):
            raise AssertionError(f"{path}: each census row must be a mapping, got {entry!r}")
        retiring_fr_value = entry.get("retiring_fr")
        rows.append(
            _CensusRow(
                category=str(entry.get("category", "")),
                module=str(entry.get("module", "")),
                function=str(entry.get("function", "")),
                status=str(entry.get("status", "")),
                retiring_fr=str(retiring_fr_value) if retiring_fr_value else None,
            )
        )
    return rows


#: Loaded at COLLECTION TIME (module import), per T005/FR-020: this is the
#: literal fixture every comparison test below consults -- editing a row in
#: ``verdict_seam_census.yaml`` (the WP16-folded document; see
#: ``_CENSUS_FIXTURE_RELPATH``) changes these rows on the next collection,
#: with no separate Python constant that merely happens to agree with it.
_CENSUS_ROWS: list[_CensusRow] = _load_census_rows(_census_fixture_path(_repo_root()))


def _active_pairs(rows: list[_CensusRow], category: str) -> frozenset[CensusPair]:
    return frozenset(
        (row.module, row.function) for row in rows if row.category == category and row.status == "active"
    )


# ---------------------------------------------------------------------------
# T002 -- a `retire` row with no retiring FR is a hard failure.
# ---------------------------------------------------------------------------

_FR_ROW_RE: re.Pattern[str] = re.compile(r"^\|\s*(FR-\d+)\s*\|")


def _parse_fr_status_table(spec_text: str) -> dict[str, str]:
    """Parse spec.md's Functional Requirements table into ``{FR-id: Status}``.
    Prefers parsing over a hard-coded FR-id set (T002) so the table can grow
    without this check going stale."""
    statuses: dict[str, str] = {}
    for line in spec_text.splitlines():
        match = _FR_ROW_RE.match(line.strip())
        if match is None:
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        statuses[match.group(1)] = cells[-1]
    return statuses


#: T002 amendment (operator ruling, WP08): every FR in this mission's spec.md
#: is ``Status: Open`` (the spec's Status column is unmaintained during
#: implementation -- no WP updates it), and FR-008's own target is retiring
#: paths WP01's census marks -- so keying the retire-row rule on that column
#: makes EVERY retire row illegal, permanently, the moment FR-008 needs one
#: (a self-set-to-zero deadlock: WP08 must land before WP13's narrowing, so at
#: WP08's time nothing may legally be marked retire, and WP08 cannot mark its
#: own IC08 rows because they would all fail the Status check). The real
#: purpose of the rule is to block a retire claim pointing at an FR **nobody
#: is delivering** -- a fabricated "this doesn't matter, retire it" dodge, not
#: to police the spec's Status prose. Keying on WP CLAIM (a ``retiring_fr``
#: named in some WP's ``requirement_refs`` frontmatter) tests exactly that:
#: some concrete work package has taken on delivering this FR, so the retire
#: claim traces to real, tracked work. Whether that WP's resolver is
#: GENUINELY unresolvable by mission exit is deferred to WP17 (mission-exit
#: verification), where it can actually be checked against landed code --
#: this rule only guards against the census-failure dodge at claim time.
_WP_TASK_FILE_RE: re.Pattern[str] = re.compile(r"^WP\d+.*\.md$")
_REQUIREMENT_REF_LIST_ITEM_RE: re.Pattern[str] = re.compile(r"^-\s*(\S+)\s*$")


def _parse_wp_claimed_frs(root: Path, mission_slug: str) -> frozenset[str]:
    """Return every FR/NFR/C id claimed by some WP's ``requirement_refs``
    frontmatter under ``kitty-specs/<mission_slug>/tasks/WP*.md`` (T002
    amendment). A minimal top-of-file frontmatter scan -- these files are
    hand-authored YAML-frontmatter Markdown, not something this check should
    fully parse as Markdown; it only needs the ``requirement_refs:`` list."""
    tasks_dir = root / "kitty-specs" / mission_slug / "tasks"
    claimed: set[str] = set()
    if not tasks_dir.is_dir():
        return frozenset(claimed)
    for wp_file in sorted(tasks_dir.iterdir()):
        if not wp_file.is_file() or not _WP_TASK_FILE_RE.match(wp_file.name):
            continue
        lines = wp_file.read_text(encoding="utf-8").splitlines()
        in_refs = False
        for line in lines:
            if line.strip() == "---" and in_refs:
                break
            if line.rstrip() == "requirement_refs:":
                in_refs = True
                continue
            if in_refs:
                match = _REQUIREMENT_REF_LIST_ITEM_RE.match(line)
                if match is None:
                    break
                claimed.add(match.group(1))
    return frozenset(claimed)


def _validate_retire_rows(
    rows: list[_CensusRow], fr_status: Mapping[str, str], claimed_frs: Iterable[str] = (),
) -> list[str]:
    """Every ``status: retire`` row must name a non-empty ``retiring_fr`` that
    both (a) EXISTS in spec.md's FR table, AND (b) is claimed by at least one
    WP's ``requirement_refs`` -- a hard failure, not a warning (T002, amended
    by operator ruling to key on WP claim rather than spec.md's unmaintained
    Status column; see the docstring above :func:`_parse_wp_claimed_frs`)."""
    claimed = frozenset(claimed_frs)
    errors: list[str] = []
    for row in rows:
        if row.status != "retire":
            continue
        label = f"{row.category}:{row.module}::{row.function}"
        if not row.retiring_fr:
            errors.append(f"{label} is status=retire with no retiring_fr")
            continue
        if row.retiring_fr not in fr_status:
            errors.append(f"{label} retiring_fr={row.retiring_fr!r} does not exist in spec.md's FR table")
        elif row.retiring_fr not in claimed:
            errors.append(
                f"{label} retiring_fr={row.retiring_fr!r} is not claimed by any WP's "
                "requirement_refs -- cannot retire against an FR nobody is delivering"
            )
    return errors


# ===========================================================================
# Tests
# ===========================================================================


def test_fixture_rows_use_the_declared_vocabulary() -> None:
    """Every row's category/status is one of the declared enums (T005 schema)."""
    assert _CENSUS_ROWS, "verdict_seam_census.yaml must not be empty"
    for row in _CENSUS_ROWS:
        assert row.category in _VALID_CATEGORIES, f"unknown category {row.category!r} on {row}"
        assert row.status in _VALID_STATUSES, f"unknown status {row.status!r} on {row}"


def test_wp01_fixture_retires_nothing() -> None:
    """WP01 was pure enumeration -- it fixed nothing, so every row ITS OWN
    original fragment landed is status=active (Reviewer Guidance). This checks
    the WP01 fragment directly (``_IC01_FRAGMENT_RELPATH``, retained on disk
    per the module docstring's "WP16/T071 update" note), NOT the post-fold
    :data:`_CENSUS_ROWS` -- the folded document legitimately DOES carry retire
    rows (folded in from WP08's fragment; see
    ``test_real_fixture_retire_rows_are_valid`` below), so asserting
    zero-retire-rows against the fold itself would be false after WP16."""
    root = _repo_root()
    ic01_rows = _load_census_rows(root / _IC01_FRAGMENT_RELPATH)
    retired = [row for row in ic01_rows if row.status == "retire"]
    assert retired == [], f"WP01's own fragment must not retire anything; found: {retired}"


def test_real_fixture_retire_rows_are_valid() -> None:
    """T002 applied to the real, live, POST-FOLD fixture. Before WP16's fold
    this was a vacuous pass (WP01's IC01-only fixture retired nothing); after
    the fold, :data:`_CENSUS_ROWS` carries the 5 retire rows WP16 folded in
    from WP08's ``verdict_seam_IC08.yaml`` fragment, so this is now the
    NON-VACUOUS real-data proof of the rule itself (the explicit assertion
    below pins that non-vacuity so a future edit cannot silently make it
    vacuous again without this test noticing)."""
    root = _repo_root()
    retired = [row for row in _CENSUS_ROWS if row.status == "retire"]
    assert retired, (
        "the folded census must carry at least one retire row (WP08's five, "
        "folded by WP16) -- a fixture with none would make this test vacuous again"
    )
    fr_status = _parse_fr_status_table(_mission_spec_path(root).read_text(encoding="utf-8"))
    claimed_frs = _parse_wp_claimed_frs(root, _MISSION_SLUG)
    assert _validate_retire_rows(_CENSUS_ROWS, fr_status, claimed_frs) == []


@pytest.mark.parametrize("category", sorted(_VALID_CATEGORIES))
def test_derived_census_matches_fixture(category: str) -> None:
    """The check's core assertion: the AST-derived writer/resolver/reader set
    over the live tree equals exactly the fixture's active rows for that
    category. Fails on EITHER direction of drift -- growth (a new,
    unclassified member) or shrinkage (a member vanishing without the fixture
    being updated)."""
    root = _repo_root()
    derived = _derive_census(root)[category]
    expected = _active_pairs(_CENSUS_ROWS, category)
    growth, shrinkage = _diff_sets(derived, expected)
    assert not growth, (
        f"new {category}(s) found in src/ not yet classified in "
        f"verdict_seam_census.yaml: {sorted(growth)}"
    )
    assert not shrinkage, (
        f"{category}(s) in verdict_seam_census.yaml no longer found in src/ "
        f"(module deleted/renamed without updating the fixture): {sorted(shrinkage)}"
    )


def test_pre_review_gate_and_verdict_aggregation_contribute_zero_rows() -> None:
    """T004: neither excluded module contributes a writer/resolver/reader row."""
    derived = _derive_census(_repo_root())
    excluded = set(_EXCLUDED_MODULE_REASONS)
    for category, pairs in derived.items():
        offending = {module for module, _ in pairs if module in excluded}
        assert not offending, f"{category} derivation includes an excluded module: {offending}"


def test_exclusion_reasons_are_named_and_non_empty() -> None:
    """T004: each exclusion carries a recorded reason, never a silent absence."""
    for relpath, reason in _EXCLUDED_MODULE_REASONS.items():
        assert reason.strip(), f"{relpath} exclusion has no recorded reason"


def test_excluded_function_reasons_are_named_and_non_empty() -> None:
    """T011: the function-level companion to
    ``test_exclusion_reasons_are_named_and_non_empty`` -- each
    ``_EXCLUDED_FUNCTIONS`` entry carries a recorded reason, never a silent
    absence."""
    for (relpath, qualname), reason in _EXCLUDED_FUNCTIONS.items():
        assert reason.strip(), f"{relpath}::{qualname} exclusion has no recorded reason"


def test_wp_inner_state_delta_from_dict_is_the_verified_from_dict_gap() -> None:
    """T002/T005 real-data test (D-PLAN-14, NFR-002): the VERIFIED live
    ``.from_dict`` gap site is ``status/models.py::WPInnerStateDelta.from_dict``
    -- it constructs ``ReviewOverride`` via ``ReviewOverride.from_dict(review_raw)``
    at ``status/models.py:570`` while rehydrating a WP's review-delta annotation.
    (Re-verification note, T002's own "don't assume" discipline: research.md's
    D-PLAN-14 names ``migration/backfill_runtime_state.py::_runtime_repair_delta``
    as the ALREADY-matched direct-ctor case, distinct from this gap -- but
    re-checked directly against the live tree, ``_runtime_repair_delta`` turns
    out to ALSO use the ``.from_dict`` factory shape today, not a direct ctor;
    it is a second, independent instance of the same gap and is reconciled as
    its own active row below, not conflated with this one.) Classified as a
    writer only after T003's broadened predicate -- the real-data companion to
    the synthetic poison test (NFR-002: >=1 synthetic + >=1 real-data)."""
    root = _repo_root()
    derived_writers = _derive_census(root)["writer"]
    assert ("src/specify_cli/status/models.py", "WPInnerStateDelta.from_dict") in derived_writers


def test_reducer_event_authority_deserializer_stays_excluded_by_named_reason() -> None:
    """T004/T005 negative control (US5 scenario 2, G2): ``status/reducer.py``'s
    ``review_result_from_state`` constructs ``ReviewResult`` via ``.from_dict``
    from an ALREADY-REDUCED event snapshot -- the exact call shape T003's
    broadened predicate would otherwise sweep in as a new writer -- yet stays
    OUT of the derived writer set because its whole module is named-excluded
    with a recorded reason, never a silent skip (T004: a growth failure here
    would mean the exclusion stopped working; an empty/missing reason would
    fail ``test_exclusion_reasons_are_named_and_non_empty`` instead)."""
    root = _repo_root()
    derived_writers = _derive_census(root)["writer"]
    assert ("src/specify_cli/status/reducer.py", "review_result_from_state") not in derived_writers
    assert _EXCLUDED_MODULE_REASONS["src/specify_cli/status/reducer.py"].strip()


def test_review_slot_is_event_authoritative_and_not_a_frontmatter_bypass() -> None:
    """T003 non-vacuity: ``"review"`` is one of the reducer's own
    ``_EVENT_SLOTS`` (imported, not re-derived) -- so a function that reads
    ``state.get("review")`` off a REDUCED SNAPSHOT
    (``post_merge/review_artifact_consistency.py::_snapshot_review_override``)
    is reading the event-authoritative copy, not a frontmatter bypass this
    census's reader heuristic should ever flag. Proven directly against the
    reader-shape predicate."""
    assert "review" in _EVENT_SLOTS
    snapshot_read = ast.parse("def f(state):\n    return state.get('review')\n").body[0]
    assert isinstance(snapshot_read, ast.FunctionDef)
    assert _classify_reader(snapshot_read) is False


def _write_module(root: Path, relpath: str, source: str) -> Path:
    path = root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def _classify_all(root: Path) -> list[_ClassifiedFunction]:
    """Test-only helper: base-classify (no closure) every candidate module
    under *root* -- used by the synthetic non-vacuity proofs below, which
    check a single new function's OWN shape rather than the full 2-hop
    census."""
    all_functions: list[_ClassifiedFunction] = []
    for path in _candidate_modules(root):
        all_functions.extend(_classify_module(path, root))
    return all_functions


def test_new_module_with_writer_shape_reds(tmp_path: Path) -> None:
    """Permanent synthetic poison (DoD): a wholly NEW module under
    ``src/specify_cli/review/`` (never an edit to an already-known module)
    containing a function that writes a ``review-cycle-*.md``-shaped file is
    detected as a writer -- the exact case a hand-typed module allowlist could
    never satisfy."""
    relpath = "src/specify_cli/review/synthetic_new_writer.py"
    _write_module(
        tmp_path,
        relpath,
        "from pathlib import Path\n\n\n"
        "def write_review_cycle_verdict(sub_dir: Path, cycle_n: int, body: str) -> Path:\n"
        "    path = sub_dir / f'review-cycle-{cycle_n}.md'\n"
        "    path.write_text(body, encoding='utf-8')\n"
        "    return path\n",
    )
    candidate_relpaths = {p.relative_to(tmp_path).as_posix() for p in _candidate_modules(tmp_path)}
    assert relpath in candidate_relpaths, "the new module must join the candidate scope"

    derived_writers = {(c.module, c.qualname) for c in _classify_all(tmp_path) if c.is_writer}
    assert (relpath, "write_review_cycle_verdict") in derived_writers


def test_new_resolver_shape_reds(tmp_path: Path) -> None:
    """Permanent synthetic poison: a new function deriving a review-cycle
    directory from WP identity (a ``"tasks"`` join plus a wp-identity param,
    with no non-review-cycle artifact/glob signal) is detected as a resolver."""
    relpath = "src/specify_cli/review/synthetic_new_resolver.py"
    _write_module(
        tmp_path,
        relpath,
        "from pathlib import Path\n\n\n"
        "def resolve_review_cycle_wp_dir(feature_dir: Path, wp_id: str) -> Path:\n"
        "    return feature_dir / 'tasks' / wp_id\n",
    )
    derived_resolvers = {(c.module, c.qualname) for c in _classify_all(tmp_path) if c.is_resolver}
    assert (relpath, "resolve_review_cycle_wp_dir") in derived_resolvers


def test_baseline_tests_json_resolver_lookalike_is_not_a_resolver(tmp_path: Path) -> None:
    """F1 non-vacuity (negative control): a function with the IDENTICAL
    ``tasks``-join + wp-identity-param shape, but resolving
    ``baseline-tests.json`` (a deliberately PRIMARY, non-review-cycle
    artifact per ADR 2026-08-03-1), must NOT be classified as a resolver."""
    relpath = "src/specify_cli/review/synthetic_baseline_lookalike.py"
    _write_module(
        tmp_path,
        relpath,
        "from pathlib import Path\n\n\n"
        "def resolve_review_cycle_baseline_dir(feature_dir: Path, wp_id: str) -> Path:\n"
        "    return feature_dir / 'tasks' / wp_id / 'baseline-tests.json'\n",
    )
    derived_resolvers = {(c.module, c.qualname) for c in _classify_all(tmp_path) if c.is_resolver}
    assert (relpath, "resolve_review_cycle_baseline_dir") not in derived_resolvers


def test_wp_task_file_glob_resolver_lookalike_is_not_a_resolver(tmp_path: Path) -> None:
    """F1 non-vacuity (negative control): a function joining ``tasks/`` with a
    wp-identity param, but globbing a bare ``{wp_id}*.md`` pattern (the WP's
    OWN task file, a ``WORK_PACKAGE_TASK``) rather than a
    ``review-cycle-*.md`` pattern, must NOT be classified as a resolver."""
    relpath = "src/specify_cli/review/synthetic_wp_file_lookalike.py"
    _write_module(
        tmp_path,
        relpath,
        "from pathlib import Path\n\n\n"
        "def resolve_review_cycle_wp_file(feature_dir: Path, wp_id: str) -> list[Path]:\n"
        "    return sorted((feature_dir / 'tasks').glob(f'{wp_id}*.md'))\n",
    )
    derived_resolvers = {(c.module, c.qualname) for c in _classify_all(tmp_path) if c.is_resolver}
    assert (relpath, "resolve_review_cycle_wp_file") not in derived_resolvers


def test_new_reader_shape_reds(tmp_path: Path) -> None:
    """Permanent synthetic poison: a new function parsing a review-cycle
    artifact's frontmatter (via the canonical ``ReviewCycleArtifact.from_file``
    call shape) is detected as a reader."""
    relpath = "src/specify_cli/review/synthetic_new_reader.py"
    _write_module(
        tmp_path,
        relpath,
        "from pathlib import Path\n\n\n"
        "from specify_cli.review.artifacts import ReviewCycleArtifact\n\n\n"
        "def read_review_cycle_verdict(path: Path) -> str:\n"
        "    return ReviewCycleArtifact.from_file(path).verdict\n",
    )
    derived_readers = {(c.module, c.qualname) for c in _classify_all(tmp_path) if c.is_reader}
    assert (relpath, "read_review_cycle_verdict") in derived_readers


def test_helper_constructed_reader_shape_reds(tmp_path: Path) -> None:
    """T013 (#3217) two-way teeth, POSITIVE half: a NEW function that
    reconstructs a ``ReviewOverride`` from an override-quartet frontmatter
    dict via ``.get(...)`` calls -- never calling ``read_text``/``yaml.load``
    itself -- is still detected as a reader. Reproduces the live
    ``migration/backfill_runtime_state.py::_review_from_frontmatter`` shape
    exactly. Fails if :func:`_classify_helper_constructed_reader`'s branch is
    removed or neutered -- the exact regression this teeth exists to catch (a
    fixture-presence assert alone would not fail on that regression)."""
    relpath = "src/specify_cli/review/synthetic_helper_constructed_reader.py"
    _write_module(
        tmp_path,
        relpath,
        "from specify_cli.status.models import ReviewOverride\n\n\n"
        "def rebuild_review_override_from_frontmatter(frontmatter: dict, wp_id: str):\n"
        "    at = frontmatter.get('review_artifact_override_at')\n"
        "    actor = frontmatter.get('review_artifact_override_actor')\n"
        "    reason = frontmatter.get('review_artifact_override_reason')\n"
        "    if not (at and actor and reason):\n"
        "        return None\n"
        "    return ReviewOverride(at=str(at), actor=str(actor), wp_id=wp_id, reason=str(reason))\n",
    )
    derived_readers = {(c.module, c.qualname) for c in _classify_all(tmp_path) if c.is_reader}
    assert (relpath, "rebuild_review_override_from_frontmatter") in derived_readers


def test_helper_constructed_record_from_unrelated_keys_is_not_a_reader(tmp_path: Path) -> None:
    """T013 (#3217) two-way teeth, NEGATIVE half: a function that ALSO
    constructs a ``ReviewResult`` via ``.get(...)`` calls, but keyed on
    UNRELATED dict fields (the external-ingress shape:
    ``reviewer``/``verdict``/``reference``, never the override-quartet
    marker -- the real ``orchestrator_api/commands.py::
    _parse_review_result_json`` shape), must NOT be classified as a reader --
    guards the over-match risk the module docstring's risk section names.
    Stays a writer (unaffected by this predicate); this test pins only the
    reader-negative half."""
    relpath = "src/specify_cli/review/synthetic_unrelated_dict_ctor.py"
    _write_module(
        tmp_path,
        relpath,
        "from specify_cli.status.models import ReviewResult\n\n\n"
        "def build_review_result_from_payload(payload: dict) -> ReviewResult:\n"
        "    reviewer = payload.get('reviewer')\n"
        "    verdict = payload.get('verdict')\n"
        "    reference = payload.get('reference')\n"
        "    return ReviewResult(reviewer=reviewer, verdict=verdict, reference=reference)\n",
    )
    classified = {(c.module, c.qualname): c for c in _classify_all(tmp_path)}
    key = (relpath, "build_review_result_from_payload")
    assert classified[key].is_writer, "sanity: the record-ctor call still makes this a writer"
    assert not classified[key].is_reader, (
        "a record built from a dict with no override-quartet marker key must "
        "not be promoted to reader"
    )


def test_display_only_review_cycle_mention_is_not_a_writer(tmp_path: Path) -> None:
    """F5 non-vacuity: a function that only MENTIONS a
    ``review-cycle-N.md``-shaped filename inside a ``print(...)`` display
    call, while writing an unrelated file, must NOT be classified as a writer
    -- the exact shape ``implement_try_render_fix_mode_prompt`` matched before
    this fix (it writes a PROMPT file; the review-cycle text is only ever
    console-printed for the human)."""
    relpath = "src/specify_cli/review/synthetic_display_only.py"
    _write_module(
        tmp_path,
        relpath,
        "from pathlib import Path\n\n\n"
        "def write_prompt_mentioning_review_cycle(cycle_n: int, prompt_text: str, out_path: Path) -> Path:\n"
        "    print(f'generating from review-cycle-{cycle_n}.md')\n"
        "    out_path.write_text(prompt_text, encoding='utf-8')\n"
        "    return out_path\n",
    )
    derived_writers = {(c.module, c.qualname) for c in _classify_all(tmp_path) if c.is_writer}
    assert (relpath, "write_prompt_mentioning_review_cycle") not in derived_writers


def test_scope_leg_2_catches_a_bare_review_result_constructor(tmp_path: Path) -> None:
    """F2 non-vacuity: a module with ZERO ``review-cycle``/``review_cycle``
    text, but constructing ``ReviewResult(...)`` directly, still joins the
    candidate scope (Leg 2) and is classified a writer -- the
    ``orchestrator_api/commands.py::_parse_review_result_json`` shape."""
    relpath = "src/specify_cli/review/synthetic_external_ingress.py"
    _write_module(
        tmp_path,
        relpath,
        "from specify_cli.status import ReviewResult\n\n\n"
        "def parse_external_review_result(reviewer: str, verdict: str, reference: str) -> ReviewResult:\n"
        "    return ReviewResult(reviewer=reviewer, verdict=verdict, reference=reference)\n",
    )
    candidate_relpaths = {p.relative_to(tmp_path).as_posix() for p in _candidate_modules(tmp_path)}
    assert relpath in candidate_relpaths, "Leg 2 (ReviewResult/ReviewOverride ctor) must admit this module"

    derived_writers = {(c.module, c.qualname) for c in _classify_all(tmp_path) if c.is_writer}
    assert (relpath, "parse_external_review_result") in derived_writers


def test_new_module_with_from_dict_factory_writer_shape_reds(tmp_path: Path) -> None:
    """T001 (FR-010, red-first): a function constructing a review record via a
    FACTORY/classmethod call -- ``ReviewOverride.from_dict(...)`` -- rather
    than a direct ``ReviewOverride(...)`` constructor, must still join the
    candidate scope (Leg 2) and red the census as a writer, exactly the live
    ``status/models.py::WPInnerStateDelta.from_dict`` shape (T002: verified
    directly -- ``ReviewOverride.from_dict(review_raw)`` at
    ``status/models.py:570``, not ``migration/backfill_runtime_state.py::
    _runtime_repair_delta``, which research.md's D-PLAN-14 named as the
    already-matched direct-ctor case but which -- re-verified against the live
    tree -- turns out to ALSO use the ``.from_dict`` factory shape; see the
    real-data test and the module-docstring note below). Neither
    ``_RECORD_CTOR_CALL_RE`` (Leg 2's module-scope regex: literal
    ``ReviewResult(``/``ReviewOverride(``) nor ``_contains_ctor``'s
    ``_call_name``-based callee match (which resolves a ``.from_dict(``
    call's own name to ``"from_dict"``, never the record name) recognizes this
    shape before T003 extends both via ``_call_base_name`` -- so this
    synthetic module is invisible to BOTH legs and the function is
    unclassified: RED before T003 lands (verified: this test's commit precedes
    T003's in the WP01 commit trail, C-002), GREEN after."""
    relpath = "src/specify_cli/review/synthetic_from_dict_poison.py"
    _write_module(
        tmp_path,
        relpath,
        "from specify_cli.status.models import ReviewOverride\n\n\n"
        "def rehydrate_review_override(raw: dict) -> object:\n"
        "    return ReviewOverride.from_dict(raw)\n",
    )
    candidate_relpaths = {p.relative_to(tmp_path).as_posix() for p in _candidate_modules(tmp_path)}
    assert relpath in candidate_relpaths, (
        "a `.from_dict(` factory call must join the candidate scope (Leg 2), "
        "same as a direct constructor call"
    )

    derived_writers = {(c.module, c.qualname) for c in _classify_all(tmp_path) if c.is_writer}
    assert (relpath, "rehydrate_review_override") in derived_writers


def test_cross_module_translator_reaches_a_fail_closed_finder(tmp_path: Path) -> None:
    """F4 non-vacuity: reproduces the ``find_rejected_review_artifact_conflicts``
    shape exactly -- a direct reader and a SAME-MODULE one-hop delegate to it
    (``rejected_review_artifact_for_terminal_lane``'s relationship to
    ``latest_review_artifact_verdict``, both in ``review/artifacts.py``), and
    a DIFFERENT-MODULE function that wraps a call to the delegate in
    ``try/except ValueError`` (``post_merge/review_artifact_consistency.py``'s
    relationship to it). The cross-module TRANSLATOR pass, not a general
    call-graph closure, must promote the finder to READER."""
    _write_module(
        tmp_path,
        "src/specify_cli/review/synthetic_artifacts.py",
        "from pathlib import Path\n\n\n"
        "from specify_cli.review.artifacts import ReviewCycleArtifact\n\n\n"
        "def direct_review_cycle_reader(path: Path) -> str:\n"
        "    return ReviewCycleArtifact.from_file(path).verdict\n\n\n"
        "def one_hop_review_cycle_reader(path: Path) -> str:\n"
        "    return direct_review_cycle_reader(path)\n",
    )
    _write_module(
        tmp_path,
        "src/specify_cli/post_merge/synthetic_translator.py",
        "from pathlib import Path\n\n\n"
        "from specify_cli.review.synthetic_artifacts import one_hop_review_cycle_reader\n\n\n"
        "def find_review_cycle_read_failures(path: Path) -> dict[str, str]:\n"
        "    try:\n"
        "        verdict = one_hop_review_cycle_reader(path)\n"
        "    except ValueError as exc:\n"
        "        return {'finding': str(exc)}\n"
        "    return {'verdict': verdict}\n",
    )
    all_functions = _classify_all(tmp_path)
    # Sanity: the same-module one-hop delegate is reader-True BEFORE the
    # translator pass runs (proves the translator pass is additive, not doing
    # the same-module closure's job over again).
    same_module_readers = {(c.module, c.qualname) for c in all_functions if c.is_reader}
    assert (
        "src/specify_cli/review/synthetic_artifacts.py",
        "one_hop_review_cycle_reader",
    ) in same_module_readers

    final = _promote_cross_module_translators(all_functions)
    readers = {(c.module, c.qualname) for c in final if c.is_reader}
    assert (
        "src/specify_cli/post_merge/synthetic_translator.py",
        "find_review_cycle_read_failures",
    ) in readers


def test_translator_pass_does_not_promote_a_plain_orchestrator(tmp_path: Path) -> None:
    """F4 negative control: a function that calls a reader-classified function
    WITHOUT wrapping it in ``try/except (ValueError, OSError)`` -- an ordinary
    orchestrator, not a fail-closed translator -- must NOT be promoted. This
    is what keeps the narrow translator pass from reopening F1's directory-
    anchored over-reach through a broad call-graph closure."""
    _write_module(
        tmp_path,
        "src/specify_cli/review/synthetic_artifacts2.py",
        "from pathlib import Path\n\n\n"
        "from specify_cli.review.artifacts import ReviewCycleArtifact\n\n\n"
        "def direct_review_cycle_reader2(path: Path) -> str:\n"
        "    return ReviewCycleArtifact.from_file(path).verdict\n",
    )
    _write_module(
        tmp_path,
        "src/specify_cli/post_merge/synthetic_orchestrator.py",
        "from pathlib import Path\n\n\n"
        "from specify_cli.review.synthetic_artifacts2 import direct_review_cycle_reader2\n\n\n"
        "def orchestrate_without_translating(path: Path) -> str:\n"
        "    return direct_review_cycle_reader2(path)\n",
    )
    all_functions = _classify_all(tmp_path)
    final = _promote_cross_module_translators(all_functions)
    readers = {(c.module, c.qualname) for c in final if c.is_reader}
    assert (
        "src/specify_cli/post_merge/synthetic_orchestrator.py",
        "orchestrate_without_translating",
    ) not in readers


def test_exclusion_mechanism_removes_a_synthetic_pre_review_gate_lookalike(tmp_path: Path) -> None:
    """T004 forward-guard proof: today's REAL ``pre_review_gate.py`` /
    ``verdict_aggregation.py`` contain no ``review-cycle``/``review_cycle``
    token at all (verified directly), so the exclusion is currently vacuous
    against the live tree -- see module docstring. This proves the exclusion
    MECHANISM itself still works: a synthetic file at the exact excluded
    relpath, carrying review-cycle content that would otherwise be swept in,
    is removed from the candidate set by name."""
    _write_module(
        tmp_path,
        "src/specify_cli/review/pre_review_gate.py",
        "def f():\n    return 'review-cycle-1.md'\n",
    )
    candidate_relpaths = {p.relative_to(tmp_path).as_posix() for p in _candidate_modules(tmp_path)}
    assert "src/specify_cli/review/pre_review_gate.py" not in candidate_relpaths


def test_function_exclusion_removes_a_synthetic_lookalike_at_the_excluded_qualname(tmp_path: Path) -> None:
    """T011 forward-guard proof (function-level companion to
    ``test_exclusion_mechanism_removes_a_synthetic_pre_review_gate_lookalike``
    above): a synthetic module at the EXACT excluded relpath, containing a
    function with the EXACT excluded name and an unmistakable writer shape
    (constructs ``ReviewResult`` directly), is still removed by
    ``_classify_module`` -- proving the mechanism keys on ``(relpath,
    qualname)`` identity, not merely "the real file happens to already work
    out this way."""
    relpath = "src/specify_cli/migration/verdict_provenance_backfill.py"
    _write_module(
        tmp_path,
        relpath,
        "from specify_cli.status.models import ReviewResult\n\n\n"
        "def _backfill_event_for_wp(reviewer: str, verdict: str, reference: str) -> ReviewResult:\n"
        "    return ReviewResult(reviewer=reviewer, verdict=verdict, reference=reference)\n",
    )
    classified = {c.qualname for c in _classify_module(tmp_path / relpath, tmp_path)}
    assert "_backfill_event_for_wp" not in classified


def test_function_exclusion_is_scoped_to_the_named_module_not_the_bare_name(tmp_path: Path) -> None:
    """T011 precision proof: a function with the SAME bare name as an
    excluded ``(relpath, qualname)`` pair, but living in a DIFFERENT module,
    is NOT excluded -- the mechanism keys on the full pair, never a bare-name
    allowlist that could accidentally swallow an unrelated function sharing
    the name."""
    relpath = "src/specify_cli/review/synthetic_same_name_writer.py"
    _write_module(
        tmp_path,
        relpath,
        "from specify_cli.status.models import ReviewResult\n\n\n"
        "def _backfill_event_for_wp(reviewer: str, verdict: str, reference: str) -> ReviewResult:\n"
        "    return ReviewResult(reviewer=reviewer, verdict=verdict, reference=reference)\n",
    )
    classified = {c.qualname for c in _classify_module(tmp_path / relpath, tmp_path)}
    assert "_backfill_event_for_wp" in classified


def test_forward_declared_vocab_module_is_excluded() -> None:
    """WP01 forward-declared ``status/verdict_vocab.py`` as an
    ``_EXCLUDED_MODULE_REASONS`` entry BEFORE WP04 created it -- and asserted
    it was still absent, a designed trip-wire so that when the module landed
    a reviewer would be forced to re-verify the exclusion against the REAL
    code rather than trusting a vacuous forward guard.

    Post-merge (verdict-seam-write-unification-01KZ9Q35 consolidation) that
    trip-wire has fired: the module now EXISTS (WP04 landed). The exclusion
    was re-verified against the live code and HOLDS: ``verdict_vocab.py`` is a
    pure vocabulary map (string -> string, no ``read_text``/``write_text``/
    ``from_file``/YAML load/record ctor), so it never reads, writes, or
    resolves a review-cycle verdict record -- correctly excluded, and it
    contributes zero derived rows.

    (WP01 originally forward-declared a SIBLING entry here for
    ``migration/verdict_provenance_backfill.py`` too; WP03 (#3236) retired
    that module-level entry in favour of the function-level mechanism -- see
    ``test_backfill_module_write_helper_is_function_excluded_while_readers_
    surface`` below, which is this test's replacement for that module.)"""
    root = _repo_root()
    derived = _derive_census(root)
    relpath = "src/specify_cli/status/verdict_vocab.py"
    assert relpath in _EXCLUDED_MODULE_REASONS
    assert _EXCLUDED_MODULE_REASONS[relpath].strip(), f"{relpath} exclusion must carry a recorded reason"
    assert (root / relpath).exists(), (
        f"{relpath} must exist now that WP04 has landed -- if it does not, the "
        "module set has drifted and this exclusion is stale again"
    )
    # Non-vacuity: an excluded module never contributes a derived row in any
    # category (the wholesale skip is what actually suppresses it).
    for category, pairs in derived.items():
        assert relpath not in {module for module, _ in pairs}, (
            f"{relpath} is excluded yet appears in the derived {category} set "
            "-- the exclusion stopped taking effect"
        )


def test_backfill_module_write_helper_is_function_excluded_while_readers_surface() -> None:
    """T014 flip (#3236): ``migration/verdict_provenance_backfill.py`` is NO
    LONGER a module-level exclusion -- it must now surface its genuine
    reader/resolver chain while ONLY its disclosed write-side helper
    (``_backfill_event_for_wp``) stays suppressed, via the T011 function-level
    mechanism.

    This replaces the old wholesale-exclusion assertion (module absent from
    every derived category) with the function-level shape:

    * the module is NOT in ``_EXCLUDED_MODULE_REASONS`` any more (T012);
    * ``_backfill_event_for_wp`` IS in ``_EXCLUDED_FUNCTIONS`` with a recorded
      reason, and contributes zero rows in every category (T011's own
      non-vacuity proof lives in ``test_function_exclusion_removes_a_
      synthetic_lookalike_at_the_excluded_qualname`` below -- this test only
      checks the REAL module's outcome);
    * the #3236 disclosed reader, ``_legacy_frontmatter_verdict``, and its
      same-module one-hop callers DO appear in the derived reader set --
      the exact row this WP exists to stop masking;
    * ``backfill_verdict_provenance`` -- writer-only before this WP purely
      via one-hop closure through the now-excluded write helper -- no longer
      carries a writer row, proving the exclusion's closure-blocking effect
      (not just the excluded function's own row) actually took hold."""
    root = _repo_root()
    relpath = "src/specify_cli/migration/verdict_provenance_backfill.py"
    assert relpath not in _EXCLUDED_MODULE_REASONS, (
        f"{relpath} must no longer be module-excluded -- T012 narrows this to "
        "a function-level exclusion"
    )
    excluded_key = (relpath, "_backfill_event_for_wp")
    assert excluded_key in _EXCLUDED_FUNCTIONS
    assert _EXCLUDED_FUNCTIONS[excluded_key].strip(), "the function exclusion must carry a recorded reason"

    derived = _derive_census(root)
    for category, pairs in derived.items():
        assert (relpath, "_backfill_event_for_wp") not in pairs, (
            f"_backfill_event_for_wp is function-excluded yet appears in the "
            f"derived {category} set -- the exclusion stopped taking effect"
        )
    assert (relpath, "_legacy_frontmatter_verdict") in derived["reader"], (
        "the #3236 disclosed reader must surface now that the module is no "
        "longer wholesale-excluded"
    )
    assert (relpath, "terminal_review_artifact") in derived["reader"]
    assert (relpath, "stranded_verdict_findings") in derived["reader"]
    assert (relpath, "backfill_verdict_provenance") in derived["reader"]
    assert (relpath, "_review_cycle_candidate_dirs") in derived["resolver"]
    assert (relpath, "terminal_review_artifact") in derived["resolver"]
    assert (relpath, "backfill_verdict_provenance") not in derived["writer"], (
        "backfill_verdict_provenance's ONLY writer signal came from calling "
        "the now-excluded _backfill_event_for_wp via the same-module one-hop "
        "closure -- it must not carry a writer row post-exclusion"
    )


def test_malformed_retire_row_with_no_retiring_fr_is_a_hard_failure() -> None:
    """T002 non-vacuity: ``status: retire`` with no ``retiring_fr`` fails.

    Neither this test nor ``test_retire_row_with_typo_fr_id_fails_loudly``
    below encoded the retired Status-Open behaviour directly (both fail at
    the "does retiring_fr even exist in spec.md's FR table" leg, before the
    WP-claim leg is ever reached) -- so WP08's amendment only needed the
    ``claimed_frs`` parameter threaded through, no logic change here."""
    bad_row = _CensusRow(category="resolver", module="src/x.py", function="f", status="retire", retiring_fr=None)
    errors = _validate_retire_rows([bad_row], {"FR-008": "Done"}, {"FR-008"})
    assert errors, "a retire row with no retiring_fr must fail validation"


def test_retire_row_with_typo_fr_id_fails_loudly() -> None:
    """T002 edge case: FR-08 (typo of FR-008) must not silently pass by
    vacuous truth against a table that simply lacks that key."""
    bad_row = _CensusRow(category="resolver", module="src/x.py", function="f", status="retire", retiring_fr="FR-08")
    errors = _validate_retire_rows([bad_row], {"FR-008": "Done"}, {"FR-008"})
    assert errors, "an FR-id typo must fail loudly, not pass by vacuous truth"


def test_retire_row_naming_a_wp_claimed_fr_passes() -> None:
    """T002 amendment (WP08 operator ruling) positive control: a retire row
    naming an FR CLAIMED by some WP's ``requirement_refs`` passes -- even when
    spec.md's (unmaintained) Status column still says ``Open``, proving the
    rule no longer keys on that column at all (this replaces the retired
    ``test_retire_row_naming_a_landed_fr_passes``, which asserted the OLD
    Status-Done-based pass condition; see the module-level rationale above
    :func:`_validate_retire_rows`)."""
    good_row = _CensusRow(category="resolver", module="src/x.py", function="f", status="retire", retiring_fr="FR-008")
    assert _validate_retire_rows([good_row], {"FR-008": "Open"}, {"FR-008"}) == []


def test_retire_row_naming_an_unclaimed_fr_fails() -> None:
    """T002 amendment (WP08 operator ruling) negative control: a retire row
    naming a REAL FR that exists in spec.md's table but is claimed by NO WP's
    ``requirement_refs`` fails -- the self-set-to-zero dodge the rule exists
    to block, regardless of the FR's (unmaintained) Status column (this
    replaces the retired ``test_retire_row_pointing_at_an_unstarted_fr_fails``,
    which asserted the OLD Status-Open-based failure condition)."""
    bad_row = _CensusRow(category="resolver", module="src/x.py", function="f", status="retire", retiring_fr="FR-008")
    errors = _validate_retire_rows([bad_row], {"FR-008": "Done"}, {"FR-999"})
    assert errors, "retiring against an FR nobody claims in requirement_refs must fail"


def test_retire_row_naming_a_nonexistent_fr_still_fails() -> None:
    """T002 amendment non-vacuity: a retire row naming an FR id that does not
    exist in spec.md's FR table AT ALL still fails, even when that same
    (fictitious) id happens to appear in ``claimed_frs`` -- the existence leg
    (a) is independent of, and checked before, the WP-claim leg (b)."""
    bad_row = _CensusRow(category="resolver", module="src/x.py", function="f", status="retire", retiring_fr="FR-999")
    errors = _validate_retire_rows([bad_row], {"FR-008": "Done"}, {"FR-999"})
    assert errors, "retiring against a nonexistent FR id must fail regardless of claimed_frs"


def test_fixture_is_the_literal_fixture_the_check_consults() -> None:
    """T005 non-vacuity: prove ``verdict_seam_census.yaml`` (the WP16-folded
    document) is the LITERAL fixture consulted, not a document a hardcoded
    Python constant merely happens to agree with today. Removing every writer
    row from a loaded copy
    changes the diff outcome from clean to "growth == the whole live writer
    set" -- editing the file changes the pass/fail result."""
    root = _repo_root()
    derived_writers = _derive_census(root)["writer"]
    expected_writers = _active_pairs(_CENSUS_ROWS, "writer")
    growth, shrinkage = _diff_sets(derived_writers, expected_writers)
    assert not growth and not shrinkage, "sanity: today's real fixture must already match the derivation"

    mutated_rows = [row for row in _CENSUS_ROWS if row.category != "writer"]
    mutated_expected = _active_pairs(mutated_rows, "writer")
    mutated_growth, _mutated_shrinkage = _diff_sets(derived_writers, mutated_expected)
    assert mutated_growth == derived_writers, (
        "removing every writer row from the (in-memory) fixture must reintroduce "
        "the whole live writer set as 'growth' -- proves the file's content, not "
        "a separate constant, drives the outcome"
    )
