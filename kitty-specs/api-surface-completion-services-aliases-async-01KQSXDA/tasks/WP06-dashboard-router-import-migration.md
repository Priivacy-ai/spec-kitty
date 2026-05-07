---
work_package_id: WP06
title: Dashboard Router Import Migration (Non-Primary)
dependencies:
- WP01
requirement_refs:
- FR-019
planning_base_branch: feature/645-api-surface-completion-mission-c
merge_target_branch: feature/645-api-surface-completion-mission-c
branch_strategy: Planning artifacts for this feature were generated on feature/645-api-surface-completion-mission-c. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/645-api-surface-completion-mission-c unless the human explicitly redirects the landing branch.
created_at: '2026-05-04T17:07:04Z'
subtasks:
- T027
- T028
- T029
- T030
- T031
- T032
agent: "copilot:claude-sonnet-4-6:alphonso:reviewer"
shell_pid: "1990781"
history:
- at: '2026-05-04T17:07:04Z'
  event: created
  note: Initial task breakdown
authoritative_surface: src/dashboard/api/routers/
execution_mode: code_change
lane: planned
mission_id: 01KQSXDASEMGGZNAX3A5FXSEPM
owned_files:
- src/dashboard/api/routers/health.py
- src/dashboard/api/routers/diagnostics.py
- src/dashboard/api/routers/sync.py
- src/dashboard/api/routers/artifacts.py
- src/dashboard/api/routers/missions.py
tags: []
---

## Objective

Update import statements in the five remaining FastAPI routers that still import from `dashboard.api_types`. WP04 already owns `features.py` and `kanban.py`; WP02 owns `glossary.py`; WP03 owns `lint.py`. This WP handles health, diagnostics, sync, artifacts, and missions — everything else in `src/dashboard/api/routers/`. After this WP, zero routers should import from `dashboard.api_types`.

## Context

These are mechanical import substitutions — no business logic changes. The work is safe to do in parallel with WP02, WP03, WP04, and WP05 because each targets different files.

**Migration map for this WP's routers:**

| Router file | Types imported from `dashboard.api_types` | New canonical location |
|------------|-------------------------------------------|------------------------|
| `health.py` | `HealthResponse`, `SyncInfo` | `kernel.api_types` |
| `diagnostics.py` | `FileIntegrity`, `DiagnosticsFeatureStatus`, `CurrentFeatureDetected`, `CurrentFeatureNotDetected`, `DashboardHealthInfo`, `DiagnosticsResponse`, `DiagnosticsErrorResponse` | `kernel.api_types` |
| `sync.py` | `SyncTriggerSuccess` | `kernel.api_types` |
| `artifacts.py` | `ArtifactDirectoryFile`, `ArtifactDirectoryResponse` | `dashboard.api.presentation_types` |
| `missions.py` | `MissionRecord` (and possibly others) | `specify_cli.missions.api_types` |

Note: `artifacts.py` is special — its types move to `dashboard.api.presentation_types` (within the dashboard package), not to a domain package. This is correct: file-browser shapes have no domain equivalent outside the dashboard UI.

## Branch Strategy

- `planning_base_branch`: `feature/645-api-surface-completion-mission-c`
- `merge_target_branch`: `feature/645-api-surface-completion-mission-c`
- WP01 must be merged to the lane branch before this WP starts.

## Subtask Guide

### T027: Update `src/dashboard/api/routers/health.py`

**Purpose:** Replace `HealthResponse` and `SyncInfo` imports from `dashboard.api_types` with `kernel.api_types`.

**Steps:**

1. Open `src/dashboard/api/routers/health.py`.

2. Find:
   ```python
   from dashboard.api_types import HealthResponse, SyncInfo
   ```

3. Replace with:
   ```python
   from kernel.api_types import HealthResponse, SyncInfo
   ```

4. Run mypy: `cd src && mypy --strict dashboard/api/routers/health.py`

5. Run: `cd src && python -c "from dashboard.api.routers.health import router; print('OK')"`

**Files:** `src/dashboard/api/routers/health.py` (update)

**Validation:**
- [x] No `from dashboard.api_types import` remains in this file
- [x] `from kernel.api_types import HealthResponse, SyncInfo` is present
- [x] `mypy --strict dashboard/api/routers/health.py` passes
- [x] Router imports without error

---

### T028: Update `src/dashboard/api/routers/diagnostics.py`

