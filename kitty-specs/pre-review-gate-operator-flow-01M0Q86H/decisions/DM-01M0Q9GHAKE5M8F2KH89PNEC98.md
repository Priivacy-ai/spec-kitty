# Decision Moment `01M0Q9GHAKE5M8F2KH89PNEC98`

- **Mission:** `pre-review-gate-operator-flow-01M0Q86H`
- **Origin flow:** `specify`
- **Slot key:** `specify.review_submission.regression_severity`
- **Input key:** `regression_severity`
- **Status:** `resolved`
- **Created:** `2026-08-23T12:28:46.291365+00:00`
- **Resolved:** `2026-08-23T13:21:02.065981+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

When the gate completes and detects new test regressions, should that verdict block the for_review transition by default?

## Options

- Preserve current policy: warn by default and block only when configured
- Block by default unless explicitly bypassed
- Use severity-based blocking
- Other

## Final answer

Preserve the current policy: newly detected test regressions warn by default and block only when the project explicitly enables blocking.

## Rationale

_(none)_

## Change log

- `2026-08-23T12:28:46.291365+00:00` — opened
- `2026-08-23T13:21:02.065981+00:00` — resolved (final_answer="Preserve the current policy: newly detected test regressions warn by default and block only when the project explicitly enables blocking.")
