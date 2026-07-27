# Decision Moment `01KQFAPRVNBB7V1QWN1E4C2VJ7`

- **Mission:** `charter-p7-release-closure-01KQF9B9`
- **Origin flow:** `plan`
- **Slot key:** `plan.json-contract.synthesis-state-shape`
- **Input key:** `synthesis_state_json_shape`
- **Status:** `resolved`
- **Created:** `2026-04-30T13:54:27.317853+00:00`
- **Resolved:** `2026-04-30T13:54:31.384843+00:00`
- **Other answer:** `false`

## Question

How should synthesis-state validation results appear in the charter bundle validate --json output?

## Options

- Nested synthesis_state key only
- Nested synthesis_state key + mirror errors into top-level errors list
- Flat merge into top-level errors list only

## Final answer

Nested synthesis_state key + mirror errors into top-level errors list

## Rationale

_(none)_

## Change log

- `2026-04-30T13:54:27.317853+00:00` — opened
- `2026-04-30T13:54:31.384843+00:00` — resolved (final_answer="Nested synthesis_state key + mirror errors into top-level errors list")
