---
work_package_id: WP04
title: Alias Retirement
dependencies: []
requirement_refs:
- FR-007
- FR-008
planning_base_branch: feature/645-api-surface-completion-mission-c
merge_target_branch: feature/645-api-surface-completion-mission-c
branch_strategy: Planning artifacts for this feature were generated on feature/645-api-surface-completion-mission-c. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/645-api-surface-completion-mission-c unless the human explicitly redirects the landing branch.
created_at: '2026-05-04T17:07:04Z'
subtasks:
- T017
- T018
- T019
- T020
- T021
agent: "copilot:claude-sonnet-4-6:alphonso:reviewer"
shell_pid: "1972687"
history:
- at: '2026-05-04T17:07:04Z'
  event: created
  note: Initial task breakdown
authoritative_surface: src/dashboard/api/routers/
execution_mode: code_change
lane: planned
mission_id: 01KQSXDASEMGGZNAX3A5FXSEPM
owned_files:
- src/dashboard/api/routers/features.py
- src/dashboard/api/routers/kanban.py
- tests/test_dashboard/test_deprecation_headers.py
tags: []
---

## Objective

Retire `GET /api/features` and `GET /api/kanban/{feature_id}` with HTTP 410 Gone responses. Remove both routes from the OpenAPI schema (`include_in_schema=False`). Remove `Deprecation` and `Link` response headers from these routes. Update the deprecation header tests to assert 410 status and the `endpoint_retired` body. Confirm no regressions.

## Context

Both routes were previously marked with `Deprecation: true` headers as temporary measures during the migration to `/api/missions`. They now have successor routes and must be fully retired (FR-007, FR-008). The retirement pattern:

- **Keep the route handler** so legacy callers receive a proper 410 rather than a silent 404.
- **Set `include_in_schema=False`** so the route is absent from the OpenAPI document and the generated TypeScript types.
- **Return HTTP 410** with a JSON body containing `{"error": "endpoint_retired", "successor": "<successor_path>"}`.
- **Remove `Deprecation` and `Link` headers** — the endpoint is gone, not merely deprecated.

This WP is **intentionally independent** of WP01–WP03. It can run in parallel with any of them, and does not wait for the TypedDict migration to complete.

Successor routes:
- `/api/features` → `/api/missions`
- `/api/kanban/{feature_id}` → `/api/missions/{feature_id}/status`

## Branch Strategy

- `planning_base_branch`: `feature/645-api-surface-completion-mission-c`
- `merge_target_branch`: `feature/645-api-surface-completion-mission-c`
- No WP dependencies — can start on the base branch immediately.

## Subtask Guide

### T017: Add `_gone_response()` Helper in `features.py`

**Purpose:** Provide a clean, reusable function for constructing the 410 response so the route handler bodies stay trivial.

**Steps:**

1. Open `src/dashboard/api/routers/features.py`.

2. Add the `_gone_response` helper near the top of the file (after imports):

```python
from fastapi.responses import JSONResponse


def _gone_response(deprecated_path: str, successor_path: str) -> JSONResponse:
    """Return a 410 Gone response for a retired endpoint.

    Body shape: {"error": "endpoint_retired", "successor": successor_path}
    The ``successor`` key (not ``detail``) is the wire format mandated by the spec.
    """
    return JSONResponse(
        status_code=410,
        content={
            "error": "endpoint_retired",
            "successor": successor_path,
        },
    )
```

3. Note: `JSONResponse` is already available as a FastAPI transitive dependency. If already imported in the file, do not add a duplicate import.

**Files:** `src/dashboard/api/routers/features.py` (update)

**Validation:**
- [x] `_gone_response(...)` returns a `JSONResponse` with status 410
- [x] Body has `error` key equal to `"endpoint_retired"` and `successor` key
- [x] Helper is importable: `cd src && python -c "from dashboard.api.routers.features import _gone_response; print('OK')"`

---

### T018: Retire `GET /api/features`

**Purpose:** Replace the handler body of `GET /api/features` with a 410 response; remove it from the OpenAPI schema; remove deprecated headers.

**Steps:**

1. Find the existing `GET /api/features` route handler in `src/dashboard/api/routers/features.py`. It likely looks similar to:

```python
@router.get("/api/features")
async def get_features(request: Request) -> FeaturesListResponse | FeaturesListErrorResponse:
    # ... implementation that adds Deprecation header ...
```

