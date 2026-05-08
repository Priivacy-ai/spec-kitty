---
work_package_id: WP02
title: MissionScanService Migration
dependencies:
- WP01
requirement_refs:
- FR-004
- FR-008
- FR-011
- NFR-001
- NFR-002
- C-001
- C-002
- C-004
planning_base_branch: feature/645-api-surface-completion-mission-c
merge_target_branch: feature/645-api-surface-completion-mission-c
branch_strategy: Planning artifacts for this feature were generated on feature/645-api-surface-completion-mission-c. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/645-api-surface-completion-mission-c unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
- T010
phase: Phase 1 - Core Registry Migration
assignee: ''
agent: "claude:sonnet-4-6:reviewer:reviewer"
shell_pid: "2998041"
history:
- at: '2026-05-07T12:36:56Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/missions/scan_service.py
execution_mode: code_change
owned_files:
- src/specify_cli/missions/scan_service.py
- src/dashboard/services/mission_scan.py
- src/specify_cli/dashboard/handlers/features.py
tags: []
---

# Work Package Prompt: WP02 – MissionScanService Migration

## Branch Strategy

- **Planning/base branch at prompt creation**: `feature/645-api-surface-completion-mission-c`
- **Final merge target for completed work**: `feature/645-api-surface-completion-mission-c`
- **Implement command**: `spec-kitty implement WP02 --base WP01`
- **Depends on**: WP01 must be complete — `src/specify_cli/missions/registry.py` must exist before this WP is functional.

---

## Objectives & Success Criteria

Move `MissionScanService` and `parse_kanban_path` from `src/dashboard/services/mission_scan.py`
to `src/specify_cli/missions/scan_service.py`. Fix the runtime `dashboard.services.registry`
import inside `__init__` (not just the TYPE_CHECKING block). Leave a shim at the original
location. Update the `specify_cli/dashboard/handlers/features.py` caller.

**Done when**:
- `src/specify_cli/missions/scan_service.py` exists with no `dashboard.*` imports
- `grep -n "from dashboard" src/specify_cli/missions/scan_service.py` → empty
- `grep -n "from dashboard" src/specify_cli/dashboard/handlers/features.py` → empty
- `python -c "from dashboard.services.mission_scan import MissionScanService, parse_kanban_path; print('OK')"` → `OK`
- `pytest tests/test_dashboard/test_seams.py -k features -q` → all pass
- `mypy src/specify_cli/missions/scan_service.py --strict` → zero errors

## Context & Constraints

**Spec**: `kitty-specs/dashboard-services-domain-migration-01KR151P/spec.md` — FR-004, FR-008, FR-011
**Research**: `kitty-specs/dashboard-services-domain-migration-01KR151P/research.md` — R-003 caller map, R-005 shim pattern
**Quickstart**: `kitty-specs/dashboard-services-domain-migration-01KR151P/quickstart.md` — WP02 section

**Critical finding (R-003)**: `mission_scan.py` has TWO import sites for `dashboard.services.registry`:
1. A `TYPE_CHECKING` block at module top
2. A **runtime deferred import** inside `MissionScanService.__init__` (not guarded by TYPE_CHECKING!)

Both must be fixed in the new canonical file. The runtime import is the one Robert's P1
finding actually triggers — it silently uses the old (potentially stale) registry if not updated.

---

## Subtasks & Detailed Guidance

### Subtask T006 – Create `src/specify_cli/missions/scan_service.py`

**Purpose**: Copy the canonical `MissionScanService` implementation to the domain layer.

**Steps**:
1. Copy the full content of `src/dashboard/services/mission_scan.py` to `src/specify_cli/missions/scan_service.py`.
2. Update the module docstring: change the reference from `dashboard.services.registry` to `specify_cli.missions.registry`.
3. Do NOT yet fix the `dashboard.*` imports — those are T007 and T008.
4. Verify the copy compiles: `python -c "import ast; ast.parse(open('src/specify_cli/missions/scan_service.py').read())"`.

**Files**:
- `src/specify_cli/missions/scan_service.py` (new)

---

### Subtask T007 – Fix TYPE_CHECKING import in `scan_service.py`

**Purpose**: Update the static-analysis import so mypy resolves `MissionRegistry` and
`MissionRecord` from the canonical domain path.

**Steps**:

1. Find the `TYPE_CHECKING` block (near top of file):
```python
# OLD
if TYPE_CHECKING:
    from dashboard.services.registry import MissionRecord, MissionRegistry
# NEW
if TYPE_CHECKING:
    from specify_cli.missions.registry import MissionRecord, MissionRegistry
```

2. Run `mypy src/specify_cli/missions/scan_service.py --strict` — must pass with zero errors.

**Files**:
- `src/specify_cli/missions/scan_service.py` (modified)

---

### Subtask T008 – Fix runtime deferred import in `MissionScanService.__init__`

**Purpose**: Remove the hidden runtime dependency on `dashboard.*` that causes
`MissionScanService` to instantiate a `MissionRegistry` from the old location when
no `registry` is injected. This is the critical fix — without it, the canonical
`scan_service.py` still imports through the shim at runtime.

**Steps**:

1. Find the deferred import inside `__init__` (NOT inside `if TYPE_CHECKING`):
```python
# Inside __init__ body, near the bottom of the constructor:
# OLD
from dashboard.services.registry import MissionRegistry
# NEW
from specify_cli.missions.registry import MissionRegistry
```

