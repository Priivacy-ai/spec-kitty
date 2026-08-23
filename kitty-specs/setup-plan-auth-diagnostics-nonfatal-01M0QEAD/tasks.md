---
description: "Work packages for authoritative local setup-plan and safe hosted refusal"
---

# Work Packages: Authoritative local setup-plan with safe hosted refusal

**Inputs**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md),
[data-model.md](data-model.md), [contract](contracts/setup-plan-result-envelope.md),
[quickstart.md](quickstart.md)
**Mission**: `setup-plan-auth-diagnostics-nonfatal-01M0QEAD`
**Planning base / merge target**: `fix/setup-plan-auth-diagnostics-nonfatal`

## Delivery Strategy

Four work packages follow the actual authority boundaries. WP01 preserves tri-state
truth inside the canonical auth subsystem. WP02 composes auth, structural, route, and
enablement evidence into one hosted decision without altering canonical preflight. WP03
separates local lifecycle persistence from hosted fan-out and may proceed independently.
WP04 integrates the three seams into setup-plan, freezes every local outcome, and adds
the non-vacuous hosted-effect gate.

Every WP is ATDD-first: its first implementation commit must contain a failing test that
is red on `planning_base_branch` and green on the final WP commit.

---

## Work Package WP01: Canonical tri-state authentication evaluation (Priority: P0)

**Goal**: Preserve authenticated, logged-out, and unknown at the TokenManager authority
and project that typed result into readiness without queue-scope or network access.
**Independent Test**: Real isolated session storage distinguishes absent from unreadable,
recognizes an expired-access/usable-refresh session, and keeps Boolean compatibility.
**Prompt**: [tasks/WP01-canonical-auth-evaluation.md](tasks/WP01-canonical-auth-evaluation.md)
**Requirement Refs**: FR-002, FR-003, FR-004, FR-005, FR-006

### Included Subtasks

T001 Write and commit rejecting TokenManager/readiness tri-state acceptance tests

T002 Preserve storage-load and materialization outcomes in TokenManager and expose typed local auth evaluation

T003 Project typed auth into readiness while preserving Boolean compatibility and Teamspace distinctions

T004 Run focused auth, readiness, lint, typing, and queue-independence gates

### Implementation Notes

- Information loss is fixed where storage is first read, not reconstructed downstream.
- `is_authenticated` remains a Boolean compatibility projection.
- No queue-scope reader, refresh, HTTP client, or SaaS call participates.

### Parallel Opportunities

- Test fixtures in the two owned test files can be prepared in parallel, but production
  work is one cohesive authority change.

### Dependencies

- None.

### Risks & Mitigations

- Existing Boolean callers could change behavior → pin compatibility explicitly.
- Hot-summary materialization could still collapse errors → test cold and hot paths.

---

## Work Package WP02: Hosted assessment and decision (Priority: P0)

**Goal**: Add a setup-plan-specific, no-raise assessment adapter and one immutable,
fail-closed hosted-effects decision with ordered structured diagnostics.
**Independent Test**: A pure decision matrix proves only authenticated + safe + routable
allows effects, while returned and raised structural failures produce separate warnings.
**Prompt**: [tasks/WP02-hosted-assessment-decision.md](tasks/WP02-hosted-assessment-decision.md)
**Requirement Refs**: FR-007, FR-008, FR-012

### Included Subtasks

T005 Write and commit rejecting hosted-decision truth-table tests

T006 Implement the setup-plan-only no-raise structural boundary adapter

T007 Implement immutable diagnostic and HostedSyncDecision composition

T008 Verify disabled-mode short-circuit, deterministic ordering, sanitization, lint, and typing

### Implementation Notes

- The adapter consumes `run_preflight(..., require_auth=False)` and never modifies it.
- Unknown authentication, boundary, or route state refuses hosted effects.
- Diagnostic severity is warning; hosted disposition is refused.

### Parallel Opportunities

- WP02 starts after WP01 because it consumes the typed auth evaluation.

### Dependencies

- Depends on WP01.

### Risks & Mitigations

- A raw exception could leak secrets → stable reasons and sanitized evidence only.
- Route availability could become auth → separate input and diagnostic code.

---

## Work Package WP03: Lifecycle persistence and fan-out split (Priority: P0)

**Goal**: Make local lifecycle JSONL persistence explicit and independent from hosted
adapter fan-out while preserving the existing composed API for other callers.
**Independent Test**: Local-only artifact-phase emission writes exactly one valid event
and invokes zero registered SaaS handlers; legacy composed emission still fans out once.
**Prompt**: [tasks/WP03-lifecycle-persistence-fanout-split.md](tasks/WP03-lifecycle-persistence-fanout-split.md)
**Requirement Refs**: FR-009, FR-010

### Included Subtasks

T009 Write and commit rejecting local-persistence versus hosted-fan-out tests

T010 Extract explicit local persistence and hosted fan-out operations

T011 Add a supported local-only artifact-phase emission path and preserve composed compatibility

T012 Run lifecycle, producer-conformance, adapter-fanout, lint, and typing regressions

### Implementation Notes

