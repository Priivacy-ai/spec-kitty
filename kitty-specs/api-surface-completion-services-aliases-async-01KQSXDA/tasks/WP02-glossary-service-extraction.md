---
work_package_id: WP02
title: GlossaryService Extraction + Pydantic Alignment
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-002
- FR-005
- FR-006
- FR-016
- FR-018
planning_base_branch: feature/645-api-surface-completion-mission-c
merge_target_branch: feature/645-api-surface-completion-mission-c
branch_strategy: Planning artifacts for this feature were generated on feature/645-api-surface-completion-mission-c. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/645-api-surface-completion-mission-c unless the human explicitly redirects the landing branch.
created_at: '2026-05-04T17:07:04Z'
subtasks:
- T008
- T009
- T010
- T011
- T012
agent: "copilot:claude-sonnet-4-6:alphonso:reviewer"
shell_pid: "1960450"
history:
- at: '2026-05-04T17:07:04Z'
  event: created
  note: Initial task breakdown
authoritative_surface: src/specify_cli/glossary/
execution_mode: code_change
lane: planned
mission_id: 01KQSXDASEMGGZNAX3A5FXSEPM
owned_files:
- src/specify_cli/glossary/service.py
- src/dashboard/api/routers/glossary.py
- src/specify_cli/dashboard/handlers/glossary.py
- src/dashboard/api/models.py
- tests/specify_cli/glossary/test_glossary_service.py
- tests/test_dashboard/test_glossary_handler.py
tags: []
---

## Objective

Extract the glossary router's private helper functions (`_build_glossary_health`, `_build_glossary_terms`) into a proper domain service class (`GlossaryService`) in `src/specify_cli/glossary/service.py`. Delegate the FastAPI router's handler bodies to the service. Update the legacy `BaseHTTPRequestHandler` in `handlers/glossary.py` to import from the new canonical type location. Align the three affected Pydantic models in `models.py` with their canonical TypedDicts (FR-018).

## Context

The current `src/dashboard/api/routers/glossary.py` contains business logic in private helper functions that duplicate the logic in `src/specify_cli/dashboard/handlers/glossary.py`. This duplication violates the "one canonical implementation" principle (NFR-001). The `GlossaryService` becomes the single implementation that both the FastAPI router and the legacy HTTP handler delegate to.

The `specify_cli.glossary` package already exposes:
- `GlossaryScope` (enum with `MISSION_LOCAL`, `TEAM_DOMAIN`, `AUDIENCE_DOMAIN`, `SPEC_KITTY_CORE`)
- `load_seed_file(scope, repo_root) -> list[TermSense]`
- `iter_semantic_conflicts(project_dir) -> Iterable[SemanticConflictRecord]`

`TermSense` attributes: `.status.value` → `"active"|"draft"|"deprecated"`, `.confidence` → `float | None`, `.surface.surface_text` → `str`, `.definition` → `str | None`.

**Constraint (C-003):** `GlossaryService` must not import `fastapi`, `starlette`, or `pydantic`. It works with plain Python dicts and TypedDicts only.

**Parity requirement (NFR-001):** The service must produce output that is byte-for-byte equivalent to the existing private helpers for the same inputs.

## Branch Strategy

- `planning_base_branch`: `feature/645-api-surface-completion-mission-c`
- `merge_target_branch`: `feature/645-api-surface-completion-mission-c`
- WP01 must be merged to the lane branch before this WP starts.

## Subtask Guide

### T008: Create `src/specify_cli/glossary/service.py`

**Purpose:** Provide a pure-Python domain service that encapsulates glossary data retrieval. This is the single source of truth for glossary health and term data; both the FastAPI router and the legacy HTTP handler delegate to it.

**Steps:**

1. Read the existing private helpers in `src/dashboard/api/routers/glossary.py` carefully, specifically:
   - `_empty_health_response()`
   - `_count_orphaned_terms(project_dir)`
   - `_collect_all_senses(repo_root)`
   - `_build_glossary_health(project_dir)`
   - `_build_glossary_terms(project_dir)`

2. Create `src/specify_cli/glossary/service.py`:

```python
"""GlossaryService — read-only domain service for glossary data.

No FastAPI, Starlette, or Pydantic imports (C-003).
"""

from __future__ import annotations

from pathlib import Path

from specify_cli.glossary.types import GlossaryHealthResponse, GlossaryTermRecord


class GlossaryService:
    """Read-only domain service for glossary data. No FastAPI/Pydantic imports."""

    def __init__(self, project_dir: Path) -> None:
        self._project_dir = project_dir

    def get_health(self) -> GlossaryHealthResponse:
        """Aggregate glossary health metrics across all scopes.

        Returns a GlossaryHealthResponse with total_terms, active_count,
        draft_count, deprecated_count, high_severity_drift_count,
        orphaned_term_count, entity_pages_generated, entity_pages_path,
        last_conflict_at.

        Returns an empty-defaults response if project_dir is unavailable.
        """
        # ... replicate _build_glossary_health logic here ...

    def get_terms(self) -> list[GlossaryTermRecord]:
        """Return all glossary terms across all scopes.

        Each entry contains surface, definition, status, confidence.
        Returns an empty list if project_dir is unavailable.
        """
        # ... replicate _build_glossary_terms logic here ...
```

