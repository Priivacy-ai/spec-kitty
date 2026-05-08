---
work_package_id: WP05
title: Dashboard Services Import Migration
dependencies:
- WP01
requirement_refs:
- FR-019
planning_base_branch: feature/645-api-surface-completion-mission-c
merge_target_branch: feature/645-api-surface-completion-mission-c
branch_strategy: Planning artifacts for this feature were generated on feature/645-api-surface-completion-mission-c. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/645-api-surface-completion-mission-c unless the human explicitly redirects the landing branch.
created_at: '2026-05-04T17:07:04Z'
subtasks:
- T022
- T023
- T024
- T025
- T026
agent: "copilot:claude-sonnet-4-6:alphonso:reviewer"
shell_pid: "1983935"
history:
- at: '2026-05-04T17:07:04Z'
  event: created
  note: Initial task breakdown
authoritative_surface: src/dashboard/services/
execution_mode: code_change
lane: planned
mission_id: 01KQSXDASEMGGZNAX3A5FXSEPM
owned_files:
- src/dashboard/services/mission_scan.py
- src/dashboard/services/project_state.py
- src/dashboard/services/registry.py
- src/dashboard/file_reader.py
- src/specify_cli/dashboard/api_types.py
tags: []
---

## Objective

Update all callers in `dashboard/services/`, `dashboard/file_reader.py`, and `specify_cli/dashboard/api_types.py` (the legacy shim) to import TypedDicts from their new canonical locations established in WP01. This clears the path for WP07 to delete `src/dashboard/api_types.py`.

## Context

After WP01 creates the six canonical type modules, four service/utility files in the dashboard package still import from `dashboard.api_types`. Additionally, the legacy shim at `src/specify_cli/dashboard/api_types.py` re-exports everything from `dashboard.api_types`. Both sets of callers must be updated.

**Migration map** (from `research.md` section A categorisation table):

| Type | Old location | New location |
|------|-------------|--------------|
| `MissionRecord` | `dashboard.api_types` | `specify_cli.missions.api_types` |
| `FeatureItem` | `dashboard.api_types` | `specify_cli.missions.api_types` |
| `WorktreeInfo` | `dashboard.api_types` | `specify_cli.missions.api_types` |
| `WorkflowStatus` | `dashboard.api_types` | `specify_cli.missions.api_types` |
| `ArtifactInfo` | `dashboard.api_types` | `specify_cli.missions.api_types` |
| `ResearchArtifact` | `dashboard.api_types` | `specify_cli.missions.api_types` |
| `ResearchResponse` | `dashboard.api_types` | `specify_cli.missions.api_types` |
| `KanbanTaskData` | `dashboard.api_types` | `specify_cli.status.api_types` |
| `KanbanStats` | `dashboard.api_types` | `specify_cli.status.api_types` |
| `KanbanResponse` | `dashboard.api_types` | `specify_cli.status.api_types` |
| `MissionContext` | `dashboard.api_types` | `specify_cli.missions.api_types` |
| `ErrorResponse` | `dashboard.api_types` | `kernel.api_types` |

This WP can run in parallel with WP02, WP03, WP04, and WP06 — all are independent after WP01.

## Branch Strategy

- `planning_base_branch`: `feature/645-api-surface-completion-mission-c`
- `merge_target_branch`: `feature/645-api-surface-completion-mission-c`
- WP01 must be merged to the lane branch before this WP starts.

## Subtask Guide

### T022: Update `src/dashboard/services/mission_scan.py`

**Purpose:** Replace all `from dashboard.api_types import ...` with imports from the new canonical locations. `mission_scan.py` is the heaviest consumer of mission-domain types.

**Steps:**

1. Open `src/dashboard/services/mission_scan.py` and identify every `dashboard.api_types` import.

2. Replace with the correct canonical imports. Typical before/after:

