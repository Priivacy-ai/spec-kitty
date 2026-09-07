# Decision Moment `01M1V8HVDQH36X06JDK22SZV02`

- **Mission:** `fsm-write-path-integrity-01M1TZV6`
- **Origin flow:** `plan`
- **Slot key:** `plan.guard.readiness-polarity`
- **Input key:** `guard_none_polarity`
- **Status:** `resolved`
- **Created:** `2026-09-06T11:44:40.375308+00:00`
- **Resolved:** `2026-09-06T11:48:31.788997+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

Q8: Confirm dependency-readiness guard polarity: fail-OPEN on None (C-004) vs update both probe sites and go fail-closed?

## Options

- Fail-open on None (default)
- Fail-closed; update probe sites
- Other

## Final answer

Fail-OPEN on None confirmed (C-004). Why: the two live probe sites (lanes/recovery.py:78 crash-recovery progression probe; agent/tasks_transition_core.py:337 FR-015 force-free backward-edge probe) call validate_transition with self-built contexts and would be silently killed by fail-closed. Sound because after WP03 no durable write bypasses the shells, which are the verdict supplier (FR-013). Do NOT copy subtasks_complete's fail-closed polarity.

## Rationale

_(none)_

## Change log

- `2026-09-06T11:44:40.375308+00:00` — opened
- `2026-09-06T11:48:31.788997+00:00` — resolved (final_answer="Fail-OPEN on None confirmed (C-004). Why: the two live probe sites (lanes/recovery.py:78 crash-recovery progression probe; agent/tasks_transition_core.py:337 FR-015 force-free backward-edge probe) call validate_transition with self-built contexts and would be silently killed by fail-closed. Sound because after WP03 no durable write bypasses the shells, which are the verdict supplier (FR-013). Do NOT copy subtasks_complete's fail-closed polarity.")
