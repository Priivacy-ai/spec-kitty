# Tasks: API Surface Completion — Domain Services, Alias Retirement, Async Transport

**Mission**: `api-surface-completion-services-aliases-async-01KQSXDA`  
**Branch**: `feature/645-api-surface-completion-mission-c`  
**Generated**: 2026-05-04T17:07:04Z

---

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Create `src/specify_cli/glossary/types.py` | WP01 | No — foundation | [D] |
| T002 | Create `src/specify_cli/charter_lint/types.py` | WP01 | No — foundation | [D] |
| T003 | Create `src/kernel/api_types.py` | WP01 | No — foundation | [D] |
| T004 | Create `src/specify_cli/status/api_types.py` | WP01 | No — foundation | [D] |
| T005 | Create `src/specify_cli/missions/api_types.py` | WP01 | No — foundation | [D] |
| T006 | Create `src/dashboard/api/presentation_types.py` | WP01 | No — foundation | [D] |
| T007 | Verify mypy --strict passes on all six new files | WP01 | No — validation | [D] |
| T008 | Create `src/specify_cli/glossary/service.py` (GlossaryService) | WP02 | After WP01 | [D] |
| T009 | Update `src/dashboard/api/routers/glossary.py` to delegate to GlossaryService | WP02 | After WP01 | [D] |
| T010 | Update `src/specify_cli/dashboard/handlers/glossary.py` imports | WP02 | After WP01 | [D] |
| T011 | Update `src/dashboard/api/models.py` Pydantic model alignment (FR-018) | WP02 | After WP01 | [D] |
| T012 | Write `tests/specify_cli/glossary/test_glossary_service.py` | WP02 | After WP01 | [D] |
| T013 | Create `src/specify_cli/charter_lint/service.py` (LintService) | WP03 | After WP01, parallel with WP02 | [D] |
| T014 | Update `src/dashboard/api/routers/lint.py` to delegate to LintService | WP03 | After WP01 | [D] |
| T015 | Update `src/specify_cli/dashboard/handlers/lint.py` imports | WP03 | After WP01 | [D] |
| T016 | Write `tests/specify_cli/charter_lint/test_lint_service.py` | WP03 | After WP01 | [D] |
| T017 | Add `_gone_response()` helper in `src/dashboard/api/routers/features.py` | WP04 | Independent | [D] |
| T018 | Retire `GET /api/features` with HTTP 410 | WP04 | Independent | [D] |
| T019 | Retire `GET /api/kanban/{feature_id}` with HTTP 410 | WP04 | Independent | [D] |
| T020 | Update `tests/test_dashboard/test_deprecation_headers.py` | WP04 | Independent | [D] |
| T021 | Run `pytest tests/test_dashboard/` to confirm 410 and no regressions | WP04 | Independent | [D] |
| T022 | Update `src/dashboard/services/mission_scan.py` imports | WP05 | After WP01, parallel with WP02/03/04 | [D] |
| T023 | Update `src/dashboard/services/project_state.py` imports | WP05 | After WP01 | [D] |
| T024 | Update `src/dashboard/services/registry.py` imports | WP05 | After WP01 | [D] |
| T025 | Update `src/dashboard/file_reader.py` imports | WP05 | After WP01 | [D] |
| T026 | Update or delete `src/specify_cli/dashboard/api_types.py` shim | WP05 | After WP01 | [D] |
| T027 | Update `src/dashboard/api/routers/health.py` imports | WP06 | After WP01, parallel with WP02/03/04/05 | [D] |
| T028 | Update `src/dashboard/api/routers/diagnostics.py` imports | WP06 | After WP01 | [D] |
| T029 | Update `src/dashboard/api/routers/sync.py` imports | WP06 | After WP01 | [D] |
| T030 | Update `src/dashboard/api/routers/artifacts.py` imports | WP06 | After WP01 | [D] |
| T031 | Update `src/dashboard/api/routers/missions.py` imports | WP06 | After WP01 | [D] |
| T032 | Audit remaining routers for any stray `dashboard.api_types` imports | WP06 | After WP01 | [D] |
| T033 | Confirm zero `dashboard.api_types` references remain in `src/` and `tests/` | WP07 | After WP02–WP06 | [D] |
| T034 | Delete `src/dashboard/api_types.py`; run targeted pytest suite | WP07 | After WP02–WP06 | [D] |
| T035 | Extend architectural boundary test to enforce no-reverse imports | WP07 | After WP02–WP06 | [D] |
| T036 | Run full test suite; confirm green | WP07 | After WP02–WP06 | [D] |
| T037 | Create `src/dashboard/api/routers/events.py` with router and route | WP08 | Independent | [D] |
| T038 | Implement SSE async generator `_stream_mission_events` | WP08 | Independent | [D] |
| T039 | Implement keepalive comment every 15 seconds | WP08 | Independent | [D] |
| T040 | Implement `Last-Event-ID` header handling and ULID resumption | WP08 | Independent | [D] |
| T041 | Register events router in `src/dashboard/api/__init__.py` | WP08 | Independent | [D] |
| T042 | Write `tests/test_dashboard/test_sse_endpoint.py` | WP08 | Independent | [D] |
| T043 | Regenerate `tests/test_dashboard/snapshots/openapi.json` | WP09 | After WP04, WP07, WP08 | [D] |
| T044 | Run `npx openapi-typescript` and commit `src/dashboard/static/ts/api.d.ts` | WP09 | After WP04, WP07, WP08 | [D] |
| T045 | Update `src/dashboard/README.md` with TypeScript API Types section | WP09 | After WP04, WP07, WP08 | [D] |
| T046 | Update `test_openapi_snapshot.py` assertions for retired paths | WP09 | After WP04, WP07, WP08 | [D] |
| T047 | Run `test_typeddict_pydantic_parity.py`; fix imports if needed | WP09 | After WP04, WP07, WP08 | [D] |
| T048 | Update `issue-matrix.md` — mark #954 and #955 fixed | WP09 | After WP04, WP07, WP08 | [D] |

