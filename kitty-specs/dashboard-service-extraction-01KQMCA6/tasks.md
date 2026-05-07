# Tasks: Dashboard Service Extraction

*Path: [kitty-specs/dashboard-service-extraction-01KQMCA6/tasks.md](tasks.md)*

**Branch**: `feature/650-dashboard-ui-ux-overhaul`
**Mission**: `dashboard-service-extraction-01KQMCA6`
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Data model**: [data-model.md](data-model.md)

---

## Subtask Index

| ID | Description | WP | Parallel? |
|---|---|---|---|
| T001 | Add `dashboard` slice entry to `05_ownership_map.md` (Audience A procedure) | WP01 | — | [D] |
| T002 | Add `dashboard` key to `05_ownership_manifest.yaml` | WP01 | [D] |
| T003 | Draft ADR `architecture/2.x/adr/2026-05-02-1-dashboard-service-extraction.md` | WP01 | — | [D] |
| T004 | Cross-link ADR from ownership map entry and from `architecture/2.x/adr/README.md` | WP01 | [D] |
| T005 | Create `src/dashboard/__init__.py` and `src/dashboard/services/__init__.py` | WP02 | — | [D] |
| T006 | Move `api_types.py` to `src/dashboard/api_types.py` | WP02 | — | [D] |
| T007 | Create backward-compat shim at `src/specify_cli/dashboard/api_types.py` | WP02 | — | [D] |
| T008 | Verify all existing imports resolve through the shim (mypy + test run) | WP02 | — | [D] |
| T009 | Register `dashboard` in `test_layer_rules.py` `_DEFINED_LAYERS` | WP02 | [D] |
| T010 | Confirm `src/dashboard/` is discovered by the editable install | WP02 | [D] |
| T011 | Create `src/dashboard/services/mission_scan.py` with `MissionScanService` | WP03 | — | [D] |
| T012 | Extract `get_features_list` logic from `handle_features_list` | WP03 | — | [D] |
| T013 | Extract `get_kanban` logic from `handle_kanban` | WP03 | — | [D] |
| T014 | Create `src/dashboard/file_reader.py` with `DashboardFileReader` | WP03 | [D] |
| T015 | Thin `handle_features_list` and `handle_kanban` to single-call delegation | WP03 | — | [D] |
| T016 | Thin `handle_research`, `handle_contracts`, `handle_checklists`, `handle_artifact` | WP03 | [D] |
| T017 | Create `src/dashboard/services/project_state.py` with `ProjectStateService` | WP04 | — |
| T018 | Extract health logic from `handle_health` to `ProjectStateService.get_health` | WP04 | — |
| T019 | Thin `handle_health` to delegate to `ProjectStateService` | WP04 | — |
| T020 | Create `src/dashboard/services/sync.py` with `SyncService` + `SyncTriggerResult` | WP04 | — |
| T021 | Extract sync orchestration from `handle_sync_trigger` to `SyncService.trigger_sync` | WP04 | — |
| T022 | Thin `handle_sync_trigger` — token check in adapter, delegate to `SyncService` | WP04 | — |
| T023 | Create `tests/architectural/test_dashboard_boundary.py` | WP05 | — | [D] |
| T024 | Create seam tests for `MissionScanService` routes (`features`, `kanban`) | WP05 | — | [D] |
| T025 | Create seam tests for `ProjectStateService` route (`health`) | WP05 | [D] |
| T026 | Create seam tests for `SyncService` route (`sync/trigger`) | WP05 | [D] |
| T027 | Run full test suite; confirm zero regressions (FR-011, SC-002) | WP05 | — | [D] |
| T028 | Audit `dashboard.js` field references against `api_types.py` TypedDicts | WP06 | — | [D] |
| T029 | Verify no field drift introduced by extraction (pre/post snapshot comparison) | WP06 | — | [D] |
| T030 | Smoke-test running dashboard — all panels load correctly (SC-006) | WP06 | — | [D] |

**Total**: 30 subtasks across 6 WPs (avg 5 per WP)

---

## Phase 1 — Governance (must land before any code change)

### WP01 — Governance Artifacts

**Priority**: P0 (gate for all other WPs)
**Estimated prompt size**: ~220 lines
**Dependencies**: none
**Owned files**: `architecture/2.x/05_ownership_map.md`, `architecture/2.x/05_ownership_manifest.yaml`, `architecture/2.x/adr/2026-05-02-1-dashboard-service-extraction.md`
**Prompt**: [tasks/WP01-governance-artifacts.md](tasks/WP01-governance-artifacts.md)

**Goal**: Register the dashboard as a first-class slice in the functional ownership map,
add the machine-readable manifest key, and draft the ADR documenting the extraction decision.
This satisfies FR-001, FR-002, FR-003, and the Audience A governance gate.

