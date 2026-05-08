---
work_package_id: WP05
title: Tests — Parity Suite, OpenAPI Snapshot, Handler-Purity, App Unit Tests
dependencies:
- WP04
requirement_refs:
- FR-006
- FR-007
- FR-013
- FR-014
planning_base_branch: feature/650-dashboard-ui-ux-overhaul
merge_target_branch: feature/650-dashboard-ui-ux-overhaul
branch_strategy: Planning artifacts for this feature were generated on feature/650-dashboard-ui-ux-overhaul. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/650-dashboard-ui-ux-overhaul unless the human explicitly redirects the landing branch.
subtasks:
- T023
- T024
- T025
- T026
- T027
- T028
agent: claude
history:
- date: '2026-05-02'
  event: created
  note: Auto-generated alongside tasks.md
agent_profile: implementer-ivan
authoritative_surface: tests/
execution_mode: code_change
owned_files:
- tests/test_dashboard/test_transport_parity.py
- tests/test_dashboard/test_openapi_snapshot.py
- tests/test_dashboard/snapshots/openapi.json
- tests/test_dashboard/test_openapi_validity.py
- tests/architectural/test_fastapi_handler_purity.py
- tests/architectural/test_dashboard_boundary.py
- tests/test_dashboard/test_fastapi_app.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load implementer-ivan
```

You are Implementer Ivan. Your role is comprehensive test coverage. Tests must be deterministic, fast, and self-explanatory.

## Objective

Comprehensive test coverage for the migration so future drift is caught in CI. The tests are the contract that prevents the migration from regressing under future maintenance.

## Subtasks

See `tasks.md` § WP05 for the full implementation sketch.

### T023 — `test_transport_parity.py`

Parametrized over `contracts/route-inventory.md`. For each route, build a `tmp_path` fixture project; spin up legacy via `urllib` against a real `BaseHTTPServer`; spin up FastAPI via `TestClient`; assert normalized JSON equivalence per the rules in `contracts/route-inventory.md`.

### T024 — `test_openapi_snapshot.py` + `snapshots/openapi.json`

Initial snapshot is committed. The test fails on any drift; failure message points at `contracts/openapi-stability.md` for the refresh procedure.

### T025 — `test_openapi_validity.py`

`openapi_spec_validator.validate(app.openapi())` (or equivalent) — guards against structurally invalid output independent of the snapshot.

### T026 — `test_fastapi_handler_purity.py`

AST-walk each `src/dashboard/api/routers/*.py`. For each function decorated with `@router.<method>`, assert no node calls `Response(...)`, `JSONResponse(...)`, or accesses `response.headers` directly inside the body. `PlainTextResponse(content=...)` and `HTMLResponse(content=...)` returns are allowed.

### T027 — Update `test_dashboard_boundary.py`

Extend the existing import-walk to allow `src.dashboard.api` to import from `dashboard.services.*`, `dashboard.api.models`, `dashboard.api_types`, `dashboard.file_reader`. Keep the `src.specify_cli.dashboard.*` exclusion as the FR-010 invariant.

### T028 — `test_fastapi_app.py`

Unit tests for the app factory, deps, and error handlers. `TestClient`-based.

## Definition of Done

- [ ] Every parametrized route in the parity suite passes.
- [ ] Snapshot test passes; snapshot file is committed.
- [ ] Validity test passes.
- [ ] Handler-purity test passes.
- [ ] Boundary test still passes (with the new allowance for `src.dashboard.api`).
- [ ] App unit tests cover the deps and error handlers with at least one happy + one failure path each.

## Reviewer guidance

- Confirm the parity test parametrization covers every route in `route-inventory.md` (count must match).
- Confirm the snapshot test failure message points at `contracts/openapi-stability.md`.
- Confirm the handler-purity test catches `Response(content=...)` calls inside route bodies (smoke-test by deliberately introducing a violation and confirming the test fails).

## Risks

- Parity test fragility from environmental noise (timestamps, paths). Mitigation: the JSON normalizer strips known volatile fields per the rules in `route-inventory.md`.
- Snapshot churn during minor FastAPI version bumps. Mitigation: documented refresh procedure; reviewer signoff required.

## Activity Log

- 2026-05-02T20:26:00Z – claude – Moved to claimed
- 2026-05-02T20:26:03Z – claude – Moved to in_progress
- 2026-05-02T20:32:29Z – claude – Moved to for_review
- 2026-05-02T20:32:32Z – claude – Moved to in_review
- 2026-05-02T20:32:35Z – claude – Moved to approved
- 2026-05-02T20:32:38Z – claude – Done override: Lane-less mission run on parent feature/650-dashboard-ui-ux-overhaul branch
