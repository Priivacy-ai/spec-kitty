"""Per-channel reachability as asserted named sets (WP08, contract §3 R-1..R-6).

Reachability is a **membership** contract, not a cardinality one: a newly
unreachable activated artefact fails a set-equality naming *itself*, where a
count could only nudge an integer. The two channels are measured by two
different traversals, both **called** from :mod:`doctrine.drg.reachability` (no
walk is reimplemented here):

* **action channel** — :func:`action_channel_reachable`, which calls
  :func:`doctrine.drg.query.resolve_context`. Pinned at ``d=1`` (compact, the
  steady state, the stricter measure) and ``d=2`` (bootstrap). The measured
  spread between them is exactly 7 nodes (R-2).
* **profile channel** — :func:`profile_channel_reachable`, a distinct
  ``walk_edges`` over ``{requires, specializes_from}``. Seeding profiles into
  ``resolve_context`` instead would measure zero (R-3), a fact this module pins
  directly.

C-009 (WP06): reconciling the activation *store* form (``025-boy-scout-rule``)
to the DRG *node* form (``directive:DIRECTIVE_025``) moves the measured
"activated-but-unreachable" count by 25 without making anything reachable. Those
25 store-form slugs are the ``not_a_node`` partition; the pinned sets below are
all in node form, so that swing is excluded from every progress claim by
construction — and asserted separately via ``normalization_delta``.

The named sets are computed empirically against the shipped built-in graph and
the project's resolved activation store; regenerate them with the same three
calls this module makes if the graph or the activation config legitimately
changes, and move any golden count only with a composition-ledger row (NFR-004).
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import pytest

from charter import pack_context
from charter.pack_context import (
    charter_activated_urns,
    partition_activated_unreachable,
)
from doctrine.drg.loader import load_built_in_graph
from doctrine.drg.models import DRGGraph, Relation
from doctrine.drg.query import resolve_context
from doctrine.drg.reachability import (
    PROFILE_CHANNEL_RELATIONS,
    action_channel_reachable,
    action_seed_urns,
    agent_profile_seed_urns,
    profile_channel_reachable,
)
from reachability_fixtures.nominal_wiring import (
    ACTION_URN,
    IN_SCOPE_DIRECTIVE,
    NOMINALLY_WIRED,
    PROPERLY_WIRED,
    UNREACHABLE_SOURCE,
    incident_urns,
    nominal_wiring_graph,
)

pytestmark = [pytest.mark.doctrine, pytest.mark.fast, pytest.mark.corpus]

#: Repo root — tests/doctrine/drg/ is three levels down.
_REPO_ROOT: Path = Path(__file__).resolve().parents[3]

#: ``resolve_context`` depths: compact (stricter) and bootstrap.
_ACTION_D1_DEPTH = 1
_ACTION_D2_DEPTH = 2

#: The C-009 normalization swing (WP06): activated directive slugs whose STORE
#: form is not a graph node while their NORMALIZED form is. Reconciling the form
#: is not reachability progress and is excluded from SC-005. Bumped 25 -> 31 for
#: the writing-comms/diagramming activation (commit 9a99801f1, #3009): six more
#: activated directives whose store slug is not a node while their normalized form
#: is -- the four numbered 047-050 (``NNN-...`` -> ``DIRECTIVE_NNN``) and the two
#: slug hubs use-c4-model-techniques / reconcile-change-scope-tensions
#: (``slug`` -> ``USE_C4_MODEL_TECHNIQUES`` / ``RECONCILE_CHANGE_SCOPE_TENSIONS``,
#: now that id_normalizer folds hyphens to underscores).
_NORMALIZATION_DELTA = 31

#: The measured d=1 <-> d=2 action-channel spread (R-2): d=2 (bootstrap) reaches
#: exactly 10 more nodes than d=1 (compact), so d=2's unreachable set is d=1's
#: minus those 10. Was 7 before #3063 family-D; the ACCEPT-DELIVERY wiring adds
#: three members that are reached only at d=2 (they were in BOTH unreachable sets
#: before, so they sit in D1 - D2 now): ``tactic:reverse-speccing`` and
#: ``tactic:test-to-system-reconstruction`` (via the brownfield-onboarding suggests
#: chain, which lands inside the d=2 bound but not d=1) and
#: ``styleguide:mutation-aware-test-design`` (a 2-hop suggests chain out of the
#: action-scoped DIRECTIVE_030). The pre-existing 7 are unchanged.
_ACTION_D1_D2_SPREAD = 10

# ---------------------------------------------------------------------------
# WP03 SUPERSEDING NOTE (mission ``doctrine-delivery-activation-01KYQVQK``)
# ---------------------------------------------------------------------------
# The per-family narratives below were authored by the PRIOR mission
# (``doctrine-delivery-reachability-01KYMXD6``) when the profile channel walked
# only {requires, specializes_from}. Their PROFILE-channel asides — "the profile
# channel is unchanged", "_PROFILE_UNREACHABLE unchanged (153)", "measured
# 39->39", "_PROFILE_RESCUES 4 -> 2", and family E's "profile channel walks
# {requires, specializes_from} only" — describe that PRE-WP01 state and are now
# SUPERSEDED. WP01 (FR-001) added ``Relation.SUGGESTS`` to
# ``PROFILE_CHANNEL_RELATIONS``, so the profile channel now follows ``suggests``:
# ``_PROFILE_UNREACHABLE`` is 59 (was 153; 60 until mission
# ``rehome-writing-comms-doctrine-01KZ9V0S`` shipped the DIRECTIVE_050 -> secure-
# design-checklist ``suggests`` edge required by the new ``minutes-maker-mahad``
# profile — see that mission's ledger section in the wiring table) and
# ``_PROFILE_RESCUES`` is 30 (was 2).
# The ACTION-channel claims in these narratives (``_ACTION_UNREACHABLE_D1``/``D2``
# and their family moves) are UNCHANGED and remain accurate — WP02's topology is
# action-inert. See the reconciled ``_PROFILE_UNREACHABLE`` / ``_PROFILE_RESCUES``
# docstrings and the "profile-channel walk-activation" ledger in
# ``docs/plans/doctrine/delivery-reachability-wiring-table.md`` for the live
# profile-channel record. These historical narratives are left in place (not
# edited in situ) to keep the prior mission's action-channel ledger diff legible.

#: The common-docs cluster WP09 wires (mission doctrine-delivery-reachability,
#: T050, FR-015). One authored `scope` edge —
#: ``action:documentation/generate --scope--> directive:DIRECTIVE_042`` — makes
#: DIRECTIVE_042 action-reachable, and 042's pre-existing ``requires``/``suggests``
#: edges then deliver the asset, the styleguide and the four common-docs tactics
#: transitively. These six leave BOTH ``_ACTION_UNREACHABLE_D1`` and
#: ``_ACTION_UNREACHABLE_D2`` (NFR-004 ledger row: the two golden membership sets
#: each shrink by exactly these six; the d1<->d2 spread stays 7 because the same
#: members leave both, and ``_PROFILE_UNREACHABLE`` / ``_PROFILE_RESCUES`` are
#: unaffected — the profile channel is unchanged and all six are profile-
#: unreachable too). The edge's source is an ``action`` node, so it satisfies
#: C-007(b)'s second clause without needing its own reachability measured, and
#: 042's ``scope:`` text ("whenever a documentation file ... is created") attests
#: the relationship to ``documentation/generate``'s ``write_docs`` step (C-007a).
#: ``asset:common-docs-structural-lint`` is delivered but not itself activated, so
#: it is proven reachable directly rather than via the activated-set subtraction.
_COMMON_DOCS_WIRED: frozenset[str] = frozenset(
    {
        "directive:DIRECTIVE_042",
        "styleguide:common-docs",
        "tactic:common-docs-curation",
        "tactic:common-docs-find",
        "tactic:common-docs-scaffold",
        "tactic:common-docs-write",
    }
)

#: The delivery target the wired cluster exists to reach (WP10/WP11 ship assets).
_COMMON_DOCS_ASSET = "asset:common-docs-structural-lint"

#: The DDD family #3063 family-A wires (operator interview outcome, C-007(a)
#: satisfied by operator ruling). One authored ``scope`` edge —
#: ``action:software-dev/specify --scope--> paradigm:domain-driven-design`` —
#: makes the DDD paradigm action-reachable, and the paradigm's ten authored
#: ``requires`` edges (to the strategic-design + tactical DDD members whose own
#: text attests DDD membership) then deliver the family transitively. Every
#: member here becomes action-reachable at BOTH depths after the edge lands;
#: ``tactic:strategic-domain-classification`` was already action-reachable
#: (via ``tactic:paula-patterns-architecture-scout-review``), so it is delivered
#: too but leaves neither ``_ACTION_UNREACHABLE`` set. NOTE the specify edge is
#: ``scope`` NOT ``suggests``: measured with the WP08 helper, a ``suggests`` edge
#: whose SOURCE is an action node is inert — ``resolve_context`` walks ``suggests``
#: only FROM scope-resolved artifacts, never from the action node — so only a
#: ``scope`` edge changes action reachability (the WP09 precedent,
#: ``action:documentation/generate --scope--> directive:DIRECTIVE_042``).
#:
#: NFR-004 ledger for this move: ``_ACTION_UNREACHABLE_D1`` and
#: ``_ACTION_UNREACHABLE_D2`` each lose the SAME twelve members —
#: ``paradigm:domain-driven-design``; its two pre-existing ``directive_refs``
#: ``DIRECTIVE_031``/``DIRECTIVE_032`` (delivered once the paradigm is scoped);
#: and the nine newly-required members that were unreachable
#: (``styleguide:aggregate-design-rules`` + the eight DDD tactics minus
#: ``strategic-domain-classification``, which was already reachable). Because the
#: same twelve leave both, the d1<->d2 spread stays 7. ``_PROFILE_UNREACHABLE`` is
#: unchanged (the profile channel is untouched: the three profile edges are
#: ``suggests``, which that channel does not follow, and the DDD paradigm stays
#: profile-unreachable so its new ``requires`` edges deliver nothing there —
#: measured 39->39). ``_PROFILE_RESCUES`` (defined as
#: ``_ACTION_UNREACHABLE_D2 - _PROFILE_UNREACHABLE``) therefore loses the four of
#: its members that just entered the action channel: ``DIRECTIVE_031``,
#: ``DIRECTIVE_032``, ``anti-corruption-layer`` and ``domain-event-capture`` — the
#: action channel now covers them, so they are no longer profile-only rescues.
#: Orphan sets are unaffected (every endpoint was already edge-incident).
_DDD_FAMILY_WIRED: frozenset[str] = frozenset(
    {
        "paradigm:domain-driven-design",
        "tactic:bounded-context-identification",
        "tactic:context-mapping-classification",
        "tactic:context-boundary-inference",
        "tactic:bounded-context-canvas-fill",
        "tactic:aggregate-boundary-design",
        "tactic:entity-value-object-classification",
        "tactic:domain-event-capture",
        "tactic:anti-corruption-layer",
        "tactic:strategic-domain-classification",
        "styleguide:aggregate-design-rules",
    }
)

#: The TESTING / BDD / MUTATION family #3063 family-D delivers (operator interview
#: outcome + ACCEPT-DELIVERY ruling 2026-07-29). Unlike families B/C, family D is
#: reachability-affecting: two hubs are EXISTING action-scoped directives, so their
#: outbound ``suggests`` edges ARE walked and DELIVER at implement/review.
#: ``directive:DIRECTIVE_034`` (test-first) and ``directive:DIRECTIVE_030`` (test-
#: quality gate) are both ``scope``-linked from ``action:software-dev/implement``
#: and ``action:software-dev/review``; ``resolve_context`` step 3 walks ``suggests``
#: from those scope-resolved artifacts.
#:
#: Delivered at BOTH d=1 and d=2 (leave both ``_ACTION_UNREACHABLE`` sets) — five
#: from DIRECTIVE_034 (development-bdd, atdd-adversarial-acceptance,
#: specification-by-example, formalized-constraint-testing, example-mapping-
#: workshop) and two from DIRECTIVE_030 (adversarial-qa-handoff,
#: work-package-completion-validation):
_TESTING_DELIVERED_AT_D1: frozenset[str] = frozenset(
    {
        "tactic:development-bdd",
        "tactic:atdd-adversarial-acceptance",
        "paradigm:specification-by-example",
        "tactic:formalized-constraint-testing",
        "procedure:example-mapping-workshop",
        "tactic:adversarial-qa-handoff",
        "tactic:work-package-completion-validation",
    }
)

#: Delivered at the bootstrap depth d=2 ONLY (leave ``_ACTION_UNREACHABLE_D2`` but
#: NOT ``_ACTION_UNREACHABLE_D1``; they move into the d1<->d2 spread):
#: ``reverse-speccing`` / ``test-to-system-reconstruction`` via the
#: ``paradigm:brownfield-onboarding`` suggests chain, and
#: ``styleguide:mutation-aware-test-design`` via a 2-hop suggests chain out of the
#: action-scoped DIRECTIVE_030.
_TESTING_DELIVERED_AT_D2_ONLY: frozenset[str] = frozenset(
    {
        "tactic:reverse-speccing",
        "tactic:test-to-system-reconstruction",
        "styleguide:mutation-aware-test-design",
    }
)

#: Every artefact family-D makes action-reachable (the union). The BDD + test-
#: quality members action-reachable at implement/review — the acceptance target of
#: the ACCEPT-DELIVERY ruling. The mutation hub (a NEW non-scoped directive) and the
#: DIRECTIVE_041 fan-out stay UNREACHABLE (their members remain in the deferred set);
#: the profile->hub and event-storming edges are ``suggests`` on the profile channel
#: and inert. ``_PROFILE_UNREACHABLE`` is unchanged (153); ``_PROFILE_RESCUES``
#: 4 -> 2 because development-bdd and reverse-speccing entered the action channel.
_TESTING_BDD_MUTATION_WIRED: frozenset[str] = (
    _TESTING_DELIVERED_AT_D1 | _TESTING_DELIVERED_AT_D2_ONLY
)

#: #3063 family-E (ANALYSIS / TERMINOLOGY / REASONS-CANVAS family) is INERT --
#: it moves NO reachability pin (measured with the WP08 helper, not assumed). Its
#: nine overlay ``suggests`` edges all originate at either
#: ``agent_profile:architect-alphonso`` (the profile channel walks {requires,
#: specializes_from} only, so profile--suggests-->X is never followed) or an
#: action-UNREACHABLE tactic/toolguide (``terminology-extraction-mapping``,
#: ``contextive``, ``terminology-guard`` are all pinned in
#: ``_ACTION_UNREACHABLE_D1``/``D2`` below, and ``resolve_context`` walks
#: ``suggests`` only FROM scope-resolved artifacts). The two reinforcement edges
#: point INTO the already-action-reachable DDD / brownfield paradigms, which does
#: not make their source reachable. So ``_ACTION_UNREACHABLE_D1``/``D2``,
#: ``_PROFILE_UNREACHABLE`` and ``_PROFILE_RESCUES`` are all UNCHANGED by family E
#: (composition-only: +9 ``suggests`` edges, 0 new artefacts). The delivery-
#: reachability DEFERRED set stays at 50 -- no artefact leaves it. See
#: ``docs/plans/doctrine/delivery-reachability-wiring-table.md`` (Family E).

#: Activated artefacts (node form) NOT reachable via the action channel at
#: d=1 (compact/steady-state). Membership, not cardinality (R-4).
_ACTION_UNREACHABLE_D1: frozenset[str] = frozenset(
    {
        "directive:DIRECTIVE_035",
        "directive:DIRECTIVE_038",
        "directive:DIRECTIVE_039",
        "directive:DIRECTIVE_044",
        "paradigm:atomic-design",
        "paradigm:behaviour-driven-development",
        "paradigm:c4-incremental-detail-modeling",
        "paradigm:structured-prompt-driven-development",
        "procedure:bdd-scenario-lifecycle",
        "procedure:documentation-gap-prioritization",
        "procedure:drill-down-documentation",
        "procedure:event-storming-discovery",
        "procedure:migrate-project-guidance-to-spec-kitty-charter",
        "styleguide:adversarial-squad-cadence",
        "styleguide:deployable-skill-authoring",
        "styleguide:java-conventions",
        "styleguide:mutation-aware-test-design",
        "styleguide:planning-and-tracking",
        "styleguide:reasons-canvas-writing",
        "tactic:analysis-extract-before-interpret",
        "tactic:architecture-diagram-review-checklist",
        "tactic:atomic-design-review-checklist",
        "tactic:atomic-state-ownership",
        "tactic:c4-zoom-in-architecture-documentation",
        "tactic:canonical-source-unification",
        "tactic:chain-of-responsibility-rule-pipeline",
        "tactic:code-documentation-analysis",
        "tactic:compositional-stream-boundaries",
        "tactic:cross-cutting-state-via-store",
        "tactic:mutation-testing-workflow",
        "tactic:occurrence-classification-workflow",
        "tactic:ownership-map-leeway",
        "tactic:pr-agent-worktree-isolation",
        "tactic:reasons-canvas-fill",
        "tactic:reasons-canvas-review",
        "tactic:refactoring-conditional-to-strategy",
        "tactic:refactoring-encapsulate-record",
        "tactic:refactoring-encapsulate-variable",
        "tactic:refactoring-extract-first-order-concept",
        "tactic:refactoring-move-field",
        "tactic:refactoring-move-method",
        "tactic:refactoring-state-pattern-for-behavior",
        "tactic:refactoring-strangler-fig",
        "tactic:reference-architectural-patterns",
        "tactic:reverse-speccing",
        "tactic:secure-regex-catastrophic-backtracking",
        "tactic:terminology-extraction-mapping",
        "tactic:test-minimisation",
        "tactic:test-readability-clarity-check",
        "tactic:test-to-system-reconstruction",
        "tactic:zombies-tdd",
        "toolguide:contextive",
        "toolguide:github-tracker",
        "toolguide:maven-review-checks",
        "toolguide:mermaid-diagramming",
        "toolguide:plantuml-diagramming",
        "toolguide:python-mutation-tools",
        "toolguide:python-review-checks",
        "toolguide:terminology-guard",
        "toolguide:typescript-mutation-tools",
        # Writing-comms/diagramming activation (commit 9a99801f1, #3009): these
        # seventeen newly-activated artefacts are reached by no action-channel
        # traversal at this depth. All are in canonical DRG node form (the two
        # slug-hub directives normalize to their UPPER_SNAKE node id, not the old
        # hyphenated store slug -- see the id_normalizer fix). Seven of them
        # (DIRECTIVE_047-050, quadruple-a-test-format, writing-audience-catalog,
        # USE_C4_MODEL_TECHNIQUES) ARE rescued by the profile channel (see
        # _PROFILE_RESCUES); the other ten are unreachable from BOTH channels and
        # are the tracked #3009 debt the deferred A2 orphan-wiring doctrine mission
        # will wire with real inbound edges.
        "directive:DIRECTIVE_047",
        "directive:DIRECTIVE_048",
        "directive:DIRECTIVE_049",
        "directive:DIRECTIVE_050",
        "directive:RECONCILE_CHANGE_SCOPE_TENSIONS",
        "directive:USE_C4_MODEL_TECHNIQUES",
        "procedure:glossary-maintenance-workflow",
        "styleguide:divio-type-discipline",
        "styleguide:docs-accessibility",
        "styleguide:docs-freshness-sla",
        "styleguide:plain-language",
        "styleguide:professional-communications",
        "styleguide:publication-authority",
        "styleguide:quadruple-a-test-format",
        "styleguide:research-citation-discipline",
        "tactic:dialectic-research",
        "tactic:writing-audience-catalog",
    }
)

#: Activated artefacts (node form) NOT reachable via the action channel at
#: d=2 (bootstrap). A strict subset of the d=1 set (bootstrap reaches more).
_ACTION_UNREACHABLE_D2: frozenset[str] = frozenset(
    {
        "directive:DIRECTIVE_035",
        "directive:DIRECTIVE_038",
        "directive:DIRECTIVE_039",
        "directive:DIRECTIVE_044",
        "paradigm:atomic-design",
        "paradigm:c4-incremental-detail-modeling",
        "paradigm:structured-prompt-driven-development",
        "procedure:documentation-gap-prioritization",
        "procedure:drill-down-documentation",
        "procedure:event-storming-discovery",
        "procedure:migrate-project-guidance-to-spec-kitty-charter",
        "styleguide:deployable-skill-authoring",
        "styleguide:java-conventions",
        "styleguide:reasons-canvas-writing",
        "tactic:analysis-extract-before-interpret",
        "tactic:architecture-diagram-review-checklist",
        "tactic:atomic-design-review-checklist",
        "tactic:atomic-state-ownership",
        "tactic:c4-zoom-in-architecture-documentation",
        "tactic:canonical-source-unification",
        "tactic:chain-of-responsibility-rule-pipeline",
        "tactic:code-documentation-analysis",
        "tactic:compositional-stream-boundaries",
        "tactic:cross-cutting-state-via-store",
        "tactic:mutation-testing-workflow",
        "tactic:occurrence-classification-workflow",
        "tactic:ownership-map-leeway",
        "tactic:pr-agent-worktree-isolation",
        "tactic:reasons-canvas-fill",
        "tactic:reasons-canvas-review",
        "tactic:refactoring-encapsulate-record",
        "tactic:refactoring-encapsulate-variable",
        "tactic:refactoring-extract-first-order-concept",
        "tactic:refactoring-move-field",
        "tactic:refactoring-move-method",
        "tactic:refactoring-state-pattern-for-behavior",
        "tactic:refactoring-strangler-fig",
        "tactic:reference-architectural-patterns",
        "tactic:secure-regex-catastrophic-backtracking",
        "tactic:terminology-extraction-mapping",
        "tactic:test-readability-clarity-check",
        "tactic:zombies-tdd",
        "toolguide:contextive",
        "toolguide:github-tracker",
        "toolguide:maven-review-checks",
        "toolguide:mermaid-diagramming",
        "toolguide:plantuml-diagramming",
        "toolguide:python-mutation-tools",
        "toolguide:terminology-guard",
        "toolguide:typescript-mutation-tools",
        # Writing-comms/diagramming activation (commit 9a99801f1, #3009): the same
        # seventeen additions as _ACTION_UNREACHABLE_D1 (canonical node form) -- all
        # seventeen remain action-unreachable at d=2 too, so the d1<->d2 spread is
        # unchanged (10) and D2 stays a subset of D1. See the D1 block for the
        # debt/rescue split.
        "directive:DIRECTIVE_047",
        "directive:DIRECTIVE_048",
        "directive:DIRECTIVE_049",
        "directive:DIRECTIVE_050",
        "directive:RECONCILE_CHANGE_SCOPE_TENSIONS",
        "directive:USE_C4_MODEL_TECHNIQUES",
        "procedure:glossary-maintenance-workflow",
        "styleguide:divio-type-discipline",
        "styleguide:docs-accessibility",
        "styleguide:docs-freshness-sla",
        "styleguide:plain-language",
        "styleguide:professional-communications",
        "styleguide:publication-authority",
        "styleguide:quadruple-a-test-format",
        "styleguide:research-citation-discipline",
        "tactic:dialectic-research",
        "tactic:writing-audience-catalog",
    }
)

#: Activated artefacts NOT reachable via the profile channel (``walk_edges``
#: over {requires, specializes_from, suggests} from every activated agent
#: profile). The profile channel is a second entry vector, so some
#: action-doctrine is legitimately outside it; the load-bearing fact is the
#: *difference* from the action set below, which names the artefacts the profile
#: channel rescues.
#:
#: WP03 (mission ``doctrine-delivery-activation-01KYQVQK``) reconciliation:
#: 153 → 60. WP01 added ``Relation.SUGGESTS`` to ``PROFILE_CHANNEL_RELATIONS``
#: (FR-001), so the unbounded ``walk_edges`` closure now follows the soft-
#: recommendation web out of every activated profile. 93 members left this set —
#: they became profile-reachable via a ``suggests`` chain from an activated
#: profile. Mission ``rehome-writing-comms-doctrine-01KZ9V0S`` then removed one
#: more (60 → 59): ``tactic:secure-design-checklist`` became profile-reachable via
#: the new ``agent_profile:minutes-maker-mahad`` --requires--> ``directive:DIRECTIVE_050``
#: --suggests--> ``tactic:secure-design-checklist`` chain (both edges authored in that
#: mission's frontmatter). It is NOT a ``_PROFILE_RESCUES`` member (it is action-
#: reachable at d=2, so it is absent from ``_ACTION_UNREACHABLE_D2`` and never
#: entered ``_ACTION_UNREACHABLE_D2 − _PROFILE_UNREACHABLE``); the rescues set is
#: unchanged. Ledger row: that mission's section in the wiring table below.
#: The per-member composition ledger (which member, via which family/
#: edge, WP01 vs WP02) lives in
#: ``docs/plans/doctrine/delivery-reachability-wiring-table.md`` under the
#: "profile-channel walk-activation" ledger; the 30 members that this move pushes
#: into ``_PROFILE_RESCUES`` are cross-checked against that ledger by
#: ``test_profile_rescues_have_ledger_coverage`` below.
#:
#: NFR-002 REVIEW-GATE NOTE (D18): this frozenset is a hardcoded literal asserted
#: ``measured == pin`` — the test greens the instant a value is pasted in,
#: whether or not the value is *correct*. That is fundamentally different from a
#: CI-counted golden. The sole non-delegable correctness gate for these numbers
#: is the reviewer's per-member ledger-vs-diff comparison against the wiring
#: table: every member that entered or left this set must trace to a ledger row
#: naming the responsible edge/WP. A pin change with no matching ledger row is a
#: hard reject regardless of whether this test is green.
#:
#: WP03 reconciliation (mission ``supply-chain-security-checks-layer-01KZBFBS``,
#: T009-T012): 60 -> 58. ``tactic:dependency-hygiene`` and
#: ``tactic:secure-design-checklist`` leave this set. Six of the seven profiles
#: bound in WP03 (``architect-alphonso``, ``frontend-freddy``,
#: ``implementer-ivan``, ``java-jenny``, ``node-norris``, ``python-pedro``) now
#: carry a direct ``agent_profile --requires--> tactic:dependency-hygiene`` edge
#: (from each profile's ``tactic-references``), so the profile channel reaches
#: it directly for the first time. That in turn makes
#: ``tactic:dependency-hygiene --suggests--> tactic:secure-design-checklist``
#: (a pre-existing edge, unchanged by this WP) walkable, so
#: ``secure-design-checklist`` is reached transitively. Neither member moves
#: into ``_PROFILE_RESCUES`` (unchanged at 30): both were already
#: action-channel-reachable at d=2, so they were never action-d2-unreachable
#: candidates for rescue. ``directive:DIRECTIVE_051`` and
#: ``tactic:supply-chain-install-safety`` (also newly profile-required by this
#: WP) are absent from both this set and the activation store — they are not
#: yet charter-activated, so they are outside this pin's scope entirely.
_PROFILE_UNREACHABLE: frozenset[str] = frozenset(
    {
        "directive:DIRECTIVE_029",
        "directive:DIRECTIVE_033",
        "directive:DIRECTIVE_035",
        "directive:DIRECTIVE_038",
        "directive:DIRECTIVE_039",
        # DIRECTIVE_042 and the common-docs cluster (styleguide:common-docs +
        # the four common-docs-* tactics) left this pin when DIRECTIVE_047 (the
        # audience-metadata directive, mission common-docs-convergence) was
        # wired into the built-in graph: 047 ``requires`` DIRECTIVE_042 and
        # ``suggests`` styleguide:common-docs, and 042 then delivers the cluster
        # transitively. The profile channel follows ``suggests`` (WP01), so all
        # six became profile-reachable via real authored edges — not C-009
        # normalization — so they are dropped here (NFR-004: real wiring shrinks
        # the pin).
        "directive:DIRECTIVE_046",
        "paradigm:atomic-design",
        "paradigm:deep-module-design",
        "paradigm:structured-prompt-driven-development",
        "procedure:disciplined-defect-diagnosis",
        "procedure:documentation-gap-prioritization",
        "procedure:domain-aware-decision-interview",
        "procedure:issue-triage-state-machine",
        "procedure:migrate-project-guidance-to-spec-kitty-charter",
        "procedure:mission-wrap-up-sequence",
        "procedure:refactoring",
        "procedure:test-first-bug-fixing",
        "styleguide:deployable-skill-authoring",
        "styleguide:java-conventions",
        "tactic:analysis-extract-before-interpret",
        "tactic:atomic-design-review-checklist",
        "tactic:atomic-state-ownership",
        "tactic:avoid-gold-plating",
        "tactic:boring-code-review",
        "tactic:chain-of-responsibility-rule-pipeline",
        # common-docs-{curation,find,scaffold,write} dropped — see the
        # DIRECTIVE_047 note above; the cluster is now profile-reachable.
        "tactic:compositional-stream-boundaries",
        "tactic:cross-cutting-state-via-store",
        "tactic:deepening-opportunity-assessment",
        "tactic:documentation-curation-audit",
        "tactic:easy-to-change",
        "tactic:focused-function-complexity-check",
        "tactic:generated-code-stewardship",
        "tactic:interface-variation-design",
        "tactic:locality-of-change",
        "tactic:reasons-canvas-fill",
        "tactic:reasons-canvas-review",
        "tactic:refactoring-change-function-declaration",
        "tactic:refactoring-combine-functions-into-transform",
        "tactic:refactoring-consolidate-conditional-expression",
        "tactic:refactoring-extract-class-by-responsibility-split",
        "tactic:refactoring-guard-clauses-before-polymorphism",
        "tactic:refactoring-inline-temp",
        "tactic:refactoring-introduce-null-object",
        "tactic:refactoring-replace-magic-number-with-symbolic-constant",
        "tactic:refactoring-replace-temp-with-query",
        "tactic:refactoring-retry-pattern",
        "tactic:reference-architectural-patterns",
        "tactic:requirements-validation-workflow",
        "tactic:secure-regex-catastrophic-backtracking",
        "tactic:testing-select-appropriate-level",
        "toolguide:git-agent-commit-signing",
        "toolguide:maven-review-checks",
        # Writing-comms/diagramming activation (commit 9a99801f1, #3009): ten of
        # the seventeen newly-activated artefacts are unreachable from the profile
        # channel too. These ten (action-d2-unreachable AND profile-unreachable)
        # are the true "activating cascades to nothing" #3009 debt the deferred A2
        # orphan-wiring mission will wire. The other seven action-d2-unreachable
        # additions ARE profile-reachable and appear in _PROFILE_RESCUES instead
        # (USE_C4_MODEL_TECHNIQUES is one of them -- diagram-daisy requires it -- so
        # it is NOT listed here).
        "directive:RECONCILE_CHANGE_SCOPE_TENSIONS",
        "procedure:glossary-maintenance-workflow",
        "styleguide:divio-type-discipline",
        "styleguide:docs-accessibility",
        "styleguide:docs-freshness-sla",
        "styleguide:plain-language",
        "styleguide:professional-communications",
        "styleguide:publication-authority",
        "styleguide:research-citation-discipline",
        "tactic:dialectic-research",
    }
)

#: Activated artefacts the profile channel reaches that the action channel at
#: d=2 does NOT — i.e. ``_ACTION_UNREACHABLE_D2 - _PROFILE_UNREACHABLE``. Proof
#: that the profile channel is a genuine, distinct entry vector (R-3): these
#: artefacts reach an agent only because a profile ``requires``, ``suggests`` or
#: ``specializes_from`` them.
#:
#: WP03 reconciliation (mission ``doctrine-delivery-activation-01KYQVQK``): 2 → 30.
#: ``_ACTION_UNREACHABLE_D2`` is measured-unchanged at 50 (WP02's Family A/B/C
#: topology is action-inert), but WP01's ``suggests`` walk extension shrank
#: ``_PROFILE_UNREACHABLE`` 153 → 60, so 28 more of the 50 action-d2-unreachable
#: artefacts are now delivered via the profile channel. These 30 members are the
#: mission's actual delivery: the previously "topology authored, delivery pending"
#: Family B/C artefacts plus the depth-gated ``suggests`` artefacts the wiring
#: table flagged for the "fast-follow walk-update mission" (this mission). Every
#: member here is covered by a wiring-table ledger row — enforced by
#: ``test_profile_rescues_have_ledger_coverage`` below.
#:
#: Writing-comms/diagramming activation (commit 9a99801f1, #3009): 30 → 37. Seven
#: newly-activated artefacts are action-d2-unreachable but profile-rescued
#: (DIRECTIVE_047-050, USE_C4_MODEL_TECHNIQUES, quadruple-a-test-format,
#: writing-audience-catalog); their delivering profile edges and ledger rows are
#: recorded in the set body and the wiring table's profile-channel walk-activation
#: ledger.
_PROFILE_RESCUES: frozenset[str] = frozenset(
    {
        "directive:DIRECTIVE_044",
        "paradigm:c4-incremental-detail-modeling",
        "procedure:drill-down-documentation",
        "procedure:event-storming-discovery",
        "styleguide:reasons-canvas-writing",
        "tactic:architecture-diagram-review-checklist",
        "tactic:c4-zoom-in-architecture-documentation",
        "tactic:canonical-source-unification",
        "tactic:code-documentation-analysis",
        "tactic:mutation-testing-workflow",
        "tactic:occurrence-classification-workflow",
        "tactic:ownership-map-leeway",
        "tactic:pr-agent-worktree-isolation",
        "tactic:refactoring-encapsulate-record",
        "tactic:refactoring-encapsulate-variable",
        "tactic:refactoring-extract-first-order-concept",
        "tactic:refactoring-move-field",
        "tactic:refactoring-move-method",
        "tactic:refactoring-state-pattern-for-behavior",
        "tactic:refactoring-strangler-fig",
        "tactic:terminology-extraction-mapping",
        "tactic:test-readability-clarity-check",
        "tactic:zombies-tdd",
        "toolguide:contextive",
        "toolguide:github-tracker",
        "toolguide:mermaid-diagramming",
        "toolguide:plantuml-diagramming",
        "toolguide:python-mutation-tools",
        "toolguide:terminology-guard",
        "toolguide:typescript-mutation-tools",
        # Writing-comms/diagramming activation (commit 9a99801f1, #3009): seven of
        # the seventeen newly-activated artefacts are rescued by the profile channel
        # -- action-d2-unreachable yet delivered by an activated writing-comms
        # profile. Delivering edges (traced from the built-in graph; ledger rows
        # below):
        #   DIRECTIVE_047, DIRECTIVE_048  <- agent_profile:scribe-sally
        #   DIRECTIVE_049, DIRECTIVE_050  <- agent_profile:minutes-maker-mahad
        #   quadruple-a-test-format       <- generic-agent -> DIRECTIVE_041 (suggests)
        #   writing-audience-catalog      <- agent_profile:comms-cleo
        #   USE_C4_MODEL_TECHNIQUES       <- agent_profile:diagram-daisy (requires)
        "directive:DIRECTIVE_047",
        "directive:DIRECTIVE_048",
        "directive:DIRECTIVE_049",
        "directive:DIRECTIVE_050",
        "directive:USE_C4_MODEL_TECHNIQUES",
        "styleguide:quadruple-a-test-format",
        "tactic:writing-audience-catalog",
    }
)


# ---------------------------------------------------------------------------
# Shared measurement helpers (each *calls* the canonical traversal helpers)
# ---------------------------------------------------------------------------


def _activated() -> frozenset[str]:
    """The project's resolved activation store, in normalized node form."""
    return frozenset(charter_activated_urns(_REPO_ROOT))


