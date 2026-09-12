# Decision Moment `01M0Q8941RVMHQX32A3H6ZQXCG`

- **Mission:** `pre-review-gate-operator-flow-01M0Q86H`
- **Origin flow:** `specify`
- **Slot key:** `specify.review_submission.gate_execution_policy`
- **Input key:** `gate_execution_policy`
- **Status:** `resolved`
- **Created:** `2026-08-23T12:07:14.744591+00:00`
- **Resolved:** `2026-08-23T12:28:45.068589+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

When an operator moves a work package to for_review, what must the pre-review gate do by default?

## Options

- Remain mandatory and atomic, but stream progress and fail without changing lane state
- Move to for_review immediately and run the gate asynchronously
- Remain mandatory and atomic with an explicit skip flag for authorized callers
- Other

## Final answer

Remain mandatory and atomic by default, with an explicit, visible skip flag for authorized callers; defer asynchronous redesign.

## Rationale

_(none)_

## Change log

- `2026-08-23T12:07:14.744591+00:00` — opened
- `2026-08-23T12:28:45.068589+00:00` — resolved (final_answer="Remain mandatory and atomic by default, with an explicit, visible skip flag for authorized callers; defer asynchronous redesign.")
