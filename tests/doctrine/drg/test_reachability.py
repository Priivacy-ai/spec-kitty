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

#: Repo root — tests/doctrine/drg/ is three levels down.
_REPO_ROOT: Path = Path(__file__).resolve().parents[3]

#: ``resolve_context`` depths: compact (stricter) and bootstrap.
_ACTION_D1_DEPTH = 1
_ACTION_D2_DEPTH = 2

#: The C-009 normalization swing (WP06): 25 activated directive slugs whose
#: STORE form is not a graph node while their NORMALIZED form is. Reconciling
#: the form is not reachability progress and is excluded from SC-005.
_NORMALIZATION_DELTA = 25

#: The measured d=1 <-> d=2 action-channel spread (R-2): d=2 (bootstrap) reaches
#: exactly 7 more nodes than d=1 (compact), so d=2's unreachable set is d=1's
#: minus those 7.
_ACTION_D1_D2_SPREAD = 7

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

#: Activated artefacts (node form) NOT reachable via the action channel at
#: d=1 (compact/steady-state). Membership, not cardinality (R-4).
_ACTION_UNREACHABLE_D1: frozenset[str] = frozenset(
    {
        "directive:DIRECTIVE_031",
        "directive:DIRECTIVE_032",
        "directive:DIRECTIVE_035",
        "directive:DIRECTIVE_038",
        "directive:DIRECTIVE_039",
        "directive:DIRECTIVE_044",
        "paradigm:atomic-design",
        "paradigm:behaviour-driven-development",
        "paradigm:c4-incremental-detail-modeling",
        "paradigm:domain-driven-design",
        "paradigm:specification-by-example",
        "paradigm:structured-prompt-driven-development",
        "procedure:bdd-scenario-lifecycle",
        "procedure:documentation-gap-prioritization",
        "procedure:drill-down-documentation",
        "procedure:event-storming-discovery",
        "procedure:example-mapping-workshop",
        "procedure:migrate-project-guidance-to-spec-kitty-charter",
        "styleguide:adversarial-squad-cadence",
        "styleguide:aggregate-design-rules",
        "styleguide:deployable-skill-authoring",
        "styleguide:java-conventions",
        "styleguide:mutation-aware-test-design",
        "styleguide:planning-and-tracking",
        "styleguide:reasons-canvas-writing",
        "tactic:adversarial-qa-handoff",
        "tactic:aggregate-boundary-design",
        "tactic:analysis-extract-before-interpret",
        "tactic:anti-corruption-layer",
        "tactic:architecture-diagram-review-checklist",
        "tactic:atdd-adversarial-acceptance",
        "tactic:atomic-design-review-checklist",
        "tactic:atomic-state-ownership",
        "tactic:bounded-context-canvas-fill",
        "tactic:bounded-context-identification",
        "tactic:c4-zoom-in-architecture-documentation",
        "tactic:canonical-source-unification",
        "tactic:chain-of-responsibility-rule-pipeline",
        "tactic:code-documentation-analysis",
        "tactic:compositional-stream-boundaries",
        "tactic:context-boundary-inference",
        "tactic:context-mapping-classification",
        "tactic:cross-cutting-state-via-store",
        "tactic:development-bdd",
        "tactic:domain-event-capture",
        "tactic:entity-value-object-classification",
        "tactic:formalized-constraint-testing",
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
        "tactic:work-package-completion-validation",
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
    }
)

#: Activated artefacts (node form) NOT reachable via the action channel at
#: d=2 (bootstrap). A strict subset of the d=1 set (bootstrap reaches more).
_ACTION_UNREACHABLE_D2: frozenset[str] = frozenset(
    {
        "directive:DIRECTIVE_031",
        "directive:DIRECTIVE_032",
        "directive:DIRECTIVE_035",
        "directive:DIRECTIVE_038",
        "directive:DIRECTIVE_039",
        "directive:DIRECTIVE_044",
        "paradigm:atomic-design",
        "paradigm:c4-incremental-detail-modeling",
        "paradigm:domain-driven-design",
        "paradigm:specification-by-example",
        "paradigm:structured-prompt-driven-development",
        "procedure:documentation-gap-prioritization",
        "procedure:drill-down-documentation",
        "procedure:event-storming-discovery",
        "procedure:example-mapping-workshop",
        "procedure:migrate-project-guidance-to-spec-kitty-charter",
        "styleguide:aggregate-design-rules",
        "styleguide:deployable-skill-authoring",
        "styleguide:java-conventions",
        "styleguide:mutation-aware-test-design",
        "styleguide:reasons-canvas-writing",
        "tactic:adversarial-qa-handoff",
        "tactic:aggregate-boundary-design",
        "tactic:analysis-extract-before-interpret",
        "tactic:anti-corruption-layer",
        "tactic:architecture-diagram-review-checklist",
        "tactic:atdd-adversarial-acceptance",
        "tactic:atomic-design-review-checklist",
        "tactic:atomic-state-ownership",
        "tactic:bounded-context-canvas-fill",
        "tactic:bounded-context-identification",
        "tactic:c4-zoom-in-architecture-documentation",
        "tactic:canonical-source-unification",
        "tactic:chain-of-responsibility-rule-pipeline",
        "tactic:code-documentation-analysis",
        "tactic:compositional-stream-boundaries",
        "tactic:context-boundary-inference",
        "tactic:context-mapping-classification",
        "tactic:cross-cutting-state-via-store",
        "tactic:development-bdd",
        "tactic:domain-event-capture",
        "tactic:entity-value-object-classification",
        "tactic:formalized-constraint-testing",
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
        "tactic:reverse-speccing",
        "tactic:secure-regex-catastrophic-backtracking",
        "tactic:terminology-extraction-mapping",
        "tactic:test-readability-clarity-check",
        "tactic:test-to-system-reconstruction",
        "tactic:work-package-completion-validation",
        "tactic:zombies-tdd",
        "toolguide:contextive",
        "toolguide:github-tracker",
        "toolguide:maven-review-checks",
        "toolguide:mermaid-diagramming",
        "toolguide:plantuml-diagramming",
        "toolguide:python-mutation-tools",
        "toolguide:terminology-guard",
        "toolguide:typescript-mutation-tools",
    }
)

