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
import sys
from pathlib import Path
from typing import Any

import pytest

from specify_cli import egress
from specify_cli.saas_client import client as saas_deciding_module
from specify_cli.tracker import saas_client as tracker_deciding_module

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


def test_sc004_clause3_both_deciding_modules_bind_the_one_definition_site() -> None:
    """Both decision points hold the *same object* as ``specify_cli.egress``.

    *Anti-vacuity (R-7)*: the three names below are imported through **three
    independent module paths** at the top of this file — ``specify_cli.egress``,
    ``specify_cli.saas_client.client`` and ``specify_cli.tracker.saas_client``.
    Comparing two imports of one path would compare an object to itself and
    prove nothing.

    *Why identity and not text*: a surviving re-export renders the **identical
    correct string**, so a correct consolidation and a stale re-export produce
    exactly the same text observations. Text cannot separate them; ``is`` can.
    This is demonstrated in the mission evidence by MUT-2, which rebinds the
    tracker attribute to a delegating wrapper returning the identical string —
    every string observation stays green and only these assertions red.

    The attributes are read **at assert time**, not captured at import time, so
    a plugin that rebinds a deciding module's attribute is detected.
    """
    assert saas_deciding_module.project_egress_refusal is egress.project_egress_refusal, (
        "specify_cli.saas_client.client.project_egress_refusal is not the object "
        "defined in specify_cli.egress. The SaaS decision point "
        "(client.py::_refuse_unless_project_consents) is bound by value at import "
        "time, so it is still calling whatever object it imported — most likely a "
        "surviving saas_client/egress_consent.py re-export. Every rendered string "
        "would still be correct; that is exactly why this is an identity check."
    )
    assert tracker_deciding_module.project_egress_refusal is egress.project_egress_refusal, (
        "specify_cli.tracker.saas_client.project_egress_refusal is not the object "
        "defined in specify_cli.egress. The tracker decision point "
        "(saas_client.py::_request) is bound by value at import time, so it is "
        "still calling whatever object it imported — most likely a surviving "
        "tracker/egress_consent.py re-export. Every rendered string would still be "
        "correct; that is exactly why this is an identity check."
    )


def test_sc004_clause3_names_are_reachable_and_the_comparison_is_not_self_identity() -> None:
    """Positive control for the assertion above — it must be able to fail.

    Three distinct module objects, three distinct dotted paths. If any of the
    three were an alias of another, the ``is`` comparisons above would be
    trivially true and would prove nothing.
    """
    modules = {
        egress.__name__,
        saas_deciding_module.__name__,
        tracker_deciding_module.__name__,
    }
    assert modules == {
        "specify_cli.egress",
        "specify_cli.saas_client.client",
        "specify_cli.tracker.saas_client",
    }, f"the three names are not three independent module paths: {sorted(modules)}"

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
TRACKER_FRAGMENT = tracker_deciding_module.TRACKER_EGRESS_IDENTIFIER_KINDS


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
    raised or answered with a non-bool".
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
