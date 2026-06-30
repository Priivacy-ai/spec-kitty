# Decision Moment `01KWAMRNK3THM82XRK1FAH8J8A`

- **Mission:** `retire-standalone-tasks-cli-01KWAMQ3`
- **Origin flow:** `specify`
- **Slot key:** `specify.migration.consumer-cleanup`
- **Input key:** `consumer_migration`
- **Status:** `deferred`
- **Created:** `2026-06-29T21:32:32.227253+00:00`
- **Resolved:** `2026-06-29T21:32:40.318941+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

Should the mission add an upgrade migration to remove scripts/tasks/ + .kittify/overrides/scripts/tasks/ from already-initialized consumer projects?

## Options

- yes-add-migration
- no-repo-only
- decide-in-plan

## Final answer

_(none)_

## Rationale

User chose to decide during the plan phase after assessing how consumer projects carry these files and whether an existing migration already sweeps them.

## Change log

- `2026-06-29T21:32:32.227253+00:00` — opened
- `2026-06-29T21:32:40.318941+00:00` — deferred
