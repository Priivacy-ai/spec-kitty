# Decision Moment `01KY1XHEH2T9RDX8ZCHCSV2VA0`

- **Mission:** `doctrine-tension-edges-01KY1WPC`
- **Origin flow:** `specify`
- **Slot key:** `specify.check.tension-under-all-active`
- **Input key:** `tension_under_all_active`
- **Status:** `resolved`
- **Created:** `2026-07-21T08:44:06.562757+00:00`
- **Resolved:** `2026-07-21T09:04:57.398575+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

consistency-check short-circuits to coherent=true when there is no explicit activation list (backward-compat all-active). Should the tension check run under implicit all-active too (making FR-011 reconciliation artefact load-bearing and SC-002 a live assertion), or only under explicit activation?

## Options

- run-under-all-active-too
- only-under-explicit-activation

## Final answer

Always on: the tension check runs regardless of explicit activation (simplifies logic, no short-circuit special-case). Consequence: the new curated default charter (tracked work; will NOT enable all doctrine elements) becomes a P0 release-blocker for this mission's release, since always-on tension checking requires a default charter that does not co-activate unreconciled tensions.

## Rationale

_(none)_

## Change log

- `2026-07-21T08:44:06.562757+00:00` — opened
- `2026-07-21T09:04:57.398575+00:00` — resolved (final_answer="Always on: the tension check runs regardless of explicit activation (simplifies logic, no short-circuit special-case). Consequence: the new curated default charter (tracked work; will NOT enable all doctrine elements) becomes a P0 release-blocker for this mission's release, since always-on tension checking requires a default charter that does not co-activate unreconciled tensions.")