---

## Work Package Summary

**WP01 — TypedDict Type Module Foundation** creates the six new canonical type modules that every subsequent WP depends on. The work is purely additive — no existing files are touched. The critical risk is that mypy --strict must pass in isolation before any callers are updated.

**WP02 — GlossaryService Extraction + Pydantic Alignment** extracts the glossary router's private helpers into a proper domain service, delegates the FastAPI router, and aligns the Pydantic models in `models.py` with their canonical TypedDicts. The key risk is parity: the service output must match the existing handler output byte-for-byte (NFR-001).

**WP03 — LintService Extraction** mirrors WP02 for the charter-lint domain. It extracts `_build_charter_lint` into a `LintService` class with `get_decay_tile()`, delegates the lint router, and updates imports. Can run in parallel with WP02 after WP01 completes.

**WP04 — Alias Retirement** retires `GET /api/features` and `GET /api/kanban/{feature_id}` with HTTP 410 Gone, removes them from the OpenAPI schema, and updates deprecation tests. Intentionally independent of WP02/03 — can proceed in parallel.

**WP05 — Dashboard Services Import Migration** updates all callers in `dashboard/services/` and `dashboard/file_reader.py` to import from the new canonical type locations established in WP01. Also resolves the legacy `specify_cli/dashboard/api_types.py` shim. Can run in parallel with WP02/03/04.

**WP06 — Dashboard API Router Import Migration** updates the remaining FastAPI routers (health, diagnostics, sync, artifacts, missions) that still import from `dashboard.api_types`. WP04 owns features.py/kanban.py; WP02 owns glossary.py; WP03 owns lint.py. This WP handles everything else. Can run in parallel with WP02/03/04/05.

**WP07 — api_types.py Deletion + Architectural Boundary Test** is the convergence gate. It confirms zero remaining references to `dashboard.api_types`, deletes the file, extends the architectural test to enforce the one-way dependency direction, and confirms the full test suite is green.

