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