**Purpose:** Replace all seven diagnostics-related type imports from `dashboard.api_types` with `kernel.api_types`.

**Steps:**

1. Open `src/dashboard/api/routers/diagnostics.py`.

2. Find all `dashboard.api_types` imports (there may be multiple import lines or one multi-line import):
   ```python
   from dashboard.api_types import (
       FileIntegrity,
       DiagnosticsFeatureStatus,
       CurrentFeatureDetected,
       CurrentFeatureNotDetected,
       DashboardHealthInfo,
       DiagnosticsResponse,
       DiagnosticsErrorResponse,
   )
   ```

3. Replace with:
   ```python
   from kernel.api_types import (
       CurrentFeatureDetected,
       CurrentFeatureNotDetected,
       DashboardHealthInfo,
       DiagnosticsErrorResponse,
       DiagnosticsFeatureStatus,
       DiagnosticsResponse,
       FileIntegrity,
   )
   ```

4. Run mypy: `cd src && mypy --strict dashboard/api/routers/diagnostics.py`

5. Run: `cd src && python -c "from dashboard.api.routers.diagnostics import router; print('OK')"`

**Files:** `src/dashboard/api/routers/diagnostics.py` (update)

**Validation:**
- [x] No `from dashboard.api_types import` remains in this file
- [x] All seven types now import from `kernel.api_types`
- [x] `mypy --strict dashboard/api/routers/diagnostics.py` passes
- [x] Router imports without error

---

### T029: Update `src/dashboard/api/routers/sync.py`

**Purpose:** Replace `SyncTriggerSuccess` import from `dashboard.api_types` with `kernel.api_types`.

**Steps:**

1. Open `src/dashboard/api/routers/sync.py`.

2. Find:
   ```python
   from dashboard.api_types import SyncTriggerSuccess
   ```

3. Replace with:
   ```python
   from kernel.api_types import SyncTriggerSuccess
   ```

4. Run mypy: `cd src && mypy --strict dashboard/api/routers/sync.py`

**Files:** `src/dashboard/api/routers/sync.py` (update)

**Validation:**
- [x] No `from dashboard.api_types import` remains in this file
- [x] `from kernel.api_types import SyncTriggerSuccess` is present
- [x] `mypy --strict dashboard/api/routers/sync.py` passes

---

### T030: Update `src/dashboard/api/routers/artifacts.py`

**Purpose:** Replace `ArtifactDirectoryFile` and `ArtifactDirectoryResponse` imports from `dashboard.api_types` with `dashboard.api.presentation_types` (the new dashboard-presentation-only module created in WP01).

**Steps:**

1. Open `src/dashboard/api/routers/artifacts.py`.

2. Find:
   ```python
   from dashboard.api_types import ArtifactDirectoryFile, ArtifactDirectoryResponse
   ```

3. Replace with:
   ```python
   from dashboard.api.presentation_types import ArtifactDirectoryFile, ArtifactDirectoryResponse
   ```

4. Note: this is the **only** router whose types move within the `dashboard` package (not to a domain package). This is intentional — file-browser shapes have no domain equivalent outside the dashboard UI.

5. Run mypy: `cd src && mypy --strict dashboard/api/routers/artifacts.py`

6. Run: `cd src && python -c "from dashboard.api.routers.artifacts import router; print('OK')"`

**Files:** `src/dashboard/api/routers/artifacts.py` (update)

**Validation:**
- [x] No `from dashboard.api_types import` remains in this file
- [x] `from dashboard.api.presentation_types import ArtifactDirectoryFile, ArtifactDirectoryResponse` is present
- [x] `mypy --strict dashboard/api/routers/artifacts.py` passes
- [x] Router imports without error

---

### T031: Update `src/dashboard/api/routers/missions.py`

**Purpose:** Replace `MissionRecord` (and any related types) imported from `dashboard.api_types` with `specify_cli.missions.api_types`.

**Steps:**

1. Open `src/dashboard/api/routers/missions.py`.

2. Find all `dashboard.api_types` imports. Expected types: `MissionRecord`, possibly `FeaturesListResponse`, `FeatureItem`, `MissionContext`.

3. Replace with imports from `specify_cli.missions.api_types`:
   ```python
   from specify_cli.missions.api_types import (
       FeatureItem,
       FeaturesListResponse,
       MissionContext,
       MissionRecord,
   )
   ```
   (Adjust to include only what the file actually uses.)

