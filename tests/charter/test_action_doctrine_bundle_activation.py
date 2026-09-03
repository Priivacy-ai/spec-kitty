"""WP02 (spdd-reasons-activation-split-brain, #3838) -- re-derive
``_load_action_doctrine_bundle``'s ``project_directives``/``selected_tactics``/
``selected_paradigms`` from ``pack_context.activated_*`` instead of the stale
``governance.charter.selected_*`` (Decision Record 2, FR-006/007/008/014).

Six red-first cases, none of them smoke tests -- each pins a distinct instance
of the "absent/un-normalized input silently collapses to a wrong value" defect
class (operator ruling, ``reviews/tasks.ruling.md``):

1. ``test_activated_directive_not_in_stale_selected_is_still_delivered`` (FR-007)
   -- silent exclusion: a genuinely ``activated_*`` directive dropped because it
   is not a member of the stale, disjoint ``selected_directives``.
2. ``test_dogfood_shape_activated_ids_widen_the_closure_roots`` (FR-008) --
   silent under-seeding: this repo's own dogfood shape (``selected_*`` all
   ``[]``, ``activated_*`` populated) starves the requires/suggests
   closure-widening ``roots``/``start_urns``.
3. ``test_explicit_empty_project_directives_excludes_everything`` (FR-014) --
   the three-state distinction itself: an EXPLICIT empty ``project_directives``
   must exclude everything, not fall through a bare-truthiness "no filter"
   read.
4. ``test_activated_tactics_and_paradigms_absent_widen_to_full_catalog`` (the
   plan-added sibling fixture) -- an absent (``None``) ``activated_tactics``/
   ``activated_paradigms`` must resolve to the catalog-backed "all built-ins"
   default, never an empty set.
5. ``test_org_required_stem_form_directive_is_normalized_before_union``
   (TASKS-FRESH2-001) -- an org-required stem-form directive id must be
   normalized to its canonical ``DIRECTIVE_NNN`` form before joining the
   ``project_directives`` union.
6. ``test_direct_activated_directives_stem_form_is_normalized`` (analyze-phase
   Finding A1, severity HIGH) -- the SAME normalization requirement, but for a
   stem-form id supplied DIRECTLY via ``pack_context.activated_directives``,
   with no org pack involved -- boundary 1 in the WP's own Union/Exclusion
   Boundary Audit, distinct from case 5's boundary 3.

Design note on FR-014's call boundary: this fixture is deliberately built
against :func:`_classify_artifact_urns` directly rather than through the full
:func:`_load_action_doctrine_bundle` pipeline. Going through the full pipeline
would route ``pack_context.activated_directives=frozenset()`` through
``filter_graph_by_activation``'s OWN (WP01-owned, already-correct) per-ID gate
first, which independently treats an explicit empty set as "exclude
everything" -- so the directive node would never reach ``resolve_context`` at
all, and the assertion "delivers ZERO directives" would trivially hold on BOTH
old and new code for the WRONG reason (a bug-preserving, non-discriminating
fixture -- the exact severity-4 defect class this mission's own charter
throughline forbids). Testing ``_classify_artifact_urns`` directly isolates
the ``is not None``-vs-bare-truthiness guard this case actually exists to pin,
matching the WP's own "why this must fail on a NAIVE fix" reasoning, which is
entirely about that guard.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from charter.activation.action_doctrine_bundle import _load_action_doctrine_bundle
from charter.activation.catalog import load_doctrine_catalog
from charter.activation.context_renderers.delivery_table import _classify_artifact_urns
from charter.activation.pack_context import PackContext
from charter.activation.schemas import DoctrineSelectionConfig
from charter.offering.drg.models import DRGEdge, DRGGraph, DRGNode, NodeKind, Relation

pytestmark = [pytest.mark.fast]

_MISSION_TYPE = "software-dev"
_ACTION = "implement"
_ACTION_URN = f"action:{_MISSION_TYPE}/{_ACTION}"

# Real built-in directives (verified live against packs/built-in/directives/
# for this WP -- not a hermetic id==stem fixture, per NFR-001).
_DIRECTIVE_038_STEM = "038-structured-prompt-boundary"
_DIRECTIVE_038_CANONICAL = "DIRECTIVE_038"
_DIRECTIVE_010_CANONICAL = "DIRECTIVE_010"
_DIRECTIVE_001_STEM = "001-architectural-integrity-standard"
_DIRECTIVE_001_CANONICAL = "DIRECTIVE_001"
_DIRECTIVE_024_STEM = "024-locality-of-change"
_DIRECTIVE_024_CANONICAL = "DIRECTIVE_024"

# Real built-in tactic/paradigm ids (config stem == canonical id for both
# kinds -- verified live, no _normalize_tactic_id/_normalize_paradigm_id
# exists anywhere in src/).
_TACTIC_ID = "adversarial-qa-handoff"
_PARADIGM_ID = "atomic-design"


def _pack_context(
    *,
    activated_directives: frozenset[str] | None = None,
    activated_tactics: frozenset[str] | None = None,
    activated_paradigms: frozenset[str] | None = None,
    activated_kinds: frozenset[str] = frozenset(
        {"directives", "tactics", "paradigms", "styleguides", "toolguides", "procedures"}
    ),
    repo_root: Path,
) -> PackContext:
    return PackContext(
        activated_kinds=activated_kinds,
        activated_mission_types=frozenset({_MISSION_TYPE}),
        pack_roots=(),
        org_pack_names=(),
        repo_root=repo_root,
        activated_directives=activated_directives,
        activated_tactics=activated_tactics,
        activated_paradigms=activated_paradigms,
    )


def _scoped_action_graph(*node_urns: str) -> DRGGraph:
    """An action node with a direct ``scope`` edge to each of *node_urns*.

    Depth-1 scope hops only -- reachability is not the variable under test in
    any of these six cases, the activation/selection derivation is.
    """
    kind_by_prefix = {
        "directive": NodeKind.DIRECTIVE,
        "tactic": NodeKind.TACTIC,
        "paradigm": NodeKind.PARADIGM,
    }
    nodes = [DRGNode(urn=_ACTION_URN, kind=NodeKind.ACTION)]
    edges = []
    for urn in node_urns:
        prefix = urn.split(":", 1)[0]
        nodes.append(DRGNode(urn=urn, kind=kind_by_prefix[prefix]))
        edges.append(DRGEdge(source=_ACTION_URN, target=urn, relation=Relation.SCOPE))
    return DRGGraph(
        schema_version="1.0",
        generated_at="2026-09-03T00:00:00+00:00",
        generated_by="test_action_doctrine_bundle_activation",
        nodes=nodes,
        edges=edges,
    )


def _register_org_pack(repo_root: Path, org_root: Path, *, name: str = "test-org") -> None:
    """Mirror test_action_doctrine_bundle_org_fragment.py's ``_register_pack``."""
    kit = repo_root / ".kittify"
    kit.mkdir(parents=True, exist_ok=True)
    (kit / "config.yaml").write_text(
        yaml.safe_dump(
            {"doctrine": {"org": {"packs": [{"name": name, "local_path": str(org_root)}]}}}
        ),
        encoding="utf-8",
    )


