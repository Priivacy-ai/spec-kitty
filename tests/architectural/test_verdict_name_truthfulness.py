"""SC-007 / FR-017 -- the test-name-truthfulness audit (WP16, T070).

User Story 5 (spec.md) requires that no test in the *affected suites* has a
name or contract key contradicting its own assertions, and that the flagship
end-to-end test asserts the ordinary (non-forced) path. This module builds
that audit as a committed, re-runnable check -- not a one-time manual pass
with no artifact -- following the census check's own precedent
(``test_verdict_seam_census.py``: fail when a new untracked member appears).

Denominator (spec.md's binding rule, restated so a reviewer can re-derive it
without opening spec.md): the union of two SEPARATELY counted sets, never the
full affected-suites collection (2820 tests -- NFR-001's denominator, a
different and much larger thing; a union anywhere near that size here would
mean the enumeration collapsed to "the whole affected suites" instead of
correctly deriving the smaller SC-007 union, and would be a bug in this
module, not confirmation).

* **|touched|** -- every test function in a ``tests/*`` file this mission's
  cumulative diff touches, computed via
  :func:`specify_cli.core.vcs.git.merge_base_changed_files` against
  :data:`_MISSION_BASE_REF` (the canonical merge-base/diff surface this repo
  already ships -- not a hand-rolled ``subprocess`` call; see
  ``tests/specify_cli/core/vcs/test_merge_base_diff_surface.py`` for that
  surface's own coverage). If ``_MISSION_BASE_REF`` no longer resolves (e.g.
  the branch is deleted well after this mission merges), the touched-set
  tests skip with an explicit reason rather than silently reporting zero.
* **|keyword-matched|** -- every test function under spec.md's Definitions
  section "Affected suites" paths whose bare name matches
  :data:`_CONCEPT_KEYWORD_RE` (guard / verdict / durability / override /
  provenance).

**Honest correction of this WP's own task prompt**: the prompt describes the
second leg as matching a test's "name or ``requirement_refs`` pytest marker".
No such marker exists anywhere in this codebase -- confirmed directly:
``pytest.ini``'s registered ``markers`` list carries no ``requirement_refs``
entry, and a repo-wide grep for ``mark.requirement_refs`` /
``@pytest.mark.requirement_refs`` returns zero hits. ``requirement_refs`` is
a WP-frontmatter/manifest field (``kitty-specs/*/tasks/WP*.md``), never a
pytest marker applied to a test function. This module therefore matches on
test NAME only for the keyword leg; it does not invent a marker mechanism
that would need registering elsewhere just to make the prompt's phrasing
literally true.

Measured at WP16 implementation time (this mission's diff so far, against
``pr/review-verdict-write-integrity-01KZ1CGF``): |touched| = 287,
|keyword-matched| = 100, union = 348 (39 overlap). All three are far below
the 2820-test NFR-001 collapse threshold, as they must be.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Iterator
from pathlib import Path

import pytest

from specify_cli.core.vcs.git import git_merge_base, merge_base_changed_files

pytestmark = pytest.mark.architectural

# ---------------------------------------------------------------------------
# Paths / constants
# ---------------------------------------------------------------------------

#: The mission's own planning/merge-target base branch (WP16's task
#: frontmatter: ``planning_base_branch`` / ``merge_target_branch``). Diffing
#: HEAD against this ref's merge-base is this mission's OWN cumulative diff,
#: not the repo's all-time history.
_MISSION_BASE_REF = "pr/review-verdict-write-integrity-01KZ1CGF"

#: spec.md's Definitions section, "Affected suites" -- copied verbatim
#: (load-bearing in NFR-001 and SC-007 per that section's own header).
_AFFECTED_SUITE_PATHS: tuple[str, ...] = (
    "tests/review",
    "tests/status",
    # Relocated out of tests/regression/ in the 2026-08 landing fold once
    # #2646 closed and this suite went permanently green (same file, same
    # tests) -- kept in lockstep with mission_exit_baseline.txt's own
    # targeted path update.
    "tests/integration/test_2646_stale_verdict_closes_via_fr001.py",
    "tests/integration/test_review_cycle_rejection_only.py",
    "tests/integration/test_ac5_hash_guard.py",
    "tests/integration/test_wp_file_hash_stability.py",
    "tests/post_merge/test_review_artifact_consistency.py",
    "tests/specify_cli/cli/commands/agent",
)

#: SC-007's five concept keywords, matched case-insensitively against a bare
#: test function name.
_CONCEPT_KEYWORD_RE = re.compile(r"guard|verdict|durab|override|provenance", re.IGNORECASE)

#: The four name-shapes User Story 5 / this WP's task prompt name explicitly
#: as making a specific refusal/rejection claim the body must then support.
#: Deliberately narrow (literal underscore-delimited shapes) so a broadly-named
#: test using "reject"/"never" as a domain NOUN elsewhere in its name (e.g.
#: ``test_create_rejected_review_cycle_...``, ``rejected`` describing the
#: fixture's state, not this test's own claim) is not swept in -- see the
#: module docstring's Edge Cases note in the WP's own task prompt.
_REFUSAL_NAME_RE = re.compile(
    r"_rejects_|_refuses_|_blocked_|_never_|^rejects_|^refuses_|^blocked_|^never_",
    re.IGNORECASE,
)

#: A count anywhere near this is itself a bug in the enumeration (it would
#: mean the union collapsed toward NFR-001's full 2820-test affected-suites
#: collection instead of the smaller touched-union-keyword-matched set).
_NFR001_COLLAPSE_GUARD_CEILING = 1000


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "src" / "specify_cli").is_dir():
            return parent
    raise AssertionError("could not locate repo root from test file")


# ---------------------------------------------------------------------------
# AST: enumerate every ``test_*`` function/method in a file.
# ---------------------------------------------------------------------------


def _iter_test_functions(path: Path) -> Iterator[tuple[str, ast.FunctionDef | ast.AsyncFunctionDef]]:
    """Yield ``(qualname, node)`` for every ``test_*`` function or method in
    *path* -- module-level or nested inside a (possibly nested) class, mirroring
    pytest's own collection shape (``Class::test_method``)."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return

    def walk(node: ast.AST, enclosing_class: str | None) -> Iterator[tuple[str, ast.FunctionDef | ast.AsyncFunctionDef]]:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                yield from walk(child, child.name)
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if child.name.startswith("test_"):
                    qualname = f"{enclosing_class}::{child.name}" if enclosing_class else child.name
                    yield qualname, child
                yield from walk(child, enclosing_class)

    yield from walk(tree, None)


