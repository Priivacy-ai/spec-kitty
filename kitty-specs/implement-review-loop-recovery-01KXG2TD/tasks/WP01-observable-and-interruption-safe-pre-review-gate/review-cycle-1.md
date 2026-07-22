---
affected_files:
  - path: src/specify_cli/review/pre_review_gate.py
  - path: tests/review/test_pre_review_gate_engine.py
  - path: tests/specify_cli/cli/commands/agent/test_tasks_move_task_pre_review_gate_observability.py
cycle_number: 1
mission_slug: implement-review-loop-recovery-01KXG2TD
reproduction_command: uv run pytest tests/review/test_pre_review_gate_engine.py tests/review/test_pre_review_gate_integration.py tests/specify_cli/cli/commands/agent/test_tasks_move_task_pre_review_gate_observability.py -q -n0
reviewed_at: '2026-07-14T15:08:25+02:00'
reviewer_agent: codex:default:reviewer-renata:reviewer
verdict: rejected
wp_id: WP01
review_artifact_override_at: "2026-07-14T13:38:49Z"
review_artifact_override_actor: "operator"
review_artifact_override_wp_id: "WP01"
review_artifact_override_reason: "Arbiter override: cycle 2 independent Reviewer Renata approval supersedes rejected cycle 1; 80 focused tests and all static gates passed, with all three prior blockers re-verified closed"
---

# WP01 Review Cycle 1 — Changes Requested

## Blocking finding 1: Windows cleanup does not terminate the owned process tree

`_launch_scoped_process()` creates a Windows process group, but `_signal_owned_process_tree()` handles Windows by calling only `Popen.terminate()` or `Popen.kill()` on the direct child. Those operations do not terminate descendants, so a pytest child process can survive timeout or cancellation. This violates the plan, WP T003, and Definition of Done requirement that the canonical runner terminate and reap its owned child/process tree on supported platforms.

Use a narrowly owned Windows process-tree mechanism that terminates descendants as well as the parent, with bounded graceful termination, kill escalation, and reap. Add explicit platform-shaped tests for both Windows and POSIX launch/signal branches; the current suite contains no test that exercises either `_launch_scoped_process()` or `_signal_owned_process_tree()` without replacing the signaling helper.

## Blocking finding 2: The interruption cleanliness matrix is incomplete

`test_json_interruption_is_singular_and_precedes_every_mutation` replaces the real gate with an already-composed verdict and checks only the fake router, one WP file, and one event-log file. It does not snapshot and compare the materialized lane, git HEAD/commit count, placement commits, or Spec Kitty-owned dirty paths across planning, coordination, and lane checkouts. `test_gate_created_path_is_preserved_and_surfaced` also replaces both dirty-path discovery and the gate. Therefore NFR-003, SC-003, and T006 are not acceptance-tested across every residue facet they enumerate.

Add exact-Typer-entry timeout and catchable-cancellation fixtures synchronized at the canonical runner seam. Snapshot and compare every NFR-003 facet before and after the attempted transition in the relevant primary, coordination, and lane workspaces. Keep the test-owned sentinel assertion, but exercise real dirty-path discovery rather than returning the expected path from a mock.

## Blocking finding 3: The SIGKILL recovery test is vacuous with respect to the command

`test_sigkill_recovery_reads_prior_authoritative_lane` starts and kills an unrelated sleeping Python process, then confirms that an event file which no product code touched remains unchanged. It would pass if the pre-review implementation were deleted, so it does not prove FR-007/T006 for `move-task --to for_review`.

Run the exact command in an isolated child, synchronize so the child is inside the real pre-mutation gate, kill that command/process group, reap it from the harness, and then invoke the authoritative status/reconciliation read. Assert the prior lane and absence of a new transition event without claiming rollback.

## Verified evidence retained

- The dedicated RED commit contains only the exact Typer acceptance test. Running it against the untouched base produced the intended failure: zero `still running` messages versus the unchanged `>= 2` assertion.
- The implementation-focused suite passed independently: 72 tests.
- Ruff, mypy, the terminology guard, and `git diff --check` passed.

These green checks do not override the three unmet acceptance and process-lifecycle requirements above.
