# Decision Moment `01KWANGYM89NRT5KNAHVGX8BF5`

- **Mission:** `retire-standalone-tasks-cli-01KWAMQ3`
- **Origin flow:** `plan`
- **Slot key:** `plan.migration.consumer-cleanup`
- **Input key:** `consumer_migration_resolved`
- **Status:** `resolved`
- **Created:** `2026-06-29T21:45:47.912838+00:00`
- **Resolved:** `2026-06-29T21:45:49.086317+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

Does retiring the standalone tasks CLI require a new consumer-project upgrade migration?

## Options

- no-migration-needed
- add-migration

## Final answer

No new migration needed. The standalone tasks CLI is not deployed to consumer projects (absent from init/upgrade templates and release packaging). The only historical consumer-side path, .kittify/scripts/tasks/, is already removed on upgrade by the existing m_0_10_0_python_only migration (_remove_tasks_helpers). The packaged src/specify_cli/scripts/tasks/ leaves the wheel automatically on deletion; scripts/tasks/ and .kittify/overrides/scripts/tasks/ are spec-kitty-repo-only dev/snapshot artifacts.

## Rationale

_(none)_

## Change log

- `2026-06-29T21:45:47.912838+00:00` — opened
- `2026-06-29T21:45:49.086317+00:00` — resolved (final_answer="No new migration needed. The standalone tasks CLI is not deployed to consumer projects (absent from init/upgrade templates and release packaging). The only historical consumer-side path, .kittify/scripts/tasks/, is already removed on upgrade by the existing m_0_10_0_python_only migration (_remove_tasks_helpers). The packaged src/specify_cli/scripts/tasks/ leaves the wheel automatically on deletion; scripts/tasks/ and .kittify/overrides/scripts/tasks/ are spec-kitty-repo-only dev/snapshot artifacts.")