def _raw_activated_map() -> Mapping[str, list[str]]:
    """The activation store in its raw *store* form (pre-normalization).

    Reuses ``charter.pack_context``'s own charter-pointer resolution — the exact
    path :func:`charter_activated_urns` reads — so the WP06 partition sees the
    same store the runtime does. The store form is what makes the C-009
    ``not_a_node`` slugs visible (e.g. ``directive:025-boy-scout-rule``); the
    normalized accessor above has already reconciled them away.
    """
    data = pack_context._load_config(_REPO_ROOT)
    activation = pack_context._load_charter_activation_source(_REPO_ROOT, data)
    raw: dict[str, list[str]] = {}
    for key, kind in pack_context._ACTIVATION_URN_KINDS.items():
        entries = activation.get(key) or []
        raw[kind] = [str(entry) for entry in entries]
    return raw


def _describe(name: str, measured: frozenset[str], pinned: frozenset[str]) -> str:
    appeared = sorted(measured - pinned)
    healed = sorted(pinned - measured)
    lines = [f"{name} drifted from its pinned membership."]
    if appeared:
        lines.append(
            "  NEWLY UNREACHABLE (measured, not pinned) — an activated artefact "
            "no traversal reaches; wire it to a reachable source or record why:\n"
            + "\n".join(f"    + {urn}" for urn in appeared)
        )
    if healed:
        lines.append(
            "  NO LONGER UNREACHABLE (pinned, not measured) — drop it from the "
            "pin; if it became reachable only by C-009 normalization, that is "
            "NOT progress (NFR-004 ledger):\n"
            + "\n".join(f"    - {urn}" for urn in healed)
        )
    return "\n".join(lines)


