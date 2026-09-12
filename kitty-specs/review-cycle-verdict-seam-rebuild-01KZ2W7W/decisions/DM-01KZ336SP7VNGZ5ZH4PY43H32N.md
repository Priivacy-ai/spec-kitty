# Decision Moment `01KZ336SP7VNGZ5ZH4PY43H32N`

- **Mission:** `review-cycle-verdict-seam-rebuild-01KZ2W7W`
- **Origin flow:** `plan`
- **Slot key:** `plan.authority.override-vocabulary`
- **Input key:** `override_vocabulary`
- **Status:** `resolved`
- **Created:** `2026-08-03T05:58:05.255159+00:00`
- **Resolved:** `2026-08-03T06:29:49.413057+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

How should the authoritative verdict express an arbiter override, and what happens to already-persisted events that recorded an override as approved?

## Options

_(none)_

## Final answer

Add an override flag alongside the verdict on ReviewResult, rather than widening the verdict vocabulary. No event backfill; the log stays append-only. Noted tension: two fields must be read together, which is structurally the shape that produced the existing multi-representation override problem, so the pairing must be encapsulated behind one accessor rather than read field-by-field at each consumer.

## Rationale

_(none)_

## Change log

- `2026-08-03T05:58:05.255159+00:00` — opened
- `2026-08-03T06:29:49.413057+00:00` — resolved (final_answer="Add an override flag alongside the verdict on ReviewResult, rather than widening the verdict vocabulary. No event backfill; the log stays append-only. Noted tension: two fields must be read together, which is structurally the shape that produced the existing multi-representation override problem, so the pairing must be encapsulated behind one accessor rather than read field-by-field at each consumer.")
