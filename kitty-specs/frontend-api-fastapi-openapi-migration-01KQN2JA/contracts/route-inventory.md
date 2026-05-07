# Route Inventory — Dashboard API

This document is the canonical list of every dashboard route covered by this
mission. The contract-parity test (`tests/test_dashboard/test_transport_parity.py`)
parametrizes against this list; every entry must have both a legacy handler
method and a FastAPI router function or route registration.

| HTTP method | Path | Legacy handler | FastAPI router | Response model | Notes |
|-------------|------|----------------|----------------|----------------|-------|
| GET | `/` | `APIHandler.handle_root` | `routers/static_mount.py:home()` | `text/html` (no JSON) | Returns rendered dashboard HTML shell. |
| GET | `/api/features` | `FeatureHandler.handle_features_list` | `routers/features.py:list_features()` | `FeaturesListResponse` | Mission scan + active feature resolution. |
| GET | `/api/kanban/{feature_id}` | `FeatureHandler.handle_kanban` | `routers/kanban.py:get_kanban()` | `KanbanResponse` | Path param disambiguates feature. |
| GET | `/api/research/{feature_id}` | `FeatureHandler.handle_research` (no trailing) | `routers/artifacts.py:get_research()` | `ResearchResponse` | research.md root payload. |
| GET | `/api/research/{feature_id}/{file}` | `FeatureHandler.handle_research` (with file) | `routers/artifacts.py:get_research_file()` | `text/plain` | Specific research file under feature. |
| GET | `/api/contracts/{feature_id}` | `FeatureHandler.handle_contracts` | `routers/artifacts.py:list_contracts()` | `ArtifactDirectoryResponse` | Directory listing. |
| GET | `/api/contracts/{feature_id}/{file}` | `FeatureHandler.handle_contracts` (with file) | `routers/artifacts.py:get_contract_file()` | `text/plain` | Specific contract file. |
| GET | `/api/checklists/{feature_id}` | `FeatureHandler.handle_checklists` | `routers/artifacts.py:list_checklists()` | `ArtifactDirectoryResponse` | Directory listing. |
| GET | `/api/checklists/{feature_id}/{file}` | `FeatureHandler.handle_checklists` (with file) | `routers/artifacts.py:get_checklist_file()` | `text/plain` | Specific checklist file. |
| GET | `/api/artifact/{feature_id}/{name}` | `FeatureHandler.handle_artifact` | `routers/artifacts.py:get_artifact()` | `text/plain` | Named primary artifact (spec.md / plan.md / etc.). |
| GET | `/api/health` | `APIHandler.handle_health` | `routers/health.py:get_health()` | `HealthResponse` | Health + sync status. |
| POST | `/api/sync/trigger` | `APIHandler.handle_sync_trigger` | `routers/sync.py:trigger_sync()` | `Union[SyncTriggerScheduledResponse, SyncTriggerSkippedResponse, SyncTriggerUnavailableResponse, SyncTriggerFailedResponse]` | Token-validated; result body comes from `SyncTriggerResult.body()`. |
| GET | `/api/charter` | `APIHandler.handle_charter` | `routers/charter.py:get_charter()` | `text/plain` | Project charter text. |
| GET | `/api/diagnostics` | `APIHandler.handle_diagnostics` | `routers/diagnostics.py:get_diagnostics()` | `DiagnosticsResponse` | Project diagnostics. |
| GET | `/api/dossier/overview` | `APIHandler.handle_dossier` | `routers/dossier.py:get_overview()` | `DossierOverviewResponse` (existing or pass-through) | mission_slug query param. |
| GET | `/api/dossier/artifacts` | `APIHandler.handle_dossier` | `routers/dossier.py:list_artifacts()` | `DossierArtifactsResponse` | Filters via query params. |
| GET | `/api/dossier/artifacts/{artifact_key}` | `APIHandler.handle_dossier` | `routers/dossier.py:get_artifact_detail()` | `DossierArtifactDetailResponse` | mission_slug query param. |
| GET | `/api/dossier/snapshots/export` | `APIHandler.handle_dossier` | `routers/dossier.py:export_snapshot()` | `DossierSnapshotExportResponse` | mission_slug query param. |
| GET | `/api/glossary/...` | `GlossaryHandler.*` | `routers/glossary.py:*` | passthrough (transport-only migration; service extraction is a follow-up mission) | TODO marker on each route. |
| GET | `/api/lint/...` | `LintHandler.*` | `routers/lint.py:*` | passthrough (transport-only migration) | TODO marker on each route. |
| GET | `/static/dashboard/dashboard.css` | `StaticHandler` | `app.mount("/static", StaticFiles(...))` | `text/css` | Asset path unchanged. |
| GET | `/static/dashboard/dashboard.js` | `StaticHandler` | `app.mount("/static", StaticFiles(...))` | `application/javascript` | Asset path unchanged. |
| POST | `/api/shutdown` | `DashboardHandler._handle_shutdown` (or per-class delegate) | `routers/shutdown.py:shutdown()` | `ShutdownResponse` | Token-validated. Threads a stop on the running server. |

## Status code table

| Route | Success | Token failure | Not found | Error |
|-------|---------|---------------|-----------|-------|
| `/api/features` | 200 | n/a | n/a | 500 (`failed_to_scan_features`) |
| `/api/kanban/{id}` | 200 | n/a | 404 (path too short) | n/a |
| `/api/research/{id}` | 200 | n/a | 404 (no research.md) | n/a |
| `/api/health` | 200 | n/a | n/a | n/a (best-effort sync read; degrades to `running:false`) |
| `/api/sync/trigger` | 202 (scheduled or skipped) / 503 (unavailable) / 500 (failed) | 403 | n/a | covered by 503/500 branches |
| `/api/charter` | 200 | n/a | 404 (no charter) | 500 (load failure) |
| `/api/diagnostics` | 200 | n/a | n/a | 500 (`diagnostics_failed`) |
| `/api/dossier/*` | 200 | n/a | 404 (unknown sub-path) | 500 / per-handler errors |
| `/api/shutdown` | 200 | 403 | n/a | 400 (invalid payload on POST) |

## Response normalization rules (parity test)

The parity test asserts JSON equivalence after this normalization step:

1. Both responses are parsed with `json.loads`.
2. The resulting dicts/lists are recursively re-serialized with `sort_keys=True`.
3. The byte sequences must be identical.

Differences that are tolerated (do NOT fail the test):

- key ordering inside JSON objects
- whitespace inside the JSON document

Differences that ARE failures:

- different keys present
- different values for the same key
- different status codes
- different `Content-Type` header (`application/json` vs `application/json; charset=utf-8` is normalized by stripping after `;`)

Differences that are explicitly out of scope:

- response time (measured separately by NFR-002)
- header order (HTTP semantics: order is not significant)
