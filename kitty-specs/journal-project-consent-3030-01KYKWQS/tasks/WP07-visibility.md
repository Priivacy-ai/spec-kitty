---
work_package_id: WP07
title: 'Operator visibility per project (folds #3004)'
dependencies:
- WP04
requirement_refs:
- FR-011
- FR-015
- NFR-007
planning_base_branch: feat/journal-project-consent-3030
merge_target_branch: feat/journal-project-consent-3030
branch_strategy: Planning artifacts for this mission were generated on feat/journal-project-consent-3030. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/journal-project-consent-3030 unless the human explicitly redirects the landing branch.
base_commit: 1dc38ea23ee04dbcabd5a56bb19e141163bbb497
created_at: '2026-07-28T13:54:48.701834+00:00'
subtasks:
- T020
- T021
history: []
execution_mode: code_change
tags: []
tracker_refs: []
authoritative_surface: src/specify_cli/
owned_files:
- src/specify_cli/cli/commands/sync.py
- tests/delivery/test_per_project_report_3030.py
- tests/cli/commands/test_sync_commands.py
- src/specify_cli/delivery/status_report.py
- src/specify_cli/sync/migrate_journal.py
---

# WP07 — Operator visibility (folds #3004)

`sync doctor` reported `Server: Connected` and a healthy queue throughout the incident; the
contamination was found only by hand-querying journal payloads and grouping by `project_slug`.

## #3004 is a prerequisite, not an incidental

`doctor`'s queue-health block reads `OfflineQueue().get_queue_stats()` (`cli/commands/sync.py:3619-3627`)
and `diagnose` reads `OfflineQueue()` (`:3531-3534`) — **both empty after `sync migrate`**, which is
precisely why doctor read healthy. A per-project report rendered from that store would pass CI and lie
in the field: the same fake-green shape as the original incident. Reconcile against the journal's
retained count (`_count_retained_events`, `cli/commands/sync.py:714-717`).

## Must render

- Per project: event count, oldest-event age, consent state.
- **Unresolved-identity** events (count from WP04's T013) as their own row — fail-closed denial must be
  visible, not silent data loss.
- **`unresolved`-consent** rows from WP05's T016, so reported state matches enforced state.
- `sync migrate`'s per-project composition of what it moved.

## Definition of done

- SC-004: zero hand-written SQLite queries needed to answer "whose data is in here?"
- Totals reconcile exactly against the journal retained count.