@pytest.fixture(scope="module")
def graph() -> DRGGraph:
    return load_built_in_graph()


@pytest.mark.doctrine
class TestActionChannelReachability:
    """The action channel is measured by CALLING ``resolve_context`` (R-1)."""

    def test_action_helper_calls_resolve_context_not_a_reimplemented_walk(
        self, graph: DRGGraph
    ) -> None:
        """Union over action seeds equals the per-seed ``resolve_context`` union.

        If the helper reimplemented the walk, this equality against a direct
        ``resolve_context`` union would be the first thing to drift.
        """
        seeds = action_seed_urns(graph)
        assert seeds, "the shipped graph must carry action nodes to seed from"
        direct: set[str] = set()
        for seed in seeds:
            direct |= resolve_context(graph, seed, depth=_ACTION_D1_DEPTH).artifact_urns
        assert action_channel_reachable(graph, seeds, _ACTION_D1_DEPTH) == frozenset(direct)

    def test_unreachable_at_d1_is_the_pinned_membership(self, graph: DRGGraph) -> None:
        reachable = action_channel_reachable(graph, action_seed_urns(graph), _ACTION_D1_DEPTH)
        measured = _activated() - reachable
        assert measured == _ACTION_UNREACHABLE_D1, _describe(
            "_ACTION_UNREACHABLE_D1", measured, _ACTION_UNREACHABLE_D1
        )

    def test_unreachable_at_d2_is_the_pinned_membership(self, graph: DRGGraph) -> None:
        reachable = action_channel_reachable(graph, action_seed_urns(graph), _ACTION_D2_DEPTH)
        measured = _activated() - reachable
        assert measured == _ACTION_UNREACHABLE_D2, _describe(
            "_ACTION_UNREACHABLE_D2", measured, _ACTION_UNREACHABLE_D2
        )

    def test_bootstrap_depth_only_relaxes_the_steady_state(self) -> None:
        """d=2 reaches a superset, so its unreachable set is d=1's minus a spread
        of exactly 7 (R-2) — never a set d=1 did not already contain."""
        assert _ACTION_UNREACHABLE_D2 <= _ACTION_UNREACHABLE_D1
        assert len(_ACTION_UNREACHABLE_D1 - _ACTION_UNREACHABLE_D2) == _ACTION_D1_D2_SPREAD

    def test_common_docs_cluster_and_asset_are_action_reachable(self, graph: DRGGraph) -> None:
        """FR-015 / WP09 acceptance (spec User Story 4, scenario 3): every wired
        artefact is action-reachable AFTER landing, not merely edge-incident.

        The whole common-docs cluster was a strongly-connected island no action
        scoped — measured unreachable at d=1 and d=2 before WP09. The single
        authored ``scope`` edge from ``documentation/generate`` to DIRECTIVE_042
        must make all six activated members AND the delivered asset reachable at
        BOTH depths. Measured by CALLING the WP08 helper (R-1); if any member
        were only edge-incident to an unreachable source (the PR #3007 failure),
        it would be absent from this set and this test would name it.
        """
        for depth in (_ACTION_D1_DEPTH, _ACTION_D2_DEPTH):
            reachable = action_channel_reachable(graph, action_seed_urns(graph), depth)
            missing = sorted((_COMMON_DOCS_WIRED | {_COMMON_DOCS_ASSET}) - reachable)
            assert not missing, (
                f"wired common-docs artefacts still unreachable at d={depth} "
                f"(wired to an unreachable source, or the scope edge is absent): "
                f"{missing}"
            )

    def test_ddd_family_is_action_reachable_at_specify_grain(
        self, graph: DRGGraph
    ) -> None:
        """#3063 family-A acceptance (operator interview outcome): the specify
        grain must reach the DDD paradigm and its strategic-design family.

        The whole DDD family was a set of activated artefacts no action scoped —
        measured unreachable at d=1 and d=2 before this edge. The single authored
        ``scope`` edge from ``software-dev/specify`` to
        ``paradigm:domain-driven-design`` makes the paradigm action-reachable, and
        its authored ``requires`` edges deliver the members transitively. Measured
        by CALLING the WP08 helper (R-1); if any member were only edge-incident to
        an unreachable source (the PR #3007 failure), it would be absent here and
        this test would name it. Red before the edge lands, green after.
        """
        for depth in (_ACTION_D1_DEPTH, _ACTION_D2_DEPTH):
            reachable = action_channel_reachable(graph, action_seed_urns(graph), depth)
            missing = sorted(_DDD_FAMILY_WIRED - reachable)
            assert not missing, (
                f"DDD family still unreachable at d={depth} "
                f"(paradigm not scoped by an action, or a member is wired only to "
                f"an unreachable source): {missing}"
            )

    def test_testing_bdd_family_is_action_reachable_at_implement_review(
        self, graph: DRGGraph
    ) -> None:
        """#3063 family-D acceptance (operator ACCEPT-DELIVERY ruling): the BDD +
        test-quality members must be action-reachable at implement/review.

        Unlike families B/C, family D delivers, because ``directive:DIRECTIVE_034``
        (test-first) and ``directive:DIRECTIVE_030`` (test-quality gate) are already
        ``scope``-linked from ``action:software-dev/implement`` and
        ``action:software-dev/review``. ``resolve_context`` step 3 walks
        ``suggests`` from those scope-resolved artifacts, so the authored
        ``suggests`` edges deliver their targets. Measured by CALLING the WP08
        helper (R-1): the seven core members must be reachable at BOTH the compact
        (d=1) and bootstrap (d=2) depths; the three brownfield/2-hop members are
        reached at the bootstrap depth only. Red before the edges land, green after.
        """
        r_d1 = action_channel_reachable(graph, action_seed_urns(graph), _ACTION_D1_DEPTH)
        missing_d1 = sorted(_TESTING_DELIVERED_AT_D1 - r_d1)
        assert not missing_d1, (
            "BDD + test-quality members still unreachable at d=1 "
            f"(a hub is not action-scoped, or an edge is absent): {missing_d1}"
        )

        r_d2 = action_channel_reachable(graph, action_seed_urns(graph), _ACTION_D2_DEPTH)
        missing_d2 = sorted(_TESTING_BDD_MUTATION_WIRED - r_d2)
        assert not missing_d2, (
            "family-D delivered members still unreachable at d=2: "
            f"{missing_d2}"
        )
        # The mutation hub (a NEW non-scoped directive) and the DIRECTIVE_041
        # fan-out are INERT by design: their members stay unreachable. Guards
        # against a future edit that accidentally makes the mutation family eager.
        assert "tactic:mutation-testing-workflow" not in r_d2
        assert "styleguide:quadruple-a-test-format" not in r_d2


