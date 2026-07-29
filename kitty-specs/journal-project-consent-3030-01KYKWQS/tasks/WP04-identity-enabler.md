---
work_package_id: WP04
title: 'Journal identity enabler: migration, columns, backfill'
dependencies: []
requirement_refs:
- FR-006
- FR-009
- FR-011
- NFR-004
- NFR-005
planning_base_branch: feat/journal-project-consent-3030
merge_target_branch: feat/journal-project-consent-3030
branch_strategy: Planning artifacts for this mission were generated on feat/journal-project-consent-3030. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/journal-project-consent-3030 unless the human explicitly redirects the landing branch.
base_commit: 1dc38ea23ee04dbcabd5a56bb19e141163bbb497
created_at: '2026-07-28T13:54:16.365774+00:00'
subtasks:
- T001
- T006
- T010
- T011
- T012
- T013
history: []
execution_mode: code_change
tags: []
tracker_refs: []
authoritative_surface: src/specify_cli/
owned_files:
- src/specify_cli/event_journal/journal.py
- src/specify_cli/event_journal/models.py
- src/specify_cli/sync/project_identity.py
- src/specify_cli/sync/emitter.py
---

# WP04 — Journal identity enabler

## T010 is a hard prerequisite for T012

**The journal has no schema-migration mechanism.** `_ensure_schema` (`event_journal/journal.py:209-214`)
runs only `CREATE_TABLE_SQL` plus two `CREATE INDEX IF NOT EXISTS` — no `ALTER`, no
`PRAGMA user_version`, no `table_info` probe. And `INSERT_SQL`, `SELECT_ALL_SQL`, `SELECT_BY_ID_SQL`
and `SELECT_BLOCKED_SQL` are **all** derived from `_COLUMN_LIST` (`event_journal/models.py:41,77-80`).

Adding columns to `ORDERED_COLUMNS` without an ALTER step therefore raises
`no such column: project_uuid` on **every existing journal file**, breaking `sync status`, `sync now`
and the backfill itself. `CREATE TABLE IF NOT EXISTS` is a no-op on an existing table.

Reuse the in-repo precedent: `sync/queue.py:1242-1248` does `PRAGMA table_info(queue)` →
`ALTER TABLE queue ADD COLUMN coalesce_key TEXT`. The migration runs **inside `_ensure_schema`** so it
is unconditional on construction and `get_journal`'s cache cannot skip it, is idempotent, and precedes
any use of the derived SQL constants.

## T011 — one resolver, four sites

Identity has a **fourth** site the canonical chain misses: `_enrich_proof_subject` writes
`payload["subject"]["project_uuid"]` (`sync/emitter.py:2037`), which
`_resolve_event_or_payload`'s chain (`namespace.project_uuid` → top-level → `payload.project_uuid`,
`sync/queue.py:1714-1720`) never inspects; `envelope_fields` can also overwrite the top-level value
(`emitter.py:2048-2049`). The canonical implementation is **module-private to `sync/queue.py`**, which
`delivery/dispatcher.py:34` may not import. Promote it to `sync/project_identity.py` (today a 29-line
re-export shim) as one ordered constant list, with a fixture per site and a test asserting a single
definition site. The nil sentinel `00000000-0000-0000-0000-000000000000` (`emitter.py:2150`) normalizes
to NULL at write and backfill so it is never groupable or consentable.

## Definition of done

- A test opens a **pre-migration** journal DB file and reads it successfully.
- SC-007: backfill twice over a 10k-row multi-project journal → byte-identical values, unchanged count.
- Columns are additive and nullable (C-001); nothing is deleted (C-002).
- Tests assert on the public seam, not SQL or private helpers.
