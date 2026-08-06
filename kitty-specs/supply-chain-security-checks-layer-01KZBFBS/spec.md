# Mission Specification: Supply Chain Security Checks Layer

**Mission Branch**: `feat/supply-chain-security-checks-layer`
**Created**: 2026-08-06
**Status**: Draft
**Input**: `/Users/zohar/Downloads/shai-hulud_research_brief_c998a584.plan.md`

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Security checks are embedded into software-dev mission flow (Priority: P1)

As a mission operator, I want software-dev `plan`, `implement`, and `review` to consistently surface install-time and dependency supply-chain checks so every mission receives the same baseline defense against worm-style package compromise.

**Why this priority**: Workflow-level coverage is the primary value of this mission. Without workflow wiring, security checks remain optional and uneven.

**Independent Test**: Resolve charter context and software-dev action metadata for `plan`, `implement`, and `review`; verify the new security directive/tactic bindings are present and visible.

**Acceptance Scenarios**:

1. **Given** a software-dev mission entering `plan`, **When** action context is resolved, **Then** security design and supply-chain checks are included in plan-time guidance.
2. **Given** a software-dev mission entering `implement`, **When** action context and step contract are resolved, **Then** supply-chain checks are required before the normal quality gate transition.
3. **Given** a software-dev mission entering `review`, **When** action context and step contract are resolved, **Then** review-time supply-chain checks are explicitly required before approval recommendations.

---

### User Story 2 - Agent profiles apply consistent supply-chain guardrails (Priority: P1)

As a reviewer or implementer profile user, I want profile guidance to require registry authenticity checks, package freshness visibility, lifecycle-script discipline, and Node LTS awareness so agents do not silently approve risky dependency actions.

**Why this priority**: Profile behavior is the enforcement surface users experience directly; if profiles are not updated, workflow wiring alone is insufficient.

**Independent Test**: Resolve profile payloads and charter context for the targeted profiles; verify security references and self-review expectations are present where intended.

**Acceptance Scenarios**:

1. **Given** `reviewer-renata` in security-audit mode, **When** review guidance is loaded, **Then** the profile requires registry verification, package age reporting, and rejection of silent script allowlisting.
2. **Given** implementer profiles handling JavaScript or TypeScript dependencies, **When** self-review is performed, **Then** the profile requires deny-by-default lifecycle script handling and Node LTS skew awareness.
3. **Given** non-JS-first profiles, **When** software-dev context still includes JS tooling changes, **Then** profile guidance still flags supply-chain checks as required where relevant.

---

### User Story 3 - The security layer remains advisory in v1 without breaking existing gates (Priority: P2)

As a maintainer, I want the new layer to improve detection and decision quality without introducing a new fail-closed transition gate in v1, so adoption can happen safely before repository-specific hard gates are designed.

**Why this priority**: The mission explicitly targets a standing-order style rollout. Stability and compatibility with current merge/review flow are required.

**Independent Test**: Verify review step contracts and gate registry configuration do not add a new fail-closed handler while still adding security micro-steps.

**Acceptance Scenarios**:

1. **Given** the updated review step contract, **When** transitions are inspected, **Then** existing transition-gate behavior remains unchanged while new security review steps are present.
2. **Given** repositories with different validator maturity levels, **When** missions run through software-dev flow, **Then** security checks are surfaced consistently without introducing unexpected hard-blocking behavior.

### Edge Cases

- Package exists but only on an unapproved mirror or unexpected namespace; mission guidance must require explicit operator attention.
- Package is newly published during an active incident window; guidance must force visibility and operator acknowledgment rather than silent acceptance.
- Project runs non-LTS or outdated Node for valid business reasons; guidance must document that rationale while still flagging elevated risk.
- Lifecycle scripts are required for legitimate native builds; guidance must support explicit allowlisting with documented justification instead of blanket script enablement.

## Domain Language

