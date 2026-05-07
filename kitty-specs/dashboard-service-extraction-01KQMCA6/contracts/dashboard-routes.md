# Dashboard Route Contracts

*Phase 1 design output for mission `dashboard-service-extraction-01KQMCA6`*

**Constraint C-001**: BaseHTTPServer transport retained — no changes to HTTP surface.
**Constraint C-002**: TypedDict shapes are frozen — no shape or field name changes.
**Constraint C-003**: `dashboard.js` behavior unchanged from operator perspective.

These contracts are derived from `api_types.py` and the pre-extraction handler code.
The extraction must not alter any observable endpoint behavior.

---

## Route Inventory

| # | Method | Path pattern | Handler method | Service delegation | Response type |
|---|---|---|---|---|---|
| 1 | GET | `/` | `handle_root` | — (HTML template, stays in adapter) | `text/html` |
| 2 | GET | `/api/health` | `handle_health` | `ProjectStateService.get_health` | `HealthResponse` |
| 3 | GET / POST | `/api/shutdown` | `handle_shutdown` | — (token-validated, stays in adapter) | `{"status": "ok"}` |
| 4 | GET / POST | `/api/sync/trigger` | `handle_sync_trigger` | `SyncService.trigger_sync` | `SyncTriggerSuccess` / error |
| 5 | GET | `/api/features` | `handle_features_list` | `MissionScanService.get_features_list` | `FeaturesListResponse` |
| 6 | GET | `/api/kanban/{feature_id}` | `handle_kanban` | `MissionScanService.get_kanban` | `KanbanResponse` |
| 7 | GET | `/api/research/{feature_id}` | `handle_research` | `DashboardFileReader.read_research` | `ResearchResponse` |
| 8 | GET | `/api/research/{feature_id}/{file}` | `handle_research` | `DashboardFileReader.read_artifact_file` | `text/plain` |
| 9 | GET | `/api/contracts/{feature_id}` | `handle_contracts` | `DashboardFileReader.read_artifact_directory` | `ArtifactDirectoryResponse` |
| 10 | GET | `/api/contracts/{feature_id}/{file}` | `handle_contracts` | `DashboardFileReader.read_artifact_file` | `text/plain` |
| 11 | GET | `/api/checklists/{feature_id}` | `handle_checklists` | `DashboardFileReader.read_artifact_directory` | `ArtifactDirectoryResponse` |
| 12 | GET | `/api/checklists/{feature_id}/{file}` | `handle_checklists` | `DashboardFileReader.read_artifact_file` | `text/plain` |
| 13 | GET | `/api/artifact/{feature_id}/{name}` | `handle_artifact` | `DashboardFileReader.read_named_artifact` | `text/plain` |
| 14 | GET | `/api/diagnostics` | `handle_diagnostics` | — (thin delegation to `run_diagnostics`, stays in adapter) | `DiagnosticsResponse` |
| 15 | GET | `/api/charter` | `handle_charter` | — (thin delegation to `resolve_project_charter_path`, stays in adapter) | `text/plain` |
| 16 | GET | `/glossary` | `handle_glossary_page` | — (not in extraction scope) | `text/html` |
| 17 | GET | `/api/glossary-health` | `handle_glossary_health` | — (not in extraction scope) | `GlossaryHealthResponse` |
| 18 | GET | `/api/glossary-terms` | `handle_glossary_terms` | — (not in extraction scope) | `list[GlossaryTermRecord]` |
| 19 | GET | `/api/charter-lint` | `handle_charter_lint` | — (not in extraction scope) | `DecayWatchTileResponse` |
| 20 | GET | `/api/dossier/*` | `handle_dossier` | — (thin routing to `DossierAPIHandler`, stays in adapter) | varies |
| 21 | GET | `/static/*` | `handle_static` | — (static file serving, stays in adapter) | varies |

---

## Route Contracts (extracted routes only)

### GET `/api/health`

**Status codes**: `200 OK` always (error conditions surface within the body, not as HTTP status).

**Response shape** (`HealthResponse`, `total=False`):

```json
{
  "status": "ok",
  "project_path": "/absolute/path/to/project",
  "sync": {
    "running": true,
    "last_sync": "2026-05-02T12:00:00+00:00",
    "consecutive_failures": 0
  },
  "websocket_status": "Active",
  "token": "<project-token>"
}
```

**Field notes**:
- `token` is conditionally present — omitted when the project has no token.
- `sync.error` replaces `sync.last_sync` / `sync.consecutive_failures` on
  daemon status exception.
- `websocket_status` is `"Offline"` on daemon exception.

