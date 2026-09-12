# Mission Specification: Doctrine Delivery Activation Fast-Follow

**Mission Branch**: `feat/doctrine-delivery-activation`
**Created**: 2026-07-29
**Status**: Draft
**Input**: Fast-follow to the doctrine-delivery-reachability slice (PR #3070, merged to
upstream/main; coverage tail #3077). Animate the inert #3063-authored doctrine delivery
topology so `suggests` edges actually deliver, reconcile the reachability pins/wiring
table, retire the forward-API allowlist as symbols are wired, deliver Family C templates
and Family B anti-patterns via edges, and close the trailing code-hygiene tickets.

## Context & Framing

This is an **engineering mission on the doctrine delivery engine**, not a user-facing
product feature. The "user" in the scenarios below is a **consuming AI agent** loading an
agent profile's action-scoped doctrine context through the **profile channel**, plus the
**maintainers** who keep the reachability pins, wiring table, and dead-symbol allowlist
honest. Requirements reference doctrine domain concepts (`suggests` edges, `when`
conditions, the profile channel, reachability partitions) — these are the domain language
of the delivery engine, not incidental implementation detail.

PR #3070 authored the delivery-rail forward API and the A–E `suggests` edge families in
the DRG, but the profile-channel reachability walk still traverses only
`{requires, specializes_from}`. The authored edges are therefore **inert**: the doctrine
they wire never reaches the consuming agent. This mission makes the topology live.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Profile channel delivers `suggests`-linked doctrine with `when` conditions (Priority: P1)

A consuming agent loads an agent profile's action-scoped doctrine context (e.g.
`architect-alphonso` for a design action). Today it receives only the `requires`- and
`specializes_from`-reachable doctrine. The A–E edge families that #3063 authored via
`suggests` (domain-driven-design for the architects; DISCIPLINED_REFACTORING →
refactoring-* tactics for implementers; USE_C4_MODEL_TECHNIQUES → C4 techniques;
reasons-canvas + terminology links) never arrive. This story extends the profile-channel
walk to follow `suggests` edges and surface each edge's `when` clause to the agent as the
applicability condition of the delivered doctrine — delivered as links with a `when`
label, not as an eager dump of every suggested body.

**Why this priority**: This is THE delivery vector. Without it, every other authored edge
stays inert and the #3063 investment delivers nothing. Items 2–5 all depend on the walk
following `suggests`.

**Independent Test**: Resolve the profile channel for `architect-alphonso` (and an
implementer profile) via the delivery-rail helper (`action_channel_reachable` /
`doctrine.drg.query.resolve_context`) and assert the A/B/C/E artefacts are now reachable
and each carries its edge's `when` clause as the surfaced applicability condition.

**Acceptance Scenarios**:

1. **Given** the profile channel walks `{requires, specializes_from}` only, **When** the
   walk is extended to include `suggests`, **Then** `profile_channel_reachable(graph,
   {agent_profile:architect-alphonso})` surfaces `domain-driven-design` (Family A) with the
   edge's `when` clause — asserted on the profile channel, never `resolve_context`.
2. **Given** an implementer profile linked `→ DISCIPLINED_REFACTORING → refactoring-*`
   tactics via `suggests`, **When** its channel is resolved, **Then** the refactoring
   tactics are reachable (Family B) with their `when` conditions surfaced.
3. **Given** a `suggests` edge with no explicit `when` clause, **When** the channel is
   resolved, **Then** the stated-default applicability condition is surfaced (never an
   empty/undefined condition).
4. **Given** a suggested artefact already delivered through another edge in the same
   context, **When** the channel is resolved, **Then** it is not duplicated.

### User Story 2 - Reachability pins & wiring table reconciled to the live topology (Priority: P1)

Once the walk follows `suggests`, the set of profile-reachable artefacts changes. A
maintainer must re-measure that set with the canonical helper (never a hand-rolled walk),
update the reachability test pins (`_PROFILE_UNREACHABLE` / `_PROFILE_RESCUES`), and update
the wiring table so the deferred set drops from 50 — with a composition-ledger entry for
every golden number that moves, so no count changes silently.

**Why this priority**: The reachability tests are the executable truth of what delivers;
leaving them stale either false-greens (pins say unreachable while runtime delivers) or
false-reds. The wiring table is the human-readable ledger of delivery status.

