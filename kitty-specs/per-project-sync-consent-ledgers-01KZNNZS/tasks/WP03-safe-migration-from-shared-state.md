---
work_package_id: WP03
title: Safe migration from shared state
dependencies:
- WP02
requirement_refs:
- FR-010
- FR-011
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
phase: Phase 3 - Migration
history:
- timestamp: '2026-08-10T11:25:00Z'
  agent: codex
  action: Prompt generated via mission task materialization
authoritative_surface: src/
create_intent:
- tests/sync/test_project_ledger_migration_3262.py
- tests/event_journal/test_legacy_project_classification_3262.py
execution_mode: code_change
owned_files:
- src/specify_cli/sync/migrate_journal.py
- tests/sync/test_project_ledger_migration_3262.py
- tests/event_journal/test_legacy_project_classification_3262.py
tags: []
tracker_refs: []
---

# Work Package Prompt: WP03 – Safe migration from shared state

Migrate legacy shared journal/offline/body state into scoped ledgers or scoped
resolver metadata without destructive purge and without silently admitting
ambiguous historical data.

## Requirements

- FR-010, FR-011
- Plan concern: IC-03

## Acceptance

- Isolated fixture databases cover mixed legacy rows and body uploads.
- Ambiguous rows remain local-only/refused until ownership is proven.
- Migration is idempotent and records imported/refused/ambiguous/unchanged counts.

## Implementation evidence — 2026-08-10

Current origin HEAD already implements the migration/backfill invariants relevant
to WP03:

- `src/specify_cli/sync/migrate_journal.py` discovers legacy and scoped queue DBs,
  imports currently queued payloads into the event journal, records provenance,
  quarantines divergent duplicates, and keeps source DBs untouched until the
  explicit cleanup path.
- `sync migrate` backfills identity onto pre-mission journal rows and leaves
  genuinely unresolvable rows with `project_uuid IS NULL`, which keeps them
  unselectable/fail-closed.
- Plain migration does not silently write consent records; consent-index backfill
  remains behind the explicit flag.

Focused validation:

```bash
SPEC_KITTY_NO_UPGRADE_CHECK=1 env -u SPEC_KITTY_ENABLE_SAAS_SYNC \
  uv run --group dev --extra test pytest \
  tests/sync/test_migrate_journal.py \
  tests/cli/commands/test_sync_migrate_backfills_h4.py \
  tests/sync/test_journal_identity_backfill_3030.py \
  tests/event_journal/test_identity_migration_3030.py -q
```

Result: `60 passed in 49.77s`.
