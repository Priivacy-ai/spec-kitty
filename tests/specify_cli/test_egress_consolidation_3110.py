"""The consolidation's own criteria: SC-004, SC-015, SC-025, NFR-004 (#3110).

This module is the mission-level home for the assertions that are **about the
consolidation itself** rather than about either transport. The per-transport
halves — SC-016's ``DENIED`` pins and SC-004 clause 2's per-transport fragment
checks — live in each package's own test tree, because only there does the
end-to-end refusal path have fixtures to drive it:

* ``tests/specify_cli/saas_client/test_client_consent_gate_3030.py``
* ``tests/sync/tracker/test_saas_client_consent_gate_3030.py``

**SC-004 is three clauses and they are not equal in discriminating power.**
Clauses 1 and 2 are ``[ratchet]``: they hold of the *unconsolidated* state by
construction (the operator's Q2 decision keeps both ``DENIED`` strings verbatim),
so a green SC-004 must never be read as "the consolidation happened". **Clause 3
— the two ``is`` comparisons below — is the clause that reds.** It reds on the
one state nothing else in the spec detects: a partial consolidation in which a
transport's old ``egress_consent`` module survives as a *re-export*, so the
deciding module's by-value binding still points at the old object while every
rendered string stays byte-for-byte correct.

**Identity is a detector, never an actuator.** Rebinding
``specify_cli.egress.project_egress_refusal`` does **not** make a patch effective
at ``saas_client/client.py``'s decision point — that module holds its own
by-value binding taken at import time, and no module layout changes that. What
the ``is`` comparisons buy is *detection* of a stale binding, and the conversion
of "did the consolidation happen?" from a source scan into a runtime assertion.
"""

from __future__ import annotations

import ast
import builtins
import importlib
import sys
from pathlib import Path
from typing import Any

import pytest

from specify_cli import egress
from specify_cli.saas_client import client as saas_deciding_module

# ``specify_cli.tracker.saas_client`` is the tracker *transport* module. It was also a Channel-1
# deciding module until #3108's Bundle-C port; it is imported here for its identifier fragment
# (clause 1 / clause 2), and clause 3 no longer reads it. See :data:`EXPECTED_VERDICT_BINDERS`.
from specify_cli.tracker import saas_client as tracker_transport_module

#: **Without this line the entire module is selected by ZERO CI gates.**
#:
#: It is not decoration. This file is the sole home of SC-004 clause 3 — the
#: only clause that reds; clauses 1 and 2 are ratchets that hold of the
#: *unconsolidated* state — and of SC-015's standing mechanism, which FR-008,
#: the mission's headline requirement, maps to **alone** and which no mutation
#: in the suite targets. Also SC-025, the FR-012 prose guard and NFR-004's five
#: pins.
#:
#: Unmarked and outside a gated path, none of that runs on the merge target:
#: every green would be a hand-invoked local green, and the partial-consolidation
#: state that clause 3 is the only thing in the spec able to detect would ship
#: undetected. `tests/architectural/test_gate_coverage.py::test_no_new_orphan_surfaces`
#: catches it and named this file.
#:
#: That gate also offers `--update-baseline`. **Do not take it.** Baselining
#: would record "the mission's only discriminating test never runs" as accepted —
#: a defect-masking ratchet, and the exact shape of every serious defect found on
#: this mission. Both sibling guards carry this same marker.
pytestmark = pytest.mark.fast

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]

#: SC-015's mandated scan scope, verbatim: *"an AST or text scan over ``src/``"*
#: (POST-ACCEPTANCE CORRECTION clause (b)). **The whole tree, not one package.**
#:
#: WP03's T021(a) narrowed this to ``src/specify_cli`` and the implementer
#: correctly followed that binding instruction, so the narrowing was a
#: spec/contract divergence rather than a deviation — recorded as WP03 R-1 and
#: closed here.
#:
#: The narrower root passed for a reason worth writing down: the measured gap is
#: **empty**. None of the six other top-level packages (``charter``,
#: ``doctrine``, ``glossary``, ``kernel``, ``mission_runtime``, ``runtime``)
#: carries egress policy today, so the widening moves no site count — it moves
#: only the 936 → 1197 input count and the *reach* of the scan. That is the whole
#: value: FR-008 is violated by a second definition appearing in a **new** file,
#: and a scan rooted at one package cannot see one land next door. An empty gap
#: today is not a promise about tomorrow.
SRC = REPO_ROOT / "src"