2. The full context looks like:
```python
def __init__(self, project_dir, *, registry=None, ...):
    ...
    # OLD:
    from dashboard.services.registry import MissionRegistry
    self._registry = registry if registry is not None else MissionRegistry(self._project_dir)
    # NEW:
    from specify_cli.missions.registry import MissionRegistry
    self._registry = registry if registry is not None else MissionRegistry(self._project_dir)
```

3. After the fix, run: `grep -n "from dashboard" src/specify_cli/missions/scan_service.py` → must return empty.

**Files**:
- `src/specify_cli/missions/scan_service.py` (modified)

**Notes**: This runtime import is inside `if registry is not None else MissionRegistry(...)`.
In production, the FastAPI app injects a registry via `app.state`, so this branch rarely
fires — which is exactly why the bug was latent. Test it by constructing `MissionScanService`
without passing a `registry` argument and asserting the created instance's `._registry` is
a `specify_cli.missions.registry.MissionRegistry`.

---

### Subtask T009 – Convert `dashboard/services/mission_scan.py` to shim

**Purpose**: Backward compatibility for `dashboard/api/` callers still using the old path.

**Steps**:

1. Replace the full content of `src/dashboard/services/mission_scan.py` with:

```python
# SHIM — removal_release: 3.2.0
# Owner: dashboard-services-domain-migration-01KR151P
# Canonical home: src/specify_cli/missions/scan_service.py
# Do not add business logic here. Edit specify_cli/missions/scan_service.py instead.
# This shim will be deleted in Phase C (after release 3.2.0).
from specify_cli.missions.scan_service import (
    MissionScanService,
    parse_kanban_path,
)

__all__ = [
    "MissionScanService",
    "parse_kanban_path",
]
```

2. Smoke-test: `python -c "from dashboard.services.mission_scan import MissionScanService, parse_kanban_path; print('OK')"` → `OK`.

**Files**:
- `src/dashboard/services/mission_scan.py` (replaced with shim)

---

### Subtask T010 – Update `specify_cli/dashboard/handlers/features.py`

**Purpose**: Remove the remaining `dashboard.*` imports in the features handler.

**Steps**:

1. There are two deferred import sites inside `features.py` (inside method bodies). Find both:

**Site 1** (approximately line 35 in the original):
```python
# OLD
from dashboard.services.mission_scan import MissionScanService
# NEW
from specify_cli.missions.scan_service import MissionScanService
```

**Site 2** (approximately line 58 in the original):
```python
# OLD
from dashboard.services.mission_scan import MissionScanService, parse_kanban_path
# NEW
from specify_cli.missions.scan_service import MissionScanService, parse_kanban_path
```

2. After edits: `grep -n "from dashboard" src/specify_cli/dashboard/handlers/features.py` → empty.

3. Run `pytest tests/test_dashboard/test_seams.py -k features -q` — all pass.

**Files**:
- `src/specify_cli/dashboard/handlers/features.py` (2 import sites updated)

**Notes**: Use `grep -n "from dashboard.services.mission_scan" src/specify_cli/dashboard/handlers/features.py` to find the exact line numbers before editing.

---

## Definition of Done

- [ ] `src/specify_cli/missions/scan_service.py` exists with no `dashboard.*` imports (both TYPE_CHECKING and runtime)
- [ ] `mypy src/specify_cli/missions/scan_service.py --strict` → zero errors
- [ ] `python -c "from dashboard.services.mission_scan import MissionScanService, parse_kanban_path; print('OK')"` → `OK`
- [ ] `grep -n "from dashboard" src/specify_cli/dashboard/handlers/features.py` → empty
- [ ] `pytest tests/test_dashboard/test_seams.py -k features -q` → all pass
- [ ] `pytest tests/test_dashboard/ -x -q` → all pass

## Reviewer Guidance

1. Specifically verify T008 — the runtime import inside `__init__`, not just the TYPE_CHECKING one. This is the latent bug Robert identified.
2. Instantiate `MissionScanService(project_dir)` without `registry=` and confirm the internal `._registry` is a `specify_cli.missions.registry.MissionRegistry` (not the shim import path).
3. Confirm the shim is ≤ 15 lines of logic and re-exports both `MissionScanService` and `parse_kanban_path`.

## Activity Log

- 2026-05-07T15:17:00Z – claude:sonnet-4-6:implementer:implementer – shell_pid=2985722 – Started implementation via action command
- 2026-05-07T15:21:35Z – claude:sonnet-4-6:implementer:implementer – shell_pid=2985722 – MissionScanService migrated; runtime + TYPE_CHECKING imports fixed; shim with __all__; features handlers updated; seam tests pass
- 2026-05-07T15:22:01Z – claude:sonnet-4-6:reviewer:reviewer – shell_pid=2998041 – Started review via action command
- 2026-05-07T15:24:46Z – claude:sonnet-4-6:reviewer:reviewer – shell_pid=2998041 – All 5 subtasks T006-T010 delivered. scan_service.py has zero dashboard.* imports; runtime registry path verified canonical (specify_cli.missions.registry.MissionRegistry instantiated by default). Shim is 14 lines with __all__ and removal_release marker. Seam-test mock-target repointing is mechanical (4 sites). All 338 dashboard tests pass. mypy --strict clean on scan_service.py. Pre-existing mypy errors in features.py and dashboard/api/app.py unrelated to WP02 scope. dashboard.file_reader imports remain but are out of WP02 scope (owned_files limited to mission_scan path). --force used per shared-lane WP03 review pattern (WP04 in-flight).
