# Data Model: Auth Local Trust And Multi-Process Hardening

## Local Auth Session

**Purpose**: Durable local authority for CLI hosted-auth state.

**Current owner**: `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/src/specify_cli/auth/session.py`

**Relevant fields**:

- Access-token state needed for hosted calls.
- Refresh-token state needed for renewal and revoke.
- Team list with `is_private_teamspace`.
- Default Teamspace id derived from available teams.
- Expiry metadata used by refresh checks.

**Invariants**:

- Durable storage remains encrypted file-only.
- Raw tokens are never printed in user output or diagnostics.
- A session that already includes a Private Teamspace must not need hosted `/api/v1/me` membership rehydrate for tests that do not exercise membership rehydrate.
- Missing, expired, revoked, or malformed sessions map to login-required guidance where hosted state is required.

## Teamspace Binding

**Purpose**: Indicates that a repository or workflow expects hosted Teamspace/tracker state.

**Current owner**: CLI sync/tracker configuration and local tracker store surfaces under:

- `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/src/specify_cli/sync/`
- `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/src/specify_cli/tracker/`

**States**:

- No binding: hosted/tracker guidance may be optional.
- Binding present, no active session: unauthenticated; show `spec-kitty auth login`.
- Binding present, active session without Private Teamspace: missing Private Teamspace or unauthorized.
- Binding present, active session with Private Teamspace: hosted direct-ingress paths may proceed.

**Invariants**:

- A binding must not cause a logged-out user to see generic `server_error`.
- Tracker package ownership is not assumed until a failing path proves it.

## Diagnostic Classification

**Purpose**: Stable user-facing and machine-facing outcome for hosted sync/tracker flows.

**Categories**:

- `unauthenticated`: no usable local session; recovery is `spec-kitty auth login`.
- `direct_ingress_missing_private_team`: direct ingress cannot proceed because Private Teamspace is unavailable.
- `unauthorized`: hosted service rejects access for a domain/permission reason other than missing local auth.
- `retryable_transport`: timeout, connection failure, or temporary transport failure.
- `server_error`: true hosted 5xx or unexpected server failure.

**Invariants**:

- Missing Private Teamspace must not be represented as `server_error`.
- Token material and audit internals are not included in user-visible diagnostics.
- JSON or automation-facing outputs should remain deterministic across repeated runs.

## Refresh-Lock Test Session

**Purpose**: Hermetic test fixture for machine-wide refresh-lock behavior.

**States**:

- Expired fake session that requires refresh.
- Refreshed fake session with Private Teamspace present.
- Refreshed fake session where post-refresh membership hook is explicitly patched out because it is not under test.

**Invariants**:

- Default concurrency tests perform zero real hosted `/api/v1/me` calls.
- Setting `SPEC_KITTY_SAAS_URL` in the developer shell must not change default test semantics.
- Hosted smoke tests must be explicitly marked or invoked separately.

## Exception Suppression Justification

**Purpose**: Auditable reason attached to broad exception suppressions in auth/storage paths.

**Fields**:

- File path.
- Line number.
- Suppression marker such as `noqa: BLE001`.
- Inline safety reason.

**Validation rules**:

- Missing reason fails.
- Empty or generic reason fails.
- Specific reasons explain why swallowing, translating, downgrading, or logging the exception is safe.

## Session Hot-Path Handoff

**Purpose**: Optional cross-process coordination aid for many short-lived local CLI processes.

**Authority relationship**:

- Durable encrypted session storage is authoritative.
- Handoff/cache state is derived and invalidatable.
- Missing, stale, unreadable, or mismatched handoff state falls back to durable storage.

**Safety rules**:

- Do not introduce OS credential-manager dependencies.
- Do not expose raw token material in output.
- Refresh coordination remains single-flight or equivalent across processes.
- Benign replay and lock contention are recoverable coordination outcomes, not user-facing fatal errors.
