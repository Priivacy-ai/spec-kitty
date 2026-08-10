---
work_package_id: WP10
title: WAL-aware layout migration, quarantine, and atomic cutover
dependencies:
- WP04
- WP07
requirement_refs:
- FR-012
- FR-013
- FR-014
- FR-015
- FR-017
- FR-023
- FR-024
- FR-029
- NFR-002
- NFR-005
- NFR-007
- C-001
- C-006
- C-007
- C-008
planning_base_branch: feat/per-project-sync-consent
merge_target_branch: feat/per-project-sync-consent
branch_strategy: Planning artifacts for this mission were generated on feat/per-project-sync-consent. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/per-project-sync-consent unless the human explicitly redirects the landing branch.
subtasks:
- T044
- T045
- T046
- T047
- T048
history:
- at: '2026-08-09T17:05:36Z'
  actor: planner
  action: Created by /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/sync/project_store_migration.py
create_intent:
- src/specify_cli/sync/project_store_migration.py
- src/specify_cli/sync/daemon_protocol.py
- tests/sync/test_project_store_migration.py
- tests/sync/test_daemon_cutover_protocol.py
- tests/sync/test_migration_writer_barrier.py
- tests/cli/commands/test_sync_project_store_commands.py
execution_mode: code_change
owned_files:
- src/specify_cli/sync/project_store_migration.py
- src/specify_cli/sync/daemon_protocol.py
- src/specify_cli/sync/migrate_journal.py
- src/specify_cli/cli/commands/sync.py
- tests/sync/test_project_store_migration.py
- tests/sync/test_daemon_cutover_protocol.py
- tests/sync/test_migration_writer_barrier.py
- tests/cli/commands/test_sync_project_store_commands.py
- tests/sync/test_migrate_journal.py
- tests/event_journal/test_identity_migration_3030.py
- tests/delivery/test_purge_all_body_uploads_3030.py
role: implementer
tags: []
tracker_refs:
- Priivacy-ai/spec-kitty#3262
- Priivacy-ai/spec-kitty#3030
---

## ⚡ Do This First: Load Agent Profile

```text
/ad-hoc-profile-load python-pedro
```

Read User Story 4, research Decision 8, both contracts, WP01's complete
current-writer census, and merged WP02–WP04 APIs. Read every owned legacy
migration/CLI path before editing. This WP consumes the layout authority and
already-converted writers; it does not create a rival authority or edit writers.

## Objective

Partition legacy shared journal, delivery, event queue, and body/offline state
into UUID-owned stores without source mutation or manufactured consent. Use a
read-only WAL-aware logical snapshot, exact verification, staged publication,
WP02 layout-generation cutover, recognized-daemon quiesce/restart, and one atomic
exclusive cutover. Unknown identity remains non-deliverable quarantine; late
old-binary writes are diagnosed residue and never dual-read.

## Subtask T044 — WAL-aware inventory and verification

Use strict read-only/immutable opening or SQLite backup semantics that include
committed WAL content and record main/WAL/SHM treatment. Inventory source schema,
exact row IDs/statuses/attempts/targets/timestamps/counts and content hashes in a
MigrationManifest. Never invoke a schema-mutating constructor on a source.

Locked, corrupt, incompatible, or changing snapshots fail closed and preserve
evidence. Verification compares logical committed data, not inode bytes.

## Subtask T045 — Copy partition and quarantine

Canonicalize valid UUIDs once and copy each attributable row plus related
delivery/body history into only that project's staged store. Preserve identities
and statuses, assigning migrated rows to sealed/non-ordinary epochs. Missing,
blank, malformed, conflicting identities and ledger ghosts enter named local
quarantine with reason codes and no sender API. Copy refusal as
`migrated_refusal`; report old grants but require explicit re-consent.

## Subtask T046 — Atomic cutover through existing authority

