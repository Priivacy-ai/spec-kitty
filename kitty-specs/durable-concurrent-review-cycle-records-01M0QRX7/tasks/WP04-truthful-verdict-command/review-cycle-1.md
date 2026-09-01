---
affected_files: []
cycle_number: 1
mission_slug: durable-concurrent-review-cycle-records-01M0QRX7
reproduction_command:
reviewed_at: '2026-08-24T06:36:35Z'
reviewer_agent: user
wp_id: WP04
---

# WP04 Review Feedback — Cycle 1

## Blocking issue: T021 is not proven at the production command boundary

The implementation has the intended lock order and the current focused tests pass, but the required real-command failure/retry/idempotence matrix is incomplete. `test_queue_busy_fails_before_evidence_allocation` and `test_adverse_automatic_commit_outcomes_are_typed_and_retain_evidence` call `_persist_approved_review_cycle` directly. They therefore do not prove the production `_do_move_task` behavior required by T021/T022: exit 1, structured error output, no `result: success`, no authoritative verdict/status event, and the correct evidence/destination fields. The adverse test also combines wrong-surface, raised exception, and timeout at the helper boundary only.

Two explicitly required recovery cases are absent entirely: an identical retry after a returned or raised persistence failure must adopt the same retained path and succeed, and a response interruption after a commit must retry idempotently without allocating a duplicate record.

### Required remediation

Extend `tests/specify_cli/cli/commands/agent/test_move_task_durability.py` without weakening the production path:

1. Drive queue busy, returned router error/wrong-surface, raised exception, and timeout through `_run_move` / `_do_move_task`. For each automatic failure assert exit 1, `result: error`, the typed classification/reason, absence of a success/event reference, and the required mutation invariant. Queue busy must prove no evidence file and no authoritative status event; persistence failures may retain the exact evidence path but must not append the verdict event.
2. For returned and raised commit failure, retry the identical verdict through the real command with a succeeding router and assert that the same retained `review-cycle-N.md` is adopted, durably verified, referenced by the one authoritative event, and no `N+1` duplicate is created.
3. Simulate a response interruption after the Git destination contains the committed bytes but before the first invocation can report completion. Retry through the real command and assert adoption/idempotence: the same path, one current verdict event, no duplicate cycle.
4. Instrument the actual evidence Git invocation (not just the enclosing `create_rejected_review_cycle` call) to prove the review-cycle allocation `feature_status_lock` is not held there, while the checkout verdict queue is held. Preserve the existing assertion that the queue is released before `_mt_execute` starts.
5. Keep real routers/real Git for the happy path and retained-evidence read-back; inject only the documented busy/router/response seams. Re-run the 19-test command (with the new cases), frozen compatibility/seam guards, Ruff, strict mypy, and the combined WP02–WP04 diff-coverage check.

### Review evidence

- Focused WP04 suite: 19 passed.
- Frozen compatibility/seam suite: 407 passed.
- Ruff: passed.
- Strict mypy on both touched production modules: passed.
- Combined changed-line coverage against `origin/main` using WP02/WP03/WP04 focused suites: 93% (threshold met).
- Commit ownership: `5dd2e4d37` touches only the owned focused test; `523e48dc9` touches only the two owned production modules and focused test.

The production code inspection found no demonstrated lock inversion: automatic evidence work is under the checkout queue, the queue exits before `_mt_execute` takes the event/status lock, and compensation reacquires the same queue only after `_mt_execute` has unwound. The rejection is for the explicit command-level acceptance proof above, not for a known production lock-order defect.
