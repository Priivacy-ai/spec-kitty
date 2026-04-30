# Decision Moment `01KQEKE49R94BGW4Q4X08KY8PD`

- **Mission:** `auth-tranche-2-5-cli-contract-consumption-01KQEJZK`
- **Origin flow:** `plan`
- **Slot key:** `plan.data_model.generation_field`
- **Input key:** `generation_field_storage`
- **Status:** `resolved`
- **Created:** `2026-04-30T07:07:46.873004+00:00`
- **Resolved:** `2026-04-30T07:11:18.521607+00:00`
- **Other answer:** `false`

## Question

Should the new generation field from the Tranche 2 refresh response be stored?

## Options

- Add generation: int | None to StoredSession
- Capture in response dataclass only
- Ignore in Tranche 2.5

## Final answer

Add generation: int | None to StoredSession

## Rationale

_(none)_

## Change log

- `2026-04-30T07:07:46.873004+00:00` — opened
- `2026-04-30T07:11:18.521607+00:00` — resolved (final_answer="Add generation: int | None to StoredSession")
