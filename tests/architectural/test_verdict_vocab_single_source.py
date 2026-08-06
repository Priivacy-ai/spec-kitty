"""FR-005 -- the vocabulary-bridge single-source architectural guard.

``status/verdict_vocab.py`` is the one canonical surface for the artifact
<-> event verdict equivalence (``rejected`` <-> ``changes_requested``,
D-PLAN-14's emission scope, the full four-value artifact domain). Before this
WP the equivalence was re-inlined independently in seven modules (paula
finding). This file is the check that keeps it that way:

- **Negative check** (:func:`test_no_module_other_than_bridge_spells_the_inline_equivalence`):
  no module other than the bridge itself spells the co-occurring
  ``"rejected"``/``"changes_requested"`` string-literal equivalence -- an
  AST-derived, module-level scan (:func:`_co_occurring_equivalence_modules`),
  not a same-line grep, so splitting the two literals across lines/functions
  cannot dodge it (squad #5's evasion concern).
- **Positive check** (:func:`test_swept_module_imports_and_calls_verdict_vocab`):
  each of the 5 WP04-owned sweep sites must import the bridge module AND call
  one of its attributes somewhere in its own AST. This defeats the
  complementary evasion -- a module that simply stops spelling the literals
  (e.g. by hardcoding an equivalent behaviour some other way) without ever
  routing through the canonical surface would pass the negative check alone
  but fails this one.

  Review cycle 1 (reviewer-renata) rejected an earlier version of this file
  that ALSO listed ``status/models.py`` and ``status/reducer.py`` here: at
  base, neither module co-occurs the equivalence pair in CODE (only in
  comments/a docstring), so they were never genuine sweep sites -- forcing
  them onto the positive-check list produced two dead public symbols
  (a decorative ``EVENT_VERDICTS`` re-export and an uncalled
  ``ReviewResultLookup.is_recognized_verdict`` property) whose only purpose
  was passing this check. The negative check already covers both modules for
  free (neither co-occurs the literal pair, so both trivially pass it); this
  file no longer lists them as positive-check sites. See
  ``reviewer-feedback-wp04-c1.md`` for the full finding.

A **named allowlist** (:data:`_UNSWEPT_ALLOWLIST`) originally exempted two
WP05-owned sites (``review/cycle.py:794``,
``post_merge/review_artifact_consistency.py``) from both checks -- WP04
shipped it GREEN with exactly those two entries (D-PLAN IC-02b:
guard-lands-last; WP04 does not touch either module). WP05
(verdict-seam-write-unification-01KZ9Q35, squad #15 BLOCKING acceptance
check) swept both sites onto the bridge and EMPTIED this allowlist --
:func:`test_allowlist_is_empty_after_wp05` asserts this programmatically.

This file ALSO carries the bridge's own unit tests (T016: totality over all
four inbound values + the render-only inverse) and the D-PLAN-14 negative
test (T019: an arbiter override must never synthesize an approved
``review_result`` event).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from specify_cli.status import verdict_vocab
from specify_cli.status.models import ReviewOverride, WPInnerStateDelta
from specify_cli.status.reducer import _apply_annotation_delta

#: The bridge itself -- excluded from both the negative and positive scans
#: (it is the canonical surface, not a sweep site).
_BRIDGE_RELPATH = "src/specify_cli/status/verdict_vocab.py"

#: WP05 (verdict-seam-write-unification-01KZ9Q35, squad #15 BLOCKING
#: acceptance check) EMPTIED this allowlist: both former entries
#: (``review/cycle.py:794`` and ``review_artifact_consistency.py``) now
#: import and call ``status.verdict_vocab`` instead of re-inlining the
#: ``rejected``/``changes_requested`` equivalence. This is a named,
#: SHRUNK-TO-EMPTY allowlist (D-PLAN IC-02b: guard-lands-last) -- WP05's own
#: Definition of Done asserts this programmatically
#: (:func:`test_allowlist_is_empty_after_wp05`): a non-empty allowlist here
#: fails WP05; it is not advisory.
_UNSWEPT_ALLOWLIST: frozenset[str] = frozenset()

#: The 5 modules THIS WP sweeps onto the bridge (WP04 owned_files) -- the
#: genuine verdict-mapping sites. ``status/models.py`` and
#: ``status/reducer.py`` are ALSO WP04-owned files, but are NOT sweep sites:
#: neither has a verdict-mapping code path to adopt the bridge onto (review
#: cycle 1 finding; see the module docstring above). Both are covered by the
#: negative check instead (they never co-occur the inline literal pair).
_SWEPT_MODULES: tuple[str, ...] = (
    "src/specify_cli/sync/emitter.py",
    "src/specify_cli/retrospective/generator.py",
    "src/specify_cli/proof/events.py",
    "src/specify_cli/orchestrator_api/commands.py",
    "src/specify_cli/cli/commands/agent/tasks_move_task.py",
)

#: The exact literal pair whose CO-OCCURRENCE (not either alone) is the
#: forbidden inline equivalence (contract's "grep-guard on co-occurring
#: literals", upgraded here to an AST scan for non-line-adjacency).
_EQUIVALENCE_LITERALS: frozenset[str] = frozenset({"rejected", "changes_requested"})


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "src" / "specify_cli").is_dir():
            return parent
    raise AssertionError("could not locate repo root from test file")


def _string_constants(tree: ast.AST) -> set[str]:
    """Every string constant literal anywhere in *tree* -- comments and
    f-string non-constant parts are never AST ``Constant`` string nodes, so
    this naturally ignores prose/comments and only sees genuine code-level
    literals."""
    return {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }


def _write_module(root: Path, relpath: str, source: str) -> Path:
    path = root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def _co_occurring_equivalence_modules(root: Path) -> dict[str, set[str]]:
    """AST-derived, MODULE-level (not same-line) scan: every ``*.py`` under
    ``src/specify_cli`` (excluding the bridge itself) whose string constants
    include BOTH ``"rejected"`` and ``"changes_requested"`` anywhere in the
    module. Module-level (rather than same-expression) scope is deliberate:
    it is immune to splitting the two literals across different lines,
    functions, or classes within the same file (squad #5's evasion)."""
    offenders: dict[str, set[str]] = {}
    scan_root = root / "src" / "specify_cli"
    if not scan_root.is_dir():
        return offenders
    for path in sorted(scan_root.rglob("*.py")):
        relpath = path.relative_to(root).as_posix()
        if relpath == _BRIDGE_RELPATH:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        present = _string_constants(tree) & _EQUIVALENCE_LITERALS
        if present == _EQUIVALENCE_LITERALS:
            offenders[relpath] = present
    return offenders


def _bound_verdict_vocab_names(tree: ast.Module) -> set[str]:
    """Local names this module's OWN import statements bind to the
    ``specify_cli.status.verdict_vocab`` module object (handles ``import ...
    as`` aliasing, though every real sweep site here uses the plain name).
    Deliberately excludes ``from specify_cli.status.verdict_vocab import X``
    -- that binds a FUNCTION/attribute, not the module object, so a later
    bare call to ``X(...)`` would not show up as a
    ``verdict_vocab.<attr>(...)`` attribute-call shape; requiring the
    module-object-call shape keeps the check simple and uniform across all 7
    sites (which all import the module, not individual names)."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "specify_cli.status":
            for alias in node.names:
                if alias.name == "verdict_vocab":
                    names.add(alias.asname or alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "specify_cli.status.verdict_vocab":
                    names.add((alias.asname or alias.name).split(".")[-1])
    return names


def _imports_and_calls_verdict_vocab(path: Path) -> bool:
    """True iff *path* both imports the bridge module object AND calls one of
    its attributes (``verdict_vocab.<fn>(...)``) somewhere in its own AST.

    This is the anti-evasion half of the guard: the negative check alone can
    be satisfied by a module that just stops spelling the two literals
    together (e.g. by re-deriving the same behaviour some other way without
    ever consulting the canonical bridge). Requiring an actual import + a
    CALL through the bound name means a module that maps verdicts must ROUTE
    through the canonical surface, not merely avoid a particular spelling.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    bound_names = _bound_verdict_vocab_names(tree)
    if not bound_names:
        return False
    return any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id in bound_names
        for node in ast.walk(tree)
    )


