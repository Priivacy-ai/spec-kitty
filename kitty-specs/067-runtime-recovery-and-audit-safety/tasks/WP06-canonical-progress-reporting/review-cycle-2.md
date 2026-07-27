---
affected_files: []
cycle_number: 2
mission_slug: 067-runtime-recovery-and-audit-safety
reproduction_command:
reviewed_at: '2026-04-06T19:05:48Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP06
---

# WP06 Review Cycle 1

## Verdict: Changes Requested

### Issue 1 (Bug): `_st_snapshot` NameError in `cli/commands/agent/tasks.py`

**Severity**: High -- runtime crash for features without event logs

**Location**: `src/specify_cli/cli/commands/agent/tasks.py`, lines 2583 and 2635

**Problem**: The variable `_st_snapshot` is only assigned inside a `try` block at line 2518. If the `try` block raises an exception (e.g., no event log file, corrupted JSONL), the `except` block at line 2523 only sets `_st_lanes = {}` but does NOT set `_st_snapshot`. The new code at lines 2583 and 2635 references `_st_snapshot` unconditionally:

```python
# Line 2583:
"progress_percentage": round(compute_weighted_progress(_st_snapshot).percentage, 1) if _st_snapshot else 0,
# Line 2635:
progress_pct = round(compute_weighted_progress(_st_snapshot).percentage, 1) if _st_snapshot else 0
```

When `_st_snapshot` is undefined, these lines raise a `NameError`, crashing the entire `tasks status` command. This is a regression -- the original code used `done_count / total * 100` which had no dependency on `_st_snapshot`.

**Fix**: Initialize `_st_snapshot = None` before the try block, or add `_st_snapshot = None` to the except block at line 2523-2524:

```python
# Option A: Initialize before try block (preferred)
_st_snapshot = None
try:
    from specify_cli.status.store import read_events as _st_read_events
    ...

# Option B: Add to except block
except Exception:
    _st_lanes = {}
    _st_snapshot = None
```

### What passes review

- All 7 callsites identified in the WP are addressed
- `merge/state.py:102` is correctly left unchanged
- `agent_utils/status.py` callsite (1) is clean -- `snapshot` is always in scope
- `dashboard/scanner.py` callsite (6) correctly adds `weighted_percentage` to `kanban_stats`
- `dashboard/handlers/features.py` correctly passes `weighted_percentage` through the kanban API
- `dashboard.js` callsites (4, 5) correctly read pre-computed `weighted_percentage` with done/total fallback
- `next/decision.py` callsite (7) adds `weighted_percentage` to the progress dict with safe fallback
- `next_cmd.py` reads `weighted_percentage` with `p.get("weighted_percentage", 0)` default
- Backward-compat fields (`done_count`, `by_lane`) are preserved in all outputs
- 11 new integration tests all pass (34 total in `tests/specify_cli/status/`)
- New test file `tests/specify_cli/status/test_progress_integration.py` covers the shared weighted-progress calculation across surfaces
- Progress is correctly non-zero for in-flight WPs (30% for in_progress, 60% for for_review, etc.)