4. Run mypy: `cd src && mypy --strict dashboard/api/routers/missions.py`

5. Run: `cd src && python -c "from dashboard.api.routers.missions import router; print('OK')"`

**Files:** `src/dashboard/api/routers/missions.py` (update)

**Validation:**
- [x] No `from dashboard.api_types import` remains in this file
- [x] All types import from `specify_cli.missions.api_types`
- [x] `mypy --strict dashboard/api/routers/missions.py` passes
- [x] Router imports without error

---

### T032: Audit Remaining Routers for Stray Imports

**Purpose:** Confirm that after T027–T031, zero routers in `src/dashboard/api/routers/` still import from `dashboard.api_types`. This audit is the gate condition for WP07's deletion step.

**Steps:**

1. Run:
   ```bash
   grep -rn "from dashboard.api_types\|import dashboard.api_types" \
     src/dashboard/api/routers/ --include="*.py"
   ```

2. Expected output: **no lines** (empty grep output, exit code 1).

3. If any file shows up, fix the remaining import before marking this WP done. Follow the same migration map:
   - Infrastructure types (health, sync, diagnostics) → `kernel.api_types`
   - Mission types → `specify_cli.missions.api_types`
   - Status/Kanban types → `specify_cli.status.api_types`
   - File-browser types → `dashboard.api.presentation_types`

4. Also run the broader check across all of `src/dashboard/`:
   ```bash
   grep -rn "from dashboard.api_types\|import dashboard.api_types" \
     src/dashboard/ --include="*.py"
   ```
   The only expected file that may still show hits is `src/dashboard/api_types.py` itself (the source file, which will be deleted in WP07).

5. Record the grep result in a commit message or WP history note as evidence for WP07.

**Files:** (audit only — no file modifications unless stragglers found)

**Validation:**
- [x] `grep -rn "from dashboard.api_types" src/dashboard/api/routers/ --include="*.py"` produces zero output
- [x] The only remaining reference to `dashboard.api_types` in `src/dashboard/` is the file itself

---

## Definition of Done

- [x] `health.py` imports `HealthResponse`, `SyncInfo` from `kernel.api_types`
- [x] `diagnostics.py` imports all seven diagnostics types from `kernel.api_types`
- [x] `sync.py` imports `SyncTriggerSuccess` from `kernel.api_types`
- [x] `artifacts.py` imports `ArtifactDirectoryFile`, `ArtifactDirectoryResponse` from `dashboard.api.presentation_types`
- [x] `missions.py` imports mission types from `specify_cli.missions.api_types`
- [x] T032 grep audit confirms zero remaining `dashboard.api_types` imports in `src/dashboard/api/routers/`
- [x] `mypy --strict` passes on all five updated routers
- [x] All five routers import without error

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| A router imports a type not in the migration map | Medium | T032 grep audit catches any stragglers; extend the map if needed |
| `missions.py` uses more types than expected | Low | Read the full file before writing the replacement import |
| `artifacts.py` imports `ArtifactDirectoryFile` from `dashboard.api_types` in multiple places | Low | grep the file for all occurrences before replacing |

## Reviewer Guidance

1. Run T032's grep command and confirm zero output.
2. Run `mypy --strict src/dashboard/api/routers/health.py src/dashboard/api/routers/diagnostics.py src/dashboard/api/routers/sync.py src/dashboard/api/routers/artifacts.py src/dashboard/api/routers/missions.py` and confirm clean.
3. Confirm `artifacts.py` imports from `dashboard.api.presentation_types`, not from a domain package (this is intentional and correct).
4. Run `pytest tests/test_dashboard/ -v` and confirm green.

Implement command: `spec-kitty agent action implement WP06 --agent <name>`

## Activity Log

- 2026-05-04T18:04:12Z – copilot:claude-sonnet-4-6:alphonso:implementer – shell_pid=1986578 – Started implementation via action command
- 2026-05-04T18:06:12Z – copilot:claude-sonnet-4-6:alphonso:implementer – shell_pid=1986578 – All remaining router imports migrated to canonical type locations; all 326 tests pass
- 2026-05-04T18:06:34Z – copilot:claude-sonnet-4-6:alphonso:reviewer – shell_pid=1990781 – Started review via action command
- 2026-05-04T18:07:25Z – copilot:claude-sonnet-4-6:alphonso:reviewer – shell_pid=1990781 – Review passed: confirmed zero dashboard.api_types imports remain in routers; all router tests pass
