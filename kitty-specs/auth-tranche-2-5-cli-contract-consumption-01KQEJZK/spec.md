# CLI Auth Tranche 2.5 Contract Consumption

## Overview

Server Tranche 2 has shipped token-family lineage, `/oauth/revoke`, refresh replay semantics, and `/api/v1/session-status`. The CLI still consumes an older contract in logout, refresh, and diagnostics. This mission aligns four CLI surfaces with the live server contract so that logout is truthful about server revocation, refresh handles benign replay without resending spent tokens, and diagnostics can optionally verify live session status.

**Mission type**: software-dev
**Target branch**: auth-tranche-2-5-cli-contract-consumption

## Actors

- **CLI user**: Person running `spec-kitty auth` commands on their machine.
- **Server (Tranche 2)**: The deployed SaaS backend. Its auth contract is fixed and in scope only for reference.

## User Scenarios & Testing

### Scenario 1: Normal logout (refresh token available, server reachable)

The user runs `spec-kitty auth logout`. The CLI calls `POST /oauth/revoke` with the refresh token, receives a 200 revocation response, then deletes local credentials. Output confirms server revocation and local cleanup both succeeded.

### Scenario 2: Logout when server is unreachable

The user runs `spec-kitty auth logout` while offline. The revoke call fails with a network error. The CLI still deletes local credentials and reports that local cleanup completed, but server revocation was not confirmed. The command does not exit as a total failure — the user's primary intent (clearing local state) succeeded.

### Scenario 3: Logout with no refresh token in local state

The user's local session has expired or was partially cleared. No refresh token is available. The CLI performs best-effort local cleanup and reports that server revocation could not be attempted (no credential to authorize the revoke call). Output is clear about what did and did not happen.

### Scenario 4: Logout when server returns a genuine error (5xx)

The server returns HTTP 500 on `/oauth/revoke`. The CLI treats this as unconfirmed revocation, completes local cleanup, and reports server revocation failed. It does not report server revocation as successful.

### Scenario 5: Token refresh — benign replay (409)

Background: a refresh was attempted, the network dropped after the server processed the request, and the CLI retries. The server returns HTTP 409 with `error_code: refresh_replay_benign_retry`. The CLI reloads the persisted session from disk. If the persisted refresh token differs from the spent one (the server already advanced it), the CLI retries with the newer token. If the persisted token matches the spent one, the CLI surfaces an ambiguous retryable error and does not resend the spent token.

### Scenario 6: Token refresh — suspicious/invalid (401)

The server returns HTTP 401 (invalid grant or family mismatch). The CLI stops retrying and surfaces guidance for the user to re-authenticate. It does not loop indefinitely.

### Scenario 7: Auth doctor (default, local only)

The user runs `spec-kitty auth doctor`. The command performs its existing local checks — credential presence, expiry, local format — and produces a report. It makes no outbound network calls. Output includes a hint: _Run `spec-kitty auth doctor --server` to verify server session status._

### Scenario 8: Auth doctor with --server flag

The user runs `spec-kitty auth doctor --server`. The CLI refreshes the access token if it is expired or near expiry, then calls `GET /api/v1/session-status` with a valid access token. Output reports:
- Session active (with no token internals in output), or
- Session invalid / needs re-authentication (on 401 from session-status).

### Scenario 9: Dev smoke verification

A developer runs the full auth flow — login, status, doctor, doctor --server, logout — against `https://spec-kitty-dev.fly.dev` with `SPEC_KITTY_ENABLE_SAAS_SYNC=1` and `SPEC_KITTY_SAAS_URL` set. All commands complete without error.

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | `auth logout` calls `POST /oauth/revoke` with the refresh token (and `token_type_hint=refresh_token`) when a refresh token is present in local state. | Proposed |
| FR-002 | Logout output distinguishes three outcomes: (a) server revocation confirmed and local cleanup completed; (b) server revocation not confirmed but local cleanup completed; (c) local cleanup failed. Outcome (b) must not be presented as total command failure. | Proposed |
| FR-003 | Local credential deletion must complete even when `/oauth/revoke` is unreachable, times out, or returns a network error. | Proposed |
| FR-004 | If no refresh token is available in local state, `auth logout` performs best-effort local cleanup and reports that server revocation could not be attempted. | Proposed |
| FR-005 | A genuine server failure (HTTP 5xx) on `/oauth/revoke` must not be reported as successful server revocation. | Proposed |
| FR-006 | The refresh flow detects HTTP 409 with `error_code: refresh_replay_benign_retry` as a benign replay condition. | Proposed |
| FR-007 | On benign 409 replay, the CLI reloads the persisted auth session under the existing local lock/transaction model, then retries the refresh only if the reloaded refresh token differs from the spent token. | Proposed |
| FR-008 | On benign 409 replay, if the persisted refresh token matches the spent token, the CLI surfaces an ambiguous retryable error without resending the spent token. | Proposed |
| FR-009 | On refresh HTTP 401 (invalid grant or suspicious token), the CLI stops retrying and instructs the user to re-authenticate. | Proposed |
| FR-010 | Successful refresh responses preserve all existing stored-session fields that the CLI already depends on: `refresh_token_expires_in`, `refresh_token_expires_at`, `scope`, `session_id`, and any team or session metadata present in the response. | Proposed |
| FR-011 | Default `auth doctor` (no flags) remains entirely local and offline; it makes no outbound network calls. Its output includes a hint: "Run `spec-kitty auth doctor --server` to verify server session status." | Proposed |
| FR-012 | `auth doctor --server` refreshes the access token if needed, then calls `GET /api/v1/session-status` with a valid, unexpired access token. | Proposed |
| FR-013 | `auth doctor --server` reports session status as active or as requiring re-authentication. Output contains no raw tokens, token-family IDs, or revocation internals. | Proposed |
| FR-014 | `auth doctor --server` on HTTP 401 from session-status instructs the user to re-authenticate and does not expose the revocation reason. | Proposed |
| FR-015 | Tests cover: `/oauth/revoke` request shape and 200 handling, server 5xx distinction, refresh 409 benign replay path, refresh 409 with matching spent token, refresh 401 suspicious path, `auth doctor --server` active path, and `auth doctor --server` 401 path. | Proposed |
| FR-016 | Legacy test assertions for the retired `/api/v1/logout` endpoint are updated or removed. Default `auth doctor` tests asserting no outbound calls must continue to pass. | Proposed |
| FR-017 | A dev smoke checklist is provided covering login → status → doctor → doctor --server → logout against `https://spec-kitty-dev.fly.dev` with the required environment variables. | Proposed |

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | CLI output never exposes raw tokens, lookup hashes, token family IDs, peppers, or audit metadata in any output path — including error and diagnostic paths. | Zero instances across all output paths | Proposed |
| NFR-002 | Server revocation status reporting is accurate: the CLI reports "confirmed" only when it has received a successful revocation-state response; it reports "not confirmed" in all other cases. | 100% accuracy | Proposed |
| NFR-003 | The benign replay retry path submits the spent refresh token zero additional times after the 409 is received. | 0 duplicate token submissions | Proposed |
| NFR-004 | Logout outcome (b) — server revocation not confirmed, local cleanup succeeded — is communicated as a partial outcome, not a command failure. Exit code and user-facing message both reflect that the primary local-cleanup intent was fulfilled. | User study or manual review confirms non-failure framing | Proposed |