- Local persistence must not import, resolve, or call hosted adapters.
- Existing callers of `append_lifecycle_event()` retain composed behavior.
- Returned event envelopes become intents consumed later by WP04.

### Parallel Opportunities

- WP03 has no code dependency on WP01 or WP02 and can run in parallel with them.

### Dependencies

- None.

### Risks & Mitigations

- Duplicate JSONL or fan-out → assert exact call and event counts.
- Existing status emitters regress → run producer and registered-adapter suites.

---

## Work Package WP04: setup-plan orchestration and compatibility (Priority: P0)

**Goal**: Integrate the local and hosted lanes, guard every hosted effect, emit one
authoritative result, and prove the complete compatibility and production-chain matrix.
**Independent Test**: The real setup-plan entry point preserves every baseline local
outcome/exit across auth and boundary variants, writes local events, and performs zero
hosted calls whenever the decision refuses.
**Prompt**: [tasks/WP04-setup-plan-orchestration-compatibility.md](tasks/WP04-setup-plan-orchestration-compatibility.md)
**Requirement Refs**: FR-001, FR-005, FR-006, FR-007, FR-008, FR-009, FR-010, FR-011, FR-012, FR-013, FR-014, FR-015

### Included Subtasks

T013 Capture baseline payloads/exits and commit the rejecting setup-plan compatibility matrix

T014 Replace early auth and boundary exits with evidence collection and one hosted decision

T015 Route local lifecycle intents and every hosted sink through the explicit executor boundary

T016 Introduce one local-outcome reporter and attach diagnostics to all eligible success, blocked, and error paths

T017 Add real encrypted-storage production-chain and structural-exception acceptance tests

T018 Add the non-vacuous hosted-effect architectural gate and named sibling-policy documentation parity

T019 Run targeted regressions, requirement evidence, and issue 3127 release-closeout check

### Implementation Notes

- Structural assessment begins only after repository-root resolution.
- Pre-root failures retain their existing payload and do not fabricate structural data.
- Local JSONL, artifact work, documentation wiring, and safe commits remain local.
- Lifecycle fan-out, dossier work, queues, daemon/dashboard publication, and any newly
  discovered hosted sink require `allow_effects=true`.

### Parallel Opportunities

- Baseline fixture capture and architectural census drafting may proceed in parallel
  before the production integration, within this single ownership package.

### Dependencies

- Depends on WP01, WP02, and WP03.

### Risks & Mitigations

- Hidden return/raise path loses warnings → matrix covers every emitter class.
- New sink bypasses decision → AST gate has a runnable synthetic violation.
- Original defect survives mocks → real encrypted-storage entry-point fixtures.

---

## Dependency & Execution Summary

- **Sequence**: WP01 → WP02; WP03 runs in parallel; WP01 + WP02 + WP03 → WP04.
- **Parallelization**: WP03 is an independent lane. WP01 test fixtures and WP03 tests
  are also file-disjoint.
- **MVP Scope**: All four WPs. Each foundation is independently reviewable, but issue
  #3621 is not user-complete until WP04 integrates them.
- **Release gate**: GitHub issue #3127 must be resolved before Mission acceptance or
  release readiness; it is not a code-lane dependency.

## Requirements Coverage Summary

| Requirement ID | Covered By Work Package(s) |
|---|---|
| FR-001 | WP04 |
| FR-002 | WP01 |
| FR-003 | WP01 |
| FR-004 | WP01 |
| FR-005 | WP01, WP04 |
| FR-006 | WP01, WP04 |
| FR-007 | WP02, WP04 |
| FR-008 | WP02, WP04 |
| FR-009 | WP03, WP04 |
| FR-010 | WP03, WP04 |
| FR-011 | WP04 |
| FR-012 | WP02, WP04 |
| FR-013 | WP04 |
| FR-014 | WP04 |
| FR-015 | WP04 |

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|---|---|---|---|---|
| T001 | Rejecting tri-state tests | WP01 | P0 | No |
| T002 | TokenManager typed evaluation | WP01 | P0 | No |
| T003 | Readiness projection | WP01 | P0 | No |
| T004 | Auth/readiness gates | WP01 | P0 | No |
| T005 | Rejecting decision matrix | WP02 | P0 | No |
| T006 | No-raise boundary adapter | WP02 | P0 | No |
| T007 | Hosted decision composition | WP02 | P0 | No |
| T008 | Decision quality gates | WP02 | P0 | No |
| T009 | Rejecting lifecycle split tests | WP03 | P0 | No |
| T010 | Explicit persistence/fan-out operations | WP03 | P0 | No |
| T011 | Local-only phase emission | WP03 | P0 | No |
| T012 | Lifecycle quality gates | WP03 | P0 | No |
| T013 | Baseline and rejecting compatibility matrix | WP04 | P0 | Yes |
| T014 | Evidence collection integration | WP04 | P0 | No |
| T015 | Hosted executor boundary | WP04 | P0 | No |
| T016 | One local-outcome reporter | WP04 | P0 | No |
| T017 | Production-chain acceptance | WP04 | P0 | Yes |
| T018 | Architectural gate and policy docs | WP04 | P0 | Yes |
| T019 | Integrated gates and release check | WP04 | P0 | No |
