---
work_package_id: WP03
title: ProjectStateService and SyncService Migration
dependencies: []
requirement_refs:
- FR-005
- FR-006
- FR-008
- FR-012
- NFR-001
- NFR-002
- C-001
- C-002
- C-004
- C-007
planning_base_branch: feature/645-api-surface-completion-mission-c
merge_target_branch: feature/645-api-surface-completion-mission-c
branch_strategy: Planning artifacts for this feature were generated on feature/645-api-surface-completion-mission-c. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/645-api-surface-completion-mission-c unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
- T015
phase: Phase 1 - Core Registry Migration
assignee: ''
agent: "claude:sonnet-4-6:reviewer:reviewer"
shell_pid: "2985722"
history:
- at: '2026-05-07T12:36:56Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/missions/sync_service.py
execution_mode: code_change
owned_files:
- src/specify_cli/missions/project_state.py
- src/specify_cli/missions/sync_service.py
- src/dashboard/services/project_state.py
- src/dashboard/services/sync.py
- src/specify_cli/dashboard/handlers/api.py
tags: []
---

# Work Package Prompt: WP03 – ProjectStateService and SyncService Migration

## Branch Strategy

- **Planning/base branch at prompt creation**: `feature/645-api-surface-completion-mission-c`
- **Final merge target for completed work**: `feature/645-api-surface-completion-mission-c`
- **Implement command**: `spec-kitty implement WP03`
- **No dependencies** — runs in parallel with WP02 (different services, no shared imports).

---

## Objectives & Success Criteria

Move `ProjectStateService` to `src/specify_cli/missions/project_state.py` and `SyncService` +
`SyncTriggerResult` + `_build_trigger_request` to `src/specify_cli/missions/sync_service.py`.
Replace both source files with compatibility shims. Update
`src/specify_cli/dashboard/handlers/api.py` so it no longer imports from `dashboard.*`.

**Done when**:
- `src/specify_cli/missions/project_state.py` and `sync_service.py` exist with no `dashboard.*` imports
- Shims pass smoke-tests
- `grep -n "from dashboard" src/specify_cli/dashboard/handlers/api.py` → empty
- `pytest tests/test_dashboard/test_seams.py -k "health or sync" -q` → all pass
- `mypy src/specify_cli/missions/project_state.py src/specify_cli/missions/sync_service.py --strict` → zero errors

## Context & Constraints

**Spec**: `kitty-specs/dashboard-services-domain-migration-01KR151P/spec.md` — FR-005, FR-006, FR-008, FR-012, C-007
**Research**: `kitty-specs/dashboard-services-domain-migration-01KR151P/research.md` — R-003 caller map (api.py section)
**Quickstart**: `kitty-specs/dashboard-services-domain-migration-01KR151P/quickstart.md` — WP03 section

**Constraint C-007**: `specify_cli/dashboard/handlers/api.py` currently re-exports
`_build_trigger_request` as `_build_sync_trigger_request` at module level for seam-test
compatibility. This re-export alias must be preserved after the import path update:
```python
from specify_cli.missions.sync_service import _build_trigger_request as _build_sync_trigger_request
```
The name `_build_sync_trigger_request` is the seam-test mock target — do NOT rename it.

**Important**: Both `project_state.py` and `sync.py` have no internal `dashboard.*`
imports. The copy to the new canonical location is straightforward; only the caller
(`handlers/api.py`) has the violations to fix.

---

## Subtasks & Detailed Guidance

### Subtask T011 – Create `src/specify_cli/missions/project_state.py`

**Purpose**: Establish `ProjectStateService` at the domain layer.

**Steps**:
1. Confirm there are no `dashboard.*` imports in `src/dashboard/services/project_state.py`:
   `grep -n "from dashboard\|import dashboard" src/dashboard/services/project_state.py` → should return empty.
2. Copy the full content to `src/specify_cli/missions/project_state.py`.
3. Update the module docstring to reference the new canonical location.
4. Verify: `mypy src/specify_cli/missions/project_state.py --strict` → zero errors.
5. Verify no dashboard imports leaked in: `grep -n "from dashboard" src/specify_cli/missions/project_state.py` → empty.

**Files**:
- `src/specify_cli/missions/project_state.py` (new)

---

### Subtask T012 – Create `src/specify_cli/missions/sync_service.py`

**Purpose**: Establish `SyncService`, `SyncTriggerResult`, and `_build_trigger_request`
at the domain layer.

**Steps**:
1. Confirm there are no `dashboard.*` imports in `src/dashboard/services/sync.py`:
   `grep -n "from dashboard\|import dashboard" src/dashboard/services/sync.py` → should return empty.
2. Copy the full content to `src/specify_cli/missions/sync_service.py`.
3. Update the module docstring to reference the new canonical location.
4. Verify: `mypy src/specify_cli/missions/sync_service.py --strict` → zero errors.
5. Verify no dashboard imports: `grep -n "from dashboard" src/specify_cli/missions/sync_service.py` → empty.

**Files**:
- `src/specify_cli/missions/sync_service.py` (new)

---

### Subtask T013 – Convert `dashboard/services/project_state.py` to shim

**Steps**:

1. Replace the full content with:
```python
# SHIM — removal_release: 3.2.0
# Owner: dashboard-services-domain-migration-01KR151P
# Canonical home: src/specify_cli/missions/project_state.py
# Do not add business logic here. Edit specify_cli/missions/project_state.py instead.
# This shim will be deleted in Phase C (after release 3.2.0).
from specify_cli.missions.project_state import ProjectStateService

__all__ = ["ProjectStateService"]
```

