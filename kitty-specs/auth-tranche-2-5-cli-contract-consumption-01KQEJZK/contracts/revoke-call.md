# CLI Contract: Revoke Call

**Endpoint**: `POST /oauth/revoke`
**Canonical source**: `spec-kitty-saas/kitty-specs/saas-cli-token-family-and-revocation-01KQATJN/contracts/revoke.yaml`

## Request

```
POST /oauth/revoke
Content-Type: application/x-www-form-urlencoded

token=<refresh_token>&token_type_hint=refresh_token
```

- No `Authorization` header. Token possession is the proof of authorization.
- `token`: the refresh token from local session state.
- `token_type_hint`: always `refresh_token` when the CLI holds a refresh token.
- Body must not contain session_id, token_family_id, or any other field.

## Responses and CLI Behavior

| HTTP | Body | `RevokeOutcome` | CLI output |
|------|------|-----------------|------------|
| 200 | `{"revoked": true}` | `REVOKED` | "Session revoked on server. Local credentials deleted." |
| 5xx | any | `SERVER_FAILURE` | "Server revocation not confirmed (server error). Local credentials deleted." |
| 400 | `{"error": "invalid_request"}` | `SERVER_FAILURE` | "Server revocation not confirmed (server error). Local credentials deleted." |
| 429 | `{"error": "throttled"}` | `SERVER_FAILURE` | "Server revocation not confirmed (server error). Local credentials deleted." |
| network error | — | `NETWORK_ERROR` | "Server revocation not confirmed (network error). Local credentials deleted." |
| no refresh token | — | `NO_REFRESH_TOKEN` | "Server revocation could not be attempted (no refresh token). Local credentials deleted." |

## Invariants

- Local `tm.clear_session()` runs after the revoke call in ALL outcome paths.
- Exit code is 0 in all outcomes where local cleanup succeeded.
- `REVOKED` is the only outcome where the CLI reports server confirmation.
- A genuine server error (5xx) must never be reported as `REVOKED`.
- The spent refresh token must not appear in any log, error, or diagnostic output.

## Timeout

10 seconds (matches existing auth HTTP timeout pattern).
