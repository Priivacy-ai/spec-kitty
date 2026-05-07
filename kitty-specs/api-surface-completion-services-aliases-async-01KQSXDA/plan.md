# Implementation Plan: API Surface Completion — Domain Services, Alias Retirement, Async Transport
*Path: kitty-specs/api-surface-completion-services-aliases-async-01KQSXDA/plan.md*

**Branch**: `feature/645-api-surface-completion-mission-c` | **Spec**: `kitty-specs/api-surface-completion-services-aliases-async-01KQSXDA/spec.md`
**Input**: Feature specification from `/kitty-specs/api-surface-completion-services-aliases-async-01KQSXDA/spec.md`

---

## Summary

Extract glossary and lint/decay-watch logic into proper domain service objects (`GlossaryService`, `LintService`) placed inside their domain modules (`specify_cli/glossary/`, `specify_cli/charter_lint/`). Retire deprecated alias endpoints (`/api/features`, `/api/kanban/{id}`) with HTTP 410. Add a read-only SSE endpoint (`GET /api/events/missions`) for push-based mission status updates. Wire an `openapi-typescript` codegen pipeline. Migrate all TypedDicts from `dashboard/api_types.py` to their canonical locations (domain modules or `kernel/`) and delete the file.

## Technical Context

**Language/Version**: Python 3.11+ (existing project requirement)
**Primary Dependencies**: FastAPI (dashboard), typer, rich, ruamel.yaml, pytest, mypy (CLI); `sse-starlette` or `starlette` built-in `EventSourceResponse` for SSE; `openapi-typescript` (npm, codegen only)
**Storage**: Filesystem only — status event log (`status.events.jsonl`), lint report (`.kittify/lint-report.json`), glossary seed files
**Testing**: pytest with ≥ 90% line coverage for new services; mypy --strict must pass; existing dashboard tests must remain green; parity tests (NFR-001, NFR-002) verifying byte-identical output vs current private helpers
**Target Platform**: Linux / macOS / Windows 10+ (cross-platform; SSE via ASGI)
**Project Type**: Single Python package (`src/` layout) with embedded FastAPI sub-application
**Performance Goals**: Median non-SSE latency increase ≤ 5 ms under 10-concurrent SSE clients (NFR-003); SSE resource release ≤ 2 s on client disconnect (NFR-004)
**Constraints**: `GlossaryService` / `LintService` must not import `fastapi`, `starlette`, or `pydantic` (C-003); no new domain services in `dashboard/services/` (C-002); alias retirement must return 410 not 3xx (C-005); codegen must run against static OpenAPI snapshot — no live server (C-007); Python 3.11+ (C-008)
**Scale/Scope**: ~30 TypedDicts across `dashboard/api_types.py` categorised and migrated; 2 new service classes; 1 new SSE router; 2 alias endpoints retired; 1 codegen pipeline

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Python 3.11+** ✅ — no new runtime without `pyproject.toml` + `uv.lock` (C-008)
- **mypy --strict** ✅ — all new code must type-check cleanly
- **pytest ≥ 90% coverage** ✅ — NFR-006 encodes this for new services
- **Cross-platform** ✅ — SSE via ASGI, no platform-specific dependencies
- **Shared package boundaries** ✅ — `specify_cli` domain packages never import from `dashboard`; `kernel` remains zero-dependency
- **Branch strategy** ✅ — planning and implementation on `feature/645-api-surface-completion-mission-c`; merges into same branch; depends on Mission B merging first
- **Terminology canon** ✅ — no `Feature*` identifiers introduced; all new identifiers use Mission terminology

No charter violations identified.

## Project Structure

### Documentation (this mission)

```
kitty-specs/api-surface-completion-services-aliases-async-01KQSXDA/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks/               # Phase 2 output (/spec-kitty.tasks)
```

### Source Code (repository root)

```
src/
├── kernel/
│   └── api_types.py                   # NEW — cross-cutting TypedDicts migrated from dashboard/api_types.py (kernel/ pkg already exists)
│
├── specify_cli/
│   ├── glossary/
│   │   ├── types.py                   # NEW — GlossaryHealthResponse, GlossaryTermRecord (moved)
│   │   └── service.py                 # NEW — GlossaryService
│   ├── charter_lint/
│   │   ├── types.py                   # NEW — DecayWatchTileResponse (moved)
│   │   └── service.py                 # NEW — LintService
│   ├── status/
│   │   └── api_types.py               # NEW — KanbanTaskData, KanbanStats, KanbanResponse (moved)
│   ├── missions/
│   │   └── api_types.py               # NEW — MissionRecord, MissionContext, WorktreeInfo, WorkflowStatus (moved)
│   └── dashboard/
│       ├── api_types.py               # SHIM → updated to import from new locations during transition
│       └── handlers/
│           ├── glossary.py            # UPDATED — imports from specify_cli.glossary.types
│           └── lint.py                # UPDATED — imports from specify_cli.charter_lint.types
│
└── dashboard/
    ├── api_types.py                   # DELETED (or presentation-only remnant) after all migrations
    └── api/
        ├── models.py                  # UPDATED — Pydantic models reference canonical TypedDicts
        └── routers/
            ├── glossary.py            # UPDATED — delegates to GlossaryService; TODO markers removed
            ├── lint.py                # UPDATED — delegates to LintService; TODO markers removed
            ├── events.py              # NEW — GET /api/events/missions SSE endpoint
            └── aliases.py             # UPDATED — /api/features, /api/kanban/{id} → 410

tests/
├── unit/
│   ├── test_glossary_service.py       # NEW — GlossaryService unit tests (≥ 90%)
│   └── test_lint_service.py           # NEW — LintService unit tests (≥ 90%)
├── integration/
│   └── test_sse_events.py             # NEW — SSE stream integration test
└── architectural/
    └── test_dashboard_boundary.py     # UPDATED — assert no specify_cli/kernel → dashboard imports
```

**Structure Decision**: Single project layout (`src/`), extending existing module structure. Domain services placed inside their bounded context packages. No new top-level packages created.

## Complexity Tracking

*No charter violations requiring justification.*