3. Replicate the full logic from `_build_glossary_health` and `_build_glossary_terms` into the service methods. Key points:
   - `_collect_all_senses` logic moves to a private `_collect_all_senses(self)` instance method or a module-level helper
   - `_count_orphaned_terms` logic moves to a private instance method
   - The service uses `self._project_dir` where the helpers used `project_dir`
   - Import from `specify_cli.glossary.types` (WP01-created) not from `dashboard.api_types`

4. Verify no FastAPI/Starlette/Pydantic imports are present: `grep -n "fastapi\|starlette\|pydantic" src/specify_cli/glossary/service.py` must produce no output.

**Files:** `src/specify_cli/glossary/service.py` (new)

**Validation:**
- [x] `GlossaryService.__init__` accepts `project_dir: Path`
- [x] `get_health()` returns `GlossaryHealthResponse`
- [x] `get_terms()` returns `list[GlossaryTermRecord]`
- [x] No `fastapi`, `starlette`, or `pydantic` imports
- [x] Imports from `specify_cli.glossary.types` (not `dashboard.api_types`)
- [x] `mypy --strict src/specify_cli/glossary/service.py` passes

---

### T009: Update `src/dashboard/api/routers/glossary.py`

**Purpose:** Remove all private helper functions from the router; delegate every route handler body to `GlossaryService`. Each handler body must be ≤ 15 LOC. Remove `# TODO(follow-up)` markers referencing issue #954.

**Steps:**

1. Read the current `src/dashboard/api/routers/glossary.py` in full.

2. Remove these functions entirely:
   - `_empty_health_response()`
   - `_count_orphaned_terms(project_dir)`
   - `_collect_all_senses(repo_root)`
   - `_build_glossary_health(project_dir)`
   - `_build_glossary_terms(project_dir)`

3. Add import at top:
   ```python
   from specify_cli.glossary.service import GlossaryService
   from specify_cli.glossary.types import GlossaryHealthResponse, GlossaryTermRecord
   ```

4. Update each route handler to delegate to the service. Example pattern:

   ```python
   @router.get("/api/glossary-health")
   async def get_glossary_health(request: Request) -> GlossaryHealthResponse:
       project_dir = request.app.state.project_dir
       service = GlossaryService(project_dir)
       return service.get_health()


   @router.get("/api/glossary-terms")
   async def get_glossary_terms(request: Request) -> list[GlossaryTermRecord]:
       project_dir = request.app.state.project_dir
       service = GlossaryService(project_dir)
       return service.get_terms()
   ```

5. Remove all `# TODO(follow-up)` comments referencing issue #954.

6. Remove imports of `GlossaryHealthResponse` and `GlossaryTermRecord` from `dashboard.api_types` — they now come from `specify_cli.glossary.types`.

7. Run: `cd src && python -c "from dashboard.api.routers.glossary import router; print('OK')"`.

**Files:** `src/dashboard/api/routers/glossary.py` (update)

**Validation:**
- [x] All five private helpers removed
- [x] Each handler body is ≤ 15 LOC
- [x] No imports from `dashboard.api_types` remain
- [x] No `# TODO(follow-up)` markers for issue #954 remain
- [x] Router imports without error

---

### T010: Update `src/specify_cli/dashboard/handlers/glossary.py` Imports

**Purpose:** The legacy `BaseHTTPRequestHandler` handler currently imports `GlossaryHealthResponse` and `GlossaryTermRecord` from `..api_types` (the shim at `specify_cli/dashboard/api_types.py`). Update to import from `specify_cli.glossary.types`. No other behavioral changes.

**Steps:**

1. Open `src/specify_cli/dashboard/handlers/glossary.py`.

2. Find the import line(s) that reference `api_types`:
   ```python
   # Before:
   from ..api_types import GlossaryHealthResponse, GlossaryTermRecord
   # OR
   from specify_cli.dashboard.api_types import GlossaryHealthResponse, GlossaryTermRecord
   ```

3. Replace with:
   ```python
   from specify_cli.glossary.types import GlossaryHealthResponse, GlossaryTermRecord
   ```

4. Do NOT change any other logic in this file.

