"""Enumerable registry of DRG content hand-authored directly in the shipped
``src/doctrine/*.graph.yaml`` fragments (mission doctrine-tension-edges-01KY1WPC
WP02) that the extractor cannot derive from built-in artifact frontmatter.

Why this exists
----------------

The extractor (:mod:`doctrine.drg.migration.extractor`) walks built-in
artifact YAML and mints DRG nodes/edges from their inline reference fields
(``tactic_refs``, ``references``, etc.). WP02 of this mission hand-authored
three new DRG relations (``in_tension_with``, ``reconciles_tension``,
``rejects``) plus six ``anti_pattern`` nodes directly into the graph
fragments. Per ADR 2026-07-18-1 / constraint C-005 ("edge-authored, not
field-derived"), the extractor has **no frontmatter mechanism** that could
ever mint these -- they are authored content, not migrated content, and a
pure regeneration will never reproduce them. That is by design, not drift.

Two consumers depend on this registry so a pure extractor regeneration never
silently regresses (or perpetually misreports staleness on) the hand-authored
content:

1. ``spec-kitty doctrine regenerate-graph`` (:mod:`specify_cli.cli.commands.doctrine`)
   -- both its ``--check`` freshness comparison and its write path must merge
   this overlay in, or running the command for real would overwrite
   ``src/doctrine/*.graph.yaml`` with a version that has silently dropped
   every hand-authored tension/reconciliation/rejection edge and anti-pattern
   node, and ``--check`` alone would report "stale" forever even when nothing
   is actually stale.
2. The doctrine test suite's shipped-graph freshness/equality canaries
   (``tests/doctrine/drg/migration/test_extractor.py``,
   ``test_extractor_projection.py``, ``test_path_ref_resolver.py``,
   ``tests/doctrine/drg/test_graph_sharding_equality.py``,
   ``test_sharding_silent_degrade.py``) -- each compares a pure extractor
   regeneration against the committed shipped graph and must merge this
   overlay into its "expected" side.

Any discrepancy beyond exactly this enumerated overlay is still a genuine
freshness failure. Growing this list is a deliberate, reviewed edit -- it
should only change in lockstep with a new hand-authored edge/node landing in
one of the ``*.graph.yaml`` fragments, never as a reflex "make the check
pass" change.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from doctrine.drg.models import DRGEdge, DRGGraph, DRGNode, NodeKind, Relation
from doctrine.drg.validator import assert_valid

# ---------------------------------------------------------------------------
# The six anti-pattern/smell nodes authored in src/doctrine/anti_pattern.graph.yaml
# (WP02 T009). None of these are ever an edge *source* (rejects edges terminate
# at them), so they carry no outgoing edges of their own.
# ---------------------------------------------------------------------------

HAND_AUTHORED_NODES: tuple[DRGNode, ...] = (
    DRGNode(
        urn="anti_pattern:anemic-domain-model",
        kind=NodeKind.ANTI_PATTERN,
        label="Anemic Domain Model",
        tags=["anti-pattern"],
    ),
    DRGNode(
        urn="anti_pattern:big-ball-of-mud",
        kind=NodeKind.ANTI_PATTERN,
        label="Big Ball of Mud",
        tags=["anti-pattern"],
    ),
    DRGNode(
        urn="anti_pattern:big-upfront-design",
        kind=NodeKind.ANTI_PATTERN,
        label="Big Upfront Design",
        tags=["anti-pattern"],
    ),
    DRGNode(
        urn="anti_pattern:code-is-the-documentation",
        kind=NodeKind.ANTI_PATTERN,
        label="Code Is the Documentation",
        tags=["smell"],
    ),
    DRGNode(
        urn="anti_pattern:database-driven-design",
        kind=NodeKind.ANTI_PATTERN,
        label="Database-Driven Design",
        tags=["anti-pattern"],
    ),
    DRGNode(
        urn="anti_pattern:single-diagram-architecture",
        kind=NodeKind.ANTI_PATTERN,
        label="Single-Diagram Architecture",
        tags=["smell"],
    ),
)

# ---------------------------------------------------------------------------
# The 2 in_tension_with + 3 reconciles_tension + 8 rejects edges authored in
# src/doctrine/{directive,paradigm}.graph.yaml (WP02 T007/T008/T010/T011),
# migrated from the retired contradiction-declaration field (WP03).
# Reason text copied verbatim from the committed fragments.
# ---------------------------------------------------------------------------

HAND_AUTHORED_EDGES: tuple[DRGEdge, ...] = (
    DRGEdge(
        source="directive:DIRECTIVE_024",
        target="directive:DIRECTIVE_025",
        relation=Relation.IN_TENSION_WITH,
        reason=(
            "Locality of Change bounds new work to the minimum scope the goal "
            "requires; Boy Scout Rule endorses opportunistic improvement of "
            "touched areas, which can justify expanding a change beyond that "
            "boundary. Both remain valid, co-activatable rules -- the tension "
            "is resolved per-change by keeping adjacent campsite cleaning "
            "inside the touched area while deferring genuinely broad refactors "
            "with an explicit rationale, not by retiring either rule. See "
            "directive:RECONCILE_CHANGE_SCOPE_TENSIONS."
        ),
    ),
    DRGEdge(
        source="directive:DIRECTIVE_025",
        target="tactic:change-apply-smallest-viable-diff",
        relation=Relation.IN_TENSION_WITH,
        reason=(
            "The Boy Scout Rule encourages leaving touched code better than "
            "found, which can justify changes beyond the smallest viable diff "
            "the tactic prescribes. Both remain valid, co-activatable rules -- "
            "apply smallest-viable-diff discipline for goal delivery, and fold "
            "in only the touched-area fixes Boy Scout Rule requires, deferring "
            "broader opportunistic improvement to an explicit task. See "
            "directive:RECONCILE_CHANGE_SCOPE_TENSIONS."
        ),
    ),
    DRGEdge(
        source="directive:RECONCILE_CHANGE_SCOPE_TENSIONS",
        target="directive:DIRECTIVE_024",
        relation=Relation.RECONCILES_TENSION,
    ),
    DRGEdge(
        source="directive:RECONCILE_CHANGE_SCOPE_TENSIONS",
        target="directive:DIRECTIVE_025",
        relation=Relation.RECONCILES_TENSION,
    ),
    DRGEdge(
        source="directive:RECONCILE_CHANGE_SCOPE_TENSIONS",
        target="tactic:change-apply-smallest-viable-diff",
        relation=Relation.RECONCILES_TENSION,
    ),
    DRGEdge(
        source="paradigm:brownfield-onboarding",
        target="anti_pattern:big-ball-of-mud",
        relation=Relation.REJECTS,
        reason=(
            "A Big Ball of Mud is the failure mode brownfield onboarding is "
            "built to interrupt. Where Big Ball of Mud lets coupling and "
            "concepts leak without investigation, brownfield onboarding "
            "insists that the leaks be mapped and named before they are "
            "either preserved or removed."
        ),
    ),
    DRGEdge(
        source="paradigm:brownfield-onboarding",
        target="anti_pattern:big-upfront-design",
        relation=Relation.REJECTS,
        reason=(
            "Big Upfront Design assumes the right structure can be derived "
            "from first principles before contact with the existing system. "
            "Brownfield onboarding inverts the priority: the existing system "
            "is the primary evidence, and design proposals must be grounded "
            "in what the codebase, its history, and its SMEs already encode."
        ),
    ),
    DRGEdge(
        source="paradigm:c4-incremental-detail-modeling",
        target="anti_pattern:big-upfront-design",
        relation=Relation.REJECTS,
        reason=(
            "Big Upfront Design attempts to specify every architectural "
            "detail before implementation begins. C4 incremental detail "
            "modeling favours progressive discovery -- start with a context "
            "diagram and add lower levels only when they earn their keep."
        ),
    ),
    DRGEdge(
        source="paradigm:c4-incremental-detail-modeling",
        target="anti_pattern:code-is-the-documentation",
        relation=Relation.REJECTS,
        reason=(
            "Relying solely on source code as documentation forces every "
            "stakeholder -- including non-technical sponsors -- to read code "
            "to understand system boundaries. C4 provides visual abstractions "
            "that make architecture accessible without requiring code "
            "literacy."
        ),
    ),
    DRGEdge(
        source="paradigm:c4-incremental-detail-modeling",
        target="anti_pattern:single-diagram-architecture",
        relation=Relation.REJECTS,
        reason=(
            "A single all-in-one architecture diagram conflates audiences and "
            "abstraction levels, producing a poster that nobody can review in "
            "a reasonable time. C4 explicitly separates concerns into "
            "distinct levels."
        ),
    ),
    DRGEdge(
        source="paradigm:domain-driven-design",
        target="anti_pattern:anemic-domain-model",
        relation=Relation.REJECTS,
        reason=(
            "Anemic Domain Models strip behaviour from domain objects, "
            "reducing them to data bags with external procedural services. "
            "This defeats the purpose of a rich, expressive domain model and "
            "scatters invariant enforcement across service layers."
        ),
    ),
    DRGEdge(
        source="paradigm:domain-driven-design",
        target="anti_pattern:big-ball-of-mud",
        relation=Relation.REJECTS,
        reason=(
            "A Big Ball of Mud architecture has no explicit context "
            "boundaries or ubiquitous language. Concepts leak across "
            "modules, coupling grows unchecked, and model integrity becomes "
            "impossible to maintain."
        ),
    ),
    DRGEdge(
        source="paradigm:domain-driven-design",
        target="anti_pattern:database-driven-design",
        relation=Relation.REJECTS,
        reason=(
            "Starting from a database schema and generating code around it "
            "inverts the DDD priority: the domain model should drive "
            "persistence, not the other way around. Schema-first thinking "
            "produces models shaped by storage constraints rather than "
            "business rules."
        ),
    ),
    # -----------------------------------------------------------------------
    # The 4 requires edges wiring the common-docs artifacts to the shipped
    # structural-lint asset (mission ship-structural-lint-as-asset). The lint
    # is now the first built-in ASSET (asset:common-docs-structural-lint); the
    # directive, styleguide, and both curation/scaffold tactics NAME it in
    # prose as the gate that enforces them. The extractor has no frontmatter
    # mechanism to mint an edge to an asset, so these are authored directly in
    # the graph fragments. REQUIRES (not suggests): activating any of these
    # artifacts pulls the shipped lint asset in as a mandatory prerequisite.
    # Note: ASSET is not a charter-activatable kind, so this is not a
    # charter-activate-cascade deployment hook -- `--cascade all` on these
    # artifacts only emits a benign "could not cascade-activate
    # asset/common-docs-structural-lint" warning. The edge's real job is DRG
    # de-orphaning (an un-linked asset that everything references is the
    # un-navigable state the asset kind exists to fix) plus transitive-ref
    # resolution: it is what lets resolve_transitive_refs() return the asset
    # with is_complete=True for consumers walking these artifacts' reference
    # closure, i.e. deployment-manifest completeness rather than an
    # activation trigger.
    # -----------------------------------------------------------------------
    DRGEdge(
        source="directive:DIRECTIVE_042",
        target="asset:common-docs-structural-lint",
        relation=Relation.REQUIRES,
        reason=(
            "DIRECTIVE_042 names the common-docs structural lint as the live "
            "mechanical gate that enforces it; activating the directive "
            "requires the shipped lint asset to be present."
        ),
    ),
    DRGEdge(
        source="styleguide:common-docs",
        target="asset:common-docs-structural-lint",
        relation=Relation.REQUIRES,
        reason=(
            "The common-docs styleguide's tooling rows and quality_test name "
            "the structural lint as their enforcing gate, and its "
            "structural_lint_config: block is the policy the asset loads; "
            "activating the styleguide requires the shipped lint asset."
        ),
    ),
    DRGEdge(
        source="tactic:common-docs-curation",
        target="asset:common-docs-structural-lint",
        relation=Relation.REQUIRES,
        reason=(
            "The common-docs curation tactic directs the agent to run the "
            "structural lint as one of the live gates; activating the tactic "
            "requires the shipped lint asset."
        ),
    ),
    DRGEdge(
        source="tactic:common-docs-scaffold",
        target="asset:common-docs-structural-lint",
        relation=Relation.REQUIRES,
        reason=(
            "The common-docs scaffold tactic relies on the structural lint's "
            "index_completeness check to enforce section-index scaffolding; "
            "activating the tactic requires the shipped lint asset."
        ),
    ),
    # -----------------------------------------------------------------------
    # WP09 (mission doctrine-delivery-reachability-01KYMXD6, T050, FR-015): the
    # reaching edge for the common-docs cluster. The four `requires` edges above
    # de-orphan asset:common-docs-structural-lint by INCIDENCE, but every one of
    # their sources (DIRECTIVE_042, styleguide:common-docs, and the curation /
    # scaffold tactics) was measured action-UNREACHABLE -- the whole documentation-
    # authoring family is a strongly-connected island no action node scopes, so
    # the asset (and the styleguide, and the four common-docs tactics) reached
    # nobody. Incidence is not reachability (contract R-6); this is exactly the
    # PR #3007 failure the mission exists to correct.
    #
    # This SCOPE edge makes DIRECTIVE_042 itself action-reachable: resolve_context
    # walks `scope` at depth 1 from the action, then 042's pre-existing
    # `requires`/`suggests` edges deliver the asset, the styleguide and the four
    # common-docs tactics transitively. Measured with the WP08 helper: d=1 and d=2
    # action-reachable each grow by exactly the seven artefacts 042 heads.
    #
    # C-007 is satisfied without inventing a relationship: (a) DIRECTIVE_042's own
    # `scope:` text -- "Applies whenever a documentation file under the Common Docs
    # root is created, moved, renamed ..." -- attests it governs documentation-file
    # creation, and `documentation/generate`'s `write_docs` step writes docs/**/*.md
    # (creates documentation files); (b) the source is an `action` node, C-007(b)'s
    # second clause. It is NOT a profile/lineage edge, so assert_valid's
    # profile-endpoint rule does not apply.
    #
    # Canonical home / B2 handoff: the canonical surface for an action->artefact
    # `scope` edge is the documentation step-contract action index
    # (missions/built_in_step_contracts/documentation-generate.step-contract.yaml,
    # `delegates_to` candidates), which is outside WP09's owned files. Mission B2
    # (drg-edge-migration-extractor-retirement-01KYFV8C) retires this overlay
    # generator; when it does it MUST migrate this edge into that action index
    # rather than silently dropping it. See
    # docs/plans/doctrine/delivery-reachability-wiring-table.md.
    DRGEdge(
        source="action:documentation/generate",
        target="directive:DIRECTIVE_042",
        relation=Relation.SCOPE,
        reason=(
            "The documentation/generate action creates documentation files "
            "(its write_docs step writes docs/**/*.md), which is DIRECTIVE_042's "
            "stated trigger ('whenever a documentation file under the Common Docs "
            "root is created'); the action is therefore governed by the common-docs "
            "documentation standard. This scope edge is the reaching entry point "
            "that delivers the common-docs styleguide, tactics and structural-lint "
            "asset, which were otherwise a strongly-connected island no action "
            "scoped (WP09 / FR-015)."
        ),
    ),
    # -----------------------------------------------------------------------
    # #3063 family-A (DDD family), operator interview outcome. The operator has
    # ATTESTED these relationships (C-007(a) satisfied by operator ruling); the
    # hub is paradigm:domain-driven-design. Three kinds of edge land here:
    #
    #   1. ONE reaching `scope` edge, action:software-dev/specify -> the DDD
    #      paradigm. This is the edge that changes action reachability: it makes
    #      the DDD paradigm action-reachable at the specify grain, and the
    #      paradigm's `requires` edges below then deliver the whole family
    #      transitively (resolve_context walks scope at depth 1 from the action,
    #      then requires transitively). Measured with the WP08 helper: d=1 and
    #      d=2 action-reachable each grow by exactly the twelve artefacts the
    #      paradigm heads (the paradigm, its two pre-existing directive_refs
    #      DIRECTIVE_031/032, and the ten members below minus
    #      strategic-domain-classification, which was already reachable).
    #
    #      NOTE the relation is `scope`, NOT `suggests`. The #3063 wiring table
    #      row named `suggests`, but that is measured INERT: resolve_context
    #      walks `suggests` only FROM scope-resolved artifacts, never from the
    #      action node itself (query.resolve_context steps 2/3 seed from
    #      `scoped_artifacts`), so a `suggests` edge sourced at an action changes
    #      no reachability. Only a `scope` edge from an action delivers — exactly
    #      the WP09 precedent (action:documentation/generate --scope--> 042). The
    #      #3063 §3 mandate ("this edge DOES change action reachability; update
    #      the pinned unreachable sets") is satisfiable only by `scope`, so the
    #      table's `suggests` is corrected to `scope` here and the discrepancy is
    #      recorded in docs/plans/doctrine/delivery-reachability-wiring-table.md.
    #
    #      C-007 without inventing a relationship: (a) the DDD paradigm's own
    #      summary attests strategic design ("aligning code with a deep model of
    #      the business domain"), which is what the software-dev specify step
    #      does ("align the mission design with architectural intent"); (b) the
    #      source is an `action` node, C-007(b)'s second clause. Canonical home /
    #      B2 handoff: an action->artefact `scope` edge belongs in the
    #      software-dev specify step-contract action index; mission B2 migrates
    #      it when it retires this overlay generator.
    #
    #   2. TEN `requires` edges, DDD paradigm -> each genuine DDD family member.
    #      Each target's OWN text attests DDD membership (C-007a): bounded-context
    #      identification / canvas-fill / boundary-inference and context-mapping
    #      (Evans strategic design), strategic-domain-classification (Core/
    #      Supporting/Generic subdomain), aggregate-boundary-design /
    #      entity-value-object-classification / domain-event-capture /
    #      anti-corruption-layer (Evans tactical patterns) and the
    #      aggregate-design-rules styleguide. EXCLUDED as non-attested:
    #      reference-architectural-patterns (its own text is general reference-
    #      architecture selection by quality attributes, not DDD) and the state/
    #      UI tactics compositional-stream-boundaries / cross-cutting-state-via-
    #      store / atomic-state-ownership.
    #
    #   3. THREE `suggests` edges, agent profiles -> the DDD paradigm. These are
    #      COMPOSITION-ONLY / INERT under today's traversal: the profile channel
    #      walks {requires, specializes_from} only, and the action channel does
    #      not seed from profiles, so a profile--suggests-->paradigm edge changes
    #      NO reachability (measured: profile channel 39->39, unchanged). They
    #      record the attested "an architect/pattern-scout/reducer should reach
    #      DDD when designing or inspecting code" relationship for when a future
    #      channel follows it.
    #
    # DEFERRED (NOT authored here): the DDD<->documentation mutual-reinforcement
    # edge — gated on the upcoming value-based edge properties (B1). Noted in the
    # wiring-table doc as pending.
    # -----------------------------------------------------------------------
    DRGEdge(
        source="action:software-dev/specify",
        target="paradigm:domain-driven-design",
        relation=Relation.SCOPE,
        reason=(
            "The software-dev specify step aligns the mission design with "
            "architectural intent; Domain-Driven Design is the paradigm that "
            "governs aligning that design with a deep model of the business "
            "domain (DDD's own summary). This scope edge is the reaching entry "
            "point that makes the DDD paradigm action-reachable at the specify "
            "grain and delivers its strategic-design family transitively "
            "(#3063 family-A). It is `scope` not `suggests` because a suggests "
            "edge sourced at an action node is inert under resolve_context."
        ),
    ),
    DRGEdge(
        source="paradigm:domain-driven-design",
        target="tactic:bounded-context-identification",
        relation=Relation.REQUIRES,
        reason=(
            "Bounded Context Identification is DDD strategic design (Evans): "
            "drawing boundaries around regions where a single consistent model "
            "and ubiquitous language apply. Activating DDD pulls it in."
        ),
    ),
    DRGEdge(
        source="paradigm:domain-driven-design",
        target="tactic:context-mapping-classification",
        relation=Relation.REQUIRES,
        reason=(
            "Context Mapping Classification is DDD strategic design: it "
            "classifies every relationship between bounded contexts using the "
            "canonical DDD context-mapping patterns. Activating DDD pulls it in."
        ),
    ),
    DRGEdge(
        source="paradigm:domain-driven-design",
        target="tactic:context-boundary-inference",
        relation=Relation.REQUIRES,
        reason=(
            "Context Boundary Inference is DDD strategic design: it detects "
            "bounded-context boundaries from team ownership and terminology "
            "conflicts, documenting ubiquitous language per context. Activating "
            "DDD pulls it in."
        ),
    ),
    DRGEdge(
        source="paradigm:domain-driven-design",
        target="tactic:bounded-context-canvas-fill",
        relation=Relation.REQUIRES,
        reason=(
            "Bounded Context Canvas Fill is DDD strategic design: it guides "
            "completing a Bounded Context Canvas (DDD Crew v5) capturing a "
            "context's strategic classification and ubiquitous language. "
            "Activating DDD pulls it in."
        ),
    ),
    DRGEdge(
        source="paradigm:domain-driven-design",
        target="tactic:strategic-domain-classification",
        relation=Relation.REQUIRES,
        reason=(
            "Strategic Domain Classification is DDD strategic design (Evans): "
            "classifying each bounded context as Core, Supporting or Generic "
            "subdomain to guide investment. Activating DDD pulls it in. (Already "
            "action-reachable via paula-patterns' review tactic; this edge "
            "records the paradigm membership without moving its reachability.)"
        ),
    ),
    DRGEdge(
        source="paradigm:domain-driven-design",
        target="tactic:aggregate-boundary-design",
        relation=Relation.REQUIRES,
        reason=(
            "Aggregate Boundary Design is DDD tactical design (Evans / Vernon): "
            "defining transactional consistency boundaries and aggregate roots "
            "within a bounded context. Activating DDD pulls it in."
        ),
    ),
    DRGEdge(
        source="paradigm:domain-driven-design",
        target="tactic:entity-value-object-classification",
        relation=Relation.REQUIRES,
        reason=(
            "Entity vs Value Object Classification is DDD tactical design "
            "(Evans): classifying each domain object as an Entity or a Value "
            "Object. Activating DDD pulls it in."
        ),
    ),
    DRGEdge(
        source="paradigm:domain-driven-design",
        target="tactic:domain-event-capture",
        relation=Relation.REQUIRES,
        reason=(
            "Domain Event Capture is DDD tactical design (Evans / Fowler): "
            "funnelling significant state changes through immutable Domain "
            "Event objects. Activating DDD pulls it in."
        ),
    ),
    DRGEdge(
        source="paradigm:domain-driven-design",
        target="tactic:anti-corruption-layer",
        relation=Relation.REQUIRES,
        reason=(
            "The Anti-Corruption Layer is a DDD context-mapping pattern (Evans): "
            "a translation layer that keeps a foreign system's model from "
            "corrupting the domain's ubiquitous language. Activating DDD pulls "
            "it in."
        ),
    ),
    DRGEdge(
        source="paradigm:domain-driven-design",
        target="styleguide:aggregate-design-rules",
        relation=Relation.REQUIRES,
        reason=(
            "The Aggregate Design Rules styleguide encodes DDD tactical "
            "aggregate discipline (reference by identity, keep aggregates small, "
            "eventual consistency between aggregates via domain events). "
            "Activating DDD pulls it in."
        ),
    ),
    DRGEdge(
        source="agent_profile:architect-alphonso",
        target="paradigm:domain-driven-design",
        relation=Relation.SUGGESTS,
        reason=(
            "When designing and reviewing significant code changes, the "
            "architect should reach Domain-Driven Design. Composition-only under "
            "today's traversal (the profile channel walks requires/"
            "specializes_from only), authored per the #3063 operator attestation."
        ),
    ),
    DRGEdge(
        source="agent_profile:paula-patterns",
        target="paradigm:domain-driven-design",
        relation=Relation.SUGGESTS,
        reason=(
            "When investigating or inspecting code, the pattern scout should "
            "reach Domain-Driven Design. Composition-only under today's "
            "traversal, authored per the #3063 operator attestation."
        ),
    ),
    DRGEdge(
        source="agent_profile:randy-reducer",
        target="paradigm:domain-driven-design",
        relation=Relation.SUGGESTS,
        reason=(
            "When investigating or inspecting code, the reducer should reach "
            "Domain-Driven Design. Composition-only under today's traversal, "
            "authored per the #3063 operator attestation."
        ),
    ),
    # -----------------------------------------------------------------------
    # #3063 family-B (REFACTORING family), operator interview outcome. The
    # operator has ATTESTED these relationships; the hub is a NEW built-in
    # directive, `directive:DISCIPLINED_REFACTORING` (authored as
    # src/doctrine/directives/built-in/disciplined-refactoring.directive.yaml).
    #
    # URN CASING NOTE: the wiring instruction named the hub
    # `directive:disciplined-refactoring` (lower-kebab). A directive node's URN is
    # derived from its artifact `id`, and the Directive model requires `id` to
    # match `^[A-Z][A-Z0-9_-]*$` while `id_normalizer.normalize_directive_id`
    # upper-cases any non-numeric slug — so the only URN a real directive artifact
    # can yield here is `directive:DISCIPLINED_REFACTORING` (exactly the
    # `directive:RECONCILE_CHANGE_SCOPE_TENSIONS` precedent). The lower-kebab form
    # is unreachable through the schema; the canonical URN is corrected to
    # UPPER_SNAKE here and recorded in
    # docs/plans/doctrine/delivery-reachability-wiring-table.md.
    #
    # This family is INERT under today's traversal (composition-only) — measured,
    # not assumed:
    #
    #   * SEVEN `suggests` edges, DISCIPLINED_REFACTORING -> each refactoring
    #     tactic, each carrying a per-tactic `when` = the applicability/"problem"
    #     the tactic solves (refactoring.guru-style "when to consider this
    #     refactor"), derived from the tactic's OWN purpose/first-step text (not
    #     invented). These deliver nothing under the action channel: the directive
    #     is scoped by no action, so `resolve_context` never reaches it, and
    #     `suggests` is only walked FROM scope-resolved artifacts — so its outbound
    #     `suggests` edges are never traversed. The seven tactics stay
    #     action-unreachable (they already were).
    #
    #   * SEVEN `suggests` edges, each implementer-role agent profile ->
    #     DISCIPLINED_REFACTORING, all sharing the attested `when` "when tidying
    #     code, encountering long classes/methods, or discovering convoluted
    #     logic". These are inert in the profile channel too: that channel walks
    #     {requires, specializes_from} only, never `suggests`. The implementer
    #     profiles are every built-in profile whose role is `implementer`
    #     (python-pedro is primary): frontend-freddy, generic-agent,
    #     implementer-ivan, java-jenny, node-norris, python-pedro, randy-reducer.
    #
    # Net reachability move: NONE. `directive:DISCIPLINED_REFACTORING` is a new
    # built-in directive that this project's charter does NOT activate, so it
    # never enters the `_activated()` universe the reachability pins subtract
    # from; the fourteen edges are `suggests` on both channels, which neither
    # channel follows into delivery. Measured with the WP08 helper: the
    # `_ACTION_UNREACHABLE_D1`/`D2`, `_PROFILE_UNREACHABLE` and `_PROFILE_RESCUES`
    # sets are UNCHANGED. Only composition counts move (one new directive node via
    # extraction + fourteen overlay edges); ledgered in the wiring-table doc and
    # test_extractor_projection's composition ledger.
    #
    # DEFERRED (recorded, NOT authored here): (1) the refactoring tactics remain
    # in the delivery-reachability DEFERRED set — their delivery needs the
    # profile-channel walk to follow `suggests` (topology authored, delivery
    # pending fast-follow); (2) an `anti_pattern`-authoring companion (each code
    # smell -> the refactor that resolves it) is a doctrine-CONTENT decision left
    # to the fast-follow, not authored in this pass.
    # -----------------------------------------------------------------------
    DRGEdge(
        source="directive:DISCIPLINED_REFACTORING",
        target="tactic:refactoring-encapsulate-record",
        relation=Relation.SUGGESTS,
        when=(
            "a raw data record (a dict, plain object, or mutably-used named "
            "tuple) is accessed by field name from many call sites, and that "
            "direct access blocks adding validation, renaming fields, or changing "
            "the internal representation"
        ),
        reason=(
            "Disciplined refactoring suggests Encapsulate Record when the smell is "
            "an unencapsulated data record; the `when` is the tactic's own stated "
            "applicability. Composition-only under today's traversal."
        ),
    ),
    DRGEdge(
        source="directive:DISCIPLINED_REFACTORING",
        target="tactic:refactoring-encapsulate-variable",
        relation=Relation.SUGGESTS,
        when=(
            "a widely-accessed module-level or global variable (or public class "
            "attribute) is read and written from many locations and needs a single "
            "chokepoint for monitoring, validation, or a later change of type"
        ),
        reason=(
            "Disciplined refactoring suggests Encapsulate Variable when the smell "
            "is a globally-accessed variable with no chokepoint; the `when` is the "
            "tactic's own stated applicability. Composition-only under today's "
            "traversal."
        ),
    ),
    DRGEdge(
        source="directive:DISCIPLINED_REFACTORING",
        target="tactic:refactoring-extract-first-order-concept",
        relation=Relation.SUGGESTS,
        when=(
            "an important concept is implicit, duplicated, or scattered across the "
            "code with no explicit name or single home"
        ),
        reason=(
            "Disciplined refactoring suggests Extract First-Order Concept when the "
            "smell is a hidden/duplicated concept that should be named; the `when` "
            "is the tactic's own stated applicability. Composition-only under "
            "today's traversal."
        ),
    ),
    DRGEdge(
        source="directive:DISCIPLINED_REFACTORING",
        target="tactic:refactoring-move-field",
        relation=Relation.SUGGESTS,
        when=(
            "a field is read and modified more by another class than the one that "
            "declares it, so data ownership has drifted"
        ),
        reason=(
            "Disciplined refactoring suggests Move Field when the smell is a field "
            "living on the wrong owner; the `when` is the tactic's own stated "
            "applicability. Composition-only under today's traversal."
        ),
    ),
    DRGEdge(
        source="directive:DISCIPLINED_REFACTORING",
        target="tactic:refactoring-move-method",
        relation=Relation.SUGGESTS,
        when=(
            "a method uses more of another class's data and behaviour than its own "
            "host's (feature envy)"
        ),
        reason=(
            "Disciplined refactoring suggests Move Method when the smell is feature "
            "envy; the `when` is the tactic's own stated applicability (its first "
            "step confirms feature envy and target ownership). Composition-only "
            "under today's traversal."
        ),
    ),
    DRGEdge(
        source="directive:DISCIPLINED_REFACTORING",
        target="tactic:refactoring-state-pattern-for-behavior",
        relation=Relation.SUGGESTS,
        when=(
            "a class's methods are full of conditionals branching on the same "
            "internal state variable (enum, status flag, boolean), and behaviour is "
            "driven by lifecycle state transitions"
        ),
        reason=(
            "Disciplined refactoring suggests State Pattern for Behavior when the "
            "smell is sprawling conditionals switching on an object's lifecycle "
            "state; the `when` is the tactic's own stated applicability. "
            "Composition-only under today's traversal."
        ),
    ),
    DRGEdge(
        source="directive:DISCIPLINED_REFACTORING",
        target="tactic:refactoring-strangler-fig",
        relation=Relation.SUGGESTS,
        when=(
            "a legacy component or code path must be replaced incrementally — "
            "running the new implementation alongside the old and rerouting callers "
            "one at a time — because a single-step cutover is too risky"
        ),
        reason=(
            "Disciplined refactoring suggests Strangler Fig when the smell is a "
            "legacy path that cannot be replaced in one safe step; the `when` is "
            "the tactic's own stated applicability. Composition-only under today's "
            "traversal."
        ),
    ),
    DRGEdge(
        source="agent_profile:frontend-freddy",
        target="directive:DISCIPLINED_REFACTORING",
        relation=Relation.SUGGESTS,
        when="when tidying code, encountering long classes/methods, or discovering convoluted logic",
        reason=(
            "An implementer-role profile should reach the disciplined-refactoring "
            "directive when restructuring code. Composition-only under today's "
            "traversal (the profile channel walks requires/specializes_from only), "
            "authored per the #3063 family-B operator attestation."
        ),
    ),
    DRGEdge(
        source="agent_profile:generic-agent",
        target="directive:DISCIPLINED_REFACTORING",
        relation=Relation.SUGGESTS,
        when="when tidying code, encountering long classes/methods, or discovering convoluted logic",
        reason=(
            "An implementer-role profile should reach the disciplined-refactoring "
            "directive when restructuring code. Composition-only under today's "
            "traversal, authored per the #3063 family-B operator attestation."
        ),
    ),
    DRGEdge(
        source="agent_profile:implementer-ivan",
        target="directive:DISCIPLINED_REFACTORING",
        relation=Relation.SUGGESTS,
        when="when tidying code, encountering long classes/methods, or discovering convoluted logic",
        reason=(
            "An implementer-role profile should reach the disciplined-refactoring "
            "directive when restructuring code. Composition-only under today's "
            "traversal, authored per the #3063 family-B operator attestation."
        ),
    ),
    DRGEdge(
        source="agent_profile:java-jenny",
        target="directive:DISCIPLINED_REFACTORING",
        relation=Relation.SUGGESTS,
        when="when tidying code, encountering long classes/methods, or discovering convoluted logic",
        reason=(
            "An implementer-role profile should reach the disciplined-refactoring "
            "directive when restructuring code. Composition-only under today's "
            "traversal, authored per the #3063 family-B operator attestation."
        ),
    ),
    DRGEdge(
        source="agent_profile:node-norris",
        target="directive:DISCIPLINED_REFACTORING",
        relation=Relation.SUGGESTS,
        when="when tidying code, encountering long classes/methods, or discovering convoluted logic",
        reason=(
            "An implementer-role profile should reach the disciplined-refactoring "
            "directive when restructuring code. Composition-only under today's "
            "traversal, authored per the #3063 family-B operator attestation."
        ),
    ),
    DRGEdge(
        source="agent_profile:python-pedro",
        target="directive:DISCIPLINED_REFACTORING",
        relation=Relation.SUGGESTS,
        when="when tidying code, encountering long classes/methods, or discovering convoluted logic",
        reason=(
            "The primary implementer-role profile should reach the "
            "disciplined-refactoring directive when restructuring code. "
            "Composition-only under today's traversal, authored per the #3063 "
            "family-B operator attestation."
        ),
    ),
    DRGEdge(
        source="agent_profile:randy-reducer",
        target="directive:DISCIPLINED_REFACTORING",
        relation=Relation.SUGGESTS,
        when="when tidying code, encountering long classes/methods, or discovering convoluted logic",
        reason=(
            "An implementer-role profile should reach the disciplined-refactoring "
            "directive when restructuring code. Composition-only under today's "
            "traversal, authored per the #3063 family-B operator attestation."
        ),
    ),
    # -----------------------------------------------------------------------
    # #3063 family-C (ARCHITECTURE-DOCS / DIAGRAMMING family), operator
    # interview outcome. The operator has ATTESTED these relationships; the hub
    # is a NEW built-in directive, `directive:USE_C4_MODEL_TECHNIQUES` (authored
    # as src/doctrine/directives/built-in/use-c4-model-techniques.directive.yaml).
    #
    # URN CASING NOTE (same rule as family-B's DISCIPLINED_REFACTORING): the
    # wiring named the hub `directive:use-c4-model-techniques` (lower-kebab). A
    # directive node's URN is derived from its artifact `id`, and the Directive
    # model requires `id` to match `^[A-Z][A-Z0-9_-]*$` while
    # `id_normalizer.normalize_directive_id` upper-cases any non-numeric slug — so
    # the only URN a real directive artifact can yield is
    # `directive:USE_C4_MODEL_TECHNIQUES` (the RECONCILE_CHANGE_SCOPE_TENSIONS /
    # DISCIPLINED_REFACTORING precedent). Recorded in
    # docs/plans/doctrine/delivery-reachability-wiring-table.md.
    #
    # This family is INERT under today's traversal (composition-only) — measured,
    # not assumed:
    #
    #   * SEVEN `suggests` edges, USE_C4_MODEL_TECHNIQUES -> each attested
    #     architecture-documentation technique, each carrying a per-member `when`
    #     grounded in the member's OWN purpose/scope text (not invented). These
    #     deliver nothing under the action channel: the directive is scoped by no
    #     action, so `resolve_context` never reaches it, and `suggests` is only
    #     walked FROM scope-resolved artifacts. The members stay action-unreachable
    #     (they already were — all seven are in the delivery-reachability DEFERRED
    #     set).
    #
    #   * ONE `suggests` edge, USE_C4_MODEL_TECHNIQUES -> paradigm:domain-driven-
    #     design: the reinforcement ("supporting") bridge the operator attested.
    #     `suggests` is the closest ATTESTED relation for "supporting/reinforces"
    #     (a soft, non-mandatory pointer) — no new relation kind was invented. It
    #     is INBOUND to the DDD paradigm, which Family A already made action-
    #     reachable; it therefore delivers nothing new (a directive->paradigm edge
    #     does not make the SOURCE reachable) and moves no pin. The documentation-
    #     family leg of the "supporting the documentation and DDD paradigms"
    #     instruction needs no separate edge: `paradigm:c4-incremental-detail-
    #     modeling` IS the documentation/architecture-modelling paradigm and is
    #     already a member above, so the documentation leg is covered by the member
    #     edge and only the DDD leg is added here.
    #
    #   * ONE `suggests` edge, agent_profile:architect-alphonso ->
    #     USE_C4_MODEL_TECHNIQUES, `when` = "documenting or reviewing system
    #     architecture" (alphonso's attested scope: roles=architect, capabilities
    #     system-design / architecture-review / component-design). Inert in the
    #     profile channel too: that channel walks {requires, specializes_from}
    #     only, never `suggests`.
    #
    # EXCLUDED as non-attested (reported to the operator): the #3063 candidate
    # `procedure:documentation-gap-prioritization`. Its own text triages
    # documentation gaps by user impact across ALL doc types (tutorials, how-tos,
    # reference, explanation) — a documentation-project-management technique, not a
    # C4 / architecture-documentation / diagramming one. No member edge is
    # authored for it; it stays in the DEFERRED set.
    #
    # Net reachability move: NONE. `directive:USE_C4_MODEL_TECHNIQUES` is a new
    # built-in directive this project's charter does NOT activate, so it never
    # enters the `_activated()` universe the reachability pins subtract from; all
    # nine edges are `suggests` on channels that do not follow `suggests` into
    # delivery. Measured with the WP08 helper: `_ACTION_UNREACHABLE_D1`/`D2`,
    # `_PROFILE_UNREACHABLE` and `_PROFILE_RESCUES` are UNCHANGED. Only composition
    # counts move (one new directive node via extraction + nine overlay edges);
    # ledgered in the wiring-table doc and test_extractor_projection's ledger.
    #
    # DEFERRED (recorded, NOT authored here): the seven architecture-doc technique
    # members remain in the delivery-reachability DEFERRED set — topology authored,
    # delivery pending fast-follow (their delivery needs the directive to be
    # action-scoped, or the profile channel to follow `suggests`).
    # -----------------------------------------------------------------------
    DRGEdge(
        source="directive:USE_C4_MODEL_TECHNIQUES",
        target="paradigm:c4-incremental-detail-modeling",
        relation=Relation.SUGGESTS,
        when=(
            "communicating a system's architecture to more than one audience at "
            "more than one level of detail, so it must be broken into progressive "
            "zoom levels (System Context, Container, Component, Code) rather than a "
            "single all-in-one diagram"
        ),
        reason=(
            "The C4 hub suggests the C4 incremental-detail paradigm as its core "
            "mental model; the `when` is the paradigm's own stated purpose "
            "(progressive zoom, right detail per audience). Composition-only under "
            "today's traversal."
        ),
    ),
    DRGEdge(
        source="directive:USE_C4_MODEL_TECHNIQUES",
        target="tactic:c4-zoom-in-architecture-documentation",
        relation=Relation.SUGGESTS,
        when=(
            "actually drawing the architecture diagrams — starting from the System "
            "Context and zooming in to Container and Component levels only where "
            "additional detail adds value"
        ),
        reason=(
            "The C4 hub suggests the zoom-in documentation workflow as the concrete "
            "step-by-step technique; the `when` is the tactic's own stated purpose. "
            "Composition-only under today's traversal."
        ),
    ),
    DRGEdge(
        source="directive:USE_C4_MODEL_TECHNIQUES",
        target="tactic:architecture-diagram-review-checklist",
        relation=Relation.SUGGESTS,
        when=(
            "an architecture diagram is about to be shared, committed, or included "
            "in documentation and must communicate to its audience without a verbal "
            "walkthrough (title, legend, typed described elements, labelled "
            "unidirectional relationships)"
        ),
        reason=(
            "The C4 hub suggests the diagram review checklist as its quality gate; "
            "the `when` is the tactic's own stated purpose. Composition-only under "
            "today's traversal."
        ),
    ),
    DRGEdge(
        source="directive:USE_C4_MODEL_TECHNIQUES",
        target="toolguide:mermaid-diagramming",
        relation=Relation.SUGGESTS,
        when=(
            "rendering the architecture diagrams as text-based, version-controlled "
            "diagram-as-code in Mermaid so they diff and review beside the code"
        ),
        reason=(
            "The C4 hub suggests the Mermaid toolguide as one text-based rendering "
            "option satisfying its 'keep diagrams as diagram-as-code' rule; the "
            "`when` is the toolguide's own stated scope. Composition-only under "
            "today's traversal."
        ),
    ),
    DRGEdge(
        source="directive:USE_C4_MODEL_TECHNIQUES",
        target="toolguide:plantuml-diagramming",
        relation=Relation.SUGGESTS,
        when=(
            "rendering the architecture diagrams as text-based, version-controlled "
            "diagram-as-code in PlantUML so they diff and review beside the code"
        ),
        reason=(
            "The C4 hub suggests the PlantUML toolguide as the other text-based "
            "rendering option satisfying its 'keep diagrams as diagram-as-code' "
            "rule; the `when` is the toolguide's own stated scope. Composition-only "
            "under today's traversal."
        ),
    ),
    DRGEdge(
        source="directive:USE_C4_MODEL_TECHNIQUES",
        target="procedure:drill-down-documentation",
        relation=Relation.SUGGESTS,
        when=(
            "capturing decisions, documentation, and architecture descriptions at a "
            "consistent abstraction level (organisational, architecture, design, "
            "code) with upward and downward traceability, rather than mixing levels "
            "in one artifact"
        ),
        reason=(
            "The C4 hub suggests the drill-down documentation procedure as the "
            "abstraction-level discipline that keeps each artifact at one C4 zoom "
            "level; the `when` is the procedure's own stated purpose/entry "
            "condition. Composition-only under today's traversal."
        ),
    ),
    DRGEdge(
        source="directive:USE_C4_MODEL_TECHNIQUES",
        target="tactic:code-documentation-analysis",
        relation=Relation.SUGGESTS,
        when=(
            "reverse-engineering or reviewing an existing system's architecture — "
            "extracting terminology from its code and documentation to surface "
            "implicit context boundaries before they calcify into accidental "
            "coupling"
        ),
        reason=(
            "The C4 hub suggests code/documentation analysis as the technique for "
            "discovering an existing system's architecture (implicit boundaries) "
            "prior to documenting it; the `when` is the tactic's own stated purpose "
            "(architectural review / boundary discovery). Composition-only under "
            "today's traversal."
        ),
    ),
    DRGEdge(
        source="directive:USE_C4_MODEL_TECHNIQUES",
        target="paradigm:domain-driven-design",
        relation=Relation.SUGGESTS,
        when=(
            "the architecture being documented is organised around a domain model, "
            "so its container/component boundaries should reflect bounded contexts "
            "and the ubiquitous language"
        ),
        reason=(
            "The reinforcement ('supporting') bridge the #3063 operator attested: "
            "the C4 architecture-documentation hub suggests the Domain-Driven Design "
            "paradigm so architecture diagrams and domain boundaries reinforce each "
            "other. `suggests` is the closest attested relation for a soft "
            "supporting/reinforces pointer (no new relation kind invented). INBOUND "
            "to the already-action-reachable DDD paradigm (Family A), so it delivers "
            "nothing new and moves no pin — composition-only under today's "
            "traversal. The documentation-family leg of 'supporting the "
            "documentation and DDD paradigms' is already covered by the member edge "
            "to paradigm:c4-incremental-detail-modeling, which IS the documentation/"
            "architecture-modelling paradigm."
        ),
    ),
    DRGEdge(
        source="agent_profile:architect-alphonso",
        target="directive:USE_C4_MODEL_TECHNIQUES",
        relation=Relation.SUGGESTS,
        when="documenting or reviewing system architecture",
        reason=(
            "The architect profile should reach the C4 architecture-documentation "
            "hub when documenting or reviewing system architecture (alphonso's "
            "attested scope: system-design / architecture-review / component-"
            "design). Composition-only under today's traversal (the profile channel "
            "walks requires/specializes_from only), authored per the #3063 family-C "
            "operator attestation."
        ),
    ),
)


def hand_authored_node_urns() -> frozenset[str]:
    """URNs of every node that exists only because it was hand-authored."""
    return frozenset(n.urn for n in HAND_AUTHORED_NODES)


def hand_authored_edge_keys() -> frozenset[tuple[str, str, str]]:
    """``(source, target, relation)`` triples for every hand-authored edge."""
    return frozenset((e.source, e.target, e.relation.value) for e in HAND_AUTHORED_EDGES)


def merge_hand_authored_overlay(graph: DRGGraph) -> DRGGraph:
    """Return a new graph = *graph* plus the enumerated hand-authored overlay.

    Re-sorts nodes/edges identically to ``generate_graph``'s own canonical
    ordering (nodes by URN; edges by ``(source, target, relation)``) and
    re-validates the result, so the returned graph is exactly what a
    "pure extraction + the known hand-authored additions" reference should
    look like.
    """
    nodes_by_urn: dict[str, DRGNode] = {n.urn: n for n in graph.nodes}
    for node in HAND_AUTHORED_NODES:
        nodes_by_urn[node.urn] = node

    edges_by_triple: dict[tuple[str, str, str], DRGEdge] = {
        (e.source, e.target, e.relation.value): e for e in graph.edges
    }
    for edge in HAND_AUTHORED_EDGES:
        edges_by_triple[(edge.source, edge.target, edge.relation.value)] = edge

    merged = DRGGraph(
        schema_version=graph.schema_version,
        generated_at=graph.generated_at,
        generated_by=graph.generated_by,
        nodes=sorted(nodes_by_urn.values(), key=lambda n: n.urn),
        edges=sorted(
            edges_by_triple.values(),
            key=lambda e: (e.source, e.target, e.relation.value),
        ),
    )
    assert_valid(merged)
    return merged


def generate_reference_graph_with_overlay(doctrine_root: Path) -> DRGGraph:
    """The in-memory freshness/equality reference: pure extraction + overlay.

    Regenerates *doctrine_root* into a throw-away scratch directory (never
    read back), then merges in :data:`HAND_AUTHORED_NODES` /
    :data:`HAND_AUTHORED_EDGES`. This is the non-vacuous reference every
    shipped-graph comparison should use now that the extractor is no longer
    the sole source of shipped content (WP02/WP03).
    """
    from doctrine.drg.migration.extractor import generate_graph

    with tempfile.TemporaryDirectory() as scratch:
        pure = generate_graph(doctrine_root, Path(scratch) / "graph.yaml")
    return merge_hand_authored_overlay(pure)


def write_reference_graph_with_overlay(doctrine_root: Path, output_path: Path) -> DRGGraph:
    """Like :func:`generate_reference_graph_with_overlay`, but also writes the
    merged reference as per-kind fragments beside *output_path* (via the
    extractor's own canonical writer), so it is byte-comparable against the
    committed shipped graph.
    """
    from doctrine.drg.migration.extractor import _write_graph_yaml

    merged = generate_reference_graph_with_overlay(doctrine_root)
    _write_graph_yaml(merged, output_path)
    return merged