```python
# Before (one or more import lines):
from dashboard.api_types import (
    MissionRecord,
    FeatureItem,
    WorktreeInfo,
    WorkflowStatus,
    ArtifactInfo,
    KanbanTaskData,
    KanbanStats,
    KanbanResponse,
    ResearchArtifact,
    ResearchResponse,
)

# After:
from specify_cli.missions.api_types import (
    ArtifactInfo,
    FeatureItem,
    MissionRecord,
    ResearchArtifact,
    ResearchResponse,
    WorkflowStatus,
    WorktreeInfo,
)
from specify_cli.status.api_types import (
    KanbanResponse,
    KanbanStats,
    KanbanTaskData,
)
```

3. Run mypy: `cd src && mypy --strict dashboard/services/mission_scan.py`

4. Fix any remaining type errors.

5. Run tests: `cd src && pytest ../tests/test_dashboard/ -k "mission_scan or scanner" -v`

**Files:** `src/dashboard/services/mission_scan.py` (update)

**Validation:**
- [x] No `from dashboard.api_types import` remains in this file
- [x] All moved types import from their canonical location
- [x] `mypy --strict dashboard/services/mission_scan.py` passes
- [x] Related tests pass

---

### T023: Update `src/dashboard/services/project_state.py`

**Purpose:** Replace `dashboard.api_types` imports with canonical locations for mission and kernel types.

**Steps:**

1. Open `src/dashboard/services/project_state.py` and identify every `dashboard.api_types` import.

2. Determine which types are used (likely `MissionContext`, `FeaturesListResponse`, or `HealthResponse`/`SyncInfo`). Replace:

```python
# Before:
from dashboard.api_types import MissionContext, HealthResponse, SyncInfo

# After:
from specify_cli.missions.api_types import MissionContext
from kernel.api_types import HealthResponse, SyncInfo
```

3. Run mypy: `cd src && mypy --strict dashboard/services/project_state.py`

4. Fix any remaining type errors.

**Files:** `src/dashboard/services/project_state.py` (update)

**Validation:**
- [x] No `from dashboard.api_types import` remains in this file
- [x] `mypy --strict dashboard/services/project_state.py` passes

---

### T024: Update `src/dashboard/services/registry.py`

**Purpose:** Replace `dashboard.api_types` imports with canonical locations for mission registry types.

**Steps:**

1. Open `src/dashboard/services/registry.py` and identify imports from `dashboard.api_types`.

2. Replace (expected types: `MissionRecord`, `MissionContext`):

```python
# Before:
from dashboard.api_types import MissionRecord, MissionContext

# After:
from specify_cli.missions.api_types import MissionContext, MissionRecord
```

3. Run mypy: `cd src && mypy --strict dashboard/services/registry.py`

**Files:** `src/dashboard/services/registry.py` (update)

**Validation:**
- [x] No `from dashboard.api_types import` remains in this file
- [x] `mypy --strict dashboard/services/registry.py` passes

---

### T025: Update `src/dashboard/file_reader.py`

**Purpose:** Replace `dashboard.api_types` imports (expected: `ErrorResponse`) with `kernel.api_types`.

**Steps:**

1. Open `src/dashboard/file_reader.py` and identify imports from `dashboard.api_types`.

2. Replace:

```python
# Before:
from dashboard.api_types import ErrorResponse

# After:
from kernel.api_types import ErrorResponse
```

3. Run mypy: `cd src && mypy --strict dashboard/file_reader.py`

**Files:** `src/dashboard/file_reader.py` (update)

**Validation:**
- [x] No `from dashboard.api_types import` remains in this file
- [x] `mypy --strict dashboard/file_reader.py` passes

---

### T026: Update or Delete `src/specify_cli/dashboard/api_types.py` (Shim)

**Purpose:** The shim at `src/specify_cli/dashboard/api_types.py` currently re-exports everything from `dashboard.api_types`. After WP01 establishes canonical locations, each re-export should point to the new canonical location. If the shim becomes a no-op (all re-exports updated, nothing left from `dashboard.api_types`), delete the file entirely.

