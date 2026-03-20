---
work_package_id: WP03
title: Dead Mission Code Deletion
lane: "doing"
dependencies: [WP02]
base_branch: 054-state-architecture-cleanup-phase-2-WP02
base_commit: e3bf132b1edb14ea76fbfe55a0511613da0ff64d
created_at: '2026-03-20T14:42:46.091792+00:00'
subtasks:
- T009
- T010
- T011
- T012
- T013
phase: Phase 1 - Core Cleanup
assignee: ''
agent: "coordinator"
shell_pid: "88054"
review_status: ''
reviewed_by: ''
review_feedback: ''
history:
- timestamp: '2026-03-20T13:39:48Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- FR-005
- FR-006
- FR-007
---

# Work Package Prompt: WP03 – Dead Mission Code Deletion

## Objectives & Success Criteria

- Delete `set_active_mission()` from `mission.py` (deprecated since v0.8.0, zero callers).
- Delete `get_active_mission_key()` from `project_resolver.py` (zero production callers).
- Remove `active_mission_marker` from the state contract.
- Add `.kittify/active-mission` to `.gitignore`.
- Grep confirms zero production references to deleted functions.

## Context & Constraints

- **Depends on WP02**: Active-mission reads must be removed first (WP02) before deleting the code they call.
- **Plan reference**: Design decision D2 — hard removal, deprecation period already passed (v0.8.0 → v2.0.9).
- **Migration concern**: `m_0_8_0_remove_active_mission.py` may import `set_active_mission()`.

## Implementation Command

```bash
spec-kitty implement WP03 --base WP02
```

## Subtasks & Detailed Guidance

### Subtask T009 – Delete `set_active_mission()` from mission.py

**Purpose**: Remove the deprecated writer that creates `.kittify/active-mission` symlinks/files.

**Steps**:

1. In `src/specify_cli/mission.py`:
   - Delete `set_active_mission()` (lines 523-566).
   - Remove any imports used only by this function.

2. Check if `m_0_8_0_remove_active_mission.py` imports or references `set_active_mission()`:
   ```bash
   grep -r "set_active_mission" src/specify_cli/upgrade/migrations/
   ```
   - If it does: the migration should have its own inline logic (it probably already does since it's a removal migration). Verify the migration still works without the function.
   - If it doesn't: proceed safely.

3. Check for any external references:
   ```bash
   grep -r "set_active_mission" src/ tests/
   ```
   - Remove any test that directly tests `set_active_mission()`.

**Files**:
- `src/specify_cli/mission.py` (MODIFY)

### Subtask T010 – Delete `get_active_mission_key()` from project_resolver.py

**Purpose**: Remove the unused resolver helper.

**Steps**:

1. In `src/specify_cli/core/project_resolver.py`:
   - Delete `get_active_mission_key()` (lines 107-134).
   - Remove `DEFAULT_MISSION_KEY` constant if only used by this function.

2. In `src/specify_cli/core/__init__.py`:
   - Remove `get_active_mission_key` from `__all__` and any explicit import/re-export.

3. Verify no production code imports it:
   ```bash
   grep -r "get_active_mission_key" src/specify_cli/ --include="*.py" | grep -v __pycache__
   ```

**Files**:
- `src/specify_cli/core/project_resolver.py` (MODIFY)
- `src/specify_cli/core/__init__.py` (MODIFY)

### Subtask T011 – Remove `active_mission_marker` from state contract

**Purpose**: The state contract should not enumerate a surface that no longer exists in production code.

**Steps**:

1. In `src/specify_cli/state_contract.py`:
   - Find the `active_mission_marker` `StateSurface` entry (around lines 522-534 in section G: Legacy).
   - Delete the entire entry.
   - If the section becomes empty, remove the section comment.

2. Update any tests that reference `active_mission_marker`:
   - `tests/specify_cli/test_state_contract.py` may have assertions about the count of surfaces or specific entry names.

**Files**:
- `src/specify_cli/state_contract.py` (MODIFY)
- `tests/specify_cli/test_state_contract.py` (MODIFY if needed)

### Subtask T012 – Add `.kittify/active-mission` to .gitignore

**Purpose**: Prevent accidental recommit of legacy active-mission markers.

**Steps**:

1. In `.gitignore` at the repo root:
   - Add `.kittify/active-mission` in the appropriate section (near other `.kittify/` ignores).

**Files**:
- `.gitignore` (MODIFY)

### Subtask T013 – Update/remove tests for deleted functions

**Purpose**: Remove tests that test deleted code; update tests that referenced it indirectly.

**Steps**:

1. In `tests/runtime/test_project_resolver.py`:
   - Find `test_get_active_mission_key_prefers_file` and any other tests for `get_active_mission_key()`.
   - Delete these tests.

2. Search for any other test references:
   ```bash
   grep -r "set_active_mission\|get_active_mission_key" tests/ --include="*.py"
   ```
   - Delete or update each reference.

3. Run the affected test files to confirm no import errors:
   ```bash
   pytest tests/runtime/test_project_resolver.py -v
   ```

**Files**:
- `tests/runtime/test_project_resolver.py` (MODIFY)
- Any other test files referencing deleted functions (MODIFY)

**Validation**:
- `pytest tests/runtime/ tests/specify_cli/test_state_contract.py -v`
- `grep -r "set_active_mission\|get_active_mission_key" src/specify_cli/ --include="*.py"` returns zero hits.

## Risks & Mitigations

- **Migration breakage**: `m_0_8_0_remove_active_mission.py` may reference the deleted function. Check before deleting and inline any needed logic.
- **External consumers**: If any external tool imports `set_active_mission` or `get_active_mission_key`, it will break. This is intentional — they've been deprecated since v0.8.0.

## Review Guidance

- Verify zero grep hits for deleted function names in production code.
- Verify the v0.8.0 migration still applies cleanly.
- Verify `.gitignore` entry is scoped correctly.

## Activity Log

- 2026-03-20T13:39:48Z – system – lane=planned – Prompt created.
- 2026-03-20T14:42:46Z – coordinator – shell_pid=88054 – lane=doing – Assigned agent via workflow command