**Included subtasks**:
- [x] T001 Add `dashboard` slice entry to `05_ownership_map.md` (Audience A procedure) (WP01)
- [x] T002 Add `dashboard` key to `05_ownership_manifest.yaml` (WP01)
- [x] T003 Draft ADR `architecture/2.x/adr/2026-05-02-1-dashboard-service-extraction.md` (WP01)
- [x] T004 Cross-link ADR from ownership map entry and `architecture/2.x/adr/README.md` (WP01)

**Success criterion**: `05_ownership_manifest.yaml` parses without error; ADR is present at
canonical path and cross-linked; ownership map entry passes Audience A field checklist.

**Risk**: Manifest schema test failure if field names don't match the schema. Read
`tests/architectural/test_ownership_manifest_schema.py` before writing the manifest entry.

---

## Phase 2 — Scaffold (enables parallel extraction)

### WP02 — Package Scaffold and `api_types.py` Relocation

**Priority**: P0 (gate for WP03, WP04)
**Estimated prompt size**: ~280 lines
**Dependencies**: WP01
**Owned files**: `src/dashboard/__init__.py`, `src/dashboard/api_types.py`, `src/dashboard/services/__init__.py`, `src/specify_cli/dashboard/api_types.py`, `tests/architectural/test_layer_rules.py`
**Prompt**: [tasks/WP02-package-scaffold.md](tasks/WP02-package-scaffold.md)

**Goal**: Create the `src/dashboard/` package skeleton, relocate `api_types.py` to its
canonical home, install a backward-compat shim at the old path, and register `dashboard`
as a known architectural layer.

**Included subtasks**:
- [x] T005 Create `src/dashboard/__init__.py` and `src/dashboard/services/__init__.py` (WP02)
- [x] T006 Move `api_types.py` to `src/dashboard/api_types.py` (WP02)
- [x] T007 Create backward-compat shim at `src/specify_cli/dashboard/api_types.py` (WP02)
- [x] T008 Verify all existing imports resolve through the shim (mypy + test run) (WP02)
- [x] T009 Register `dashboard` in `test_layer_rules.py` `_DEFINED_LAYERS` (WP02)
- [x] T010 Confirm `src/dashboard/` is discovered by the editable install (WP02)

**Success criterion**: `python -c "from dashboard.api_types import HealthResponse"` succeeds;
`python -c "from specify_cli.dashboard.api_types import HealthResponse"` succeeds (shim);
all pre-extraction tests still pass; `dashboard` appears in `_DEFINED_LAYERS`.

---

## Phase 3 — Service Extractions (WP03 and WP04 parallel)

### WP03 — MissionScanService + DashboardFileReader (features.py)

**Priority**: P1
**Estimated prompt size**: ~360 lines
**Dependencies**: WP02
**Owned files**: `src/dashboard/services/mission_scan.py`, `src/dashboard/file_reader.py`, `src/specify_cli/dashboard/handlers/features.py`
**Prompt**: [tasks/WP03-mission-scan-service.md](tasks/WP03-mission-scan-service.md)

**Goal**: Extract all inline business logic from `features.py` into `MissionScanService`
(scan + kanban) and `DashboardFileReader` (file-serving I/O). Thin handler methods to
single delegation calls.

**Included subtasks**:
- [x] T011 Create `src/dashboard/services/mission_scan.py` with `MissionScanService` (WP03)
- [x] T012 Extract `get_features_list` logic from `handle_features_list` (WP03)
- [x] T013 Extract `get_kanban` logic from `handle_kanban` (WP03)
- [x] T014 Create `src/dashboard/file_reader.py` with `DashboardFileReader` (WP03)
- [x] T015 Thin `handle_features_list` and `handle_kanban` to single-call delegation (WP03)
- [x] T016 Thin `handle_research`, `handle_contracts`, `handle_checklists`, `handle_artifact` (WP03)

**Parallel opportunity**: T014 (DashboardFileReader creation) is parallel-safe relative to T011-T013 since it touches a different file.

**Success criterion**: Each thinned handler body contains only dispatch and a single call to
a service object. Existing `tests/test_dashboard/` pass without modification.

**Risk**: `is_legacy_format` import — currently in adapter; keep it in `MissionScanService`
constructor or as a utility call from the service, not from the adapter.

---

### WP04 — ProjectStateService + SyncService (api.py)

**Priority**: P1
**Estimated prompt size**: ~350 lines
**Dependencies**: WP02
**Owned files**: `src/dashboard/services/project_state.py`, `src/dashboard/services/sync.py`, `src/specify_cli/dashboard/handlers/api.py`
**Prompt**: [tasks/WP04-api-services.md](tasks/WP04-api-services.md)

