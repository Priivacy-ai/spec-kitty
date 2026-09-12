# Decision Moment `01M0QEA9SMC7GG1PC0DNAR71HR`

- **Mission:** `pre-review-gate-operator-flow-01M0Q86H`
- **Origin flow:** `plan`
- **Slot key:** `plan.architecture.unknown_scope_policy`
- **Input key:** `unknown_scope_policy`
- **Status:** `resolved`
- **Created:** `2026-08-23T13:52:44.852123+00:00`
- **Resolved:** `2026-08-23T13:54:16.462764+00:00`
- **Resolved by:** `user`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

How should the pre-review gate handle a custom or newly derived scope that has no deterministic budget classification?

## Options

- Preserve compatibility: warn that budget is unknown, then run under the existing timeout
- Fail closed and require a bounded scope or explicit skip
- Treat every unclassified scope as oversized and refuse it

## Final answer

Preserve compatibility: warn that budget is unknown, then run under the existing timeout

## Rationale

Only explicitly classified oversized scopes refuse promptly. New and custom scopes retain current behavior under the existing timeout, with a visible unknown-budget warning, avoiding a 3.2.6 allowlist migration.

## Change log

- `2026-08-23T13:52:44.852123+00:00` — opened
- `2026-08-23T13:54:16.462764+00:00` — resolved (final_answer="Preserve compatibility: warn that budget is unknown, then run under the existing timeout")
