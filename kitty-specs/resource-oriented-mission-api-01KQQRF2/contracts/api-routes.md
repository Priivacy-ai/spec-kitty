# API Route Contracts

**Mission**: `resource-oriented-mission-api-01KQQRF2`

## New Routes

### GET /api/missions

List all missions.

**Response**: `200 OK`, `application/json`

```json
[
  {
    "mission_id": "01KQQRF2ZKPQW1CT7H6BYTN5BG",
    "mission_slug": "resource-oriented-mission-api-01KQQRF2",
    "mission_number": null,
    "mid8": "01KQQRF2",
    "friendly_name": "Resource-Oriented Mission API and HATEOAS-LITE",
    "mission_type": "software-dev",
    "target_branch": "feature/650-dashboard-ui-ux-overhaul",
    "lane_counts": { "total": 6, "planned": 2, "claimed": 0, "in_progress": 1, "for_review": 0, "in_review": 0, "approved": 0, "done": 3, "blocked": 0, "canceled": 0 },
    "weighted_percentage": 50.0,
    "is_legacy": false,
    "_links": {
      "self": { "href": "/api/missions/01KQQRF2ZKPQW1CT7H6BYTN5BG" },
      "status": { "href": "/api/missions/01KQQRF2ZKPQW1CT7H6BYTN5BG/status" },
      "workpackages": { "href": "/api/missions/01KQQRF2ZKPQW1CT7H6BYTN5BG/workpackages" }
    }
  }
]
```

**Error cases**: None (empty array if no missions found).

---

### GET /api/missions/{id}

Fetch a single mission by `mission_id`, `mid8`, or `mission_slug`.

**Response**: `200 OK` — same shape as `MissionSummary` plus `created_at`.

**Error cases**:
- `404 Not Found`: `{"detail": "Mission not found: <id>"}`
- `409 Conflict`: `{"detail": "MISSION_AMBIGUOUS_SELECTOR", "candidates": ["slug-a", "slug-b"]}`

---

### GET /api/missions/{id}/status

Lane counts and progress for a single mission.

**Response**: `200 OK`

```json
{
  "mission_id": "01KQQRF2ZKPQW1CT7H6BYTN5BG",
  "lane_counts": { "total": 6, "planned": 2, "claimed": 0, "in_progress": 1, "for_review": 0, "in_review": 0, "approved": 0, "done": 3, "blocked": 0, "canceled": 0 },
  "weighted_percentage": 50.0,
  "done_count": 3,
  "total_count": 6,
  "current_phase": 2,
  "_links": {
    "self": { "href": "/api/missions/01KQQRF2ZKPQW1CT7H6BYTN5BG/status" },
    "mission": { "href": "/api/missions/01KQQRF2ZKPQW1CT7H6BYTN5BG" }
  }
}
```

**Error cases**: `404`, `409` — same as `/api/missions/{id}`.

---

### GET /api/missions/{id}/workpackages

List all WPs for a mission.

**Response**: `200 OK`

```json
[
  {
    "wp_id": "WP01",
    "title": "Registry extension + Pydantic resource models",
    "assignment": {
      "wp_id": "WP01",
      "lane": "in_progress",
      "assignee": "claude:sonnet-4-6",
      "agent_profile": "python-pedro",
      "role": "implementer",
      "claimed_at": "2026-05-03T21:00:00+00:00",
      "last_event_id": "01KQQRF2...",
      "blocked_reason": null,
      "review_evidence": null
    },
    "_links": {
      "self": { "href": "/api/missions/01KQQRF2ZKPQW1CT7H6BYTN5BG/workpackages/WP01" },
      "mission": { "href": "/api/missions/01KQQRF2ZKPQW1CT7H6BYTN5BG" }
    }
  }
]
```

**Error cases**: `404`, `409` — mission not found / ambiguous.

---

### GET /api/missions/{id}/workpackages/{wp_id}

Fetch a single WP with full detail.

**Response**: `200 OK` — `WorkPackageSummary` fields plus `subtasks_done`, `subtasks_total`, `dependencies`, `requirement_refs`, `prompt_ref`.

```json
{
  "wp_id": "WP01",
  "title": "Registry extension + Pydantic resource models",
  "assignment": { "...": "..." },
  "subtasks_done": 2,
  "subtasks_total": 5,
  "dependencies": [],
  "requirement_refs": ["FR-001", "FR-006", "FR-007", "FR-008"],
  "prompt_ref": "kitty-specs/resource-oriented-mission-api-01KQQRF2/tasks/WP01.md",
  "_links": {
    "self": { "href": "/api/missions/01KQQRF2ZKPQW1CT7H6BYTN5BG/workpackages/WP01" },
    "mission": { "href": "/api/missions/01KQQRF2ZKPQW1CT7H6BYTN5BG" },
    "workpackages": { "href": "/api/missions/01KQQRF2ZKPQW1CT7H6BYTN5BG/workpackages" }
  }
}
```

**Error cases**: `404` for unknown mission or WP. `409` for ambiguous mission selector.

---

## Updated Routes (Deprecation Aliases)

### GET /api/features (deprecated alias for GET /api/missions)

Behaviour unchanged. Additional response headers:
- `Deprecation: true`
- `Link: </api/missions>; rel="successor-version"`

### GET /api/kanban/{feature_id} (deprecated alias for GET /api/missions/{id}/status)

Behaviour unchanged. Additional response headers:
- `Deprecation: true`
- `Link: </api/missions/{feature_id}/status>; rel="successor-version"`

---

## OpenAPI Tag Groups

Every router declares `tags=[...]` so Swagger UI groups routes:

| Tag | Domain | Routes |
|-----|--------|--------|
| `missions` | Mission + WP resource endpoints | `/api/missions/**` |
| `kanban` | Deprecated aliases | `/api/features`, `/api/kanban/{id}` |
| `research` | Research artifacts | `/api/research/**` |
| `contracts` | Contract artifacts | `/api/contracts/**` |
| `checklists` | Checklist artifacts | `/api/checklists/**` |
| `charter` | Charter surfaces | `/api/charter`, `/api/charter-lint` |
| `dossier` | Dossier surfaces | `/api/dossier/**` |
| `glossary` | Glossary surfaces | `/api/glossary-*`, `/glossary` |
| `health` | Health + diagnostics | `/api/health`, `/api/diagnostics` |
| `sync` | Sync daemon | `/api/sync/trigger` |
| `lifecycle` | Server lifecycle | `/api/shutdown` |