def _write_org_charter(org_root: Path, *, required_directives: list[str]) -> None:
    org_root.mkdir(parents=True, exist_ok=True)
    (org_root / "org-charter.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "1",
                "org_name": "test-org",
                "required_directives": required_directives,
            }
        ),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# 1. FR-007 -- silent exclusion: an activated, DRG-reachable directive dropped
#    because it is not a member of the stale, disjoint selected_directives.
# ---------------------------------------------------------------------------


def test_activated_directive_not_in_stale_selected_is_still_delivered(
    tmp_path: Path,
) -> None:
    """RED on main: ``project_directives`` is built from
    ``doctrine_selection.selected_directives`` only -- ``activated_directives``
    is never consulted for this decision. ``_classify_artifact_urns``'s
    exclusion guard then drops ``DIRECTIVE_038`` because
    ``"DIRECTIVE_038" not in {"DIRECTIVE_010"}`` (verified against the live
    guard, not assumed).
    """
    graph = _scoped_action_graph(f"directive:{_DIRECTIVE_038_CANONICAL}")
    pack_context = _pack_context(
        activated_directives=frozenset({_DIRECTIVE_038_STEM}), repo_root=tmp_path
    )
    stale_selection = DoctrineSelectionConfig(selected_directives=[_DIRECTIVE_010_CANONICAL])

    with (
        patch("charter.activation._drg_helpers.load_validated_graph", return_value=graph),
        # create=True: WP02's fix removes action_doctrine_bundle's own
        # reference to _load_doctrine_selection entirely (replaced by
        # _read_org_required_selections) -- this patch target therefore only
        # exists pre-fix. create=True keeps the SAME test collectible and
        # correct post-fix too: the patch becomes inert (nothing looks the
        # name up any more) and the real activated_*-derived behavior this
        # case asserts on takes over, unaffected by a stale patch target.
        patch(
            "charter.activation.action_doctrine_bundle._load_doctrine_selection",
            return_value=stale_selection,
            create=True,
        ),
    ):
        bundle = _load_action_doctrine_bundle(
            repo_root=tmp_path,
            action=_ACTION,
            effective_depth=2,
            mission_type=_MISSION_TYPE,
            pack_context=pack_context,
        )

    assert _DIRECTIVE_038_CANONICAL in bundle.directive_ids


