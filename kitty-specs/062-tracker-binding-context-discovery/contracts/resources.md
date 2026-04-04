# Contract: Resource Inventory

**Endpoint**: `GET /api/v1/tracker/resources/`
**Owner**: spec-kitty-saas
**Consumer**: spec-kitty CLI (`SaaSTrackerClient.resources()`)

## Request

```
GET /api/v1/tracker/resources/?provider=linear
Headers:
  Authorization: Bearer <access_token>
  X-Team-Slug: <team_slug>
```

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `provider` | query string | Yes | Normalized provider name |

## Response (200)

```json
{
  "resources": [
    {
      "candidate_token": "cand_01HXYZ...",
      "display_label": "My Project (LINEAR-123)",
      "provider": "linear",
      "provider_context": {
        "team_name": "Engineering",
        "workspace_name": "Acme Corp"
      },
      "binding_ref": "srm_01HXYZ...",
      "bound_project_slug": "my-project",
      "bound_at": "2026-03-01T10:00:00Z"
    }
  ],
  "installation_id": "inst_01HXYZ...",
  "provider": "linear"
}
```

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `resources` | array | No | List of bindable resources |
| `resources[].candidate_token` | string | No | Pre-bind opaque token for bind-confirm |
| `resources[].display_label` | string | No | Human-readable label for CLI display |
| `resources[].provider` | string | No | Normalized provider name |
| `resources[].provider_context` | object | No | Provider-specific display metadata |
| `resources[].binding_ref` | string | Yes | Non-null if already bound |
| `resources[].bound_project_slug` | string | Yes | Non-null if already bound |
| `resources[].bound_at` | string (ISO) | Yes | Non-null if already bound |
| `installation_id` | string | No | Installation identifier |
| `provider` | string | No | Echo of requested provider |

## Error Responses

| Status | Error Code | Meaning |
|--------|-----------|---------|
| 401 | `unauthorized` | Token expired/invalid (triggers refresh) |
| 403 | `no_installation` | No installation for this provider |
| 429 | `rate_limited` | Rate limited (retry with backoff) |

## Client Method

```python
def resources(self, provider: str) -> dict[str, Any]:
    """GET /api/v1/tracker/resources/?provider=<provider>"""
```

## Contract Tests

- Verify GET method + path `/api/v1/tracker/resources/`
- Verify `provider` query parameter is sent
- Verify response parsed into resources list
- Verify 403 `no_installation` raises appropriate error
- Verify empty resources list (valid response, not an error)
