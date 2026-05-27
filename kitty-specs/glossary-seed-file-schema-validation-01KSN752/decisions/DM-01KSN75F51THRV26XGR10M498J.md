# Decision Moment `01KSN75F51THRV26XGR10M498J`

- **Mission:** `glossary-seed-file-schema-validation-01KSN752`
- **Origin flow:** `specify`
- **Slot key:** `specify.scope.error-recovery`
- **Input key:** `error_recovery_behavior`
- **Status:** `resolved`
- **Created:** `2026-05-27T17:19:24.833994+00:00`
- **Resolved:** `2026-05-27T17:19:36.570148+00:00`
- **Other answer:** `false`

## Question

When validation catches invalid glossary data at load time, should it fail the entire scope or skip invalid terms?

## Options

- Fail entire scope with actionable error
- Skip invalid terms and load valid ones with warning
- Other

## Final answer

Fail entire scope with actionable error — no partial loads, DDD aggregate consistency

## Rationale

_(none)_

## Change log

- `2026-05-27T17:19:24.833994+00:00` — opened
- `2026-05-27T17:19:36.570148+00:00` — resolved (final_answer="Fail entire scope with actionable error — no partial loads, DDD aggregate consistency")