@pytest.mark.doctrine
class TestProfileChannelReachability:
    """The profile channel is a SEPARATE ``walk_edges`` traversal (R-3)."""

    def test_profile_relations_are_requires_and_specializes_from(self) -> None:
        """The channel follows lineage + hard-dependency + soft-recommendation
        edges — and crucially NOT ``scope``, the relation ``resolve_context``
        seeds on. That absence is why the two channels cannot be folded (R-3).

        ``suggests`` joins the set in mission
        ``doctrine-delivery-activation-01KYQVQK`` (WP01/FR-001): the profile
        channel now delivers the #3063 A–E families that were authored inert.
        """
        assert {r.value for r in PROFILE_CHANNEL_RELATIONS} == {
            "requires",
            "specializes_from",
            "suggests",
        }
        assert Relation.SCOPE not in PROFILE_CHANNEL_RELATIONS

    def test_resolve_context_from_a_profile_reaches_nothing(self, graph: DRGGraph) -> None:
        """The reason the profile channel is not a ``resolve_context`` seed set.

        ``resolve_context`` step 1 walks ``scope`` only, and profiles carry zero
        outbound ``scope``, so seeding a profile into it returns 0 artefacts at
        every depth — folding the channels would silently measure nothing.
        """
        for seed in agent_profile_seed_urns(graph):
            for depth in (_ACTION_D1_DEPTH, _ACTION_D2_DEPTH):
                assert resolve_context(graph, seed, depth=depth).artifact_urns == frozenset()

    def test_profile_channel_is_fail_closed_on_empty_configuration(
        self, graph: DRGGraph
    ) -> None:
        """``profile: str | None`` — an unconfigured caller reaches NOTHING, not
        the whole graph (R-3b: it must not repeat the fail-open shape FR-018
        retires)."""
        assert profile_channel_reachable(graph, frozenset()) == frozenset()

    def test_profile_unreachable_is_the_pinned_membership(self, graph: DRGGraph) -> None:
        reachable = profile_channel_reachable(graph, agent_profile_seed_urns(graph))
        measured = _activated() - reachable
        assert measured == _PROFILE_UNREACHABLE, _describe(
            "_PROFILE_UNREACHABLE", measured, _PROFILE_UNREACHABLE
        )

    def test_profile_channel_rescues_activated_artefacts_the_action_channel_misses(
        self, graph: DRGGraph
    ) -> None:
        """The load-bearing R-3 fact: the profile channel is a distinct entry
        vector. These activated artefacts are unreachable from every action at
        d=2 yet reachable because a profile ``requires`` them."""
        rescues = _ACTION_UNREACHABLE_D2 - _PROFILE_UNREACHABLE
        assert rescues == _PROFILE_RESCUES, _describe(
            "_PROFILE_RESCUES", rescues, _PROFILE_RESCUES
        )
        assert rescues, "the profile channel must rescue at least one activated artefact"
        # Delivered to nobody by the action channel, delivered by the profile
        # channel: exactly the two-channel model (R-3), proven from the graph.
        profile_reachable = profile_channel_reachable(graph, agent_profile_seed_urns(graph))
        action_d2 = action_channel_reachable(graph, action_seed_urns(graph), _ACTION_D2_DEPTH)
        assert rescues <= profile_reachable
        assert not (rescues & action_d2)


