# Data Model: Tracker Publish Resource Routing

**Feature**: 048-tracker-publish-resource-routing
**Date**: 2026-03-10

## Entities

### Tracker Snapshot Publish Payload (Extended)

The JSON payload sent by `TrackerService.sync_publish()` to `POST /api/v1/connectors/trackers/snapshots/`.

| Field | Type | Source | New? | Description |
|-------|------|--------|------|-------------|
| `provider` | `string` | `TrackerProjectConfig.provider` | No | Normalized provider name (e.g., `"jira"`, `"linear"`) |
| `workspace` | `string` | `TrackerProjectConfig.workspace` | No | Provider workspace/site identifier |
| `external_resource_type` | `string \| null` | `RESOURCE_ROUTING_MAP[provider][0]` | **Yes** | Canonical wire value identifying the resource kind (e.g., `"jira_project"`, `"linear_team"`) |
| `external_resource_id` | `string \| null` | `credentials[credential_key]` | **Yes** | Provider-specific resource identifier (e.g., Jira project key `"ACME"`, Linear team ID `"abc-123"`) |
| `doctrine_mode` | `string` | `TrackerProjectConfig.doctrine_mode` | No | Ownership policy mode |
| `doctrine_field_owners` | `object` | `TrackerProjectConfig.doctrine_field_owners` | No | Per-field ownership map |
| `project_uuid` | `string \| null` | `.kittify/config.yaml` | No | Spec-Kitty project UUID |
| `project_slug` | `string \| null` | `.kittify/config.yaml` | No | Spec-Kitty project slug |
| `issues` | `array` | `TrackerSqliteStore.list_issues()` | No | Issue snapshot objects |
| `mappings` | `array` | `TrackerSqliteStore.list_mappings()` | No | WP-to-issue mapping records |
| `checkpoint` | `object` | `TrackerSqliteStore.get_checkpoint()` | No | Sync checkpoint state |

### Resource Routing Map (Module Constant)

Static lookup table, not persisted. Lives in `src/specify_cli/tracker/service.py`.

| Provider | `external_resource_type` | Credential Key | Example `external_resource_id` |
|----------|--------------------------|----------------|-------------------------------|
| `jira` | `"jira_project"` | `project_key` | `"ACME"` |
| `linear` | `"linear_team"` | `team_id` | `"abc-123-def"` |
| *(other)* | `null` | — | `null` |

### Canonical Wire Values

These are **stable contract strings** — not display labels. Changing them requires a versioned migration.

| Wire Value | Provider | Resource Kind | Maps to ADR Layer |
|------------|----------|---------------|-------------------|
| `"jira_project"` | Jira | Jira project (identified by project key) | Layer 3: ServiceResourceMapping |
| `"linear_team"` | Linear | Linear team (identified by team ID) | Layer 3: ServiceResourceMapping |

## Relationships

```
TrackerProjectConfig
  ├── provider ─────────────────┐
  └── workspace                 │
                                ▼
TrackerCredentialStore     RESOURCE_ROUTING_MAP
  └── get_provider(provider)    └── (resource_type, credential_key)
        │                              │
        ▼                              ▼
   credentials dict         _resolve_resource_routing()
        │                         │         │
        ▼                         ▼         ▼
   credential_key value     external_resource_type  external_resource_id
```

## State Transitions

None — the new fields are stateless, derived at publish time from existing config and credentials.

## Validation Rules

| Rule | Description |
|------|-------------|
| Provider lookup | If `provider` not in `RESOURCE_ROUTING_MAP`, both fields are `null` |
| Credential key lookup | If `credentials[key]` is missing, `None`, or empty/whitespace-only, both fields are `null` |
| Atomic null | Both fields are always `null` together or both populated — never one null and one populated |
| No mutation | The derivation function does not modify config, credentials, or any external state |