**Goal**: Extract health-response assembly and sync orchestration from `api.py` into
`ProjectStateService` and `SyncService`. Token-validation logic stays in the adapter.
Both handler methods become single-call delegations.

**Included subtasks**:
- [ ] T017 Create `src/dashboard/services/project_state.py` with `ProjectStateService` (WP04)
- [ ] T018 Extract health logic from `handle_health` to `ProjectStateService.get_health` (WP04)
- [ ] T019 Thin `handle_health` to delegate to `ProjectStateService` (WP04)
- [ ] T020 Create `src/dashboard/services/sync.py` with `SyncService` + `SyncTriggerResult` (WP04)
- [ ] T021 Extract sync orchestration from `handle_sync_trigger` to `SyncService.trigger_sync` (WP04)
- [ ] T022 Thin `handle_sync_trigger` — token check in adapter, delegate to `SyncService` (WP04)

**Parallel opportunity**: WP04 is parallel with WP03 (different handler files).

**Success criterion**: `handle_health` and `handle_sync_trigger` contain no inline business
logic. `_build_sync_trigger_request` moves into `sync.py` or is inlined there. Existing
tests pass.

**Risk**: `_build_sync_trigger_request` is a module-level helper in `api.py` that enforces
the localhost-only invariant. Move it into `SyncService.trigger_sync` so the invariant stays
with the logic that uses it.

---

## Phase 4 — Verification

### WP05 — Boundary Test + Seam Tests

**Priority**: P1
**Estimated prompt size**: ~330 lines
**Dependencies**: WP03, WP04
**Owned files**: `tests/architectural/test_dashboard_boundary.py`, `tests/test_dashboard/test_seams.py`
**Prompt**: [tasks/WP05-tests.md](tasks/WP05-tests.md)

**Goal**: Add the architectural boundary assertion (no circular imports between service
layer and its adapter) and per-route seam tests verifying that each handler method
delegates correctly to the expected service object.

**Included subtasks**:
- [x] T023 Create `tests/architectural/test_dashboard_boundary.py` (WP05)
- [x] T024 Create seam tests for `MissionScanService` routes (`features`, `kanban`) (WP05)
- [x] T025 Create seam tests for `ProjectStateService` route (`health`) (WP05)
- [x] T026 Create seam tests for `SyncService` route (`sync/trigger`) (WP05)
- [x] T027 Run full test suite; confirm zero regressions (FR-011, SC-002) (WP05)

**Success criterion**: `test_dashboard_boundary.py` passes with zero violations;
`test_seams.py` has one test per extracted route; all 16 pre-existing `tests/test_dashboard/`
tests pass.

---

## Phase 5 — Frontend Verification

### WP06 — dashboard.js Audit + Smoke Test

**Priority**: P1
**Estimated prompt size**: ~170 lines
**Dependencies**: WP05
**Owned files**: `src/specify_cli/dashboard/static/dashboard/dashboard.js`
**Prompt**: [tasks/WP06-dashboard-js-audit.md](tasks/WP06-dashboard-js-audit.md)

**Goal**: Verify the extraction introduced no field drift from the perspective of
`dashboard.js`. Audit all fetch calls and property accesses against the stabilised
`api_types.py` TypedDicts. Smoke-test the running dashboard to confirm SC-006.

**Included subtasks**:
- [x] T028 Audit `dashboard.js` field references against `api_types.py` TypedDicts (WP06)
- [x] T029 Verify no field drift introduced by extraction (pre/post snapshot comparison) (WP06)
- [x] T030 Smoke-test running dashboard — all panels load correctly (SC-006) (WP06)

**Expected outcome**: Zero changes to `dashboard.js` beyond confirming the audit passed.
Any drift discovered is documented as a pre-existing issue.

---

## Parallelization Summary

```
WP01 (governance)
  └── WP02 (scaffold)
        ├── WP03 (features.py extract)  ─┐ parallel
        └── WP04 (api.py extract)       ─┘
              └── WP05 (tests)
                    └── WP06 (JS audit)
```

**Parallel lanes**:
- **Lane A**: WP01 → WP02 → WP03 → WP05 → WP06
- **Lane B**: (wait for WP02) → WP04 → (merge into Lane A after WP04 done)

WP03 and WP04 can run simultaneously in two worktrees after WP02 lands.

---

## MVP Scope

Minimum to satisfy SC-001 through SC-005 (all governance + behavioral invariants):
**WP01 + WP02 + WP03 + WP04 + WP05**

WP06 satisfies SC-006 (operator smoke-test) but does not modify source code.