# ---------------------------------------------------------------------------
# SC-004 clause 3 — binding identity (THE CLAUSE THAT REDS)
# ---------------------------------------------------------------------------


#: Every module holding a **module-level by-value binding** of ``project_egress_refusal``,
#: i.e. every module where a stale re-export could hide. Derived by AST over ``src/`` by
#: :func:`_scan_verdict_binders`; this constant is the pinned expectation that derivation is
#: checked against, so a *change* in the topology reds and forces a human to look instead of
#: being absorbed silently.
#:
#: RE-PINNED 2026-08-10 (#3287 / #3302, egress-single-authority). Previously this set also
#: included ``specify_cli.tracker.egress_verdict``. The single-authority consolidation retired
#: ``egress_verdict``'s second Channel-1 derivation: ``_resolve_channel1`` no longer binds the
#: ``project_egress_refusal`` *wrapper* by value — it now takes a module-level by-value binding
#: of the underlying decider ``egress._egress_decision`` and reads ``refusal_message`` /
#: ``channel1_state`` / ``generic`` straight off the single ``EgressDecision`` it returns
#: (``egress_verdict.py`` imports ``_egress_decision`` at module level; ``_resolve_channel1``
#: calls it). So the name DISAPPEARED here because the decision point *tightened onto the one
#: decider*, not because it stopped reaching it — the verified delegation chain the assertion
#: message asks for. Binding ``_egress_decision`` from its own definition module carries no
#: stale-re-export hazard (unlike the historical ``egress_consent.py`` re-export of
#: ``project_egress_refusal`` that this gate hunts), so ``egress_verdict`` is correctly out of
#: scope for THIS scan. Restoring a direct ``project_egress_refusal`` binding here would
#: reintroduce the exact second Channel-1 derivation the PR removes.
#:
#: RE-PINNED 2026-08-07 (PR #3135 / #3108 Bundle-C port). Previously
#: ``{specify_cli.saas_client.client, specify_cli.tracker.saas_client}``, hardcoded as two
#: import aliases at the top of this file. The Bundle-C port routed the tracker transport's
#: decision point (``tracker/saas_client.py::_request``, now ``:341``) through
#: ``tracker_egress_verdict(...)`` — the two-channel verdict — instead of calling
#: ``project_egress_refusal`` directly, so ``specify_cli.tracker.saas_client`` no longer binds
#: the name at all and the old pin raised ``AttributeError``.
#:
#: **The consolidation clause 3 guards did not regress — it tightened.** Verified delegation
#: chain (not an independent decider): ``tracker/saas_client.py::_request`` ->
#: ``tracker.egress_verdict.tracker_egress_verdict`` -> ``egress_verdict._resolve_channel1``
#: (``:383``) -> ``specify_cli.egress.project_egress_refusal``. ``egress_verdict.py:143-153``
#: states the property in the product itself: *"This module holds the Mission's only
#: module-level import of ``project_egress_refusal``"*, and ``_resolve_channel1``'s docstring
#: says it *"delegates entirely"* to it. Under ``egress_verdict.py``'s own design statement —
#: both the gates that raise and the surface that reports call one function *"so the enforced
#: answer and the reported answer cannot disagree"* — ``tracker.saas_client`` is no longer a
#: decider; it is a caller of the one decider. The definition site is **more** singular than
#: before the port, not less: the tracker side went from one binding per transport client to
#: one binding for the whole tracker package.
#:
#: **Restoring a direct ``project_egress_refusal`` binding in ``tracker/saas_client.py`` would
#: be the wrong fix.** It would give the hosted tracker path two Channel-1 decisions — one
#: direct, one through the verdict — which is precisely the "enforced answer and reported
#: answer disagree" hazard ``egress_verdict.py`` exists to prevent, and it would put a second
#: composer in front of FR-016's byte-identical hosted refusal string.
#:
#: This is a re-pin of the module SET, never a weakening of the assertion: the ``is``
#: comparison below is unchanged, it is now applied to every derived binder rather than to two
#: names restated by hand, and a THIRD binder appearing anywhere under ``src/`` reds this too —
#: which the hardcoded form could not do.
EXPECTED_VERDICT_BINDERS = frozenset(
    {
        "specify_cli.saas_client.client",
    }
)


