# Feature Specification: Auth Local Trust And Multi-Process Hardening

**Feature Branch**: `auth-local-trust-and-multi-process-hardening-01KQW587`  
**Created**: 2026-05-05  
**Status**: Draft  
**Input**: User description: "Create a CLI mission for auth-adjacent trust, diagnostics, and local multi-process hardening from the workspace start-here.md handoff."

## Intent Summary

CLI users and maintainers need tracker-bound and hosted-sync workflows to fail truthfully, remain hermetic in local tests, and stay efficient for many short-lived local processes after the browser/device OAuth work has already shipped. This mission does not redesign OAuth, token refresh, logout, revoke, or server session-status behavior. It closes the remaining CLI-side reliability gaps around logged-out Teamspace guidance, Private Teamspace ingress classification, broad exception suppression guardrails, refresh-lock test isolation, and cross-process session hot-path behavior while preserving encrypted file-only storage as the durable root of trust.

## Domain Language

- **Teamspace**: The user's hosted workspace context used by tracker-bound and sync-capable CLI workflows.
- **Private Teamspace**: A Teamspace state required for direct ingress acceptance; missing Private Teamspace access is an authorization/domain condition, not a generic server outage.
- **Hosted sync/tracker workflow**: Any CLI flow that depends on hosted session, Teamspace, tracker, or direct ingress state.
- **Durable root of trust**: The encrypted file-only session storage under the user's Spec Kitty auth directory.
- **Local session hot path**: Cross-process behavior that reduces repeated expensive local session work without replacing durable encrypted storage.
- **Broad exception suppression**: Any broad catch or `BLE001` suppression in auth or secure-storage paths that could hide meaningful failures unless it includes an explicit safety reason.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Logged-Out Tracker Guidance (Priority: P1)

A developer has a repository bound to a Teamspace or tracker, but their local CLI session is logged out or expired. When they run a command that needs hosted state, the CLI clearly explains that login is required and points them to `spec-kitty auth login` instead of surfacing a vague tracker, sync, or server error.

**Why this priority**: This is the most visible trust failure. Users can recover only if the CLI names the actual condition and next action.

**Independent Test**: Can be tested with a tracker-bound or Teamspace-bound repository and no active auth session; the command must produce a login-required diagnostic and avoid generic server-error wording.

**Acceptance Scenarios**:

1. **Given** a Teamspace-bound repository with no active local auth session, **When** the user runs a hosted-sync or tracker-bound command, **Then** the CLI reports that login is required and tells the user to run `spec-kitty auth login`.
2. **Given** a Teamspace-bound repository with an expired or missing local session, **When** the hosted state check cannot proceed, **Then** the CLI classifies the condition as unauthenticated rather than tracker failure, sync failure, or server failure.

---

### User Story 2 - Direct Ingress Authorization Classification (Priority: P1)

A developer runs `sync now` or a related direct-ingress flow, and the hosted service rejects the request because Private Teamspace access is missing. The CLI reports the existing direct-ingress/private-teamspace category instead of classifying the failure as a generic `server_error`.

**Why this priority**: Misclassifying authorization/domain failures as server failures sends users and operators to the wrong recovery path.

**Independent Test**: Can be tested by simulating a direct-ingress 403 for missing Private Teamspace access and verifying the CLI's user-facing category and machine-facing classification.

**Acceptance Scenarios**:

1. **Given** direct ingress rejects a sync request because Private Teamspace access is missing, **When** the CLI formats the result, **Then** the user sees a Private Teamspace/direct-ingress diagnostic rather than a generic server failure.
2. **Given** the same rejection is consumed by automation, **When** the machine-facing result is inspected, **Then** it preserves the direct-ingress classification and does not emit `server_error`.

---

### User Story 3 - Hermetic Refresh-Lock Tests (Priority: P1)

A maintainer runs auth concurrency tests in a developer shell that has a hosted SaaS URL configured. The tests remain hermetic and never call the hosted `/api/v1/me` membership rehydrate path unless the test is explicitly marked as a hosted dev smoke test.

**Why this priority**: Local test behavior must not depend on the developer's shell environment or accidentally contact the dev deployment.

**Independent Test**: Can be tested with `SPEC_KITTY_SAAS_URL` set to the dev deployment and a guard that fails if refresh-lock tests attempt hosted membership rehydrate or network access.

**Acceptance Scenarios**:

1. **Given** `SPEC_KITTY_SAAS_URL` is set in the environment, **When** the auth machine refresh-lock concurrency tests run, **Then** they complete using hermetic fakes and make no real hosted membership request.
2. **Given** a test intentionally validates hosted auth behavior, **When** it requires a real hosted service, **Then** it is marked or scoped as a dev smoke test rather than being part of the default hermetic concurrency suite.

---

### User Story 4 - Auth Exception Accountability (Priority: P2)

A maintainer reviews auth, CLI auth-command, or secure-storage code. Broad exception suppressions are either absent or include a specific inline reason explaining why translating or swallowing the exception is safe.

