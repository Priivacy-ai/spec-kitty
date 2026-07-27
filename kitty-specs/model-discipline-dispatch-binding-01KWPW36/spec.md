# Mission Specification: Model-Discipline Dispatch Binding

**Mission Branch**: `design/model-discipline-dispatch-2364`
**Created**: 2026-07-04
**Status**: Draft (rev 2 — post-spec squad folds: alphonso design + paula sizing, both opus; scope = **full evaluator** per operator ruling)
**Input**: Issue [#2364](https://github.com/Priivacy-ai/spec-kitty/issues/2364) (bug/workflow/doctrine/catfooding) — "model-discipline rule not applied at the dispatch/delegation seam (delegates inherit session model)."

## Problem Statement *(context)*

The **model-discipline** rule is authored across the doctrine stack but **nothing consults it at the dispatch/delegation seam**:
- **Charter** (`.kittify/charter/charter.md:97-100`) states model discipline and points at a `model_task_routing` reference.
- **Adversarial-squad procedure** (`src/doctrine/procedures/built-in/adversarial-squad-deployment.procedure.yaml:50-53, 81-82, 101`) carries the "match model tier to task" step — activated (`.kittify/config.yaml:183`) but prose guidance, not machine-consulted routing.
- **Routing catalog schema** (`src/doctrine/schemas/model-to-task_type.schema.yaml`) + Pydantic mirror (`src/doctrine/model_task_routing/models.py`): `models[]` each with `task_fit[]` (per-model↔task_type scores), `routing_policy` (`objective` quality_first|balanced|cost_first, `weights` quality/cost/risk/latency, `tier_constraints[]`, `override_policy` advisory|gated|required, `freshness_policy`).

**Verified gaps (HEAD 71b2787e8):**
1. **The catalog is defined-but-DEAD** — the Pydantic model is whitelisted in `tests/architectural/test_no_dead_modules.py` as *schema-generation only* ("Never imported by runtime code"); there is **no populated catalog instance** and **no runtime loader** (`grep "ModelToTaskType(" src/` → only the class def).
2. **The dispatch seam consults no routing** — `ProfileInvocationExecutor.invoke()` (`src/specify_cli/invocation/executor.py:168-284`) resolves `profile` + `action` and returns an `InvocationPayload` with **no model hint** (`__slots__` :105-116). It has **no task_type concept** at all (`grep task_type src/specify_cli/invocation/` → empty). `router.py`'s `routing_priority` scoring (:156-157) is *which-agent-to-pick*, not *which-model*.
3. **The charter reference DANGLES** — `model_task_routing` is not an activatable `ArtifactKind` (only 9: `artifact_kinds.py:80-88`) and is absent from the *generated* `references.yaml`. The sibling `autonomous-operation-protocol` (charter.md:106) — whose tactic file **already exists** (`src/doctrine/tactics/built-in/autonomous-operation-protocol.tactic.yaml`, `graph.yaml:367`) — is also absent from `references.yaml` because it has **no inbound directive `suggests` edge** (references.yaml is generated from directive-reachable artifacts via `reference_resolver.py:69-72`). A section-level gap: the "all references resolve" guarantee (charter.md:8-13) covers only the *Standing Orders* section.

**Structural subtlety (advisory-only ceiling).** `spec-kitty dispatch` **never spawns an LLM call** (`executor.py:150,181` — *"Does NOT spawn any LLM call. Returns synchronously."*); it hands a payload to the **calling agent**, which executes via its own host-level Agent-tool delegation. So a routing decision can only be **advisory data on the payload**, honored by the caller — never enforced in-process. The interactive model spawn is host-level (Claude Code's tool), outside this repo. **Honesty caveat:** there *is* an existing static model selector at the implement/review seam — `wp_metadata.py:150-163` resolves `AgentAssignment(tool, model, profile_id, role)` from a WP `agent:` field and carries `active_model` into status events. That is #1049-adjacent static config (not a doctrine-routed spawn), correctly scoped out here — but the rule "*nothing* consults model routing" overstates the void; this mission adds the *doctrine-routed advisory* layer, distinct from that static WP field.

**Capability-vs-cost-tier resolution.** The charter rule is about *capability* ("strongest model for hard judgment"); the schema's `CostTier`/`LatencyTier` are not capability tiers. The evaluator expresses capability through the **`objective: quality_first` + `weights.quality`** dimension of `routing_policy` — quality-first routing selects the strongest-fit model for high-judgment task types. No schema change to add a capability tier; the quality objective is the lever.

**Root cause.** The schema shipped in mission 057's bulk doctrine bootstrap (`623057f97`) with **no consumer ever scoped** (later only a parity fix, #1438/PR #1545). The consumer was never planned.

**Boundary vs [#1049](https://github.com/Priivacy-ai/spec-kitty/issues/1049) (OPEN)** — #1049 is a *static* per-step config (`agents.models.steps.*`); this is *doctrine-bound task-class* routing. Complementary, not overlapping; this mission builds no config surface. (See also [#1841](https://github.com/Priivacy-ai/spec-kitty/issues/1841) — same "rule instructed not structurally bound" pattern; cross-referenced, not folded.)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Governed dispatch surfaces a doctrine-routed advisory model recommendation (Priority: P1)

As an operator/agent using `spec-kitty dispatch`, I want the returned payload to carry an advisory model recommendation computed from the routing catalog for the resolved action's task-class, so delegated work runs on the model discipline dictates instead of silently inheriting the session model.

**Why this priority**: the core doctrine-fidelity gap. Advisory surfacing is the only code-enforceable lever.

**Independent Test**: with a populated catalog activated, `spec-kitty dispatch "<request>" --json` returns a recommendation whose value **changes when the catalog's scoring inputs change** and is **absent when the catalog is removed** (proving it's computed, not hardcoded).

**Acceptance Scenarios**:
1. **Given** an activated catalog scoring model M highest for the task_type mapped from action A, **When** `dispatch` resolves a profile+action A, **Then** the payload (`--json` + rich) carries recommended model M with provenance (source=catalog, task_type, objective).
2. **Given** the catalog's `task_fit`/`weights` are changed so model N wins, **When** the same dispatch runs, **Then** the recommendation changes to N — proving derivation, not a stub.
3. **Given** no catalog (or a match miss under `override_policy: advisory`), **When** dispatch runs, **Then** the recommendation is absent and dispatch still succeeds (non-fatal).

---

### User Story 2 - Per-profile model/effort override, honored by the evaluator (Priority: P2)

As an agent-profile author, I want an optional `model`/`effort` field on the profile that the evaluator honors per `override_policy`, so a profile can pin its tier (e.g. a reviewer on the strongest model).

**Why this priority**: profiles are the natural override anchor; without it the catalog is the only lever.

**Independent Test**: a profile declaring `model` changes the recommendation per `override_policy.mode`; an existing profile with no field loads unchanged and reaches the evaluator (not silently dropped).

**Acceptance Scenarios**:
1. **Given** a profile with `model: X` and catalog `override_policy: advisory`, **When** dispatch resolves it, **Then** the recommendation surfaces both the catalog pick and the profile declaration as provenance-tagged entries (advisory enforces neither; the caller sees both with sources) — deterministic, no silent override.
2. **Given** a profile without the field, **When** loaded via `AgentProfile.model_validate`, **Then** it validates unchanged AND the absent field is observable at the evaluator (the field reaches `profile.py`, not just the schema).

---

### User Story 3 - The charter model-discipline references resolve (Priority: P2)

As a governance maintainer, I want the charter's model-discipline reference (and the sibling) to resolve to activated doctrine via the DRG, so the rule is loadable through `charter context` — not a broken prose link.

**Independent Test**: `charter context` surfaces the model-discipline tactic guidance; both tokens resolve in the generated `references.yaml` via directive-reachability.

**Acceptance Scenarios**:
1. **Given** the new `model-task-routing` tactic + its directive `suggests` edge, **When** `references.yaml` is regenerated, **Then** the repointed charter token resolves to it (loadable, not just string-present).
2. **Given** the one-line `suggests` edge to the existing `autonomous-operation-protocol` tactic, **When** references regenerate, **Then** it too resolves.

### Edge Cases

- **Unpopulated/stale catalog** (`freshness_policy.max_catalog_age_hours` exceeded) → recommendation suppressed/flagged, dispatch succeeds.
- **action with no task_type mapping** → no recommendation (advisory), logged; dispatch unchanged.
- **`override_policy` gated/required** → out of scope this mission (advisory only, C-004); the evaluator reads the mode but only `advisory` is exercised.
- **`--json` vs rich render** → identical recommendation payload.
- **whole-file-invalid catalog YAML** → treated as absent (non-fatal), distinct from a malformed *entry* which fails schema validation at load.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Catalog loader | As a maintainer, I want a runtime loader that resolves the activated catalog path, parses YAML, validates against `ModelToTaskType`, and applies `freshness_policy` — removing `model_task_routing.models` from the dead-module allowlist (`test_no_dead_modules.py:251`) as the wiring lands. | High | Open |
| FR-002 | action → task_type mapping | As a maintainer, I want an explicit, maintained mapping from dispatch `action`/role verbs (`DEFAULT_ROLE_CAPABILITIES` canonical_verbs) to catalog `task_type` vocabulary, so the evaluator can key on task-class. Kept in sync with both namespaces. | High | Open |
| FR-003 | Routing evaluator | As a maintainer, I want a deterministic evaluator that, given task_type + profile, computes a recommendation from `task_fit` × `weights` under `objective` (quality_first = the capability lever), applies `tier_constraints`, and resolves `override_policy` precedence (advisory: emit catalog + profile as provenance-tagged candidates). Pure/stub-testable. | High | Open |
| FR-004 | Advisory recommendation on the dispatch payload | As a dispatch user, I want `ProfileInvocationExecutor.invoke()` to attach the evaluator's recommendation to a new `InvocationPayload` slot (`__slots__` + `to_dict()` + `_render_rich_payload()`), advisory and non-fatal, so the governed seam surfaces model discipline. | High | Open |
| FR-005 | Per-profile `model`/`effort` field (domain model) | As a profile author, I want an optional `model`/`effort` field added to `agent-profile.schema.yaml`'s **source** (`schema_models.py`, regenerated — not hand-edited YAML) AND to the **domain model** `AgentProfile` in `profile.py` with a kebab alias (mirroring `routing_priority` at :264), so it reaches the evaluator (not silently dropped by `extra='ignore'`). Back-compatible. | High | Open |
| FR-006 | `model-task-routing` tactic + DRG resolution | As a governance maintainer, I want a new `model-task-routing.tactic.yaml` (kebab) carrying the routing guidance + catalog pointer, a `graph.yaml` node, an activated-directive → `tactic:model-task-routing` `suggests` edge, and the charter prose token **repointed** from snake_case `model_task_routing` to `model-task-routing`, so `references.yaml` (regenerated) resolves it. | High | Open |
| FR-007 | Resolve `autonomous-operation-protocol` (one-line edge) | As a maintainer, I want a single activated-directive → `tactic:autonomous-operation-protocol` `suggests` edge added to `graph.yaml` (the tactic already exists), closing the same-section dangling reference. | Medium | Open |
| FR-008 | Populated catalog instance | As a maintainer, I want a populated `model-to-task_type` catalog (models + task_fit + `objective: quality_first` policy + `override_policy: advisory` + `freshness_policy`), schema-valid, so FR-001/003 have real data. | Medium | Open |
| FR-009 | Durable no-dangling-reference invariant | As a platform maintainer, I want a refactor-stable test that parses **all** charter.md `→ \`token\`` references (every section) and asserts each resolves to a `references.yaml` id-suffix, so the section-level dangling class cannot recur. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Red-first through the governed dispatch surface | Behavior proven by tests failing pre-fix / passing post-fix through `spec-kitty dispatch` / `invoke()` payload contents — not the Pydantic model in isolation, not a stubbed recommendation. SC-001's derivation is proven by the vary-with-catalog check (FR-001/003). | Correctness | High | Open |
| NFR-002 | Advisory, non-fatal | Missing/stale/unmatched catalog → absent recommendation, dispatch succeeds. No fabricated in-process model spawn. | Reliability | High | Open |
| NFR-003 | Back-compat profiles | Existing profiles without `model`/`effort` validate and load unchanged; the field reaches the evaluator when present. | Compatibility | High | Open |
| NFR-004 | Evaluator determinism | Same catalog + task_type + profile → same recommendation; the scorer is pure and unit-tested on stable inputs. | Correctness | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Advisory-only at the governed seam | `invoke()` does not spawn models; routing is advisory payload data. Acknowledge `wp_metadata.py` `AgentAssignment.model` as the existing static WP selector (distinct, out of scope). Do not fabricate a spawn path. | Technical | High | Open |
| C-002 | DRG-driven resolution | Charter references resolve via the DRG (`suggests` edges → generated `references.yaml`), NOT manual `references.yaml`/`config.yaml` rows. FR-006/007 add graph edges + regenerate the bundle; note the `_LIBRARY`/synthesis-manifest regeneration step (generated-lockfile; can red CI if skipped). | Technical | High | Open |
| C-003 | Boundary vs #1049 | Charter-bound task-CLASS routing, NOT #1049's static `agents.models.steps.*`. Build no config surface. | Technical | High | Open |
| C-004 | Advisory override mode only | Ship `override_policy: advisory`. `gated`/`required` require a mature, freshness-verified catalog — out of scope; evaluator reads the mode but only advisory is exercised. | Technical | High | Open |
| C-005 | Non-breaking + generated-schema discipline | The profile field is OPTIONAL; the agent-profile schema is GENERATED from `schema_models.py` — regenerate, never hand-edit the `.yaml`. Watch the `model_` protected-namespace on the Pydantic field (alias if needed). | Technical | High | Open |

### Key Entities

- **`ModelToTaskType` catalog** (`model_task_routing/models.py` + schema): dead today; loaded (FR-001), populated (FR-008), evaluated (FR-003).
- **action→task_type map** (new): bridges dispatch verbs to catalog vocabulary (FR-002).
- **`InvocationPayload`** (`executor.py:94-116`): gains a recommendation slot (FR-004).
- **`AgentProfile`** (`profile.py:255-264`) + schema source (`schema_models.py`): gains `model`/`effort` (FR-005).
- **`model-task-routing` tactic** + `graph.yaml` edges + `references.yaml` (generated): FR-006/007.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `spec-kitty dispatch --json` returns a catalog-computed recommendation whose value **changes with catalog scoring inputs** and is **absent when the catalog is removed** (proves derivation, not a stub); dispatch always succeeds.
- **SC-002**: a profile `model`/`effort` reaches the evaluator and affects the recommendation per `override_policy: advisory` (both candidates surfaced with provenance); profiles without it load unchanged.
- **SC-003**: both charter tokens resolve — the `model-task-routing` tactic loads via DRG traversal (not merely string-present in `references.yaml`); `charter context` surfaces the guidance body.
- **SC-004**: a refactor-stable, all-sections charter-reference invariant fails on pre-fix HEAD (both tokens dangling) and passes post-fix.

## Non-Goals *(out of scope)*

- Enforcing model tier on interactive Agent-tool delegations (host-level).
- #1049's static per-step config surface.
- `gated`/`required` override modes (need a mature catalog).
- Replacing `wp_metadata.py`'s static `AgentAssignment.model` WP field.
- Redesigning the routing schema / adding a capability-tier enum (the quality objective is the capability lever).
