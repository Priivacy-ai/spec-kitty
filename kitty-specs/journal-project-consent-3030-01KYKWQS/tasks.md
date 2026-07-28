# Tasks: Journal Project Consent — #3030

**Mission**: `journal-project-consent-3030-01KYKWQS` · **Branch**: `feat/journal-project-consent-3030`
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)

> **Containment wave first (WP01, WP02), and it needs no migration.** The leak is in the journal
> dispatcher (`delivery/dispatcher.py:_select_undelivered` over `journal.read_all()`), not
> `sync/batch.py`. WP01 makes the leak loud and also unblocks `saas#585`; WP02 deletes an entire second
> leaking drain. Only then the durable wave (WP04–WP06) makes delivery correct.
>
> **WP01 is bounded to mixed batches.** The cross-project refusal only fires when a *selected batch*
> spans projects. Because selection is FIFO and limit-bounded, a homogeneous window of one
> non-consented project still ships. Correct per-project delivery arrives with WP06 — do not treat WP01
> as containment for the incident population.
>
> **The enabler is load-bearing and easy to get wrong**: the journal has *no* schema-migration
> mechanism (`_ensure_schema` is `CREATE TABLE IF NOT EXISTS` only) while all four SQL constants derive
> from `_COLUMN_LIST` — so adding columns without an ALTER step bricks every existing journal file.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | **Red-first**: incident reproduction (6 projects, 1 consented, other 5 with **no consent record at all**) + multi-project refusal + empty-selection tests. RED on current code (SC-001, SC-003) | WP01 | |
| T002 | Cross-project pre-flight: refuse before any POST, name the projects, exit non-zero, no retry-count mutation. Identity resolved in-memory over the **already-selected batch** only (FR-004) | WP01 | |
| T003 | Split `drain_blocked_reason` into **transient gate reasons** (re-evaluated at drain) and a **terminal reason**; exclude only the terminal one from `_select_undelivered`. Today the column collapses `not saas_enabled OR not checkout_enabled` into one token and also stamps `missing_auth`/`missing_team` (`journal.py:338-352`), and `emitter.py:2246-2248` states drain-blocked events are re-evaluated each tick — so excluding all non-null values would permanently strand every pre-login capture | WP01 | |
| T004 | `GateKind` consent-availability gate + consent port in `GateContext`/`evaluate_gates`; aborts the run when consent is unresolvable (FR-001) | WP01 | |
| T005 | Fail closed at `routing.py:114-116`; empty-selection short-circuit before payload build, replacing the misleading no-Private-Teamspace message at `batch.py:1484-1488` (FR-003, FR-005) | WP01 | |
| T006 | FR-010 restated: journal write requires identity; identity-less capture is stamped into a named non-deliverable state via the existing `drain_blocked_reason` vocabulary — **not** dropped (NFR-005) | WP01 | |
| T007 | Precondition guard: require/run `migrate_queues_to_journal`, assert the legacy queue is empty, **fail loudly** rather than discard (pre-WP03 rows may have no journal copy) | WP02 | |
| T008 | Delete the queue-backed daemon drain: `background.py:395,455-461,589-592`; retire `queue.remove_project_events` per C-004. Assert no code path constructs it (FR-012, SC-005) | WP02 | |
| T009 | Terminal reject classification **in `delivery/receivers.py`**: `DeliveryOutcome.TERMINAL_FAILED` is reachable from exactly one predicate today (`receivers.py:411-414`, oversized-single-event). Map a stable server refusal reason there. `delivery/ledger.py:98-101` **already** maps `terminal_failed`/`failed_permanent`, so no ledger work is needed. Folds #3005 (FR-014, SC-009) | WP01 | |
| T010 | Additive journal migration: `PRAGMA table_info` → `ALTER TABLE ADD COLUMN`, inside `_ensure_schema`, idempotent, before any derived-SQL use. Reuse the `queue.py:1242-1248` precedent. Test opens a **pre-migration** DB file and reads it (C-001, C-002) | WP04 | |
| T011 | Promote the identity resolver to `sync/project_identity.py` as **one ordered constant chain** incl. the fourth site `payload.subject.project_uuid` (`emitter.py:2037`); nil sentinel normalizes to NULL. Test asserts a single definition site (NFR-001) | WP04 | |
| T012 | `project_uuid`/`project_slug` in `ORDERED_COLUMNS` + indexes; idempotent, lossless backfill using T011's chain (FR-006, FR-009, NFR-004, SC-007) | WP04 | |
| T013 | Count unresolved-identity events for FR-011 (WP07 owns surfacing them) | WP04 | |
| T014 | `sync/consent.py`: uuid-keyed consent index, written by `enable_checkout_sync`/`disable_checkout_sync`; conflict rule **deny if any checkout of the project is opted out**, encoded once (FR-013) | WP05 | |
| T015 | Absence of a consent record denies for delivery, overriding the default-allow fall-through at `routing.py:87` (FR-002) | WP05 | |
| T016 | Backfill path-keyed → uuid-keyed as a **single batched write**; unreadable paths retain the path entry with an `unresolved` marker the predicate ignores and WP07 renders; `enable_checkout_sync` **fails loudly** when no uuid resolves | WP05 | |
| T017 | Project-filtered journal read as an **identity projection** (`event_id`, `created_at`, `project_uuid`; no payload BLOB) with **no `LIMIT`**; payload hydration via `read_by_id` over the ledger-selected batch (FR-008, NFR-003) | WP06 | |
| T018 | `_select_undelivered` consumes the filtered read; stored column is the **sole authority** for selection (FR-007, NFR-001) | WP06 | |
| T019 | Liveness: 2,000 non-consented events older than 10 consented → one drain delivers all 10 (NFR-002, SC-002) | WP06 | |
| T020 | **Corrected target**: `max_events_per_batch`/`_should_probe_advertised_limits` exist **only** in `sync/batch.py` — the dead daemon path WP02 deletes. The journal drain's window is the local constant `_EVENT_SYNC_DISPATCH_BATCH_LIMIT` in `_run_dispatch_batches` (`cli/commands/sync.py:807-820`), halved and regrown on HTTP 413. Exercise the real window there; a fake advertising batch limits would test a corpse (NFR-007) | WP07 | |
| T021 | Per-project breakdown in `sync doctor`/`status`/`migrate`, reconciled against the journal's retained count — **not** `OfflineQueue().get_queue_stats()`. Folds #3004. Renders unresolved-identity and `unresolved`-consent rows (FR-011, FR-015, SC-004) | WP07 | Y |
| T022 | `sync purge --project <slug-or-uuid>` (dry-run default) + `--all`, over journal **and** ledger, via `delivery/retention.py` (FR-016, FR-017, NFR-006, SC-006) | WP08 | Y |
| T023 | Document that `SPEC_KITTY_ENABLE_SAAS_SYNC`/`SPEC_KITTY_SAAS_URL` are machine-global; CI-checkable anchor (FR-018) | WP09 | Y |
| T025 | Body-upload consent: `prepare_body_uploads` gates once at enqueue on `is_sync_enabled_for_checkout(repo_root)` (`body_upload.py:150`), which is default-allow on absence; `_drain_body_queue` then POSTs every task under only the machine-global `is_saas_sync_enabled()`. Resolve consent **per task at drain time** from the task's namespace project identity, not cwd. Bodies are full `spec.md`/`plan.md`/`tasks/WP*.md` text (`body_upload.py:33-52`) | WP11 | |
| T026 | Add the body-upload queue to the purge differential — it shares the offline-queue DB file, so a purge reporting 100% today leaves queued bodies behind | WP11 | |
| T024 | Live drain against **`spec-kitty-dev`** at the incident's shape — **≥6 projects**: 1 consented, ≥3 with no consent record, ≥1 explicit opt-out, ≥1 identity-less. Evidence artefact records **before/after counts per `project_slug`**, the drain's own delivered count, and the CLI commit SHA (SC-008) | WP10 | |

