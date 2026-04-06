---
work_package_id: WP06
title: Canonical Progress Reporting
dependencies: []
requirement_refs:
- C-005
- FR-013
- FR-014
- FR-015
- NFR-003
planning_base_branch: main
merge_target_branch: main
branch_strategy: 'Current branch at workflow start: main. Planning/base branch for this feature: main. Completed changes must merge into main.'
subtasks: [T027, T028, T029, T030, T031, T032]
history:
- timestamp: '2026-04-06T18:43:32+00:00'
  event: created
  actor: claude
authoritative_surface: src/specify_cli/dashboard/
execution_mode: code_change
owned_files:
- src/specify_cli/agent_utils/status.py
- src/specify_cli/cli/commands/agent/tasks.py
- src/specify_cli/cli/commands/next_cmd.py
- src/specify_cli/dashboard/scanner.py
- src/specify_cli/dashboard/static/dashboard/dashboard.js
- src/specify_cli/next/decision.py
- tests/specify_cli/status/test_progress*
- tests/specify_cli/dashboard/**
- tests/specify_cli/agent_utils/test_status*
---

# WP06: Canonical Progress Reporting

## Objective

Replace all broken `done / total` progress formulas with the existing `compute_weighted_progress()` function. Every operator-facing surface (CLI, dashboard, next command) must show the same weighted progress that reflects in-flight work — not just completed WPs.

**Issues**: [#447](https://github.com/Priivacy-ai/spec-kitty/issues/447), [#443](https://github.com/Priivacy-ai/spec-kitty/issues/443) (consolidated into #447)

## Context

The correct progress module **already exists and is tested** at `src/specify_cli/status/progress.py:81-162`:
- `compute_weighted_progress(snapshot)` takes a `StatusSnapshot` and returns a `ProgressResult`
- Lane weights: `planned=0.0, claimed=0.05, in_progress=0.3, for_review=0.6, approved=0.8, done=1.0`
- Tests at `tests/specify_cli/status/test_progress.py` confirm correct behavior

The problem is that **nobody calls it**. There are 7 broken callsites using naive `done / total * 100`:

| # | File | Line | Current Formula |
|---|------|------|----------------|
| 1 | `src/specify_cli/agent_utils/status.py` | 138 | `done_count / total * 100` |
| 2 | `src/specify_cli/cli/commands/agent/tasks.py` | 2582 | `lane_counts["done"] / len(wps) * 100` |
| 3 | `src/specify_cli/cli/commands/agent/tasks.py` | 2634 | `done_count / total * 100` |
| 4 | `src/specify_cli/dashboard/static/dashboard/dashboard.js` | 319 | `completed / total * 100` (JS) |
| 5 | `src/specify_cli/dashboard/static/dashboard/dashboard.js` | 401 | `completed / total * 100` (JS) |
| 6 | `src/specify_cli/dashboard/scanner.py` | 351-390 | Emits raw lane counts only |
| 7 | `src/specify_cli/cli/commands/next_cmd.py` | 199 | `done / total * 100` |

Callsite 8 (`merge/state.py:102` — `completed_wps / wp_order * 100`) is intentionally kept as-is: merge tracks "how many WPs are merged" not weighted lane progress.

### Key files

| File | Line(s) | What |
|------|---------|------|
| `src/specify_cli/status/progress.py` | 81-162 | `compute_weighted_progress()` — CORRECT module |
| `src/specify_cli/status/progress.py` | 19-40 | `DEFAULT_LANE_WEIGHTS`, `ProgressResult` dataclass |
| `src/specify_cli/status/reducer.py` | all | `materialize()` — produces StatusSnapshot from events |
| `src/specify_cli/agent_utils/status.py` | 132-138 | Broken callsite 1 |
| `src/specify_cli/cli/commands/agent/tasks.py` | 2574-2587 | Broken callsite 2 (JSON output) |
| `src/specify_cli/cli/commands/agent/tasks.py` | ~2634 | Broken callsite 3 (display output) |
| `src/specify_cli/dashboard/scanner.py` | 351-390 | Broken callsite 6 (raw counts) |
| `src/specify_cli/dashboard/static/dashboard/dashboard.js` | 319, 401 | Broken callsites 4-5 (JS) |
| `src/specify_cli/cli/commands/next_cmd.py` | 194-200 | Broken callsite 7 |
| `src/specify_cli/next/decision.py` | 225-262 | `_compute_wp_progress()` — raw counts helper |

## Branch Strategy

- Planning base branch: `main`
- Final merge target: `main`
- Execution worktrees are allocated per computed lane from `lanes.json`

## Subtasks

### T027: Fix `agent_utils/status.py` Progress Formula

**Purpose**: Replace the broken `done_count / total * 100` at line 138 with `compute_weighted_progress()`.

**Steps**:

1. In `src/specify_cli/agent_utils/status.py`:
   - Add imports: `from specify_cli.status.progress import compute_weighted_progress`
   - Add import: `from specify_cli.status.reducer import materialize`
   - At line 138, the function has access to the feature_dir (check context around line 120-135)
   - Materialize the snapshot: `snapshot = materialize(feature_dir)`
   - Compute progress: `progress = compute_weighted_progress(snapshot)`
   - Replace: `progress_pct = round((done_count / total * 100), 1)` → `progress_pct = round(progress.percentage, 1)`

2. Update the returned dict (around line 155):
   - `"progress_percentage"` now uses the weighted value
   - Keep `"done_count"` field for backward compatibility (still available from the snapshot)

**Validation**:
- [ ] Progress shows ~30% when all WPs are `in_progress` (not 0%)
- [ ] Progress shows ~60% when all WPs are `for_review`
- [ ] Progress shows 100% only when all WPs are `done`

### T028: Fix `cli/commands/agent/tasks.py` Progress Formulas

**Purpose**: Replace the two broken formulas at lines 2582 and 2634.

**Steps**:

1. **Line 2582** (JSON output path):
   - This is inside a function that builds JSON output for `spec-kitty agent tasks status --json`
   - Add imports for `compute_weighted_progress` and `materialize`
   - The function has access to `feature_dir` (trace upward from line 2574)
   - Replace: `round(lane_counts.get("done", 0) / len(work_packages) * 100, 1)` → `round(compute_weighted_progress(materialize(feature_dir)).percentage, 1)`

2. **Line 2634** (display output path):
   - Similar replacement: `round((done_count / total * 100), 1)` → `round(progress.percentage, 1)`
   - May need to materialize snapshot once and reuse

3. In both cases, keep the `by_lane` dict in the output for backward compatibility — it's useful context alongside the weighted percentage.

**Validation**:
- [ ] `spec-kitty agent tasks status --json` shows weighted percentage
- [ ] `spec-kitty agent tasks status` display shows weighted percentage
- [ ] `by_lane` dict still present in JSON output

### T029: Update Scanner to Pre-Compute Weighted Progress

**Purpose**: The dashboard gets data from the scanner. Instead of sending raw counts and letting JS compute `done/total`, pre-compute the weighted percentage in Python.

**Steps**:

1. In `src/specify_cli/dashboard/scanner.py`:
   - In `scan_all_features()` or `_count_wps_by_lane()`:
   - After computing lane counts, materialize the status snapshot
   - Call `compute_weighted_progress(snapshot)`
   - Add `"weighted_percentage"` to the `kanban_stats` dict

2. The output structure becomes:
   ```json
   {
     "kanban_stats": {
       "total": 5,
       "planned": 0,
       "doing": 1,
       "for_review": 3,
       "approved": 0,
       "done": 1,
       "weighted_percentage": 58.0
     }
   }
   ```

3. Keep existing raw count fields (`planned`, `doing`, `for_review`, `approved`, `done`, `total`) for backward compatibility — the dashboard may still use them for the kanban column rendering.

**Validation**:
- [ ] Scanner emits `weighted_percentage` in kanban_stats
- [ ] Raw count fields still present
- [ ] `weighted_percentage` matches what `compute_weighted_progress()` would return

### T030: Update Dashboard JS

**Purpose**: Make the dashboard read the pre-computed `weighted_percentage` from the scanner payload instead of computing `done/total`.

**Steps**:

1. At `src/specify_cli/dashboard/static/dashboard/dashboard.js:319` (Overview panel):
   - Replace:
     ```javascript
     const completed = stats.done;
     const completionRate = total > 0 ? Math.round((completed / total) * 100) : 0;
     ```
   - With:
     ```javascript
     const completionRate = stats.weighted_percentage != null
       ? Math.round(stats.weighted_percentage)
       : (total > 0 ? Math.round((stats.done / total) * 100) : 0);
     ```
   - The fallback handles older scanner data that doesn't have `weighted_percentage`.

2. At `dashboard.js:401` (Kanban panel):
   - Same replacement pattern as above

3. Update progress bar rendering (lines ~369, 371, 431, 433) to use the new `completionRate`.

**Validation**:
- [ ] Dashboard shows ~30% when all WPs in `in_progress`
- [ ] Dashboard shows ~60% when all WPs in `for_review`
- [ ] Falls back to `done/total` if scanner data lacks `weighted_percentage`

### T031: Update `next_cmd.py` via Runtime Engine

**Purpose**: The `next` command at line 199 reads `decision.progress` which comes from `_compute_wp_progress()` in `next/decision.py`, not from `materialize()`. This needs a different wiring pattern.

**Steps**:

1. In `src/specify_cli/next/decision.py`, update `_compute_wp_progress()` (lines 225-262):
   - This function already computes raw lane counts
   - Add `weighted_percentage` to the returned dict:
     - Materialize the snapshot from the feature directory
     - Call `compute_weighted_progress(snapshot)`
     - Add `"weighted_percentage": progress.percentage` to the counts dict

2. In `src/specify_cli/cli/commands/next_cmd.py:194-200`:
   - Update the display to use `weighted_percentage`:
     ```python
     if decision.progress:
         p = decision.progress
         total = p.get("total_wps", 0)
         pct = int(p.get("weighted_percentage", 0))
         done = p.get("done_wps", 0)
         if total > 0:
             print(f"  Progress: {pct}% ({done}/{total} done)")
     ```

3. Note: `_compute_wp_progress()` needs the `feature_dir` to materialize the snapshot. Check if it already has access via the function parameters or needs to receive it.

**Validation**:
- [ ] `spec-kitty next` shows weighted percentage (not done/total)
- [ ] Display format is clear: "Progress: 60% (1/5 done)"
- [ ] Falls back gracefully if weighted_percentage is missing

### T032: Write Tests for Weighted Progress Across Surfaces

**Purpose**: Verify that all surfaces produce the same progress value for the same event log input.

**Test scenarios**:

1. **test_all_surfaces_agree_on_progress**: Create a feature with known lane states (3 for_review, 1 in_progress, 1 planned). Verify all surfaces report the same weighted percentage:
   - `show_kanban_status()` from agent_utils/status.py
   - `tasks status --json` output
   - Scanner JSON payload
   - next_cmd progress display

2. **test_progress_nonzero_when_no_done**: Feature with 5 WPs all in `in_progress` — progress should be 30%, not 0%

3. **test_progress_100_only_when_all_done**: Feature with 4 done + 1 approved — progress should be ~96%, not 80%

4. **test_progress_with_blocked_and_canceled**: Blocked/canceled WPs weight 0.0 — verify they don't inflate or deflate progress

5. **test_dashboard_js_uses_weighted_percentage**: Mock scanner data with `weighted_percentage`, verify JS would read it (or test via the Python rendering)

6. **test_backward_compat_without_weighted**: Scanner data without `weighted_percentage` — callsites fall back to done/total

**Files**: `tests/specify_cli/status/test_progress_integration.py` (new file)

## Definition of Done

- All 7 broken callsites use `compute_weighted_progress()` (directly or pre-computed)
- CLI, dashboard, and next command show identical weighted progress for the same input
- Progress is non-zero when WPs are `claimed`, `in_progress`, `for_review`, or `approved`
- `merge/state.py:102` remains unchanged (merge-specific binary progress)
- #443 is closed/cross-referenced as consolidated into #447
- 90%+ test coverage on new code

## Risks

- SaaS sync consumers might expect `done/total` format (mitigate: keep raw counts alongside weighted_percentage, C-005)
- Materializing snapshots at each callsite could be expensive for large missions (mitigate: snapshot is lightweight, read from JSONL)

## Reviewer Guidance

- Verify all 7 callsites are updated (check the line numbers from the table above)
- Confirm `merge/state.py:102` is intentionally NOT changed
- Check that backward-compat fields (done_count, by_lane) are preserved in all outputs
- Test with a real mission that has WPs in various lanes
- Verify #443 is closed or cross-referenced when this WP ships
