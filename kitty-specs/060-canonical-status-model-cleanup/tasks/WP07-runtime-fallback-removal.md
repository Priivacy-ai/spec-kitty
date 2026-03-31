---
work_package_id: WP07
title: Runtime Fallback Removal
dependencies: []
requirement_refs:
- FR-008
- FR-009
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: main
base_commit: 7de1e1542d5ef2a47e889db5d8acf20562eab160
created_at: '2026-03-31T07:22:41.645329+00:00'
subtasks: [T024, T025, T026, T027, T028, T029]
shell_pid: "88151"
agent: "orchestrator"
history:
- at: '2026-03-31T06:58:09+00:00'
  actor: planner
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/tasks_support.py
execution_mode: code_change
owned_files:
- src/specify_cli/tasks_support.py
- src/specify_cli/dashboard/scanner.py
- src/specify_cli/mission_v1/guards.py
- src/specify_cli/next/runtime_bridge.py
- src/specify_cli/cli/commands/merge.py
- tests/specify_cli/test_runtime_hard_fail.py
---

# WP07: Runtime Fallback Removal

## Objective

Remove frontmatter-lane fallback from the 5 remaining runtime reader sites. Replace each with canonical-only reads. Hard-fail when canonical state is missing (event log absent) or show "uninitialized" for individual WPs missing from the event log (read-only commands).

## Context

- WP03 already removed the bootstrap/sync block in `tasks.py` and WP04 removed workflow.py fallbacks
- This WP covers the remaining 5 files that still have frontmatter-lane fallback
- After this WP, NO active runtime code reads lane from frontmatter

## Implementation Command

```bash
spec-kitty implement WP07 --base WP02
```

---

## Subtask T024: tasks_support.py — WorkPackage.lane

**Location**: `src/specify_cli/tasks_support.py` around line 293

**Steps**:
1. Find the `WorkPackage.lane` property
2. Current: tries event log via `get_wp_lane()`, falls back to `frontmatter.get("lane")`
3. Change: use `get_wp_lane()` only. If it returns None/default:
   - Check if `status.events.jsonl` exists for the feature
   - If event log absent: raise `RuntimeError("Canonical status not found for feature {slug}. Run finalize-tasks.")`
   - If event log exists but WP has no event: return `"uninitialized"`
4. Import `get_wp_lane` from `specify_cli.status.lane_reader`

---

## Subtask T025: dashboard/scanner.py — Both Fallback Branches

**Locations**: `src/specify_cli/dashboard/scanner.py` around lines 322 and 454

**Steps**:
1. **Line 322** (`_count_wps_by_lane_frontmatter`):
   - Remove `frontmatter.get("lane", "planned")` fallback
   - Use `get_all_wp_lanes()` from `status/lane_reader.py` only
   - WPs not in the lane dict → "uninitialized" (for display)
   - If event log absent → raise with finalize-tasks guidance

2. **Line 454** (additional dashboard fallback):
   - Remove `frontmatter.get("lane", default_lane)` fallback branch
   - Use event log state only

3. Rename `_count_wps_by_lane_frontmatter()` to `_count_wps_by_lane()` (no longer frontmatter-based)

---

## Subtask T026: mission_v1/guards.py — Delete Frontmatter Lane Reader

**Location**: `src/specify_cli/mission_v1/guards.py` around line 169

**Steps**:
1. Find `_read_lane_from_frontmatter()` function
2. Replace with call to `get_wp_lane()` from `status/lane_reader.py`
3. If the function is only used within guards.py, inline the replacement
4. Ensure the caller handles None/missing state appropriately

---

## Subtask T027: next/runtime_bridge.py — Use lane_reader

**Location**: `src/specify_cli/next/runtime_bridge.py` around line 117

**Steps**:
1. Current: `resolve_lane_alias(str(wp_state.get("lane", "planned")))` where `wp_state` comes from frontmatter
2. Change: use `get_wp_lane(feature_dir, wp_id)` from `status/lane_reader.py`
3. Handle None: if no canonical state, hard-fail with guidance

---

## Subtask T028: merge.py — Remove Frontmatter Fallback

**Location**: `src/specify_cli/cli/commands/merge.py` around line 72

**Steps**:
1. Current: reads WP lane with `frontmatter.get("lane")` fallback via `resolve_lane_alias()`
2. Change: read from canonical reducer state only
3. If WP has no canonical state: hard-fail merge preflight with guidance

---

## Subtask T029: Write Hard-Fail Tests

**File**: `tests/specify_cli/test_runtime_hard_fail.py` (new)

**Tests**:
1. **Event log absent → hard-fail**:
   - Create feature with WP files but no `status.events.jsonl`
   - Call `WorkPackage.lane` → raises with "Canonical status not found" + finalize-tasks guidance
   - Call dashboard scanner → raises similarly
   - Call merge preflight → raises similarly

2. **Event log exists, WP missing → "uninitialized"**:
   - Create feature with event log containing events for WP01 only, but WP02 also exists
   - `WorkPackage("WP02").lane` → returns "uninitialized"
   - Dashboard shows WP02 as "uninitialized", WP01 in correct lane

3. **Event log exists, WP has state → normal behavior**:
   - Full canonical state exists
   - All readers return correct lane values
   - No frontmatter consulted

---

## Definition of Done

- [ ] NO active runtime code reads `lane` from WP frontmatter
- [ ] Event log absent → all commands hard-fail with finalize-tasks guidance
- [ ] Event log exists, WP missing → read-only commands show "uninitialized"
- [ ] Event log exists, WP has state → normal behavior unchanged
- [ ] `_count_wps_by_lane_frontmatter` renamed (no longer frontmatter-based)
- [ ] Tests cover all three state scenarios
- [ ] `mypy --strict` passes on all modified files

## Reviewer Guidance

- Grep the repo for `frontmatter.*lane` and `extract_scalar.*lane` in non-migration Python files — should be zero matches after this WP
- Verify each hard-fail message names the specific feature slug and the exact command to run
- Verify "uninitialized" is the display label, not a lane value (it's not in the Lane enum)

## Activity Log

- 2026-03-31T07:22:41Z – orchestrator – shell_pid=88151 – lane=doing – Started implementation via workflow command
- 2026-03-31T07:31:20Z – orchestrator – shell_pid=88151 – lane=for_review – Ready for review: removed all 5 frontmatter-lane fallbacks, 22 tests pass
- 2026-03-31T07:31:51Z – orchestrator – shell_pid=88151 – lane=approved – Review passed: all 5 frontmatter-lane fallback sites removed, CanonicalStatusNotFoundError for missing event log, 'uninitialized' for missing WPs, _count_wps_by_lane renamed, 677 tests pass. Approved.