## Constraints

| ID | Constraint | Status |
|----|-----------|--------|
| C-001 | Refresh must use `POST /oauth/token` with `grant_type=refresh_token` and `client_id=cli_native`. No new auth endpoint may be introduced for refresh. | Accepted |
| C-002 | Logout revocation must use `POST /oauth/revoke`. The legacy `/api/v1/logout` endpoint is retired and must not be called. | Accepted |
| C-003 | No server-side changes are in scope. Server Tranche 2 contract is fixed. | Accepted |
| C-004 | Default `auth doctor` must not make outbound network calls. Server-aware behavior is gated behind the `--server` flag. | Accepted |
| C-005 | The spent refresh token must not be printed or persisted during diagnostics, logs, or failure reports — including 409 error handling and any debug output. | Accepted |
| C-006 | Sync queue cleanup (issue #889) is out of scope. Tranche 2.5 must not create a dependency on resolved queue behavior. | Accepted |
| C-007 | Web/admin force-revocation UI, replay cache, and encrypted credential cache are out of scope. | Accepted |

## Success Criteria

1. `auth logout` calls `/oauth/revoke` in all cases where a refresh token is available, confirmed by test coverage and dev smoke.
2. Logout output correctly distinguishes server revocation success, server revocation failure, and local cleanup failure in 100% of tested paths.
3. Local credential deletion succeeds when the server is unreachable, confirmed by offline-mode tests.
4. Refresh benign replay never resends the spent token, confirmed by unit test asserting zero duplicate submissions.
5. Refresh 401 invalid-grant leads to re-authentication guidance, not an infinite retry loop.
6. `auth doctor` (default) passes all existing offline tests without regressions.
7. `auth doctor --server` successfully reports session status against the dev server in the dev smoke run.
8. No legacy `/api/v1/logout` assertions remain in the test suite after the migration.

## Key Entities

| Entity | Description |
|--------|-------------|
| Refresh token | Short-lived credential used to authorize both token refresh (`/oauth/token`) and revocation (`/oauth/revoke`). Consumed on use; a new one is issued on successful refresh. |
| Access token | Short-lived credential used to call authenticated endpoints including `/api/v1/session-status`. |
| Local session state | The persisted auth record on disk, protected by the existing local lock/transaction model. Contains refresh token, access token, expiry fields, session_id, scope, and team metadata. |
| Token family | Server-side lineage tracking for a refresh token chain. The CLI does not read or emit family identifiers. |
| Benign replay | A 409 response from `/oauth/token` indicating the server already processed an identical refresh request. The current token may have been advanced in the server's state. |

## Assumptions

1. The server's `/oauth/revoke` returns HTTP 200 with `{"revoked": true}` for any token-state outcome (including already-revoked tokens). Only HTTP 5xx indicates a genuine server error.
2. Session-status returns HTTP 401 for both expired and revoked access tokens, without disclosing the specific reason. The CLI does not attempt to distinguish these cases.
3. The existing local lock/transaction model in `refresh_transaction.py` is the correct place to reload persisted session state on 409 replay; no new locking mechanism is needed.
4. `token_type_hint=refresh_token` is the correct hint for the revoke call when using the refresh token.
5. Dev smoke can be run against `https://spec-kitty-dev.fly.dev` with `SPEC_KITTY_ENABLE_SAAS_SYNC=1` set; the known issue #889 (sync queue ingress errors) does not affect auth smoke paths.

## Out of Scope

- Server-side auth changes (Server Tranche 2 is already deployed)
- Sync queue cleanup (issue #889)
- Web or admin force-revocation UI
- Replay cache or encrypted credential cache
- Any new auth endpoint beyond the three defined in the server contract (`/oauth/token`, `/oauth/revoke`, `/api/v1/session-status`)