## Dependency graph

```
WP01 (containment + terminal reject) ─┐
WP02 (legacy drain removal)          ─┴─ no deps, ship first
                                        WP01 also unblocks saas#585 WP07

WP04 (identity enabler) ─┬─> WP05 (consent index) ──> WP06 (filtered read + gate) ──> WP10 (live)
                         ├─> WP07 (visibility, folds #3004)
                         └─> WP08 (purge)
WP05 ──> WP11 (body-upload consent — uncovered egress path)
WP09 (docs) — no deps
```

- **WP01, WP02, WP09** have no dependencies and may run in parallel. **WP03 was deleted**: its assigned files (`delivery/ledger.py`, `delivery/interfaces.py`) contained no work — the ledger already maps both terminal keys and the only file needing change is `receivers.py`, which WP01 owns. T009 moved to WP01.
- **WP02 is a deletion, not a gate** — research decision 1 resolved to *remove*, because
  `_capture_to_journal` (`emitter.py:2057`) runs before every gate and is unconditional, so every
  queued event already has a journal copy.
- **WP05** depends on WP04 only for T011's shared resolver; it could start against that signature.
- Each enabler asserts on its **public seam** (the filtered read API, the consent resolver) — no test
  reaches into SQL or private helpers, or the enabler reviews lock in implementation shape.

