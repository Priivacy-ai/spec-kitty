---
work_package_id: WP02
title: Remove the legacy queue-backed daemon drain
dependencies: []
requirement_refs:
- FR-012
planning_base_branch: feat/journal-project-consent-3030
merge_target_branch: feat/journal-project-consent-3030
branch_strategy: Planning artifacts for this mission were generated on feat/journal-project-consent-3030. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/journal-project-consent-3030 unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-journal-project-consent-3030-01KYKWQS
base_commit: b09ac6680ad89efcdaf0fbf029895cea7ca3394b
created_at: '2026-07-29T11:03:42.214983+00:00'
subtasks:
- T007
- T008
history: []
authoritative_surface: src/specify_cli/sync/
execution_mode: code_change
owned_files:
- src/specify_cli/sync/background.py
- src/specify_cli/sync/batch.py
- src/specify_cli/sync/queue.py
- src/specify_cli/sync/__init__.py
- tests/sync/test_background.py
- tests/sync/test_background_body.py
- tests/sync/test_body_integration.py
- tests/sync/test_issue_598_hang_fixes.py
- tests/sync/test_target_authority_wiring.py
- tests/sync/test_legacy_queue_precondition_3030.py
- tests/sync/test_no_queue_drain_constructed_3030.py
tags: []
tracker_refs: []
---

# WP02 — Remove the legacy queue drain

Research decision 1 resolved to **remove**, not enforce.

## Why removal strands nothing

`_capture_to_journal` is called at `sync/emitter.py:2057`, **before** the identity check at
`:2081-2085` and before every gate. Its own comment: *"the journal write is unconditional; the gates
only set the recorded drain_blocked_reason, never whether the durable write happens."* So every event
reaching the legacy queue — including identity-less ones that skip `_route_event` — already has a
journal copy the dispatcher can deliver. This retires the `queue.py:1-12` objection, whose stated
precondition is satisfied per `cli/commands/sync.py:2360-2367`.

## Definition of done

- `migrate_queues_to_journal` run or required first; legacy queue asserted empty; **fails loudly**
  rather than discarding — pre-WP03 rows may predate journal capture. ✅ T007 — `start()` refuses via
  `_assert_legacy_queue_converged`. Requires rather than runs the migration: `converge_legacy_runtime`
  deletes rows from the operator's source queues, which a background timer must not do unasked.
- SC-005 asserts **no code path constructs the queue-backed drain**. ✅
  `tests/sync/test_no_queue_drain_constructed_3030.py` — AST scan over `src/` plus `__all__` and the
  lazy `__getattr__` map. Both entry points are un-exported; the implementations stay in `batch.py`
  for the WP that opens that file for FR-014 (operator decision, 2026-07-29).
- ~~`queue.remove_project_events` retired per C-004.~~ **Moved to WP08.** Not achievable here: its
  caller `disable_checkout_sync` (`routing.py:164`) needs a journal-side replacement, and the journal
  has no `project_uuid` column to purge by until WP04 lands (`event_journal/models.py:30-39`).
  Deleting the call unilaterally would also zero the user-visible
  `SyncOptOutResult.removed_events`. See WP08 for the full note.


## T007's unreadable-legacy-DB decision, and its reversal (recorded 2026-07-30)

Neither the original decision nor its reversal was ever written down; a reviewer found the
reversal living only in a commit message. Recording both, because a landed contract that
changes silently is the drift this mission exists to end.

**WP02 decided (2026-07-29):** `_count_legacy_event_rows` returns `0` when
`detect_legacy_rows_for_scope` raises, on the reasoning that wedging the daemon — and with
it body uploads — on an unrelated SQLite fault is worse than starting. That reasoning was
wrong, and it was the fail-open shape this same WP criticised elsewhere in the same file.

**Reversed (2026-07-30, commits `07a5d10b69` / `aba6312fbe`, H8):** an unreadable legacy DB
now refuses. The decisive fact is that `sync/queue.py:918-921` returns an empty
`LegacyRowCounts()` when the DB is merely **absent**, so an exception can only mean *the
file exists and could not be read* — precisely the state where stranded undeliverable rows
cannot be ruled out. "Unrelated fault" never fit that fault, and the guard's safe default
was permission, which is FR-003's failure mode.

The reversal is deliberately narrow: a credentials/scope read failure still falls back to
`""` and does **not** refuse (pinned by `test_a_credentials_read_failure_is_not_evidence`),
and the swallowed set is `(sqlite3.Error, OSError, ValueError)` so a `TypeError` from a
changed arity propagates instead of degrading to "clean" — the fake-green that WP02's own
anchor test caught once already.
