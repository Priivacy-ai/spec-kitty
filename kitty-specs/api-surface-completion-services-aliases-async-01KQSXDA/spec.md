# Mission Specification: API Surface Completion — Domain Services, Alias Retirement, Async Transport

**Mission ID**: `01KQSXDASEMGGZNAX3A5FXSEPM`
**Mission slug**: `api-surface-completion-services-aliases-async-01KQSXDA`
**Friendly name**: API Surface Completion: Domain Services, Alias Retirement, Async Transport
**Type**: software-dev
**Target branch**: `feature/645-api-surface-completion-mission-c`
**Epic**: [#645 — Stable Application API Surface](https://github.com/Priivacy-ai/spec-kitty/issues/645)
**Tracker issues**: [#954](https://github.com/Priivacy-ai/spec-kitty/issues/954) · [#955](https://github.com/Priivacy-ai/spec-kitty/issues/955)
**Date**: 2026-05-04
**Status**: Draft

---

## Overview

This mission closes out the remaining open items on epic #645, as identified in the
[2026-05-04 status comment](https://github.com/Priivacy-ai/spec-kitty/issues/645#issuecomment-4369983868):

- **Mission C** — Extract glossary and lint/decay-watch logic into proper domain
  service objects (issues #954 and #955).
- **Alias retirement** — Remove the deprecated `/api/features` and `/api/kanban/{id}`
  endpoints after one tagged release has passed with the `Deprecation` headers in place.
- **Step 5** — Add a server-sent events (SSE) endpoint so the dashboard UI and future
  consumers can receive mission/WP state changes as a push stream instead of polling.
- **Step 6** — Wire up the `openapi-typescript` codegen pipeline so TypeScript
  consumers can generate typed bindings from the published OpenAPI document.

The **primary focus** is the **read side** of the API and the domain service layer.
No mutation/write endpoints are introduced. The async transport (Step 5) surfaces
existing read state as a push stream; it does not introduce new write operations.

### Architectural constraint incorporated from Alphonso's assessment (2026-05-04)

Architect Alphonso's review
(`architecture/2.x/initiatives/2026-05-stable-application-api-surface/api-service-placement-assessment.md`)
finds that placing new domain services in `dashboard/services/` would deepen an
existing architectural smell: `specify_cli` (the domain CLI package) already imports
upward from `dashboard.services.registry`, inverting the intended dependency direction.

**This mission applies the corrective posture for Mission C services only**:

- `GlossaryService` → `src/specify_cli/glossary/service.py`
- `LintService` → `src/specify_cli/charter_lint/service.py`

The FastAPI routers remain thin transport adapters that import these services from
their canonical domain locations. Migration of the existing `MissionRegistry` and
companions is explicitly **out of scope** and tracked as a Phase B follow-up.

A further refinement applies to **data transfer objects (DTOs)**:

- DTOs used as return types by a domain service must be defined *alongside* that
  service in its domain module, not in `dashboard/api_types.py`. This is required
  because `dashboard/api` may import from domain modules, but domain modules must
  never import upward from `dashboard/`. Placing `GlossaryHealthResponse` in
  `dashboard/api_types.py` while having `GlossaryService` return it would force
  `specify_cli/glossary/` to import from `dashboard/` — the exact violation the
  dependency direction rule prohibits.
- `GlossaryHealthResponse` and `GlossaryTermRecord` move to
  `src/specify_cli/glossary/types.py`.
- `DecayWatchTileResponse` moves to `src/specify_cli/charter_lint/types.py`.
- All callers — the FastAPI routers, the legacy `BaseHTTPRequestHandler` handlers,
  and the Pydantic model definitions in `dashboard/api/models.py` — update their
  imports to reference the new domain locations. No shim re-exports are left in
  `dashboard/api_types.py`; the moved definitions are deleted from that file as part
  of this mission.
- The remaining TypedDicts in `dashboard/api_types.py` that have no single domain
  owner (e.g., `ErrorResponse`, `HealthResponse`, `ArtifactInfo`,
  `ArtifactDirectoryFile`, `ArtifactDirectoryResponse`, `SyncInfo`,
  `SyncTriggerSuccess`, `FileIntegrity`) are moved to `src/kernel/api_types.py`.
  TypedDicts that have a clear domain correlation (e.g., `KanbanTaskData`,
  `KanbanStats`, `KanbanResponse` → `specify_cli/status/`; `MissionRecord`,
  `MissionContext`, `WorktreeInfo`, `WorkflowStatus` → `specify_cli/missions/`)
  are moved to their respective domain modules instead.
  The planning/research phase will produce a definitive categorisation for each
  type. Once all moves are complete, `dashboard/api_types.py` is removed or
  retained only for types that are unambiguously dashboard-presentation-only
  (e.g., `DiagnosticsResponse`, `ResearchResponse`) — each such exception must
  be justified. All callers update their imports in this mission.

---

## Goals

1. Remove the `# TODO(follow-up)` markers in `src/dashboard/api/routers/glossary.py`
   and `src/dashboard/api/routers/lint.py` by backing them with real domain service objects.
2. Place those service objects inside their domain modules (`specify_cli/glossary/` and
   `specify_cli/charter_lint/`), not in `dashboard/services/`, establishing the
   corrective placement pattern for future domain service extraction.
3. Co-locate domain-specific DTOs (TypedDicts) with their domain service modules;
   `dashboard/api` imports from domain modules — not the other way around.
3. Retire the `/api/features` and `/api/kanban/{id}` deprecation-alias endpoints,
   completing the resource-oriented URL migration from Mission B.
4. Give the dashboard UI (and any future SSE consumer) a push stream of mission and
   WP status events rather than a 1 Hz polling loop.
5. Provide a reproducible codegen step that generates TypeScript type bindings from
   the spec-kitty OpenAPI document, enabling typed dashboard and future SDK consumers.

---

## Out of Scope

- Migrating `MissionRegistry`, `MissionScanService`, `ProjectStateService`, or
  `SyncService` out of `dashboard/services/` — that is Alphonso's Phase B, a separate
  follow-up mission.
- Any new write/mutation endpoints or services.
- Full TypeScript client generation and distribution as a package — only the codegen
  pipeline (tooling wired up, types generated on demand) is in scope.
- WebSocket transport — SSE is sufficient for a unidirectional read stream.
- Visual or design-system changes (covered by sibling epic #650).
- Changes to the legacy `BaseHTTPRequestHandler` stack beyond delegation to the new
  service objects.

---

## Assumptions

1. The `Deprecation: true` headers on `/api/features` and `/api/kanban/{id}` have been
   live for at least one tagged release (shipped in Mission B,
   `resource-oriented-mission-api-01KQQRF2`). Retirement is therefore safe once this
   mission lands.
2. `openapi-typescript` is the agreed codegen tool (documented in the FastAPI migration
   runbook). No tool-selection decision is deferred.
3. The `specify_cli/charter_lint/` package already exists and contains the decay-watch
   domain logic that `LintService` will wrap.
4. SSE events are scoped to mission status changes and WP lane transitions — the data
   that the dashboard currently obtains by polling `/api/missions` and
   `/api/missions/{id}/status`.
5. The architectural test `test_dashboard_boundary.py` currently asserts "no
   `specify_cli.dashboard.*` imports inside `src/dashboard/`". That test is extended
   in this mission but not replaced.

---

## User Scenarios and Testing

### Scenario A — Dashboard drops polling for mission state

The dashboard client, on page load, opens an SSE connection to
`/api/events/missions`. When a WP lane changes (e.g., `planned → in_progress`), the
server pushes a structured event. The UI updates the kanban tile without waiting for
the next poll cycle. On connection loss, the client reconnects using the
`Last-Event-ID` header to resume from the last acknowledged event.

**Edge cases**:
- No missions exist: stream opens, server sends a `connected` keepalive, no data events.
- Client disconnects mid-stream: server closes the generator cleanly; no error logged.
- Concurrent connections from multiple browser tabs: each gets an independent stream.

### Scenario B — Glossary health tile via domain service

A developer adds a new glossary term. `GET /api/glossary-health` returns an updated
`total_terms` count. The router body is ≤ 15 LOC and contains no business logic; it
delegates entirely to `GlossaryService.get_health(project_dir)`.

### Scenario C — Lint tile via domain service

A CI job writes a new `lint-report.json`. `GET /api/charter-lint` reflects the
updated counts. The router delegates to `LintService.get_decay_watch_tile(project_dir)`.

### Scenario D — Deprecated aliases return 410 Gone

A consumer that still calls `GET /api/features` receives HTTP `410 Gone` with a JSON
body pointing to `/api/missions`. No `200 OK` is returned. The OpenAPI document no
longer lists these paths; the snapshot test passes.

### Scenario E — TypeScript codegen produces typed bindings

Running the documented codegen command against the OpenAPI JSON snapshot produces a
`.d.ts` file with typed interfaces for every response model. The command is
exercisable in CI without a live server.

---

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | A `GlossaryService` class exists at `src/specify_cli/glossary/service.py` with public methods: `get_health(project_dir: Path) -> GlossaryHealthResponse` and `get_terms(project_dir: Path) -> list[GlossaryTermRecord]`, where both return types are defined in `src/specify_cli/glossary/types.py`. | Proposed |
| FR-002 | The FastAPI router `src/dashboard/api/routers/glossary.py` delegates `GET /api/glossary-health` and `GET /api/glossary-terms` exclusively to `GlossaryService`; each route handler body is ≤ 15 LOC; all `# TODO(follow-up)` markers referencing issue #954 are removed. | Proposed |
| FR-003 | A `LintService` class exists at `src/specify_cli/charter_lint/service.py` with public method: `get_decay_watch_tile(project_dir: Path) -> DecayWatchTileResponse`, where the return type is defined in `src/specify_cli/charter_lint/types.py`. | Proposed |
| FR-004 | The FastAPI router `src/dashboard/api/routers/lint.py` delegates `GET /api/charter-lint` exclusively to `LintService`; the route handler body is ≤ 15 LOC; all `# TODO(follow-up)` markers referencing issue #955 are removed. | Proposed |
| FR-005 | `GlossaryService` and `LintService` contain no imports from `fastapi`, `starlette`, or `pydantic`; they are usable by CLI and MCP consumers without pulling the web framework. | Proposed |
| FR-006 | The legacy `BaseHTTPRequestHandler` glossary handler (`src/specify_cli/dashboard/handlers/glossary.py`) and lint handler (`src/specify_cli/dashboard/handlers/lint.py`) either delegate to the new services or remain unchanged; they must not be deleted in this mission. | Proposed |
| FR-007 | `GET /api/features` returns HTTP `410 Gone` with JSON body `{"error": "endpoint_retired", "successor": "/api/missions"}` and is removed from the OpenAPI document. | Proposed |
| FR-008 | `GET /api/kanban/{feature_id}` returns HTTP `410 Gone` with JSON body `{"error": "endpoint_retired", "successor": "/api/missions/{id}/status"}` and is removed from the OpenAPI document. | Proposed |
| FR-009 | A `GET /api/events/missions` SSE endpoint exists on the FastAPI app streaming `text/event-stream` events of type `mission_status` with payload fields: `mission_id`, `mission_slug`, `wp_id`, `from_lane`, `to_lane`, `at` (ISO-8601). | Proposed |
| FR-010 | The SSE endpoint sends a `connected` keepalive event on initial connection and a periodic keepalive comment (`: keepalive`) at least every 30 seconds to prevent proxy timeouts. | Proposed |
| FR-011 | The SSE endpoint supports `Last-Event-ID` resumption: on reconnect with a valid `Last-Event-ID`, the server replays events that occurred after that event ID before resuming the live stream. | Proposed |
| FR-012 | The SSE event stream is scoped to read operations only; no mutation is triggered by establishing or consuming the stream. | Proposed |
| FR-013 | A `npx openapi-typescript` invocation against the spec-kitty OpenAPI JSON snapshot generates a valid `.d.ts` file covering all response models published under `/api/`. The command and snapshot path are documented in `src/dashboard/README.md`. | Proposed |
| FR-014 | The OpenAPI snapshot test is updated to reflect: removed alias paths (`/api/features`, `/api/kanban/{id}`), new `/api/events/missions` path (documented as SSE). | Proposed |
| FR-015 | The `kitty-specs/frontend-api-fastapi-openapi-migration-01KQN2JA/issue-matrix.md` rows for issues #954 and #955 are updated to `fixed`. | Proposed |
| FR-016 | `GlossaryHealthResponse` and `GlossaryTermRecord` TypedDicts are moved from `src/dashboard/api_types.py` to `src/specify_cli/glossary/types.py`; all callers (FastAPI routers, legacy `BaseHTTPRequestHandler` handlers, `dashboard/api/models.py`) update their imports to the new location; the definitions are **deleted** from `dashboard/api_types.py` (no shim left). | Proposed |
| FR-017 | `DecayWatchTileResponse` TypedDict is moved from `src/dashboard/api_types.py` to `src/specify_cli/charter_lint/types.py`; all callers update their imports; the definition is **deleted** from `dashboard/api_types.py` (no shim left). | Proposed |
| FR-018 | The Pydantic `GlossaryTermRecord`, `GlossaryHealthResponse`, and `DecayWatchTileResponse` models in `src/dashboard/api/models.py` are updated to derive their field definitions from the canonical TypedDicts in their new domain locations (i.e., the Pydantic models document their alignment, not duplicate the field list independently). | Proposed |
| FR-019 | All remaining TypedDicts in `src/dashboard/api_types.py` are migrated to their canonical locations (see Overview §DTO for categorisation). Truly cross-cutting types with no domain owner (`ErrorResponse`, `HealthResponse`, `ArtifactInfo`, `ArtifactDirectoryFile`, `ArtifactDirectoryResponse`, `SyncInfo`, `SyncTriggerSuccess`, `FileIntegrity`) move to `src/kernel/api_types.py`. Domain-correlated types move to their respective domain modules (e.g., `KanbanTaskData`, `KanbanStats`, `KanbanResponse` → `src/specify_cli/status/api_types.py`; `MissionRecord`, `MissionContext`, `WorktreeInfo`, `WorkflowStatus` → `src/specify_cli/missions/api_types.py`). Types that are unambiguously dashboard-presentation-only may remain or move to a `src/dashboard/api/presentation_types.py`; each must be justified in the research phase. All callers update imports. `src/dashboard/api_types.py` is deleted when empty. | Proposed |

---

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | `GlossaryService` methods produce output byte-identical to the current `_build_glossary_health()` and `_build_glossary_terms()` private helpers, verified by a parity test. | Zero diff on the existing golden-output test dataset | Proposed |
| NFR-002 | `LintService.get_decay_watch_tile()` produces output byte-identical to the current `_build_charter_lint()` private helper, verified by a parity test. | Zero diff on the existing golden-output test dataset | Proposed |
| NFR-003 | The SSE endpoint does not increase median latency for non-SSE requests by more than 5 ms under a 10-concurrent-client SSE load. | ≤ 5 ms increase | Proposed |
| NFR-004 | The SSE endpoint releases all resources within 2 seconds of the client disconnecting. | ≤ 2 s | Proposed |
| NFR-005 | All existing dashboard tests pass unchanged after alias retirement and service extraction. | 100% pass rate | Proposed |
| NFR-006 | Unit test coverage for `GlossaryService` and `LintService` is ≥ 90% line coverage. | ≥ 90% | Proposed |
| NFR-007 | The OpenAPI document produced after alias retirement contains no paths under `/api/features` or `/api/kanban/{id}`. Verified by the OpenAPI snapshot test. | Snapshot matches | Proposed |

---

## Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | `GlossaryService` and `LintService` **must** be placed in `src/specify_cli/glossary/service.py` and `src/specify_cli/charter_lint/service.py` respectively. Placing them in `src/dashboard/services/` is **forbidden** in this mission. (Rationale: Alphonso's assessment 2026-05-04 — corrects inverted dependency direction.) | Proposed |
| C-002 | No new domain services may be created inside `src/dashboard/services/` as part of this mission. Phase B migration of existing services is a separate follow-up. | Proposed |
| C-003 | `GlossaryService` and `LintService` must not import from `fastapi`, `starlette`, or `pydantic`. | Proposed |
| C-004 | The SSE endpoint must be a read-only surface: no request body accepted, no disk writes, no calls to `emit_status_transition()` or any mutation function. | Proposed |
| C-005 | The alias retirement endpoints must return `410 Gone`, not `301` or `308`. Redirects would silently succeed for legacy callers; a 410 forces them to notice and migrate. | Proposed |
| C-006 | The legacy `BaseHTTPRequestHandler` glossary and lint handlers (`src/specify_cli/dashboard/handlers/glossary.py`, `lint.py`) must continue to function correctly after this mission. Import-path updates (pointing to the new domain `types.py` locations) are permitted and required; behavioral or structural changes to those handlers are not in scope. | Proposed |
| C-007 | The `openapi-typescript` codegen step must be exercisable in CI without a live dashboard server, using the existing OpenAPI JSON snapshot file. | Proposed |
| C-008 | All new code must run under Python 3.11+ (existing project requirement). No new runtime dependencies may be added without a corresponding `pyproject.toml` entry and `uv.lock` update. | Proposed |
| C-009 | Domain-specific DTOs (TypedDicts used as return types by domain services) **must** be defined in the domain module, not in `dashboard/api_types.py` or `dashboard/api/models.py`. The dependency direction is one-way: `dashboard/api` imports from domain modules; domain modules must never import from `dashboard/`. The three TypedDicts in scope (FR-016, FR-017) are fully removed from `dashboard/api_types.py` — no shim re-exports permitted. | Proposed |
| C-010 | All TypedDicts in `dashboard/api_types.py` must be migrated to their canonical locations as part of this mission (FR-019). No type may remain in `dashboard/api_types.py` without explicit justification (dashboard-presentation-only, documented in `research.md`). No new TypedDicts may be added to `dashboard/api_types.py` in this mission. | Proposed |

---

## Key Entities

| Entity | Description | Location |
|--------|-------------|----------|
| `GlossaryService` | Application service: reads glossary term senses, computes health metrics, lists terms. Pydantic-free. | `src/specify_cli/glossary/service.py` (new) |
| `LintService` | Application service: reads `.kittify/lint-report.json`, returns decay-watch tile summary. Pydantic-free. | `src/specify_cli/charter_lint/service.py` (new) |
| `GlossaryHealthResponse` | TypedDict wire shape — **moved** to domain module; definition deleted from `dashboard/api_types.py`. | `src/specify_cli/glossary/types.py` (moved from `dashboard/api_types.py`) |
| `GlossaryTermRecord` | TypedDict wire shape — **moved** to domain module; definition deleted from `dashboard/api_types.py`. | `src/specify_cli/glossary/types.py` (moved from `dashboard/api_types.py`) |
| `DecayWatchTileResponse` | TypedDict wire shape — **moved** to domain module; definition deleted from `dashboard/api_types.py`. | `src/specify_cli/charter_lint/types.py` (moved from `dashboard/api_types.py`) |
| `kernel/api_types.py` | New kernel module holding cross-cutting TypedDicts (`ErrorResponse`, `HealthResponse`, `ArtifactInfo`, etc.) after migration from `dashboard/api_types.py`. | `src/kernel/api_types.py` (new) |
| SSE event `mission_status` | JSON payload pushed on every WP lane transition. Fields: `mission_id`, `mission_slug`, `wp_id`, `from_lane`, `to_lane`, `at`. | New — defined in `src/dashboard/api/routers/events.py` |
| SSE event `connected` | Sent once on initial connection to confirm stream is live. | New — same router |
| OpenAPI TypeScript types | Static `.d.ts` generated from the OpenAPI JSON snapshot, committed for CI verification. | `src/dashboard/static/types/spec-kitty-api.d.ts` (new) |

---

## Success Criteria

1. All `# TODO(follow-up)` markers in `src/dashboard/api/routers/glossary.py` and
   `src/dashboard/api/routers/lint.py` are removed; those routers contain no inline
   business logic.
2. `GlossaryService` and `LintService` exist in their domain module locations and have
   ≥ 90% unit test coverage (NFR-006).
3. No module under `src/dashboard/api/routers/` imports directly from
   `specify_cli.glossary.*` or `specify_cli.charter_lint.*` — only via the service
   objects (C-001, C-003 verifiable by the architectural test). No domain module
   imports from `dashboard.*` (C-009, verifiable by an extension of the layer-rule test).
4. `GlossaryHealthResponse`, `GlossaryTermRecord`, and `DecayWatchTileResponse` exist
   in their canonical domain locations (`specify_cli/glossary/types.py` and
   `specify_cli/charter_lint/types.py`); the definitions are **absent** from
   `dashboard/api_types.py`; all callers import from the new locations (FR-016, FR-017).
5. `dashboard/api_types.py` is deleted (or contains only justified dashboard-presentation-only
   types documented in `research.md`); all cross-cutting and domain-correlated TypedDicts
   have been moved to `src/kernel/api_types.py` or their respective domain modules; all
   callers import from the new locations (FR-019, C-010).
6. `GET /api/features` and `GET /api/kanban/{id}` return `410 Gone`; both paths are
   absent from the OpenAPI document; the OpenAPI snapshot test passes (FR-007, FR-008,
   NFR-007).
7. `GET /api/events/missions` streams `text/event-stream` events; a new integration
   test asserts that a triggered status transition produces the expected event on the
   stream (FR-009).
8. A documented `npx openapi-typescript` command runs against the OpenAPI snapshot and
   produces a `.d.ts` file with zero TypeScript errors (FR-013).
9. All existing dashboard tests pass; CI Quality check is green (NFR-005).
10. The `issue-matrix.md` rows for #954 and #955 are marked `fixed` (FR-015).

---

## Dependencies

| Dependency | Type | Notes |
|------------|------|-------|
| Mission B (`resource-oriented-mission-api-01KQQRF2`) | Predecessor | Introduced `/api/missions` and `Deprecation` headers on aliases. Must be merged before alias retirement. |
| Mission A (`mission-registry-and-api-boundary-doctrine-01KQPDBB`) | Predecessor | Introduced `MissionRegistry` and `DIRECTIVE_API_DEPENDENCY_DIRECTION`. |
| `specify_cli.glossary` domain package | Runtime | `GlossaryService` wraps `GlossaryScope`, `load_seed_file`, `iter_semantic_conflicts`. Must remain stable. |
| `specify_cli.charter_lint` package | Runtime | `LintService` reads `.kittify/lint-report.json`. |
| `specify_cli.status` event log | Runtime | SSE endpoint tails the status event log to detect lane transitions. |
| `openapi-typescript` (npm) | Tooling | Added to `package.json` devDependencies or documented as an `npx` invocation. |

---

## Related Issues and Documents

- Epic: [#645](https://github.com/Priivacy-ai/spec-kitty/issues/645)
- Issue #954 glossary service extraction: [link](https://github.com/Priivacy-ai/spec-kitty/issues/954)
- Issue #955 lint service extraction: [link](https://github.com/Priivacy-ai/spec-kitty/issues/955)
- Alphonso's service placement assessment: `architecture/2.x/initiatives/2026-05-stable-application-api-surface/api-service-placement-assessment.md`
- Initiative README: `architecture/2.x/initiatives/2026-05-stable-application-api-surface/README.md`
- ADR (resource-oriented API): `architecture/2.x/adr/2026-05-03-2-resource-oriented-mission-api.md`
- Issue matrix: `kitty-specs/frontend-api-fastapi-openapi-migration-01KQN2JA/issue-matrix.md`