#: The wiring-table composition ledger this WP authored for the profile-channel
#: walk-activation. The cross-check below scopes its search to THIS section so a
#: forgotten ledger row genuinely fails (a whole-document scan would pass on a
#: member that happens to appear elsewhere in the doc).
_WIRING_TABLE_PATH: Path = (
    _REPO_ROOT / "docs" / "plans" / "doctrine" / "delivery-reachability-wiring-table.md"
)
_LEDGER_SECTION_START = "## Composition ledger (NFR-002) — profile-channel walk-activation"
_LEDGER_SECTION_END = "## Composition ledger (NFR-004) — counts this WP moves"


def _profile_channel_ledger_text() -> str:
    """The profile-channel walk-activation ledger section, as raw markdown.

    A line-scan between the two known section headers — deliberately NOT a
    markdown AST (T015: keep the parser cheap). Fails loudly if either header
    is missing so the cross-check can never silently degrade to "no rows found,
    therefore vacuously pass".
    """
    text = _WIRING_TABLE_PATH.read_text(encoding="utf-8")
    start = text.find(_LEDGER_SECTION_START)
    assert start != -1, (
        f"profile-channel walk-activation ledger header not found in "
        f"{_WIRING_TABLE_PATH} — the T013 ledger section is missing"
    )
    end = text.find(_LEDGER_SECTION_END, start)
    assert end != -1, (
        f"ledger section end header {_LEDGER_SECTION_END!r} not found after the "
        f"start header in {_WIRING_TABLE_PATH}"
    )
    return text[start:end]


