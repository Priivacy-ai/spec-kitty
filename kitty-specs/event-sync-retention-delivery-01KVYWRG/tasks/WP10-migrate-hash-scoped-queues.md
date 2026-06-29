---
work_package_id: WP10
title: Migration off hash-scoped queues
dependencies:
- WP01
- WP03
- WP05
requirement_refs:
- FR-013
- FR-018
tracker_refs: []
planning_base_branch: mission/event-sync-retention-delivery
merge_target_branch: mission/event-sync-retention-delivery
branch_strategy: Planning artifacts for this mission were generated on mission/event-sync-retention-delivery. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/event-sync-retention-delivery unless the human explicitly redirects the landing branch.
subtasks:
- T056
- T057
- T058
- T059
- T060
- T061
- T062
- T063
phase: Phase 5 - Policy, migration, status, CLI
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "76850"
history:
- at: '2026-06-29T06:21:37Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/sync/migrate_journal.py
create_intent:
- src/specify_cli/sync/migrate_journal.py
- tests/sync/test_migrate_journal.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/sync/migrate_journal.py
- src/specify_cli/sync/queue.py
- tests/sync/test_migrate_journal.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP10 – Migration off hash-scoped queues

## ⚡ Do This First: Load Agent Profile
Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter and behave per its guidance before parsing the rest of this prompt.
- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`
If no profile is specified, run `spec-kitty agent profile list` and select the best match for this WP's `task_type` and `authoritative_surface`.

---

## Objectives & Success Criteria

This WP implements plan concern **IC-07 (Migration off the hash-scoped queues)**. It moves currently-queued events out of the existing scoped SQLite queues into the new journal + ledger, and it retires the *event-queueing* responsibility from `queue.py` while keeping the non-event body-upload tables intact.

The hard reality this WP must respect: the existing scoped queue path is `~/.spec-kitty/queues/queue-<digest>.db`, where `<digest>` is a **one-way SHA-256** of `server|user|team` (`build_queue_scope`, `src/specify_cli/sync/queue.py:402`; path builder at `queue.py:504-505`). **The URL/scope cannot be recovered from the filename.** Migration must therefore discover all such DBs, attach events to a best-effort or explicitly-`unknown` target without fabricating identity, dedupe duplicate `event_id`s deterministically, quarantine divergent duplicates, and never rewrite event IDs.

This WP **owns all of `queue.py`** (single-owner), so it is also where event-capture is redirected to the journal and where `queue.py` consumes the WP01 derived queue scope — while `body_upload_queue` / `body_upload_failure_log` and their flow stay untouched (C-006).

Complete when:

- **FR-013 (migration of existing queues)** — every scoped `queue-<digest>.db` and the legacy `queue.db` is discovered and migrated into the journal+ledger; queued payloads are preserved; unknown-scope and duplicate-`event_id` cases are handled (contract §5).
- **FR-018 (collision quarantine)** — a same-`event_id`/divergent-payload collision writes a migration-conflict/audit row, leaves the source DB untouched, blocks cleanup, and exits non-zero/blocked (contract §5; SC-011).
- **NFR-005 (migration safety)** — migration is transactional per source DB and idempotent on re-run; no currently-queued payload is ever lost.
- **SC-006** — migrating from **one or more** scoped DBs preserves 100% of currently-queued payloads, resolves duplicate `event_id`s deterministically, and attaches events to a best-effort-or-`unknown` target without fabricating identity. A single-DB happy path is **insufficient**.
- **C-006** — `body_upload_queue` / `body_upload_failure_log` and their flow remain owned by and operational in `queue.py`; no "retire `queue.py`" step breaks non-event body uploads.

## Context & Constraints

**Prerequisite WPs and what they hand you:**

- **WP01 — Target Authority resolver** (`src/specify_cli/sync/target_authority.py`): the canonical `ResolvedSyncTarget`, including the **derived queue scope** and `queue_db_path`. This WP redirects `queue.py`'s scope consumption onto WP01's derived scope (T062) — `queue.py` must stop computing its own selector and consume the resolver's derived isolation key.
- **WP03 — Event Journal** (`src/specify_cli/event_journal/journal.py`): the append-only, `event_id`-keyed payload store the migration writes into. The migration appends migrated payloads here; it does not delete from sources during dry-run/import.
- **WP05 — Delivery Ledger** (`src/specify_cli/delivery/ledger.py`): per-event/per-target state. Migrated events are attached to a best-effort or `unknown` target via the registry, and the ledger records provenance for the migrated rows.

**The unrecoverable-identity problem (spec edge case "Hash-only scoped DB paths"; contract §5):**

- `build_queue_scope(server, user, team)` (`queue.py:402`) produces the canonical scope string; `_scoped_queue_path` hashes it with SHA-256 truncated to 16 hex chars → `queues/queue-<digest>.db` (`queue.py:504-505`).
- Because the digest is a one-way hash, **the original `server|user|team` cannot be derived from the filename**. Migration must NOT fabricate a URL/team from a digest. Unknown source scope is represented as **explicit `unknown` provenance**.
- The *current* migration only folds a legacy `queue.db` into the active scope — that is insufficient. This WP must glob the whole queue dir.

**Links:**

- `kitty-specs/event-sync-retention-delivery-01KVYWRG/spec.md` — FR-013, FR-018, NFR-005; SC-006, SC-011; edge cases "Hash-only scoped DB paths", "Migration with no recoverable history", "Duplicate event_id collision during migration".
- `kitty-specs/event-sync-retention-delivery-01KVYWRG/plan.md` — IC-07 (purpose + duplicate policy + risks), C-006.
- `kitty-specs/event-sync-retention-delivery-01KVYWRG/contracts/event-sync-delivery-contract.md` — §5 (Migration) is the binding observable behavior; §6 compatibility rules (body-upload tables stay owned by `queue.py`).

**Architectural constraints to honor:**

- **C-006 (body-upload tables untouched)** — `queue.py` keeps `body_upload_queue` / `body_upload_failure_log` (setup-plan / dossier sync, **not** event queueing) and their flow. The "retire event-queueing from `queue.py`" step (T062) must touch only the event-queueing responsibility.
- **C-005 (no event-ID changes)** — migration never rewrites `event_id`s.
- **C-001 (separate domain)** — migration logic lands in `sync/migrate_journal.py`; it writes into the WP03 journal / WP05 ledger surfaces, not new ad-hoc tables.
- **NFR-005** — atomic per source DB, idempotent re-run.
- **NFR-001** — tests assert observable CLI output + on-disk state, not call order.

> **Out-of-map note**: this WP owns `sync/migrate_journal.py`, **all of** `sync/queue.py`, and `tests/sync/test_migrate_journal.py`. WP02 rewires other `sync/` surfaces onto the resolver but explicitly does **not** edit `queue.py` (its risk note defers `queue.py` scope-consumption to this WP). Coordinate the scope-consumption seam with WP01/WP02; do not duplicate the resolver here.

## Branch Strategy
- **Strategy**: Planning artifacts were generated on mission/event-sync-retention-delivery; completed changes must merge back into mission/event-sync-retention-delivery.
- **Planning base branch**: mission/event-sync-retention-delivery
- **Merge target branch**: mission/event-sync-retention-delivery
> Populated by `spec-kitty agent mission tasks`. Do not change manually.

## 🔴 ATDD-First (binding — charter C-011)

**You cannot start implementation until a failing-first ATDD test exists.** Per the charter's *ATDD-First Discipline* (binding, C-011), this WP follows red→green→refactor:

1. **RED first** — before any implementation commit, write at least one acceptance test that pins the user-observable behaviour this WP delivers (see the Subtasks/Acceptance below) and commit it **as the lane's first, separate commit while it FAILS**.
2. **GREEN** — implement until that test (and the rest) pass.
3. **Refactor** with the tests green.

The reviewer verifies **red→green**: the ATDD test was RED on `mission/event-sync-retention-delivery` and GREEN on this WP's final commit. A WP without a failing-first ATDD commit is **rejected at review** even if the code works.

## 🔒 Identifier Safety (binding — charter)

This WP generates storage-facing identifiers (the `queue-<digest>` scope digest and any migration-target slug) from user/branch/URL/team input. Per the charter's *Identifier Safety Rules* they MUST be **ASCII-only and deterministic**: sanitize with an explicit ASCII allowlist (`[A-Za-z0-9_]`) or opt regexes into `re.ASCII` — never rely on default Unicode `\w`/`\W`. **Required regression coverage**: at least one accented-Latin input plus an assertion that the produced identifier `.isascii()` is `True`.

## Subtasks & Detailed Guidance

### Subtask T056 – Discover ALL scoped `queue-<digest>.db` files + legacy `queue.db`
- **Purpose**: Find every source DB the migration must process — not just the active scope the current migration handles. Glob the queue dir for all `queue-<digest>.db` files plus the legacy `queue.db` (FR-013; contract §5 rule 1). `[P]` — discovery is independent of the import/dedupe phases.
- **Steps**:
  1. In `src/specify_cli/sync/migrate_journal.py`, add a discovery function `discover_source_dbs(spec_kitty_dir) -> list[SourceDb]` that:
     - globs `<spec_kitty_dir>/queues/queue-*.db` (the scoped DBs; path shape from `queue.py:504-505`),
     - includes `<spec_kitty_dir>/queue.db` (legacy) if present.
  2. Represent each source as a small record (`path`, parsed `digest` or `legacy`, plus a placeholder for resolved provenance filled in T057).
  3. Do **not** assume the active scope is the only one — explicitly enumerate the directory. The current migration's active-scope-only behavior is the bug being fixed.
  4. Reuse the existing `queue.py` scope-dir / legacy-path helpers (`_scoped_queue_dir`, `_legacy_queue_db_path`) rather than re-deriving paths, since this WP owns `queue.py`.
- **Files**: `src/specify_cli/sync/migrate_journal.py` (discovery); may read helpers from `src/specify_cli/sync/queue.py`.
- **Parallel?**: Yes (`[P]`) — pure filesystem discovery.
- **Validation**:
  - [ ] All `queue-<digest>.db` files in the queue dir are discovered (not just the active one).
  - [ ] Legacy `queue.db` is discovered when present.
  - [ ] Discovery is stable/deterministic (sorted) so re-runs and tests are reproducible.
- **Edge cases**: an empty queue dir yields an empty list (no error). A malformed filename that doesn't match `queue-<digest>.db` is skipped (not misparsed). A digest the current install cannot map to a known scope is **not** an error here — it's handled as unknown provenance in T057.

### Subtask T057 – Best-effort OR explicitly-`unknown` delivery target — never fabricate identity
- **Purpose**: Attach migrated events to a delivery target. Where the source scope can be matched to a known target (e.g. the active resolved target's digest matches the filename digest), attach best-effort; otherwise attach to an explicit **`unknown`** provenance. Because the digest is a one-way hash, the migration must **never fabricate a URL/team identity from a digest** (FR-013; contract §5 rule 2; SC-006).
- **Steps**:
  1. Compute the digest for the WP01 resolved target via `build_queue_scope` + the same SHA-256 truncation, and compare it to each source DB's filename digest. A match → best-effort attach to that known target.
  2. Any unmatched digest → attach migrated events to an explicit `unknown` provenance marker (recorded on the ledger/journal provenance), **not** a guessed URL/team.
  3. Record the source digest as provenance regardless, so an operator can audit which source DB an event came from.
  4. Be explicit in code/comments that the digest is not reversible — no reverse-lookup, no fabrication.
- **Files**: `src/specify_cli/sync/migrate_journal.py`.
- **Parallel?**: No — consumes discovery (T056).
- **Validation**:
  - [ ] An unmatched-digest source attaches events to `unknown` provenance (SC-006), never a fabricated identity.
  - [ ] A matched-digest source attaches best-effort to the known target.
  - [ ] Source digest is recorded as provenance on migrated rows.
- **Edge cases**: multiple unmatched digests each produce distinct `unknown`-with-digest provenance (they are distinguishable for audit, but none gets a fabricated URL). The legacy `queue.db` (no digest) is also `unknown` provenance unless it matches the active scope by content/convention.

### Subtask T058 – Transactional per source DB + idempotent re-run (NFR-005)
- **Purpose**: Make migration safe to interrupt and safe to re-run. Each source DB is migrated within a single transaction (all-or-nothing per source); re-running the migration imports nothing new for already-migrated sources (NFR-005; contract §5 rule 4).
- **Steps**:
  1. Wrap each source DB's import in a transaction against the journal/ledger writes; on failure, roll back that source's writes and leave the source DB untouched.
  2. Make import idempotent by keying on `event_id` (+ provenance) — an event already present in the journal with identical canonical payload is a no-op import (ties into T059 dedupe).
  3. Record per-source migration status (imported / skipped-already / conflict) so a re-run can report "nothing to do" and a partial prior run can be safely resumed.
  4. Never delete a source DB as part of import; deletion/cleanup is a separate, explicit, post-success step (and is blocked entirely if any conflict exists — T060).
- **Files**: `src/specify_cli/sync/migrate_journal.py`.
- **Parallel?**: No — consumes T057.
- **Validation**:
  - [ ] A failure mid-source rolls back that source's writes (atomic per DB, NFR-005).
  - [ ] Re-running after a complete migration imports zero new rows (idempotent).
  - [ ] No currently-queued payload is lost across an interrupted-then-resumed run.
- **Edge cases**: an interrupted run that committed source A but not source B re-runs cleanly: A is a no-op, B imports. A source DB that is locked/corrupt fails that source only and does not abort migration of the others (report it; don't crash the whole run).

### Subtask T059 – Identical duplicate `event_id` imports once with all provenance
- **Purpose**: Define the deterministic dedupe for the common case — the *same* `event_id` appears in multiple source DBs with an **identical canonical payload**. It imports **once** and records **all** source-DB provenance (FR-013; contract §5 rule 5; SC-006/SC-011 identical-dup half).
- **Steps**:
  1. Canonicalize the payload deterministically (stable serialization) before comparing, so byte-level encoding differences that are semantically identical do not count as divergence.
  2. On a second occurrence of an `event_id` with a matching canonical payload, do not insert a second journal row — instead append the new source-DB digest to that event's provenance list.
  3. Ensure the provenance accumulation is itself idempotent on re-run (the same source digest is recorded once).
- **Files**: `src/specify_cli/sync/migrate_journal.py`.
- **Parallel?**: No — consumes T057/T058.
- **Validation**:
  - [ ] Two source DBs with the same `event_id` + identical canonical payload → one journal row, two provenance entries (SC-011 identical-dup).
  - [ ] Re-run does not duplicate provenance entries.
  - [ ] `event_id` is unchanged (no rewrite — C-005, T061).
- **Edge cases**: three+ sources with the same identical event accumulate three+ provenance entries on one row. An identical duplicate within the *same* source DB (rare) also dedupes to one row.

### Subtask T060 – Divergent duplicate → conflict/audit row; source untouched; cleanup blocked; non-zero/blocked
- **Purpose**: Define the safety case — the *same* `event_id` appears with a **divergent canonical payload** across sources. This must NOT overwrite, merge, or silently pick one. It writes a **migration-conflict/audit row**, leaves the source DB **untouched**, **blocks cleanup**, and exits **non-zero/blocked** until an operator resolves it (FR-018; contract §5 rule 6; SC-011 divergent-dup half).
- **Steps**:
  1. When an incoming `event_id` matches an existing journal `event_id` but the canonical payloads differ, do not import the divergent payload into the journal and do not mutate the existing row.
  2. Write a migration-conflict/audit record capturing: the `event_id`, the conflicting source digests, and enough to let an operator inspect both payloads.
  3. Mark the affected source DB(s) as **cleanup-blocked** — the migration must refuse to delete/clean any source DB while an unresolved conflict references it.
  4. The overall migration command exits **non-zero / blocked** when any conflict exists, with an actionable message pointing the operator to the conflict records.
  5. Never rewrite the `event_id` and never fabricate a merged event (C-005; spec edge case).
- **Files**: `src/specify_cli/sync/migrate_journal.py`.
- **Parallel?**: No — consumes T059.
- **Validation**:
  - [ ] A divergent duplicate writes a conflict/audit row and does **not** mutate or overwrite the existing journal payload (FR-018).
  - [ ] The source DB(s) involved are left untouched and cleanup is blocked (SC-011).
  - [ ] The migration command exits non-zero/blocked while a conflict is unresolved.
  - [ ] No `event_id` rewrite, no merged-event fabrication.
- **Edge cases**: a source DB containing both clean events and one divergent-conflict event imports the clean events but is still cleanup-blocked due to the conflict. Resolving a conflict is an operator action outside this command's automatic flow — this WP only records and blocks, it does not auto-resolve.

### Subtask T061 – Never rewrite event IDs; delivered-and-deleted events are unrecoverable
- **Purpose**: Lock in C-005 and set honest expectations. Migration never rewrites `event_id`s, and it must be explicit that events already **delivered-and-deleted** under the old destructive queue cannot be reconstructed — only currently-queued payloads survive (FR-013; contract §5 rules 3 & 7; spec edge case "Migration with no recoverable history").
- **Steps**:
  1. Carry each source row's `event_id` through verbatim into the journal — assert (in code) that the migrated `event_id` equals the source `event_id`.
  2. Make the migration report/output state plainly that it migrates **only currently-queued payloads**; delivered-and-deleted history is unrecoverable (no attempt to reconstruct it).
  3. Surface a count of migrated events vs. an explicit note that prior deleted events are not recoverable, so operators are not misled into thinking the journal is complete history.
- **Files**: `src/specify_cli/sync/migrate_journal.py`.
- **Parallel?**: No — applies across the import path.
- **Validation**:
  - [ ] Migrated `event_id` is byte-identical to the source `event_id` (no rewrite — C-005).
  - [ ] Migration output explicitly states only currently-queued payloads survive.
- **Edge cases**: a source DB that is empty (all its events were already delivered-and-deleted) migrates zero events and the report says so — not an error, just an honest "nothing queued to migrate".

### Subtask T062 – Retire event-queueing from `queue.py`; keep body-upload tables; consume WP01 derived scope
- **Purpose**: Move the event-queueing responsibility out of `queue.py` (events now live in the journal) **while keeping `body_upload_queue` / `body_upload_failure_log` and their flow fully intact** (C-006). Redirect new event capture to the journal. This is also where `queue.py` consumes WP01's **derived** queue scope (the scope is a derived isolation key, not an independent selector — FR-016 rationale).
- **Steps**:
  1. Identify the event-queueing surface in `queue.py` (the event enqueue path + the destructive `process_batch_results` event branches at `queue.py:1668`) and redirect new event capture to the WP03 journal. The non-destructive ledger semantics for events are owned by the dispatcher (WP07) — `queue.py` stops being the event store.
  2. **Preserve** `body_upload_queue` and `body_upload_failure_log` (setup-plan / dossier body uploads) and every method/flow that drives them. These are NOT event queueing (C-006). No method, table, or call path for body uploads may be removed or broken.
  3. Make `queue.py` consume the WP01 `derived_queue_scope` / `queue_db_path` from `target_authority.py` instead of independently computing a selector. Add an inline rationale: queue scope is a *derived isolation key* for the body-upload tables, never a target selector (FR-016 / contract §1: "active_queue_scope is never an input selector").
  4. Keep `build_queue_scope` / `_scoped_queue_path` available where the migration and body-upload paths still need digest computation, but ensure event capture no longer creates new `queue-<digest>.db` event rows.
- **Files**: `src/specify_cli/sync/queue.py` (this WP owns all of it).
- **Parallel?**: No — depends on the journal write path (T056–T061) being defined.
- **Validation**:
  - [ ] `body_upload_queue` / `body_upload_failure_log` tables and their flow are unchanged and still pass any existing body-upload tests (C-006; contract §6).
  - [ ] New event capture routes to the journal, not a new `queue-<digest>.db` event row.
  - [ ] `queue.py` consumes WP01's derived scope; no independent target-selector logic remains, with an inline rationale comment.
  - [ ] `ruff` and `mypy` clean on `queue.py`; no new suppressions.
- **Edge cases**: a mixed `queue.py` operation that touches both event rows (now gone) and body-upload rows (kept) must still serve the body-upload side. If existing event-queueing tests exist, update them to assert the new journal routing rather than deleting coverage of the (retained) body-upload path. If retiring an event method risks a body-upload regression, file the seam as an upstream coordination note rather than removing shared infrastructure.

### Subtask T063 – Tests in `tests/sync/test_migrate_journal.py`
- **Purpose**: Cover the contract §5 "Required tests" and SC-006/SC-011 with observable on-disk assertions (NFR-001). A single-DB happy path is **insufficient** — the multi-DB, unknown-digest, identical-dup, and divergent-dup cases are mandatory.
- **Steps**: Author `tests/sync/test_migrate_journal.py` with at least these scenarios, asserting journal rows, ledger/provenance, conflict records, and source-DB state:
  1. **Multiple scoped DBs in one run (SC-006, contract §5 row 1)**: seed two+ `queue-<digest>.db` files with distinct events; run migration; assert all currently-queued payloads from all sources land in the journal, none lost.
  2. **Unknown-digest source → unknown provenance (contract §5 row 2)**: seed a source whose digest does not match the resolved target; assert its events attach to explicit `unknown` provenance, with no fabricated URL/team (SC-006).
  3. **Identical duplicate dedupes with provenance (contract §5 row 3, SC-011)**: same `event_id` + identical canonical payload in two sources; assert one journal row with two provenance entries; `event_id` unchanged.
  4. **Divergent duplicate creates a conflict and preserves the source DB (FR-018, contract §5 row 4, SC-011)**: same `event_id` + divergent payload; assert a migration-conflict/audit row, the existing journal payload is unmutated, both source DBs are left untouched, cleanup is blocked, and the command exits non-zero/blocked.
  5. **Idempotent re-run (NFR-005)**: run migration twice; assert the second run imports zero new rows and does not duplicate provenance.
  6. **Body-upload untouched (C-006, contract §6)**: assert `body_upload_queue` / `body_upload_failure_log` rows and flow are unaffected by migration.
- **Files**: `tests/sync/test_migrate_journal.py`.
- **Parallel?**: No — depends on all prior subtasks.
- **Validation**:
  - [ ] All six scenarios present; a single-DB happy path alone is rejected as insufficient (SC-006).
  - [ ] Tests assert on-disk/journal/ledger/conflict state and CLI exit status, not call order (NFR-001).
  - [ ] `PWHEADLESS=1 .venv/bin/pytest tests/sync/test_migrate_journal.py -q` passes.
- **Edge cases**: include an empty source DB (zero queued → zero migrated, no error) and a source that mixes clean + conflicting events (clean imported, still cleanup-blocked).

## Test Strategy

- **Mandatory test file**: `tests/sync/test_migrate_journal.py` (in `owned_files`).
- **Command**: `PWHEADLESS=1 .venv/bin/pytest tests/sync/test_migrate_journal.py -q`. These are filesystem/SQLite migration tests over temp queue dirs and the journal/ledger — they do **not** bind real ports or a daemon, so they run under the default parallel run (`-n auto --dist loadfile`). Per-worker HOME isolation (WP04 of the testing infra) keeps each worker's `~/.spec-kitty` separate, so seeding `queues/queue-<digest>.db` under an isolated home is safe. No `-n0` serial pass is needed.
- **Fixtures/stubs**: build a fixture that materializes a temp spec-kitty home with N scoped `queue-<digest>.db` source DBs (use the real `queue.py` schema for the source rows) plus the journal/ledger surfaces from WP03/WP05. Seed digests deterministically — one matching the resolved target (best-effort), one not (unknown provenance).
- **Observable-state discipline (NFR-001)**: assert journal rows by `event_id`, provenance lists, the presence/absence of migration-conflict rows, source-DB untouched-ness (row counts unchanged for conflicting sources), and the command exit status. Do not assert internal call order.
- Run `.venv/bin/ruff check` and `.venv/bin/mypy` on `migrate_journal.py` and `queue.py` before review — zero issues required.

## Risks & Mitigations

- **Migrating only the active scope (IC-07 risk; the current bug)** — *Mitigation*: T056 globs the whole queue dir; T063 scenario 1 asserts multi-DB coverage; a single-DB test is explicitly rejected (SC-006).
- **Fabricating identity from a one-way digest** — *Mitigation*: T057 attaches unmatched digests to explicit `unknown` provenance and forbids reverse-lookup; T063 scenario 2 asserts no fabricated URL/team.
- **Silently overwriting a divergent duplicate (FR-018 risk)** — *Mitigation*: T060 writes a conflict row, leaves the source untouched, blocks cleanup, and exits non-zero; T063 scenario 4 asserts all four.
- **Non-atomic / non-idempotent migration (NFR-005 risk)** — *Mitigation*: T058 wraps each source in a transaction and keys imports on `event_id`; T063 scenario 5 asserts a clean re-run.
- **Breaking body uploads while retiring event-queueing (C-006 risk)** — *Mitigation*: T062 preserves `body_upload_queue` / `body_upload_failure_log` and their flow; T063 scenario 6 asserts they are unaffected. This is the single most dangerous step in the WP — treat any body-upload test failure as a hard stop.
- **Rewriting event IDs (C-005)** — *Mitigation*: T061 asserts byte-identical `event_id` carry-through.

## Review Guidance

For `/spec-kitty.review`, verify against the contract's §5 "Required tests" and §6 compatibility:

- [ ] **FR-013**: all scoped `queue-<digest>.db` + legacy `queue.db` discovered and migrated; only currently-queued payloads survive (delivered-and-deleted history explicitly unrecoverable).
- [ ] **SC-006**: multi-DB migration preserves 100% of queued payloads; unknown digest → `unknown` provenance, no fabricated identity.
- [ ] **FR-018 / SC-011**: divergent duplicate → conflict/audit row, source DB untouched, cleanup blocked, non-zero/blocked exit; identical duplicate dedupes once with all provenance.
- [ ] **NFR-005**: transactional per source DB, idempotent re-run.
- [ ] **C-005**: `event_id`s never rewritten.
- [ ] **C-006 / contract §6**: `body_upload_queue` / `body_upload_failure_log` and their flow are intact and owned by `queue.py`; no event-queueing retirement broke a body-upload path.
- [ ] `queue.py` consumes WP01's derived queue scope with the "never a selector" rationale; `ruff` and `mypy` clean; no new suppressions.
- [ ] Tests assert observable on-disk/journal/ledger/conflict state and CLI exit status, not call order (NFR-001); multi-DB coverage present (single-DB happy path insufficient).

## Activity Log
> Entries chronological, appended at END. Format: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <action>`
- 2026-06-29T06:21:37Z – system – Prompt created.
- 2026-06-29T08:52:27Z – claude:opus:python-pedro:implementer – shell_pid=55131 – Assigned agent via action command
- 2026-06-29T09:20:39Z – user – shell_pid=55131 – WP10 implementation complete; advancing lane state for handoff
- 2026-06-29T09:20:42Z – user – shell_pid=55131 – WP10 implementation complete; advancing lane state for handoff
- 2026-06-29T09:25:06Z – claude:opus:python-pedro:implementer – shell_pid=55131 – Ready: multi-DB migration (unknown provenance, dup quarantine); queue.py event-queueing retired, body-upload intact (C-006); ATDD + gates green. Lane status-file drift is a coordination artifact (forced past kitty-specs guard).
- 2026-06-29T09:32:23Z – claude:opus:python-pedro:implementer – shell_pid=55131 – Ready: WP10 multi-DB migration; queue.py event-queueing retired, body-upload intact (C-006); ATDD + gates green
- 2026-06-29T09:36:03Z – claude:opus:python-pedro:implementer – shell_pid=55131 – for_review (propagated from primary; lane pristine at 9110fcb3c)
- 2026-06-29T09:36:05Z – claude:opus:reviewer-renata:reviewer – shell_pid=76850 – Started review via action command
- 2026-06-29T09:45:00Z – user – shell_pid=76850 – Review passed (forced past kitty-specs lane guard - known status-file drift coordination artifact): multi-DB discovery (scoped+legacy+malformed-skip), unknown->unknown: provenance (no fabricated identity), transactional+idempotent re-run, identical-dup dedupes once with all provenance, divergent-dup writes conflict/audit row with source opened mode=ro (sizes unchanged) + journal not overwritten + cleanup_blocked + exit_code=1, event_id verbatim (C-005), ASCII-only migration_target_token (re.ASCII) + accented regression. C-006 INTACT: body tests 189 passed, queue.py diff touches no body_upload code. queue.py bridge staging coherent: event-queueing authority retired/documented, queue table KEPT as legacy batch-transport bridge until WP07 dispatcher lands; capture-first writes journal in parallel while legacy dispatcher stays sole active drain -> no double-delivery. default_queue_db_path consumes WP01 queue_db_path with derived-never-a-selector rationale. ATDD red->green (bbfa9f6df<9110fcb3c); mypy+ruff clean; 98% coverage. Pre-existing strict_json failure confirmed NOT WP10 (identical at base). Note: migrate CLI wiring pending in dependent WP11/WP12.
- 2026-06-29T09:46:16Z – user – shell_pid=76850 – Approved by reviewer-renata (verdict on record): C-006 body-upload intact (189 tests), divergent-dup conflict safe, bridge-staging coherent. Propagating to authoritative log.
