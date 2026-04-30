# CLI Contract: Refresh 409 Benign Replay

**Endpoint**: `POST /oauth/token` (existing, `grant_type=refresh_token`)
**Canonical source**: `spec-kitty-saas/kitty-specs/saas-cli-token-family-and-revocation-01KQATJN/contracts/refresh.yaml`

## 409 Response Shape

```json
{
  "error": "refresh_replay_benign_retry",
  "error_description": "Refresh token was just rotated; reload current token and retry.",
  "error_uri": "<uri>",
  "retry_after": 0
}
```

Note: the field is `error`, not `error_code`. `retry_after` is 0–5 seconds (informational; CLI does not sleep for this duration in Tranche 2.5).

## CLI Handling (inside `_run_locked`)

```
TokenRefreshFlow.refresh(persisted) → raises RefreshReplayError
  │
  ├── re-read storage.read()
  │
  ├── repersisted is None
  │   └── return LOCK_TIMEOUT_ERROR  (session cleared concurrently)
  │
  ├── repersisted.refresh_token == persisted.refresh_token  (same spent token)
  │   └── return LOCK_TIMEOUT_ERROR  (no newer token; do not retry)
  │
  └── repersisted.refresh_token != persisted.refresh_token  (newer token present)
      │
      ├── refresh_flow.refresh(repersisted) → success
      │   └── storage.write(updated) → return REFRESHED
      │
      └── refresh_flow.refresh(repersisted) → any failure
          └── return LOCK_TIMEOUT_ERROR  (second attempt failed; stop)
```

## Invariants

- The spent `persisted.refresh_token` is never submitted to the server again after a 409.
- The retry uses `repersisted` (structurally different object with a different token).
- Maximum one retry per 409; no loop.
- `TokenManager` outcome set is unchanged — it sees only `REFRESHED` or `LOCK_TIMEOUT_ERROR`.

## Comparison to 401

| Status | `error` value | CLI action |
|--------|---------------|------------|
| 409 | `refresh_replay_benign_retry` | Reload persisted, retry if newer token |
| 401 | `invalid_grant` | `CURRENT_REJECTION_CLEARED` → re-authenticate |
| 401 | `session_invalid` | `CURRENT_REJECTION_CLEARED` → re-authenticate |

401 always means family revocation or genuine expiry. No retry.