**Independent Test**: Run the reachability suite; confirm the newly-reachable artefacts
have moved from `_PROFILE_UNREACHABLE` to `_PROFILE_RESCUES` (or off the deferred list),
that each moved count has a matching ledger entry, and that the measurement used the
helper, not an ad-hoc traversal.

**Acceptance Scenarios**:

1. **Given** the walk now follows `suggests`, **When** reachability is re-measured via
   `action_channel_reachable`, **Then** `_PROFILE_UNREACHABLE` / `_PROFILE_RESCUES` in the
   reachability test reflect the newly profile-reachable artefacts.
2. **Given** the wiring table lists a deferred set of 50, **When** the walk delivers the
   A/B/C/E families, **Then** the deferred count drops and the table records the new count.
3. **Given** a golden reachability count changes, **When** the change is committed, **Then**
   a composition-ledger entry accompanies it (NFR-002) — no silent golden movement.

### User Story 3 - Forward-API allowlist retired as symbols are wired (Priority: P1)

The parent slice left 9 delivery-rail forward-API symbols allowlisted in the dead-symbols
gate because they were authored ahead of their consumer. As this mission wires each into
runtime, the maintainer removes it from `_CATEGORY_C_DELIVERY_RAIL_FORWARD_API` (and its
`_baselines.yaml` mirror row) and confirms the dead-symbols gate stays green with the
symbol now genuinely `src`-consumed. Any symbol not wired in this mission stays allowlisted
with a note.

**Why this priority**: The allowlist is a temporary scaffold; retiring it as consumption
lands is how the dead-code gate keeps meaning. Leaving a wired symbol on the allowlist
would false-green a now-live symbol as "dead".

**Independent Test**: For each of the 9 symbols wired this mission, assert it is imported
and used in `src/` and absent from the frozenset + baseline mirror, and that
`test_no_dead_symbols` passes. Any unwired symbol remains listed with a rationale note.

**Acceptance Scenarios**:

1. **Given** a forward-API symbol becomes `src`-consumed by the walk update, **When** it is
   removed from the frozenset and the `_baselines.yaml` mirror row, **Then** the
   dead-symbols gate stays green.
2. **Given** a forward-API symbol is not wired in this mission, **When** the allowlist is
   finalized, **Then** it remains allowlisted with an explanatory note.

### User Story 4 - Family C templates & Family B anti-patterns delivered by edge (Priority: P2)

