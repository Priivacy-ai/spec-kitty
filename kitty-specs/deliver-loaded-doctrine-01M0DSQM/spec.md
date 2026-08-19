# Mission Specification: Deliver Loaded Doctrine to the Agent

**Mission Branch**: `m4-doctrine-delivery`
**Created**: 2026-08-19
**Status**: Draft
**Input**: Charter-resolution program M4 — close the silent delivery/render no-ops (#3489, #3176, #3389, #3488 render half) so authored doctrine that loads and validates clean actually reaches the dispatched agent.

## Context

Two delivery pipelines carry governance to a dispatched agent — the **action-doctrine bundle** (activation-scoped doctrine for the current action) and the **profile channel** (doctrine a loaded agent profile attests). Each has silent no-ops: content loads, validates, reports healthy, then drops between authoring and consumption. The operator sees green checks and empty results.

This mission is M4 of the charter-resolution program (`docs/plans/charter-resolution/`). M1 (single-authority resolution parity) and M2 (DRG read-path bridge) have landed on `main`, so M4 can deliver **full org reach**, not just built-in/project. Scope is delivery/render/builder only; operating-procedures *edge wiring* (M3) and cascade-traversal completeness (M5) are out.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Glossary packs reach the agent (Priority: P1)

A doctrine author ships a glossary pack (canonical terms) in an org or project pack and activates it. Today `GLOSSARY_PACK` has `slot=None` in the action-bundle delivery table — one of two `None` rows lacking the module's required "stated reason" — and no renderer, so the pack is diagnostically present but structurally unreachable in **every** configuration.

**Why this priority**: This is the headline defect (#3489) — an entire authored artifact kind reaches no consumer, silently. It also anchors the "close the missing-reason class" work that the totality guard depends on.

**Independent Test**: Activate a glossary pack whose node is graph-reachable for an action; run `charter context --action <a>` and confirm the pack's term **names** appear under the action doctrine with a `--include glossary-pack:<id>` fetch pointer for full definitions — where before zero glossary content appeared.

**Acceptance Scenarios**:

1. **Given** an activated, graph-reachable glossary pack, **When** the agent loads action doctrine, **Then** the pack's term names render as a surface list plus a fetch pointer, and no full term definitions are inlined (token budget).
2. **Given** the delivery table after this mission, **When** the totality guard scans every `NodeKind` row, **Then** every `slot=None` row carries a stated reason (glossary resolved to a slot; `ANTI_PATTERN`'s twin `None`-without-reason row now carries its reason too).
3. **Given** an **org-authored** glossary pack (M2 bridge landed), **When** the agent loads action doctrine, **Then** it reaches the agent through the same path as a built-in pack.

---

### User Story 2 - Procedure and tactic step descriptions render (Priority: P1)

A doctrine author writes a procedure/tactic whose steps carry both a `title` and a longer `description`. Today the render reads only `title` (`title` is required, so `title or description` / `getattr(step, "title", …)` never reaches `description`), so the description half of every step — measured ~63% of step content — is undeliverable.

**Why this priority**: A large fraction of authored step content silently never arrives (#3488 render half). The fix is small and high-leverage.

**Independent Test**: Resolve a procedure whose steps carry descriptions; render it through both the action-doctrine bundle body and the profile-channel inline body; confirm each step's `description` appears alongside its `title`.

**Acceptance Scenarios**:

1. **Given** a procedure step with a non-empty `description`, **When** it renders in the action-doctrine bundle, **Then** the description appears alongside the title.
2. **Given** the same step, **When** it renders in the profile channel inline body, **Then** the description appears (not just the title).
3. **Given** a step with no `description`, **When** it renders, **Then** output is byte-identical to today (title only).

---

### User Story 3 - Project-overlay agent profiles are found (Priority: P1)

A project author writes an agent profile at `.kittify/agent_profiles/<id>.agent.yaml`. Today `build_activation_aware_doctrine_service` derives its project root from three fixed candidates (`.kittify/doctrine`, `src/doctrine`, `doctrine`) — none is `.kittify/agent_profiles` — so a migration of `default_profile_repository` onto the builder silently drops every project-overlay profile. Three named projection tests are red-carved-out today.

**Why this priority**: A project-authored profile silently vanishes when resolved through the activation-aware service (#3176), blocking the sole-door consolidation.

**Independent Test**: Seed `.kittify/agent_profiles/<id>.agent.yaml`; build the activation-aware service with the overlay seam; confirm the seeded profile is visible through `default_profile_repository` and the three carved-out projection tests pass.

**Acceptance Scenarios**:

1. **Given** a project profile at `.kittify/agent_profiles`, **When** `default_profile_repository` resolves via the builder overlay seam, **Then** the profile is visible (with `project` provenance).
2. **Given** the overlay param unset, **When** the builder constructs a service, **Then** the service is byte-identical to pre-mission (no regression for existing callers).
3. **Given** the migration, **When** the activation-aware wrapper is built, **Then** exactly one body constructs the wrapper and the service is always wrapped (single-wrapper-body invariant preserved).

---

### User Story 4 - `context --json` ships a typed `procedures[]` array (Priority: P2)

An external consumer pins the `charter context --json` payload shape. Today the text render ships procedures but the JSON omits a `procedures[]` array — `procedure` is folded only into the flat `references[]` — so the two renders disagree and a JSON consumer cannot read procedures as first-class.

**Why this priority**: Render parity + a versioned-contract obligation (#3389). Lower than P1 because it is additive and gated behind a deliberate schema bump rather than a silent-loss defect.

**Independent Test**: Run `charter context --action <a> --json` for an action that delivers procedures; confirm a typed `procedures[]` array is present under a bumped `context_schema_version`, decorated like the other typed arrays; confirm `asset` remains reference-only and is documented as such.

**Acceptance Scenarios**:

1. **Given** an action delivering procedures, **When** `--json` renders, **Then** a typed `procedures[]` array is present (fifth typed array), with per-entry reference/cadence decoration.
2. **Given** the payload, **When** a consumer reads `context_schema_version`, **Then** it is bumped (`1.0.0` → `1.1.0`) and `procedures` is in the top-level key ledger — atomically with the array promotion.
3. **Given** the payload, **When** a consumer looks for `asset`, **Then** `asset` is deliberately reference-only (in `references[]`, no typed array), stated in the versioned contract.

### Edge Cases

- **Glossary pack with many terms**: term-list renders **names only** + fetch pointer; full definitions are never inlined, so a large pack cannot blow the token budget.
- **Styleguide/toolguide bodies**: remain **pointer-only** (fetch stanza) by deliberate design; the choice is made explicit/discoverable in schema+docs rather than an unlabeled `body_fn=None` silent no-op.
- **Glossary pack not graph-reachable**: the slot+render row exist, but an unreachable pack still does not deliver — reachability/edge wiring is M3/M5, not this mission. The delivery no-op is closed regardless.
- **Overlay directory absent**: builder behaves exactly as before (no override), so legacy projects are unaffected.
- **Procedure step description empty/whitespace**: render falls back to title-only, byte-identical to today.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Glossary delivery slot | As a doctrine author, I want `GLOSSARY_PACK` to have a real action-bundle delivery slot (ACTIVATED gate) so an activated, graph-reachable glossary pack is delivered in the action-doctrine bundle. | High | Open |
| FR-002 | Glossary term-list render row | As a dispatched agent, I want a glossary render row that emits the pack's term **names** as a surface list plus a `--include glossary-pack:<id>` fetch pointer, so I get the terminology without full definitions being inlined. | High | Open |
| FR-003 | Close the missing-reason class | As a maintainer, I want every `slot=None` delivery-table row to carry the module's required stated reason after this mission — including `ANTI_PATTERN` (glossary's twin) — so no row is a silent, unexplained no-op. | High | Open |
| FR-004 | Render step description | As a doctrine author, I want procedure and tactic step `description` rendered alongside the required `title` across every render path (action-doctrine bundle body and profile-channel inline body), so authored step content is not dropped. | High | Open |
| FR-005 | Ratify styleguide/toolguide pointer-only | As a maintainer, I want the styleguide/toolguide profile-channel references to stay pointer-only (fetch stanza) with that choice made explicit and discoverable in schema+docs, so a deliberate budget decision is not an unlabeled silent no-op. | Medium | Open |
| FR-006 | Builder overlay seam | As a caller, I want an optional agent-profile overlay directory threaded through `_build_activation_aware_doctrine_service` → `_build_doctrine_service`, defaulting to no override, so a caller can point the project-profile overlay at `.kittify/agent_profiles`. | High | Open |
| FR-007 | Project-overlay profiles found | As a project author, I want `default_profile_repository` to resolve `.kittify/agent_profiles` profiles through the builder overlay seam so a project-authored profile is visible via the activation-aware service, deleting the carve-out that skipped the three projection tests. | High | Open |
| FR-008 | Typed `procedures[]` in JSON | As a JSON consumer, I want `charter context --json` to emit a typed `procedures[]` array (fifth typed array) decorated like the other typed arrays, so procedures are first-class and match the text render. | High | Open |
| FR-009 | Asset reference-only, stated | As a JSON consumer, I want `asset` to remain reference-only (folded into `references[]`, no typed array) with that asymmetry stated in the versioned contract as deliberate, so the shape is documented rather than accidental. | Medium | Open |
| FR-010 | Schema version bump + ledger | As a JSON consumer, I want `context_schema_version` bumped (`1.0.0` → `1.1.0`) and `procedures` added to the top-level key ledger atomically with the array promotion, so I can detect the shape moved instead of a silent surprise. | High | Open |
| FR-011 | Full org reach | As a doctrine author, I want org-authored glossary packs and procedures to reach the agent through the same delivery paths as built-in/project (M2 landed), so org doctrine is not second-class. | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Token budget respected | No render path emits full glossary term definitions inline (names-only surface list + pointer); the existing per-entry inline-body cap continues to gate any inline body with a fetch-stanza fallback, so the action-doctrine bundle / profile channel do not exceed the established budget. | Performance | High | Open |
| NFR-002 | Behavior-preserving defaults | With the overlay param unset and no glossary/description content present, the doctrine-service builder and all render paths produce byte-identical output to pre-mission; existing builder/service/render tests remain unchanged and green. | Reliability | High | Open |
| NFR-003 | Totality/parity guard intact | The delivery table stays totality-guarded (no `NodeKind` row without slot+reason) and the JSON top-level key set stays ledger-guarded (no undeclared key); both guards redden on any omission after this mission. | Reliability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Charter must not import specify_cli | The overlay-seam authority lives in the charter/doctrine layer; `charter` must not import `specify_cli` (dependency direction preserved). | Technical | High | Open |
| C-002 | Zero suppressions | New code passes `ruff` and `mypy --strict` with zero new suppressions (no blanket `# noqa`, `# type: ignore`, or per-file ignore additions). | Technical | High | Open |
| C-003 | Red-first per fix | Each defect gets a failing test proven red on the merge-base before its fix lands (green-before-check to attribute the red). | Technical | High | Open |
| C-004 | Delivery/render/builder only | OUT of scope: operating-procedures edge wiring (M3) and cascade-traversal completeness (M5). No cascade relation-set change; no golden-count ripple beyond the deliberate schema-version bump. | Technical | High | Open |
| C-005 | Versioned-contract discipline | The `procedures[]` promotion, `context_schema_version` bump, and ledger update are deliberate and atomic — never incidental. | Technical | High | Open |
| C-006 | Single-wrapper-body invariant | Only one body constructs the activation-aware wrapper, and the builder always wraps (R5); the overlay seam must not reintroduce a second construction site. | Technical | High | Open |
| C-007 | Action-bundle glossary only | Glossary is delivered via the action-bundle path only; no profile-channel glossary renderer is added (glossary is unattested by the profile schema — consistent with the asset/anti-pattern/paradigm C-007 deferrals). | Technical | Medium | Open |

### Key Entities

- **Delivery-table row**: maps a `NodeKind` to a delivery `slot` (`None` = not delivered, with a stated reason) and a `gate` (`ACTIVATED` / `ALL`). Totality-guarded.
- **Action-doctrine bundle**: the per-kind typed id lists (directives, tactics, styleguides, toolguides, procedures, assets, + glossary after this mission) resolved for an action; rendered by the bootstrap-text render rows.
- **Profile-channel section**: per-kind rendered references a loaded agent profile attests (directive/tactic/styleguide/toolguide/procedure/suggested-doctrine).
- **Context JSON payload**: the top-level `charter context --json` envelope — typed arrays + `references[]` + `context_schema_version`, guarded by the versioned-contract ledger.
- **Agent-profile overlay directory**: `.kittify/agent_profiles`, the project-overlay source the builder seam must be able to target.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An activated, graph-reachable glossary pack's term names appear in the agent's loaded action doctrine with a fetch pointer for full definitions — where before **zero** glossary content reached the agent.
- **SC-002**: **Zero** delivery-table `slot=None` rows lack a stated reason (glossary resolved to a slot; anti-pattern twin gains its reason).
- **SC-003**: A procedure/tactic step carrying a `description` shows that description in the rendered doctrine — recovering the ~63% of step content that was undeliverable.
- **SC-004**: A profile authored at `.kittify/agent_profiles/<id>.agent.yaml` is visible through the activation-aware doctrine service; the three previously red-carved projection tests pass and the carve-out is deleted.
- **SC-005**: `charter context --action <a> --json` includes a typed `procedures[]` array whenever procedures are delivered, under `context_schema_version` `1.1.0`, with `asset` documented as deliberately reference-only.
- **SC-006**: With the overlay param unset, the doctrine-service builder output is byte-identical to pre-mission (no regression for existing callers) — verified by the unchanged builder/service test suite.
- **SC-007**: The full targeted test suite for touched modules passes with `ruff` + `mypy --strict` clean and zero new suppressions.

## Assumptions

- The DRG can resolve glossary-pack nodes into an action closure when edges exist; M4 makes the *delivery/render* home exist so a reachable pack is delivered. Whether packs are reachable (edge/cascade wiring) is M3/M5.
- M2's org DRG read-path bridge is on `main`, so org-authored glossary/procedure artifacts can reach the delivery paths (full org reach).
- The existing per-entry inline-body budget primitive (`_PROFILE_INLINE_BODY_LIMIT_CHARS`) remains the token-budget gate for inline bodies; this mission does not change the budget threshold.