5. Run existing tests to confirm no regressions: `cd src && pytest ../tests/test_dashboard/test_glossary_handler.py -v`.

**Files:** `src/specify_cli/dashboard/handlers/glossary.py` (import update only)

**Validation:**
- [x] Import uses `specify_cli.glossary.types`, not `..api_types`
- [x] No other lines changed
- [x] Existing handler tests pass

---

### T011: Update `src/dashboard/api/models.py` — Pydantic Alignment (FR-018)

**Purpose:** The Pydantic model classes for `GlossaryTermRecord`, `GlossaryHealthResponse`, and `DecayWatchTileResponse` in `models.py` must import their canonical TypedDicts from the new locations (FR-018). This file is exclusively owned by WP02 — WP03 does not touch it (the lint models are part of the same alignment pass).

**Steps:**

1. Open `src/dashboard/api/models.py` and identify the Pydantic classes for:
   - `GlossaryTermRecord` (or a model that references `GlossaryTermRecord`)
   - `GlossaryHealthResponse` (or a model that references `GlossaryHealthResponse`)
   - `DecayWatchTileResponse` (or a model that references `DecayWatchTileResponse`)

2. Update import statements:
   ```python
   # Before:
   from dashboard.api_types import GlossaryTermRecord, GlossaryHealthResponse, DecayWatchTileResponse
   # OR
   from dashboard.api_types import (
       GlossaryTermRecord,
       GlossaryHealthResponse,
       DecayWatchTileResponse,
       # ... other types ...
   )

   # After (separate imports per domain):
   from specify_cli.glossary.types import GlossaryTermRecord, GlossaryHealthResponse
   from specify_cli.charter_lint.types import DecayWatchTileResponse
   ```

3. Add docstring alignment notes to each Pydantic model class that references these types:
   ```python
   class GlossaryTermRecordModel(BaseModel):
       """Pydantic model aligned with GlossaryTermRecord TypedDict (FR-018).

       Canonical TypedDict: specify_cli.glossary.types.GlossaryTermRecord
       """
       ...
   ```

4. Remove any remaining imports of these three types from `dashboard.api_types`.

5. Run: `cd src && pytest ../tests/test_dashboard/ -k "model or glossary" -v`.

**Files:** `src/dashboard/api/models.py` (update)

**Validation:**
- [x] No imports of `GlossaryTermRecord`, `GlossaryHealthResponse`, `DecayWatchTileResponse` from `dashboard.api_types`
- [x] Pydantic models for these types import from `specify_cli.glossary.types` or `specify_cli.charter_lint.types`
- [x] Docstring alignment notes added
- [x] Models module imports without error

---

### T012: Write `tests/specify_cli/glossary/test_glossary_service.py`

**Purpose:** Unit tests for `GlossaryService` that verify correctness of both methods and parity with the original private helpers (NFR-001, NFR-006).

**Steps:**

1. Create the test file `tests/specify_cli/glossary/test_glossary_service.py`.

2. Structure:

```python
"""Unit tests for GlossaryService.

Covers:
  - get_health() baseline
  - get_terms() baseline
  - get_health() with missing project_dir (empty response)
  - get_terms() with missing project_dir (empty list)
  - Parity: service output matches _build_glossary_health golden data (NFR-001)
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.glossary.service import GlossaryService
from specify_cli.glossary.types import GlossaryHealthResponse, GlossaryTermRecord


class TestGlossaryServiceGetHealth:
    def test_returns_glossary_health_response_type(self, tmp_path: Path) -> None:
        """get_health() returns a dict with GlossaryHealthResponse shape."""
        service = GlossaryService(tmp_path)
        result = service.get_health()
        assert isinstance(result, dict)

    def test_empty_when_project_dir_missing(self, tmp_path: Path) -> None:
        """get_health() returns empty-defaults when project_dir does not exist."""
        missing_dir = tmp_path / "nonexistent"
        service = GlossaryService(missing_dir)
        result = service.get_health()
        # Should not raise; must return some dict
        assert isinstance(result, dict)

    def test_health_fields_present_with_valid_data(self, tmp_path: Path) -> None:
        """get_health() includes expected fields when glossary data is present."""
        # Set up mock glossary data using tmp_path
        # ... use unittest.mock.patch to mock load_seed_file and iter_semantic_conflicts
        ...


class TestGlossaryServiceGetTerms:
    def test_returns_list(self, tmp_path: Path) -> None:
        """get_terms() returns a list."""
        service = GlossaryService(tmp_path)
        result = service.get_terms()
        assert isinstance(result, list)

    def test_empty_when_no_terms(self, tmp_path: Path) -> None:
        """get_terms() returns empty list when no terms exist."""
        missing = tmp_path / "no-glossary"
        service = GlossaryService(missing)
        result = service.get_terms()
        assert result == []

    def test_term_record_shape(self, tmp_path: Path) -> None:
        """Each term record has the GlossaryTermRecord fields."""
        # Mock load_seed_file to return a single TermSense
        ...


class TestGlossaryServiceParity:
    """Parity tests: service output must match golden data (NFR-001)."""

    def test_get_health_parity_with_original_helper(self, tmp_path: Path) -> None:
        """GlossaryService.get_health() matches _build_glossary_health golden output."""
        # Arrange: set up the same mock state
        # Act: call both original helper (if it still exists) and service
        # Assert: outputs are equal
        ...

    def test_get_terms_parity_with_original_helper(self, tmp_path: Path) -> None:
        """GlossaryService.get_terms() matches _build_glossary_terms golden output."""
        ...
```

