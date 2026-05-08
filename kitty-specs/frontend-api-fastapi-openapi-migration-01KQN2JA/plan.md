# Implementation Plan: Frontend API — FastAPI + OpenAPI Migration

**Branch**: `feature/650-dashboard-ui-ux-overhaul` | **Date**: 2026-05-02 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/frontend-api-fastapi-openapi-migration-01KQN2JA/spec.md`

## Summary

Replace the dashboard's hand-rolled `BaseHTTPServer` + multi-inheritance router with a FastAPI app, mounted under `src/dashboard/api/`. Existing Python service objects (`MissionScanService`, `ProjectStateService`, `SyncService`, `DashboardFileReader`) are reused as-is — they have no transport coupling. A strangler boundary in `src/specify_cli/dashboard/server.py` chooses between the legacy stack and the FastAPI app via config (`dashboard.transport: legacy | fastapi`, default `fastapi`); a CLI flag overrides. Pydantic v2 response models replace TypedDict shapes for the OpenAPI generator while a TypedDict shim layer keeps any existing TypedDict importer compiling.

The mission ships:

1. `src/dashboard/api/app.py` — `create_app()` factory.
2. `src/dashboard/api/routers/*.py` — one APIRouter per route family, mounted on the app.
3. `src/dashboard/api/models.py` — Pydantic v2 BaseModels (one per existing TypedDict).
4. Strangler boundary in `src/specify_cli/dashboard/server.py`.
5. CLI flag `--transport {legacy,fastapi}` on `spec-kitty dashboard`.
6. Auto-published OpenAPI doc at `/openapi.json` + Swagger UI at `/docs` + ReDoc at `/redoc`.
7. Golden-snapshot OpenAPI test, contract-parity test suite, FastAPI handler-purity architectural test.
8. ADR `2026-05-02-2-fastapi-openapi-transport.md`, ownership map / manifest entries, migration runbook.

## Technical Context

**Language/Version**: Python 3.11+ (existing repo requirement; `.python-version` pins 3.11 for ops, but tests run cleanly on 3.13.12 also).
**Primary Dependencies**: `fastapi` (~0.115.x or current minor), `uvicorn[standard]` (~0.32.x or current), `pydantic` (v2; pinned via FastAPI's lower bound, no separate top-level pin needed).
**Storage**: filesystem only — `kitty-specs/`, `.kittify/`, OpenAPI snapshot in `tests/test_dashboard/snapshots/openapi.json`.
**Testing**: pytest + FastAPI's `TestClient` for transport tests; `openapi_spec_validator` for spec validity; existing seam-test pattern for service-layer mocks.
**Target Platform**: local development on Linux / macOS / Windows; loopback-only HTTP; same operator surface as today (`spec-kitty dashboard`).
**Project Type**: single project (Python library + CLI; no separate frontend deploy).
**Performance Goals**: cold-start ≤ 25 % regression vs legacy (NFR-001); per-request median ≤ 30 % regression on `/api/features` (NFR-002).
**Constraints**: localhost-only network binding; no auth changes; no contract redesign; legacy stack retained in tree until a separate retirement mission removes it.
**Scale/Scope**: ~14 existing routes, 3 service classes already in place, 1 file reader; OpenAPI doc < 200 KB (NFR-005).

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Charter directive | Conformance |
|-------------------|-------------|
| DIRECTIVE_024 (Locality of Change) | Pass — allowed scope explicitly enumerated in spec § Governance and reaffirmed in this plan: `src/dashboard/api/`, `src/dashboard/api_types.py` (compat shim), `src/specify_cli/dashboard/server.py` (strangler), `tests/test_dashboard/`, `tests/architectural/`, `architecture/2.x/`, `docs/migration/`, mission directory. |
| DIRECTIVE_010 (Test Coverage Discipline) | Pass — every route has a parity test; every Pydantic model has shape coverage; the snapshot test guards the OpenAPI doc. |
| DIRECTIVE_036 (Adapter Test Pattern) | Pass — FastAPI `TestClient` is the canonical seam tool; service-layer mocks reuse the existing `dashboard.services.*` patch points. |

No charter violations. No `Complexity Tracking` entries needed.

## Project Structure

### Documentation (this feature)

```
kitty-specs/frontend-api-fastapi-openapi-migration-01KQN2JA/
├── plan.md              # This file
├── spec.md              # ✅ already authored
├── research.md          # Phase 0 — created next
├── data-model.md        # Phase 1 — created next
├── quickstart.md        # Phase 1 — created next
├── contracts/
│   ├── route-inventory.md          # canonical list of routes + methods + response models
│   └── openapi-stability.md        # rules for what's allowed to change without snapshot bump
└── tasks.md              # Phase 2 (created by /spec-kitty.tasks)
```

### Source Code (repository root)

The FastAPI app subpackage is added under the existing `src/dashboard/` package; the legacy `src/specify_cli/dashboard/handlers/` tree stays in place until retirement. No restructuring of unrelated trees.

```
src/dashboard/
├── __init__.py
├── api_types.py                    # ✅ existing — TypedDicts (kept for compat)
├── file_reader.py                  # ✅ existing
├── services/
│   ├── __init__.py
│   ├── mission_scan.py             # ✅ existing
│   ├── project_state.py            # ✅ existing
│   └── sync.py                     # ✅ existing
└── api/                            # 🆕 NEW — FastAPI subpackage
    ├── __init__.py
    ├── app.py                      # 🆕 create_app() factory
    ├── deps.py                     # 🆕 FastAPI Depends (token validation, DI)
    ├── models.py                   # 🆕 Pydantic v2 BaseModels (one per TypedDict)
    ├── errors.py                   # 🆕 HTTPException → JSON error payload mapping
    └── routers/                    # 🆕 one APIRouter per route family
        ├── __init__.py
        ├── features.py             # /api/features
        ├── kanban.py               # /api/kanban/{feature_id}
        ├── artifacts.py            # /api/research, /api/contracts, /api/checklists, /api/artifact
        ├── health.py               # /api/health
        ├── sync.py                 # /api/sync/trigger
        ├── charter.py              # /api/charter
        ├── diagnostics.py          # /api/diagnostics
        ├── dossier.py              # /api/dossier/*
        ├── glossary.py             # /api/glossary/*
        ├── lint.py                 # /api/lint/*
        ├── shutdown.py             # /api/shutdown
        └── static_mount.py         # StaticFiles mount for dashboard.css/js + index HTML

src/specify_cli/dashboard/
├── server.py                       # ✏️  modified — strangler boundary
├── handlers/                       # ✅ existing — left in place during transition
└── ... (unchanged)

src/specify_cli/cli/commands/
└── dashboard.py                    # ✏️  modified — adds --transport flag

tests/test_dashboard/
├── test_seams.py                   # ✅ existing — keeps passing
├── test_api_contract.py            # ✅ existing — keeps passing
├── test_openapi_snapshot.py        # 🆕 golden-snapshot test
├── test_transport_parity.py        # 🆕 legacy vs FastAPI per-route parity
├── test_fastapi_app.py             # 🆕 unit tests for app factory + deps
└── snapshots/
    └── openapi.json                # 🆕 committed OpenAPI snapshot

tests/architectural/
├── test_dashboard_boundary.py      # ✏️  modified — allows src/dashboard/api → dashboard.services etc.
└── test_fastapi_handler_purity.py  # 🆕 enforces FR-009 / NFR-007 (no Response in handlers)

architecture/2.x/
├── 05_ownership_map.md             # ✏️  Dashboard slice gains src/dashboard/api/ entry
├── 05_ownership_manifest.yaml      # ✏️  mirrored
└── adr/
    └── 2026-05-02-2-fastapi-openapi-transport.md   # 🆕 ADR

docs/migration/
└── dashboard-fastapi-transport.md  # 🆕 migration runbook

pyproject.toml                      # ✏️  fastapi + uvicorn[standard] added
```

**Structure Decision**: Single-project layout. The new `src/dashboard/api/` subpackage is the canonical FastAPI surface. Service objects from the parent extraction mission are reused unchanged.

## Phase 0 — Research (`research.md`)

Topics to resolve before Phase 1 design:

1. **Pydantic v1 vs v2 compatibility** — confirm no v1-only API is used elsewhere in the repo. (Initial check: `pyproject.toml` does not pin Pydantic; FastAPI 0.115.x requires v2. Document the upgrade path.)
2. **Token validation as `Depends`** — design the dependency function: takes `request`, reads project_token from app state, compares to `?token=` query param, raises `HTTPException(403)`. The dependency feeds the validated token into the handler as a typed argument.
3. **Static file serving** — does `StaticFiles` cover the existing static handler's behavior (asset paths, index fallback)? Resolve any gaps.
4. **WSGI vs ASGI co-existence** — `BaseHTTPServer` is sync/threaded; FastAPI is ASGI on Uvicorn. The strangler boundary chooses one stack at process start; both never run concurrently. Document the trade-off vs an `a2wsgi`-style mounted-app approach.
5. **Trailing-slash redirects** — FastAPI defaults to trailing-slash normalization (308 redirect). Audit existing routes for sensitivity (the parity test will catch it; document the configured behavior).
6. **OpenAPI determinism** — does FastAPI's spec generator produce a stable byte-equivalent output across runs? Verify and document any sort/normalization step needed for the snapshot test.
7. **Test client lifecycle** — running TestClient against `create_app(project_dir=tmp_path)` vs the legacy `urllib`-against-real-server pattern. Document the test layering.
8. **Charter / dossier / glossary handlers** — confirm these still hold inline business logic (not yet service-extracted). Plan the transport-only migration for them and explicitly file follow-up tickets for service extraction (out of scope for this mission).

## Phase 1 — Design & Contracts

### `data-model.md`

For each existing TypedDict in `src/dashboard/api_types.py`, declare the equivalent Pydantic v2 `BaseModel`:

| TypedDict (existing) | Pydantic model (new) | Notes |
|----------------------|----------------------|-------|
| `Feature` | `Feature` | nested in `FeaturesListResponse.features` |
| `MissionContext` | `MissionContext` | optional `feature` key remains optional via `field: str \| None = None` |
| `FeaturesListResponse` | `FeaturesListResponse` | top-level for `/api/features` |
| `KanbanResponse` | `KanbanResponse` | top-level for `/api/kanban/{id}` |
| `HealthResponse` | `HealthResponse` | top-level for `/api/health` |
| `SyncTriggerResponse` (4 variants) | `SyncTriggerScheduledResponse`, `SyncTriggerSkippedResponse`, `SyncTriggerUnavailableResponse`, `SyncTriggerFailedResponse` | union response — FastAPI `response_model=Union[...]` or per-status response definitions |
| `DiagnosticsResponse` | `DiagnosticsResponse` | … |
| (any artifact / research / contracts / checklists shapes) | matching models | handled per-router |
| (dossier shapes) | passthrough — leave existing TypedDict + dict response in router until follow-up | documented as transport-only migration |
| (glossary, lint shapes) | passthrough — same as above | documented as transport-only migration |

### `contracts/route-inventory.md`

A canonical list of every existing route, its method(s), the legacy handler method, and the new FastAPI router function. Used by the parity test as the single source of truth.

### `contracts/openapi-stability.md`

Rules for when the OpenAPI snapshot may change without manual review:

- adding a new route — snapshot bump expected, requires reviewer signoff
- adding a new optional field — snapshot bump expected, requires reviewer signoff
- removing a field, changing a field type, changing a status code — **prohibited in this mission** (C-004); must be a separate redesign mission
- FastAPI version bump — snapshot bump may be unavoidable; flag in PR description

### `quickstart.md`

A copy-pasteable walk-through:

1. `git checkout feature/650-dashboard-ui-ux-overhaul`
2. `uv sync --frozen`
3. `spec-kitty dashboard --transport fastapi` → opens `http://127.0.0.1:<port>/`
4. Visit `/docs` → confirm Swagger UI loads with all routes
5. `curl http://127.0.0.1:<port>/openapi.json | jq` → confirm valid OpenAPI 3.x
6. `pytest tests/test_dashboard/test_transport_parity.py -q` → confirm legacy↔FastAPI parity
7. Flip back via `--transport legacy` to confirm rollback path

## Phase 2 — Tasks (created by `/spec-kitty.tasks`)

Phase 2 will produce `tasks.md` with work packages. Anticipated WP shape (the actual decomposition is `/spec-kitty.tasks`'s job, not this plan's):

- WP01 — Governance: ADR, ownership map / manifest, migration runbook (≤ 5 subtasks)
- WP02 — Dependencies + app factory + StaticFiles + strangler boundary (≤ 7 subtasks)
- WP03 — Pydantic models + Depends + error mapping (≤ 6 subtasks)
- WP04 — Routers (split by family if needed; could span 2 WPs depending on size) (≤ 7 subtasks)
- WP05 — Tests: parity suite + OpenAPI snapshot + handler-purity architectural test (≤ 6 subtasks)
- WP06 — CLI integration + benchmark script + documentation tie-off (≤ 5 subtasks)

## Phase 3 — Implementation

`/spec-kitty.implement WP## --agent claude` per WP. Lane allocation handled by `/spec-kitty.tasks-finalize` based on `owned_files` overlap.

## Phase 4 — Review & Merge

Per-WP review via `/spec-kitty.review`. After all WPs done, mission merge via `spec-kitty merge`. Post-merge `/spec-kitty.mission-review` to surface drift and risks.

## Complexity Tracking

*No charter violations identified. Section intentionally empty.*
