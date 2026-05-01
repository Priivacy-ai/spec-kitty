# Research: CLI Auth Tranche 2.5 Contract Consumption

## Phase 0 Findings

### D1 — Existing Logout Call (Retired)

**Finding**: `_auth_logout.py` currently POSTs to `POST /api/v1/logout` with an `Authorization: Bearer <access_token>` header and no request body. This endpoint is retired in Tranche 2.

**Impact**: The entire `_call_server_logout` function must be removed and replaced with `RevokeFlow.revoke()`. The existing behavior where server-side failures downgrade to warnings is preserved in spirit — local cleanup is still unconditional — but the semantics of the three outcome states change.

**References**: `src/specify_cli/cli/commands/_auth_logout.py:_call_server_logout`

---

### D2 — Revoke Contract (RFC 7009)

**Finding**: `POST /oauth/revoke` uses token-possession authorization — no `Authorization` header required. The request body carries `token` (the refresh token) and optionally `token_type_hint=refresh_token`. The response is always `{"revoked": true}` with 200 for any syntactically valid token shape (including already-revoked, expired). HTTP 5xx indicates a genuine server error. HTTP 429 is throttling.

**Impact**:
- `RevokeFlow` must distinguish 200 from 5xx. A 200 is revocation-confirmed regardless of whether the token was still valid.
- A 5xx must never be reported as "revoked successfully."
- 400 means malformed request (missing token field) — treat as `SERVER_FAILURE`.
- Token possession means the request works with an expired access token. No need to refresh before revoking.

**Decision**: `RevokeFlow` returns a `RevokeOutcome` enum rather than raising exceptions, matching the "never raises" contract that `_call_server_logout` already had.

**References**: `spec-kitty-saas/kitty-specs/saas-cli-token-family-and-revocation-01KQATJN/contracts/revoke.yaml`

---

### D3 — Refresh 409 Contract

**Finding**: `POST /oauth/token` with `grant_type=refresh_token` now returns 409 for benign replay. The body is `{"error": "refresh_replay_benign_retry", ..., "retry_after": N}` where N is 0–5 seconds. This means the presented refresh token was spent within the server's reuse-grace window and a new token exists in persisted state. The server does NOT revoke the token family on 409.

**Impact**: The CLI should:
1. Raise `RefreshReplayError` from `TokenRefreshFlow.refresh()`.
2. In `_run_locked`, catch it, re-read persisted session, and compare refresh tokens.
3. If the persisted token differs (newer), retry once with that token.
4. If the persisted token matches the spent one, surface `LOCK_TIMEOUT_ERROR` (no newer token available yet; caller may retry later).

The 401 path is unchanged — `invalid_grant` means family revocation or genuine expiry; the user must re-authenticate.

**Note**: The start-here.md described the 409 body field as `error_code`; the actual contract uses `error` (standard OAuth envelope). Implementation must check `body.get("error") == "refresh_replay_benign_retry"`.

**References**: `spec-kitty-saas/kitty-specs/saas-cli-token-family-and-revocation-01KQATJN/contracts/refresh.yaml`

---

### D4 — Session-Status Contract

**Finding**: `GET /api/v1/session-status` requires a valid, unexpired access token via `Authorization: Bearer`. Returns 200 with `{"session_id", "current_generation", "created_at", ..., "status": "active"}` for a live session. Returns a generic 401 for expired, revoked, or invalid tokens — the body does NOT disclose is_revoked, revocation_reason, or token_family_id.

**Impact**:
- `_check_server_session()` must refresh first if the access token is expired or near expiry, then call this endpoint.
- The 200 response exposes `current_generation` and `session_id` — these are safe to log/display (not token-family internals).
- On 401, doctor output says "re-authenticate" without attempting to determine why the session is invalid.
- Fields like `token_family_id`, `is_revoked`, `revocation_reason` are explicitly absent from the response per the contract's `additionalProperties: false`.

**References**: `spec-kitty-saas/kitty-specs/saas-cli-token-family-and-revocation-01KQATJN/contracts/session-status.yaml`

---

