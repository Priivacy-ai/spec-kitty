# Decision Moment `01KZ336RG98TK7P3BXQ2J1W98Q`

- **Mission:** `review-cycle-verdict-seam-rebuild-01KZ2W7W`
- **Origin flow:** `plan`
- **Slot key:** `plan.migration.retired-path-trigger`
- **Input key:** `retired_path_trigger`
- **Status:** `resolved`
- **Created:** `2026-08-03T05:58:04.041277+00:00`
- **Resolved:** `2026-08-03T06:29:48.263090+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

What triggers FR-008's reconciliation of verdict records under retired resolver paths, and are cross-branch coord records in scope?

## Options

_(none)_

## Final answer

Operator-invoked repair command. A doctor-style subcommand detects records under retired resolver paths and reports, with an opt-in fix. Chosen over read-time (no permanent read cost) and over an upgrade migration (no dependency on the operator upgrading). Safest for coord topology because the operator controls when branches are materialized. Accepted cost: nothing reconciles unless someone runs it.

## Rationale

_(none)_

## Change log

- `2026-08-03T05:58:04.041277+00:00` — opened
- `2026-08-03T06:29:48.263090+00:00` — resolved (final_answer="Operator-invoked repair command. A doctor-style subcommand detects records under retired resolver paths and reports, with an opt-in fix. Chosen over read-time (no permanent read cost) and over an upgrade migration (no dependency on the operator upgrading). Safest for coord topology because the operator controls when branches are materialized. Accepted cost: nothing reconciles unless someone runs it.")