# ---------------------------------------------------------------------------
# G2 -- negative check (no inline equivalence outside the bridge/allowlist)
# ---------------------------------------------------------------------------


def test_no_module_other_than_bridge_spells_the_inline_equivalence() -> None:
    """G2: outside the 2-entry WP05 allowlist, no module spells the
    co-occurring ``rejected``/``changes_requested`` equivalence inline."""
    root = _repo_root()
    offenders = _co_occurring_equivalence_modules(root)
    unexpected = set(offenders) - _UNSWEPT_ALLOWLIST
    assert not unexpected, (
        "inline rejected<->changes_requested equivalence found outside "
        f"status/verdict_vocab.py and the WP05 allowlist: {sorted(unexpected)}"
    )


def test_allowlist_is_empty_after_wp05() -> None:
    """squad #15 BLOCKING acceptance check: the allowlist WP05 owns emptying
    is EMPTY at the end of WP05 -- a non-empty allowlist here is a WP05
    failure, not advisory (see WP05's own Definition of Done)."""
    assert not _UNSWEPT_ALLOWLIST


def test_former_allowlist_sites_no_longer_carry_the_equivalence() -> None:
    """Non-vacuity for the (now-empty) allowlist's retirement: the two
    formerly-allowlisted sites (``review/cycle.py``,
    ``review_artifact_consistency.py``) genuinely no longer inline the
    ``rejected``/``changes_requested`` equivalence -- proving WP05 actually
    swept them onto the bridge, rather than the allowlist merely being
    emptied without the underlying modules changing."""
    root = _repo_root()
    offenders = _co_occurring_equivalence_modules(root)
    formerly_allowlisted = frozenset(
        {
            "src/specify_cli/review/cycle.py",
            "src/specify_cli/post_merge/review_artifact_consistency.py",
        }
    )
    still_offending = formerly_allowlisted & set(offenders)
    assert not still_offending, (
        f"{sorted(still_offending)} still inline the rejected/"
        "changes_requested equivalence -- WP05 must route these through "
        "status.verdict_vocab, not merely empty the allowlist"
    )