## WP01 — Containment: refuse loudly, fail closed

Subtasks: T001–T006. Dependencies: none. `execution_mode: code_change`. Requirements: FR-001, FR-003,
FR-004, FR-005, FR-010, SC-001, SC-003. Makes the leak loud with **no schema change**. Note honestly:
this does not make delivery correct for a multi-project machine — WP06 does. FR-003 hardens the emit
path, daemon batch and body uploads, **not** the drain that leaked (`is_sync_enabled_for_checkout` has
zero callers under `delivery/`), so it must not be presented as containment.

## WP02 — Remove the legacy queue drain

Subtasks: T007–T008. Dependencies: none. `execution_mode: code_change`. Requirements: FR-012, SC-005.
Deletes the second live drain rather than teaching it consent.

## WP04 — Journal identity enabler (migration + columns + backfill)

Subtasks: T010–T013. Dependencies: none. `execution_mode: code_change`. Requirements: FR-006, FR-009,
FR-011 (count), NFR-004, NFR-005, SC-007, C-001, C-002, C-003. **T010 must land before T012** — without
the ALTER step, adding columns to `ORDERED_COLUMNS` breaks every existing journal file.

## WP05 — Consent index and resolution rule

Subtasks: T014–T016. Dependencies: WP04. `execution_mode: code_change`. Requirements: FR-002, FR-013.
Consent is keyed by absolute path today (`config.py:216,233`) while events carry `project_uuid`; this
supplies the missing join. `SyncConfig` setters are unlocked whole-file read-modify-writes, so a lost
record is now a silent delivery denial — hence the single batched write.

## WP06 — Filtered read and per-project selection

Subtasks: T017–T020. Dependencies: WP04, WP05. `execution_mode: code_change`. Requirements: FR-007,
FR-008, NFR-001, NFR-002, NFR-003, NFR-007, SC-001, SC-002. The **only** per-project seam; FR-001 lives
in WP01 because `GateContext` has no project dimension. NFR-001 is a **subset** invariant
(`delivered ⊆ consented` and `None ∉ delivered`), never a cardinality check — identity-less events
collapse to `{None}` and would satisfy `cardinality == 1` while leaking.

## WP07 — Operator visibility (folds #3004)

Subtasks: T021. Dependencies: WP04. `execution_mode: code_change`. Requirements: FR-011 (surfacing),
FR-015, SC-004. Without #3004, the per-project report renders from the store that is empty after
`sync migrate` — reproducing the incident's false-green.

## WP08 — Purge

Subtasks: T022. Dependencies: WP04. `execution_mode: code_change`. Requirements: FR-016, FR-017,
NFR-006, SC-006. Spans **two** stores: journal rows and delivery-ledger history. Research decision 2
(retain or remove ledger history) must be answered inside this WP and recorded.

## WP11 — Body-upload consent (uncovered egress path)

Subtasks: T025–T026. Dependencies: WP05. `execution_mode: code_change`. Requirements: FR-002, FR-016.
**Found by the post-tasks squad; no earlier artefact mentioned it.** `sync now` calls
`drain_body_uploads_only()` (`cli/commands/sync.py:2368`) — the same command the operator ran twice —
and that drain ships full document bodies with no per-project consent. Same breach class, live path,
previously unowned.

## WP09 — Documentation

Subtasks: T023. Dependencies: none. `execution_mode: code_change`. Requirements: FR-018.

## WP10 — Live verification

Subtasks: T024. Dependencies: WP06. `execution_mode: code_change`. Requirements: SC-008. Owns the
criterion no other WP claimed. Never production — see `docs/production-safety-guardrails.md`.
