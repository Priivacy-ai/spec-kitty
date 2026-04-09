---
affected_files: []
cycle_number: 2
mission_slug: 080-wpstate-lane-consumer-strangler-fig-phase-2
reproduction_command:
reviewed_at: '2026-04-09T14:37:33Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP03
---

## WP03 Review - Cycle 1: Request Changes

### CRITICAL ISSUE: Dead Code - Function Not Called from Live Paths

**Status**: BLOCKED - Implementation incomplete

**Problem**: The helper function `_get_progress_display()` has been correctly implemented with `WPState.progress_bucket()` integration, but it is **never called** from any actual code paths. This violates the acceptance criterion:

> "Verify new code is verified to be called from live entry points (not dead code)"

**Evidence**:
- Function defined at line 28-52 in `src/specify_cli/agent_utils/status.py`
- Zero calls to `_get_progress_display()` in the file
- Function only exists to satisfy the unit tests
- Actual kanban display logic remains unchanged

**Search Results**:
```bash
$ grep "_get_progress_display" src/specify_cli/agent_utils/status.py
28:def _get_progress_display(lane: str) -> str:
31:    Uses WPState.progress_bucket() to delegate bucketing logic.
# No calls to the function found
```

### How to Fix

1. **Integrate into display logic**: The function must be called from the actual display code that generates the kanban board output.

2. **Suggested integration point**: Either:
   - Call from `show_kanban_status()` when building the lane buckets (lines 113-116)
   - Or call from `_analyze_parallelization()` where it checks lane membership (line 217)
   - Or both locations if bucketing is needed in multiple places

3. **Example usage** (pick one):
   ```python
   # In show_kanban_status(), replace hardcoded lane grouping:
   for wp in work_packages:
       lane = wp["lane"]
       progress_bucket = _get_progress_display(lane)  # ← USE IT HERE
       # Then group by bucket instead of by lane
   ```

4. **Update tests**: Add an integration test that verifies `show_kanban_status()` calls `_get_progress_display()` and produces correct output.

### What Passed

✅ Function implementation is correct
- Correctly imports `wp_state_for` from `specify_cli.status.wp_state`
- Correctly calls `state.progress_bucket()`
- Bucket-to-display-string mapping is accurate
- All 4 unit tests pass

### What Failed

❌ **Live code integration** (CRITICAL)
- Function not called from any code path
- Display logic unchanged from original
- Test coverage doesn't include integration verification
- Acceptance criterion "verified to be called from live entry points" not met

### Acceptance Criteria Status

| Criterion | Status | Notes |
|-----------|--------|-------|
| Manual bucketing if-elif chain removed | ⚠️  PARTIAL | Chain was never there in current code base |
| `state.progress_bucket()` used instead | ❌ NO | Function defined but not called |
| Regression test covers all 9 lanes | ✅ YES | Test passing |
| No hardcoded Lane tuples remain | ⚠️  PARTIAL | Some still exist in `_analyze_parallelization()` |
| All existing tests pass | ✅ YES | Both new and existing tests pass |
| mypy --strict passes | ⚠️  UNTESTED | Not verified in review |
| **Called from live entry points** | ❌ NO | **BLOCKING ISSUE** |

### Next Steps

1. Integrate `_get_progress_display()` into actual display code
2. Verify with `grep` that the function is now called
3. Add integration test that includes the display logic
4. Re-run full test suite to ensure no regressions
5. Resubmit for review

---

**Reviewed by**: claude:haiku:reviewer:reviewer
**Review Date**: 2026-04-09
**Status**: Requesting Changes
