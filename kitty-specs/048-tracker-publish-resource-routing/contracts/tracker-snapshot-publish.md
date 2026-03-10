# Contract: Tracker Snapshot Publish Payload

**Feature**: 048-tracker-publish-resource-routing
**Version**: 2.1.0
**Date**: 2026-03-10
**Endpoint**: `POST {server_url}/api/v1/connectors/trackers/snapshots/`

## Payload Schema

| Field | Type | Required | New? | Description |
|-------|------|----------|------|-------------|
| `provider` | `string` | Yes | No | Normalized provider name (e.g., `"jira"`, `"linear"`) |
| `workspace` | `string` | Yes | No | Provider workspace/site identifier |
| `external_resource_type` | `string \| null` | Yes | **Yes** | Canonical wire value for resource kind. Stable contract string. |
| `external_resource_id` | `string \| null` | Yes | **Yes** | Provider-specific resource identifier |
| `doctrine_mode` | `string` | Yes | No | Ownership policy mode |
| `doctrine_field_owners` | `object` | Yes | No | Per-field ownership map |
| `project_uuid` | `string \| null` | No | No | Spec-Kitty project UUID |
| `project_slug` | `string \| null` | No | No | Spec-Kitty project slug |
| `issues` | `array` | Yes | No | Issue snapshot objects (see existing contract) |
| `mappings` | `array` | Yes | No | WP-to-issue mapping records |
| `checkpoint` | `object` | Yes | No | Sync checkpoint state (`cursor`, `updated_since`) |

## New Fields Detail

### `external_resource_type`

Canonical wire value identifying the kind of external resource. These are **stable contract strings** — not display labels.

| Value | Provider | Resource Kind |
|-------|----------|---------------|
| `"jira_project"` | Jira | A Jira project, identified by project key |
| `"linear_team"` | Linear | A Linear team, identified by team ID |
| `null` | Any unsupported or missing | Routing unavailable |

### `external_resource_id`

The provider-specific identifier for the resource.

| Provider | Credential Source | Example |
|----------|-------------------|---------|
| Jira | `credentials["project_key"]` | `"ACME"` |
| Linear | `credentials["team_id"]` | `"abc-123-def-456"` |
| Other | — | `null` |

### Null Semantics

Both fields are always atomically `null` or atomically populated:
- If provider is not in the routing map → both `null`
- If credential key is missing or empty → both `null`
- Never one `null` and one populated

A `null` value means "routing unavailable" — the SaaS should fall back to `(provider, workspace)` resolution.

## Backward Compatibility

| Scenario | Behavior |
|----------|----------|
| Old CLI (pre-048) sends payload without new fields | SaaS accepts; treats fields as absent |
| New CLI (048+) sends payload with new fields | SaaS uses fields for `ServiceResourceMapping` resolution |
| SaaS pre-048 receives payload with new fields | Unknown fields ignored (standard JSON forward compatibility) |

## Example Payloads

### Jira (routing available)

```json
{
  "provider": "jira",
  "workspace": "acme.atlassian.net",
  "external_resource_type": "jira_project",
  "external_resource_id": "ACME",
  "doctrine_mode": "external_authoritative",
  "doctrine_field_owners": {},
  "project_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "project_slug": "spec-kitty",
  "issues": [],
  "mappings": [],
  "checkpoint": {"cursor": null, "updated_since": null}
}
```

### Linear (routing available)

```json
{
  "provider": "linear",
  "workspace": "acme-engineering",
  "external_resource_type": "linear_team",
  "external_resource_id": "abc-123-def-456",
  "doctrine_mode": "split",
  "doctrine_field_owners": {"status": "external", "title": "local"},
  "project_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "project_slug": "spec-kitty",
  "issues": [],
  "mappings": [],
  "checkpoint": {"cursor": "cursor-value", "updated_since": "2026-03-10T00:00:00+00:00"}
}
```

### Unsupported provider (routing unavailable)

```json
{
  "provider": "beads",
  "workspace": "my-workspace",
  "external_resource_type": null,
  "external_resource_id": null,
  "doctrine_mode": "external_authoritative",
  "doctrine_field_owners": {},
  "project_uuid": null,
  "project_slug": null,
  "issues": [],
  "mappings": [],
  "checkpoint": {"cursor": null, "updated_since": null}
}
```

## SaaS Routing Resolution

The SaaS should resolve the resource mapping using this lookup order:

1. If `external_resource_type` and `external_resource_id` are both non-null:
   - Look up `ServiceResourceMapping` by `(provider, workspace, external_resource_type, external_resource_id)`
   - `workspace` is required in the lookup because the same resource identifier (e.g., Jira project key `"ACME"`) can exist on different provider sites
   - If found, use the mapped project/feed
2. Fall back to `(provider, workspace)` resolution (existing behavior)
3. If no match, queue for manual mapping

**Why `workspace` is part of the routing key**: A team may connect multiple Jira sites (e.g., `acme.atlassian.net` and `acme-staging.atlassian.net`). Both sites can have a project with key `"ACME"`. Without `workspace` in the lookup, the SaaS would conflate the two. The 4-tuple `(provider, workspace, external_resource_type, external_resource_id)` is the unique routing key.

## Relation to Git Event Envelope

This contract is **independent** of the Git event envelope. The tracker snapshot publish payload is sent to a different endpoint (`/api/v1/connectors/trackers/snapshots/`) than the batch event pipeline (`/api/v1/events/batch/`). The 15-field event envelope is unchanged by this feature.
