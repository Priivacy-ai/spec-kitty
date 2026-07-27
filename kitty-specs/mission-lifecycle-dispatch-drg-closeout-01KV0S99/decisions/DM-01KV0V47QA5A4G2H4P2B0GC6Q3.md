# Decision Moment `01KV0V47QA5A4G2H4P2B0GC6Q3`

- **Mission:** `mission-lifecycle-dispatch-drg-closeout-01KV0S99`
- **Origin flow:** `plan`
- **Slot key:** `plan.architecture.post-mission-lifecycle-surface`
- **Input key:** `post_mission_lifecycle_surface`
- **Status:** `resolved`
- **Created:** `2026-06-13T15:55:36.554944+00:00`
- **Resolved:** `2026-06-13T16:05:21.309990+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

How should the #1802 post-mission lifecycle surface (follow-up recording + mission re-open) be modeled?

## Options

- Extend FSM + lifecycle events
- Linked-artifact + new residual mission
- Follow-up only; split re-open to child

## Final answer

Extend FSM + events: add MissionReopened/FollowUpRecorded events to the canonical status event log; mission reopen = recorded, reversible force-transition out of terminal done/merged to an actionable lane (force+evidence); mission follow-up links commit/PR to original mission_id. Reuses status FSM, reducer, meta.json identity.

## Rationale

_(none)_

## Change log

- `2026-06-13T15:55:36.554944+00:00` — opened
- `2026-06-13T16:05:21.309990+00:00` — resolved (final_answer="Extend FSM + events: add MissionReopened/FollowUpRecorded events to the canonical status event log; mission reopen = recorded, reversible force-transition out of terminal done/merged to an actionable lane (force+evidence); mission follow-up links commit/PR to original mission_id. Reuses status FSM, reducer, meta.json identity.")