2. Smoke-test: `python -c "from dashboard.services.project_state import ProjectStateService; print('OK')"` → `OK`.

**Files**:
- `src/dashboard/services/project_state.py` (replaced with shim)

---

### Subtask T014 – Convert `dashboard/services/sync.py` to shim

**Purpose**: Backward compatibility for `dashboard/api/routers/sync.py` and the seam test
that mocks `_build_trigger_request` via the `handlers/api.py` re-export.

**Steps**:

1. Replace the full content with:
```python
# SHIM — removal_release: 3.2.0
# Owner: dashboard-services-domain-migration-01KR151P
# Canonical home: src/specify_cli/missions/sync_service.py
# Do not add business logic here. Edit specify_cli/missions/sync_service.py instead.
# This shim will be deleted in Phase C (after release 3.2.0).
from specify_cli.missions.sync_service import (
    SyncService,
    SyncTriggerResult,
    _build_trigger_request,
)

__all__ = [
    "SyncService",
    "SyncTriggerResult",
    "_build_trigger_request",
]
```

2. Note: `_build_trigger_request` must be in `__all__` because `handlers/api.py` re-exports
   it. Even though the shim path is used only transiently, an incomplete `__all__` would
   break any code doing `from dashboard.services.sync import *`.

3. Smoke-test: `python -c "from dashboard.services.sync import SyncService, SyncTriggerResult, _build_trigger_request; print('OK')"` → `OK`.

**Files**:
- `src/dashboard/services/sync.py` (replaced with shim)

---

### Subtask T015 – Update `specify_cli/dashboard/handlers/api.py`

**Purpose**: Remove all `dashboard.*` imports from the API handler, preserving the
`_build_sync_trigger_request` module-level re-export alias for seam-test compatibility.

**Steps**:

1. Find and update the **top-level import** (not deferred):
```python
# OLD (top-level, around line 18)
from dashboard.services.sync import _build_trigger_request as _build_sync_trigger_request
# NEW
from specify_cli.missions.sync_service import _build_trigger_request as _build_sync_trigger_request
```

2. Find and update the **first deferred import** (inside a method body, around line 39):
```python
# OLD
from dashboard.services.project_state import ProjectStateService
# NEW
from specify_cli.missions.project_state import ProjectStateService
```

3. Find and update the **second deferred import** (inside a method body, around line 59):
```python
# OLD
from dashboard.services.sync import SyncService
# NEW
from specify_cli.missions.sync_service import SyncService
```

4. Verify: `grep -n "from dashboard" src/specify_cli/dashboard/handlers/api.py` → empty.

5. Verify the alias is preserved: `grep -n "_build_sync_trigger_request" src/specify_cli/dashboard/handlers/api.py` → should still appear on the top-level import line.

6. Run: `pytest tests/test_dashboard/test_seams.py -k "health or sync" -q` → all pass.

**Files**:
- `src/specify_cli/dashboard/handlers/api.py` (3 import sites updated)

**Notes**: Use `grep -n "from dashboard.services" src/specify_cli/dashboard/handlers/api.py`
to find exact line numbers before editing.

---

## Definition of Done

- [ ] `src/specify_cli/missions/project_state.py` and `sync_service.py` exist with no `dashboard.*` imports
- [ ] `mypy src/specify_cli/missions/project_state.py src/specify_cli/missions/sync_service.py --strict` → zero errors
- [ ] Both shims smoke-test successfully
- [ ] `_build_trigger_request` is in the sync shim's `__all__`
- [ ] `grep -n "from dashboard" src/specify_cli/dashboard/handlers/api.py` → empty
- [ ] `grep -n "_build_sync_trigger_request" src/specify_cli/dashboard/handlers/api.py` → alias import still present
- [ ] `pytest tests/test_dashboard/test_seams.py -k "health or sync" -q` → all pass
- [ ] `pytest tests/test_dashboard/ -x -q` → all pass

## Reviewer Guidance

1. Confirm `_build_sync_trigger_request` module-level alias is preserved in `handlers/api.py` — this is what seam tests mock.
2. Check `sync.py` shim `__all__` includes `_build_trigger_request` (private helper, but re-exported by convention).
3. Verify neither `project_state.py` nor `sync.py` source files ever had `dashboard.*` imports (grep confirms) so the copy was clean.

## Activity Log

- 2026-05-07T15:05:54Z – claude:sonnet-4-6:implementer:implementer – shell_pid=2967967 – Started implementation via action command
- 2026-05-07T15:16:18Z – claude:sonnet-4-6:implementer:implementer – shell_pid=2967967 – ProjectStateService + SyncService migrated; shims with __all__; handlers/api.py updated; seam tests pass
- 2026-05-07T15:16:56Z – claude:sonnet-4-6:reviewer:reviewer – shell_pid=2985722 – Started review via action command
- 2026-05-07T15:19:57Z – claude:sonnet-4-6:reviewer:reviewer – shell_pid=2985722 – WP03 approved. ProjectStateService and SyncService moved to specify_cli/missions; thin shims (8 + 16 lines); _build_trigger_request in sync shim __all__; handlers/api.py uses canonical paths in top-level alias and both deferred imports; _build_sync_trigger_request alias preserved per C-007; seam-test changes are mechanical mock-target repointing only (no behavioral changes); 13/13 health+sync seam tests pass; 338/338 dashboard tests pass; mypy --strict clean. --force used because lane-a worktree contains untracked scan_service.py from concurrent WP02 work (unrelated to WP03 commit 14f557729).
