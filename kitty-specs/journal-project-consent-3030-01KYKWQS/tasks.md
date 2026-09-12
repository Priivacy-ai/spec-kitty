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
| T001 | **Red-first**: incident reproduction (6 projects, 1 consented, other 5 with **no consent record at all**). RED on current code (SC-001) | WP04 | |
| T002 | Cross-project pre-flight: refuse before any POST, name the projects, exit non-zero, no retry-count mutation. Identity resolved in-memory over the **already-selected batch** only (FR-004) | WP01 | |
| T003 | Split `drain_blocked_reason` into **transient gate reasons** (re-evaluated at drain) and a **terminal reason**; exclude only the terminal one from `_select_undelivered`. Today the column collapses `not saas_enabled OR not checkout_enabled` into one token and also stamps `missing_auth`/`missing_team` (`journal.py:338-352`), and `emitter.py:2246-2248` states drain-blocked events are re-evaluated each tick — so excluding all non-null values would permanently strand every pre-login capture. **Covers ZERO incident rows** — never treat as containment | WP06 | |
| T004 | **UN-MARKED 2026-07-30 — was falsely recorded done.** `GateKind` still holds exactly `{SAAS_ENABLED, PRIVATE_TEAMSPACE, AUTH, ENDPOINT_CONFIGURED}` (`delivery/receivers.py:144-147`); no consent member, no consent port on `GateContext`, no change to `evaluate_gates`. spec.md names this the **first** root cause. Residual scope after C-003 and WP06: a `GateKind` can only express *machine-level* facts (per IC-01), so what is still owed is "consent is unresolvable → abort the whole run", NOT per-project selection, which WP06 delivers. Decide explicitly: implement that machine-level gate, or retire FR-001 in the spec — do not re-mark done without one of those (FR-001) | WP01 | |
| T005 | **PARTIALLY DONE — un-marked 2026-07-30.** The `routing.py` fail-close half shipped (`de274f3f7b`). The **empty-selection short-circuit did not**: `grep -rn "nothing to deliver" src/` returns nothing, the misleading message still stands at `sync/batch.py:1488`, and the journal drain has no equivalent report. SC-003 requires five fail-closed tests, one per path; the empty-selection one does not exist (FR-003 done, FR-005 open) | WP01 | |
| T006 | **Two distinct rules — do not conflate them (corrected 2026-07-29).** (a) *Identity-less* capture: FR-010 restated — the journal write requires identity, and an event whose identity cannot be resolved is stamped into a named non-deliverable state via the existing `drain_blocked_reason` vocabulary, **not** dropped; it stays durable and is counted under T013. (b) *Non-consenting* capture: per **amended** NFR-005 a non-consenting project's events must **never reach the journal** at all — capture-first durability applies only to consenting projects. Rule (b) is a deliberate reversal of the unconditional-write invariant documented in `event_journal/journal.py`, whose contract must be updated with it. Pinned by `tests/sync/test_sync_consent_capture_gap_3031.py::test_non_consenting_project_event_never_reaches_the_journal`. Beware the fake-green NFR-005 names: a bare `if skip_journal: return event` guard leaves capture unconditional at the real caller (`_capture_to_journal`, `sync/emitter.py:2057`) | WP04 | |
| T007 | Precondition guard: require/run `migrate_queues_to_journal`, assert the legacy queue is empty, **fail loudly** rather than discard (pre-WP03 rows may have no journal copy) | WP02 | |
| T008 | Delete the queue-backed daemon drain: `background.py:395,455-461,589-592`. Assert no code path constructs it (FR-012, SC-005). **C-004's `queue.remove_project_events` retirement moved to WP08** (corrected 2026-07-29): its caller `disable_checkout_sync` needs a journal-side purge, and the journal had no `project_uuid` to purge by until WP04 — see `tasks/WP08-purge.md` | WP02 | |
| T009 | Terminal reject classification **in `delivery/receivers.py`**: `DeliveryOutcome.TERMINAL_FAILED` is reachable from exactly one predicate today (`receivers.py:411-414`, oversized-single-event). Map a stable server refusal reason there. `delivery/ledger.py:98-101` **already** maps `terminal_failed`/`failed_permanent`, so no ledger work is needed. Folds #3005 (FR-014, SC-009) | WP01 | |
| T010 | Additive journal migration: `PRAGMA table_info` → `ALTER TABLE ADD COLUMN`, inside `_ensure_schema`, idempotent, before any derived-SQL use. Reuse the `queue.py:1242-1248` precedent. Test opens a **pre-migration** DB file and reads it (C-001, C-002) | WP04 | |
| T011 | Promote the identity resolver to `sync/project_identity.py` as **one ordered constant chain** incl. the fourth site `payload.subject.project_uuid` (`emitter.py:2037`); nil sentinel normalizes to NULL. Test asserts a single definition site (NFR-001) | WP04 | |
| T012 | `project_uuid`/`project_slug` in `ORDERED_COLUMNS` + indexes; idempotent, lossless backfill using T011's chain (FR-006, FR-009, NFR-004, SC-007) | WP04 | |
| T013 | Count unresolved-identity events for FR-011 (WP07 owns surfacing them) | WP04 | |
| T014 | `sync/consent.py`: the **one** consent resolver, encoding the FR-013×FR-019 precedence chain exactly once (see spec.md "FR-013 × FR-019 reconciliation"): project-local `.kittify/config.yaml` (refusal outranks grant) → machine-global uuid-keyed index → env var (never a grant alone) → absent = deny. Index is written by `enable_checkout_sync`/`disable_checkout_sync` and is a **cache**, not a second source of truth: when a readable checkout disagrees, the file wins and the index is corrected (FR-013, FR-019) | WP05 | |
| T015 | Absence of a consent record denies — expressed as **resolver semantics in `consent.py`** (WP05's file). The matching `routing.py:87` default-allow flip is a **WP01 DoD item**, since WP01 owns `routing.py`; splitting it this way keeps both inside their lane and keeps the emit/body paths deny-by-default too (FR-002) | WP05 | |
| T016 | Backfill path-keyed → uuid-keyed as a **single batched write**; unreadable paths retain the path entry with an `unresolved` marker the predicate ignores and WP07 renders; `enable_checkout_sync` **fails loudly** when no uuid resolves | WP05 | |
| T017 | Project-filtered journal read as an **identity projection** (`event_id`, `created_at`, `project_uuid`; no payload BLOB) with **no `LIMIT`**; payload hydration via `read_by_id` over the ledger-selected batch (FR-008, NFR-003) | WP06 | |
| T018 | `_select_undelivered` consumes the filtered read; stored column is the **sole authority** for selection (FR-007, NFR-001) | WP06 | |
| T019 | Liveness: 2,000 non-consented events older than 10 consented → one drain delivers all 10 (NFR-002, SC-002) | WP06 | |
| T020 | **Corrected target**: `max_events_per_batch`/`_should_probe_advertised_limits` exist **only** in `sync/batch.py` — the drain WP02 retired (the module still exists — un-exported, not deleted). The journal drain's window is the local constant `_EVENT_SYNC_DISPATCH_BATCH_LIMIT` in `_run_dispatch_batches` (`cli/commands/sync.py:807-820`), halved and regrown on HTTP 413. Exercise the real window there; a fake advertising batch limits would test a corpse (NFR-007) | WP07 | |
| T021 | Per-project breakdown in `sync doctor`/`status`/`migrate`, reconciled against the journal's retained count — **not** `OfflineQueue().get_queue_stats()`. Folds #3004. Renders unresolved-identity and `unresolved`-consent rows (FR-011, FR-015, SC-004) | WP07 | Y |
| T022 | `sync purge --project <slug-or-uuid>` (dry-run default) + `--all`, over journal **and** ledger, via `delivery/retention.py` (FR-016, FR-017, NFR-006, SC-006) | WP08 | Y |
| T023 | Document that `SPEC_KITTY_ENABLE_SAAS_SYNC`/`SPEC_KITTY_SAAS_URL` are machine-global; CI-checkable anchor (FR-018) | WP09 | Y |
| T025 | Body-upload consent: `prepare_body_uploads` gates once at enqueue on `is_sync_enabled_for_checkout(repo_root)` (`body_upload.py:150`), which is default-allow on absence; `_drain_body_queue` then POSTs every task under only the machine-global `is_saas_sync_enabled()`. Resolve consent **per task at drain time** from the task's namespace project identity, not cwd. Bodies are full `spec.md`/`plan.md`/`tasks/WP*.md` text (`body_upload.py:33-52`) | WP11 | |
| T026 | Add the body-upload queue to the purge differential — it shares the offline-queue DB file, so a purge reporting 100% today leaves queued bodies behind | WP11 | |
| T027 | Gate local-commit frame emission **and** the connect-time flush on per-project consent, resolved from the **frame's own** identity rather than cwd (`sync/local_commit.py`, `git/commit_helpers.py:1141-1157`, flushed via `sync/client.py:181-189`). Found by the post-WP06 review; ships mission slugs = client engagement names with zero consent check (FR-002, NFR-001) | WP12 | |
| T028 | Close `_auto_start_enabled`'s two fail-open `return True` paths (`sync/runtime.py:70,80`) — inability to determine consent is not consent (FR-003's rule) | WP12 | |
| T024 | Live drain against **`spec-kitty-dev`** at the incident's shape — **≥6 projects**: 1 consented, ≥3 with no consent record, ≥1 explicit opt-out, ≥1 identity-less. Evidence artefact records **before/after counts per `project_slug`**, the drain's own delivered count, and the CLI commit SHA (SC-008) | WP10 | |

