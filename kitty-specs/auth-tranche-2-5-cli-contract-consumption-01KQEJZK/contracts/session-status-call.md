# CLI Contract: Session Status Call

**Endpoint**: `GET /api/v1/session-status`
**Canonical source**: `spec-kitty-saas/kitty-specs/saas-cli-token-family-and-revocation-01KQATJN/contracts/session-status.yaml`

## Request

```
GET /api/v1/session-status
Authorization: Bearer <unexpired_access_token>
```

- Requires a valid, unexpired access token.
- Refresh tokens must not be presented on this endpoint.
- The CLI must refresh the access token first if it is expired or near expiry.

## Responses and CLI Behavior

| HTTP | Meaning | `ServerSessionStatus` | `auth doctor --server` output |
|------|---------|----------------------|-------------------------------|
| 200 | Session active | `active=True, session_id=<id>` | "Server session: active (session: <id>)" |
| 401 | Expired, revoked, or invalid | `active=False, error="re-authenticate"` | "Server session: invalid. Run `spec-kitty auth login` to re-authenticate." |
| network error | Unreachable | `active=False, error=<brief message>` | "Server session check failed: <brief message>" |

## Safe-to-Display Fields (200 response)

- `session_id`: safe to display (not a secret)
- `status`: always `"active"` on 200
- `current_generation`: available but not displayed in Tranche 2.5

## Fields Never Displayed

Per contract (`additionalProperties: false`) and spec (NFR-001, C-005):
- `token_family_id` — absent from response
- `is_revoked` — absent from response
- `revocation_reason` — absent from response
- Raw tokens — never passed through to output

## Pre-call Sequence

```
auth doctor --server
  │
  ├── get_access_token()  (auto-refresh if expired)
  │   ├── refresh succeeds → valid access token obtained
  │   └── refresh fails → ServerSessionStatus(active=False, error="could not refresh")
  │
  └── GET /api/v1/session-status with valid token
      ├── 200 → ServerSessionStatus(active=True, ...)
      └── 401 → ServerSessionStatus(active=False, error="re-authenticate")
```