**Post-extraction invariant**: `ProjectStateService.get_health` returns this
exact shape. The adapter calls `_send_json(200, service.get_health(token=...))`.

---

### GET / POST `/api/sync/trigger`

**Auth**: Optional `?token=<project_token>` query parameter. If a token is
configured for the project and the request omits it or supplies the wrong value,
the adapter returns `403`.

**Success status codes**:
- `202` — daemon started and trigger request accepted (`{"status": "scheduled"}`)
- `202` — daemon skipped by policy (`{"status": "skipped", "manual_mode": true, "reason": "..."}`)

**Error status codes**:
- `403` — invalid token
- `503` — daemon unavailable
- `500` — unexpected exception

**Success response** (`SyncTriggerSuccess`):

```json
{ "status": "scheduled" }
```

**Skip response** (manual mode or rollout disabled):

```json
{ "status": "skipped", "manual_mode": true, "reason": "policy_manual" }
```

**Post-extraction invariant**: `SyncService.trigger_sync(token=...)` returns
`SyncTriggerResult`. The adapter maps result fields to HTTP status and JSON body.
Token validation remains in the adapter (HTTP concern).

---

### GET `/api/features`

**Status codes**: `200 OK` on success; `500` with `FeaturesListErrorResponse` on
exception.

**Response shape** (`FeaturesListResponse`):

```json
{
  "features": [
    {
      "id": "dashboard-service-extraction-01KQMCA6",
      "name": "dashboard-service-extraction-01KQMCA6",
      "display_name": "Dashboard Service Extraction",
      "path": "kitty-specs/dashboard-service-extraction-01KQMCA6",
      "artifacts": {
        "spec": { "exists": true, "mtime": 1746187124.0, "size": 8192 },
        "plan": { "exists": true, "mtime": 1746190000.0, "size": 4096 }
      },
      "workflow": {
        "specify": "done",
        "plan": "done",
        "tasks": "pending",
        "implement": "not_started"
      },
      "kanban_stats": {
        "total": 7, "planned": 5, "doing": 1, "for_review": 0,
        "approved": 0, "done": 1
      },
      "meta": { "mission_id": "01KQMCA6PM8QZTQ3ZJ0RZPX708", "mission_type": "software-dev" },
      "worktree": { "path": null, "exists": false },
      "is_legacy": false
    }
  ],
  "active_feature_id": "dashboard-service-extraction-01KQMCA6",
  "project_path": "~/Documents/_code/SDD/fork/spec-kitty",
  "worktrees_root": null,
  "active_worktree": null,
  "active_mission": {
    "name": "Software Development",
    "domain": "software",
    "version": "1.0.0",
    "slug": "software-dev",
    "description": "Build software features, APIs, and CLI tools",
    "path": "~/.kittify/missions/software-dev",
    "feature": "dashboard-service-extraction-01KQMCA6"
  }
}
```

**Error response** (`FeaturesListErrorResponse`, HTTP 500):

```json
{ "error": "failed_to_scan_features", "detail": "<exception message>" }
```

**Post-extraction invariant**: `MissionScanService.get_features_list()` returns
`FeaturesListResponse`. The `is_legacy` flag on each `FeatureItem` is set by the
service object, not the adapter.

---

### GET `/api/kanban/{feature_id}`

**Path parameter**: `feature_id` — mission slug or directory name.

**Status codes**: `200 OK` on success; `404` when the feature_id segment is missing.

**Response shape** (`KanbanResponse`):

```json
{
  "lanes": {
    "planned": [ { "id": "WP01", "title": "...", "lane": "planned", ... } ],
    "in_progress": [],
    "for_review": [],
    "done": []
  },
  "is_legacy": false,
  "upgrade_needed": false,
  "weighted_percentage": 14.3
}
```

**Field notes**:
- `lanes` keys are the 9-lane names from the status model; values are lists of
  `KanbanTaskData` objects.
- `weighted_percentage` is `null` for legacy features, or when the event log
  is missing or unreadable.
- `upgrade_needed` mirrors `is_legacy`.

**Post-extraction invariant**: `MissionScanService.get_kanban(feature_id)` returns
`KanbanResponse`. The adapter writes the JSON body and sets `Cache-Control: no-cache`.

---

### GET `/api/research/{feature_id}`

**Path parameter**: `feature_id` — mission slug or directory name.

**Status codes**: `200 OK` always (missing research returns empty body fields).

**Response shape** (`ResearchResponse`):

```json
{
  "main_file": "# Research: ...\n...",
  "artifacts": [
    { "name": "notes.md", "path": "research/notes.md", "icon": "📝" },
    { "name": "data.csv", "path": "research/data.csv", "icon": "📊" }
  ]
}
```

