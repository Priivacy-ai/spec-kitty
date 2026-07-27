# Contract: Bind Confirmation

**Endpoint**: `POST /api/v1/tracker/bind-confirm/`
**Owner**: spec-kitty-saas
**Consumer**: spec-kitty CLI (`SaaSTrackerClient.bind_confirm()`)

## Request

```
POST /api/v1/tracker/bind-confirm/
Headers:
  Authorization: Bearer <access_token>
  X-Team-Slug: <team_slug>
  Content-Type: application/json
  Idempotency-Key: <uuid>
Body:
{
  "provider": "linear",
  "candidate_token": "cand_01HXYZ...",
  "project_identity": {
    "uuid": "550e8400-e29b-41d4-a716-446655440000",
    "slug": "my-project",
    "node_id": "a1b2c3d4e5f6",
    "repo_slug": null
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `provider` | string | Yes | Normalized provider name |
| `candidate_token` | string | Yes | Pre-bind token from resolution or inventory |
| `project_identity.uuid` | string (UUID) | Yes | From ProjectIdentity |
| `project_identity.slug` | string | Yes | From ProjectIdentity |
| `project_identity.node_id` | string | Yes | From ProjectIdentity |
| `project_identity.repo_slug` | string | No | User override from ProjectIdentity |
| `Idempotency-Key` | header (UUID) | Yes | Prevents duplicate bindings on retry |

## Response (200)

```json
{
  "binding_ref": "srm_01HXYZ...",
  "display_label": "My Project (LINEAR-123)",
  "provider": "linear",
  "provider_context": {
    "team_name": "Engineering",
    "workspace_name": "Acme Corp"
  },
  "bound_at": "2026-04-04T08:32:00Z"
}
```

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `binding_ref` | string | No | Stable post-bind reference. Primary routing key. |
| `display_label` | string | No | Human-readable label for display/caching |
| `provider` | string | No | Normalized provider name |
| `provider_context` | object | No | Provider-specific display metadata |
| `bound_at` | string (ISO) | No | Timestamp of binding |

## Error Responses

| Status | Error Code | Meaning |
|--------|-----------|---------|
| 400 | `invalid_candidate_token` | Token expired, invalid, or already consumed |
| 401 | `unauthorized` | Token expired/invalid (triggers refresh) |
| 409 | `already_bound` | Resource already bound to a different project |
| 429 | `rate_limited` | Rate limited (retry with backoff) |

**Token expiry**: If `invalid_candidate_token` is returned, the CLI should retry discovery once (re-call bind-resolve to get a fresh token) and re-attempt bind-confirm. If retry also fails, surface a clear error.

## Client Method

```python
def bind_confirm(
    self,
    provider: str,
    candidate_token: str,
    project_identity: dict[str, Any],
    *,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    """POST /api/v1/tracker/bind-confirm/"""
```

## Contract Tests

- Verify POST method + path `/api/v1/tracker/bind-confirm/`
- Verify request body includes `provider`, `candidate_token`, `project_identity`
- Verify `Idempotency-Key` header is sent
- Verify idempotency key is auto-generated (UUID4) if not provided
- Verify response parsed with `binding_ref`, `display_label`, `provider_context`
- Verify 400 `invalid_candidate_token` raises appropriate error
- Verify 409 `already_bound` raises appropriate error
