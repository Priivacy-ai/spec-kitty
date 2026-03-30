# Data Model: SaaS-Mediated CLI Tracker Reflow

## CLI-Side Entities

### TrackerProjectConfig (Modified)

Stored in `.kittify/config.yaml` under `tracker:` section.

| Field | Type | SaaS-backed | Local | Notes |
|-------|------|-------------|-------|-------|
| `provider` | `str \| None` | Required | Required | Provider name (linear, jira, github, gitlab, beads, fp) |
| `project_slug` | `str \| None` | Required | Unused | SaaS routing key in API request bodies |
| `workspace` | `str \| None` | Unused | Required | Local workspace identifier for beads/fp |
| `doctrine_mode` | `str` | Default | Default | Ownership doctrine (default: external_authoritative) |
| `doctrine_field_owners` | `dict[str, str]` | Default | Default | Per-field ownership overrides |

**Serialized form** (`.kittify/config.yaml`):
```yaml
tracker:
  provider: linear
  project_slug: my-project
  doctrine:
    mode: external_authoritative
    field_owners: {}
```

### Provider Classification

| Provider | Category | Binding model | Execution path |
|----------|----------|---------------|----------------|
| `linear` | SaaS-backed | provider + project_slug | SaaSTrackerService → SaaS API |
| `jira` | SaaS-backed | provider + project_slug | SaaSTrackerService → SaaS API |
| `github` | SaaS-backed | provider + project_slug | SaaSTrackerService → SaaS API |
| `gitlab` | SaaS-backed | provider + project_slug | SaaSTrackerService → SaaS API |
| `beads` | Local | provider + workspace | LocalTrackerService → direct connector |
| `fp` | Local | provider + workspace | LocalTrackerService → direct connector |
| `azure_devops` | Removed | N/A | Hard fail with guidance |

## SaaS Contract Entities (Read-Only from CLI)

These entities are defined by the frozen PRI-12 contract. The CLI receives them in API responses but never constructs or mutates them.

### NormalizedIssue

Received in `PullResultEnvelope.items[]`.

| Field | Type | Notes |
|-------|------|-------|
| `ref` | `ExternalRef` | `{system, id, workspace, key?, url?}` -- `workspace` is required per PRI-12 |
| `title` | `str` | |
| `body` | `str \| null` | |
| `status` | `enum` | `todo, in_progress, in_review, blocked, done, canceled` |
| `issue_type` | `enum` | `epic, story, task, bug, chore, subtask` |
| `priority` | `int (0-4)` | 0 = unset, 1 = urgent, 4 = low |
| `assignees` | `str[]` | |
| `labels` | `str[]` | |
| `parent_ref` | `ExternalRef \| null` | |
| `links` | `IssueLink[]` | |
| `custom_fields` | `object` | Freeform |
| `created_at` | `datetime` | ISO 8601 |
| `updated_at` | `datetime` | ISO 8601 |
| `provider_metadata` | `object` | Freeform |

### PullResultEnvelope

| Field | Type | Notes |
|-------|------|-------|
| `status` | `enum` | `ok, partial, error` |
| `summary` | `ResultSummary` | `{total, succeeded, failed, skipped}` |
| `items` | `NormalizedIssue[]` | |
| `item_errors` | `ItemError[] \| null` | |
| `identity_path` | `IdentityPath` | |
| `has_more` | `bool` | Pagination |
| `next_cursor` | `str \| null` | Opaque, SaaS-issued |
| `doctrine` | `object \| null` | |

### PushResultEnvelope

| Field | Type | Notes |
|-------|------|-------|
| `status` | `enum` | `ok, partial, error` |
| `summary` | `ResultSummary` | |
| `items` | `PushResultItem[]` | Each: `{ref, action, outcome, remote_ref, version, message}` |
| `item_errors` | `ItemError[] \| null` | |
| `identity_path` | `IdentityPath` | |
| `doctrine` | `object \| null` | |

### RunResultEnvelope

| Field | Type | Notes |
|-------|------|-------|
| `status` | `enum` | `ok, partial, error` |
| `summary` | `ResultSummary` | |
| `pull` | `PullPhaseResult` | Pull phase subset |
| `push` | `PushPhaseResult` | Push phase subset |
| `identity_path` | `IdentityPath` | |
| `doctrine` | `object \| null` | |

### OperationAccepted (HTTP 202)

| Field | Type | Notes |
|-------|------|-------|
| `operation_id` | `str (UUID)` | Used for polling |
| `status` | `str` | Always `pending` |

### OperationResult (Polling Response)

| Field | Type | Notes |
|-------|------|-------|
| `operation_id` | `str (UUID)` | |
| `status` | `enum` | `pending, running, completed, failed` |
| `result` | `PushResultEnvelope \| RunResultEnvelope \| null` | Present when `completed` |
| `error` | `ErrorEnvelope \| null` | Present when `failed` |

### ErrorEnvelope

| Field | Type | Notes |
|-------|------|-------|
| `code` | `str` | Error code within category (e.g., `missing_installation`) |
| `category` | `str` | Top-level category (e.g., `identity_resolution`). Separate field from `code` per PRI-12. |
| `http_status` | `int` | |
| `message` | `str` | Human-readable |
| `retryable` | `bool` | |
| `user_action_required` | `bool` | |
| `source` | `enum` | `saas, provider` |
| `retry_after_seconds` | `int \| null` | For 429 |
| `provider` | `str \| null` | |
| `details` | `object \| null` | |

### IdentityPath

| Field | Type | Notes |
|-------|------|-------|
| `type` | `enum` | `installation, user_link` |
| `installation_id` | `str (UUID)` | |
| `user_link_id` | `str (UUID) \| null` | Present for user_link type |
| `provider` | `str` | |
| `provider_account_id` | `str` | |

## State Transitions

### Operation Lifecycle (push/run async)

```
[CLI sends request]
    │
    ├─ 200 → completed (inline result)
    │
    └─ 202 → pending
               │
               ├─ poll → pending (continue polling)
               ├─ poll → running (continue polling)
               ├─ poll → completed (result envelope)
               └─ poll → failed (error envelope)
```

### Auth Token Lifecycle (on 401)

```
[Request fails with 401]
    │
    └─ refresh_tokens()
         │
         ├─ success → retry original request (once)
         │     │
         │     ├─ success → return result
         │     └─ 401 again → halt with re-login guidance
         │
         └─ failure → halt with re-login guidance
```