**Field notes**:
- `main_file` is `null` when `research.md` does not exist for the feature.
- Encoding errors produce a UTF-8-safe warning prefix prepended to the content
  (not an error response).

---

### GET `/api/research/{feature_id}/{file}`

**Path parameters**: `feature_id`, `file` — URL-encoded relative path within
the feature directory.

**Status codes**: `200 OK` with `text/plain`; `404` when the file does not exist
or the path escapes the feature directory boundary.

**Security invariant**: `artifact_file.relative_to(feature_dir.resolve())` is
enforced before reading; path traversal attempts return `404`.

---

### GET `/api/contracts/{feature_id}` and GET `/api/checklists/{feature_id}`

**Response shape** (`ArtifactDirectoryResponse`):

```json
{
  "files": [
    { "name": "dashboard-routes.md", "path": "contracts/dashboard-routes.md", "icon": "📝" },
    { "name": "schema.json", "path": "contracts/schema.json", "icon": "📋" }
  ]
}
```

Empty `files` list when the directory does not exist. `icon` is `"✅"` for `.md`
files in the checklists directory; `"📝"` in the contracts directory.

---

### GET `/api/contracts/{feature_id}/{file}` and GET `/api/checklists/{feature_id}/{file}`

Same contract as `GET /api/research/{feature_id}/{file}`. `text/plain`;
path-traversal check enforced.

---

### GET `/api/artifact/{feature_id}/{name}`

**Path parameter**: `name` — one of: `spec`, `plan`, `tasks`, `research`,
`quickstart`, `data-model`.

**Status codes**: `200 OK` with `text/plain`; `404` when the artifact does not
exist or `name` is not in the allowed set.

**Artifact map** (canonical, must not change post-extraction):

| name | filename |
|---|---|
| `spec` | `spec.md` |
| `plan` | `plan.md` |
| `tasks` | `tasks.md` |
| `research` | `research.md` |
| `quickstart` | `quickstart.md` |
| `data-model` | `data-model.md` |

---

## Routes Staying in the Adapter (no service delegation)

The following routes are not extracted to `src/dashboard/` during this mission.
They either perform thin delegation to subsystems that are not yet extracted
(`diagnostics`, `charter`, `dossier`) or are file-serving / framework-level
concerns (`static`, `root`, `shutdown`).

| Route | Reason stays in adapter |
|---|---|
| `GET /` | Renders HTML template — pure I/O, no business logic |
| `GET /api/diagnostics` | Delegates to `run_diagnostics`; diagnostics module not yet extracted |
| `GET /api/charter` | Delegates to `resolve_project_charter_path`; charter module already canonical |
| `GET /api/dossier/*` | Routes to `DossierAPIHandler`; dossier not in extraction scope |
| `GET /glossary` | HTML page; static serving |
| `GET /api/glossary-health` | Thin delegation to `GlossaryHandler`; glossary module already canonical |
| `GET /api/glossary-terms` | Same as glossary-health |
| `GET /api/charter-lint` | Thin delegation to `LintTileHandler`; lint module not in scope |
| `GET /static/*` | Static asset serving (C-006) |
| `GET / POST /api/shutdown` | HTTP token validation; no business logic |

---

## Pre/Post Extraction Snapshot Comparison

To satisfy FR-011 and SC-002, the existing test suite (`tests/test_dashboard/`)
captures pre-extraction behavior. The post-extraction responses must be
byte-identical for JSON routes (field order may vary; values must not).

**Field audit checklist** (for `dashboard.js` consumers — FR-012):

| Field | Route | Referenced in `dashboard.js` | Pre-extraction present | Post-extraction present |
|---|---|---|---|---|
| `features[].id` | `/api/features` | ✅ | ✅ | must be ✅ |
| `features[].display_name` | `/api/features` | ✅ | ✅ | must be ✅ |
| `features[].kanban_stats.total` | `/api/features` | ✅ | ✅ | must be ✅ |
| `active_feature_id` | `/api/features` | ✅ | ✅ | must be ✅ |
| `active_mission.name` | `/api/features` | ✅ | ✅ | must be ✅ |
| `lanes` | `/api/kanban/*` | ✅ | ✅ | must be ✅ |
| `weighted_percentage` | `/api/kanban/*` | ✅ | ✅ | must be ✅ |
| `status` | `/api/health` | ✅ | ✅ | must be ✅ |
| `sync.running` | `/api/health` | ✅ | ✅ | must be ✅ |
| `main_file` | `/api/research/*` | ✅ | ✅ | must be ✅ |

Full field audit to be performed during WP07 per `research.md §5`.
Any drift discovered predates this mission and must be documented as a
pre-existing issue.
