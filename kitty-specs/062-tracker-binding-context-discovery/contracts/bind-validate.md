# Contract: Binding Validation

**Endpoint**: `POST /api/v1/tracker/bind-validate/`
**Owner**: spec-kitty-saas
**Consumer**: spec-kitty CLI (`SaaSTrackerClient.bind_validate()`)

## Request

```
POST /api/v1/tracker/bind-validate/
Headers:
  Authorization: Bearer <access_token>
  X-Team-Slug: <team_slug>
  Content-Type: application/json
Body:
{
  "provider": "linear",
  "binding_ref": "srm_01HXYZ...",
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
| `binding_ref` | string | Yes | The binding reference to validate |
| `project_identity.uuid` | string (UUID) | Yes | From ProjectIdentity |
| `project_identity.slug` | string | Yes | From ProjectIdentity |
| `project_identity.node_id` | string | Yes | From ProjectIdentity |
| `project_identity.repo_slug` | string | No | User override from ProjectIdentity |

## Response (200 — Valid)

```json
{
  "valid": true,
  "binding_ref": "srm_01HXYZ...",
  "display_label": "My Project (LINEAR-123)",
  "provider": "linear",
  "provider_context": {
    "team_name": "Engineering",
    "workspace_name": "Acme Corp"
  }
}
```

## Response (200 — Invalid)

```json
{
  "valid": false,
  "binding_ref": "srm_01HXYZ...",
  "reason": "mapping_deleted",
  "guidance": "The bound tracker resource no longer exists. Run `tracker bind --provider linear` to rebind."
}
```

| Field | Type | Nullable | Condition | Description |
|-------|------|----------|-----------|-------------|
| `valid` | boolean | No | Always | Whether the binding_ref is still valid |
| `binding_ref` | string | No | Always | Echo of the validated ref |
| `display_label` | string | Yes | valid=true | Human-readable label |
| `provider` | string | Yes | valid=true | Normalized provider name |
| `provider_context` | object | Yes | valid=true | Provider-specific display metadata |
| `reason` | string | Yes | valid=false | Machine-readable: `mapping_deleted`, `mapping_disabled`, `project_mismatch` |
| `guidance` | string | Yes | valid=false | Human-readable guidance for CLI display |

## Error Responses

| Status | Error Code | Meaning |
|--------|-----------|---------|
| 401 | `unauthorized` | Token expired/invalid (triggers refresh) |
| 429 | `rate_limited` | Rate limited (retry with backoff) |

Note: Invalid binding is **not** a 4xx error — it returns 200 with `valid: false`. The endpoint validates the ref's existence, not the request format.

## Usage Contexts

1. **`tracker bind --bind-ref <ref>`**: Validates the CI-supplied ref before persisting to local config.
2. **Error sharpening**: When a real endpoint returns an ambiguous failure that might be a stale binding, the service layer may call bind-validate once to produce a clearer error message.

This endpoint is **not** called proactively on normal commands (`status`, `push`, `pull`, `run`). Stale binding detection for those paths is reactive from endpoint error responses.

## Client Method

```python
def bind_validate(
    self,
    provider: str,
    binding_ref: str,
    project_identity: dict[str, Any],
) -> dict[str, Any]:
    """POST /api/v1/tracker/bind-validate/"""
```

## Contract Tests

- Verify POST method + path `/api/v1/tracker/bind-validate/`
- Verify request body includes `provider`, `binding_ref`, `project_identity`
- Verify valid response parsed with display metadata
- Verify invalid response parsed with reason and guidance
- Verify both valid and invalid return 200 (not 4xx)
- Verify standard auth/rate-limit error handling