def test_synthetic_module_splitting_the_literals_across_lines_still_reds(
    tmp_path: Path,
) -> None:
    """Anti-gaming (squad #5): splitting ``'rejected'`` and
    ``'changes_requested'`` across different lines/functions cannot dodge the
    negative check -- it is module-level AST constant presence, not
    same-line/same-expression adjacency."""
    relpath = "src/specify_cli/synthetic_split_equivalence.py"
    _write_module(
        tmp_path,
        relpath,
        "def a() -> str:\n"
        "    return 'rejected'\n"
        "\n\n"
        "def b() -> str:\n"
        "    return 'changes_requested'\n",
    )
    offenders = _co_occurring_equivalence_modules(tmp_path)
    assert relpath in offenders


def test_synthetic_module_with_only_one_literal_does_not_red(tmp_path: Path) -> None:
    """Single-value sites (only one of the two literals) are NOT a G2
    violation -- only the co-occurring PAIR is forbidden."""
    relpath = "src/specify_cli/synthetic_single_value.py"
    _write_module(
        tmp_path,
        relpath,
        "def only_checks_one() -> bool:\n"
        "    return 'changes_requested' == 'changes_requested'\n",
    )
    offenders = _co_occurring_equivalence_modules(tmp_path)
    assert relpath not in offenders


# ---------------------------------------------------------------------------
# T017 -- positive check (import + call), and its own anti-evasion proofs
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("relpath", _SWEPT_MODULES)
def test_swept_module_imports_and_calls_verdict_vocab(relpath: str) -> None:
    """Positive check: each of the 5 WP04-owned sweep sites imports the
    bridge AND calls one of its functions on its verdict-mapping path."""
    root = _repo_root()
    path = root / relpath
    assert _imports_and_calls_verdict_vocab(path), (
        f"{relpath} does not import+call status.verdict_vocab -- the sweep "
        "must route its verdict-mapping path through the canonical bridge, "
        "not merely avoid the inline literal"
    )


def test_synthetic_module_with_fake_verdict_vocab_object_reds_positive_check(
    tmp_path: Path,
) -> None:
    """A module that calls something LOCALLY NAMED ``verdict_vocab`` without
    ever importing the real bridge does NOT satisfy the positive check --
    the bound-name resolution requires an actual import statement, so a
    module cannot fake compliance with a same-named local object."""
    relpath = "src/specify_cli/synthetic_fake_call.py"
    _write_module(
        tmp_path,
        relpath,
        "class _Fake:\n"
        "    def to_event_verdict(self, v: str) -> str:\n"
        "        return v\n\n\n"
        "verdict_vocab = _Fake()\n"
        "verdict_vocab.to_event_verdict('rejected')\n",
    )
    assert not _imports_and_calls_verdict_vocab(tmp_path / relpath)


def test_synthetic_module_importing_but_never_calling_reds_positive_check(
    tmp_path: Path,
) -> None:
    """A module that imports the bridge but never calls any of its
    functions (e.g. only mentions it in a docstring/comment) does not
    satisfy the positive check -- import alone is not adoption."""
    relpath = "src/specify_cli/synthetic_import_only.py"
    _write_module(
        tmp_path,
        relpath,
        "from specify_cli.status import verdict_vocab\n\n\n"
        "_NOTE = 'see verdict_vocab for details'\n",
    )
    assert not _imports_and_calls_verdict_vocab(tmp_path / relpath)


