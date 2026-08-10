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

## Implementation evidence — 2026-08-10

Current origin HEAD already implements the WP02 selector/ledger invariant across
the #3030 surfaces:

- `src/specify_cli/event_journal/journal.py::read_identity_projection()` requires
  a non-empty `project_uuids` filter and returns no rows for an empty filter.
- `src/specify_cli/delivery/selection.py::select_consented()` resolves consent
  over distinct project UUIDs, then reads the identity projection filtered to the
  consented UUIDs before selecting event IDs.
- `src/specify_cli/delivery/consent_gate.py` requires `ConsentedBatch` /
  `ConsentAnswer` before ordinary delivery.
- `src/specify_cli/delivery/status_report.py` exposes `per_project_store` status
  and unresolved identity counts.

Focused validation:

```bash
SPEC_KITTY_NO_UPGRADE_CHECK=1 env -u SPEC_KITTY_ENABLE_SAAS_SYNC \
  uv run --group dev --extra test pytest \
  tests/delivery/test_incident_reproduction_3030.py \
  tests/delivery/test_consented_batch_3030.py \
  tests/delivery/test_dispatch_project_consent_3030.py \
  tests/delivery/test_nfr003_predicate_cost_3030.py \
  tests/delivery/test_purge_all_events_3030.py \
  tests/event_journal/test_identity_migration_3030.py \
  tests/architectural/test_unfiltered_journal_read_boundary.py -q
```

Result: `56 passed in 72.86s`.