# ---------------------------------------------------------------------------
# 2. FR-008 -- silent under-seeding: this repo's own dogfood shape
#    (selected_* all []) starves the requires/suggests closure-widening
#    roots/start_urns regardless of what activated_* says.
# ---------------------------------------------------------------------------


def test_dogfood_shape_activated_ids_widen_the_closure_roots(tmp_path: Path) -> None:
    """RED on main: with ``selected_*`` all ``[]`` (this repo's own dogfood
    shape -- no charter.yaml governance section on a bare ``tmp_path``),
    ``project_directives``/``selected_tactics``/``selected_paradigms`` are all
    empty sets on main, so ``roots``'s three generator expressions produce
    ZERO directive/tactic/paradigm URNs regardless of ``activated_*``.
    """
    graph = _scoped_action_graph(
        f"directive:{_DIRECTIVE_038_CANONICAL}",
        f"tactic:{_TACTIC_ID}",
        f"paradigm:{_PARADIGM_ID}",
    )
    pack_context = _pack_context(
        activated_directives=frozenset({_DIRECTIVE_038_STEM}),
        activated_tactics=frozenset({_TACTIC_ID}),
        activated_paradigms=frozenset({_PARADIGM_ID}),
        repo_root=tmp_path,
    )

    with patch("charter.activation._drg_helpers.load_validated_graph", return_value=graph):
        bundle = _load_action_doctrine_bundle(
            repo_root=tmp_path,
            action=_ACTION,
            effective_depth=2,
            mission_type=_MISSION_TYPE,
            pack_context=pack_context,
        )

    assert f"directive:{_DIRECTIVE_038_CANONICAL}" in bundle.roots
    assert f"tactic:{_TACTIC_ID}" in bundle.roots
    assert f"paradigm:{_PARADIGM_ID}" in bundle.roots


# ---------------------------------------------------------------------------
# 3. FR-014 -- the three-state distinction: an EXPLICIT empty
#    project_directives excludes everything, never "no filter".
# ---------------------------------------------------------------------------