@pytest.mark.doctrine
class TestProfileRescuesHaveLedgerCoverage:
    """T015 cross-check: every ``_PROFILE_RESCUES`` member is named in the ledger.

    NFR-002 for the reachability pins is REVIEW-gated, not CI-gated (D18):
    ``measured == pin`` greens on any pasted value. This cross-check does NOT
    validate that a pin value is *numerically correct* — that remains the
    reviewer's per-member ledger-vs-diff comparison. It catches only the most
    common regression class: a pin edited without a matching wiring-table ledger
    row. A green here means "every rescued member is documented", never "the
    numbers are right".
    """

    def test_every_profile_rescue_member_has_a_ledger_row(self) -> None:
        ledger = _profile_channel_ledger_text()
        missing = sorted(m for m in _PROFILE_RESCUES if f"`{m}`" not in ledger)
        assert not missing, (
            "Every _PROFILE_RESCUES member must be named (backtick-quoted) in the "
            "profile-channel walk-activation ledger of "
            f"{_WIRING_TABLE_PATH.name}. Missing ledger rows for:\n"
            + "\n".join(f"    - {m}" for m in missing)
            + "\n\nAdd a ledger entry (which family/edge delivers it, which WP wired "
            "the edge) before moving the pin — a pin move without a ledger row is an "
            "NFR-002 violation."
        )

    def test_cross_check_is_not_vacuous(self) -> None:
        """The cross-check must have real bite: a fabricated missing member is
        caught. Guards against the ledger text going empty/unparseable and the
        membership check silently passing over nothing (D18 vacuity risk)."""
        ledger = _profile_channel_ledger_text()
        fabricated = "tactic:__definitely-not-a-real-rescued-member__"
        assert f"`{fabricated}`" not in ledger
        # A member NOT in the ledger would be flagged — proving the assertion in
        # the sibling test is load-bearing, not always-true.
        pretend_rescues = frozenset({fabricated})
        missing = sorted(m for m in pretend_rescues if f"`{m}`" not in ledger)
        assert missing == [fabricated]