### D5 — Existing Transaction Model (read-decide-refresh-reconcile)

**Finding**: `run_refresh_transaction` already implements a bounded, machine-wide-locked sequence:
1. Acquire `MachineFileLock`.
2. Reload persisted session.
3. If persisted is newer and valid → adopt without network call (`ADOPTED_NEWER`).
4. Otherwise call `refresh_flow.refresh(persisted)`.
5. On `RefreshTokenExpiredError`/`SessionInvalidError`: re-read persisted; compare identity `(session_id, refresh_token)`; if rejected token is current → delete (`CURRENT_REJECTION_CLEARED`); if stale → preserve repersisted (`STALE_REJECTION_PRESERVED`).

**Impact for 409 replay**: The new `RefreshReplayError` handling in `_run_locked` follows the same re-read-and-compare pattern. The comparison is the refresh token only (not full identity), since the replay means the server has already rotated the token, so `session_id` is unchanged but `refresh_token` should differ in persisted state if another process completed the rotation.

**References**: `src/specify_cli/auth/refresh_transaction.py`

---

### D6 — Existing Auth Doctor Contract

**Finding**: `_auth_doctor.py` is explicitly offline (`C-007` in its own module docstring). It reads local files and probes `127.0.0.1` ports only. The `assemble_report` function is pure data-gather; no mutation. `doctor_impl` takes `json_output`, `reset`, `unstick_lock`, `stuck_threshold` parameters. The `auth.py` typer command wires these directly.

**Impact**: Adding `--server` requires:
- New `server: bool = False` parameter on `doctor_impl`
- New `--server` typer Option in `auth.py` doctor command (line ~101)
- New async `_check_server_session()` function that calls `asyncio.run()` internally or is called via `asyncio.run()` in `doctor_impl`
- The `assemble_report` function is NOT changed — server status is appended as a separate rendered section

**References**: `src/specify_cli/cli/commands/_auth_doctor.py`, `src/specify_cli/cli/commands/auth.py:101`

---

### D7 — StoredSession Serialization

**Finding**: `StoredSession.to_dict()` has an explicit field list (not `asdict()`). `from_dict()` reads fields with explicit keys. Adding `generation: int | None = None` requires:
- Append field to dataclass (after all existing fields, with default)
- Add `"generation": self.generation` to `to_dict()` return dict
- Add `generation=data.get("generation")` to `from_dict()` call

Deserialization is backward-compatible because `data.get("generation")` returns `None` for sessions stored before Tranche 2.5. No migration needed.

**References**: `src/specify_cli/auth/session.py`

---

### D8 — Refresh Response Field Preservation

**Finding**: `TokenRefreshFlow._update_session()` already preserves `scope`, `session_id`, `user_id`, `email`, `name`, `teams`, `default_team_id`, `auth_method`, and `storage_backend` from the existing session. It reads `access_token`, `refresh_token`, `expires_in`, `refresh_token_expires_at`/`refresh_token_expires_in` from the response.

**Impact for FR-010**: The new `generation` field from the Tranche 2 response must be captured via `tokens.get("generation")` and stored in the returned `StoredSession`. No other existing field is at risk of being dropped — the preservation is already correct.

**References**: `src/specify_cli/auth/flows/refresh.py:_update_session`

## Alternatives Considered

| Topic | Rejected Alternative | Reason |
|-------|---------------------|--------|
| 409 retry location | New `RefreshOutcome.REPLAY_RETRY_NEEDED` surfaced to token_manager | Adds product-level complexity for a mechanical recovery step. Keeps the lock across two transactions, doubling the lock-contention window. |
| generation storage | Don't persist (`Ignore in Tranche 2.5`) | Lossy round-trips: every refresh would drop a server-supplied value. Once useful (local/server mismatch check), adding it requires a migration. |
| Revoke client | Inline `_call_server_revoke()` in `_auth_logout.py` | False-success behavior is security-relevant. Test injection is cleaner with a dedicated class. Consistent with `TokenRefreshFlow` pattern. |
| Revoke encoding | JSON body | Both work per contract. Form encoding matches existing httpx usage in logout. No preference from server side. |
