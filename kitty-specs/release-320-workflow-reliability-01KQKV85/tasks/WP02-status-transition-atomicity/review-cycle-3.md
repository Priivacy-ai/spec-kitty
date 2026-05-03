---
affected_files: []
cycle_number: 3
mission_slug: release-320-workflow-reliability-01KQKV85
reproduction_command:
reviewed_at: '2026-05-03T13:21:01Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP02
---

**Issue 1**: `move-task` and `agent status emit` do not expose the success fields required by `contracts/status-transition-atomicity.yaml`.

The contract says successful observable output requires `event_id`, `work_package_id`, `to_lane`, and `status_events_path`. The implementation verifies readback inside `emit_status_transition`, but `move-task` still returns only `result`, `task_id`, `old_lane`, `new_lane`, and `path` from `src/specify_cli/cli/commands/agent/tasks.py`. `agent status emit` returns `event_id`, `wp_id`, lane fields, and actor, but still omits `status_events_path` and does not use the required `work_package_id` key. Please make these command outputs additive and add regression assertions for the contract fields.

**Issue 2**: Event persistence failures are not reported with the structured failure fields required by the contract.

The contract failure output requires `diagnostic_code`, `violated_invariant`, and `remediation`. `EventPersistenceError` currently carries the necessary context in a formatted string, and the CLI JSON error helpers wrap it as only `{"error": "..."}`. Please convert readback/append verification failures into structured command diagnostics, preserving mission slug/id, WP id, requested lane, and event path, and test JSON output for missing-event/readback failure cases.

**Validation run**:

- `SPEC_KITTY_ENABLE_SAAS_SYNC=0 uv run pytest tests/status/test_store.py tests/status/test_work_package_lifecycle.py tests/tasks/test_move_task_git_validation_unit.py tests/unit/status/test_review_claim_transition.py -q -x` passed: 58 passed.
- `SPEC_KITTY_ENABLE_SAAS_SYNC=0 uv run pytest tests/status tests/tasks/test_move_task_git_validation_unit.py tests/unit/status/test_review_claim_transition.py -q` exited non-zero without a failure summary in the PTY output. Re-run the full WP command after addressing the contract-output gaps.
