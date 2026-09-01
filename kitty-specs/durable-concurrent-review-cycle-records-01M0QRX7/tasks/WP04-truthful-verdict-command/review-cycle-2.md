---
affected_files: []
cycle_number: 2
mission_slug: durable-concurrent-review-cycle-records-01M0QRX7
reproduction_command:
reviewed_at: '2026-08-24T07:04:27Z'
reviewer_agent: user
wp_id: WP04
---

# WP04 Review Feedback — Cycle 2

## Blocking issue: the retry tests compare the wrong event identity

Commit `e446caced` closes the cycle-1 command-boundary gaps for busy, returned router error, wrong-surface, raised exception, timeout, retained-path retry, post-commit interruption, and direct Git lock observation. However, the two new retry/idempotence tests assert that the authoritative approval event's `review_result.reference` equals the caller's `approval_ref` (`test_move_task_durability.py:1333` and `:1387`). That is not the durable evidence identity they separately read from `payload["evidence_ref"]`.

The mission data-model invariant requires every durable result's authoritative event to reference `evidence_ref`. `create_rejected_review_cycle` already constructs the correct `CreatedRejectedReviewCycle.review_result` whose reference is the canonical `review-cycle://.../review-cycle-N.md` pointer, and the rejection path correctly installs that result. The approval path instead discards it: `_persist_approved_review_cycle` returns only the durability signal, then `_mt_plan_review_result` rebuilds a different `ReviewResult` from `approval_ref`. Consequently a green retry has one committed evidence artifact and one authoritative event, but the event does not reference that artifact; `feedback_path` is also absent. The tests green-light this mismatch by comparing two approval-token identities rather than correlating the event to the persisted evidence.

### Required remediation

1. On the approval path, derive the emitted `ReviewResult` from the successfully verified `CreatedRejectedReviewCycle.review_result` (or an equivalently canonical single seam) so its reference identifies the same durable cycle carried by `VerdictPersistenceOutcome.evidence_ref`. Preserve the event-log/evidence authority split; do not add a second verdict authority.
2. Update the returned-error retry, raised-error retry, and post-commit-interruption retry assertions to compare the authoritative event's evidence pointer/path to the retained `evidence_ref`, not to `approval_ref`. Assert that resolving the pointer yields the same `review-cycle-2.md` whose exact bytes are reachable at `destination_ref`.
3. Keep the existing one-event/no-cycle-3 assertions and add a negative control that would fail if `_mt_plan_review_result` reverted to rebuilding the event from `approval_ref`.
4. Re-run the focused 24-test suite, 407 frozen compatibility/seam tests, Ruff, strict mypy, and the 84-test WP02–WP04 diff-coverage gate.

### Review evidence

- Focused WP04 suite: 24 passed.
- Frozen compatibility/seam suite: 407 passed.
- Combined WP02–WP04 suite: 84 passed.
- Combined changed-line coverage versus `origin/main`: 95% (threshold met).
- Ruff: passed.
- Strict mypy on both touched production modules: passed.
- Lock/order inspection: the evidence Git stage/read-back is directly observed with the allocation `feature_status_lock` absent and verdict queue held; the queue is released before `_mt_execute`; compensation reacquires the queue only after `_mt_execute` unwinds.

This rejection is solely for the missing authoritative event-to-evidence correlation and the tests' wrong-identity comparison. The other cycle-1 blockers are causally covered.
