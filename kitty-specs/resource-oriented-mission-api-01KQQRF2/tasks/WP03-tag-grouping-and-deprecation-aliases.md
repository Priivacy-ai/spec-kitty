---
work_package_id: WP03
title: Tag grouping and deprecation aliases on existing routers
dependencies: []
requirement_refs:
- FR-009
- FR-010
- FR-011
planning_base_branch: feature/650-dashboard-ui-ux-overhaul
merge_target_branch: feature/650-dashboard-ui-ux-overhaul
branch_strategy: Planning artifacts for this feature were generated on feature/650-dashboard-ui-ux-overhaul. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/650-dashboard-ui-ux-overhaul unless the human explicitly redirects the landing branch.
subtasks:
- T017
- T018
- T019
- T020
- T021
- T022
- T023
- T024
agent: claude
history: []
agent_profile: python-pedro
authoritative_surface: src/dashboard/api/routers/
execution_mode: code_change
model: claude-sonnet-4-6
owned_files:
- src/dashboard/api/routers/artifacts.py
- src/dashboard/api/routers/charter.py
- src/dashboard/api/routers/dossier.py
- src/dashboard/api/routers/features.py
- src/dashboard/api/routers/glossary.py
- src/dashboard/api/routers/health.py
- src/dashboard/api/routers/kanban.py
- src/dashboard/api/routers/lint.py
- src/dashboard/api/routers/shutdown.py
- src/dashboard/api/routers/static_mount.py
- src/dashboard/api/routers/sync.py
- src/dashboard/api/routers/diagnostics.py
- tests/test_dashboard/test_deprecation_headers.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