def test_explicit_empty_project_directives_excludes_everything() -> None:
    """RED on a naive re-derivation (not necessarily on main as-is -- this
    pins the three-state distinction itself). A naive fix that assigns
    ``pack_context.activated_directives`` straight into ``project_directives``
    and lets ``frozenset()`` fall through the bare-truthiness guard unchanged
    would deliver ALL DRG-reached directives (the guard's
    ``project_directives and ...`` short-circuits False on an empty/falsy
    set, meaning "no filter") -- the OPPOSITE of "nothing activated".

    Tested directly against ``_classify_artifact_urns`` (this WP's own
    exclusion-guard boundary) rather than through the full
    ``_load_action_doctrine_bundle`` pipeline -- see the module docstring's
    design note for why the full pipeline confounds this specific case.
    """
    graph = _scoped_action_graph(f"directive:{_DIRECTIVE_038_CANONICAL}")

    result = _classify_artifact_urns(
        frozenset({f"directive:{_DIRECTIVE_038_CANONICAL}"}),
        graph,
        frozenset(),
    )

    assert result["directives"] == ()


# ---------------------------------------------------------------------------
# 4. Plan-added sibling fixture -- activated_tactics/activated_paradigms
#    ABSENT (None, not []) must widen to the full catalog, never empty sets.
# ---------------------------------------------------------------------------


def test_activated_tactics_and_paradigms_absent_widen_to_full_catalog(
    tmp_path: Path,
) -> None:
    """RED on main, precisely: an absent ``activated_tactics``/
    ``activated_paradigms`` never even reaches this decision on main --
    ``selected_tactics``/``selected_paradigms`` come from
    ``_load_doctrine_selection``'s stale ``selected_*`` reads, which for this
    fixture's shape (nothing authored) are also naturally empty -- so
    ``roots``/``start_urns`` carry ZERO tactic/paradigm URNs on main. A
    fixture that instead asserted "no worse than today" would pass on BOTH
    the buggy main behavior and a correct catalog-widened fix, proving
    nothing -- this asserts the precise, falsifiable catalog-derived outcome
    instead.
    """
    graph = _scoped_action_graph(f"directive:{_DIRECTIVE_038_CANONICAL}")
    pack_context = _pack_context(
        activated_directives=frozenset({_DIRECTIVE_038_STEM}),
        activated_tactics=None,
        activated_paradigms=None,
        repo_root=tmp_path,
    )
    catalog = load_doctrine_catalog()

    with patch("charter.activation._drg_helpers.load_validated_graph", return_value=graph):
        bundle = _load_action_doctrine_bundle(
            repo_root=tmp_path,
            action=_ACTION,
            effective_depth=2,
            mission_type=_MISSION_TYPE,
            pack_context=pack_context,
        )

    root_tactic_ids = {r.split(":", 1)[1] for r in bundle.roots if r.startswith("tactic:")}
    root_paradigm_ids = {r.split(":", 1)[1] for r in bundle.roots if r.startswith("paradigm:")}

    assert root_tactic_ids == set(catalog.tactics), (
        f"expected every catalog tactic id as a root URN "
        f"({len(catalog.tactics)} expected, got {len(root_tactic_ids)})"
    )
    assert root_paradigm_ids == set(catalog.paradigms), (
        f"expected every catalog paradigm id as a root URN "
        f"({len(catalog.paradigms)} expected, got {len(root_paradigm_ids)})"
    )


# ---------------------------------------------------------------------------
# 5. TASKS-FRESH2-001 -- org-required stem-form directive normalization.
# ---------------------------------------------------------------------------