def test_synthetic_module_importing_and_calling_the_bridge_greens_positive_check(
    tmp_path: Path,
) -> None:
    """Sanity: the positive check DOES accept the real adopted shape (import
    + a call through the bound name) -- proves the check is satisfiable, not
    just a permanent red."""
    relpath = "src/specify_cli/synthetic_real_sweep.py"
    _write_module(
        tmp_path,
        relpath,
        "from specify_cli.status import verdict_vocab\n\n\n"
        "def f(v: str) -> str:\n"
        "    return verdict_vocab.to_event_verdict(v)\n",
    )
    assert _imports_and_calls_verdict_vocab(tmp_path / relpath)


# ---------------------------------------------------------------------------
# T016 -- the bridge's own unit tests (total mapping + render-only inverse)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("artifact_verdict", "expected_event_verdict"),
    [
        ("approved", "approved"),
        ("rejected", "changes_requested"),
        ("arbiter_override", "approved"),
        ("approved_after_orchestrator_fix", "approved"),
    ],
)
def test_to_event_verdict_is_total_over_all_four_inbound_values(
    artifact_verdict: str, expected_event_verdict: str
) -> None:
    """G1: the mapping is total over all four inbound artifact values."""
    assert verdict_vocab.to_event_verdict(artifact_verdict) == expected_event_verdict


def test_to_event_verdict_rejects_unknown_input() -> None:
    with pytest.raises(ValueError):
        verdict_vocab.to_event_verdict("damaged")


@pytest.mark.parametrize(
    ("event_verdict", "expected_artifact_verdict"),
    [
        ("approved", "approved"),
        ("changes_requested", "rejected"),
    ],
)
def test_to_artifact_verdict_inverse_for_prose_render(
    event_verdict: str, expected_artifact_verdict: str
) -> None:
    assert verdict_vocab.to_artifact_verdict(event_verdict) == expected_artifact_verdict


def test_to_artifact_verdict_rejects_unknown_input() -> None:
    with pytest.raises(ValueError):
        verdict_vocab.to_artifact_verdict("damaged")


def test_artifact_and_event_verdict_domains() -> None:
    assert verdict_vocab.artifact_verdicts() == {
        "approved",
        "rejected",
        "arbiter_override",
        "approved_after_orchestrator_fix",
    }
    assert verdict_vocab.event_verdicts() == {"approved", "changes_requested"}
    assert verdict_vocab.emission_artifact_verdicts() == {"approved", "rejected"}


def test_is_changes_requested_and_is_approved_predicates() -> None:
    assert verdict_vocab.is_changes_requested("changes_requested") is True
    assert verdict_vocab.is_changes_requested("approved") is False
    assert verdict_vocab.is_changes_requested(None) is False
    assert verdict_vocab.is_approved("approved") is True
    assert verdict_vocab.is_approved("changes_requested") is False


# ---------------------------------------------------------------------------
# D-PLAN-14 / T019 -- override never synthesizes a review_result verdict
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "override_verdict", ["arbiter_override", "approved_after_orchestrator_fix"]
)
def test_emission_event_verdict_refuses_override_values(override_verdict: str) -> None:
    """D-PLAN-14: an override/orchestrator-fix artifact verdict must NEVER be
    accepted by the emission-scoped helper -- it is not a valid input to an
    *emitted* ``review_result`` event. A caller attempting this gets a
    refusal, never a silently-synthesized ``"approved"``."""
    with pytest.raises(ValueError):
        verdict_vocab.emission_event_verdict(override_verdict)


@pytest.mark.parametrize(
    ("artifact_verdict", "expected_event_verdict"),
    [("approved", "approved"), ("rejected", "changes_requested")],
)
def test_emission_event_verdict_accepts_the_two_scoped_values(
    artifact_verdict: str, expected_event_verdict: str
) -> None:
    assert verdict_vocab.emission_event_verdict(artifact_verdict) == expected_event_verdict


def test_arbiter_override_does_not_synthesize_an_approved_review_result_event() -> None:
    """End-to-end negative test (T019): an arbiter override recorded via a
    :class:`ReviewOverride` annotation delta must never be reflected as a
    synthesized ``approved`` ``review_result`` event by the reducer --
    ``reducer.py``'s ``_apply_annotation_delta`` keeps the ``review``
    (override) slot and the ``review_result`` (reviewer verdict) slot
    strictly separate; only the former is written here, and the latter is
    never derived from it via this bridge or otherwise."""
    override = ReviewOverride(
        at="2026-01-01T00:00:00+00:00",
        actor="arbiter",
        wp_id="WP01",
        reason="stale rejection superseded",
    )
    state: dict[str, object] = {}
    delta = WPInnerStateDelta(review=override)

    _apply_annotation_delta(state, delta)

    assert state.get("review") == override.to_dict()
    assert "review_result" not in state, (
        "an arbiter override must be recorded via the 'review' slot only -- "
        "the reducer must never fabricate a 'review_result' verdict "
        "(approved or otherwise) from an override annotation"
    )