Two independent but cohesive tasks on the existing router files:
1. **OpenAPI tag grouping** (#958): Add `tags=[...]` to every `APIRouter(...)` constructor so Swagger UI renders routes grouped by domain.
2. **Deprecation aliases**: Retrofit `/api/features` and `/api/kanban/{feature_id}` with `Deprecation: true` and `Link` response headers, signalling that clients should migrate to the new `/api/missions` surface.

This WP runs in **parallel with WP02** (Lane B). It does not depend on WP01 or WP02.

## Branch Strategy

- **Planning base / merge target**: `feature/650-dashboard-ui-ux-overhaul`
- No dependencies — run from the HEAD of `feature/650-dashboard-ui-ux-overhaul`.
- `spec-kitty agent action implement WP03 --agent claude`

## Tag Assignment Reference

| Router file | Tag |
|-------------|-----|
| `features.py` | `["kanban"]` |
| `kanban.py` | `["kanban"]` |
| `artifacts.py` | `["research"]` or `["contracts"]` or `["checklists"]` — inspect the routes it declares to assign the right tag; if it serves multiple artifact types, use `["artifacts"]` |
| `charter.py` | `["charter"]` |
| `dossier.py` | `["dossier"]` |
| `glossary.py` | `["glossary"]` |
| `health.py` | `["health"]` |
| `diagnostics.py` | `["health"]` |
| `sync.py` | `["sync"]` |
| `shutdown.py` | `["lifecycle"]` |
| `static_mount.py` | `["static"]` (or omit if it serves only static files and OpenAPI will not show it) |
| `lint.py` | `["glossary"]` (lint/decay-watch is a glossary health concern) |

**Note**: The `missions.py` router (created in WP02) will already have `tags=["missions"]` — do not touch it.

## Implementation Guide

### T017 — Tags on features.py and kanban.py

**Files**: `src/dashboard/api/routers/features.py`, `src/dashboard/api/routers/kanban.py`

Locate the `APIRouter()` constructor in each file. Example — before:

```python
router = APIRouter()
```

After:
```python
router = APIRouter(tags=["kanban"])
```

These two files are also touched by T019/T020 (deprecation headers), so do both in a single edit pass per file.

---

### T018 — Tags on all remaining existing routers

Apply the same single-line change to every other router in `src/dashboard/api/routers/`. Use the tag assignment table above. For each file:
1. Read the route paths to confirm the tag is right.
2. Edit the `APIRouter(...)` constructor line only.
3. Do not change any route handler logic.

Routers to update: `artifacts.py`, `charter.py`, `dossier.py`, `glossary.py`, `health.py`, `diagnostics.py`, `sync.py`, `shutdown.py`, `static_mount.py`, `lint.py`.

---

### T019 — Deprecation headers on GET /api/features

**File**: `src/dashboard/api/routers/features.py`

Find the route handler for `GET /api/features`. Add a `Response` parameter and inject the headers:

```python
from fastapi import APIRouter, Depends, Response
# ... existing imports ...

@router.get("/api/features")
async def list_features(
    response: Response,
    # ... existing parameters ...
):
    response.headers["Deprecation"] = "true"
    response.headers["Link"] = '</api/missions>; rel="successor-version"'
    # ... existing handler body, unchanged ...
```

**Important**: The response body must remain byte-equivalent to the pre-mission response. Do not alter the return statement or the serialization.

---

### T020 — Deprecation headers on GET /api/kanban/{feature_id}

**File**: `src/dashboard/api/routers/kanban.py`

Same pattern:

```python
@router.get("/api/kanban/{feature_id}")
async def get_kanban(
    feature_id: str,
    response: Response,
    # ... existing parameters ...
):
    response.headers["Deprecation"] = "true"
    response.headers["Link"] = f'</api/missions/{feature_id}/status>; rel="successor-version"'
    # ... existing handler body, unchanged ...
```

Note: `feature_id` in the `Link` header is the path parameter value, not the resolved `mission_id`. Clients that follow the link will still need to resolve it via the registry, which handles `mission_slug` as a valid selector.

---

### T021 — Test: deprecation headers present

**File**: `tests/test_dashboard/test_deprecation_headers.py` (new file)

Using the existing test client pattern:

```python
def test_features_has_deprecation_header(client):
    resp = client.get("/api/features")
    assert resp.status_code == 200
    assert resp.headers.get("deprecation") == "true"
    assert "/api/missions" in resp.headers.get("link", "")

def test_kanban_has_deprecation_header(client, fixture_feature_id):
    resp = client.get(f"/api/kanban/{fixture_feature_id}")
    assert resp.status_code == 200
    assert resp.headers.get("deprecation") == "true"
    assert "/api/missions" in resp.headers.get("link", "")
```

Look at existing tests (e.g., `tests/test_dashboard/test_api_contract.py`) for the `client` fixture definition and `fixture_feature_id` pattern.

---

### T022 — Assert deprecated response bodies structurally unchanged

In the same test file, add tests that confirm the body shape of the deprecated routes matches the pre-mission contract:

```python
def test_features_body_shape_unchanged(client):
    resp = client.get("/api/features")
    data = resp.json()
    # features endpoint returns a list or a dict with "features" key — check existing test for exact shape
    assert isinstance(data, (list, dict))
    # Assert the key fields that existing consumers rely on are still present
    # e.g., if it returns a dict with "features" key:
    # assert "features" in data or assert isinstance(data, list)

def test_kanban_body_shape_unchanged(client, fixture_feature_id):
    resp = client.get(f"/api/kanban/{fixture_feature_id}")
    data = resp.json()
    # kanban returns a dict — assert key shape fields
    assert "lane_counts" in data or "kanban" in str(data)
```

**Note**: Before writing these, read existing tests that already cover `/api/features` and `/api/kanban/{id}` to understand the expected response shape. Mirror those shape assertions here.

---

### T023 — Run architectural tests

```bash
.venv/bin/python -m pytest tests/architectural/ -q --timeout=60
```

Must pass with 0 failures. The tag changes do not affect architectural invariants.

---

### T024 — Run full dashboard tests

```bash
.venv/bin/python -m pytest tests/test_dashboard/ -q --timeout=90
```

Must pass with 0 failures. The deprecated routes return the same body, so existing tests must still pass.

## Definition of Done

- [ ] Every `APIRouter(...)` in every file under `src/dashboard/api/routers/` has `tags=[...]`.
- [ ] `GET /api/features` response includes `Deprecation: true` and `Link` headers.
- [ ] `GET /api/kanban/{feature_id}` response includes `Deprecation: true` and `Link` headers.
- [ ] `tests/test_dashboard/test_deprecation_headers.py` passes.
- [ ] Existing deprecated-route tests still pass (body unchanged).
- [ ] `pytest tests/architectural/ -q` exits 0.
- [ ] `pytest tests/test_dashboard/ -q` exits 0.
- [ ] Zero new `# type: ignore` added.

## Risks

- **`Response` parameter injection**: FastAPI requires `Response` to be listed as a parameter for the decorator-based pattern to inject headers correctly. If the existing route uses a `return Response(...)` pattern instead of the `Response` parameter, use a different injection approach — e.g., set headers on the returned `Response` object directly.
- **Artifacts router ambiguity**: `artifacts.py` may serve research, contracts, and checklist artifacts. Read its route paths first before assigning a tag — `["artifacts"]` is a safe fallback if it mixes types.
- **Header case sensitivity**: HTTP headers are case-insensitive but the test should use `.lower()` or `casefold()` when reading response headers in case the framework normalises them.
