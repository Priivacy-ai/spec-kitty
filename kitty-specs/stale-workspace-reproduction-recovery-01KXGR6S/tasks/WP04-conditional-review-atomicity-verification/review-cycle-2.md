---
affected_files:
- src/specify_cli/cli/commands/agent/workflow_executor.py
- tests/agent/test_workflow_review_lane_gate.py
cycle_number: 2
mission_slug: stale-workspace-reproduction-recovery-01KXGR6S
reviewed_at: '2026-07-14T19:48:00Z'
reviewer_agent: reviewer-renata
verdict: rejected
wp_id: WP04
---

# WP04 Review Cycle 2 — Changes Requested

## Verdict

Changes requested. The cleanup/ownership blocker from cycle 1 is resolved and its
focused tests pass. The placement-success predicate still does not provide the
required per-ref proof for COORD.

## Blocking issue — COORD advancement is not tied to a returned COORD commit hash

`_commit_partition_aware_workflow_change()` now requires both refs to advance,
but `returned_hashes_match = all(...)` only validates entries that happen to be
present in `router_result.commit_hashes`. It does not require the returned hash
set to equal `expected_refs`, and only `primary_hash_proved` is explicit.

Therefore this deterministic combination still enters the success branch:

- PRIMARY and COORD refs both changed after the router call;
- router result status is `committed`;
- `commit_hashes` contains only the matching PRIMARY hash;
- COORD changed for an unproved reason or the router omitted its receipt.

For that input, `all_refs_advanced`, `primary_hash_proved`, and
`returned_hashes_match` are all true. The function emits committed receipts for
both refs despite having no returned COORD commit proof. This does not satisfy the
cycle-1 remediation, T020 step 6, FR-004, or C-003.

Required remediation:

1. Require exact per-ref evidence, for example
   `set(commit_hashes) == expected_refs` plus equality between every returned hash
   and its post-call ref OID, or explicit PRIMARY and COORD hash proofs.
2. Add the missing negative test: both refs advance but the router returns only
   the PRIMARY hash (and preferably a wrong COORD hash variant). Assert refusal
   and no false committed receipts.
3. Retain the existing tests for PRIMARY-only advancement and all cleanup paths.

## Re-review evidence

- Frozen acceptance witness remains exact: parent blob `48ca83d8091dde8cd288fc7905ea6c128aec62f8`,
  post-980e blob `303ba210883e95f6037c7350a14ad0778a842d97`, and no later witness edit.
- Remediation commit `eaff3130c8436ebfc3794db36da9f2fca961f8ba` changes only the four owned
  production/test files; no router or out-of-map implementation expansion.
- Focused placement/cleanup/failure tests: 10 passed, 44 deselected.
- Ruff passed and strict mypy passed for the changed production/test surface.
- Cleanup coverage now includes claim failure, prompt failure, cleanup-error
  precedence, idempotence, pre-existing worktree preservation, and
  foreign/replaced-lock preservation.

## Anti-pattern checklist

1. Dead code: PASS.
2. Synthetic-fixture test: PASS — the real-CLI acceptance witness remains intact;
   focused fault tests directly invoke the production seam.
3. Silent empty return: PASS.
4. FR coverage: FAIL — FR-004/C-003 still lack exact COORD hash proof and the
   missing-hash negative test.
5. Frozen surface: PASS.
6. Locked decision: PASS — no router change or second authority was introduced.
7. Shared-file ownership: PASS.
8. Production fragility: FAIL — success can still be emitted for an unproved
   COORD ref change.