@pytest.mark.doctrine
class TestC009NormalizationSwingExcluded:
    """The store->node slug reconciliation is declared, and never banked.

    The swing size is pinned by ``_NORMALIZATION_DELTA`` (31 as of the
    writing-comms/diagramming activation) rather than baked into names here, so a
    later count change touches only the constant.
    """

    def test_normalization_delta_is_the_declared_swing(self, graph: DRGGraph) -> None:
        node_urns = graph.node_urns()
        reachable = action_channel_reachable(graph, action_seed_urns(graph), _ACTION_D1_DEPTH)
        partition = partition_activated_unreachable(_raw_activated_map(), node_urns, reachable)
        assert partition.normalization_delta == _NORMALIZATION_DELTA

    def test_pinned_sets_carry_no_store_form_not_a_node_slug(self, graph: DRGGraph) -> None:
        """The pinned progress sets are all node form, so the ``not_a_node``
        store slugs (the C-009 swing) cannot inflate them (C-009)."""
        node_urns = graph.node_urns()
        reachable = action_channel_reachable(graph, action_seed_urns(graph), _ACTION_D1_DEPTH)
        not_a_node = partition_activated_unreachable(
            _raw_activated_map(), node_urns, reachable
        ).not_a_node
        assert not_a_node  # the swing exists...
        for pinned in (_ACTION_UNREACHABLE_D1, _ACTION_UNREACHABLE_D2, _PROFILE_UNREACHABLE):
            assert not (pinned & not_a_node)  # ...but is excluded from every pin
            assert pinned <= node_urns