- **Supply-chain install safety**: controls focused on dependency origin/authenticity, lifecycle script execution, and install-time compromise patterns.
- **Registry authenticity check**: confirmation that the selected package and version resolve on the approved official registry.
- **Package freshness signal**: age and recency metadata (first publish and version publish/update timing) used to inform risk decisions.
- **Lifecycle script approval discipline**: deny-by-default handling of `preinstall`/`install`/`postinstall` scripts unless explicitly justified.
- **Node LTS skew**: mismatch between project/runtime Node versions and current Active LTS baseline.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Author supply-chain install safety directive | As a mission operator, I need a built-in directive that defines required supply-chain controls for software-dev missions, including official registry verification, package age/last-update visibility, deny-by-default lifecycle script handling, Node Active LTS awareness, incident-list awareness, and IoC/persistence awareness for install-time worm patterns. | High | Open |
| FR-002 | Extend dependency hygiene for JavaScript and TypeScript | As an implementer, I need dependency hygiene guidance to include JavaScript and TypeScript so package authenticity, freshness, script discipline, lock behavior, and Node runtime baseline checks are covered alongside existing language guidance. | High | Open |
| FR-003 | Add supply-chain install safety tactic | As a reviewer and implementer, I need an operational tactic with concrete checkpoints (registry existence check, freshness report, no automatic script approvals, Node LTS awareness, IoC/persistence checks, review evidence expectations). | High | Open |
| FR-004 | Wire security artifacts into software-dev action indexes | As a mission operator, I need `plan`, `implement`, and `review` actions to include the new directive/tactic bindings so security checks are part of standard context resolution. | High | Open |
| FR-005 | Add security micro-steps to software-dev step contracts | As a mission operator, I need step contracts to include explicit security check steps in plan/implement/review sequencing while preserving existing transition gate behavior in v1. | High | Open |
| FR-006 | Bind targeted agent profiles to the security layer | As a profile user, I need relevant built-in profiles (review and implementation focused) to include the new supply-chain checks so behavior is consistent with workflow-level governance. | High | Open |
| FR-007 | Update software-dev SOURCE mission-step guidance | As an agent operator, I need source prompts/guidelines to reference the new security checks so generated agent surfaces inherit the behavior through canonical upgrade flow. | Medium | Open |
| FR-008 | Provide regression tests for doctrine and context wiring | As a maintainer, I need automated tests proving the new directive/tactic/profile and action/step-contract bindings resolve correctly in software-dev contexts. | High | Open |
| FR-009 | Preserve advisory rollout strategy in v1 | As a maintainer, I need v1 to remain advisory (no new fail-closed gate handler) while still requiring visibility and evidence in plan/implement/review workflows. | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Context coverage consistency | 100% of software-dev action context resolutions for `plan`, `implement`, and `review` include at least one supply-chain security artifact introduced by this mission. | Reliability | High | Open |
| NFR-002 | Profile coverage consistency | 100% of targeted profile context resolutions (reviewer + implementation-focused profiles listed in scope) expose the new supply-chain expectations after mission changes. | Reliability | High | Open |
| NFR-003 | Advisory compatibility | 0 new fail-closed transition gate handlers are introduced by this mission in software-dev review flow; existing transition gates continue operating with no additional hard-block configuration requirements. | Compatibility | High | Open |
| NFR-004 | Validation fidelity | New or updated tests for this mission pass with no unresolved placeholders and demonstrate red-to-green behavior for at least one action-index wiring path, one step-contract wiring path, and one profile-binding path. | Quality | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Source-of-truth edits only | Changes must be made only to canonical source doctrine and mission files; generated agent copies are out of scope. | Process | High | Open |
| C-002 | No new built-in AppSec persona in v1 | The mission must enhance existing built-in profiles rather than adding a new built-in security-specialist persona. | Scope | High | Open |
| C-003 | No fail-closed security gate in v1 | The mission must not introduce a new fail-closed transition gate handler for software-dev review flow in this release. | Technical | High | Open |
| C-004 | No live external denylist sync in core | The mission must not add continuously synced external package denylist ingestion into Spec Kitty core behavior. | Scope | Medium | Open |
| C-005 | Terminology canon compliance | Mission artifacts must use canonical terminology conventions and avoid deprecated feature-language where mission-language is required. | Governance | Medium | Open |

### Key Entities

- **Supply-Chain Security Directive**: policy artifact that defines mandatory behavior for dependency/source/install-time safety decisions.
- **Supply-Chain Install Safety Tactic**: procedural checklist used during planning, implementation, and review to gather evidence and drive decisions.
- **Software-Dev Action Context**: resolved governance payload for `plan`, `implement`, and `review` actions.
- **Step Contract Security Step**: explicit mission step that inserts security review tasks into workflow sequencing.
- **Profile Security Binding**: profile-level directive/tactic/self-review references that enforce consistent behavior.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Software-dev action contexts for `plan`, `implement`, and `review` each include the new supply-chain security layer artifacts in automated validation.
- **SC-002**: Targeted built-in profiles resolve with documented supply-chain checks, including registry authenticity, package freshness visibility, script-approval discipline, and Node LTS awareness.
- **SC-003**: At least one automated test each validates action wiring, step-contract wiring, and profile binding introduced by this mission.
- **SC-004**: No new fail-closed security transition handler is added in v1, while review guidance still requires explicit security evidence before approval recommendation.

## Assumptions

- This mission follows a PR-bound workflow and starts from `feat/supply-chain-security-checks-layer` branched from current `main`.
- CAS incident guidance remains the operational source of truth for active package/version incident lists and escalation order.
- Advisory rollout in v1 is intentional; hard-gate ratcheting is deferred until repository-specific machine-checkable controls are standardized.