## Ownership resolution (2026-07-28)

`lanes.json` mirrors `owned_files`, so a subtask that must write another lane's file is a hard stop at
implement time. Resolved: **WP01 owns `receivers.py` + `routing.py`** (the delivery-decision surface),
**WP06 owns `dispatcher.py` + `selection.py`** (the selection surface). T003 moved to WP06, T001/T006
to WP04, T005's `batch.py` message to WP02. Rationale in `tasks/WP01-containment.md`. Reversible if you
would rather keep T003 in wave 1 — but note it protects none of the incident population.

## Test-file ownership (added 2026-07-28)

The lane guard flagged that **no WP declared its test files**, so every WP would trip
`ACTIVE_WP_SCOPE_VIOLATION` on its first red-first commit. Each WP must own the test modules it
writes, alongside its source files. WP01 now owns `tests/sync/test_routing.py` and
`tests/delivery/test_receivers.py`; the remaining WPs need the same treatment before they start.

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

Subtasks: T014–T016. Dependencies: WP04. `execution_mode: code_change`. Requirements: FR-002, FR-013, FR-019.
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

## WP12 — Local-commit frames (third uncovered egress path)

Subtasks: T027–T028. Dependencies: WP05. `execution_mode: code_change`. Requirements: FR-002, NFR-001.
**Found by the post-WP06 adversarial review (2026-07-30); no earlier artefact mentions it.** Same breach
class as WP11 — a live path shipping project identity with no consent check — folded in rather than
deferred. See `tasks/WP12-local-commit-consent.md` for the full trace.

## WP10 — Live verification

Subtasks: T024. Dependencies: WP06. `execution_mode: code_change`. Requirements: SC-008. Owns the
criterion no other WP claimed. Never production — see `docs/production-safety-guardrails.md`.
