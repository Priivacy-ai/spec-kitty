# Decision Moment `01KTH03GKJ2PEWCRGGECXVZ2CM`

- **Mission:** `wp-lane-state-machine-fsm-01KTGZAZ`
- **Origin flow:** `plan`
- **Slot key:** `plan.architecture.guard-force-ownership`
- **Input key:** `guard_force_ownership`
- **Status:** `resolved`
- **Created:** `2026-06-07T12:14:44.850542+00:00`
- **Resolved:** `2026-06-07T12:16:31.356611+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

How fully should the WPState objects own transition guards and force-override (the 'full wiring' boundary)?

## Options

- Full ownership: guards+force move into the State objects; validate_transition becomes a thin delegator
- FSM owns edges+force; rich guards stay in validate_transition as a composed layer
- Other

## Final answer

Full ownership: guards + force-override move into the WPState objects; validate_transition becomes a thin delegator to the FSM. Behavior preserved, pinned by tests.

## Rationale

_(none)_

## Change log

- `2026-06-07T12:14:44.850542+00:00` — opened
- `2026-06-07T12:16:31.356611+00:00` — resolved (final_answer="Full ownership: guards + force-override move into the WPState objects; validate_transition becomes a thin delegator to the FSM. Behavior preserved, pinned by tests.")