Use WP02's sole layout authority to advance generation only after copy and exact
verification. Publish staged stores and the project-only marker atomically under
the layout lock. Do not modify the current writers owned by WP04: validate each
census row's existing immediate pre-insert permit in both orderings. If writer
commit wins, the snapshot captures it once; if cutover wins, the existing writer
redirects/retries exactly once into the project store.

## Subtask T047 — Recognized-daemon protocol and residue diagnosis

Implement a versioned quiesce acknowledgement/restart handshake for recognized
daemons/current binaries. Track durable phases `inventoried`, `quiesced`,
`copied`, `verified`, `cutover`, `restarted`, `complete`/`failed`; rerun resumes
idempotently. Unrecognized old binaries are outside the barrier: post-cutover
writes are diagnosed residue and permanently absent from live delivery.

## Subtask T048 — Commands and hard-kill convergence

Wire explicit preview, migrate, status/doctor, and quarantine diagnostics. Also
wire WP03 opt-in/opt-out services and turn old grant flags into non-zero migration
guidance without reimplementing consent. Kill subprocesses before/after each
durable phase, rerun, and prove exact convergence, unchanged sources, no duplicate
or redelivery, and no cross-project side effect.

## Branch Strategy

Run `spec-kitty agent action implement WP10 --agent <name>` after WP04 and WP07
approval. WP07 sequentially owns the final/exit sync transport redesign in
`src/specify_cli/cli/commands/sync.py`; WP10 may edit that shared file only after
the approved WP07 lineage is present, and only for migration/cutover commands.
It may still progress alongside disjoint later transport evidence. Use the
computed lane and governed merge; do not publish.

## Test strategy

Commit one mixed-store WAL fixture red-first. Run all five owned tests plus
relevant CLI/migrate-journal tests. Use temporary runtime roots and real
subprocess kills. Run ruff and strict mypy on touched modules.

Sequentially own `tests/event_journal/test_identity_migration_3030.py` here:
its legacy file/schema/ALTER scenarios are read-only migration-input contracts,
not a reason for WP04 to retain a live path constructor. Re-pin those scenarios
to the WAL-aware inventory/copy boundary and preserve source bytes.

Sequentially own `tests/delivery/test_purge_all_body_uploads_3030.py` here as
well. Its shared `queue.db`, blank/whitespace identities, and whole-legacy-store
disposition are migration/quarantine contracts. Replace the removed global live
purge API with explicit immutable-source inventory and complete
migrated/quarantined disposition evidence; WP04 must not resurrect a shared-store
compatibility constructor or `purge_all_body_uploads` live path.

## Definition of Done

- Inventory includes committed WAL state and never mutates source evidence.
- Attributable rows preserve exact state; unsafe rows quarantine.
- Old grants/flags create no grant.
- Every WP04 writer is verified against WP02's cutover authority.
- Cutover is atomic, exclusive, resumable, and has no live dual-read.
- Old-binary residue is diagnosed and non-deliverable.

## Risks and reviewer guidance

Hash and compare sources, inspect WAL-resident cases, and kill real processes at
every phase. Verify A-only commands do not scan B and late old-binary rows remain
invisible. Reject cleanup/deletion, synthetic UUIDs, schema-creating source opens,
writer edits in this WP, a second layout authority, or live legacy fallback.

## Activity Log

- 2026-08-10T02:25:00Z – codex – Sequentially assigned the existing identity-migration #3030 suite to WP10. Its legacy file/schema/ALTER cases are read-only migration-source contracts and cannot justify retaining a live path constructor in WP04.
- 2026-08-10T02:45:00Z – codex – Sequentially assigned the legacy purge-all body-upload #3030 suite to WP10 after WP04 review. Blank/whitespace identities and a whole shared queue are migration/quarantine inputs, not grounds for restoring a live global purge API.
- 2026-08-10T19:20:00Z – codex – Added WP07 as a dependency because both packages sequentially require `src/specify_cli/cli/commands/sync.py`: WP07 first phases final/exit dispatch around short project-store UoWs and WP06 transport commits; WP10 later adds migration/cutover commands without reopening or replacing the transport design.