def _resolve_suite_files(root: Path, entry: str) -> list[Path]:
    """A suite path entry is either a directory (walked for ``test_*.py``) or
    a single file (spec.md's list mixes both shapes)."""
    target = root / entry
    if target.is_dir():
        return sorted(target.rglob("test_*.py"))
    if target.is_file():
        return [target]
    return []


# ---------------------------------------------------------------------------
# |touched| -- every test in a tests/* file this mission's diff touches.
# ---------------------------------------------------------------------------


def _touched_test_node_ids(root: Path) -> frozenset[str] | None:
    """``None`` when the mission base ref no longer resolves (no merge-base) --
    a distinguishable "cannot determine" outcome, not a silent empty set."""
    if git_merge_base(root, "HEAD", _MISSION_BASE_REF) is None:
        return None
    touched = merge_base_changed_files(root, _MISSION_BASE_REF, pathspec="tests/*")
    node_ids: set[str] = set()
    for relpath in touched:
        if not relpath.endswith(".py"):
            continue
        path = root / relpath
        if not path.is_file():
            continue
        for qualname, _node in _iter_test_functions(path):
            node_ids.add(f"{relpath}::{qualname}")
    return frozenset(node_ids)


# ---------------------------------------------------------------------------
# |keyword-matched| -- every test in the affected suites whose NAME (no
# ``requirement_refs`` marker exists -- see module docstring) hits a concept.
# ---------------------------------------------------------------------------


def _keyword_matched_nodes(root: Path) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    matched: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
    for entry in _AFFECTED_SUITE_PATHS:
        for path in _resolve_suite_files(root, entry):
            relpath = path.relative_to(root).as_posix()
            for qualname, node in _iter_test_functions(path):
                if _CONCEPT_KEYWORD_RE.search(qualname):
                    matched[f"{relpath}::{qualname}"] = node
    return matched


def _all_candidate_nodes(root: Path) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    """Every node reachable from EITHER leg, keyed by node id -- used by the
    name/assertion mismatch scan below, which needs the actual AST node, not
    just its id."""
    nodes: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = dict(_keyword_matched_nodes(root))
    touched = merge_base_changed_files(root, _MISSION_BASE_REF, pathspec="tests/*")
    for relpath in touched:
        if not relpath.endswith(".py"):
            continue
        path = root / relpath
        if not path.is_file():
            continue
        for qualname, node in _iter_test_functions(path):
            nodes.setdefault(f"{relpath}::{qualname}", node)
    return nodes