**Why this priority**: Auth and storage failures are trust boundaries. Silent broad catches make real failures look benign.

**Independent Test**: Can be tested with a guard that scans auth/storage paths and fails on unjustified broad exception suppressions.

**Acceptance Scenarios**:

1. **Given** auth or secure-storage code contains a broad exception suppression, **When** the guard checks the affected paths, **Then** the suppression must include a specific safety justification.
2. **Given** a broad exception suppression lacks a justification, **When** the guard runs, **Then** it fails with the affected path and line.

---

### User Story 5 - Multi-Process Local Session Hot Path (Priority: P2)

A developer or automation invokes many short-lived CLI processes in one local session. The CLI coordinates session refresh and reduces repeated expensive local session work while keeping encrypted file-only storage as the durable source of truth.

**Why this priority**: The shipped storage model is correct, but repeated local process startup should not make normal workflows slow or refresh-racy.

**Independent Test**: Can be tested by running multiple short-lived local CLI processes against the same session state and verifying that they coordinate refresh and avoid repeated unnecessary session rehydration work.

**Acceptance Scenarios**:

1. **Given** many local CLI processes start close together with the same valid session, **When** they need hosted state, **Then** they avoid redundant expensive local session work where a safe shared handoff is available.
2. **Given** a refresh is required while multiple local processes are active, **When** the first process coordinates the refresh, **Then** peers observe a consistent session result without treating benign replay or lock contention as fatal.
3. **Given** any hot-path cache or handoff is missing, stale, or invalid, **When** the CLI needs session state, **Then** it falls back to encrypted file-only durable storage without exposing raw token material.

### Edge Cases

- A repository has tracker or Teamspace binding metadata but the user has never logged in locally.
- A local session exists but is expired, revoked, malformed, or unreadable.
- A direct-ingress response distinguishes missing Private Teamspace from unauthenticated, retryable transport failure, and true server failure.
- Developer shells set hosted auth environment variables during normal test runs.
- Many local processes start simultaneously and race on refresh or local session handoff.
- A broad catch is justified for cleanup, compatibility, or diagnostic translation but the reason is too generic to be auditable.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Status | Requirement | Acceptance Criteria |
| --- | --- | --- | --- |
| FR-001 | Confirmed | Hosted-sync and tracker-bound CLI commands MUST distinguish unauthenticated, unauthorized or missing Private Teamspace, retryable transport failure, and true server failure. | Tests cover each category and assert both user-facing wording and machine-facing classification. |
| FR-002 | Confirmed | When a Teamspace or tracker binding exists but no active local auth session exists, affected commands MUST tell the user to run `spec-kitty auth login`. | A logged-out Teamspace-bound workflow test asserts the login guidance and rejects generic tracker, sync, or server-error wording. |
| FR-003 | Confirmed | Direct-ingress 403 responses caused by missing Private Teamspace access MUST use the existing direct-ingress/private-teamspace classification rather than `server_error`. | A regression test for issue #889 asserts the exact classification for the missing Private Teamspace path. |
| FR-004 | Confirmed | Auth refresh-lock concurrency tests MUST remain hermetic when developer shells configure hosted SaaS URLs. | A regression test for issue #977 fails if the concurrency suite attempts hosted membership rehydrate or real network access under a configured hosted URL. |
| FR-005 | Confirmed | Default auth concurrency tests MUST not depend on `https://spec-kitty-dev.fly.dev` or any other hosted deployment unless explicitly marked as hosted dev smoke coverage. | The default concurrency command passes with hosted URL variables set and with hosted URL variables unset. |
| FR-006 | Confirmed | Auth, auth-related CLI command, and secure-storage paths MUST reject unexplained broad exception suppressions. | A guard fails on unjustified `BLE001` suppressions or equivalent broad catches in the scoped paths. |
| FR-007 | Confirmed | Any allowed broad catch in auth or secure-storage paths MUST include a specific inline reason that explains why swallowing, translating, or downgrading the exception is safe. | Guard coverage includes one allowed justified case and one failing unjustified case. |
| FR-008 | Confirmed | The CLI MUST preserve encrypted file-only session storage as the durable root of trust for local auth state. | Tests or packaging checks verify no Keychain, keyring, Secret Service, or credential-manager dependency is introduced. |
| FR-009 | Confirmed | The local session hot path MUST reduce repeated expensive session work for many short-lived local CLI processes without exposing raw token material in output, logs, or diagnostics. | Multi-process coverage verifies coordinated behavior and scans observable output for absence of token material. |
| FR-010 | Confirmed | Multi-process refresh behavior MUST handle benign refresh replay and lock contention without converting expected coordination outcomes into fatal user errors. | Concurrency tests cover peer processes observing a completed refresh and benign replay handling. |
| FR-011 | Confirmed | Existing shipped browser/device login, logout revoke, refresh replay, and server-session doctor behaviors MUST remain supported. | Focused regression tests for login-adjacent logout/revoke, refresh replay, and server doctor status continue passing. |

### Non-Functional Requirements

