# Decision Moment `01KTSJEQANMNEV16WMSAJP6FR1`

- **Mission:** `do-dispatch-open-op-lifecycle-01KTSJ2H`
- **Origin flow:** `plan`
- **Slot key:** `plan.schema.saas-envelope-compat`
- **Input key:** `saas_envelope_compat`
- **Status:** `resolved`
- **Created:** `2026-06-10T20:09:22.005618+00:00`
- **Resolved:** `2026-06-10T20:10:39.313704+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

Must the new started/completed Op event schema remain wire-compatible with the existing SaaS propagation envelope (OpStarted/OpCompleted, handlers pending in #1720), or may the envelope change shape with this mission?

## Options

- Keep envelope wire-compatible
- Change envelope freely (SaaS handlers not yet implemented)
- Other

## Final answer

Change envelope freely: CLI behavior gets locked first; SaaS handlers are unimplemented (#1720/#1693) so no wire-compat shim — SaaS adopts the new shape later.

## Rationale

_(none)_

## Change log

- `2026-06-10T20:09:22.005618+00:00` — opened
- `2026-06-10T20:10:39.313704+00:00` — resolved (final_answer="Change envelope freely: CLI behavior gets locked first; SaaS handlers are unimplemented (#1720/#1693) so no wire-compat shim — SaaS adopts the new shape later.")
