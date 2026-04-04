# Contract: Binding Resolution

**Endpoint**: `POST /api/v1/tracker/bind-resolve/`
**Owner**: spec-kitty-saas
**Consumer**: spec-kitty CLI (`SaaSTrackerClient.bind_resolve()`)

## Request

```
POST /api/v1/tracker/bind-resolve/
Headers:
  Authorization: Bearer <access_token>
  X-Team-Slug: <team_slug>
  Content-Type: application/json
Body:
{
  "provider": "linear",
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
| `project_identity.uuid` | string (UUID) | Yes | From ProjectIdentity |
| `project_identity.slug` | string | Yes | From ProjectIdentity |
| `project_identity.node_id` | string | Yes | From ProjectIdentity |
| `project_identity.repo_slug` | string | No | User override from ProjectIdentity |

## Response (200) — Exact Match

```json
{
  "match_type": "exact",
  "candidate_token": "cand_01HXYZ...",
  "binding_ref": "srm_01HXYZ...",
  "candidates": [],
  "display_label": "My Project (LINEAR-123)"
}
```

When `match_type` is `"exact"`:
- `candidate_token` is always present
- `binding_ref` is non-null if a ServiceResourceMapping already exists (CLI can skip bind-confirm)
- `binding_ref` is null if the match is confident but no mapping exists yet (CLI must call bind-confirm)

## Response (200) — Multiple Candidates

```json
{
  "match_type": "candidates",
  "candidate_token": null,
  "binding_ref": null,
  "candidates": [
    {
      "candidate_token": "cand_01HABC...",
      "display_label": "My Project (LINEAR-123)",
      "confidence": "high",
      "match_reason": "project_slug matches existing mapping",
      "sort_position": 0
    },
    {
      "candidate_token": "cand_01HDEF...",
      "display_label": "Backend API (LINEAR-456)",
      "confidence": "medium",
      "match_reason": "repo_slug partial match",
      "sort_position": 1
    }
  ],
  "display_label": null
}
```

**Ordering contract**: `candidates` is sorted by `sort_position` (ascending). The host assigns `sort_position` deterministically: confidence descending, then `display_label` ascending within the same confidence tier. Ordering is stable for a given installation state.

## Response (200) — No Match

```json
{
  "match_type": "none",
  "candidate_token": null,
  "binding_ref": null,
  "candidates": [],
  "display_label": null
}
```

## Response Fields

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `match_type` | string | No | `"exact"`, `"candidates"`, or `"none"` |
| `candidate_token` | string | Yes | For exact match: the pre-bind token |
| `binding_ref` | string | Yes | For exact match with existing mapping |
| `candidates` | array | No | Empty for exact/none; populated for candidates |
| `candidates[].candidate_token` | string | No | Pre-bind token for this candidate |
| `candidates[].display_label` | string | No | Human-readable label |
| `candidates[].confidence` | string | No | `"high"`, `"medium"`, or `"low"` |
| `candidates[].match_reason` | string | No | Why this candidate matched |
| `candidates[].sort_position` | integer | No | Zero-based stable ordinal |
| `display_label` | string | Yes | For exact match: the display label |

## Client Method

```python
def bind_resolve(
    self,
    provider: str,
    project_identity: dict[str, Any],
) -> dict[str, Any]:
    """POST /api/v1/tracker/bind-resolve/"""
```

## Contract Tests

- Verify POST method + path `/api/v1/tracker/bind-resolve/`
- Verify request body includes `provider` and `project_identity`
- Verify exact match response parsing (with and without binding_ref)
- Verify candidates response parsing with sort_position ordering
- Verify none response parsing
- Verify candidates are sorted by sort_position in response
