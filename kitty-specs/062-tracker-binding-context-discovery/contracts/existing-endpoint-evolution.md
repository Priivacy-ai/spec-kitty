# Contract: Existing Endpoint Evolution

**Affected Endpoints**: `status`, `mappings`, `pull`, `push`, `run`
**Owner**: spec-kitty-saas (coordinated change)
**Consumer**: spec-kitty CLI (`SaaSTrackerClient` existing methods)

## Summary

All 5 existing tracker endpoints currently route by `project_slug`. After 062, they must also accept `binding_ref` as an alternative routing key. The SaaS host accepts either; the CLI sends whichever is available (binding_ref-first).

## Wire Change

### GET endpoints (status, mappings)

**Current**:
```
GET /api/v1/tracker/status/?provider=linear&project_slug=my-project
```

**Updated** (either key accepted):
```
GET /api/v1/tracker/status/?provider=linear&binding_ref=srm_01HXYZ
GET /api/v1/tracker/status/?provider=linear&project_slug=my-project
```

### POST endpoints (pull, push, run)

**Current**:
```json
{"provider": "linear", "project_slug": "my-project", ...}
```

**Updated** (either key accepted):
```json
{"provider": "linear", "binding_ref": "srm_01HXYZ", ...}
{"provider": "linear", "project_slug": "my-project", ...}
```

## Client Method Signature Changes

All methods change `project_slug` from required positional to optional, add keyword-only `binding_ref`:

```python
# Before:
def status(self, provider: str, project_slug: str) -> dict[str, Any]:

# After:
def status(
    self,
    provider: str,
    project_slug: str | None = None,
    *,
    binding_ref: str | None = None,
) -> dict[str, Any]:
```

At least one of `project_slug` or `binding_ref` must be provided. If both are provided, `binding_ref` takes precedence.

## Stale Binding Error Response

When the host receives a `binding_ref` that maps to a deleted, disabled, or mismatched ServiceResourceMapping, it returns a PRI-12 error envelope with a specific `error_code`:

```json
{
  "error_code": "binding_not_found",
  "message": "The binding reference srm_01HXYZ is no longer valid.",
  "user_action_required": true
}
```

| Error code | Meaning |
|-----------|---------|
| `binding_not_found` | ServiceResourceMapping deleted |
| `mapping_disabled` | Mapping exists but disabled |
| `project_mismatch` | binding_ref doesn't match the authenticated project context |

The enriched `SaaSTrackerClientError` preserves these codes for the service layer to inspect.

## Opportunistic Upgrade Response Enrichment

When the host routes a request by `project_slug` (legacy path) and can resolve the corresponding `binding_ref`, it includes `binding_ref` in the response alongside the normal payload:

```json
{
  "provider": "linear",
  "connected": true,
  "binding_ref": "srm_01HXYZ...",
  "display_label": "My Project (LINEAR-123)",
  ...existing fields...
}
```

This is optional — the host returns these fields when available. The CLI's `_maybe_upgrade_binding_ref()` checks for their presence.

## Contract Tests

For each of the 5 existing endpoints:
- Verify `binding_ref` query param / body field is sent when provided
- Verify `project_slug` query param / body field is sent when binding_ref is absent
- Verify stale-binding error codes are preserved in `SaaSTrackerClientError`
- Verify normal response with `binding_ref` enrichment is parsed correctly
