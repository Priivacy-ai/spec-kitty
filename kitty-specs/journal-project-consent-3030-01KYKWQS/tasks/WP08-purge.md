---
work_package_id: WP08
title: Purge by project and full purge
dependencies:
- WP04
requirement_refs:
- FR-016
- FR-017
- NFR-006
planning_base_branch: feat/journal-project-consent-3030
merge_target_branch: feat/journal-project-consent-3030
branch_strategy: Planning artifacts for this mission were generated on feat/journal-project-consent-3030. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/journal-project-consent-3030 unless the human explicitly redirects the landing branch.
base_commit: 1dc38ea23ee04dbcabd5a56bb19e141163bbb497
created_at: '2026-07-28T13:54:48.701834+00:00'
subtasks:
- T022
history: []
execution_mode: code_change
tags: []
tracker_refs: []
authoritative_surface: src/specify_cli/delivery/
owned_files:
- src/specify_cli/delivery/retention.py
- src/specify_cli/sync/local_commit.py
---

# WP08 — Purge

Today there is no remediation path: `sync gc` only purges payloads delivered to **all** targets, so it
cannot clear the retained rejected rows the incident left behind.

## Spans two stores — decide and record

Journal rows **and** delivery-ledger history. The spec's "delivered, rejected and undelivered" are
**ledger** concepts, not journal columns — the journal knows only `archived_at`
(`event_journal/models.py:27`). `journal.py:5-8` states the journal "never deletes a payload on the
normal path", so destructive work routes through `delivery/retention.py`
(`_PURGE_SQL` at `:51`, `_purge_journal_rows` at `:189`, `gc_payloads` at `:150`).

**Research decision 2 must be answered inside this WP and recorded**: is ledger history for a purged
project retained or removed? It changes NFR-006's differential count.

## Definition of done

- Dry-run is the **default** and reports per-state counts while changing nothing.
- SC-006 / NFR-006: 100% of the target project's rows gone, **0%** of any other project's, measured by
  differential row counts across journal and ledger.
- `queue.remove_project_events` is not used, **and is deleted here** (C-004).

## WP12's residual frames are WP08's to purge (corrected 2026-07-30)

WP12's T027 gate records its residual-state decision as "retained-and-ignored, WP08 owns
the operator's purge path" — in `sync/local_commit.py`, in its commit message, and in its
test docstring. **That was false when written**: this WP's surface was `delivery/` only,
its scope was journal rows plus delivery-ledger history, and `sync-state.json` appeared
nowhere in it. An operator reading that decision would run WP08's purge and find pre-fix
mission slugs still sitting in `.kittify/sync-state.json` with no command that clears them.

Now true rather than aspirational: `sync/local_commit.py` is in `owned_files` and T022's
purge must clear `pending_local_commits` entries for the target project alongside the
journal and ledger rows.

Two properties this adds to T022:

- Pre-fix frames carry **no** `project_uuid` (WP12 added the field additively), so they
  cannot be matched by uuid. Purging them is `--all`-shaped, or matches on the
  `changed_files` mission slug. Decide and record which; do not leave the pre-fix
  population unpurgeable, because it is the exact set the incident produced.
- The frames are gitignored, machine-local `LOCAL_RUNTIME` state
  (`state/contract.py:169-178`), so purging them is not a git operation and needs no
  worktree coordination.

## C-004 lands here, not in WP02 (corrected 2026-07-29)

WP02 could not retire `queue.remove_project_events`; the note that it would was wrong. Its one caller is
`disable_checkout_sync` (`sync/routing.py:164`), which purges a project's pending uploads on opt-out.
Retiring it needs a replacement that purges the store that actually ships — the journal — and **that is
not expressible until WP04 lands**: `ORDERED_COLUMNS` (`event_journal/models.py:30-39`) is
`(event_id, event_type, payload, occurred_at, created_at, coalesce_key, archived_at,
drain_blocked_reason)`, with **no `project_uuid`**, so there is no column to purge by. This is why WP08
already depends on WP04.

Two consequences for this WP:

- Deleting the call also silently zeroes `SyncOptOutResult.removed_events`, which is user-visible. Either
  repoint it at the journal purge built here or change what opt-out reports — do not just drop it.
- `body_queue.remove_project_tasks` in the same function must **stay**: body uploads are a separate store
  that the daemon still drains, so that purge is live, not superseded.

Post-WP02 the legacy-queue purge is already inert for delivery (nothing drains that store), so the gap
this leaves open is retention-on-disk, not a new leak — it is C-006's collection question, escalated.
