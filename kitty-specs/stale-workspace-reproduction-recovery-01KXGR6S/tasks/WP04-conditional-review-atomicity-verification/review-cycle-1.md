---
affected_files:
- src/specify_cli/cli/commands/agent/workflow_executor.py
- tests/specify_cli/cli/commands/test_workspace_husk_resolution_1833.py
- tests/agent/test_workflow_review_lane_gate.py
cycle_number: 1
mission_slug: stale-workspace-reproduction-recovery-01KXGR6S
reviewed_at: '2026-07-14T19:35:00Z'
reviewer_agent: reviewer-renata
verdict: rejected
wp_id: WP04
---

# WP04 Review Cycle 1 — Changes Requested

Reviewer: Reviewer Renata  
Reviewed commits: `980eae6a9` (test-only contract), `c4478b358` (production)  
Approved dependency witness blob: `48ca83d8091dde8cd288fc7905ea6c128aec62f8`

## Verdict

Changes requested. The real-CLI contract is green and the RED-first/frozen-witness
discipline is sound, but the new partition-aware commit path does not yet prove
the atomic placement and compensation contract required by T019/T020.

## Blocking issue 1 — success does not prove that both placement commits landed

`_commit_partition_aware_workflow_change()` computes `status_recorded` as
`after_oids[status_placement_ref] is not None`. A pre-existing COORD ref therefore
satisfies the check even when it did not advance. The canonical router's aggregate
result intentionally projects the caller partition: `_merge_group_results()` may
return the PRIMARY `WORK_PACKAGE_TASK` result as `status="committed"` while the
other partition is `unchanged` or `no_op_wrong_surface`. At
`workflow_executor.py:150-152`, that combination is accepted as success and emits
committed receipts for both refs, even though the COORD status commit was never
proved. This contradicts T020 step 6, FR-004, C-003, and the contract's requirement
that success means every required placement commit landed.

Required remediation:

1. Require explicit evidence that both the PRIMARY and COORD groups committed.
   Validate the canonical router's per-ref commit receipts/hashes and/or require
   both expected refs to advance; mere ref existence is not evidence.
2. Add focused tests for PRIMARY committed plus COORD `unchanged`,
   `no_op_wrong_surface`, and `error`/partial-failure outcomes. Assert non-zero
   truthful output, no false committed receipt, restored working-tree bytes, and
   the exact ref/porcelain outcome.
3. If satisfying the partial-ref atomicity contract requires changing the
   canonical router outside WP04 ownership, stop and return the architectural
   ownership finding instead of adding a second transaction mechanism here.

## Blocking issue 2 — required later-failure and ownership-safety tests are missing

The only new cleanup test calls prepare then cleanup for an invocation-created
worktree. There is no failure injection after readiness, no prompt/claim failure
snapshot, no repeated-cleanup proof, and no direct proof that cleanup preserves a
pre-existing worktree or a foreign/replaced lock. T018 steps 4/7/8 and T019 steps
1/8/9 explicitly require those cases. The production exception path and equality
guard are therefore not independently exercised.

Required remediation:

1. Add focused post-readiness failure injection at meaningful boundaries (at
   minimum claim/placement failure and prompt construction after successful
   readiness) and assert lock/path/status/WP/ref/porcelain surfaces appropriate to
   each reached boundary.
2. Prove cleanup is idempotent and removes only an invocation-created worktree and
   the exact lock acquired by this invocation.
3. Prove a pre-existing worktree and a foreign/replaced active lock remain intact.
4. Prove cleanup failure cannot hide or replace the original operator-visible
   error.

## Independent evidence

- Frozen witness: `980eae6a9^` is exactly blob `48ca83d8091dde8cd288fc7905ea6c128aec62f8`;
  `980eae6a9` changes only the desired review outcome branch for rows 9-12; the
  production commit does not edit the witness.
- RED-first exact nodes at `980eae6a9`: 4 failed as expected.
- Same exact nodes at `c4478b358`: 4 passed in 57.75s.
- Full 12-row real-CLI witness: 12 passed in 52.66s.
- Owned focused suites: 45 passed in 59.76s.
- WP02 regression set: 70 passed in 60.53s.
- WP03 lifecycle integration: 3 passed in 56.02s.
- Ruff passed; strict mypy passed; architectural/terminology gates: 11 passed.
- `git diff --check` passed; lane worktree was clean; PR #2641 is OPEN and DRAFT.
- The observed pre-review `no_coverage` result is not a rejection reason: the
  independently approved real-CLI witness and exact six-surface evidence are sound.

## Anti-pattern checklist

1. Dead code: PASS — new internal helpers have production callers.
2. Synthetic-fixture test: PASS — the acceptance witness uses the registered CLI
   and real Git/worktree state.
3. Silent empty return: PASS — no new silent empty-return handler was found.
4. FR coverage: FAIL — FR-004/C-003 aggregate placement failure is not directly
   exercised, and the success predicate does not prove both commits.
5. Frozen surface: PASS — the approved blob and rows 1-8 are preserved.
6. Locked decision: PASS — no second workspace resolver or #2160 ownership claim
   was introduced.
7. Shared-file ownership: PASS — the one out-of-map witness edit matches the
   reviewed Charter exception exactly.
8. Production fragility: FAIL — split-placement refusal/partial failure can be
   misreported because the status-ref check accepts existence instead of a proven
   commit, and the required failure tests are absent.
