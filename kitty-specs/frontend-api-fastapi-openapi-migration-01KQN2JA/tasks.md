# Tasks — Frontend API FastAPI/OpenAPI Migration

**Mission**: `frontend-api-fastapi-openapi-migration-01KQN2JA`
**Branch**: `feature/650-dashboard-ui-ux-overhaul`
**Spec / Plan**: [spec.md](./spec.md) · [plan.md](./plan.md) · [research.md](./research.md) · [data-model.md](./data-model.md) · [contracts/](./contracts/)

## Subtask Index

| ID   | Description | WP   | Parallel |
|------|-------------|------|----------|
| T001 | Draft ADR `2026-05-02-2-fastapi-openapi-transport.md` (Decision, Rationale, Consequences, Rejected Alternatives, Future Work § MCP exposure sketch) | WP01 | — | [D] |
| T002 | Add Dashboard slice entries for `src/dashboard/api/` and `src/dashboard/api/models.py` to `architecture/2.x/05_ownership_map.md` | WP01 | — | [D] |
| T003 | Mirror entries in `architecture/2.x/05_ownership_manifest.yaml` (`dashboard.adapter_responsibilities` updated) | WP01 | — | [D] |
| T004 | Author `docs/migration/dashboard-fastapi-transport.md` runbook (config flag, rollback, known behavior diffs, fallback procedure) | WP01 | [D] |
| T005 | Add `fastapi`, `uvicorn[standard]` to `pyproject.toml` `[project] dependencies`; `uv sync --upgrade-package fastapi`; verify Pydantic v2 in lockfile | WP02 | — | [D] |
| T006 | Create `src/dashboard/api/__init__.py`, `src/dashboard/api/app.py` with `create_app(project_dir, project_token) -> FastAPI` factory; mount StaticFiles for `/static/dashboard/*`; register OpenAPI metadata (title, version) | WP02 | — | [D] |
| T007 | Create `src/dashboard/api/deps.py` with `verify_project_token` Depends and any DI getters needed by routers (project_dir, services factories) | WP02 | — | [D] |
| T008 | Create `src/dashboard/api/errors.py` with `register_exception_handlers(app)` that maps service-layer errors to JSON error payloads | WP02 | [D] |
| T009 | Modify `src/specify_cli/dashboard/server.py` to read `dashboard.transport` config and dispatch to legacy or FastAPI stack via Uvicorn programmatic API | WP02 | — | [D] |
| T010 | Add `--transport {legacy,fastapi}` Typer option to `spec-kitty dashboard` in `src/specify_cli/cli/commands/dashboard.py`; CLI flag overrides config. **Also add a `--bench-exit-after-first-byte` hidden flag** consumed by the benchmark script in WP06 (T029); without it the benchmark cannot measure cold-start to first-byte | WP02 | — | [D] |
| T011 | Create `src/dashboard/api/models.py` with Pydantic v2 BaseModels for every TypedDict in `src/dashboard/api_types.py` (mirror names, mirror fields) | WP03 | — | [D] |
| T012 | Define discriminated union response for `/api/sync/trigger` (Scheduled, Skipped, Unavailable, Failed) | WP03 | — | [D] |
| T013 | Add adapter test `tests/test_dashboard/test_typeddict_pydantic_parity.py` that constructs Pydantic instances from TypedDict literals and asserts JSON shape match | WP03 | [D] |
| T014 | Implement `src/dashboard/api/routers/features.py` (GET /api/features) | WP04 | — | [D] |
| T015 | Implement `src/dashboard/api/routers/kanban.py` (GET /api/kanban/{feature_id}) | WP04 | [D] |
| T016 | Implement `src/dashboard/api/routers/artifacts.py` (research, contracts, checklists, artifact — 7 endpoints) | WP04 | [D] |
| T017 | Implement `src/dashboard/api/routers/health.py` + `routers/sync.py` + `routers/shutdown.py` | WP04 | [D] |
| T018 | Implement `src/dashboard/api/routers/charter.py` + `routers/diagnostics.py` (thin wrappers — both already thin in the legacy handler) | WP04 | — | [D] |
| T019 | Implement `src/dashboard/api/routers/dossier.py` (4 sub-routes; passes `mission_slug` query param through to existing `DossierAPIHandler`) | WP04 | [D] |
| T020 | Implement `src/dashboard/api/routers/glossary.py` + `routers/lint.py` as transport-only migrations (call into existing handler-layer logic via small adapter funcs); add `# TODO(follow-up)` markers per route | WP04 | [D] |
| T021 | Implement `src/dashboard/api/routers/static_mount.py` for `GET /` returning the rendered HTML shell; mount `/static/dashboard/*` static files | WP04 | [D] |
| T022 | Wire all routers into `app.py` via `app.include_router(...)`; ensure trailing-slash redirect is OFF (`redirect_slashes=False`) | WP04 | — | [D] |
| T023 | Author `tests/test_dashboard/test_transport_parity.py` — parametrized over the route inventory; per route, runs the same fixture project through both legacy and FastAPI and asserts JSON parity | WP05 | — | [D] |
| T024 | Author `tests/test_dashboard/test_openapi_snapshot.py` (golden snapshot) + `tests/test_dashboard/snapshots/openapi.json` (initial commit) | WP05 | — | [D] |
| T025 | Author `tests/test_dashboard/test_openapi_validity.py` — uses `openapi_spec_validator` to assert the doc is valid OpenAPI 3.x | WP05 | [D] |
| T026 | Author `tests/architectural/test_fastapi_handler_purity.py` — AST-scans `src/dashboard/api/routers/` for `fastapi.Response` / `starlette.Response` writes inside route function bodies | WP05 | [D] |
| T027 | Update `tests/architectural/test_dashboard_boundary.py` so `src/dashboard/api/` is allowed to import from `dashboard.services.*`, `dashboard.api.models`, `dashboard.api_types`, `dashboard.file_reader`; `src/specify_cli/dashboard/*` import remains forbidden | WP05 | [D] |
| T028 | Author `tests/test_dashboard/test_fastapi_app.py` — unit tests for `create_app` factory, deps, error handlers (FastAPI `TestClient`-based) | WP05 | [D] |
| T029 | Author `scripts/bench_dashboard_startup.py` — measures cold-start p50 for both stacks; writes results to a JSON file the release-checklist references | WP06 | — | [D] |
| T030 | Run NFR-001 / NFR-002 benchmarks locally; record numbers in `kitty-specs/frontend-api-fastapi-openapi-migration-01KQN2JA/release-checklist.md` (created by T031) | WP06 | — | [D] |
| T031 | Author `kitty-specs/frontend-api-fastapi-openapi-migration-01KQN2JA/release-checklist.md` with SC-006 verification slots, benchmark numbers slot, and rollback verification slot | WP06 | [D] |
| T032 | Run the full test suite; confirm zero regressions in `tests/test_dashboard/`, `tests/architectural/`, `tests/sync/` | WP06 | — | [D] |
| T033 | Update `kitty-specs/frontend-api-fastapi-openapi-migration-01KQN2JA/spec.md` checkbox status for FRs that map to user-visible signals (no code change; book-keeping only) | WP06 | [D] |

