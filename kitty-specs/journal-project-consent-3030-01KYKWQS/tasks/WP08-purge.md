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
- `queue.remove_project_events` is not used (C-004; WP02 retires it).
