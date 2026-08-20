# Mission Specification: Kind-Complete Cascade + Orphan Wiring

**Mission Branch**: `feat/kind-complete-cascade-orphan-wiring`
**Created**: 2026-08-20
**Status**: Draft
**Input**: Seed `docs/plans/charter-resolution/seeds/seed-m5-kind-complete-cascade.md` (charter-resolution program M5). Closes #2829 and the residual of #3009.

## Context

Authored governance is only useful if it reaches the agent doing the work. Two
complementary reach gaps remain in the charter cascade — the mechanism that
turns a single `charter activate` into the set of artifacts that should activate
alongside it, computed as pure graph logic over the merged Doctrine Reference
Graph (DRG).

- **#2829 — the relation-set dead-end.** The cascade follows only
  `{requires, suggests, refines}`. A `mission_type` node carries only
  `requires → action` edges; an `action` node carries `scope → {directive,
  tactic, …}` and `instantiates → template` — never `requires`/`suggests`/
  `refines`. The forward closure reaches the `action` node, cannot continue
  (those relations aren't followed), and the `action` node is not itself an
  artifact, so nothing is returned. **Measured on the shipped graph: cascade
  from every one of the four built-in mission types returns 0 activated
  artifacts.** The governance an operator switched on by activating a mission
  type reaches nobody.

- **#3009 residual — artifacts with no followed inbound edge.** Most of #3009
  has already landed (the orphan membership ledger, the wire-8/delete-1 pass,
  the reachability companion metric). Five charter-activated artifacts remain in
  the `_ACTIVATED_BUT_ORPHANED` ledger: they have no inbound edge in the **pure
  extractor graph**, so a context walk or cascade reaches none of them from the
  artifact graph itself. Four already carry a *hand-authored overlay* edge (a
  secondary authority patched onto the shipped graph); one has no defensible
  source anywhere.

These are complementary: #2829 fixes artifacts that *have* `scope`/`instantiates`
inbound but are never followed; #3009 fixes artifacts with no followed inbound
edge at all.

The primary actor for both gaps is the **operator** running `charter activate`
(and the **maintainer** who curates the shipped doctrine graph). The desired
outcome: governance that is switched on actually shows up where work happens,
and every activated artifact is either reachable or explicitly recorded as
direct-activation-only.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Activating a mission type reaches its dependent governance (Priority: P1)

An operator activates a built-in mission type (for example `documentation` or
`software-dev`) with `charter activate mission-type <name> --cascade all`.
Today the cascade reports zero referenced artifacts, so none of the directives,
tactics, or styleguides the mission's steps depend on are activated. After this
mission, the cascade walks through the mission's action steps to the governance
artifacts those steps are scoped to, and activates them.

**Why this priority**: This is the headline defect (#2829). A mission type is
the most natural thing an operator activates, and it is precisely the case that
returns nothing today — the governance is authored, reachable in principle, and
silently dropped.

**Independent Test**: Build the shipped DRG, run the cascade from each built-in
`mission_type` URN, and assert the activated set is non-empty and contains the
governance kinds (directive/tactic/styleguide/…) its actions scope to — proven
red on the base (returns 0) and green after the change.

**Acceptance Scenarios**:

1. **Given** the shipped DRG, **When** the cascade is computed from
   `mission_type:documentation`, **Then** the activated set is non-empty and
   includes the directives, tactics, and styleguides reachable through that
   mission's `action` steps' `scope` edges (measured baseline: 0 → non-zero).
2. **Given** the shipped DRG, **When** the cascade is computed from every one of
   the four built-in mission types, **Then** none returns an empty activated set.
3. **Given** an `action` node reached transitively from a `mission_type`,
   **When** the cascade walks it, **Then** the `action` node itself is not
   emitted as an activation target (it is an intermediate node, not an artifact).

### User Story 2 - The cascade proposes only activatable kinds (Priority: P1)

An operator activates any artifact whose reference closure reaches a `template`
or `asset` (both non-charter-activatable). Today those surface as cascade
targets and each produces a spurious "could not cascade-activate template/<id>"
warning (a caught error, not a crash). After this mission the cascade proposes
only charter-activatable kinds, so the operator sees a clean, actionable set.

**Why this priority**: This is the "kind-complete" half of the mission. Widening
the followed set to reach governance through `scope`/`instantiates` also reaches
templates the actions produce; without a kind filter, every mission-type
activation would emit a flood of misleading template warnings. The same filter
also removes the pre-existing noise for the ~137 sources that already reach
templates/assets today.

**Independent Test**: Run the cascade from a source whose closure reaches a
`template`/`asset` and assert no `template`/`asset` (nor other
non-charter-activatable kind) appears in the activated or no-cascade-warning
output; assert the activated set still contains the activatable kinds.

**Acceptance Scenarios**:

1. **Given** a cascade source whose closure reaches `template:` and `asset:`
   nodes, **When** the cascade activation targets are computed, **Then** no
   `template` or `asset` id appears in the activated buckets.
2. **Given** the same source with no `--cascade` flag, **When** the no-cascade
   warning is computed, **Then** it does not list any `template`/`asset` id as
   "referenced but not activated".
3. **Given** the cascade from a mission type, **When** activation targets are
   computed, **Then** the activatable governance kinds are still present (the
   filter narrows to activatable kinds, it does not empty the set).

### User Story 3 - Every activated artifact is reachable or explicitly direct-only (Priority: P2)

A maintainer curating the shipped doctrine wants the pure extractor graph to
have no unexplained orphans: every charter-activated artifact either has a real
inbound edge authored in its own source (single-authority) or is explicitly
recorded as direct-activation-only with a rationale. The five residual
`_ACTIVATED_BUT_ORPHANED` artifacts are resolved: four gain a real
source-artifact frontmatter edge (promoted from the existing overlay), and the
one with no defensible source is recorded direct-activation-only.

**Why this priority**: Closes the #3009 residual and keeps the orphan ledger a
true "must only shrink" signal. It depends on the doctrine graph, not the
cascade engine, so it is independent of Stories 1–2 and can be verified against
the regenerated graph.

**Independent Test**: Regenerate the graph; assert each of the four wired
orphans now has its inbound edge in the **pure** extractor graph (leaving
`_ACTIVATED_BUT_ORPHANED`), the fifth is recorded in the new direct-activation-
only disposition, and the golden node/edge/orphan ledger and reachability pins
match the single re-ledger.

**Acceptance Scenarios**:

1. **Given** the pure extractor graph, **When** it is regenerated after this
   mission, **Then** `styleguide:given-when-then-authoring`,
   `styleguide:quadruple-a-test-format`, `toolguide:sonar`, and
   `toolguide:gherkin` each have a real inbound edge sourced from their owning
   directive's frontmatter (not the hand-authored overlay).
2. **Given** the same regeneration, **When** the shipped graph edge set is
   compared to the base, **Then** it is unchanged (the promoted edges already
   existed via overlay; only their authority moved), so reachability pins do not
   move for those four.
3. **Given** `styleguide:deployable-skill-authoring` (no defensible source),
   **When** the orphan ledger is evaluated, **Then** it is recorded as
   direct-activation-only with a rationale and removed from the
   "must-shrink" orphan-debt set.
4. **Given** the golden-count ledger surfaces (extractor projection + reach-
   ability pins + the reachability wiring-table doc), **When** the mission
   lands, **Then** each moved count/membership is traced to exactly one
   followed-relation change or orphan-edge change, and the re-ledger is applied
   exactly once.

### Edge Cases

- **A mission type whose actions only `instantiate` templates and scope nothing**
  (e.g. a plan step reaching only a template): its cascade yields an empty
  activatable set after the kind filter — this is correct (no activatable
  governance is referenced), and must not be mistaken for the #2829 defect. The
  non-vacuous test targets a mission type that *does* scope governance.
- **Deactivation symmetry**: the followed-relation set feeds both activation and
  the shared-reference-safe deactivation exclusivity computation. Expanding the
  set must keep deactivation shared-reference-safe (no artifact reachable from
  another active source is removed).
- **Excluded relations must stay excluded**: `vocabulary`, `applies`, `replaces`,
  `delegates_to`, `specializes_from`, `enhances`, `overrides`,
  `in_tension_with`, `reconciles_tension`, `rejects` are not followed. Following
  any of them would over-cascade (tension partners, anti-patterns, runtime
  handoffs, lineage, or overlay edges are not forward artifact references).
- **Anti-pattern nodes** are never reached (only `rejects` points at them, and
  `rejects` is excluded), so the kind filter's exclusion of `anti_pattern` is a
  belt-and-suspenders guarantee, not a live path.
- **Frontmatter promotion must not change the shipped graph**: if promoting an
  overlay edge to frontmatter changed the merged edge set, a byte-identity graph
  guard would fail. The promoted edge must be identical (same source, target,
  relation) so only its authoring authority moves.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Cascade follows the action hop | As an operator, I want activating a mission type to reach the governance artifacts its action steps are scoped to, so that switched-on governance is not silently dropped. | High | Open |
| FR-002 | Non-zero cascade from every governance-bearing built-in mission type | As an operator, I want every governance-bearing built-in mission type's cascade to return a non-empty activatable set, so that the #2829 dead-end is closed. (Measured discovery: `mission_type:plan` correctly cascades to empty — its step contracts scope **no** governance, only `instantiates→template`; the dead-end is closed for it too, but there is no governance to reach. Wiring plan-step governance is a graph-data gap tracked as a follow-up, out of this mission's cascade-code scope.) | High | Open |
| FR-003 | Cascade proposes only charter-activatable kinds | As an operator, I want the cascade to propose only kinds I can actually activate, so that I never see spurious "could not cascade-activate template/asset" warnings. | High | Open |
| FR-004 | Intermediate action nodes are never activation targets | As an operator, I want `action` nodes (and other non-artifact nodes) excluded from activation targets, so that only real artifacts are proposed. | High | Open |
| FR-005 | Excluded relations stay excluded | As a maintainer, I want tension/lineage/overlay/handoff/vocabulary relations to remain unfollowed, so that the cascade does not over-reach. | High | Open |
| FR-006 | Deactivation stays shared-reference-safe under the widened set | As an operator, I want cascade deactivation to still skip any artifact reachable from another active source, so that widening the followed set does not remove shared governance. | High | Open |
| FR-007 | Four residual orphans gain real inbound edges | As a maintainer, I want the four defensible residual orphans wired by a real source-artifact frontmatter edge (promoted from the overlay), so that the pure graph explains their reachability from a single authority. | Medium | Open |
| FR-008 | Source-less orphan recorded direct-activation-only | As a maintainer, I want `styleguide:deployable-skill-authoring` recorded as direct-activation-only with a rationale, so that an artifact with no defensible source is honestly classified instead of given a guessed edge. | Medium | Open |
| FR-009 | Single golden re-ledger | As a maintainer, I want the golden node/edge/orphan counts and reachability pins re-ledgered exactly once, with every move traced, so that the shipped-graph accounting stays honest and reviewable. | High | Open |
| FR-010 | Relation-set expansion captured in an ADR | As a maintainer, I want the "which relations join the followed set" decision recorded in an ADR, so that a future reader understands why `scope`/`instantiates` are in and the others are out. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Zero-suppression quality | New/changed code passes `ruff` and `mypy --strict` with zero warnings and zero suppressions (no blanket `# noqa`/`# type: ignore`/per-file ignores). | Maintainability | High | Open |
| NFR-002 | Layering preserved | `charter/cascade.py` continues to import only `doctrine.*` and never `specify_cli`; the kind filter reuses the canonical `CHARTER_ACTIVATABLE_KINDS` authority rather than re-declaring an exclusion list. | Architecture | High | Open |
| NFR-003 | Red-first, non-vacuous gates | Both defects have a failing-first test proving the pre-change state (mission-type cascade = 0; the ~5 orphans unreachable/unclassified) before the fix makes them green. | Testing | High | Open |
| NFR-004 | Deterministic, pure graph logic | The cascade remains pure graph logic with no per-specific-kind branch beyond the single canonical activatable-kind filter; results stay deterministically sorted. | Reliability | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Land last, re-ledger once | The mission lands atop M1/M2/M3/M4 (all merged); golden counts must move exactly once, never re-ledgered against a moving base. | Technical | High | Open |
| C-002 | Disjoint scope from M3/M4 | No operating-procedures edge wiring (M3), no doctrine delivery/render change (M4); this mission owns cascade traversal + the residual orphan edges only. | Technical | High | Open |
| C-003 | Real relationships only | Every authored orphan edge mirrors an existing `source_kind → target_kind` pattern in the shipped graph; an orphan with no defensible source is marked direct-activation-only, never given a guessed edge. | Technical | High | Open |
| C-004 | Shipped graph edge-set stability for promotions | Promoting an overlay edge to frontmatter must not change the merged shipped edge set (byte-identity graph guard must stay green). | Technical | High | Open |
| C-005 | No cascade candidate-filter scope creep | The activatable-kind filter is applied inside the cascade referenced-artifact seam only; it does not alter the canonical `CHARTER_ACTIVATABLE_KINDS` set or other activation surfaces. | Technical | Medium | Open |

### Key Entities

- **Cascade followed-relation set**: the set of DRG relations the cascade walks
  forward from an activation source. Currently `{requires, suggests, refines}`;
  this mission adds `{scope, instantiates}`.
- **Charter-activatable kind**: an artifact kind an operator can activate
  (`CHARTER_ACTIVATABLE_KINDS` = all kinds minus `template` and `asset`). The
  cascade proposes only these as targets.
- **Action node**: an intermediate DRG node (`action:<mission>/<step>`) linking a
  mission type's step to the governance it is scoped to; never itself an
  activation target.
- **`_ACTIVATED_BUT_ORPHANED` artifact**: a charter-activated artifact with no
  followed inbound edge in the pure extractor graph.
- **Direct-activation-only disposition**: an explicit record that an activated
  artifact has no defensible inbound source and is intentionally reached only by
  direct activation, not by cascade/context traversal.
- **Golden-count ledger**: the extractor-projection node/edge/orphan pins, the
  reachability membership sets, and the reachability wiring-table doc that
  together certify the shipped graph; re-ledgered once by this mission.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Cascade from every **governance-bearing** built-in mission type
  (`documentation`, `research`, `software-dev`) returns a non-empty activatable
  set (measured after fix: 31 / 23 / 160 activatable ids; baseline: all four
  returned 0). `mission_type:plan` returns empty because its step contracts scope
  no governance (only `instantiates→template`) — the #2829 traversal dead-end is
  closed for it too, but there is nothing to reach; this is a graph-data property,
  not a cascade defect (follow-up: author plan-step governance).
- **SC-002**: No `template`, `asset`, or other non-charter-activatable kind
  appears in any cascade activation or no-cascade-warning output.
- **SC-003**: The `_ACTIVATED_BUT_ORPHANED` pure-graph orphan-debt set shrinks by
  five: four via real frontmatter inbound edges, one via a direct-activation-only
  disposition; no residual member lacks a documented disposition.
- **SC-004**: The golden node/edge/orphan counts and reachability pins are
  re-ledgered exactly once, and every moved value is traced in the plan/ledger to
  a single followed-relation or orphan-edge change.
- **SC-005**: The full targeted test surface (cascade, extractor projection,
  reachability), plus `ruff` and `mypy --strict`, pass with zero suppressions.