2. Replace with:

```python
@router.get("/api/features", include_in_schema=False)
async def retired_features() -> JSONResponse:
    """Retired endpoint. Use /api/missions instead."""
    return _gone_response("/api/features", "/api/missions")
```

3. Remove `Deprecation` and `Link` header-setting code from this route.

4. Remove now-unused imports of `FeaturesListResponse` and `FeaturesListErrorResponse` from `dashboard.api_types` if these are no longer referenced anywhere else in `features.py`.

5. Verify the route no longer appears in the OpenAPI schema by checking `include_in_schema=False` is set.

**Files:** `src/dashboard/api/routers/features.py` (update)

**Validation:**
- [x] `@router.get("/api/features", include_in_schema=False)` is present
- [x] Handler body calls `_gone_response("/api/features", "/api/missions")`
- [x] No `Deprecation` or `Link` header code remains in this route
- [x] No imports of `FeaturesListResponse` or `FeaturesListErrorResponse` from `dashboard.api_types` remain (unless referenced elsewhere in the file)
- [x] `cd src && python -c "from dashboard.api.routers.features import router; print('OK')"` succeeds

---

### T019: Retire `GET /api/kanban/{feature_id}`

**Purpose:** Replace the handler body of `GET /api/kanban/{feature_id}` with a 410 response; remove it from the OpenAPI schema.

**Steps:**

1. Open `src/dashboard/api/routers/kanban.py`.

2. Add the same `_gone_response` helper (or import it from `features.py` — however the module is structured, keep it consistent). Prefer a local copy to avoid cross-router imports:

```python
from fastapi.responses import JSONResponse


def _gone_response(deprecated_path: str, successor_path: str) -> JSONResponse:
    return JSONResponse(
        status_code=410,
        content={"error": "endpoint_retired", "successor": successor_path},
    )
```

3. Find the existing `GET /api/kanban/{feature_id}` route. Replace with:

```python
@router.get("/api/kanban/{feature_id}", include_in_schema=False)
async def retired_kanban(feature_id: str) -> JSONResponse:
    """Retired endpoint. Use /api/missions/{feature_id}/status instead."""
    return _gone_response(
        f"/api/kanban/{feature_id}",
        f"/api/missions/{feature_id}/status",
    )
```

4. Remove now-unused imports of `KanbanResponse` from `dashboard.api_types`.

5. Remove any `Deprecation` or `Link` header-setting code.

6. Verify: `cd src && python -c "from dashboard.api.routers.kanban import router; print('OK')"`.

**Files:** `src/dashboard/api/routers/kanban.py` (update)

**Validation:**
- [x] `@router.get("/api/kanban/{feature_id}", include_in_schema=False)` is present
- [x] Handler body calls `_gone_response` with the correct successor path
- [x] No `KanbanResponse` import from `dashboard.api_types` remains
- [x] No `Deprecation` or `Link` header code remains
- [x] Router imports without error

---

### T020: Update `tests/test_dashboard/test_deprecation_headers.py`

**Purpose:** The existing tests assert that these routes return `Deprecation: true` headers. After retirement, they should assert HTTP 410 and the `endpoint_retired` body instead.

**Steps:**

1. Open `tests/test_dashboard/test_deprecation_headers.py` and read it fully.

2. For any test that checks `/api/features` with `Deprecation: true` or `200 OK`, replace with:

```python
def test_features_route_returns_410(client):
    """GET /api/features returns 410 Gone after alias retirement."""
    response = client.get("/api/features")
    assert response.status_code == 410
    body = response.json()
    assert body["error"] == "endpoint_retired"
    assert body["successor"] == "/api/missions"


def test_features_route_not_in_openapi_schema(client):
    """GET /api/features is excluded from the OpenAPI schema."""
    response = client.get("/openapi.json")
    schema = response.json()
    assert "/api/features" not in schema.get("paths", {})
```

3. For any test that checks `/api/kanban/{feature_id}` with `Deprecation: true` or `200 OK`, replace with:

```python
def test_kanban_route_returns_410(client):
    """GET /api/kanban/{feature_id} returns 410 Gone after alias retirement."""
    response = client.get("/api/kanban/some-feature")
    assert response.status_code == 410
    body = response.json()
    assert body["error"] == "endpoint_retired"
    assert body["successor"] == "/api/missions/some-feature/status"


def test_kanban_route_not_in_openapi_schema(client):
    """GET /api/kanban/{feature_id} is excluded from the OpenAPI schema."""
    response = client.get("/openapi.json")
    schema = response.json()
    # Check no path matches the kanban pattern
    paths = schema.get("paths", {})
    kanban_paths = [p for p in paths if "/kanban/" in p]
    assert len(kanban_paths) == 0
```

4. Remove any `Deprecation` header assertions for these two routes. Keep all other tests in the file unchanged.

**Files:** `tests/test_dashboard/test_deprecation_headers.py` (update)

**Validation:**
- [x] No assertions for `Deprecation: true` remain for these two routes
- [x] New assertions for 410 status and `endpoint_retired` body are present
- [x] Tests for other routes in the file are unchanged

---

### T021: Run `pytest tests/test_dashboard/` and Confirm

**Purpose:** Gate check — confirm the retired routes return 410, and no regressions exist in other dashboard tests.

**Steps:**

1. Run: `cd src && pytest ../tests/test_dashboard/ -v --tb=short`

2. All tests must pass. If any test fails:
   - If it's a test for `/api/features` or `/api/kanban/`: it was missed in T020. Fix the test.
   - If it's a test for another route: investigate whether the import of `FeaturesListResponse` or `KanbanResponse` was used elsewhere and broken.

3. Specifically verify:
   - `GET /api/features` → 410, body has `error == "endpoint_retired"`, `successor == "/api/missions"`
   - `GET /api/kanban/test-id` → 410, body has `error == "endpoint_retired"`, `successor == "/api/missions/test-id/status"`
   - `/openapi.json` paths dict does NOT contain `/api/features` or any `/api/kanban/...` key

**Files:** (no new files — verification step)

**Validation:**
- [x] `pytest tests/test_dashboard/ -v` exits with code 0
- [x] No regressions in non-retired routes
- [x] HTTP 410 confirmed for both retired routes

---

## Definition of Done

- [x] `GET /api/features` returns HTTP 410 with `{"error": "endpoint_retired", "successor": "/api/missions"}`
- [x] `GET /api/kanban/{feature_id}` returns HTTP 410 with correct successor path
- [x] Both routes have `include_in_schema=False`
- [x] Neither route appears in `/openapi.json` paths
- [x] No `Deprecation` or `Link` headers on either route
- [x] `test_deprecation_headers.py` tests pass with 410 assertions
- [x] `pytest tests/test_dashboard/ -v` exits clean

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Other test files still assert 200 or headers on these routes | Medium | Run full `tests/test_dashboard/` suite in T021; fix any stragglers |
| `FeaturesListResponse`/`KanbanResponse` imported elsewhere in same router file | Low | Check with `grep -n "FeaturesListResponse\|KanbanResponse" src/dashboard/api/routers/features.py` |
| `_gone_response` duplicated across two files leads to inconsistency | Low | Both copies use the same exact body shape; or extract to a shared `routers/_utils.py` |

## Reviewer Guidance

1. Verify both routes have `include_in_schema=False` in the decorator.
2. Confirm the 410 body has `successor` (not `detail`) as the second key.
3. Run `curl -s http://localhost:8765/api/features | jq .` against a running dashboard to confirm live behavior.
4. Check the OpenAPI JSON: `GET /openapi.json` → `paths` must not contain `/api/features` or `/api/kanban/{feature_id}`.
5. Confirm all assertions in `test_deprecation_headers.py` use 410 status for these routes.

Implement command: `spec-kitty agent action implement WP04 --agent <name>`

## Activity Log

- 2026-05-04T17:50:56Z – copilot:claude-sonnet-4-6:alphonso:implementer – shell_pid=1967145 – Started implementation via action command
- 2026-05-04T17:55:05Z – copilot:claude-sonnet-4-6:alphonso:implementer – shell_pid=1967145 – Both alias routes return 410 with successor key; tests updated; include_in_schema=False on both
- 2026-05-04T17:55:30Z – copilot:claude-sonnet-4-6:alphonso:reviewer – shell_pid=1972687 – Started review via action command
- 2026-05-04T17:57:16Z – copilot:claude-sonnet-4-6:alphonso:reviewer – shell_pid=1972687 – Review passed: both routes return 410 with successor key, include_in_schema=False, tests updated
