---
work_package_id: "WP05"
subtasks:
  - "T022"
  - "T023"
  - "T024"
  - "T025"
  - "T026"
title: "Fix Duplicate Emissions"
phase: "Phase 3 - Bug Fixes"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: ["WP04"]
history:
  - timestamp: "2026-02-07T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP05 – Fix Duplicate Emissions

## Implementation Command

```bash
spec-kitty implement WP05 --base WP04
```

---

## Objectives & Success Criteria

**Goal**: Remove duplicate WPStatusChanged events from `implement.py` and `accept.py`.

**Scope Note**: Post-MVP (nice-to-have cleanup once identity + auto-sync are stable).

**Success Criteria**:
- [ ] `spec-kitty implement WP01` emits exactly ONE WPStatusChanged event
- [ ] `spec-kitty accept` emits exactly ONE WPStatusChanged event per WP
- [ ] Error paths still emit appropriate ErrorLogged events
- [ ] All tests pass

---

## Context & Constraints

**Target Branch**: 2.x

**IMPORTANT**: This work package requires the **2.x branch** where event emissions are already wired in. The main branch does NOT have these emissions.

**Supporting Documents**:
- [spec.md](../spec.md) - User Story 5 (Fix Duplicate Emissions)

**Prerequisites**: WP04 (runtime) should be complete for proper testing.

**Key Constraints**:
- Keep exactly one emission per status transition
- Do not break error logging/reporting
- Test by counting emitter calls

---

## Subtasks & Detailed Guidance

### Subtask T022 – Audit implement.py emissions on 2.x

**Purpose**: Identify all WPStatusChanged emission points in implement.py.

**Steps**:
1. Switch to 2.x branch: `git checkout 2.x`
2. Open `src/specify_cli/cli/commands/implement.py`
3. Search for `emit_wp_status_changed` calls
4. Document all emission points:
   ```
   Example findings:
   - Line 245: emit_wp_status_changed(wp_id, "planned", "doing") after worktree creation
   - Line 312: emit_wp_status_changed(wp_id, "planned", "doing") in success path
   - Line 350: emit_wp_status_changed(wp_id, "planned", "doing") in finally block
   ```
5. Identify which is the "correct" single point (typically: success path, after all work done)

**Files**:
- `src/specify_cli/cli/commands/implement.py` (audit, no changes yet)

**Notes**:
- Record line numbers and contexts for each emission
- Note which are in error paths vs success paths
- Some may be guarded by conditions that make them mutually exclusive

---

### Subtask T023 – Consolidate to single emission in implement.py

**Purpose**: Keep only one WPStatusChanged emission in implement.py.

**Steps**:
1. Based on T022 audit, decide the correct emission point:
   - Should be at END of successful implementation flow
   - After worktree is created and lane is updated
   - NOT in error paths or finally blocks

2. Remove or guard duplicate emissions:
   ```python
   # BEFORE (duplicate)
   if some_condition:
       emit_wp_status_changed(wp_id, "planned", "doing")
   # ... later ...
   emit_wp_status_changed(wp_id, "planned", "doing")  # Also emitted!
   
   # AFTER (single)
   # Remove the first emission, keep only the final one
   # ... do all work ...
   emit_wp_status_changed(wp_id, "planned", "doing")  # Single emission
   ```

3. If error paths need events, use `emit_error_logged()` instead

**Files**:
- `src/specify_cli/cli/commands/implement.py` (modify, remove duplicates)

**Notes**:
- Keep the emission in the final successful path (after lane update + commit)
- Check if earlier emissions were for error cases - those might be ErrorLogged

---

### Subtask T024 – Audit accept.py emissions on 2.x

**Purpose**: Identify all WPStatusChanged emission points in accept.py.

**Steps**:
1. Open `src/specify_cli/cli/commands/accept.py`
2. Search for `emit_wp_status_changed` calls
3. Document all emission points (similar to T022)
4. Note: accept.py may emit for multiple WPs (one per WP being accepted)
5. Verify: should be exactly ONE emission per WP

**Files**:
- `src/specify_cli/cli/commands/accept.py` (audit, no changes yet)

---

### Subtask T025 – Consolidate to single emission in accept.py

**Purpose**: Keep only one WPStatusChanged emission per WP in accept.py.

**Steps**:
1. Based on T024 audit, identify duplicates
2. For each WP in the acceptance flow:
   - Emit `WPStatusChanged(for_review -> done)` exactly once
   - At the point where the WP is actually marked as done

3. Remove or guard duplicates:
   ```python
   # Correct pattern: emit once per WP at the right point
   for wp in work_packages:
       # ... do acceptance work ...
       emit_wp_status_changed(wp.id, "for_review", "done")  # Once per WP
   ```

**Files**:
- `src/specify_cli/cli/commands/accept.py` (modify, remove duplicates)

---

### Subtask T026 – Add test verifying single emission per command

**Purpose**: Regression test to prevent future duplicates.

**Steps**:
1. Add test to `tests/sync/test_event_emission.py`:
   ```python
   from unittest.mock import patch, MagicMock
   
   class TestNoDuplicateEmissions:
       def test_implement_emits_once(self, temp_project):
           """implement command emits exactly one WPStatusChanged."""
           mock_emitter = MagicMock()
           
           with patch("specify_cli.sync.events.emit_wp_status_changed", return_value=None) as mock_emit:
               # Run implement command (may need CLI runner)
               # ...
               pass
           
           # Count emit_wp_status_changed calls
           assert mock_emit.call_count == 1, f"Expected 1, got {mock_emit.call_count}"
       
       def test_accept_emits_once_per_wp(self, temp_project_with_wps):
           """accept command emits exactly one WPStatusChanged per WP."""
           # Similar pattern
           pass
   ```

**Files**:
- `tests/sync/test_event_emission.py` (add, ~50 lines)

**Test Commands**:
```bash
pytest tests/sync/test_event_emission.py::TestNoDuplicateEmissions -v
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Removing wrong emission | Carefully audit; keep emission at success point |
| Breaking error reporting | Keep ErrorLogged emissions for error paths |
| Regression | Add regression test in T026 |

---

## Review Guidance

**Reviewers should verify**:
1. Only ONE `emit_wp_status_changed` call per success path
2. Error paths use `emit_error_logged` if needed
3. Regression test counts emissions correctly

---

## Activity Log

- 2026-02-07T00:00:00Z – system – lane=planned – Prompt created.