Two companion deliverables complete the A–E families. The already-shipped C4 mermaid
templates are delivered via a `template:instantiates` edge from `action:documentation/design`
(the canonical path recorded in the wiring table's Family C asset assessment) rather than
being re-homed as assets. And `anti_pattern` artefacts are authored for the code smells that
each `refactoring-*` tactic solves, wired via `smell → refactoring-tactic` edges, with
content grounded in each tactic's own attested `problem`/`when` text (no inventions).

**Why this priority**: These round out the delivery families opened by the walk update. They
are companions, not the core vector, so P2.

**Independent Test**: Assert the C4 templates are reachable via a `template:instantiates`
edge from `action:documentation/design`; assert each authored `anti_pattern` is reachable by
edge from its `refactoring-*` tactic and that its text is traceable to that tactic's attested
`problem`/`when`.

**Acceptance Scenarios**:

1. **Given** the C4 mermaid templates exist under `src/doctrine/templates/architecture/` and are
   referenced by the C4 zoom-in tactic, **When** the `template:instantiates` edge from
   `action:documentation/design` is added AND IC-01's suggests-walk makes the C4 tactic
   profile-reachable, **Then** the templates reach the architect via the tactic's references
   (not re-homed as assets).
2. **Given** a `refactoring-*` tactic with an attested `problem`/`when`, **When** an
   `anti_pattern` artefact is authored and a `tactic --REJECTS--> anti_pattern` edge added,
   **Then** the anti_pattern is a valid REJECTS-target (validator green) and its content is
   grounded in the tactic's text (no invention).

### User Story 5 - Trailing code-hygiene tickets closed (Priority: P2)

Four hygiene items from the parent slice are finished here, each tied to a filed ticket:
the non-hermetic delivery-fixture false-red; the writer-registry blind spot (#3075); the
`DRGGraphSchemaError` UX + asset source-path ordering (#3062); and the inline
`context.py` helper extraction (#2532).

**Why this priority**: These are correctness/hygiene closures that keep the delivery engine
honest and the codebase consistent; they ride with the mission but are not the primary
delivery vector.

**Independent Test**: Each ticket's acceptance is independently checkable — hermetic fixture
(first_load always True in a populated checkout), writer-discovery gate green + both emit
sites registered, `doctrine validate` surfaces a structured issue instead of a traceback,
context helpers live in `context_renderers/` with consumer tests green.

**Acceptance Scenarios**:

1. **Given** a populated local checkout with an ambient `context-state.json`, **When** the
   `test_every_load_delivery` fixture runs, **Then** `first_load` is True unless the test
   sets it (no local false-red).
2. **Given** a new top-level DRG graph field, **When** either DRGGraph emit site serializes,
   **Then** the field is not dropped (both routed through `graph_document_to_dict` and
   registered), and a writer-discovery gate fails if any src writer is unregistered.
3. **Given** a pack with a schema error, **When** `doctrine validate` loads it, **Then** a
   structured `ValidationIssue` is emitted instead of an uncaught `DRGGraphSchemaError`
   traceback.
4. **Given** the reference-block + delivery helpers currently inline in `context.py`, **When**
   they are extracted to `context_renderers/` sibling modules, **Then** all `context.py`
   consumer tests stay green (behaviour-preserving).

### Edge Cases

- A `suggests` edge whose target artefact is a non-activatable kind (`anti_pattern`,
  `template`) — reachable by edge, must not be treated as charter-activatable.
- A `suggests` edge target that is already `requires`-reachable — must not be double-counted
  or double-delivered.
- Context-bloat pressure: many `suggests` edges fanning out from one profile — delivery must
  stay links-not-bodies and `when`-gated, never an eager full-body dump.
- A forward-API symbol partially wired (referenced only in a test, not `src/`) — must NOT be
  removed from the allowlist (the gate scans `src/` consumers).
- `AssetRepository.source_path(id)` for an id that failed model validation — must return
  absent, not a stale recorded path.
- Extraction of context helpers must not change the rendered payload for any consumer.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Profile-channel walk follows `suggests` | As a consuming agent, I want the profile channel to follow `suggests` edges (in addition to `requires`/`specializes_from`) so that the A–E linked doctrine actually reaches me. | High | Open |
| FR-002 | Surface `when` as applicability condition | As a consuming agent, I want each delivered `suggests` edge's `when` clause surfaced as the doctrine's applicability condition (stated-default when absent) so that I know when the linked doctrine applies. | High | Open |
| FR-003 | Context-bloat-safe delivery cadence | As a consuming agent, I want suggested doctrine delivered as `when`-gated/labelled links (not eager full bodies) building on `_ActionDoctrineBundle.bridge_urns` + the requires-closure render cadence, so my context is not bloated. | High | Open |
| FR-004 | Reconcile reachability pins | As a maintainer, I want `_PROFILE_UNREACHABLE` / `_PROFILE_RESCUES` re-measured via the canonical helper (never a hand-rolled walk) and updated to the live reachable set. | High | Open |
| FR-005 | Update wiring table + drop deferred set | As a maintainer, I want `delivery-reachability-wiring-table.md` updated so the deferred set drops from 50, with a composition-ledger entry per moved golden number. | High | Open |
| FR-006 | Retire forward-API allowlist incrementally | As a maintainer, I want each forward-API symbol that gains a **cross-file `src/` consumer** this mission (≈2–3, not all 9 — the charter-activation/action symbols stay) removed from `_CATEGORY_C_DELIVERY_RAIL_FORWARD_API` + its `_baselines.yaml` mirror, with unwired symbols kept allowlisted-with-note and the dead-symbols gate green (no manufactured importers). | High | Open |
| FR-007 | Deliver C4 templates via `template:instantiates` | As a consuming agent, I want the C4 mermaid templates delivered via a `template:instantiates` edge from `action:documentation/design` (per the wiring table's Family C asset assessment), not re-homed as assets. | Medium | Open |
| FR-008 | Author refactoring anti-patterns + `REJECTS` edges | As a maintainer, I want `anti_pattern` artefacts for the smells each `refactoring-*` tactic solves, wired via `tactic --REJECTS--> anti_pattern` (the existing canonical relation; anti_patterns are validation-only, never delivered), grounded in the tactic's attested `problem`/`when` (no invented smells). | Medium | Open |
| FR-009 | Hermetic delivery-test fixture | As a maintainer, I want the `test_every_load_delivery::project` fixture to exclude/reset `context-state.json` so `first_load` is always True unless the test sets it (no local false-red). | Medium | Open |
| FR-010 | Route + register both DRGGraph emit sites + discovery gate (#3075) | As a maintainer, I want `rewrite_opposed_by._write_graph` and `project_drg._serialize_graph` routed through `graph_document_to_dict` and registered as `DocumentWriter` members, plus a writer-discovery gate that scans `src/` for node/edge/graph-dict writers and asserts registry membership, plus the repo Protocol typing cleanup folded in. | High | Open |
| FR-011 | Structured `DRGGraphSchemaError` UX + asset source-path fix (#3062) | As a maintainer running `doctrine validate`, I want `DRGGraphSchemaError` caught at consumer load sites (`pack_validator`, `pack_assembler`) and surfaced as a structured `ValidationIssue`, and `AssetRepository._pre_validate` to record `_source_paths[id]` only after successful validation. | Medium | Open |
| FR-012 | Extract inline `context.py` helpers (#2532) | As a maintainer, I want the reference-block + delivery helpers and the new requires-closure render cadence extracted from `context.py` into `context_renderers/` sibling modules, behaviour-preserving. | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Behaviour-preserving extraction | 0 regressions across `context.py` consumer test suites after FR-012 extraction; rendered payloads byte-identical for exercised consumers. | Reliability | High | Open |
| NFR-002 | No silent golden movement | Every changed reachability/deferred-set golden number (FR-004/FR-005) carries a matching composition-ledger entry; 0 golden counts move without a ledger row. | Maintainability | High | Open |
| NFR-003 | Context-bloat bound | Suggested-doctrine delivery emits links + `when` labels, never full artefact bodies; no per-context eager body dump of the suggested set (assert delivered payload contains references, not inlined bodies, for `suggests`-reached artefacts). | Performance | High | Open |
| NFR-004 | Dead-symbols gate integrity | After allowlist retirement, 0 wired symbols remain on the allowlist and 0 removed symbols are unreferenced in `src/`; `test_no_dead_symbols` green. | Maintainability | High | Open |
| NFR-005 | Lint/type cleanliness | `ruff` and `mypy --strict` pass with zero new issues and zero new blanket suppressions across all touched modules; FR-010 removes (not adds) `# type: ignore[attr-defined]`. | Maintainability | High | Open |
| NFR-006 | Writer-discovery non-vacuity | The FR-010 writer-discovery gate is non-vacuous — a self-mutation test proves it fails when a src graph-dict writer is left unregistered. | Reliability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Consume the delivery-rail forward API, don't re-derive | Measure/consume reachability via the 9 public symbols (`action_channel_reachable`, `PROFILE_CHANNEL_RELATIONS`, `action_seed_urns`, `agent_profile_seed_urns`, `partition_delivery`, `charter_activated_urns`, `normalize_activation_identifier`, `partition_activated_unreachable`, `ActivationReachabilityPartition`); never hand-roll the walk. | Technical | High | Open |
| C-002 | Progressive-disclosure helpers are module-private | The 10 composition helpers (`link_references`, `edge_to_reference`, `outbound_references`, `requires_closure`, `reconstruct_urns`, `artifact_to_dict`, `bare_id`, `DELIVERY_INLINE/LINK`, `STATED_DEFAULT_WHEN`) are internal impl of `build_disclosure_payload` — consume as internal, NOT as public API. | Technical | High | Open |
| C-003 | Build on existing bundle scaffolding | `context.py`'s `_ActionDoctrineBundle` already carries `bridge_urns` + a requires-closure render cadence from the landing pass — build on them, do not re-derive. | Technical | High | Open |
| C-004 | `anti_pattern` is non-activatable, edge-reached | `anti_pattern` artefacts are a non-activatable kind reached only by edge; content grounded in attested tactic `problem`/`when` text — no invented smells. | Technical | High | Open |
| C-005 | Template via edge, not re-home | C4 templates delivered via `template:instantiates` from the canonical `action:documentation/design` path recorded in the wiring table's Family C asset assessment — not re-homed as assets. | Technical | Medium | Open |
| C-006 | Explicit out-of-scope | Value-based edge properties (B1 `impacts`/`is_symmetric`) and the DDD↔documentation mutual-reinforcement edge that depends on them, and #3064 (empty-charter/`default-charter.yml` asset, DIRECTIVE_044 always-on), are OUT of scope — separate missions. | Business | High | Open |
| C-007 | Close #3075 only if all three sub-parts done | #3075 closes only when: both emit sites routed+registered, the writer-discovery gate added, AND the repo Protocol typing cleanup folded. Otherwise leave open with residual note. | Technical | High | Open |
| C-008 | Canonical sources + git discipline | Use doctrine DRG YAML / templates / CLI (no improvised paths); base = upstream/main tip; PRs only, operator merges; no version numbers assigned in scope. | Technical | High | Open |

### Key Entities

- **`suggests` edge**: A DRG edge carrying a `when` applicability clause; the delivery vector
  this mission activates in the profile channel.
- **Profile channel**: The reachability walk that resolves an agent profile's action-scoped
  doctrine; currently follows `{requires, specializes_from}`, extended here to add `suggests`.
- **`PROFILE_CHANNEL_RELATIONS`**: The set of edge relations the profile channel walks (a
  forward-API symbol; wiring it in is part of FR-001/FR-006).
- **Delivery-rail forward API (9 symbols)**: The public helper surface consumed to measure and
  deliver reachability (C-001).
- **`_ActionDoctrineBundle`**: The context bundle carrying `bridge_urns` + requires-closure
  render cadence built on for delivery (C-003).
- **Reachability partition / `ActivationReachabilityPartition`**: The delivered-vs-unreachable
  split re-measured to reconcile pins (FR-004).
- **Wiring table**: `docs/plans/doctrine/delivery-reachability-wiring-table.md` — the deferred-set
  ledger updated in FR-005.
- **Forward-API allowlist**: `_CATEGORY_C_DELIVERY_RAIL_FORWARD_API` frozenset + `_baselines.yaml`
  mirror — retired incrementally in FR-006.
- **`anti_pattern` artefact / `template:instantiates` edge**: Family B/C companion deliverables
  (FR-007/FR-008).
- **`DocumentWriter` registry / DRGGraph emit sites**: The writer-registry surface hardened in
  FR-010.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `profile_channel_reachable(graph, {agent_profile:architect-alphonso})` (and an
  implementer profile) delivers the A/B/C/E `suggests`-linked artefacts, each with its `when`
  condition surfaced via the profile render path — verified on the **profile channel**, NOT
  `resolve_context` (the action channel, which is vacuous/red for this — post-plan D10).
- **SC-002**: The wiring table's deferred set drops below its **baseline of 60** (measured), and
  every changed reachability/deferred golden number has a matching composition-ledger entry.
- **SC-003**: Every forward-API symbol this mission wires with a **cross-file `src/` consumer**
  (≈2–3 per the D17 pre-classification — not all 9) is removed from the allowlist + baseline
  mirror; `test_no_dead_symbols` is green; every unwired symbol stays documented-and-retained
  (no manufactured importers).
- **SC-004**: The C4 templates reach the architect via IC-01's suggests-walk to the C4 tactic's
  references (the `template:instantiates` edge from `action:documentation/design` completes the
  topology), and each refactoring `anti_pattern` is a `REJECTS`-target of its tactic with the
  anti-pattern validator green.
- **SC-005**: #3075, #3062, and #2532 are closable (all sub-parts done); the writer-discovery
  gate is green and non-vacuous; all `context.py` consumer tests stay green; the
  `test_every_load_delivery` local false-red is eliminated.
- **SC-006**: `ruff` + `mypy --strict` pass with zero new issues/suppressions across touched
  modules (FR-010 net-removes `# type: ignore`).

## Assumptions

- Per explicit operator instruction, discovery was minimized; the pre-specified brief is the
  authoritative intent and is recorded above. No open `[NEEDS CLARIFICATION]` markers remain.
- The parent slice (PR #3070, delivery rail + families A–E topology + forward API) is merged
  to upstream/main (tip `10e970ed2`); this mission builds on that base.
- The 9 forward-API symbols and the 10 module-private composition helpers are as enumerated in
  the brief; plan-phase code grounding will confirm exact locations before wiring.
- The C4 mermaid templates already exist under `src/doctrine/templates/architecture/`.
- Each `refactoring-*` tactic carries attested `problem`/`when` text sufficient to ground an
  `anti_pattern` without invention; if a tactic lacks it, that anti-pattern is deferred with a
  note rather than fabricated.
