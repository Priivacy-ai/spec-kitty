# Pending SaaS Contract Amendment: Refresh Token Lifetime Metadata

**Status**: PROPOSED — blocking TTL-sensitive UX in this mission
**Target**: SaaS epic #49 (mission `032-browser-mediated-cli-auth-renewable-sessions`)
**Affects**: `POST /oauth/token` response schema (all grant types)
**Author**: spec-kitty CLI mission 080, post-tasks review
**Date**: 2026-04-09

---

## Problem

The CLI cannot reliably display refresh token expiry, warn the user before
forced re-login, or compute a remaining-session countdown without an explicit
server-provided refresh-token lifetime. The current SaaS token endpoint
contract (see `oauth-token-endpoint.md` and the SaaS-side
`protected-endpoints.md`) returns only `expires_in` (access token TTL) — there
is no field for the refresh token's TTL.

Spec.md C-008 says "refresh token TTL is ~90 days (SaaS token policy)", but the
SaaS-side merged implementation currently mixes 30-day, 90-day, and
"renewable indefinitely" semantics across different code paths. A
client-hardcoded 90-day default would codify drift, not resolve it.

The CLI mission therefore refuses to hardcode any refresh TTL. Until this
amendment lands, the CLI sets `refresh_token_expires_at = None` and treats
refresh expiry as server-managed: it only learns about expiry via a
`400 invalid_grant` response on a refresh attempt.

This blocks the following CLI behaviors:

1. **`spec-kitty auth status` "expires in N days" display** for the refresh
   token. Current state: `auth status` shows the refresh token row as
   `Refresh token: server-managed (no client-known TTL)`.
2. **Proactive expiry warnings** in `auth status` when refresh expiry is near.
3. **"Session ends in" countdown** before forced re-login.
4. **Optimistic re-login prompts** when the CLI can predict a refresh failure
   before it happens.

These behaviors are explicitly marked as DEPENDENT on this amendment in:

- `kitty-specs/080-browser-mediated-oauth-cli-auth/spec.md` constraint C-012
- `kitty-specs/080-browser-mediated-oauth-cli-auth/data-model.md` StoredSession
  notes on `refresh_token_expires_at`
- `kitty-specs/080-browser-mediated-oauth-cli-auth/tasks/WP04-browser-login-flow.md`
  T025 (build_session) notes
- `kitty-specs/080-browser-mediated-oauth-cli-auth/tasks/WP05-headless-login-flow.md`
  T030 (build_session) notes
- `kitty-specs/080-browser-mediated-oauth-cli-auth/tasks/WP07-status-command.md`
  T038 (duration formatter) notes

---

## Proposed Amendment

Add the following fields to the `POST /oauth/token` response (all grant types:
authorization_code, refresh_token, urn:ietf:params:oauth:grant-type:device_code).

### New field: `refresh_token_expires_in`

```json
{
  "access_token": "at_xyz...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "rt_xyz...",
  "refresh_token_expires_in": 7776000,    ← NEW (90 days = 7776000s, example)
  "issued_at": "2026-04-09T13:37:14Z",    ← NEW (recommended; lets client compute exact expiry)
  "scope": "offline_access",
  "session_id": "sess_xyz..."
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `refresh_token_expires_in` | integer | **Yes** | Refresh token TTL in seconds, computed from `issued_at`. Server is the source of truth for the lifetime; CLI MUST NOT assume a default. |
| `issued_at` | ISO 8601 string | Recommended | When the tokens were issued, server clock. Lets the client compute the exact expiry without local-clock drift. If absent, the client uses its own `now()` as a fallback (small drift acceptable). |

### Validation Rules

- `refresh_token_expires_in` MUST be a positive integer
- `refresh_token_expires_in` MUST be ≥ `expires_in` (refresh outlives access)
- `issued_at` (if present) MUST be a valid ISO 8601 timestamp in UTC
- Both fields MUST be returned by all three grant types (authorization_code,
  refresh_token, device_code) so the CLI can update them on every refresh

### Backwards Compatibility

This is an additive amendment. Older CLI versions ignore unknown fields. The
CLI shipped from this mission tolerates the absence of these fields by setting
`refresh_token_expires_at = None` and degrading the affected UX, so the SaaS
side can roll out the amendment independently of any CLI release.

---

## CLI-Side Implementation Plan (after amendment lands)

Once SaaS adds the fields, the CLI side does **not** need a new mission. The
existing `_build_session()` helpers in WP04/WP05 already read
`tokens.get("refresh_token_expires_in")` (returning `None` if absent). When
the field appears, the next refresh fills in `refresh_token_expires_at`. WP07
status display already branches on `is None` to show the right message.

Specifically:

1. WP01 `session.py` already declares `refresh_token_expires_at: Optional[datetime]`
2. WP04 `_build_session()` reads `tokens.get("refresh_token_expires_in")` and
   sets `now + timedelta(seconds=...)` if present, else `None`
3. WP05 `_build_session()` does the same
4. WP07 `_print_token_expiry()` shows "server-managed" when `None`, otherwise
   shows the human-readable duration

No code changes are needed when the amendment lands beyond verifying that
the new fields appear in real refresh responses.

---

## Open Questions for SaaS Team

1. **Renewal semantics**: Does refresh token TTL extend on every refresh (sliding
   window) or stay fixed from initial login (absolute expiry)?
   - If sliding: the CLI needs to update `refresh_token_expires_at` on every
     successful refresh — already supported by the existing
     `TokenRefreshFlow._update_session()` shape
   - If absolute: the CLI should set `refresh_token_expires_at` once at login
     and never update it during refresh
   - Document the chosen semantics in the amendment doc on the SaaS side

2. **Inactive session expiry**: Is the 90-day (or whatever) TTL extended on
   token use, or only on refresh? If extended on use, does `/api/v1/me` count
   as use? CLI behavior depends on the answer.

3. **Server clock vs client clock**: If `issued_at` is omitted, how should the
   CLI handle clock skew (e.g., user's laptop is 10 minutes off NTP)?
   Recommendation: include `issued_at` as a `Recommended` field and document
   that clients should fall back to local `now()` if absent.

---

## Acceptance Criteria for SaaS Side

- [ ] `POST /oauth/token` returns `refresh_token_expires_in` for all grant types
- [ ] `POST /oauth/token` returns `issued_at` (recommended) for all grant types
- [ ] Documentation in SaaS contract docs (`oauth-token-endpoint.md`,
      `protected-endpoints.md`) updated with the new fields
- [ ] At least one SaaS test verifies the new fields appear in token responses
- [ ] SaaS team confirms the renewal semantics (sliding vs absolute) and
      documents it in the amendment

---

## Acceptance Criteria for CLI Side (this mission)

The CLI mission can ship without this amendment landing. After the amendment
lands, CLI behavior automatically improves with no code changes required:

- [ ] WP01 `StoredSession.refresh_token_expires_at` is `Optional[datetime]`
- [ ] WP04/WP05 `_build_session()` reads `tokens.get("refresh_token_expires_in")`
      and sets `refresh_token_expires_at` only if present
- [ ] WP07 `_print_token_expiry()` displays "server-managed (no client-known TTL)"
      when `refresh_token_expires_at is None`
- [ ] WP01 `TokenManager.refresh_if_needed()` only checks
      `is_refresh_token_expired()` if the value is set; otherwise lets the SaaS
      reject refresh attempts with `invalid_grant`
- [ ] No CLI code anywhere contains a hardcoded 90-day (or any other) refresh TTL
