# Decision Moment `01M1VRM6HN09R2NX6C4A3YJZ5E`

- **Mission:** `dead-port-disposition-01M1VRA2`
- **Origin flow:** `specify`
- **Slot key:** `specify.compat.transitional-alias`
- **Input key:** `transitional_alias_policy`
- **Status:** `resolved`
- **Created:** `2026-09-06T16:25:34.522658+00:00`
- **Resolved:** `2026-09-06T16:26:55.564524+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

The ADR says the promoted constructor is named for_mission, with for_feature kept only as a transitional alias if the two bridge construction sites cannot be renamed in the same change. Should this mission rename cleanly with no alias, or ship a deprecated for_feature alias with a removal note?

## Options

- Clean rename, no alias
- Ship a deprecated for_feature alias
- Other

## Final answer

Clean rename, no alias

## Rationale

_(none)_

## Change log

- `2026-09-06T16:25:34.522658+00:00` — opened
- `2026-09-06T16:26:55.564524+00:00` — resolved (final_answer="Clean rename, no alias")
