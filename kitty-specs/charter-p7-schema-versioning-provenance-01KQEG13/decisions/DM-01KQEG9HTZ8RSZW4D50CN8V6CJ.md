# Decision Moment `01KQEG9HTZ8RSZW4D50CN8V6CJ`

- **Mission:** `charter-p7-schema-versioning-provenance-01KQEG13`
- **Origin flow:** `plan`
- **Slot key:** `plan.architecture.bundle-migration-trigger`
- **Input key:** `bundle_migration_trigger`
- **Status:** `resolved`
- **Created:** `2026-04-30T06:12:51.167626+00:00`
- **Resolved:** `2026-04-30T06:15:05.121384+00:00`
- **Other answer:** `false`

## Question

When the CLI encounters a charter bundle whose integer schema_version is outside the supported range, how should migration work?

## Options

- auto-migrate on spec-kitty upgrade (same pattern as project schema_version migrations)
- block with error and add spec-kitty charter migrate-bundle command
- block with error on any charter subcommand that touches the bundle, migration via spec-kitty upgrade

## Final answer

Option C: Block with error on any charter subcommand that reads the bundle; spec-kitty upgrade applies the registered migration in-place. No new migrate-bundle command. Tests cover both the reader block and the upgrade migration path.

## Rationale

_(none)_

## Change log

- `2026-04-30T06:12:51.167626+00:00` — opened
- `2026-04-30T06:15:05.121384+00:00` — resolved (final_answer="Option C: Block with error on any charter subcommand that reads the bundle; spec-kitty upgrade applies the registered migration in-place. No new migrate-bundle command. Tests cover both the reader block and the upgrade migration path.")
