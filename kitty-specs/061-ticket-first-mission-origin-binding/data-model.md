# Data Model: Ticket-First Mission Origin Binding

**Feature**: 061-ticket-first-mission-origin-binding
**Date**: 2026-04-01

## Entities

### OriginCandidate

A candidate external issue returned by search. Immutable value object.

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `external_issue_id` | `str` | Provider-native ID (e.g., Linear issue UUID, Jira issue ID) | Non-empty |
| `external_issue_key` | `str` | Human-readable key (e.g., `"WEB-123"`) | Non-empty |
| `title` | `str` | Issue title / summary | Non-empty |
| `status` | `str` | Current issue status in the provider | Non-empty |
| `url` | `str` | Deep link to the issue in the provider UI | Non-empty, valid URL |
| `match_type` | `str` | `"exact"` or `"text"` | Must be one of the two values |

**Implementation**: `@dataclass(frozen=True, slots=True)` in `tracker/origin.py`

### SearchOriginResult

Structured result from `search_origin_candidates()`.

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `candidates` | `list[OriginCandidate]` | Matching issues, ordered by relevance | May be empty |
| `provider` | `str` | Resolved provider name | `"jira"` or `"linear"` |
| `resource_type` | `str` | Resource type (e.g., `"linear_team"`, `"jira_project"`) | Non-empty |
| `resource_id` | `str` | Resource identifier used for scoping | Non-empty |
| `query_used` | `str` | The query that was actually executed | Non-empty |

**Implementation**: `@dataclass(frozen=True, slots=True)` in `tracker/origin.py`

### MissionFromTicketResult

Result of `start_mission_from_ticket()`.

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `feature_dir` | `Path` | Path to the created feature directory | Must exist |
| `feature_slug` | `str` | Assigned feature slug (e.g., `"061-web-123"`) | Non-empty, matches slug pattern |
| `origin_ticket` | `dict[str, str]` | The persisted `origin_ticket` metadata block | All required keys present |
| `event_emitted` | `bool` | Whether `MissionOriginBound` event was emitted | N/A |

**Implementation**: `@dataclass(slots=True)` in `tracker/origin.py` (not frozen — `feature_dir` is a Path)

## Metadata Extensions

### origin_ticket block in meta.json

Additive metadata block. Written via `set_origin_ticket()` → `write_meta()`.

```json
{
  "origin_ticket": {
    "provider": "linear",
    "resource_type": "linear_team",
    "resource_id": "team-uuid",
    "external_issue_id": "issue-uuid",
    "external_issue_key": "WEB-123",
    "external_issue_url": "https://linear.app/acme/issue/WEB-123/add-clerk-auth",
    "title": "Add Clerk auth"
  }
}
```

**Required keys**: `provider`, `resource_type`, `resource_id`, `external_issue_id`, `external_issue_key`, `external_issue_url`, `title`

All seven fields are required. `resource_type` and `resource_id` are routing context needed for offline intelligibility and possible future rebind/replay. They are always available from `SearchOriginResult` at bind time.

### FeatureMetaOptional TypedDict extension

```python
class FeatureMetaOptional(TypedDict, total=False):
    # ... existing fields ...
    origin_ticket: dict[str, Any]
```

## Event Model

### MissionOriginBound

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `feature_slug` | `str` | Yes | Matches `^\d{3}-[a-z0-9-]+$` |
| `provider` | `str` | Yes | `"jira"` or `"linear"` |
| `external_issue_id` | `str` | Yes | Non-empty |
| `external_issue_key` | `str` | Yes | Non-empty |
| `external_issue_url` | `str` | Yes | Non-empty |
| `title` | `str` | Yes | Non-empty |

**Aggregate**: `Feature` (aggregate_id = feature_slug)
**Role**: Observational telemetry only. Does NOT create the SaaS-side `MissionOriginLink` (that is done by the bind API call).

## Relationships

```
TrackerProjectConfig (config.yaml)
  └──provides──▶ provider + project_slug
                    │
                    ▼
        SaaSTrackerClient.search_issues()
                    │
                    ▼
            SearchOriginResult
              └── candidates: [OriginCandidate, ...]
                                    │
                            (developer confirms one)
                                    │
                                    ▼
                        bind_mission_origin()
                          ├── meta.json ← origin_ticket block
                          ├── SaaS ← MissionOriginLink (authoritative write)
                          └── Event ← MissionOriginBound (telemetry)
```

## State Transitions

The origin_ticket binding is a one-time write-once operation per mission (in v1):

```
(no origin) ──bind──▶ (origin bound)
                           │
                    (same-origin re-bind = no-op)
                    (different-origin re-bind = hard error)
```

No state machine beyond this. The origin_ticket block is immutable after binding (unless a future version adds unbind support).