@pytest.mark.doctrine
class TestNominalWiringIsCaughtT047:
    """Wiring an artefact to an unreachable source does not make it reachable.

    This is the WP's reason to exist: an *incidence* check (PR #3007's method)
    reports the nominally-wired artefact fixed; the *reachability* check reports
    it unreachable.
    """

    def test_incidence_calls_the_nominal_wiring_fixed(self) -> None:
        """The wrong method, demonstrated. Both the unreachable source and the
        nominally-wired target are incident to an edge, so incidence de-orphans
        them — the exact false 'fixed' verdict this WP exists to refuse."""
        incident = incident_urns(nominal_wiring_graph())
        assert NOMINALLY_WIRED in incident
        assert UNREACHABLE_SOURCE in incident

    def test_reachability_reports_the_nominal_wiring_unreachable(self) -> None:
        graph = nominal_wiring_graph()
        reachable = action_channel_reachable(graph, [ACTION_URN], _ACTION_D2_DEPTH)
        # The trap: inbound edge from an unreachable source confers no reach.
        assert NOMINALLY_WIRED not in reachable
        assert UNREACHABLE_SOURCE not in reachable

    def test_positive_control_wiring_to_a_reachable_source_does_reach(self) -> None:
        """Guards against a helper that simply refuses every ``requires`` target:
        a directive the action scopes DOES carry reach to what it requires."""
        graph = nominal_wiring_graph()
        reachable = action_channel_reachable(graph, [ACTION_URN], _ACTION_D2_DEPTH)
        assert IN_SCOPE_DIRECTIVE in reachable
        assert PROPERLY_WIRED in reachable
