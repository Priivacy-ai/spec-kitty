---
affected_files: []
cycle_number: 1
mission_slug: execution-state-domain-remediation-01KT6HVH
reproduction_command:
reviewed_at: '2026-06-03T13:03:48Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP06
---

# Review Feedback for WP06 — Cycle 1

## Blocking Issues

### Issue 1: DoD items 2 and 3 — `resolve_action_context` not used (FR-032, FR-033 violated)

The DoD explicitly requires:
- "runtime_bridge query-mode derives feature_dir through `resolve_action_context`"
- "workflow.py fix-mode routes through `resolve_action_context`"

The actual implementation uses lower-level helpers instead:
- `src/runtime/next/runtime_bridge.py:2985-2991` (in `query_current_state`) — uses `resolve_mission_read_path` from `missions._read_path_resolver`, not `resolve_action_context`
- `src/runtime/next/runtime_bridge.py:3122-3128` (in `answer_decision_via_runtime`) — same, uses `_resolve_read_path`
- `src/specify_cli/cli/commands/agent/workflow.py:859` (in `_ensure_target_branch_checked_out`) — uses `get_feature_target_branch`, not `resolve_action_context`

The comments in the code acknowledge this: they say the helpers are "sub-functions used inside `resolve_action_context`" — but the DoD and spec FR-032/FR-033 require routing through the canonical OHS entry point (`resolve_action_context`) itself, not its internal sub-functions.

**Note**: If `resolve_action_context` cannot be used directly (e.g., it requires an `action` parameter that isn't available at these call sites), this must be explicitly documented as a constraint and the DoD must be updated. The current implementation does not document this reasoning.

### Issue 2: DoD items 6 and 7 — ratchet tests not present on the branch

The DoD requires:
- e2e ratchet (`tests/architectural/test_execution_context_parity.py`) green
- status boundary test (`tests/architectural/test_status_module_boundary.py`) green

Neither file exists anywhere on the `kitty/mission-execution-state-domain-remediation-01KT6HVH-lane-e` branch or its base:
```
$ git show kitty/mission-execution-state-domain-remediation-01KT6HVH:tests/architectural/test_execution_context_parity.py
fatal: path does not exist
$ find . -name 'test_execution_context_parity.py'
(no output)
$ find . -name 'test_status_module_boundary.py'
(no output)
```

These tests exist only in lane-a (WP02) and lane-b (WP03), which are approved but not merged into the base branch yet. The WP06 lane-e was branched from the mission base which doesn't include WP02/WP03's code contributions.

The DoD says these tests must be green — they cannot be "green" if they don't exist on the branch.

### Issue 3: DoD item 5 — grep zero-hits criterion not met

The DoD grep:
```
grep -rn 'kitty-specs.*mission_slug|main_repo_root.*kitty|feature_dir.*slug' src/ --include='*.py' | grep -v 'status/' | grep -v 'core/execution_context'
```
returns 221 hits (not zero) on this branch. While most are pre-existing in other WPs' files (outside WP06's owned_files), the DoD requires zero hits globally across `src/`.

## What Must Change

1. **For issues 2 and 3 (ratchet tests)**: The implementer needs to either:
   - Rebase lane-e on top of the merged WP02/WP03 content so the tests exist and can be run; OR
   - Document in the WP that WP06's DoD test-green items are contingent on WP02/WP03 being on the same branch (i.e., these are pre-merge validation items, not per-WP items)

   The simplest fix: rebase/merge the lane-e branch to include WP02 (lane-a) and WP03 (lane-b) content before re-submitting for review.

2. **For issue 1 (resolve_action_context)**: Either:
   - Route the three call sites through `resolve_action_context` as required by the DoD and FR-032/FR-033; OR
   - File a documented exception explaining why `resolve_action_context` cannot be used at these sites (e.g., it requires `action` and `wp_id` parameters that aren't available in a query-mode context), and update the DoD text to reflect the accepted alternative (using `_resolve_read_path` / `get_feature_target_branch` as canonical sub-function substitutes)

   The implementer's approach of using sub-functions is functionally reasonable, but violates the letter of the DoD and FR. The reviewer cannot approve a DoD item that says "X" when the implementation does "Y", even if Y is a reasonable approximation of X.