# ---------------------------------------------------------------------------
# Name/assertion mismatch scan: a refusal-shaped name with no visible
# failure-assertion signal in its body.
# ---------------------------------------------------------------------------


def _is_empty_container_literal(node: ast.AST) -> bool:
    return isinstance(node, (ast.List, ast.Tuple, ast.Set)) and len(node.elts) == 0


def _isinstance_call_names_a_failure_class(call: ast.Call) -> bool:
    if not (isinstance(call.func, ast.Name) and call.func.id == "isinstance" and len(call.args) == 2):
        return False
    cls_arg = call.args[1]
    cls_name = cls_arg.attr if isinstance(cls_arg, ast.Attribute) else (cls_arg.id if isinstance(cls_arg, ast.Name) else "")
    return bool(re.search(r"refuse|reject|block|error|invalid|fail", cls_name, re.IGNORECASE))


def _assert_test_proves_failure(test_expr: ast.expr) -> bool:
    for sub in ast.walk(test_expr):
        if isinstance(sub, ast.Constant) and sub.value is False:
            return True
        if isinstance(sub, ast.UnaryOp) and isinstance(sub.op, ast.Not):
            return True
        if isinstance(sub, ast.Compare):
            for op, comparator in zip(sub.ops, sub.comparators, strict=True):
                if isinstance(op, (ast.NotEq, ast.NotIn)):
                    return True
                if isinstance(op, ast.Eq) and (
                    _is_empty_container_literal(comparator)
                    or (isinstance(comparator, ast.Constant) and isinstance(comparator.value, int) and comparator.value != 0)
                ):
                    return True
    return False


def _has_failure_assertion(node: ast.AST) -> bool:
    """True if *node*'s body contains a ``pytest.raises``/``.fail(`` call, an
    ``isinstance(..., <FailureShapedClass>)`` check, or an ``assert`` whose
    test proves a negative/refusal outcome (``is False``, ``not ...``,
    ``!=``, ``not in``, or ``==`` to an empty container or a non-zero int --
    e.g. an exit code). Deliberately broader than a literal
    ``pytest.raises``-only check -- WP16's own audit found five
    mechanically-flagged candidates that were true negatives once this
    broader shape was recognized (an ``isinstance(x, RefuseExit1)`` check, an
    ``exit_code == 1`` comparison, a ``blocking_verdicts == ()`` comparison,
    and a ``"review_result" not in snapshot...`` membership test); see this
    WP's Activity Log for the full triage."""
    for child in ast.walk(node):
        if isinstance(child, ast.With):
            for item in child.items:
                call = item.context_expr
                if isinstance(call, ast.Call):
                    func = call.func
                    if (isinstance(func, ast.Attribute) and func.attr == "raises") or (
                        isinstance(func, ast.Name) and func.id == "raises"
                    ):
                        return True
        if isinstance(child, ast.Call):
            func = child.func
            if isinstance(func, ast.Attribute) and func.attr in ("raises", "fail"):
                return True
            if _isinstance_call_names_a_failure_class(child):
                return True
        if isinstance(child, ast.Assert) and _assert_test_proves_failure(child.test):
            return True
    return False


#: Reviewed-and-confirmed TRUE NEGATIVES: a candidate this module's mechanical
#: pattern flags, individually inspected and confirmed to be a genuinely
#: truthful name -- not a defect, and not filed as a cross-WP finding either.
#: Each entry carries the reason inline so a future reviewer does not have to
#: re-derive it. Growing this set silently (without a reason) would be
#: exactly the "quietly narrow the denominator" risk this WP's task prompt
#: names -- so an entry with no citation below is a bug in this file, not a
#: legitimate use of the allowlist.
_REVIEWED_TRUE_NEGATIVES: dict[str, str] = {
    "tests/specify_cli/cli/commands/test_review_cycle_reconcile_doctor.py::test_both_stranded_classes_are_never_conflated_across_missions": (
        "asserts `{f.stranded_class for f in deleted_report.findings} == "
        "{rcr._DELETED_COORD_BRANCH_CLASS}` and the symmetric case for the "
        "live report -- a genuine 'never conflated' proof (each mission's "
        "findings resolve to a disjoint, single-class set), just not caught "
        "by this module's mechanical shape because the comparator is a "
        "non-empty set literal, not False/empty/isinstance-of-a-failure-class."
    ),
}

