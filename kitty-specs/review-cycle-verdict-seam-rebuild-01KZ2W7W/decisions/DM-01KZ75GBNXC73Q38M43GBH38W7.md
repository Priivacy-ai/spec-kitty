# Decision Moment `01KZ75GBNXC73Q38M43GBH38W7`

- **Mission:** `review-cycle-verdict-seam-rebuild-01KZ2W7W`
- **Origin flow:** `plan`
- **Slot key:** `wp11_revert_partition_kind_bug`
- **Input key:** `wp11_revert_partition_kind_bug`
- **Status:** `resolved`
- **Created:** `2026-08-04T19:55:13.469938+00:00`
- **Resolved:** `2026-08-04T19:55:16.573686+00:00`
- **Resolved by:** `Stijn Dejongh (operator)`
- **Opened by:** `claude-opus-5`
- **Other answer:** `false`

## Question

WP15 found that WP11's revert_committed_verdict_write resolves its commit target with kind=WORK_PACKAGE_TASK, which the placement seam maps to the PRIMARY ref, while WP04's ADR re-pins REVIEW_CYCLE as COORD. Verified empirically: WORK_PACKAGE_TASK -> pr/review-verdict-write-integrity-01KZ1CGF, REVIEW_CYCLE -> kitty/mission-review-cycle-verdict-seam-rebuild-01KZ2W7W. The revert calls safe_commit directly, bypassing the partition regrouping that would otherwise override a stale kind, so on coord topology the compensator commits a deletion on the wrong branch and the orphan survives -- FR-002 unmet. WP11's tests passed because they used a single-branch fixture where both kinds resolve identically. tasks_verdict_persistence.py is owned only by closed WPs (WP06, WP11, WP12). How should the fix be routed?

## Options

- amend-WP13-which-already-corrects-the-same-stale-partition-claim
- reopen-WP11
- defer-to-WP17

## Final answer

amend-WP13-which-already-corrects-the-same-stale-partition-claim

## Rationale

OPERATOR-CONFIRMED. This is a regression THIS MISSION introduced, not a pre-existing defect, so it is squarely in scope -- the operator's standing direction is that tackling this class of issue is part of the mission's purpose. Routed to WP13 because its T061 already corrects the identical false claim ('WORK_PACKAGE_TASK, PRIMARY-partition for every topology') in the sibling post_merge/review_artifact_consistency.py: same defect class, same WP, so the correction lands once and coherently. WP13 is live; WP11 and WP12 are approved and closed, and reopening a closed WP is heavier than extending a running one whose scope already covers the class. Ownership legality: no live WP owned the file; WP13's amendment adds it to owned_files AND to create_intent, the latter because the file does not exist on the PRIMARY checkout (WP06 created it in lane-e and the lane is unmerged), which is the same mechanism WP06/WP11/WP12 all use to satisfy the gate. finalize-tasks --validate-only passes at 18 WPs / 0 modified. Scope: change the resolved kind to REVIEW_CYCLE, correct the docstring's PRIMARY-for-every-topology claim, and add a COORD-topology regression test that would have caught this -- NOT a wider refactor. REVIEWER ACCOUNTABILITY, recorded deliberately: my WP11 review verified the compensator's placement, its ordering, and that it used write_target rather than a hand-built CommitTarget, but never checked WHICH KIND it passed. A single-branch fixture makes this class of bug invisible, so topology coverage is the control that catches it -- which is exactly what WP15 was built to provide, and it worked.

## Change log

- `2026-08-04T19:55:13.469938+00:00` — opened
- `2026-08-04T19:55:16.573686+00:00` — resolved (final_answer="amend-WP13-which-already-corrects-the-same-stale-partition-claim")