## Dependencies

```
WP01 (governance) ──┬──▶ WP02 (transport scaffold)
                    │
                    └──▶ WP05 (architectural tests benefit from updated boundary doc)

WP02 (transport scaffold) ──▶ WP03 (response models — needs app to register)
                          ──▶ WP04 (routers — need app + deps)

WP03 (models) ──▶ WP04

WP04 ──▶ WP05 (parity / snapshot / handler-purity tests)
     ──▶ WP06 (benchmark + release checklist + final QA)

WP05 ──▶ WP06 (benchmark must run after parity is green)
```

## Work Packages

### WP01 — Governance: ADR, ownership map, runbook

**Goal**: Land the governance artifacts before any code change so DIRECTIVE_024 (Locality of Change) compliance is auditable from the start.

**Priority**: P0
**Independent test**: Reviewer reads ownership map, ADR, and runbook in isolation and can answer "what is the dashboard transport layer about to become, why, and how do I roll back" without opening any code.

**Subtasks**:
- [x] T001 Draft ADR `2026-05-02-2-fastapi-openapi-transport.md`
- [x] T002 Update `architecture/2.x/05_ownership_map.md`
- [x] T003 Update `architecture/2.x/05_ownership_manifest.yaml`
- [x] T004 Author `docs/migration/dashboard-fastapi-transport.md`

