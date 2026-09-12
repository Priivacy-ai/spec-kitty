# Decision Moment `01KZ6JE62Q6CQ24DMBX8KZZ5R9`

- **Mission:** `review-cycle-verdict-seam-rebuild-01KZ2W7W`
- **Origin flow:** `plan`
- **Slot key:** `wp11_t048_ownership_widening`
- **Input key:** `wp11_t048_ownership_widening`
- **Status:** `resolved`
- **Created:** `2026-08-04T14:21:59.255847+00:00`
- **Resolved:** `2026-08-04T14:22:18.380058+00:00`
- **Resolved by:** `Stijn Dejongh (operator)`
- **Opened by:** `claude-opus-5`
- **Other answer:** `false`

## Question

WP11/T048 (the FR-002 revert-compensator) cannot be built inside WP11's owned files. _do_move_task in tasks_move_task.py calls _mt_finalize_plan (verdict write+commit) then _mt_execute (transition emit) sequentially, so the compensator must hook that sequence; the --json durability key is blocked the same way because _mt_output and _MoveTaskState's field list also live there. tasks_move_task.py is owned by WP06 ALONE, which is already approved and closed, so the mission's FR-002 deliverable has no landing site. How should this be routed?

## Options

- widen-WP11-owned_files-to-include-tasks_move_task.py
- author-a-new-WP-as-was-done-for-T017
- defer-T048-to-WP13-consumer-unification

## Final answer

widen-WP11-owned_files-to-include-tasks_move_task.py

## Rationale

OPERATOR-CONFIRMED ('wp11, agreed'). Chosen over authoring a new WP (heavier, and T048 is squarely WP11's own requirement) and over deferring to WP13 (lands FR-002 late and conflates it with consumer unification). Legality: WP11 already declares WP06 as a dependency, so WP06/WP11 co-ownership of tasks_move_task.py is dependency-ORDERED, which is what validate_no_overlap requires -- the gate refuses only dependency-UNORDERED overlap. Confirmed by finalize-tasks --validate-only both before the edit (as a reverted trial) and after: 18 WPs validated, 0 would be modified. Scope of the widening is strictly T048's revert-compensator plus threading the already-computed VerdictDurabilitySignal into _mt_output's result dict; it is NOT license to refactor tasks_move_task.py generally, and WP12/WP13 retain their own later claims on that area. Note WP06 is already approved and closed, so this is a co-ownership grant over a completed WP's file rather than a live contention. Binding constraint carried forward: emit-first ordering remains forbidden -- the fix is a revert-compensator, not a reordering. Same deadlock class as WP04's T017 (which produced WP18) and WP18's own missing test home; three instances now, suggesting the planning-time ownership assignment did not model cross-module compensators or generated/pinned-gate surfaces.

## Change log

- `2026-08-04T14:21:59.255847+00:00` — opened
- `2026-08-04T14:22:18.380058+00:00` — resolved (final_answer="widen-WP11-owned_files-to-include-tasks_move_task.py")