def test_org_required_stem_form_directive_is_normalized_before_union(
    tmp_path: Path,
) -> None:
    """Pins TASKS-FRESH2-001 (severity 4): each
    ``_read_org_required_selections()["directives"]`` entry must be normalized
    via ``_normalize_directive_id`` before it joins the ``project_directives``
    union. ``activated_directives`` is left absent/None on the project side,
    so ``project_directives``'s only content comes from this org-required
    union.

    NOTE on this fixture's RED-ness against literal current ``main``: reading
    ``org_pack_discovery._load_doctrine_selection`` live shows it ALREADY
    unions raw org-required stems into ``selected_directives`` internally,
    and ``_load_action_doctrine_bundle``'s existing single
    ``_normalize_directive_id`` comprehension over the merged
    ``selected_directives`` set normalizes them "for free" today -- so this
    exact fixture, run through the current unmodified pipeline, is observed
    GREEN, not red (see this WP's final report for the live-run evidence).
    The severity-4 finding this fixture pins is specific to what happens once
    ``_load_doctrine_selection`` is replaced by a direct
    ``_read_org_required_selections`` call (T009 step 2) -- an omit-the-
    normalization-line implementation of THAT replacement is what reddens
    here; that intermediate state was exercised and captured red before the
    normalization line was added (see the report).
    """
    graph = _scoped_action_graph(f"directive:{_DIRECTIVE_001_CANONICAL}")
    org_root = tmp_path.parent / "org-pack-required"
    _write_org_charter(org_root, required_directives=[_DIRECTIVE_001_STEM])
    _register_org_pack(tmp_path, org_root)
    pack_context = _pack_context(activated_directives=None, repo_root=tmp_path)

    with patch("charter.activation._drg_helpers.load_validated_graph", return_value=graph):
        bundle = _load_action_doctrine_bundle(
            repo_root=tmp_path,
            action=_ACTION,
            effective_depth=2,
            mission_type=_MISSION_TYPE,
            pack_context=pack_context,
        )

    assert _DIRECTIVE_001_CANONICAL in bundle.directive_ids
    assert f"directive:{_DIRECTIVE_001_CANONICAL}" in bundle.roots
    assert f"directive:{_DIRECTIVE_001_STEM}" not in bundle.roots


# ---------------------------------------------------------------------------
# 6. Analyze-phase Finding A1 (severity HIGH) -- direct-path stem-form
#    directive normalization, boundary 1 (distinct from case 5's boundary 3).
# ---------------------------------------------------------------------------


def test_direct_activated_directives_stem_form_is_normalized(tmp_path: Path) -> None:
    """Boundary 1 in the Union/Exclusion Boundary Audit: ``project_directives``
    derivation DIRECTLY from ``pack_context.activated_directives`` (T009 step
    1), no org-pack involved -- distinct from case 5 above, which only
    exercises stem-form normalization via the SEPARATE org-required-union
    path (boundary 3). A T009 step 1 implementation that dropped
    ``_normalize_directive_id(d)`` from the comprehension -- assigning
    ``directives_arg`` straight into ``project_directives`` unnormalized --
    would pass every other case in this file untouched, because none of them
    puts a stem-form id on this specific direct-assignment boundary.

    RED on literal current main, via ``bundle.roots``: main's
    ``project_directives`` is built solely from the stale (here, empty)
    ``selected_directives`` -- ``pack_context.activated_directives`` is never
    consulted for it at all -- so ``roots`` carries no ``directive:...`` URN
    from this fixture's activation on main regardless of stem-vs-canonical
    form. ``directive_ids`` alone would NOT discriminate here (main's empty,
    falsy ``project_directives`` also means "no filter", so
    ``filter_graph_by_activation``'s own gate already lets the real,
    activated ``DIRECTIVE_024`` node through to ``resolve_context``, and the
    downstream bare-truthiness guard never excludes it either) -- ``roots``
    is the assertion that actually discriminates.
    """
    graph = _scoped_action_graph(f"directive:{_DIRECTIVE_024_CANONICAL}")
    pack_context = _pack_context(
        activated_directives=frozenset({_DIRECTIVE_024_STEM}), repo_root=tmp_path
    )

    with patch("charter.activation._drg_helpers.load_validated_graph", return_value=graph):
        bundle = _load_action_doctrine_bundle(
            repo_root=tmp_path,
            action=_ACTION,
            effective_depth=2,
            mission_type=_MISSION_TYPE,
            pack_context=pack_context,
        )

    assert f"directive:{_DIRECTIVE_024_CANONICAL}" in bundle.roots
    assert f"directive:{_DIRECTIVE_024_STEM}" not in bundle.roots
    assert _DIRECTIVE_024_CANONICAL in bundle.directive_ids