**WP08 — SSE Endpoint** creates `GET /api/events/missions` as a Server-Sent Events stream using Starlette's built-in `StreamingResponse` (zero new deps). The endpoint supports keepalive comments, `Last-Event-ID` resumption, and read-only semantics (C-004). Intentionally independent — can run in parallel with all other WPs.

**WP09 — OpenAPI Snapshot + TypeScript Codegen + Issue Matrix** is the final delivery gate. It regenerates the OpenAPI snapshot after all route changes, runs `npx openapi-typescript` to produce `api.d.ts`, documents the pipeline in the dashboard README, and closes out the issue matrix. Depends on WP04 (retired routes), WP07 (deleted api_types), and WP08 (SSE route).

---

## WP01 — TypedDict Type Module Foundation

**Priority:** P0 · **Size:** ~360 lines · **Dependencies:** none

**Goal:** Create all six new type modules that define the canonical locations for every TypedDict moving out of `src/dashboard/api_types.py`. No callers are updated yet — this WP is purely additive.

**Included subtasks:**
- [x] T001 Create `src/specify_cli/glossary/types.py` (WP01)
- [x] T002 Create `src/specify_cli/charter_lint/types.py` (WP01)
- [x] T003 Create `src/kernel/api_types.py` (WP01)
- [x] T004 Create `src/specify_cli/status/api_types.py` (WP01)
- [x] T005 Create `src/specify_cli/missions/api_types.py` (WP01)
- [x] T006 Create `src/dashboard/api/presentation_types.py` (WP01)
- [x] T007 Verify mypy passes on new modules (WP01)

**Implementation sketch:** Each file is a standalone module with `from __future__ import annotations`, appropriate `typing` imports, and TypedDict classes with docstrings. The `missions/api_types.py` file cross-references `status/api_types.py` for `KanbanStats`. The `kernel/` package already exists — just add the file.

**Parallelization:** WP02, WP03, WP04, WP05, WP06, and WP08 can all start once WP01 is merged to the lane branch.

