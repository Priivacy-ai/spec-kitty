---
work_package_id: WP08
title: Legacy Bridge Import Hardening
lane: "for_review"
dependencies: []
base_branch: 2.x
base_commit: 20e2a63bb590443ec2d0885d22d58f40efa6f9ce
created_at: '2026-03-20T13:52:04.586264+00:00'
subtasks:
- T033
- T034
- T035
- T036
phase: Phase 2 - Correctness
assignee: ''
agent: coordinator
shell_pid: '73924'
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
- FR-021
- FR-022
- NFR-002
---

# Work Package Prompt: WP08 – Legacy Bridge Import Hardening

## Objectives & Success Criteria

- `legacy_bridge` is a top-level import in `emit.py` — missing module fails at import time (not silently at runtime).
- The stale `# WP06 not yet available` comment is removed.
- The broad `Exception` catch for bridge UPDATE failures is preserved (canonical state is already safe).
- Tests verify that `ImportError` is NOT silently swallowed.

## Context & Constraints

- **Plan reference**: Design decision D5 in plan.md.
- **Current code** (emit.py:288-301): `try: from ... import update_all_views` with `except ImportError: pass`.
- **Why this matters**: `legacy_bridge.py` is in-tree, tested, and required on 2.x. A missing import now indicates a packaging regression, not a planned transitional state.
- **What stays**: The `except Exception` catch around `update_all_views()` call stays — bridge update failures are non-critical because canonical state (event log + snapshot) is already persisted at Step 5, before Step 7.

## Implementation Command

```bash
spec-kitty implement WP08
```

## Subtasks & Detailed Guidance

### Subtask T033 – Move legacy_bridge to top-level import

**Purpose**: Make the import a hard requirement that fails at module load time if missing.

**Steps**:

1. In `src/specify_cli/status/emit.py`, find the top-level imports section.

2. Add:
   ```python
   from specify_cli.status.legacy_bridge import update_all_views
   ```

3. This import should be alongside other `specify_cli.status` imports.

**Files**: `src/specify_cli/status/emit.py` (MODIFY)

### Subtask T034 – Remove ImportError catch and WP06 comment

**Purpose**: Clean up the transitional code that is no longer transitional.

**Steps**:

1. In `src/specify_cli/status/emit.py`, find the Step 7 block (around lines 288-301):
   ```python
   # Step 7: Update legacy bridge views (WP06 may not be merged yet)
   if snapshot is not None:
       try:
           from specify_cli.status.legacy_bridge import update_all_views

           update_all_views(feature_dir, snapshot)
       except ImportError:
           pass  # WP06 not yet available
       except Exception:
           logger.warning(
               "Legacy bridge update failed for event %s; "
               "canonical log and snapshot are unaffected",
               event.event_id,
           )
   ```

2. Replace with:
   ```python
   # Step 7: Update legacy compatibility views
   if snapshot is not None:
       try:
           update_all_views(feature_dir, snapshot)
       except Exception:
           logger.warning(
               "Legacy bridge update failed for event %s; "
               "canonical log and snapshot are unaffected",
               event.event_id,
           )
   ```

3. Changes:
   - Remove inline `from ... import` (now at top level)
   - Remove `except ImportError: pass`
   - Remove `# WP06 not yet available` and `# WP06 may not be merged yet` comments
   - Update the step comment to remove transitional language
   - Keep the `except Exception` catch with the warning log

**Files**: `src/specify_cli/status/emit.py` (MODIFY)

### Subtask T035 – Add test for ImportError propagation

**Purpose**: Verify that a missing `legacy_bridge` module causes a hard failure, not silent degradation.

**Steps**:

1. In `tests/status/test_emit.py`, add a new test:
   ```python
   def test_legacy_bridge_import_error_is_not_swallowed(monkeypatch):
       """On 2.x, missing legacy_bridge is a packaging regression — must fail."""
       # Patch sys.modules to simulate missing legacy_bridge
       import sys
       monkeypatch.setitem(sys.modules, "specify_cli.status.legacy_bridge", None)

       with pytest.raises(ImportError):
           # Re-import emit to trigger the top-level import failure
           import importlib
           importlib.reload(specify_cli.status.emit)
   ```

   Note: The exact test approach depends on how the import is structured. If using top-level import, the reload will fail. Alternatively, test at the module level.

2. A simpler approach: verify the import is at the top level by inspecting the module:
   ```python
   def test_legacy_bridge_is_top_level_import():
       """Verify legacy_bridge is imported at module level, not inside try/except."""
       import ast
       import inspect

       source = inspect.getsource(specify_cli.status.emit)
       tree = ast.parse(source)

       # Check top-level imports include legacy_bridge
       top_level_imports = [
           node for node in ast.walk(tree)
           if isinstance(node, (ast.Import, ast.ImportFrom))
           and getattr(node, 'module', '') and 'legacy_bridge' in getattr(node, 'module', '')
       ]
       assert len(top_level_imports) >= 1, "legacy_bridge must be a top-level import"
   ```

**Files**: `tests/status/test_emit.py` (MODIFY)

### Subtask T036 – Update existing test for new behavior

**Purpose**: The existing `test_legacy_bridge_import_error_handled` test asserts silent handling — it must be updated.

**Steps**:

1. In `tests/status/test_emit.py`, find `test_legacy_bridge_import_error_handled` (lines 825-835).

2. This test currently:
   - Verifies that ImportError doesn't block emit
   - Asserts event is still persisted

3. Update or replace this test:
   - **Option A**: Delete the test entirely (the behavior it tests no longer exists).
   - **Option B**: Rename to `test_legacy_bridge_update_exception_does_not_block_emit` and change it to test the `Exception` catch (bridge update failure, not import failure). This test already exists as `test_legacy_bridge_exception_handled` (lines 837-867) — so just delete the import error test.

4. Also verify `test_legacy_bridge_exception_handled` (lines 837-867) still passes — this one tests that bridge UPDATE failures are caught, which is the behavior we're keeping.

**Files**: `tests/status/test_emit.py` (MODIFY)

**Validation**:
```bash
pytest tests/status/test_emit.py -v
```

## Risks & Mitigations

- **CI impact**: If any CI environment accidentally excludes `legacy_bridge.py` from the package, the hard import will fail. This is the DESIRED behavior — it surfaces the regression.
- **Test stability**: The `importlib.reload` approach for testing import failure can be fragile. The AST inspection approach is more stable.

## Review Guidance

- Verify the `from ... import update_all_views` is at module top level.
- Verify NO `except ImportError` remains anywhere in the function.
- Verify the `except Exception` catch for bridge UPDATE failures is preserved.
- Verify the old `test_legacy_bridge_import_error_handled` test is removed or updated.

## Activity Log

- 2026-03-20T13:39:48Z – system – lane=planned – Prompt created.
- 2026-03-20T13:52:04Z – coordinator – shell_pid=73924 – lane=doing – Assigned agent via workflow command
- 2026-03-20T13:56:10Z – coordinator – shell_pid=73924 – lane=for_review – Ready for review: legacy_bridge import hardened to top-level, ImportError swallow removed, AST-based test added, all 45 tests pass