3. Ensure ≥ 90% line coverage (NFR-006): `cd src && pytest ../tests/specify_cli/glossary/test_glossary_service.py --cov=specify_cli.glossary.service --cov-report=term-missing`.

4. Also update `tests/test_dashboard/test_glossary_handler.py` to verify the router now delegates to the service (remove any tests that test private helpers directly; add a test that the service is instantiated and called):

```python
def test_glossary_health_route_delegates_to_service(client, mocker):
    """The /api/glossary-health route delegates to GlossaryService."""
    mock_service = mocker.patch("dashboard.api.routers.glossary.GlossaryService")
    mock_service.return_value.get_health.return_value = {"total_terms": 0}
    response = client.get("/api/glossary-health")
    assert response.status_code == 200
    mock_service.return_value.get_health.assert_called_once()
```

**Files:** `tests/specify_cli/glossary/test_glossary_service.py` (new), `tests/test_dashboard/test_glossary_handler.py` (update)

**Validation:**
- [x] `pytest tests/specify_cli/glossary/test_glossary_service.py -v` passes
- [x] `pytest tests/test_dashboard/test_glossary_handler.py -v` passes
- [x] Line coverage ≥ 90% for `specify_cli.glossary.service`
- [x] At least one parity test per method

---

## Definition of Done

- [x] `src/specify_cli/glossary/service.py` exists with `GlossaryService` class
- [x] `GlossaryService.get_health()` and `get_terms()` contain the extracted logic
- [x] `src/dashboard/api/routers/glossary.py` has no private helpers; each handler ≤ 15 LOC
- [x] No `# TODO(follow-up)` markers for issue #954 remain in the router
- [x] `src/specify_cli/dashboard/handlers/glossary.py` imports from `specify_cli.glossary.types`
- [x] `src/dashboard/api/models.py` no longer imports glossary types from `dashboard.api_types`
- [x] `tests/specify_cli/glossary/test_glossary_service.py` passes with ≥ 90% coverage
- [x] `tests/test_dashboard/test_glossary_handler.py` passes
- [x] `mypy --strict src/specify_cli/glossary/service.py` passes

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Parity break: service output differs from original helper | High | Parity tests in T012 compare against golden data |
| C-003 violation: FastAPI/Pydantic imported in service | High | `grep` check in T008 validation |
| `models.py` edit breaks serialization for other types | Medium | Run full `tests/test_dashboard/` suite after T011 |
| Legacy HTTP handler behavior changes | Medium | T010 is import-only; existing handler tests catch any regression |

## Reviewer Guidance

1. Check that `GlossaryService` has no `fastapi`, `starlette`, or `pydantic` imports.
2. Confirm each router handler body is ≤ 15 LOC (count lines in the `async def` body).
3. Verify parity tests actually assert equality (not just that the function doesn't raise).
4. Check `models.py` diff: only import lines and docstrings should change.
5. Run `pytest tests/test_dashboard/test_glossary_handler.py tests/specify_cli/glossary/ -v` and confirm green.

Implement command: `spec-kitty agent action implement WP02 --agent <name>`

## Activity Log

- 2026-05-04T17:38:03Z – copilot:claude-sonnet-4-6:alphonso:implementer – shell_pid=1956319 – Started implementation via action command
- 2026-05-04T17:42:37Z – copilot:claude-sonnet-4-6:alphonso:implementer – shell_pid=1956319 – GlossaryService extracted, router delegated, parity tests pass
- 2026-05-04T17:43:21Z – copilot:claude-sonnet-4-6:alphonso:reviewer – shell_pid=1960450 – Started review via action command
- 2026-05-04T17:45:42Z – copilot:claude-sonnet-4-6:alphonso:reviewer – shell_pid=1960450 – Review passed: GlossaryService correctly extracted, router delegates cleanly, tests pass
