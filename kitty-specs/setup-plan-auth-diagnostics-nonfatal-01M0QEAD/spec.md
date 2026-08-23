# Mission Specification: Nonfatal setup-plan auth diagnostics

**Mission Branch**: `fix/setup-plan-auth-diagnostics-nonfatal`  
**Created**: 2026-08-23  
**Status**: Draft  
**Input**: [GitHub issue #3621](https://github.com/Priivacy-ai/spec-kitty/issues/3621)

## Context and Intent

`setup-plan` performs local specification and plan-completeness verification, but it
currently refuses to perform that work when SaaS sync is enabled and its auth gate
cannot find a queue scope. Queue scope availability is not proof of authentication:
a valid browser-mediated login can use encrypted session storage and a refreshable
session without materializing a plaintext queue scope. The same refusal also blocks
genuinely logged-out operators even though local verification does not require hosted
sync.

This Mission makes authentication and queue-routing metadata distinct concepts. Local
verification always runs. Hosted-sync availability is reported as a nonfatal diagnostic,
and the local verification result alone determines whether `setup-plan` succeeds or
fails.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Complete local verification while logged out (Priority: P1)

An operator or automation agent runs `setup-plan` in a connected workspace while SaaS
sync is enabled but no authenticated session is available. The command completes its
local work and reports that hosted sync cannot be guaranteed without treating auth as
a precondition.

**Why this priority**: The current refusal blocks the normal planning loop and offers
remediation that an automation agent is not authorized to perform.

**Independent Test**: Run `setup-plan` against a complete plan in a connected,
logged-out workspace with SaaS sync enabled; verify the local result is successful, the
auth diagnostic is a warning, and the process exits successfully.

**Acceptance Scenarios**:

1. **Given** a connected workspace, no authenticated session, SaaS sync enabled, and a
   complete plan, **When** `setup-plan` runs with structured output, **Then** it reports
   phase completeness, includes one `SAAS_SYNC_UNAUTHENTICATED` warning, and exits 0.
2. **Given** the same auth state and a complete plan, **When** `setup-plan` runs with
   human-readable output, **Then** it prints a nonfatal auth warning and reports local
   verification success.

---

### User Story 2 - Recognize a valid login without queue scope (Priority: P1)

An operator who is logged in through the supported SaaS authentication flow runs
`setup-plan`. The login may use encrypted session storage, may have a refreshable
session with an expired short-lived access token, and may not have a materialized queue
scope. The command recognizes the authenticated state and does not display a false
unauthenticated warning.

**Why this priority**: The reported production case was a logged-in operator. A queue
scope lookup answered a routing question and was incorrectly treated as an auth check.

**Independent Test**: Represent a valid supported login without a queue-scope value,
run `setup-plan` with SaaS sync enabled, and verify no
`SAAS_SYNC_UNAUTHENTICATED` diagnostic appears.

**Acceptance Scenarios**:

1. **Given** a valid supported login stored without a queue scope, **When**
   `setup-plan` runs, **Then** no unauthenticated diagnostic is emitted and local
   verification proceeds normally.
2. **Given** a valid refreshable session whose short-lived access token has expired,
   **When** `setup-plan` runs, **Then** the absence of a queue scope does not cause the
   host to be classified as logged out.

---

### User Story 3 - Preserve the real completeness outcome (Priority: P2)

An operator runs `setup-plan` against an incomplete plan while logged out. The command
reports the plan-completeness problem as the blocking result; the auth warning remains
supplementary and does not replace or mask it.

**Why this priority**: Operators and agents need an actionable result for the work they
asked the command to verify.

**Independent Test**: Run `setup-plan` against an incomplete plan with SaaS sync enabled
and no authenticated session; verify the existing completeness failure is returned and
the auth state is only a warning.

**Acceptance Scenarios**:

1. **Given** an incomplete plan and no authenticated session, **When** `setup-plan`
   runs, **Then** its blocking result identifies plan incompleteness rather than auth.
2. **Given** either authentication state, **When** local verification produces the same
   result, **Then** the result's success/failure classification is identical.

### Edge Cases

- A login is valid but no plaintext session or credential file contains a queue scope.
- A refresh token remains usable while the short-lived access token has expired.
- Credentials or session material are genuinely absent.
- Auth state is unavailable while local verification succeeds.
- Auth state is unavailable while local verification fails for an unrelated reason.
- SaaS sync is not enabled; no new auth warning is introduced.
- Structured and human-readable output communicate the same severity without changing
  their established output contracts.

## Domain Language

- **Authentication state**: Whether the operator has a supported, usable SaaS login.
  It is not inferred from synchronization routing metadata.
- **Queue scope**: Metadata that identifies where synchronized work belongs. Its
  absence does not prove that an operator is logged out.
- **Local verification result**: The authoritative `setup-plan` assessment of local
  specification and plan readiness.
- **Hosted-sync diagnostic**: A report about whether hosted synchronization can be
  guaranteed; it is supplementary to local verification.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Local verification always runs | As an operator, I want `setup-plan` to perform local verification regardless of SaaS authentication state so that planning is never blocked by an unrelated hosted-sync condition. | High | Approved |
| FR-002 | Auth and queue scope are distinct | As a logged-in operator, I want authentication to be assessed independently of queue-scope availability so that supported login storage forms are recognized correctly. | High | Approved |
| FR-003 | No false unauthenticated diagnostic | As a logged-in operator with a supported usable session, I want no `SAAS_SYNC_UNAUTHENTICATED` diagnostic even when no queue scope is materialized. | High | Approved |
| FR-004 | Logged-out state is nonfatal | As a logged-out operator, I want hosted-sync unavailability reported as a warning so that I can still obtain the local verification result. | High | Approved |
| FR-005 | Verification controls exit outcome | As an automation caller, I want exit success or failure to be determined by local verification rather than authentication state so that the command remains scriptable and truthful. | High | Approved |
| FR-006 | Structured warning contract | As an automation caller, I want structured output to carry `SAAS_SYNC_UNAUTHENTICATED` in a warnings collection alongside the verification result. | High | Approved |
| FR-007 | Human-readable warning parity | As an interactive operator, I want a clear nonfatal warning in human-readable output that conveys the same severity as structured output. | Medium | Approved |
| FR-008 | Completeness failure remains primary | As an operator with an incomplete plan, I want the completeness failure reported as the blocking result rather than being replaced by an auth failure. | High | Approved |
| FR-009 | Consistent local-command policy | As a maintainer, I want `setup-plan` documented and tested consistently with sibling local Mission commands that proceed while logged out. | Medium | Approved |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Acceptance-matrix fidelity | All logged-in/logged-out × complete/incomplete acceptance scenarios defined above produce the specified verification result, warning severity, and exit outcome. | Reliability | High | Approved |
| NFR-002 | Zero false auth warnings | Every supported valid-login fixture, including encrypted storage without queue scope and a refreshable session with an expired short-lived access token, emits zero `SAAS_SYNC_UNAUTHENTICATED` diagnostics. | Correctness | High | Approved |
| NFR-003 | Single diagnostic | A genuinely logged-out invocation emits at most one `SAAS_SYNC_UNAUTHENTICATED` warning per command execution. | Usability | Medium | Approved |
| NFR-004 | Read-surface compatibility | All existing `setup-plan` read-surface behaviors unrelated to auth severity retain their established results, with the affected regression suite reporting zero new failures. | Compatibility | High | Approved |
| NFR-005 | Machine-readable stability | Every structured warning response remains parseable and includes both the local verification result and a stable warning code in 100% of covered logged-out cases. | Interoperability | High | Approved |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Token-expiry UX excluded | A general warning or workflow for expired access tokens is outside this Mission. | Scope | High | Approved |
| C-002 | No fail-closed opt-in | The optional `--require-sync` concept is not part of this Mission unless separately authorized. | Scope | Medium | Approved |
| C-003 | Sync flag is not an eligibility gate | `SPEC_KITTY_ENABLE_SAAS_SYNC=1` may enable hosted-sync reporting but must not make auth a prerequisite for local verification. | Product policy | High | Approved |
| C-004 | Preserve queue-scope meaning | Queue scope remains synchronization routing metadata and must not be redefined as authentication state. | Domain integrity | High | Approved |
| C-005 | Preserve supported login forms | Browser-mediated and encrypted-session login forms remain supported; the Mission must not narrow valid auth to plaintext queue-scope-bearing files. | Compatibility | High | Approved |
| C-006 | Respect release dependency | Finalization follows the 3.2.6 execution DAG dependency on issue #3127. | Coordination | Medium | Approved |

### Key Entities

- **Authentication State**: Logged-in or logged-out classification derived from the
  supported login authority rather than queue-routing metadata.
- **Queue Scope**: Optional synchronization routing context; related to hosted delivery
  but not proof of authentication.
- **Verification Result**: Local completeness outcome, including success or the actual
  local blocking reason.
- **Warning Diagnostic**: Nonfatal, stable-coded information that may accompany a
  verification result without replacing it.

## Assumptions and Dependencies

- Issue #3621 and its maintainer comments are the authoritative product ruling.
- The existing sibling-command behavior tracked by #2695 is the policy reference for
  nonfatal logged-out handling.
- The existing false-negative credential work in the historical
  `legacy-journal-capture-cutover` Mission is related context, not a second authority;
  this Mission owns the superseding nonfatal `setup-plan` outcome.
- Issue #3127 is the upstream release-DAG dependency; specification work may proceed,
  while final release readiness waits for that node.

## Out of Scope

- General access-token expiry detection, messaging, or re-login guidance.
- Changing the authentication method or asking agents to authenticate for operators.
- Changing queue/store placement, queue migration, or synchronization routing policy.
- Adding a default fail-closed mode or optional `--require-sync` flag.
- Altering local completeness rules unrelated to auth severity.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A complete plan on a logged-out connected workspace with SaaS sync enabled
  returns the successful local verification result, one nonfatal auth warning, and exit
  code 0 in every acceptance test.
- **SC-002**: A valid supported login without queue scope produces zero false
  unauthenticated diagnostics across all defined login-storage fixtures.
- **SC-003**: An incomplete plan reports its existing completeness failure in every auth
  state, with no auth-derived refusal replacing that result.
- **SC-004**: Structured and human-readable modes both communicate nonfatal severity in
  all logged-out acceptance cases.
- **SC-005**: The targeted existing `setup-plan` read-surface and sibling-command policy
  regression suites complete with zero failures attributable to this Mission.

## Definition of Done

- The logged-in, logged-out, complete-plan, and incomplete-plan scenarios are covered by
  rejecting-first acceptance tests.
- Auth state is no longer inferred from the presence of queue scope.
- Auth unavailability is a structured and human-readable warning, never the default
  blocking result.
- Documentation states the same nonfatal policy as the executable behavior.
- All targeted verification and quality gates pass without weakening unrelated guards.