def _dotted_module_name(path: Path, root: Path) -> str:
    """The importable dotted name of *path*, a ``.py`` file under *root* (``src/``)."""
    relative = path.relative_to(root).with_suffix("")
    parts = list(relative.parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _scan_verdict_binders(root: Path) -> tuple[frozenset[str], int]:
    """Modules under *root* with a module-level ``from specify_cli.egress import
    project_egress_refusal``, plus the number of files scanned.

    **Module level only, and that is the point.** A by-value binding is only observable — and
    only capable of going stale against a re-export — when it lands as a module *attribute*.
    A function-local import creates no attribute and rebinds nothing that outlives the call, so
    it cannot be the partial-consolidation state clause 3 detects. ``import specify_cli.egress``
    plus attribute access is likewise out of scope: it resolves through the definition module on
    every call and can never be stale.

    The file count is returned so a caller can prove the scan looked at something. A scan that
    walks zero files finds zero binders and reads exactly like a clean tree.
    """
    binders: set[str] = set()
    files = sorted(root.rglob("*.py"))
    for path in files:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (SyntaxError, UnicodeDecodeError):  # pragma: no cover - defensive
            continue
        for node in tree.body:  # direct children only == module level
            if not isinstance(node, ast.ImportFrom):
                continue
            if node.module != EGRESS_MODULE_DOTTED_NAME or node.level:
                continue
            if any(alias.name == "project_egress_refusal" for alias in node.names):
                binders.add(_dotted_module_name(path, root))
    return frozenset(binders), len(files)


def test_sc004_clause3_every_deciding_module_binds_the_one_definition_site() -> None:
    """Every decision point holds the *same object* as ``specify_cli.egress``.

    *Anti-vacuity (R-7)*: the modules compared here are **derived** from an AST scan over
    ``src/`` and imported through their own dotted paths, never through ``specify_cli.egress``.
    Comparing two imports of one path would compare an object to itself and prove nothing.

    *Why identity and not text*: a surviving re-export renders the **identical correct
    string**, so a correct consolidation and a stale re-export produce exactly the same text
    observations. Text cannot separate them; ``is`` can. This is demonstrated in the mission
    evidence by MUT-2, which rebinds the tracker attribute to a delegating wrapper returning
    the identical string — every string observation stays green and only these assertions red.

    The attributes are read **at assert time**, not captured at import time, so a plugin that
    rebinds a deciding module's attribute is detected.
    """
    derived, scanned = _scan_verdict_binders(SRC)
    assert scanned > 100, (
        f"scanned only {scanned} files under {SRC} — a scan over (almost) nothing finds no "
        "binders and reads exactly like a consolidated tree"
    )
    assert derived == EXPECTED_VERDICT_BINDERS, (
        "the set of modules holding a module-level by-value binding of "
        f"project_egress_refusal changed: derived {sorted(derived)}, pinned "
        f"{sorted(EXPECTED_VERDICT_BINDERS)}. A NEW name here is a new place a stale "
        "re-export can hide and must be justified before it is pinned; a name DISAPPEARING "
        "means a decision point stopped binding the canonical decider — confirm it now "
        "reaches it through a verified delegation chain (as tracker.saas_client does via "
        "tracker.egress_verdict) and re-pin with a dated rationale, or restore the binding. "
        "Do not edit this constant to match without establishing which of the two it is."
    )

    for dotted in sorted(derived):
        module = importlib.import_module(dotted)
        assert module.project_egress_refusal is egress.project_egress_refusal, (
            f"{dotted}.project_egress_refusal is not the object defined in "
            "specify_cli.egress. That decision point is bound by value at import time, so "
            "it is still calling whatever object it imported — most likely a surviving "
            "egress_consent.py re-export. Every rendered string would still be correct; "
            "that is exactly why this is an identity check."
        )


def test_sc004_clause3_names_are_reachable_and_the_comparison_is_not_self_identity() -> None:
    """Positive control for the assertion above — it must be able to fail.

    Distinct module objects, distinct dotted paths, none of them ``specify_cli.egress``
    itself. If any pinned binder were an alias of the definition module, the ``is``
    comparisons above would be trivially true and would prove nothing.
    """
    # FLOOR LOWERED 2->1 on 2026-08-10 (#3287 / #3302, egress-single-authority). The
    # single-authority consolidation retired the second ``project_egress_refusal`` binder
    # (``tracker.egress_verdict`` now binds the underlying decider ``_egress_decision`` directly
    # — see the RE-PINNED note on EXPECTED_VERDICT_BINDERS above), leaving exactly one binder,
    # ``saas_client.client``. That single comparison is NOT vacuous: non-vacuity here is fully
    # carried by the ``EGRESS_MODULE_DOTTED_NAME not in ...`` self-identity guard below and the
    # impostor control at the end of this test — the old ``>= 2`` floor was belt-and-suspenders
    # on top of those, not the thing preventing self-identity. A floor of ``>= 1`` still reds a
    # fully-empty (genuinely vacuous, zero-binder) pin, which is the failure mode worth keeping.
    assert len(EXPECTED_VERDICT_BINDERS) >= 1, (
        "clause 3 is pinned to zero deciding modules — the comparison would iterate nothing and "
        f"prove nothing: {sorted(EXPECTED_VERDICT_BINDERS)}"
    )
    assert EGRESS_MODULE_DOTTED_NAME not in EXPECTED_VERDICT_BINDERS, (
        "the definition module is pinned as one of its own binders — that comparison is "
        "self-identity and clause 3 would be vacuous"
    )
    names = {importlib.import_module(dotted).__name__ for dotted in EXPECTED_VERDICT_BINDERS}
    assert names == set(EXPECTED_VERDICT_BINDERS), (
        f"the pinned names are not independent module paths: {sorted(names)}"
    )

    # A deliberately wrong comparison: a different object must NOT satisfy the
    # identity assertion. This is the control that proves `is` here is doing work.
    def _impostor(project_root: Path | None, identifiers: str) -> str | None:
        return egress.project_egress_refusal(project_root, identifiers)

    assert _impostor is not egress.project_egress_refusal, (
        "a delegating wrapper compared identical to the real function — `is` is "
        "not discriminating here and clause 3 would be vacuous"
    )


# ---------------------------------------------------------------------------
# SC-004 clause 1 [ratchet] — one template, one non-fragment portion
# ---------------------------------------------------------------------------

#: The per-caller identifier-set fragments, imported from the two transports
#: rather than restated here — each transport owns its own (Q2).
SAAS_FRAGMENT = saas_deciding_module.SAAS_EGRESS_IDENTIFIER_KINDS
TRACKER_FRAGMENT = tracker_transport_module.TRACKER_EGRESS_IDENTIFIER_KINDS


def test_sc004_clause1_the_non_fragment_portion_is_byte_identical() -> None:
    """The two ``DENIED`` strings differ **only** in the per-caller fragment.

    ``[ratchet]`` — already true at ``bb2020fea``, where the two strings were
    four-part concatenations differing in exactly one word. It must **stay**
    true; it does not distinguish a correct consolidation from an incorrect one.

    Asserted mechanically: render the one shared template with each fragment and
    remove that fragment from each rendering. What is left must be identical —
    which is only possible if there is one template.
    """
    root = Path("/nonexistent/example-project")
    saas_rendered = egress._render_denied_refusal(root, SAAS_FRAGMENT)
    tracker_rendered = egress._render_denied_refusal(root, TRACKER_FRAGMENT)

    assert saas_rendered != tracker_rendered, (
        "the two transports rendered the identical string — the per-caller "
        "fragment is not reaching the template, so FR-009's per-transport "
        "requirement is unmet"
    )
    assert saas_rendered.replace(SAAS_FRAGMENT, "") == tracker_rendered.replace(
        TRACKER_FRAGMENT, ""
    ), (
        "the non-fragment portion of the two DENIED strings is not byte-identical:\n"
        f"  saas:    {saas_rendered!r}\n"
        f"  tracker: {tracker_rendered!r}\n"
        "Two templates would produce this. FR-008 requires one."
    )


# ---------------------------------------------------------------------------
# SC-004 clause 2 [ratchet] — each fragment names exactly its own set
# ---------------------------------------------------------------------------

#: The identifier kinds each transport can put on the wire, transcribed from the
#: spec's **Key Entities** table (`spec.md`, "Identifier kinds each transport can
#: transmit"). These are a fixed list the implementer did not choose — that is
#: the point: the implementer can no longer both pick the wording and write the
#: assertion that blesses it.
#:
#: **Scope, ruling PB-3**: FR-009 covers *the identifiers of the project whose
#: consent was refused*. It does **not** cover ``team_slug`` (the destination
#: team the request would be addressed to) or ``invited_user_ids`` (recipient
#: ints). Corollary: nobody may "fix" a refusal string by appending the
#: destination team's name — that would *add* an identifier to an operator-facing
#: message rather than remove one.
SAAS_OWN_KINDS = ("mission", "decision")
TRACKER_OWN_KINDS = ("mission", "engagement")

#: Kinds that belong to the other transport only. ``mission`` is the single
#: member the two sets share, so it appears in neither list.
SAAS_FOREIGN_KINDS = ("engagement",)
TRACKER_FOREIGN_KINDS = ("decision",)


@pytest.mark.parametrize(
    ("fragment", "own", "foreign", "label"),
    [
        (SAAS_FRAGMENT, SAAS_OWN_KINDS, SAAS_FOREIGN_KINDS, "saas_client"),
        (TRACKER_FRAGMENT, TRACKER_OWN_KINDS, TRACKER_FOREIGN_KINDS, "tracker"),
    ],
)
def test_sc004_clause2_fragment_names_its_own_set_and_no_foreign_kind(
    fragment: str, own: tuple[str, ...], foreign: tuple[str, ...], label: str
) -> None:
    """Every kind this transport carries is named; no other transport's is.

    ``[ratchet]`` — true of the unconsolidated state by construction, because
    Q2 keeps both current strings verbatim. *One live edge*: if this fails
    against the Key-Entities sets **on the existing text**, that is a real
    finding and FR-009 returns to ``[build]``.
    """
    for kind in own:
        assert kind in fragment, (
            f"{label}'s fragment {fragment!r} does not name {kind!r}, which this "
            "transport can put on the wire (spec Key Entities). An operator told "
            "less than what was about to move is misinformed."
        )
    for kind in foreign:
        assert kind not in fragment, (
            f"{label}'s fragment {fragment!r} names {kind!r}, which this transport "
            "cannot transmit. Overstating exposure in a confidentiality message is "
            "the wrong direction to be wrong (US2-AS2)."
        )


# ---------------------------------------------------------------------------
# SC-015 [standing] — exactly one definition site (the MECHANISM)
# ---------------------------------------------------------------------------

#: The names of the texts whose definition sites are counted: the shared
#: **template** plus the **four verdict branches**, plus the two texts that are
#: not verdict branches but are equally duplicable (the ``None`` guard and the
#: import-failure degradation). Read off ``specify_cli.egress`` at run time so
#: this scan never hard-codes today's wording.
_ONE_SITE_ATTRS = (
    "_DENIED_TEMPLATE",
    "_NO_RESOLVER_REFUSAL",
    "_UNANSWERABLE_TEMPLATE",
    "_UNRECOGNISED_VERDICT_TEMPLATE",
    "_IMPORT_FAILURE_TEMPLATE",
    "UNDETERMINED_PROJECT_REFUSAL",
)


def _string_constants(tree: ast.AST) -> list[tuple[str, int]]:
    """Every ``str`` constant in *tree*, with its line number.

    Python folds implicitly concatenated adjacent string literals into a single
    :class:`ast.Constant` at parse time, so a refusal written across six source
    lines is recovered here as one value — which is what makes a *content* scan
    possible at all.
    """
    out: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            out.append((node.value, node.lineno))
    return out


def test_sc015_template_and_verdict_branches_have_exactly_one_definition_site() -> None:
    """A second definition of the template or of a verdict branch reds this.

    **This is a content scan, not a file-absence check.** ``assert not (SRC /
    "specify_cli" / "saas_client" / "egress_consent.py").exists()`` would pass
    forever after the deletion and could **never** red on a second definition
    appearing in a *new* file — which is the only way FR-008 is realistically
    violated. The scan below keys on the text, so a copy under a different
    constant name in a brand-new module is still found.

    **Scope is ``src/``, the whole tree** (SC-015's POST-ACCEPTANCE CORRECTION
    clause (b)). See :data:`SRC` for why the narrower ``src/specify_cli`` root
    this replaces measured identically and was still the wrong scope.

    Q2 does not weaken this: per-caller identifier fragments are **arguments**,
    not second presentations.
    """
    canonical = {name: getattr(egress, name) for name in _ONE_SITE_ATTRS}
    missing = [name for name, value in canonical.items() if not isinstance(value, str)]
    assert not missing, (
        f"specify_cli.egress no longer defines {missing} — this scan would silently "
        "count zero sites for a text that no longer exists and read as a clean gate"
    )

    files = sorted(SRC.rglob("*.py"))
    assert len(files) > 100, (
        f"scanned only {len(files)} files under {SRC} — a scan over "
        "(almost) nothing finds one of nothing and looks like a measurement"
    )

    # SC-015 mandates ``src/``, and "over 100 files" cannot tell that root apart
    # from a re-narrowing to ``src/specify_cli`` alone — 936 files, comfortably
    # over the floor, and exactly the state WP03 R-1 records. So the scan's
    # *reach* is asserted too.
    #
    # The expectation is anchored at ``REPO_ROOT / "src"`` and NOT at :data:`SRC`,
    # and the duplication is the whole point: deriving both sides from the scan
    # root makes the assertion agree with whatever that root happens to be, which
    # is vacuous against the one regression it exists to catch. Anchored here, a
    # narrowed ``SRC`` reds. Do not "simplify" this to ``SRC.iterdir()``.
    #
    # Keyed on ``__init__.py`` rather than on "is a directory" so that adding a
    # non-package directory under ``src/`` does not red this — only losing a
    # *package* from the scan's reach does.
    src_packages = [d for d in sorted((REPO_ROOT / "src").iterdir()) if (d / "__init__.py").is_file()]
    assert len(src_packages) > 1, (
        f"found {len(src_packages)} package(s) under {REPO_ROOT / 'src'} — with one "
        "or none the reach assertion below cannot distinguish a src/-wide scan from "
        "a single-package one, so it would pass without measuring anything"
    )
    unreached = [d.name for d in src_packages if not any(f.is_relative_to(d) for f in files)]
    assert not unreached, (
        f"the definition-site scan reached {len(files)} files but none in "
        f"{unreached} — package(s) that exist under {REPO_ROOT / 'src'}.\n\n"
        "SC-015's POST-ACCEPTANCE CORRECTION mandates a scan over `src/` — the "
        "whole tree. A second definition of the refusal policy violates FR-008 "
        "wherever it lands, and a scan rooted at one package cannot see one "
        "appear in a sibling. Removing a package from src/ does not red this; "
        "narrowing the scan root away from src/ is what does."
    )

    sites: dict[str, list[str]] = {name: [] for name in canonical}
    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for value, lineno in _string_constants(tree):
            for name, canonical_value in canonical.items():
                if value == canonical_value:
                    sites[name].append(f"{path.relative_to(REPO_ROOT)}:{lineno}")

    report = "\n".join(f"  {name}: {len(found)} site(s) — {found}" for name, found in sites.items())
    duplicated = {name: found for name, found in sites.items() if len(found) != 1}
    assert not duplicated, (
        f"expected exactly 1 definition site per refusal text over {len(files)} files "
        f"under {SRC}, found:\n{report}\n\n"
        "FR-008 requires exactly one editable presentation of the refusal policy. "
        "A second copy is a second thing to edit, and the two will drift."
    )

    for name, found in sites.items():
        assert found[0].startswith("src/specify_cli/egress.py:"), (
            f"{name} is defined at {found[0]}, not in src/specify_cli/egress.py — "
            "the single definition site must be the module owned by neither transport"
        )


# ---------------------------------------------------------------------------
# SC-025 [standing] — the C-005 classification is present
# ---------------------------------------------------------------------------

#: The dotted name of the consolidated module, as a **value**. SC-025's
#: anti-vacuity clause forbids restating the list:
#: ``"specify_cli.egress" in ["specify_cli.egress"]`` asserts nothing.
EGRESS_MODULE_DOTTED_NAME = "specify_cli.egress"


def test_sc025_the_shared_module_is_classified_as_integration() -> None:
    """The integration-boundary gate must know about ``specify_cli.egress``.

    *Why this is gated at all, and why nothing else notices*: forgetting the
    classification makes the boundary gate **permissive**, not red.
    ``_gate_coverage._src_dir_of_glob`` returns ``None`` for any
    ``src/specify_cli/<file>.py`` glob and the unclaimed-src-dir worklist
    iterates direct child **directories**, so a plain module is *structurally
    outside* that detector at any size. A package that grew past ``T_LOC = 500``
    would eventually surface there; a module never can. This assertion is what
    closes the gap that loss opens.
    """
    from tests.architectural.test_integration_boundary import INTEGRATION_PREFIXES

    assert egress.__name__ == EGRESS_MODULE_DOTTED_NAME, (
        "this test names a module that is not the one under test — "
        f"{EGRESS_MODULE_DOTTED_NAME!r} vs {egress.__name__!r}"
    )
    assert EGRESS_MODULE_DOTTED_NAME in INTEGRATION_PREFIXES, (
        f"{EGRESS_MODULE_DOTTED_NAME!r} is not in the integration-boundary gate's "
        f"INTEGRATION_PREFIXES ({INTEGRATION_PREFIXES!r}). The module lazily imports "
        "specify_cli.sync, so leaving it unclassified makes the CORE→INTEGRATION "
        "gate permissive about anything in CORE that reaches it — silently (C-005)."
    )


# ---------------------------------------------------------------------------
# NFR-004 — every refusal branch is operator-actionable, pinned PER BRANCH
# ---------------------------------------------------------------------------
#
# All five pins already hold at ``bb2020fea``, so the build work is *pinning*
# them: they do NOT discriminate a correct implementation from an incorrect one.
# "Non-empty and distinguishable" is explicitly not the bar — five strings
# "denied 1".."denied 5" satisfy that weaker form, which is a defect-masking
# assertion under DIR-041.


def _verdicts() -> Any:
    from specify_cli.invocation.adapters import EgressConsent

    return EgressConsent


def test_nfr004_denied_branch_names_the_operator_action() -> None:
    rendered = egress._render_denied_refusal(Path("/nonexistent/p"), SAAS_FRAGMENT)
    assert "sync opt-in" in rendered, (
        f"the DENIED branch does not name a concrete next action: {rendered!r}"
    )
    assert ".kittify/config.yaml" in rendered, (
        f"the DENIED branch does not name the file to correct: {rendered!r}"
    )


def test_nfr004_no_resolver_branch_names_the_resolver() -> None:
    rendered = egress._refusal_for_verdict(_verdicts().NO_RESOLVER, Path("/nonexistent/p"), SAAS_FRAGMENT)
    assert rendered is not None and "resolver" in rendered, (
        f"the NO_RESOLVER branch does not name the resolver: {rendered!r}"
    )


def test_nfr004_undetermined_and_unanswerable_stay_distinguishable() -> None:
    """Both contain ``could not be determined``; they must still differ.

    Correction C-1: they are different *causes* with different operator fixes —
    "nothing told the transport whose data it carries" versus "the consent chain
    raised or returned an unrecognized answer".
    """
    undetermined = egress.project_egress_refusal(None, SAAS_FRAGMENT)
    unanswerable = egress._refusal_for_verdict(
        _verdicts().UNANSWERABLE, Path("/nonexistent/p"), SAAS_FRAGMENT
    )
    assert undetermined is not None and unanswerable is not None
    assert "could not be determined" in undetermined
    assert "could not be determined" in unanswerable
    assert undetermined != unanswerable, (
        "UNDETERMINED and UNANSWERABLE render the same text; the operator cannot "
        "tell 'no project was named' from 'the consent chain faulted'"
    )
    assert "is not consent" in unanswerable, (
        f"the UNANSWERABLE branch does not state why it refuses: {unanswerable!r}"
    )


def test_nfr004_import_failure_branch_carries_the_exception_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-013: an unimportable hosted-sync package refuses, and says why.

    Driven behaviourally rather than pinned on the constant: the lazy
    ``import specify_cli.sync`` is made to raise, and the real function is
    called. That also proves the import stays *inside* the function — a
    module-level import could not be intercepted here.
    """
    real_import = builtins.__import__
    boom = "synthetic import failure for FR-013"

    def _explode(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "specify_cli.sync":
            raise ImportError(boom)
        return real_import(name, *args, **kwargs)

    monkeypatch.delitem(sys.modules, "specify_cli.sync", raising=False)
    monkeypatch.setattr(builtins, "__import__", _explode)

    refusal = egress.project_egress_refusal(Path("/nonexistent/p"), SAAS_FRAGMENT)

    assert refusal is not None, (
        "an unimportable hosted-sync package produced a PERMIT — inability to "
        "resolve consent is never consent (FR-013)"
    )
    assert boom in refusal, (
        f"the import-failure branch does not carry the exception text: {refusal!r}"
    )


def test_nfr004_unrecognised_future_verdict_does_not_reuse_denied_remedy() -> None:
    """A member added to ``EgressConsent`` later must not borrow DENIED's advice."""

    class _FutureVerdict:
        value = "quarantined"
        permits_egress = False

    rendered = egress._refusal_for_verdict(_FutureVerdict(), Path("/nonexistent/p"), SAAS_FRAGMENT)  # type: ignore[arg-type]
    assert rendered is not None
    assert "quarantined" in rendered, (
        f"the unrecognised-verdict branch drops the verdict name: {rendered!r}"
    )
    assert "sync opt-in" not in rendered, (
        "an unrecognised verdict reused DENIED's remedy, which tells the operator "
        f"to do something that will not help: {rendered!r}"
    )


# ---------------------------------------------------------------------------
# FR-012 / T019(b) — the relocated rationale actually landed here
# ---------------------------------------------------------------------------


def test_fr012_rationale_and_tracker_precondition_live_in_the_consolidated_module() -> None:
    """The deleted files' load-bearing prose has a home, and it is this module.

    FR-012 is High-impact, ``[ratchet]`` and deliberately has **no success
    criterion**. Its only written rationale in the repository was the prose in
    ``tracker/egress_consent.py`` — a file this mission deletes. Two guard tests
    now point a reader at ``specify_cli/egress.py`` for the precondition; this
    assertion is what stops that pointer from dangling.
    """
    # Whitespace-normalised: this asserts the *content* is present, not that it
    # sits on particular lines. Pinning wrapped prose by exact layout is a
    # ratchet that benign reflow moves (DIR-041), which would train the next
    # editor to delete the assertion rather than keep the text.
    doc = " ".join((egress.__doc__ or "").split())
    for needle, why in [
        ("FR-012", "the requirement id a future editor would search for"),
        ("resolve_egress_consent", "the seam the wrapper must keep resolving through"),
        ("never re-derive", "the prohibition on a local checkout->project->consent chain"),
        (
            "Every construction site must pass the root of the project that owns "
            "the record the request will carry.",
            "the attribution precondition, quoted in both guards' failure messages",
        ),
        (
            "written down here rather than left implicit",
            "the paragraph explaining WHY the precondition is stated at all — the "
            "SaaS file quoted the sentence but never this reasoning",
        ),
        (
            "machine-global",
            "the 2026-07-27 incident mechanism: arming is never a grant",
        ),
        ("bind_mission_origin", "tracker site 1 of the three-site enumeration"),
        ("SaaSTrackerService", "tracker site 2 of the three-site enumeration"),
        ("search_origin_candidates", "tracker site 3 of the three-site enumeration"),
        ("decision widen", "the SaaS enumeration's weakest site (FR-026/SC-022)"),
    ]:
        assert needle in doc, (
            f"src/specify_cli/egress.py's docstring does not contain {needle!r} — "
            f"{why}. tests/sync/tracker/test_saas_client_consent_gate_3030.py and "
            "tests/specify_cli/saas_client/test_client_consent_gate_3030.py both "
            "point a reader here; without this text those pointers dangle."
        )

    assert "ULID rather than a slug" not in doc, (
        "the relocated FR-026 enumeration still argues the `decision widen` entry "
        "is benign because decision_id is a ULID rather than a slug. F-B2 falsified "
        "that: there is no validation anywhere on the path and the string is "
        "interpolated raw into the URL (SC-022)."
    )
    assert "egress_consent.py" not in doc, (
        "the consolidated module's docstring points at a file this mission deletes "
        "— a verbatim relocation shipped a dangling pointer into the new module"
    )