**Risks:** If a TypedDict field is missed or typed incorrectly, downstream WPs (especially WP07's mypy gate) will surface it. Mitigation: copy field definitions directly from `data-model.md` which has the authoritative canonical form.

---

## WP02 — GlossaryService Extraction + Pydantic Alignment

**Priority:** P1 · **Size:** ~280 lines · **Dependencies:** WP01

**Goal:** Extract the glossary router's private helpers into `GlossaryService`; delegate the router; align Pydantic models with the canonical TypedDicts (FR-018); write parity tests.

**Included subtasks:**
- [x] T008 Create `src/specify_cli/glossary/service.py` (WP02)
- [x] T009 Update `src/dashboard/api/routers/glossary.py` (WP02)
- [x] T010 Update `src/specify_cli/dashboard/handlers/glossary.py` imports (WP02)
- [x] T011 Update `src/dashboard/api/models.py` Pydantic alignment (WP02)
- [x] T012 Write `tests/specify_cli/glossary/test_glossary_service.py` (WP02)

**Implementation sketch:** `GlossaryService.__init__` stores `project_dir`; `get_health()` replicates `_build_glossary_health`; `get_terms()` replicates `_build_glossary_terms`. The router delegates to the service with no logic of its own (≤ 15 LOC per handler). The legacy HTTP handler's import path is updated to match.

**Parallelization:** Can start immediately after WP01; runs independently of WP03/04/05/06/08.

**Risks:** Parity with the existing router logic is critical (NFR-001). Mitigation: the parity test in T012 uses the same golden data to verify output matches the original private helpers.

---

## WP03 — LintService Extraction

**Priority:** P1 · **Size:** ~200 lines · **Dependencies:** WP01

**Goal:** Extract `_build_charter_lint` from the lint router into `LintService.get_decay_tile()`; delegate the router; update imports; write parity tests.

**Included subtasks:**
- [x] T013 Create `src/specify_cli/charter_lint/service.py` (WP03)
- [x] T014 Update `src/dashboard/api/routers/lint.py` (WP03)
- [x] T015 Update `src/specify_cli/dashboard/handlers/lint.py` imports (WP03)
- [x] T016 Write `tests/specify_cli/charter_lint/test_lint_service.py` (WP03)

**Implementation sketch:** `LintService.__init__` stores `project_dir`; `get_decay_tile()` reads `.kittify/lint-report.json` and returns `DecayWatchTileResponse`. When the file is absent, returns the zero-count empty response. No fastapi/pydantic imports anywhere in the service.

**Parallelization:** Parallel with WP02 (different files).

**Risks:** The JSON schema of `lint-report.json` must match what the research.md documents. Use `tmp_path` in tests to avoid dependency on real disk state.

---

## WP04 — Alias Retirement

**Priority:** P1 · **Size:** ~80 lines · **Dependencies:** none

**Goal:** Retire `/api/features` and `/api/kanban/{feature_id}` with HTTP 410 Gone; remove from OpenAPI schema; update tests.

**Included subtasks:**
- [x] T017 Add `_gone_response()` helper in features.py (WP04)
- [x] T018 Retire `GET /api/features` (WP04)
- [x] T019 Retire `GET /api/kanban/{feature_id}` (WP04)
- [x] T020 Update `test_deprecation_headers.py` (WP04)
- [x] T021 Run `pytest tests/test_dashboard/` (WP04)

**Implementation sketch:** The `_gone_response(deprecated_path, successor_path)` helper returns `JSONResponse(status_code=410, content={"error": "endpoint_retired", "successor": successor_path})`. Both routes gain `include_in_schema=False`. All `Deprecation`/`Link` headers are removed. Tests are updated to assert 410 status and the `endpoint_retired` body.

**Parallelization:** Fully independent of WP02/03/05/06/08.

**Risks:** Existing integration tests that assert 200 or `Deprecation: true` on these routes will break intentionally. The test update (T020) is the critical step.

---

## WP05 — Dashboard Services Import Migration

**Priority:** P1 · **Size:** ~120 lines changed · **Dependencies:** WP01

**Goal:** Update all callers in `dashboard/services/` and `dashboard/file_reader.py` to import from new canonical type locations; resolve the legacy shim.

**Included subtasks:**
- [x] T022 Update `src/dashboard/services/mission_scan.py` (WP05)
- [x] T023 Update `src/dashboard/services/project_state.py` (WP05)
- [x] T024 Update `src/dashboard/services/registry.py` (WP05)
- [x] T025 Update `src/dashboard/file_reader.py` (WP05)
- [x] T026 Update or delete `src/specify_cli/dashboard/api_types.py` shim (WP05)

**Implementation sketch:** For each file, replace `from dashboard.api_types import X` with the import from the canonical location determined by the categorisation table in `research.md`. Run mypy after each file change to catch missed types.

**Parallelization:** Parallel with WP02/03/04/06/08.

**Risks:** If any type was missed in WP01's migration categorisation, mypy will surface it here. Mitigation: always run mypy per-file as each import is updated.

---

## WP06 — Dashboard API Router Import Migration (Non-Primary)

**Priority:** P1 · **Size:** ~60 lines changed · **Dependencies:** WP01

**Goal:** Update import statements in the remaining FastAPI routers (health, diagnostics, sync, artifacts, missions) that still import from `dashboard.api_types`.

**Included subtasks:**
- [x] T027 Update `src/dashboard/api/routers/health.py` (WP06)
- [x] T028 Update `src/dashboard/api/routers/diagnostics.py` (WP06)
- [x] T029 Update `src/dashboard/api/routers/sync.py` (WP06)
- [x] T030 Update `src/dashboard/api/routers/artifacts.py` (WP06)
- [x] T031 Update `src/dashboard/api/routers/missions.py` (WP06)
- [x] T032 Audit remaining routers for stray imports (WP06)

**Implementation sketch:** Mechanical import substitution per the categorisation table. Each router imports only from its domain's canonical location. T032 runs a grep audit to confirm completeness before WP07 proceeds.

**Parallelization:** Parallel with WP02/03/04/05/08.

**Risks:** A missed import in this WP will block WP07's deletion step. Mitigation: T032's grep audit catches any stragglers.

---

## WP07 — api_types.py Deletion + Architectural Boundary Test

**Priority:** P2 · **Size:** ~100 lines · **Dependencies:** WP02, WP03, WP04, WP05, WP06

**Goal:** Delete `src/dashboard/api_types.py`; extend the architectural boundary test; confirm the full test suite is green.

**Included subtasks:**
- [x] T033 Confirm zero `dashboard.api_types` references (WP07)
- [x] T034 Delete `src/dashboard/api_types.py`; run targeted tests (WP07)
- [x] T035 Extend `tests/architectural/test_dashboard_boundary.py` (WP07)
- [x] T036 Run full test suite (WP07)

**Implementation sketch:** T033 uses grep to confirm zero references. T034 deletes the file and runs the dashboard + specify_cli test suites to confirm no import errors. T035 adds an assertion that no module under `src/specify_cli/` or `src/kernel/` imports from `src/dashboard/`. T036 runs the entire test suite.

**Parallelization:** Convergence gate — must run after all of WP02–WP06.

**Risks:** A missed caller anywhere in the codebase will produce an `ImportError` at test time. Mitigation: T033's grep audit runs before deletion.

---

## WP08 — SSE Endpoint

**Priority:** P1 · **Size:** ~250 lines · **Dependencies:** none

**Goal:** Create `GET /api/events/missions` as a Server-Sent Events stream using Starlette's built-in `StreamingResponse`. Keepalive, `Last-Event-ID` resumption, read-only semantics.

**Included subtasks:**
- [x] T037 Create `src/dashboard/api/routers/events.py` (WP08)
- [x] T038 Implement SSE async generator `_stream_mission_events` (WP08)
- [x] T039 Implement keepalive comment every 15 seconds (WP08)
- [x] T040 Implement `Last-Event-ID` header handling (WP08)
- [x] T041 Register events router in `src/dashboard/api/__init__.py` (WP08)
- [x] T042 Write `tests/test_dashboard/test_sse_endpoint.py` (WP08)

**Implementation sketch:** `StreamingResponse(media_type="text/event-stream")` wrapping an async generator. Poll `status.events.jsonl` every 2 s with `asyncio.sleep`. Send `: keepalive\n\n` if no events in 15 s. Read `Last-Event-ID` header; skip events whose `event_id` ≤ the provided ULID. Zero new dependencies.

**Parallelization:** Fully independent — can start at the same time as WP01.

**Risks:** Resource leak on client disconnect. Mitigation: the async generator must not hold open file handles between `yield` points — use `Path.read_text()` within each tick.

---

## WP09 — OpenAPI Snapshot + TypeScript Codegen + Issue Matrix

**Priority:** P2 · **Size:** ~120 lines · **Dependencies:** WP04, WP07, WP08

**Goal:** Regenerate the OpenAPI snapshot; run `npx openapi-typescript`; update snapshot test assertions; update the issue matrix.

**Included subtasks:**
- [x] T043 Regenerate `tests/test_dashboard/snapshots/openapi.json` (WP09)
- [x] T044 Run codegen and commit `src/dashboard/static/ts/api.d.ts` (WP09)
- [x] T045 Update `src/dashboard/README.md` with TypeScript API Types section (WP09)
- [x] T046 Update `test_openapi_snapshot.py` assertions (WP09)
- [x] T047 Run `test_typeddict_pydantic_parity.py`; fix imports if needed (WP09)
- [x] T048 Update `issue-matrix.md` — mark #954 and #955 fixed (WP09)

**Implementation sketch:** Regenerate snapshot by calling `app.openapi()` and writing to the snapshot file. Run `npx openapi-typescript` against the new snapshot. Assert retired paths are absent. Assert SSE endpoint is present (or explicitly not present if excluded from schema).

**Parallelization:** Convergence gate after WP04, WP07, and WP08.

**Risks:** `npx openapi-typescript` may not be installed. Mitigation: document the install step in README; test with `--dry-run` if available.
