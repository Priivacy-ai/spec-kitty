---
affected_files: []
cycle_number: 1
mission_slug: review-verdict-write-integrity-01KZ1CGF
reproduction_command:
reviewed_at: '2026-08-02T19:58:18Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP01
---

# WP01 Review Feedback — Cycle 1 Rejection

## Verdict: REJECTED

## What's correct

- `create_rejected_review_cycle` (T001) correctly gained a `verdict` parameter; existing callers
  keep working via the default.
- `validate_review_artifact` (T002) correctly loosened to `REVIEW_ARTIFACT_VERDICTS`.
- The provenance guard (T003) — path-identity + content-identity, independently enforced — looks
  right, and `test_new_cycle_body_never_duplicates_a_prior_cycle_file` was correctly rewritten to
  `pytest.raises` per the WP's own correction note, asserting `latest()` still returns cycle 1.
- The commit step (T004) via `commit_artifact`/`ports.coord` is real — verified via a git fixture,
  not just "no exception raised".
- `tests/review/test_cycle.py` (14/14) and `tests/post_merge/test_review_artifact_consistency.py`
  (11/11) pass; lint sweep is clean (exit 0); `mypy --strict` has one pre-existing unrelated error
  confirmed present on the unmodified base.

Thank you for surfacing the integration-verification finding honestly instead of silently
patching an unowned file or declaring done around it — that's exactly right. But the finding
itself means this WP is not done: it describes a real gap in FR-001's acceptance criteria, not an
FYI to note and move past.

## Why this is rejected

**FR-001's entire point is that the *ordinary* `move-task --to approved` path — no
`--skip-review-artifact-check` — persists a real approved artifact.** Spec.md User Story 1's
Acceptance Scenarios 1 & 2, SC-002, and NFR-002 all hinge on this. The mission's own
`purpose_context` (recorded at mission creation, `MissionCreated` event in
`status.events.jsonl`) states the problem directly: *"the only escape hatch
(`--skip-review-artifact-check`) gets reached for on the ordinary reject-fix-approve path."*
Closing that is this WP's job — it is not a peripheral discovery to note and defer.

Trace of why the current implementation doesn't close it:

1. `_mt_finalize_plan` (where you added `_persist_approved_review_cycle()`) only runs *after*
   `decide_transition()` has already produced an `Emit` (see the call site — `_mt_finalize_plan`
   is invoked from the success path, never reached on a `RefuseExit1`).
2. `_guard_rejected_verdict` (`tasks_transition_core.py:364-388`) runs *inside*
   `decide_transition()`, before any `Emit`/`decision` exists. When `req.target_lane` is
   APPROVED/DONE and the WP's current latest verdict is `"rejected"`, it returns `RefuseExit1`
   unconditionally unless `--skip-review-artifact-check` (+ `--note`) is supplied.
3. Therefore, on the exact path this mission targets — reviewer runs a plain
   `move-task --to approved` after a genuine rework and re-review, no override flags — the
   transition is refused *before* `_persist_approved_review_cycle()` is ever reached. Your new
   code is correct but dead on arrival for the ordinary path.
4. This is independently pinned by two pre-existing tests neither in `tests/review/` nor
   `tests/post_merge/` (so your declared Test Strategy didn't run them, but your own
   "verify it's reachable from the CLI path" instinct found the underlying defect anyway):
   - `tests/specify_cli/cli/commands/agent/test_tasks_transition_core.py::test_rejected_verdict_without_skip_refuses`
   - `tests/integration/test_review_cycle_rejection_only.py::test_approving_a_rejected_wp_writes_no_verdict_artifact`
   Both currently assert the *old, broken* behavior (refusal / no artifact ever written) as the
   expected outcome. Their own docstrings/root-cause analysis describe precisely the defect
   FR-001 exists to fix — they were written to pin #2996(a) as reproduced against `main`, not to
   pin a permanent design choice. They need the same treatment T003 already gave
   `test_new_cycle_body_never_duplicates_a_prior_cycle_file`: rewritten to assert the *fixed*
   behavior, not left asserting the bug.

## What to fix (cycle 1)

1. **Fix `_guard_rejected_verdict`** (`src/specify_cli/cli/commands/agent/tasks_transition_core.py`)
   so the ordinary path (no `--skip-review-artifact-check`) no longer unconditionally refuses when
   the current latest verdict is `rejected` — it should let the transition proceed to
   `_mt_finalize_plan`, which now writes a genuine `approved` artifact via your T001/T004 writer.
   **Preserve `_authorize_review_override`/the `--skip-review-artifact-check --note` path
   unchanged** for genuine arbiter overrides — spec.md's Edge Cases section is explicit that this
   mechanism must keep working, it's just no longer *required* for the ordinary case. Do not
   remove the guard entirely; narrow its refusal condition.
2. **Rewrite the two pinned tests** listed above to assert the new, correct behavior (ordinary
   approve succeeds, a fresh `review-cycle-(N+1).md` with `verdict: approved` and a real
   `reviewer_agent` is created) — same pattern as your T003 rewrite of
   `test_new_cycle_body_never_duplicates_a_prior_cycle_file`. Do not delete or skip them; they are
   this mission's most direct evidence FR-001 actually closes #2996(a).
3. **Add an end-to-end CLI-level regression** (if one doesn't already fall out of #2 — check
   `test_review_cycle_rejection_only.py`'s existing fixture shape) proving: reject a WP, rework,
   resubmit through the normal lifecycle, then `move-task --to approved` with **no**
   `--skip-review-artifact-check` — succeeds and writes the approved artifact. This is the literal
   SC-002/Acceptance-Scenario-1&2 proof and should not only exist at the unit level
   (`tests/review/test_cycle.py` already covers the writer function in isolation).
4. Re-run the full `tests/review/ tests/post_merge/ tests/agent/` scoped regression plus these two
   now-corrected files, and re-confirm the diff-scoped lint sweep and `mypy --strict` are clean.
5. Update the Activity Log with a clear entry describing this fix and why it was necessary (link
   back to this feedback).

This is cycle 1 of a max-3 rejection budget.
