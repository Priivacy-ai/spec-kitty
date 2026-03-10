# Quickstart: Tracker Publish Resource Routing

**Feature**: 048-tracker-publish-resource-routing

## What Changed

The CLI tracker snapshot publish payload now includes two new routing fields:

- `external_resource_type` — canonical wire value identifying the resource kind
- `external_resource_id` — provider-specific resource identifier

These fields let the SaaS resolve `ServiceResourceMapping` records without inventing CLI-side follow-up fields.

## Wire Values

| Provider | `external_resource_type` | `external_resource_id` source |
|----------|--------------------------|-------------------------------|
| Jira | `"jira_project"` | `credentials["project_key"]` |
| Linear | `"linear_team"` | `credentials["team_id"]` |
| Other | `null` | `null` |

## Example Payload (Jira)

```json
{
  "provider": "jira",
  "workspace": "acme.atlassian.net",
  "external_resource_type": "jira_project",
  "external_resource_id": "ACME",
  "doctrine_mode": "external_authoritative",
  "project_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "issues": [...],
  "mappings": [...],
  "checkpoint": {...}
}
```

## Null Handling

When credentials lack the required key (or it is empty), both routing fields are `null`:

```json
{
  "provider": "jira",
  "workspace": "acme.atlassian.net",
  "external_resource_type": null,
  "external_resource_id": null,
  ...
}
```

The publish still succeeds — the SaaS falls back to `(provider, workspace)` resolution.

## What Did NOT Change

- The 15-field Git event envelope (`git_branch`, `head_commit_sha`, `repo_slug`, etc.)
- The batch event API contract (`/api/v1/events/batch/`)
- Tracker config in `.kittify/config.yaml`
- Credential storage format in `~/.spec-kitty/credentials`
