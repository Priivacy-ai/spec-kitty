---
description: "Work package task list for dashboard-services-domain-migration-01KR151P"
---

# Work Packages: Dashboard Services Domain Migration (Phase B)

**Inputs**: Design documents from `/kitty-specs/dashboard-services-domain-migration-01KR151P/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, quickstart.md ✓

**Lane layout**:
```
Lane A: WP01 → WP02 → WP04
Lane B:         WP03
```
WP03 has no dependency on WP01/WP02 and can proceed in parallel with WP02.
WP04 depends on all three (removes boundary-test exemptions only valid after all callers fixed).

---

## Work Package WP01: Registry Migration and Cache Fixes (Priority: P0)

**Goal**: Move `MissionRegistry`, `WorkPackageRegistry`, and all supporting classes to
`specify_cli/missions/registry.py`; apply the P1 two-level cache fix and P2 strong-reference
store fix; leave a compatibility shim at `dashboard/services/registry.py`; update the one
`specify_cli/` caller (`cli/commands/dashboard.py`).

**Independent Test**: After WP01, `pytest tests/specify_cli/missions/ tests/specify_cli/cli/`
passes; the P1 regression test (appending an event invalidates the list cache) passes; the
P2 identity test passes; existing registry seam tests green.

**Prompt**: `tasks/WP01-registry-migration-and-cache-fixes.md`
**Requirement Refs**: FR-001, FR-002, FR-003, FR-007, FR-010, NFR-001, NFR-002, NFR-004, C-001, C-002, C-004, C-005

### Included Subtasks
- [x] T001 Create `src/specify_cli/missions/registry.py` with full canonical implementation (move from `dashboard/services/registry.py`)
- [x] T002 Apply P1 fix — add `_per_mission_cache: dict[Path, CacheEntry[MissionRecord]]` and update `list_missions()` to use two-level cache
- [x] T003 Apply P2 fix — replace `WeakValueDictionary[str, WorkPackageRegistry]` with `dict[str, WorkPackageRegistry]`; update `workpackages_for()` and remove `weakref` import
- [x] T004 Convert `src/dashboard/services/registry.py` to compatibility shim (re-exports from `specify_cli.missions.registry`); add SHIM comment
- [x] T005 Update `src/specify_cli/cli/commands/dashboard.py` — both `MissionRecord` (TYPE_CHECKING) and `MissionRegistry` (runtime deferred) imports point to `specify_cli.missions.registry`

### Implementation Notes
- The new module is a self-contained copy plus two targeted edits (P1 field + algorithm, P2 dict swap).
- `weakref` import is removed entirely from the new canonical module.
- Shim must export all symbols currently in `dashboard.services.__init__` re-export list.
- `dashboard/services/__init__.py` is NOT changed (it imports from the registry shim transitively).

### Parallel Opportunities
- T002 and T003 are independent edits to different parts of `MissionRegistry`; can be done in any order.
- T004 and T005 are independent of each other.

### Dependencies
- None (starting package).

### Risks & Mitigations
- **Risk**: Missing a public symbol in the shim causes an `ImportError` at startup.
  - **Mitigation**: After writing the shim, run `python -c "from dashboard.services.registry import *"` to verify.
- **Risk**: P1 algorithm introduces a double-lock acquisition.
  - **Mitigation**: Follow the double-checked locking pattern in `data-model.md § 1`; the outer check happens outside the lock; the inner check after acquiring.

---

## Work Package WP02: MissionScanService Migration (Priority: P0)

**Goal**: Move `MissionScanService` and `parse_kanban_path` to
`specify_cli/missions/scan_service.py`; fix the runtime `dashboard.services.registry` import
inside `__init__`; leave a shim at `dashboard/services/mission_scan.py`; update the one
`specify_cli/` caller (`dashboard/handlers/features.py`).

**Independent Test**: `pytest tests/test_dashboard/test_seams.py -k features` passes;
`grep -rn "from dashboard" src/specify_cli/dashboard/handlers/features.py` returns empty.

**Prompt**: `tasks/WP02-missionscanservice-migration.md`
**Requirement Refs**: FR-004, FR-008, FR-011, NFR-001, NFR-002, C-001, C-002, C-004

### Included Subtasks
- [x] T006 Create `src/specify_cli/missions/scan_service.py` with full `MissionScanService` and `parse_kanban_path` implementations
- [x] T007 Fix TYPE_CHECKING import in `scan_service.py` — update to `from specify_cli.missions.registry import MissionRecord, MissionRegistry`
- [x] T008 Fix runtime deferred import in `MissionScanService.__init__` — update `from dashboard.services.registry import MissionRegistry` to `from specify_cli.missions.registry import MissionRegistry`
- [x] T009 Convert `src/dashboard/services/mission_scan.py` to compatibility shim
- [x] T010 Update `src/specify_cli/dashboard/handlers/features.py` — both deferred import sites to `specify_cli.missions.scan_service`

### Implementation Notes
- T007 and T008 both live inside the new `scan_service.py` (not the old file); fix them during the copy, not after.
- `features.py` has two separate deferred import blocks (lines ~35 and ~58 in the original); both must be updated.
- The shim must export `MissionScanService` and `parse_kanban_path`.

### Parallel Opportunities
- T009 and T010 are independent; can proceed after T006–T008 are done.

### Dependencies
- WP01 — `MissionScanService.__init__` default `registry` fallback imports `MissionRegistry`; the canonical path must exist before this WP's `scan_service.py` is functional.

### Risks & Mitigations
- **Risk**: The runtime import inside `__init__` is deferred (inside the constructor body), not top-level. If forgotten, a `ModuleNotFoundError` only appears at service instantiation, not import time.
  - **Mitigation**: Explicitly grep the new file for `dashboard.services` before committing.

---

## Work Package WP03: ProjectStateService and SyncService Migration (Priority: P0)

**Goal**: Move `ProjectStateService` to `specify_cli/missions/project_state.py` and
`SyncService` + `SyncTriggerResult` + `_build_trigger_request` to
`specify_cli/missions/sync_service.py`; leave shims at both original locations; update
`specify_cli/dashboard/handlers/api.py`, preserving the `_build_sync_trigger_request`
re-export for seam-test compatibility.

**Independent Test**: `pytest tests/test_dashboard/test_seams.py -k "health or sync"` passes;
`grep -rn "from dashboard" src/specify_cli/dashboard/handlers/api.py` returns empty.

**Prompt**: `tasks/WP03-projectstateservice-and-syncservice-migration.md`
**Requirement Refs**: FR-005, FR-006, FR-008, FR-012, NFR-001, NFR-002, C-001, C-002, C-004, C-007

### Included Subtasks
- [x] T011 Create `src/specify_cli/missions/project_state.py` — copy `ProjectStateService` verbatim (no `dashboard.*` imports present; confirm before copying)
- [x] T012 Create `src/specify_cli/missions/sync_service.py` — copy `SyncService`, `SyncTriggerResult`, `_build_trigger_request`, and all helpers; confirm no `dashboard.*` imports
- [x] T013 Convert `src/dashboard/services/project_state.py` to compatibility shim
- [x] T014 Convert `src/dashboard/services/sync.py` to compatibility shim; preserve explicit `__all__` including `_build_trigger_request` (required for re-export compat)
- [x] T015 Update `src/specify_cli/dashboard/handlers/api.py` — top-level import of `_build_trigger_request`, two deferred imports of `ProjectStateService` and `SyncService` — all point to `specify_cli.missions.*`; re-export alias `_build_sync_trigger_request` preserved

### Implementation Notes
- `project_state.py` and `sync.py` have no `dashboard.*` imports internally; the copy is straightforward.
- `handlers/api.py` has one TOP-LEVEL import (not deferred): `from dashboard.services.sync import _build_trigger_request as _build_sync_trigger_request`. This becomes `from specify_cli.missions.sync_service import _build_trigger_request as _build_sync_trigger_request`.
- The re-export alias `_build_sync_trigger_request` at module level in `handlers/api.py` is preserved for seam tests that mock it.

### Parallel Opportunities
- T011 and T012 can be done simultaneously (different files).
- T013 and T014 are independent.
- T015 is independent of T011–T014 (only import paths change).

### Dependencies
- None — `ProjectStateService` and `SyncService` have no dependency on `MissionRegistry`.

### Risks & Mitigations
- **Risk**: Sync shim drops `_build_trigger_request` from `__all__`, breaking seam-test mocking.
  - **Mitigation**: Explicitly include `_build_trigger_request` in the shim's `__all__`; run seam tests after WP03.

---

## Work Package WP04: API Consumers, Shim Registry, Tests, and ADR (Priority: P1)

**Goal**: Update all `dashboard/api/` consumers to import directly from
`specify_cli.missions.*`; register all four shims in `shim-registry.yaml`; tighten the
`test_no_upstream_dashboard_imports` boundary test by removing (or narrowing) exemptions
now that all violations are fixed; write the P1 and P2 regression tests; file the Phase B ADR.

**Independent Test**: `spec-kitty doctor shim-registry` exits clean; `pytest tests/architectural/test_dashboard_boundary.py` passes with no violations and the synthetic violation test catches the fake import; P1 and P2 tests pass; OpenAPI snapshot test passes unchanged.

**Prompt**: `tasks/WP04-api-consumers-shim-registry-tests-adr.md`
**Requirement Refs**: FR-009, FR-013, FR-014, FR-015, FR-016, FR-017, NFR-001, NFR-002, NFR-005, C-002, C-006

### Included Subtasks
- [x] T016 [P] Update `src/dashboard/api/app.py` and `src/dashboard/api/deps.py` — `MissionRegistry` from `specify_cli.missions.registry`
- [x] T017 [P] Update `src/dashboard/api/routers/missions.py`, `health.py`, `sync.py` — service symbols from `specify_cli.missions.*`
- [x] T018 Register 4 shims in `architecture/2.x/shim-registry.yaml` (replace `shims: []` with 4 entries from `data-model.md § 4`)
- [x] T019 Tighten `tests/architectural/test_dashboard_boundary.py::test_no_upstream_dashboard_imports` — remove `dashboard.py` from `_ALLOWED_BOUNDARY_FILES`; narrow or remove the `specify_cli/dashboard/` broad exclusion; add synthetic violation fixture test
- [x] T020 Write `tests/specify_cli/missions/test_registry_cache.py` — P1 regression: append event, assert `list_missions()` returns fresh lane counts
- [x] T021 Write P2 regression in same file — `workpackages_for()` returns same `WorkPackageRegistry` instance on second call (identity check)
- [x] T022 File `architecture/2.x/adr/2026-05-07-1-dashboard-services-phase-b.md`; add cross-link in `architecture/2.x/adr/README.md`

### Implementation Notes
- T016 and T017 are parallel (different files/routers).
- T019: after all callers are fixed, `grep -rn "from dashboard" src/specify_cli/` should only show `specify_cli/dashboard/` bridge files that are legitimately excluded (if any remain). Remove the broad exclusion if the handlers are clean; otherwise add only the remaining legitimate files to `_ALLOWED_BOUNDARY_FILES`.
- T020/T021 live in `tests/specify_cli/missions/test_registry_cache.py`; the directory already exists.
- ADR sections: Context, Decision, Rationale, Consequences, Phase C plan (shim retirement), Relationship to #992.

### Parallel Opportunities
- T016, T017, T018 are independent of each other and T019–T022; run all in parallel.
- T020 and T021 are independent (different test functions in the same file).
- T022 is independent of T016–T021.

### Dependencies
- Depends on WP01, WP02, WP03 — exemption removal in T019 only holds once all callers are fixed.

### Risks & Mitigations
- **Risk**: `specify_cli/dashboard/` still has legitimate `dashboard.*` imports after WP02/WP03 (e.g., `dashboard.file_reader`). Removing the broad exclusion would create false positives.
  - **Mitigation**: Before narrowing the exclusion, run `grep -rn "from dashboard" src/specify_cli/dashboard/` and review each hit. Add only legitimately bridge files to `_ALLOWED_BOUNDARY_FILES`; the broad exclusion can then be removed.
- **Risk**: P1 regression test is non-deterministic due to filesystem mtime granularity (mtime_ns has 1 ns precision on Linux but may be coarser on macOS/Windows).
  - **Mitigation**: After appending the event, `os.utime()` the file with `st_mtime_ns + 1` to guarantee a different mtime. Or write the test to compare `CacheEntry.cache_key` before and after rather than relying on mtime change.