#: Genuine name/assertion mismatches this audit FOUND but does not fix here
#: (WP16 does not own the affected file) -- filed as cross-WP findings with
#: the exact test node id, per this WP's own Definition of Done. A future run
#: of this check treats these as already-known (not a fresh failure); a NEW,
#: undisclosed mismatch anywhere else in the candidate set still fails the
#: check below.
_FILED_CROSS_WP_FINDINGS: dict[str, str] = {
    "tests/review/test_reader_polarity_merge_gate_regression.py::test_arbiter_override_reader_refuses_a_malformed_event_sourced_slot": (
        "FILED against WP14 (owns this file). The name claims 'refuses' "
        "(a fail-closed/raise polarity), but the test's own docstring and "
        "body assert the OPPOSITE polarity: a review snapshot slot missing a "
        "required ReviewOverride field is 'silently skipped -- never an "
        "uncaught crash' by get_arbiter_overrides_for_wp's narrow "
        "except (KeyError, TypeError, ValueError), and the assertion is "
        "`result == []` (a skip-shaped empty result, not a raised "
        "exception). WP14's own task file marks the arbiter reader "
        "safety-relevant and states no safety-relevant reader may be "
        "`skip` -- so this is either a truthfulness defect in the test's "
        "name (rename to something like "
        "`test_arbiter_override_reader_skips_a_malformed_event_sourced_slot`) "
        "or, if WP14 intended this narrow internal-invariant case to be an "
        "exception to its own skip/refuse rule, that reasoning is not "
        "recorded anywhere the name reflects. WP16 does not own "
        "`tests/review/test_reader_polarity_merge_gate_regression.py` or "
        "`src/specify_cli/review/arbiter.py`, so this is reported, not fixed, "
        "here."
    ),
}


def test_denominator_counts_are_recorded_and_not_the_nfr001_collapse() -> None:
    """SC-007's denominator, re-derived: |touched| and |keyword-matched| are
    recorded as two SEPARATE counts (never summed into one figure), and their
    union is asserted well below the 2820-test NFR-001 collapse threshold --
    a union anywhere near that size would mean this module's enumeration
    rule regressed into sweeping in the whole affected-suites collection."""
    root = _repo_root()
    touched = _touched_test_node_ids(root)
    if touched is None:
        pytest.skip(f"{_MISSION_BASE_REF} no longer resolves a merge-base with HEAD")
    keyword_matched = frozenset(_keyword_matched_nodes(root))

    assert touched, "expected at least one touched test in this mission's cumulative diff"
    assert keyword_matched, "expected at least one keyword-matched test in the affected suites"

    union = touched | keyword_matched
    assert len(union) < _NFR001_COLLAPSE_GUARD_CEILING, (
        f"SC-007's touched-union-keyword-matched denominator measured "
        f"{len(union)}, at or above the {_NFR001_COLLAPSE_GUARD_CEILING} "
        "collapse-guard ceiling -- this is NOT confirmation of a large "
        "denominator, it is a sign the enumeration rule regressed into "
        "sweeping in NFR-001's full ~2820-test affected-suites collection "
        "instead of the smaller SC-007 union; fix the enumeration before "
        "trusting the audit below."
    )


def test_refusal_named_tests_have_a_failure_assertion_or_are_disclosed() -> None:
    """SC-007's core scan: every test in the touched-union-keyword-matched
    denominator whose name makes a specific refusal/rejection claim
    (``_rejects_``/``_refuses_``/``_blocked_``/``_never_``) must have a body
    that actually proves a failure -- unless it is a reviewed true negative or
    an already-filed cross-WP finding, both named explicitly above with a
    reason. A NEW, undisclosed mismatch anywhere in the candidate set fails
    this test."""
    root = _repo_root()
    if git_merge_base(root, "HEAD", _MISSION_BASE_REF) is None:
        pytest.skip(f"{_MISSION_BASE_REF} no longer resolves a merge-base with HEAD")

    candidates = _all_candidate_nodes(root)
    flagged = {
        node_id
        for node_id, node in candidates.items()
        if _REFUSAL_NAME_RE.search(node_id.rsplit("::", 1)[-1]) and not _has_failure_assertion(node)
    }

    disclosed = frozenset(_REVIEWED_TRUE_NEGATIVES) | frozenset(_FILED_CROSS_WP_FINDINGS)
    undisclosed = flagged - disclosed
    assert not undisclosed, (
        "new, undisclosed name/assertion mismatch(es) found (a refusal-shaped "
        f"test name with no failure-proving assertion): {sorted(undisclosed)} "
        "-- fix the test's name or assertions, or add a reasoned entry to "
        "_REVIEWED_TRUE_NEGATIVES / _FILED_CROSS_WP_FINDINGS above."
    )

    # Non-vacuity: the disclosed sets must actually still be reachable from
    # today's candidate set -- an entry that silently stopped matching (e.g.
    # the test was renamed or deleted) should be pruned, not left stale.
    stale = disclosed - set(candidates)
    assert not stale, f"disclosed allowlist entries no longer exist in the candidate set: {sorted(stale)}"