#: Activated artefacts NOT reachable via the profile channel (``walk_edges``
#: over {requires, specializes_from} from every activated agent profile). The
#: profile channel is a second entry vector, so most action-doctrine is
#: legitimately outside it; the load-bearing fact is the *difference* from the
#: action set below, which names the artefacts the profile channel rescues.
_PROFILE_UNREACHABLE: frozenset[str] = frozenset(
    {
        "directive:DIRECTIVE_029",
        "directive:DIRECTIVE_033",
        "directive:DIRECTIVE_035",
        "directive:DIRECTIVE_036",
        "directive:DIRECTIVE_037",
        "directive:DIRECTIVE_038",
        "directive:DIRECTIVE_039",
        "directive:DIRECTIVE_042",
        "directive:DIRECTIVE_046",
        "paradigm:atomic-design",
        "paradigm:behaviour-driven-development",
        "paradigm:brownfield-onboarding",
        "paradigm:c4-incremental-detail-modeling",
        "paradigm:deep-module-design",
        "paradigm:domain-driven-design",
        "paradigm:specification-by-example",
        "paradigm:structured-prompt-driven-development",
        "procedure:adversarial-squad-deployment",
        "procedure:bdd-scenario-lifecycle",
        "procedure:disciplined-defect-diagnosis",
        "procedure:documentation-gap-prioritization",
        "procedure:domain-aware-decision-interview",
        "procedure:drill-down-documentation",
        "procedure:event-storming-discovery",
        "procedure:example-mapping-workshop",
        "procedure:issue-triage-state-machine",
        "procedure:legacy-codebase-triage",
        "procedure:migrate-project-guidance-to-spec-kitty-charter",
        "procedure:mission-tracer-files",
        "procedure:mission-wrap-up-sequence",
        "procedure:post-merge-arch-gate-adjudication",
        "procedure:red-main-release-discipline",
        "procedure:refactoring",
        "procedure:situational-assessment",
        "procedure:test-first-bug-fixing",
        "styleguide:adversarial-squad-cadence",
        "styleguide:aggregate-design-rules",
        "styleguide:common-docs",
        "styleguide:deployable-skill-authoring",
        "styleguide:java-conventions",
        "styleguide:kitty-glossary-writing",
        "styleguide:mutation-aware-test-design",
        "styleguide:planning-and-tracking",
        "styleguide:python-conventions",
        "styleguide:reasons-canvas-writing",
        "styleguide:testing-principles",
        "styleguide:tiered-standards",
        "tactic:acceptance-test-first",
        "tactic:adr-drafting-workflow",
        "tactic:adversarial-qa-handoff",
        "tactic:aggregate-boundary-design",
        "tactic:ammerse-impact-analysis",
        "tactic:analysis-extract-before-interpret",
        "tactic:architectural-gate-non-vacuity",
        "tactic:architecture-diagram-review-checklist",
        "tactic:atdd-adversarial-acceptance",
        "tactic:atomic-design-review-checklist",
        "tactic:atomic-state-ownership",
        "tactic:autonomous-operation-protocol",
        "tactic:avoid-gold-plating",
        "tactic:black-box-integration-testing",
        "tactic:boring-code-review",
        "tactic:bounded-context-canvas-fill",
        "tactic:bounded-context-identification",
        "tactic:c4-zoom-in-architecture-documentation",
        "tactic:canonical-source-unification",
        "tactic:chain-of-responsibility-rule-pipeline",
        "tactic:change-apply-smallest-viable-diff",
        "tactic:clean-linear-commit-history",
        "tactic:code-documentation-analysis",
        "tactic:common-docs-curation",
        "tactic:common-docs-find",
        "tactic:common-docs-scaffold",
        "tactic:common-docs-write",
        "tactic:compositional-stream-boundaries",
        "tactic:connascence-analysis",
        "tactic:context-boundary-inference",
        "tactic:context-mapping-classification",
        "tactic:cross-cutting-state-via-store",
        "tactic:deepening-opportunity-assessment",
        "tactic:dependency-hygiene",
        "tactic:documentation-curation-audit",
        "tactic:easy-to-change",
        "tactic:eisenhower-prioritisation",
        "tactic:entity-value-object-classification",
        "tactic:focused-function-complexity-check",
        "tactic:forensic-repository-audit",
        "tactic:formalized-constraint-testing",
        "tactic:frozen-baseline-shrink-only-ratchet",
        "tactic:function-over-form-testing",
        "tactic:generated-code-stewardship",
        "tactic:glossary-curation-interview",
        "tactic:input-validation-fail-fast",
        "tactic:interface-variation-design",
        "tactic:locality-of-change",
        "tactic:mutation-testing-workflow",
        "tactic:no-parallel-duplicate-test-runs",
        "tactic:occurrence-classification-workflow",
        "tactic:ownership-map-leeway",
        "tactic:pr-agent-worktree-isolation",
        "tactic:premortem-risk-identification",
        "tactic:problem-decomposition",
        "tactic:quality-gate-verification",
        "tactic:reasons-canvas-fill",
        "tactic:reasons-canvas-review",
        "tactic:refactoring-change-function-declaration",
        "tactic:refactoring-combine-functions-into-transform",
        "tactic:refactoring-conditional-to-strategy",
        "tactic:refactoring-consolidate-conditional-expression",
        "tactic:refactoring-encapsulate-record",
        "tactic:refactoring-encapsulate-variable",
        "tactic:refactoring-extract-class-by-responsibility-split",
        "tactic:refactoring-extract-first-order-concept",
        "tactic:refactoring-guard-clauses-before-polymorphism",
        "tactic:refactoring-inline-temp",
        "tactic:refactoring-introduce-null-object",
        "tactic:refactoring-move-field",
        "tactic:refactoring-move-method",
        "tactic:refactoring-replace-magic-number-with-symbolic-constant",
        "tactic:refactoring-replace-temp-with-query",
        "tactic:refactoring-retry-pattern",
        "tactic:refactoring-state-pattern-for-behavior",
        "tactic:refactoring-strangler-fig",
        "tactic:reference-architectural-patterns",
        "tactic:requirements-validation-workflow",
        "tactic:reviewer-implementer-role-separation",
        "tactic:safe-to-fail-experiment",
        "tactic:secure-design-checklist",
        "tactic:secure-regex-catastrophic-backtracking",
        "tactic:stakeholder-alignment",
        "tactic:stopping-conditions",
        "tactic:strategic-domain-classification",
        "tactic:tdd-red-green-refactor",
        "tactic:terminology-extraction-mapping",
        "tactic:test-boundaries-by-responsibility",
        "tactic:test-minimisation",
        "tactic:test-pyramid-progression",
        "tactic:test-to-system-reconstruction",
        "tactic:testing-select-appropriate-level",
        "tactic:usage-examples-sync",
        "tactic:work-package-completion-validation",
        "tactic:zombies-tdd",
        "toolguide:contextive",
        "toolguide:efficient-local-tooling",
        "toolguide:git-agent-commit-signing",
        "toolguide:github-tracker",
        "toolguide:maven-review-checks",
        "toolguide:mermaid-diagramming",
        "toolguide:plantuml-diagramming",
        "toolguide:python-mutation-tools",
        "toolguide:python-review-checks",
        "toolguide:terminology-guard",
        "toolguide:typescript-mutation-tools",
    }
)