| ID | Status | Requirement | Measurement |
| --- | --- | --- | --- |
| NFR-001 | Confirmed | Default auth concurrency tests MUST complete without hosted network dependency in both hosted-URL-set and hosted-URL-unset developer environments. | The focused concurrency suite completes within 60 seconds in both environments. |
| NFR-002 | Confirmed | Auth diagnostic classification MUST be deterministic for the covered failure categories. | Re-running the focused classification tests 5 times produces the same category for each fixture. |
| NFR-003 | Confirmed | Local session hot-path behavior MUST improve repeated short-lived process startup cost without weakening durable storage. | A representative many-process scenario demonstrates fewer repeated expensive local session operations than the current baseline while preserving encrypted-file fallback. |
| NFR-004 | Confirmed | Guardrail feedback for unjustified broad exception suppression MUST be actionable. | A failing guard names every affected file and line in its output. |
| NFR-005 | Confirmed | User-facing diagnostics MUST avoid leaking sensitive auth material. | Tests assert diagnostics do not contain raw tokens, lookup hashes, peppers, family IDs, or audit metadata. |

### Constraints

| ID | Status | Constraint | Rationale |
| --- | --- | --- | --- |
| C-001 | Confirmed | This mission MUST NOT reimplement shipped Tranche 2 or Tranche 2.5 browser/device OAuth, token refresh, logout revoke, or session-status contracts. | The core auth path is already shipped; this mission is auth-adjacent hardening. |
| C-002 | Confirmed | This mission MUST NOT introduce Keychain, keyring, Secret Service, or OS credential-manager dependencies. | Current runtime storage is encrypted file-only and must remain so. |
| C-003 | Confirmed | This mission MUST NOT change the shipped server auth contract unless a separate SaaS mission explicitly owns that change. | This is the CLI mission; server contract changes need separate ownership. |
| C-004 | Confirmed | Tests MUST NOT depend on `https://spec-kitty-dev.fly.dev` unless they are explicitly marked as dev smoke tests. | Default local test suites must be hermetic. |
| C-005 | Confirmed | Tracker package changes are out of scope unless investigation proves tracker owns part of the classification or logged-out guidance failure. | The tracker repo is context-only unless ownership evidence appears. |
| C-006 | Confirmed | The local machine rule requiring `SPEC_KITTY_ENABLE_SAAS_SYNC=1` for hosted auth, tracker, or sync CLI testing MUST NOT be treated as a tracker rollout system. | The machine rule is local testing policy only. |

### Key Entities

- **Local Auth Session**: The user's durable encrypted-file auth state, including refreshable session information required by hosted CLI workflows.
- **Teamspace Binding**: Repository-local or user-local indication that a workflow expects hosted Teamspace or tracker state.
- **Direct Ingress Result**: The sync/tracker result category returned or derived when hosted direct ingress accepts, rejects, or cannot process a request.
- **Session Hot-Path Handoff**: A local, cross-process aid that can reduce repeated expensive session work while deferring to durable encrypted storage as authority.
- **Exception Suppression Justification**: The inline explanation attached to a broad catch or suppression in auth/storage paths.

## Assumptions

- The issue list from `start-here.md` is the confirmed source of truth for this CLI mission: CLI #829, #907, #889, #977, and the CLI side of SaaS #77.
- Existing CLI tests already cover parts of logout/revoke, refresh replay, doctor server status, secure-storage dependency exclusion, and packaging; this mission may extend rather than replace them.
- The known #977 diagnosis is test isolation, not proof that the refresh-lock algorithm is broken.
- Cross-process hot-path work may include cache, handoff, or lock coordination as long as it preserves encrypted file-only durable storage and does not expose token material.

## Non-Goals

- Rebuilding the OAuth browser/device login flow.
- Replacing encrypted file-only auth storage with OS credential managers.
- Changing SaaS OAuth, token, revoke, or session-status contracts from the CLI mission.
- Adding rollout gating to `spec-kitty-tracker`.
- Treating every hosted auth test as a dev deployment smoke test.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of covered hosted-sync and tracker-bound failure fixtures produce one of the expected categories: unauthenticated, missing Private Teamspace or unauthorized, retryable transport failure, or true server failure.
- **SC-002**: The logged-out Teamspace workflow displays `spec-kitty auth login` guidance in every covered user-facing command path.
- **SC-003**: The issue #889 regression fixture produces the direct-ingress/private-teamspace classification in both user-facing and machine-facing outputs, with zero `server_error` classifications for that case.
- **SC-004**: The issue #977 concurrency test passes within 60 seconds when `SPEC_KITTY_SAAS_URL` is set and performs zero real hosted membership requests.
- **SC-005**: The broad-exception guard reports zero unjustified broad exception suppressions in the scoped auth/storage paths.
- **SC-006**: Packaging or dependency checks continue to report zero Keychain, keyring, Secret Service, or OS credential-manager dependencies.
- **SC-007**: Multi-process local session coverage demonstrates coordinated refresh or handoff behavior for concurrent short-lived processes without leaking raw token material in observable output.
