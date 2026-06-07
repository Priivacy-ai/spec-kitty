# Mission Specification: WP Lane State Machine Canonicalization

**Mission Branch**: `kitty/mission-wp-lane-state-machine-fsm-01KTGZAZ`
**Created**: 2026-06-07
**Status**: Draft
**Input**: Operator direction — "Convert the lacklustre WP-lane state implementation into a proper, encapsulated, testable State-pattern Finite State Machine (https://refactoring.guru/design-patterns/state) as the single source of transition truth, with an explicit `genesis` lane; do it right once rather than another whack-a-class hotfix. Then fold ALL adversarial-review findings into this mission."

<!--
  Purpose (stakeholder TL;DR): The WP lane status model accreted into a split-brain
  (issue #1589): finalize clobbered the coordination event log, an unseeded WP
  silently defaulted to `planned`, and transition truth lived in two parallel
  places (a hand-maintained matrix and the State-pattern classes). An initial fix
  (branch `fix/status-genesis-lane-bootstrap`) introduced `Lane.GENESIS` and made
  the State machine the single source of transition truth. A five-lens adversarial
  review (research/) confirmed the core but found follow-ups. This mission ratifies
  the FSM design and resolves every review finding so the lane model is one
  encapsulated, testable FSM with no parallel sources and no boundary leaks.
-->

## Baseline (already implemented on `fix/status-genesis-lane-bootstrap` @ a43aa6a06)

This mission **formalizes and completes** an initial implementation. Already landed
(validated by the adversarial review — see `research/adversarial-review-synthesis.md`):

- `Lane.GENESIS` non-display lane; `_derive_from_lane` returns it for unseeded WPs.
- `status/wp_state.py` (State pattern) is the single source of transition edges;
  `transitions.ALLOWED_TRANSITIONS` is **derived** from `allowed_targets()`.
- FSM interface on `WPState`: `current_lane`, `may_transition_to(target)`, `transition_to(target, ctx)`.
- Finalize no longer clobbers the coordination event log (`_stage_finalize_artifacts_in_coord_worktree`).
- ADR `architecture/3.x/adr/2026-06-07-1-wp-lane-fsm-genesis-and-finalize-clobber.md`.

The requirements below **ratify** that baseline (US1–US3) and **resolve the review
follow-ups** (US4–US8). Research artefacts: the five raw reviews + synthesis in `research/`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — The FSM is the FULLY-wired, single authority for WP lane behavior (Priority: P1)

A developer reasoning about WP lane behavior finds exactly one authority: the
`WPState` State machine. **Every** lane read and lane transition at runtime flows
through the State objects. There is no parallel/duplicate lane logic: the flat
`ALLOWED_TRANSITIONS` matrix is *derived* from the states, and the guard layer
(`validate_transition`, `_GUARDED_TRANSITIONS`) and **force-override** are owned by
or delegated through the State objects — not maintained as a separate, divergent
code path. Each of the ten lanes (including `genesis`) is a full `StateObject`
(like `GenesisState`) that owns its own edges, guards, and force behavior.

**Why this priority**: The dual-source / half-wired model was the root enabler of
the whack-a-class drift and the #1589 split-brain. A *fully* wired FSM — old paths
shifted onto it, not running beside it — is the structural fix the operator mandated.

**Independent Test**: Prove `ALLOWED_TRANSITIONS == {(s.lane, t) for s in states for t in s.allowed_targets()}`; prove no `(from,to)` transition table, lane-adjacency map, or direct lane-string `if`/`match` branching exists in `src/` outside the FSM; prove the FSM interface (`current_lane`/`may_transition_to`/`transition_to`) is the path real callers use.

**Acceptance Scenarios**:
1. **Given** the derived matrix, **When** compared to the historical 27 edges + 2 genesis edges, **Then** it is exactly equal (0 missing / 0 extra).
2. **Given** a grep across `src/`, **When** searching for parallel transition-edge tables, lane-adjacency maps, or out-of-FSM lane-string branching, **Then** only the FSM and its derivations exist.
3. **Given** a forced terminal exit and a guarded transition, **When** routed through the FSM `transition_to`, **Then** the State object enforces the guard/force decision (no divergent authority in `validate_transition`).
4. **Given** the lane readers and the transition emitters, **When** traced, **Then** they consume `WPState` (no direct `.value` lane-string comparisons that bypass the FSM).

---

### User Story 2 — Explicit, non-display `genesis` lane (Priority: P1)

An unseeded work package (created, not yet finalized) is in an explicit `genesis`
state, not a silent `planned` default. `finalize-tasks` seeds an explicit
`genesis → planned` transition. `genesis` never appears on the kanban board, in
the board summary, or in any operator-facing lane list.

**Why this priority**: Removes the genesis/planned conflation that made the
bootstrap seed a no-op (the write-side half of #1589).

**Independent Test**: `_derive_from_lane` returns `GENESIS` for unseeded WPs; the bootstrap seed is a persisted `genesis → planned` event; no materialized snapshot, board, or summary contains genesis.

**Acceptance Scenarios**:
1. **Given** a fresh WP with no lane events, **When** `_derive_from_lane` runs, **Then** it returns `GENESIS`.
2. **Given** any materialized `status.json`, **When** its `summary` is read, **Then** it contains **no** `genesis` key (FR-007).
3. **Given** the kanban board / `tasks status` table, **When** rendered, **Then** there is no genesis column and no genesis WP is silently dropped.

---

### User Story 3 — Finalize preserves the coordination event log (Priority: P1)

`finalize-tasks` on a coordination-topology mission commits planning artifacts to
the coordination branch **without** overwriting the canonical `status.events.jsonl` /
`status.json` that the transactional emitter already seeded.

**Why this priority**: The read-side half of #1589 — the actual data-loss that
blocked the implement loop.

**Independent Test**: After a coord-topology `finalize-tasks`, the committed coordination event log still contains the bootstrap lane events.

**Acceptance Scenarios**:
1. **Given** a coordination mission whose coord worktree holds seeded lane events, **When** `finalize-tasks` commits, **Then** those lane events survive (not clobbered by the primary checkout's stale copies).
2. **Given** a non-coordination mission, **When** `finalize-tasks` commits, **Then** its primary-checkout `status.events.jsonl`/`status.json` ARE committed (no regression).

---

### User Story 4 — Read and write layers agree on unseeded WP state (Priority: P1)

Every reader of WP lane state reports an unseeded WP as `genesis`, matching the
writer. Attempting to implement an unfinalized WP fails fast with an actionable
message ("run finalize-tasks") **before** any workspace is allocated — never a
cryptic `Illegal transition: genesis -> claimed` or a dangling worktree.

**Why this priority**: The adversarial review's top correctness/UX finding (F2);
the residual #1589 split-brain. Makes the ADR's "read/write agree" claim true.

**Independent Test**: `wp_lane_actor_from_events`, the transactional read fallback, and the runtime discovery defaults all return `GENESIS` for an unseeded WP; `start_implementation_status` on a genesis WP raises `WorkPackageStartRejected` with a finalize hint, before workspace allocation.

**Acceptance Scenarios**:
1. **Given** an unseeded WP, **When** any status reader resolves its lane, **Then** it returns `GENESIS` (not `PLANNED`).
2. **Given** an unseeded WP, **When** `implement` is invoked, **Then** it fails with an actionable "not finalized; run `finalize-tasks`" message and **no** workspace/worktree is left allocated.

---

### User Story 5 — SaaS event boundary represents the genesis seed faithfully (Priority: P2)

The `genesis → planned` seed is propagated to the SaaS/sync event stream as a
first-seen/bootstrap event the external contract understands — not silently dropped.

**Why this priority**: F1/Alphonso-3 — the highest-severity boundary leak; breaks
SaaS replay integrity. P2 because it is a hosted-surface concern, not local-loop blocking.

**Independent Test**: Emitting a `genesis → planned` seed produces a SaaS payload that validates against `spec_kitty_events` (e.g. mapped to `from_lane=None`, matching `is_bootstrap_planned_event()`), with no dropped event / no swallowed `ValidationError`.

**Acceptance Scenarios**:
1. **Given** a genesis seed event, **When** `_saas_fan_out` runs, **Then** a valid payload is produced (genesis mapped to the bootstrap-planned representation), not a `None` + console warning.
2. **Given** the local `_PAYLOAD_RULES["WPStatusChanged"]` lane validator, **When** inspected, **Then** its lane set is derived from the canonical source (no parallel hardcoded 9-lane list).

---

### User Story 6 — The FSM owns force-override, or the boundary is explicit (Priority: P2)

`WPState.transition_to(target, ctx)` either honours `ctx.force` (with actor + reason)
for forced terminal exits, or the contract explicitly documents that
`validate_transition` remains the force authority — so "single source of truth"
is not overstated.

**Why this priority**: F3/Alphonso-2 — a caller migrating to the FSM API must not
silently lose forced terminal exits.

**Independent Test**: Either `done_state.transition_to(planned, force=True+actor+reason)` succeeds (parity with `validate_transition`), or the ABC docstring + ADR state the force boundary and a test pins that contract.

**Acceptance Scenarios**:
1. **Given** a terminal state and a forced transition with actor + reason, **When** the FSM `transition_to` is called, **Then** behavior matches `validate_transition` (or the documented boundary is enforced by a test).

---

### User Story 7 — Genesis non-display invariant is enforced consistently (Priority: P2)

The non-display property of `genesis` holds across every representation: enum vs
`CANONICAL_LANES`, reducer summary, runtime discovery defaults, the `by_lane`
display dict, and frontmatter-lane validation messaging.

**Why this priority**: Several LOW leaks (reducer summary F4, discovery defaults,
`by_lane` bucket, frontmatter "must be one of" message) collectively undermine the invariant.

**Independent Test**: Grep/assert that no display/summary/discovery surface includes genesis as a visible lane, and that genesis-state WPs are never silently dropped from a table.

**Acceptance Scenarios**:
1. **Given** the reducer summary, runtime discovery, and `tasks status` table, **When** inspected, **Then** none surface genesis as a column/summary key and none drop a genesis WP.
2. **Given** WP frontmatter validation, **When** it reports valid lanes, **Then** genesis is not offered as an authorable lane.

---

### User Story 8 — Leanness and hygiene (Priority: P3)

The change carries no avoidable complexity: one shared seed fixture (not 12
copies), the operator-mandated FSM API is locked in by real callers, `validate`
accepts genesis as `from_lane` only, and stale docstrings/tests are corrected.

**Why this priority**: Randy's TRIM-RECOMMENDED items; quality, lower blast radius.

**Independent Test**: One/two shared `seed_to_planned` fixtures replace the 12 `_seed_planned` copies; `current_lane`/`may_transition_to`/`transition_to` have ≥1 real caller; `validate` rejects `to_lane=genesis`; docstrings/comments updated.

**Acceptance Scenarios**:
1. **Given** the test suite, **When** counting `_seed_planned` definitions, **Then** ≤2 shared fixtures exist.
2. **Given** the FSM interface methods, **When** grepped, **Then** each has at least one production/test caller (operator-mandated API locked in, not dead).
3. **Given** `validate_canonical_event`, **When** an event has `to_lane=genesis`, **Then** it is flagged non-canonical.

### Edge Cases

- A WP appended to `tasks/` **after** finalize already ran on the others → derives `genesis`; it must be re-seedable by re-running finalize (idempotent bootstrap).
- A coord re-finalize where only status files changed → must not error with an empty-changeset commit (debbie Attack 3b).
- A forced terminal exit through the FSM vs through `validate_transition` → must not diverge (US6).

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | FSM is the single transition source | US1 · `ALLOWED_TRANSITIONS` is derived from `WPState.allowed_targets()`; no parallel `(from,to)` edge table exists in `src/`. | High | Done (baseline) |
| FR-002 | FSM interface is the runtime path | US1 · `WPState` exposes `current_lane`, `may_transition_to(target)`, `transition_to(target, ctx)` AND real production/runtime callers use them (not a parallel direct-lane path). | High | Partial (interface done; wiring open) |
| FR-002b | Full FSM wiring — shift old paths | US1 · All lane reads and transitions route through `WPState`; `validate_transition`/guards/force are owned-by or delegated-through the State objects; no direct lane-string branching, lane-adjacency map, or parallel transition logic remains outside the FSM. Every lane is a full StateObject (like `GenesisState`). | High | Open |
| FR-003 | Behavior preservation (9 lanes) | US1 · The derived matrix equals the historical 27 edges exactly; existing transition/guard behavior unchanged. | High | Done (baseline) |
| FR-004 | `Lane.GENESIS` non-display lane | US2 · `genesis` exists in the enum, is excluded from `CANONICAL_LANES`/kanban/board, weight 0, valid `from_lane`. | High | Done (baseline) |
| FR-005 | Genesis derive + explicit seed | US2 · `_derive_from_lane` returns `GENESIS` for unseeded WPs; bootstrap seeds an explicit `genesis → planned`. | High | Done (baseline) |
| FR-006 | Finalize does not clobber the coordination event log | US3 · finalize skips `_COORD_OWNED_STATUS_FILES` in the coord-worktree copy; non-coord missions still commit their status files. | High | Done (baseline) |
| FR-007 | Genesis excluded from snapshot summary | US2/US7 · the reducer `summary` excludes `genesis`; a test asserts the reducer's real output (not a fixture). | Medium | Open |
| FR-008 | Read-side defaults to genesis | US4 · `wp_lane_actor_from_events`, `read_current_wp_state_transactional` fallback, `runtime/next/discovery.py`, `runtime/next/decision.py`, `agent_utils/status.py` return `GENESIS` for an unseeded WP. | High | Open |
| FR-009 | Actionable unseeded-implement rejection | US4 · `start_implementation_status` detects genesis and raises `WorkPackageStartRejected("… run finalize-tasks")` **before** workspace allocation; no dangling worktree. | High | Open |
| FR-010 | SaaS-faithful genesis seed (enum bump) | US5 · **Decision DM-01KTH03H:** `spec_kitty_events.Lane` is extended to add `genesis` (coordinated upstream release via the owning-package workflow); the `genesis → planned` seed then fans out as a real genesis transition, not dropped and not mapped to `from_lane=None`. | Medium | Open |
| FR-011 | SaaS lane validator single-sourced | US5 · `sync/emitter.py` `_PAYLOAD_RULES["WPStatusChanged"]` lane set is derived from the canonical lane source (now including genesis), not a parallel hardcoded list. | Medium | Open |
| FR-012 | FSM owns force + guards (full ownership) | US6 · **Decision DM-01KTH03G:** the guard matrix (actor, subtasks-complete, review-result, done-evidence) AND force-override move into the `WPState` objects; `validate_transition` becomes a thin delegator to `wp_state_for(from).transition_to(to, ctx)`. Behavior preserved, pinned by tests. | High | Open |
| FR-013 | Discovery hides genesis | US7 · runtime discovery / `tasks.py` `by_lane` exclude genesis; a genesis WP is never silently dropped from a table. | Medium | Open |
| FR-014 | Frontmatter validation excludes genesis | US7 · `task_metadata_validation` does not offer genesis as an authorable lane in its "must be one of" message. | Low | Open |
| FR-015 | `validate` accepts genesis as `from_lane` only | US8 · `validate_canonical_event` flags `to_lane=genesis` as non-canonical. | Low | Open |
| FR-016 | Shared seed fixture | US8 · the 12 duplicated `_seed_planned` helpers are consolidated to ≤2 shared conftest fixtures. | Low | Open |
| FR-017 | Lock in the FSM API | US8 · `current_lane`/`may_transition_to`/`transition_to` each have ≥1 real caller (migrate select call sites) so the operator-mandated API is load-bearing, not dead. | Low | Open |
| FR-018 | Docstring + comment hygiene | US8 · fix the `emit.py` pipeline "(or 'planned')" comment, `tests/utils.py` PLANNED default, "9-lane"/"7 lanes" comments, and annotate the tautological equivalence/count test. | Low | Open |
| FR-019 | End-to-end clobber regression test | US3 · a test exercises `finalize_tasks` on a coord mission and asserts the committed coord event log retains the bootstrap lane events. | Medium | Open |
| FR-020 | Drop redundant bootstrap `force=True` | US8 · the guard-free `genesis → planned` seed does not record `force=true` (or documents why). | Low | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Behavior preservation | The nine pre-existing lanes' transition + guard semantics are unchanged; existing suites green. | Reliability | High | Open |
| NFR-002 | One owner per concern (Paula IC) | Exactly one transition-edge source (the FSM); the genesis non-display invariant holds across every representation. | Maintainability | High | Open |
| NFR-003 | Leanness (Randy IC) | No dead API, no duplicated seed helpers, no stale comments; the FSM API is locked in by real callers. | Maintainability | Medium | Open |
| NFR-004 | Lint & type clean | New code passes `ruff` and `mypy` with zero new issues; no disabled checks (justified narrow suppressions only, with rationale). | Maintainability | High | Open |
| NFR-005 | External-contract integrity | Local lane-model changes that cross the `spec_kitty_events` boundary are represented in a contract-valid way (no silent drops). | Compatibility | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Refactor, not redesign | The State-pattern conversion preserves the functional meaning/constraints of the existing 9 lanes; only internal structure changes. | Process | High | Open |
| C-002 | Genesis stays non-display | `genesis` is never added to `CANONICAL_LANES`, kanban columns, or board summary. | Technical | High | Open |
| C-003 | Operator-mandated FSM API | `current_lane` / `transition_to` / `may_transition_to` are retained (operator directive); the "remove dead methods" review recommendation is overridden by locking them in (FR-017). | Governance | High | Open |
| C-004 | spec_kitty_events boundary (enum bump) | **Decision DM-01KTH03H (overrides earlier preference):** add `genesis` to `spec_kitty_events.Lane` via the owning-package workflow (Shared Package Boundary charter): change the package repo first, publish a versioned artifact with compatibility notes, update CLI dependency constraints/lockfile, run consumer/compatibility tests. No path/editable overrides committed. | Technical | High | Open |
| C-005 | Persona ICs | Shaping WPs carry Randy-Reducer (leanness) and Paula-Patterns (single-ownership) implementation contracts. | Process | High | Open |

### Key Entities

- **`WPState` FSM**: the State-pattern authority for lane behavior; owns edges (`allowed_targets`), the `current_lane`/`may_transition_to`/`transition_to` interface, and per-state guards-entry.
- **`Lane.GENESIS`**: explicit non-display pre-finalize lane; `from_lane`-only seed source.
- **Derived `ALLOWED_TRANSITIONS`**: structural matrix projected from the FSM (single source).
- **`validate_transition` / `_GUARDED_TRANSITIONS`**: the mission-guard layer composed on top of FSM edges (and, per US6, the force-override authority unless the FSM subsumes it).
- **`_stage_finalize_artifacts_in_coord_worktree`**: the finalize seam that preserves the coordination event log.
- **SaaS event boundary** (`spec_kitty_events.Lane`, `sync/emitter.py`, `_saas_fan_out`): external contract that must faithfully represent the genesis seed.
- **Adversarial review artefacts**: `research/review-*.md` + `research/adversarial-review-synthesis.md` — the source of FR-007..FR-020.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: One transition-edge source — grep proves no parallel `(from,to)` table; derived matrix exactly equals historical + genesis edges.
- **SC-002**: `genesis` is invisible everywhere it should be — zero genesis in any materialized summary, board, kanban, discovery list, or frontmatter validity message; a genesis WP is never silently dropped.
- **SC-003**: Read/write parity — every lane reader returns `GENESIS` for an unseeded WP; `implement` on an unfinalized WP fails fast with a finalize hint and leaves no workspace.
- **SC-004**: SaaS fidelity — a genesis seed yields a contract-valid SaaS payload (no dropped events); the SaaS lane validator is single-sourced.
- **SC-005**: FSM force contract — `transition_to` force parity holds, or the documented boundary is test-pinned.
- **SC-006**: Lean — ≤2 shared seed fixtures; the FSM API has real callers; docstrings/comments current; `ruff`+`mypy` clean (no new issues).
- **SC-007**: Finalize never clobbers — the end-to-end coord finalize regression test is green; non-coord missions unaffected.

<!--
  Domain Language: "State-pattern FSM", "single source of transition truth",
  "genesis lane (non-display)", "genesis -> planned seed", "coordination event log",
  "read/write parity". Avoid: "lane string", "transition matrix" as a hand-maintained
  artifact, "planned default for unseeded".

  Assumptions: baseline implementation is on fix/status-genesis-lane-bootstrap @ a43aa6a06,
  validated by the five-lens adversarial review (research/). #1589 is the umbrella
  symptom; this mission is a slice of epic #1666. spec_kitty_events is an external
  PyPI contract (per the Shared Package Boundary charter) — prefer representing
  genesis via from_lane=None over an upstream enum bump.
-->