#: Activated artefacts the profile channel reaches that the action channel at
#: d=2 does NOT — i.e. ``_ACTION_UNREACHABLE_D2 - _PROFILE_UNREACHABLE``. Proof
#: that the profile channel is a genuine, distinct entry vector (R-3): these
#: artefacts reach an agent only because a profile ``requires`` them.
_PROFILE_RESCUES: frozenset[str] = frozenset(
    {
        "directive:DIRECTIVE_031",
        "directive:DIRECTIVE_032",
        "directive:DIRECTIVE_044",
        "tactic:anti-corruption-layer",
        "tactic:development-bdd",
        "tactic:domain-event-capture",
        "tactic:reverse-speccing",
        "tactic:test-readability-clarity-check",
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


@pytest.mark.doctrine
class TestProfileChannelReachability:
    """The profile channel is a SEPARATE ``walk_edges`` traversal (R-3)."""

    def test_profile_relations_are_requires_and_specializes_from(self) -> None:
        """The channel follows lineage + hard-dependency edges — and crucially
        NOT ``scope``, the relation ``resolve_context`` seeds on. That absence is
        why the two channels cannot be folded (R-3)."""
        assert {r.value for r in PROFILE_CHANNEL_RELATIONS} == {
            "requires",
            "specializes_from",
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


@pytest.mark.doctrine
class TestC009NormalizationSwingExcluded:
    """The 25-slug store->node reconciliation is declared, and never banked."""

    def test_normalization_delta_is_the_declared_25_swing(self, graph: DRGGraph) -> None:
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
