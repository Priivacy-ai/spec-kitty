# Decision Moment `01M0QDX721GV3TRCGC039K6RX7`

- **Mission:** `pre-review-gate-operator-flow-01M0Q86H`
- **Origin flow:** `plan`
- **Slot key:** `plan.architecture.scope_budget_authority`
- **Input key:** `scope_budget_authority`
- **Status:** `resolved`
- **Created:** `2026-08-23T13:45:36.065359+00:00`
- **Resolved:** `2026-08-23T13:52:07.280804+00:00`
- **Resolved by:** `user`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

What should be the canonical authority for deciding that a baseline-plus-head pre-review scope cannot fit the transition budget before execution?

## Options

- Explicit deterministic budget metadata on the canonical scope/suite definition
- Persisted historical execution timings
- No preclassification; require an operator override after a timeout

## Final answer

Explicit deterministic budget metadata on the canonical scope/suite definition

## Rationale

Use narrowly scoped, deterministic metadata owned by the interactive pre-review gate. Seed known oversized scopes from current dogfood evidence; do not mine or backfill CI history, estimate durations, or change CI scheduling.

## Change log

- `2026-08-23T13:45:36.065359+00:00` — opened
- `2026-08-23T13:52:07.280804+00:00` — resolved (final_answer="Explicit deterministic budget metadata on the canonical scope/suite definition")
