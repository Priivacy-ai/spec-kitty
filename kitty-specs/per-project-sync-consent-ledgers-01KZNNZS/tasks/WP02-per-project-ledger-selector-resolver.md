---
work_package_id: WP02
title: Per-project ledger and selector resolver
dependencies:
- WP01
requirement_refs:
- FR-003
- FR-004
- FR-005
- FR-013
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
- T010
phase: Phase 2 - Ledger isolation
history:
- timestamp: '2026-08-10T11:25:00Z'
  agent: codex
  action: Prompt generated via mission task materialization
authoritative_surface: src/
create_intent:
- tests/delivery/test_project_ledger_selection_3262.py
- tests/event_journal/test_project_scoped_journal_3262.py
execution_mode: code_change
owned_files:
- src/specify_cli/event_journal/journal.py
- src/specify_cli/event_journal/models.py
- src/specify_cli/sync/queue.py
- src/specify_cli/sync/body_queue.py
- src/specify_cli/delivery/ledger.py
- src/specify_cli/delivery/selection.py
- src/specify_cli/delivery/status_report.py
- tests/delivery/test_project_ledger_selection_3262.py
- tests/event_journal/test_project_scoped_journal_3262.py
tags: []
tracker_refs: []
---

# Work Package Prompt: WP02 – Per-project ledger and selector resolver

Introduce scoped ledger resolution for journal, offline queue, body queue, and
delivery ledger behavior. Selection, acknowledgement, purge, and status must be
keyed by the row/task project, not by the current checkout.

## Requirements

- FR-003, FR-004, FR-005, FR-013
- Plan concern: IC-02

## Acceptance

- A two-project fixture selects only the opted-in project's rows.
- Acknowledgement and purge cannot affect rows from a non-consenting project.
- Status internals can report per-project counts.
