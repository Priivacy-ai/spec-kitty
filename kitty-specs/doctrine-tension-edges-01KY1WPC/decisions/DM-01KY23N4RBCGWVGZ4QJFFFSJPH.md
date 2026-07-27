# Decision Moment `01KY23N4RBCGWVGZ4QJFFFSJPH`

- **Mission:** `doctrine-tension-edges-01KY1WPC`
- **Origin flow:** `plan`
- **Slot key:** `plan.process.bulk-edit-classification`
- **Input key:** `bulk_edit_classification`
- **Status:** `resolved`
- **Created:** `2026-07-21T10:30:59.083254+00:00`
- **Resolved:** `2026-07-21T10:34:22.272955+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

C-007: removing opposed_by/Contradiction touches 21 sites across src/docs/tests. Should this mission run under change_mode: bulk_edit (triggering the occurrence-classification skill + occurrence_map.yaml before implement can start WP01), or does the operator record this as an exempt pure-removal?

## Options

- Run under change_mode: bulk_edit - produce occurrence_map.yaml at plan time (default per C-007)
- Exempt as pure-removal - no occurrence_map.yaml required

## Final answer

Run under change_mode: bulk_edit per C-007 default. Produce occurrence_map.yaml at plan time via the spec-kitty-bulk-edit-classification skill, covering all 8 standard categories for the opposed_by/Contradiction removal (21 sites).

## Rationale

_(none)_

## Change log

- `2026-07-21T10:30:59.083254+00:00` — opened
- `2026-07-21T10:34:22.272955+00:00` — resolved (final_answer="Run under change_mode: bulk_edit per C-007 default. Produce occurrence_map.yaml at plan time via the spec-kitty-bulk-edit-classification skill, covering all 8 standard categories for the opposed_by/Contradiction removal (21 sites).")
