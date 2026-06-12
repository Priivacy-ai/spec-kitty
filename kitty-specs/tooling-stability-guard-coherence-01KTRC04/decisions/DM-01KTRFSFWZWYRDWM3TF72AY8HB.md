# Decision Moment `01KTRFSFWZWYRDWM3TF72AY8HB`

- **Mission:** `01KTRC04`
- **Origin flow:** `plan`
- **Slot key:** `plan.drg.provenance-shape`
- **Input key:** `provenance_shape`
- **Status:** `resolved`
- **Created:** `2026-06-10T10:03:34.687813+00:00`
- **Resolved:** `2026-06-10T10:06:57.664007+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

FR-007: typed Provenanced[T] wrapper vs declared optional field on DRG models?

## Options

- declared-optional-field
- provenanced-wrapper

## Final answer

Provenanced[T] wrapper (operator choice): typed generic carrier holding model + provenance; provenance never pollutes the domain model. Accept the 3-layer consumer ripple — inventory getattr(node,'provenance',None) consumers first; migration is part of the AC.

## Rationale

_(none)_

## Change log

- `2026-06-10T10:03:34.687813+00:00` — opened
- `2026-06-10T10:06:57.664007+00:00` — resolved (final_answer="Provenanced[T] wrapper (operator choice): typed generic carrier holding model + provenance; provenance never pollutes the domain model. Accept the 3-layer consumer ripple — inventory getattr(node,'provenance',None) consumers first; migration is part of the AC.")
