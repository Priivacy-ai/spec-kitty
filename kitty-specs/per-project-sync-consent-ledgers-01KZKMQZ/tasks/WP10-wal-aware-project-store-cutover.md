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
- tests/architectural/test_project_store_boundary.py
- tests/architectural/test_egress_consent_boundary.py
- tests/architectural/_baselines.yaml
- tests/specify_cli/cli/commands/test_sync_opt_in_converge.py
- tests/cli/commands/test_sync_commands.py
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

After attributable legacy rows have been copied into sealed project epochs, wire
the operator-facing history disclosure flow in this same command surface:
preview the exact WP03 cohort/hash/count, explicitly confirm it with actor and
idempotency identity, consume the persisted capability under the current target
and admission tuple, and invoke WP07's history/preflight transport with that exact
capability. The legacy filesystem importer must remain fail-closed without this
authority; migration or `--apply` may never manufacture or auto-confirm consent.

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
- 2026-08-10T22:55:00Z – codex – Closed a live-caller ownership gap discovered during T033: WP03 supplies the immutable history capability and WP07 supplies capability-gated history/preflight transport, but neither package owned the operator command that previews and confirms migrated sealed rows. WP10 now wires that flow after verified sealed-epoch copy, in the CLI surface it already owns. It must not synthesize a grant or auto-confirm during migration/import.
- 2026-08-11T17:43:37Z – codex – Sequential ownership amendment authorized by the mission arbiter after source-discovery gates correctly surfaced WP10's new boundaries. WP10 narrowly owns the two architecture census tests and their existing baseline artifact only to attribute exactly three snapshot connections (two read-only evidence connections plus one disposable backup destination), one exact loopback daemon-control sink, and eight staged-copy INSERT sites; prior census rows remain unchanged and negative controls must reject writable source access, non-loopback URLs, and ordinary live writers.
- 2026-08-11T17:52:21Z – codex – Sequential test ownership amendment authorized by the mission arbiter after the WP10 contract audit retired two live compatibility violations: opt-in no longer auto-deletes legacy source rows, and the old `sync migrate --backfill-consent-index` path can no longer promote machine-global consent. Ownership is limited to the complete focused opt-in-convergence module and exactly the three retired-migrate nodes in `test_sync_commands.py`; unrelated legacy reds and nodes remain unchanged.
- 2026-08-11T18:07:24Z – codex – Held uncommitted pre-review checkpoint on merge base `206204213d18ea0cb52010701bc57020f5306d8e` (approved PR head `7b3aa377cbba056bd51c2329f22ebcb725c3e816` is an exact parent). Final governed selection: 100 passed, 2 intentional xfails, one inherited shrink warning; adjacent project-store/history/layout/daemon selection: 114 passed. Ruff format/check, strict mypy on all three touched source modules, diff-check, ancestry, and owned-path census pass. NFR-007 reports are hash/reference-only; raw bodies remain only in chmod-0600 immutable staging snapshots and project-owned stores. A separate diagnostic baseline probe retains 26 unrelated pre-existing legacy-suite reds from removed live constructors/consent APIs; all five WP10-attributable contract-reversal nodes now pass.
- 2026-08-11T21:10:00Z – codex – Review-cycle reroll closed seven material cutover/evidence gaps without publishing: the winning source snapshot, copy, exact verification, and PROJECT_ONLY publication now share the sole machine layout lock; a blocked current writer redirects once after publication, and a real commit immediately before cutover is included. PROJECT_ONLY rejects every new migration identity before copy and leaves late legacy rows diagnosis-only. Delivery attempts require and exactly preserve the complete epoch/consent/target/admission/audience/hash/reference/state/deadline/policy/created authority shape; malformed rows quarantine without coercion. Verification/failure evidence is hash-only and stable across hard-kill resume, preview leaves main/WAL/SHM byte-identical, and reachable daemon identity drift fails closed. Focused remediation: 26 passed; owned migration/legacy commands: 44 passed plus 7 retired-command controls; adjacent project-store/history/layout: 139 passed; architecture: 51 passed, 2 intentional xfails. Held uncommitted for independent re-review.
- 2026-08-11T18:59:04Z – codex – Final review reroll closed the remaining raw-staging, result-validation, and relational-integrity blockers without publishing. Physical main/WAL/SHM staging now creates its directory at 0700 and each destination at 0600 before any bytes, with hard-kill residue and resumable cleanup proof. Delivery results require exact closed outcome/category/recorded-at and authority fields, with malformed rows quarantined and no copy/verify defaults. Attempts carrying an unmigrated outbox-task relation and their dependent results are classified incompatible/ghost before copy, so migration cannot fail mid-copy or silently drop/null the relation. Decisive migration/barrier/daemon set: 29 passed; governed owned set: 47 passed; retired-command controls: 7 passed; adjacent project-store/history/layout: 139 passed; architecture: 51 passed, 2 intentional xfails. Held uncommitted for independent re-review.
- 2026-08-11T19:15:00Z – codex – Narrow re-review reroll reconciled result dependencies after divergent-duplicate classification, so a result whose exact source-owned attempt is quarantined becomes a ledger ghost before partition/copy. Delivery-result validation now requires the exact canonical column set and the shared strict RFC3339 validator while preserving lowercase `t`/`z` contract parity. Red-first duplicate and shape/time mutants pass; decisive migration/barrier/daemon set is 31 passed, with Ruff, format, strict mypy, and diff-check green. Held uncommitted for independent re-review.
- 2026-08-11T19:41:32Z – codex – Final schema/duplicate/authority reroll moved duplicate poisoning ahead of schema and relation filtering, so one malformed divergent attempt poisons every same-identity copy and fixed-point reconciliation parks dependent results. Inventory now uses `table_xinfo` and fails closed on generated/hidden extensions. Attempt deadline/creation timestamps use the shared strict RFC3339 validator with lowercase `t`/`z` and numeric-offset parity. Lane-h write scope now records all seven previously authorized sequential architecture/legacy-test paths without changing other lane history. Red-first mutants pass; decisive set: 34 passed; governed owned set: 52 passed; retired-command controls: 7 passed; adjacent set: 139 passed; architecture: 51 passed, 2 intentional xfails; Ruff/format, strict mypy, JSON/diff, and ownership checks pass. Held uncommitted for independent re-review.
- 2026-08-11T19:49:26Z – codex – Narrow exact-schema reroll changed delivery-attempt validation from subset acceptance to exact canonical key-set equality. A real visible `future_authority` extension now quarantines the attempt as incompatible before copy and its dependent result as a ledger ghost, preventing PROJECT_ONLY publication from silently dropping unknown authority. Red-first mutant: 1 passed after correction; decisive migration/barrier/daemon set: 35 passed; Ruff/format, strict mypy, diff, and lane-h ownership checks pass. Held uncommitted for independent re-review.