**Steps:**

1. Read `src/specify_cli/dashboard/api_types.py` fully.

2. For each re-export like:
   ```python
   from dashboard.api_types import GlossaryTermRecord, GlossaryHealthResponse
   ```
   Update to:
   ```python
   from specify_cli.glossary.types import GlossaryTermRecord, GlossaryHealthResponse
   ```

3. Apply the full migration map to every import in the shim. After all updates, the shim should have zero remaining imports from `dashboard.api_types`.

4. If the shim now only re-exports from canonical locations (which is what it should do after this step), check whether any file still imports from `specify_cli.dashboard.api_types`. Run:
   ```bash
   grep -r "from specify_cli.dashboard.api_types\|from ..api_types\|from ...dashboard.api_types" src/ tests/ --include="*.py"
   ```

5. If no files import from the shim (they've all been updated by WP02/WP03/T010/T015), delete the shim file.

6. If files still import from the shim and cannot be changed in this WP, update the shim's re-exports to point to canonical locations and leave the file in place for WP07 to clean up.

7. Run: `cd src && pytest ../tests/specify_cli/dashboard/ -v` to confirm no regressions.

**Files:** `src/specify_cli/dashboard/api_types.py` (update or delete)

**Validation:**
- [x] No imports from `dashboard.api_types` remain in the shim (if retained)
- [x] OR the shim file is deleted (if no callers remain)
- [x] `pytest tests/specify_cli/dashboard/` passes

---

## Definition of Done

- [x] `src/dashboard/services/mission_scan.py` has no `dashboard.api_types` imports
- [x] `src/dashboard/services/project_state.py` has no `dashboard.api_types` imports
- [x] `src/dashboard/services/registry.py` has no `dashboard.api_types` imports
- [x] `src/dashboard/file_reader.py` has no `dashboard.api_types` imports
- [x] `src/specify_cli/dashboard/api_types.py` is either deleted or has no `dashboard.api_types` imports
- [x] `mypy --strict` passes on all five files
- [x] `pytest tests/specify_cli/dashboard/ tests/test_dashboard/` passes

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Type missed in migration map — mypy surfaces it | Medium | Run `mypy --strict` per file; the categorisation table in `research.md` is the reference |
| Shim still has callers after WP02/WP03 complete | Low | T026 step 4 uses grep to discover all callers before deciding to delete |
| Circular import if `missions/api_types.py` indirectly imports from `dashboard/services/` | Low | `missions/api_types.py` only imports from `status/api_types.py`; no dashboard dependencies |

## Reviewer Guidance

1. Run `grep -r "from dashboard.api_types" src/dashboard/services/ src/dashboard/file_reader.py --include="*.py"` — must produce no output.
2. If the shim was deleted, confirm `grep -r "specify_cli.dashboard.api_types" src/ tests/ --include="*.py"` produces no output.
3. Run `mypy --strict src/dashboard/services/ src/dashboard/file_reader.py` and confirm clean.
4. Run `pytest tests/test_dashboard/ tests/specify_cli/dashboard/ -v` and confirm green.

Implement command: `spec-kitty agent action implement WP05 --agent <name>`

## Activity Log

- 2026-05-04T17:57:35Z – copilot:claude-sonnet-4-6:alphonso:implementer – shell_pid=1976107 – Started implementation via action command
- 2026-05-04T18:01:24Z – copilot:claude-sonnet-4-6:alphonso:implementer – shell_pid=1976107 – All dashboard service imports migrated to canonical type locations
- 2026-05-04T18:01:46Z – copilot:claude-sonnet-4-6:alphonso:reviewer – shell_pid=1983935 – Started review via action command
- 2026-05-04T18:03:54Z – copilot:claude-sonnet-4-6:alphonso:reviewer – shell_pid=1983935 – Review passed: all service imports migrated to canonical locations, tests pass