def test_wp10_flagship_rename_precedent_is_not_re_flagged() -> None:
    """T070's Objective explicitly names this precedent: WP10 already renamed
    ``test_new_cycle_body_never_duplicates_a_prior_cycle_file`` (which matched
    the exact ``_never_`` refusal shape with no ``pytest.raises`` -- the
    predecessor mission's flagship offender) to
    ``test_duplicate_prose_in_an_ordinary_feedback_file_is_admitted``. Confirm
    the fix landed (old name gone, new name present) and that the new name no
    longer matches the refusal pattern at all -- it is not merely passing this
    module's scan by accident."""
    root = _repo_root()
    path = root / "tests/review/test_cycle.py"
    names = {qualname for qualname, _node in _iter_test_functions(path)}
    assert "test_new_cycle_body_never_duplicates_a_prior_cycle_file" not in names, (
        "the stale, refusal-named test must not have been silently reintroduced"
    )
    assert "test_duplicate_prose_in_an_ordinary_feedback_file_is_admitted" in names, (
        "WP10's renamed replacement must exist"
    )
    assert not _REFUSAL_NAME_RE.search("test_duplicate_prose_in_an_ordinary_feedback_file_is_admitted")


def test_flagship_end_to_end_test_asserts_the_non_forced_path() -> None:
    """User Story 5 Acceptance Scenario 2: "the flagship end-to-end test
    asserts the non-forced path." The flagship end-to-end test for this
    mission's core defect (FR-001/#2996) is
    ``test_approving_a_rejected_wp_writes_no_verdict_artifact`` in
    ``tests/integration/test_review_cycle_rejection_only.py`` -- its own
    docstring calls it "this mission's most direct evidence that the fix
    actually closes the gap at the real CLI boundary", driving a full
    reject -> rework -> resubmit -> approve lifecycle through the real CLI.
    Confirm mechanically that its CLI invocation never passes
    ``--skip-review-artifact-check`` -- the ONE flag that would make this the
    FORCED/override path SC-002 distinguishes from the ordinary one. (It does
    pass ``--force``, but only to bypass two guards unrelated to the fix under
    test, per its own docstring -- ``--force`` is not
    ``--skip-review-artifact-check`` and this assertion does not claim it is.)

    Honest finding, not fixed here (WP16 does not own this file): the test's
    OWN NAME contradicts its assertions -- it is named
    "writes_no_verdict_artifact" but its body asserts the opposite
    (``ReviewCycleArtifact.latest(...)`` is not None, ``latest.verdict ==
    "approved"``) and its docstring says the fix means an ordinary approve
    "now DOES record a fresh verdict: approved review-cycle artifact." This is
    the single highest-value finding of this WP's audit and is filed as a
    cross-WP finding in this WP's Activity Log with the exact node id,
    per this WP's Definition of Done (WP16 does not own
    ``tests/integration/test_review_cycle_rejection_only.py``)."""
    root = _repo_root()
    path = root / "tests/integration/test_review_cycle_rejection_only.py"
    flagship_name = "test_approving_a_rejected_wp_writes_no_verdict_artifact"
    node = next((n for qualname, n in _iter_test_functions(path) if qualname == flagship_name), None)
    assert node is not None, f"expected to find {flagship_name!r} in {path}"

    literal_strings = {
        subnode.value
        for subnode in ast.walk(node)
        if isinstance(subnode, ast.Constant) and isinstance(subnode.value, str)
    }
    assert "--skip-review-artifact-check" not in literal_strings, (
        "the flagship end-to-end test must exercise the NON-FORCED path -- "
        "it must never pass --skip-review-artifact-check"
    )