**Implementation sketch**:
1. Write the ADR following the existing 2026-05-02-1 ADR structure (Context / Decision / Rationale / Consequences / Rejected Alternatives).
2. Add a Future Work § showing how an MCP adapter would re-use a FastAPI route handler (single-paragraph sketch + 10-line code example).
3. Update the Dashboard slice in the ownership map: add `src/dashboard/api/` and `src/dashboard/api/models.py` to `current_state` (or a new `target_state` field if that's the convention); update `adapter_responsibilities` so it lists FastAPI app construction and route registration; cross-link the ADR.
4. Mirror the changes in the YAML manifest.
5. Author the migration runbook covering: config flag, CLI flag, default value per release, rollback procedure, known behavior differences (trailing slash, header casing).

**Risks**: governance drift between map and manifest. Mitigation: schema test (`test_ownership_manifest_schema.py`) catches structural drift; manual review of map vs manifest catches text drift.

**Owned files**: `architecture/2.x/05_ownership_map.md`, `architecture/2.x/05_ownership_manifest.yaml`, `architecture/2.x/adr/2026-05-02-2-fastapi-openapi-transport.md`, `docs/migration/dashboard-fastapi-transport.md`.

### WP02 — Transport scaffold: deps, app factory, strangler boundary

**Goal**: Stand up the FastAPI app skeleton + the strangler boundary so subsequent WPs can plug routers and models in.

**Priority**: P0
**Independent test**: `spec-kitty dashboard --transport fastapi` starts the app; `curl http://127.0.0.1:<port>/openapi.json` returns a valid OpenAPI doc with zero routes (or only static mount).

**Subtasks**:
- [x] T005 Add `fastapi`, `uvicorn[standard]` to `pyproject.toml`
- [x] T006 Create `src/dashboard/api/__init__.py`, `src/dashboard/api/app.py`
- [x] T007 Create `src/dashboard/api/deps.py`
- [x] T008 Create `src/dashboard/api/errors.py`
- [x] T009 Modify `src/specify_cli/dashboard/server.py` for strangler dispatch
- [x] T010 Add `--transport` flag to `spec-kitty dashboard`

**Implementation sketch**:
1. Add deps: `uv add fastapi uvicorn[standard]`. Confirm Pydantic v2 is resolved.
2. App factory: `create_app(project_dir: Path, project_token: str | None) -> FastAPI`. Set `redirect_slashes=False`. Register CORS only for `127.0.0.1` (defensive). Stash `project_dir` and `project_token` on `app.state`.
3. `verify_project_token` dependency function reads `request.app.state.project_token` and compares to `?token=` query param; raises `HTTPException(403)` on mismatch.
4. `errors.py` adds an `Exception` handler that converts service-layer `RuntimeError("dashboard project_dir is not configured")` into a 500 with the same JSON shape the legacy stack returns.
5. Strangler boundary: read `dashboard.transport` from `.kittify/config.yaml`; `--transport` CLI flag wins. Run via `uvicorn.Server(uvicorn.Config(app, host=..., port=..., log_level="warning"))` for FastAPI; legacy code path unchanged.
6. CLI flag in `src/specify_cli/cli/commands/dashboard.py`.

**Risks**: dependency resolution conflicts. Mitigation: run full test suite after `uv sync`.

**Owned files**: `pyproject.toml`, `uv.lock`, `src/dashboard/api/__init__.py`, `src/dashboard/api/app.py`, `src/dashboard/api/deps.py`, `src/dashboard/api/errors.py`, `src/specify_cli/dashboard/server.py`, `src/specify_cli/cli/commands/dashboard.py`.

### WP03 — Pydantic response models

**Goal**: Define every Pydantic model the routers need.

**Priority**: P0
**Independent test**: `tests/test_dashboard/test_typeddict_pydantic_parity.py` passes — every TypedDict in `dashboard.api_types` round-trips through its Pydantic counterpart with byte-equivalent JSON.

**Subtasks**:
- [x] T011 Create `src/dashboard/api/models.py`
- [x] T012 Discriminated union for `SyncTriggerResponse`
- [x] T013 Adapter test `test_typeddict_pydantic_parity.py`

**Implementation sketch**:
1. One Pydantic class per TypedDict; same name; field types mirrored (`Optional[T]` → `T | None = None`).
2. Discriminated union: use `Field(discriminator="status")` only on the responses that have a status field; for the variant that returns `{"error": ...}` use the `error` field as discriminator (or omit the discriminator and let FastAPI emit `oneOf`).
3. Parity test: for each TypedDict, write a literal that satisfies its shape; instantiate the equivalent Pydantic model via `Model.model_validate(literal)`; assert `model.model_dump_json(sort_keys=True) == json.dumps(literal, sort_keys=True)`.

**Risks**: TypedDict shapes that include `Any` or unbounded dicts (e.g., `KanbanResponse.lanes: dict[str, list[Any]]`) are hard to model strictly in Pydantic; use `dict[str, list[Any]]` directly. Lint will complain about `Any` but the alternative is over-tightening.

**Owned files**: `src/dashboard/api/models.py`, `tests/test_dashboard/test_typeddict_pydantic_parity.py`.

### WP04 — Routers: every dashboard route + wire-up

**Goal**: Migrate every dashboard route from legacy handlers to FastAPI APIRouters and wire them all into the app.

**Priority**: P0
**Independent test**: `curl http://127.0.0.1:<port>/openapi.json | jq '.paths | length' >= 14` AND `pytest tests/test_dashboard/test_transport_parity.py` passes for every parametrized route.

**Subtasks**:
- [x] T014 `routers/features.py`
- [x] T015 `routers/kanban.py`
- [x] T016 `routers/artifacts.py`
- [x] T017 `routers/health.py` + `routers/sync.py` + `routers/shutdown.py`
- [x] T018 `routers/charter.py` + `routers/diagnostics.py`
- [x] T019 `routers/dossier.py`
- [x] T020 `routers/glossary.py` + `routers/lint.py` (transport-only)
- [x] T021 `routers/static_mount.py`
- [x] T022 Wire all routers in `app.py`

**Implementation sketch**:
- Each router instantiates the corresponding service class (or uses a Depends factory) and returns the result. No HTTP-only side effects in the route function body (FR-009).
- Token validation for `/api/sync/trigger` and `/api/shutdown` via `Depends(verify_project_token)`.
- Path params come through FastAPI's path parser; no `path.split("/")` in the body.
- File-serving routes (`/api/research/{id}/{file}` etc.) return `PlainTextResponse(content=...)` — model-equivalent return for non-JSON content.
- Charter and diagnostics are thin wrappers — pull the existing helper out and call from the router.
- Dossier keeps using `DossierAPIHandler(repo_root)`; each sub-route is its own FastAPI route function; `mission_slug` is a typed query param.
- Glossary and lint migrate transport-only — copy the legacy handler logic into a private function in the router module. Add `# TODO(follow-up): extract glossary/lint service object` markers; file two follow-up issues at mission close.
- `static_mount` registers `app.mount("/static", StaticFiles(directory=...))` and `GET /` returning `HTMLResponse(content=get_dashboard_html_bytes())`.
- Wire-up: `app.include_router(...)` calls in alphabetical order in `app.py` for snapshot determinism.

**Owned files**: `src/dashboard/api/routers/{__init__,features,kanban,artifacts,health,sync,shutdown,charter,diagnostics,dossier,glossary,lint,static_mount}.py`.

### WP05 — Tests: parity suite, OpenAPI snapshot, handler-purity, app unit tests

**Goal**: Comprehensive test coverage for the migration so future drift is caught in CI.

**Priority**: P0
**Independent test**: Full test run is green; OpenAPI snapshot exists; parity suite covers every route in `contracts/route-inventory.md`.

**Subtasks**:
- [x] T023 `test_transport_parity.py`
- [x] T024 `test_openapi_snapshot.py` + `snapshots/openapi.json`
- [x] T025 `test_openapi_validity.py`
- [x] T026 `test_fastapi_handler_purity.py`
- [x] T027 update `test_dashboard_boundary.py`
- [x] T028 `test_fastapi_app.py`

**Implementation sketch**:
- Parity test: parametrize over `contracts/route-inventory.md`. For each route, build a `tmp_path` fixture project; spin up legacy via `urllib` against a real `BaseHTTPServer`; spin up FastAPI via `TestClient`; assert normalized JSON equivalence.
- Snapshot test: `json.dumps(app.openapi(), sort_keys=True, indent=2) + "\n"` vs committed snapshot.
- Validity test: `openapi_spec_validator.validate(app.openapi())`.
- Handler-purity test: AST-walk each `src/dashboard/api/routers/*.py`; for each FunctionDef decorated with `@router.<method>`, assert no node calls `Response(...)` or `JSONResponse(...)` directly inside the body. `PlainTextResponse` and `HTMLResponse` are allowed (they're the model-equivalent return for non-JSON content).
- Boundary test update: extend the existing import-walk to allow `src.dashboard.api` to import from `dashboard.services.*`, `dashboard.api.models`, `dashboard.api_types`, `dashboard.file_reader`; keep the `src.specify_cli.dashboard` exclusion.
- App unit tests: `TestClient`-based; exercise the deps, error handlers, app factory, OpenAPI metadata.

**Owned files**: `tests/test_dashboard/test_transport_parity.py`, `tests/test_dashboard/test_openapi_snapshot.py`, `tests/test_dashboard/snapshots/openapi.json`, `tests/test_dashboard/test_openapi_validity.py`, `tests/architectural/test_fastapi_handler_purity.py`, `tests/architectural/test_dashboard_boundary.py`, `tests/test_dashboard/test_fastapi_app.py`.

### WP06 — Benchmarks, release checklist, final QA

**Goal**: Verify NFRs locally, record results, and produce the release-readiness artifact for the branch.

**Priority**: P1
**Independent test**: `scripts/bench_dashboard_startup.py` runs and produces a numeric report; the report is committed to the mission's release-checklist; full test suite is green.

**Subtasks**:
- [x] T029 `scripts/bench_dashboard_startup.py`
- [x] T030 Run benchmarks; record numbers in release-checklist
- [x] T031 `kitty-specs/frontend-api-fastapi-openapi-migration-01KQN2JA/release-checklist.md`
- [x] T032 Run full test suite; confirm zero regressions
- [x] T033 Update spec FR checkbox status (book-keeping)

**Implementation sketch**:
- Benchmark: spawn `spec-kitty dashboard --transport <stack> --port <free>` with a `--bench-exit-after-first-byte` flag (added in WP02 if not already there); time process spawn → first byte. Run 5×; report p50.
- Release checklist mirrors the structure of the parent mission's release checklist (operator/date/commit slots, SC-006 live verification block, NFR numbers block, rollback test block).
- Full QA: `PYENV_VERSION=3.13.12 uv run --no-sync pytest tests/test_dashboard/ tests/architectural/ tests/sync/ -q`.

**Owned files**: `scripts/bench_dashboard_startup.py`, `kitty-specs/frontend-api-fastapi-openapi-migration-01KQN2JA/release-checklist.md`, `kitty-specs/frontend-api-fastapi-openapi-migration-01KQN2JA/spec.md` (book-keeping only).

## Definition of Done

The mission is done when:

- [ ] Every WP's subtasks are checked off and committed.
- [ ] `pytest tests/test_dashboard/ tests/architectural/ tests/sync/ -q` is green.
- [ ] `tests/test_dashboard/test_transport_parity.py` covers every route in `contracts/route-inventory.md`.
- [ ] `tests/test_dashboard/snapshots/openapi.json` exists and the snapshot test passes.
- [ ] `spec-kitty dashboard --transport fastapi` works locally; `--transport legacy` works as rollback.
- [ ] ADR + ownership map + manifest + runbook + release checklist are committed.
- [ ] NFR-001 / NFR-002 numbers recorded in the release checklist within thresholds.
- [ ] No new `# type: ignore` directives in `src/dashboard/api/`.
- [ ] No FastAPI / Starlette `Response` writes in route function bodies (architectural test passes).
- [ ] Two follow-up tickets filed for glossary and lint service extraction (transport-only migration leaves a service-extraction debt).
