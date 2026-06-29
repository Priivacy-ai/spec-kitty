---
work_package_id: WP05
title: Delivery Ledger
dependencies:
- WP04
requirement_refs:
- FR-002
- FR-004
- FR-015
tracker_refs: []
planning_base_branch: mission/event-sync-retention-delivery
merge_target_branch: mission/event-sync-retention-delivery
branch_strategy: Planning artifacts for this mission were generated on mission/event-sync-retention-delivery. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/event-sync-retention-delivery unless the human explicitly redirects the landing branch.
subtasks:
- T026
- T027
- T028
- T029
- T030
- T031
- T032
phase: Phase 3 - Delivery domain
assignee: ''
agent: "claude:opus:python-pedro:implementer"
shell_pid: "50697"
history:
- at: '2026-06-29T06:21:37Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/delivery/ledger.py
create_intent:
- src/specify_cli/delivery/ledger.py
- tests/delivery/test_ledger.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/delivery/ledger.py
- tests/delivery/test_ledger.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP05 – Delivery Ledger

## ⚡ Do This First: Load Agent Profile
Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter and behave per its guidance before parsing the rest of this prompt.
- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`
If no profile is specified, run `spec-kitty agent profile list` and select the best match for this WP's `task_type` and `authoritative_surface`.

---

## Objectives & Success Criteria

This WP delivers plan concern **IC-04 (Delivery Ledger)** and folds in two deferred concerns so downstream WPs consume them without re-owning `ledger.py`:
- **IC-05a — the terminal-failed STATE** (the storage half of FR-015; the *selection-exclusion* half is consumed by WP07).
- **IC-02a — the delivered-anywhere QUERY** (the ledger half; the coalescing logic that calls it is WP08).

The Delivery Ledger is the per-event/per-target state surface that answers "was event X delivered to target Y, when, with what result?" (**FR-002**). It is the single authority for which events still need draining (**FR-004**) and which are permanently parked (**FR-015**).

When this WP is complete:

- `delivery/ledger.py` defines a per-`(event_id, target_id)` ledger table with primary key `(event_id, target_id)`, shaped to grow to **many targets without a schema break** (**C-003**).
- Every delivery outcome maps to a ledger state: terminal-success (`success`/`duplicate`), `pending`, `rejected`, `failed_transient`, and `terminal_failed`. None of these delete the journal event (the journal is WP03's domain — **FR-001** boundary).
- A **selection query** returns events lacking a terminal-successful delivery for the active target, **excluding terminal-failed** (so an oversized event parks and the drain still progresses) — this is exactly what the WP07 dispatcher calls (**FR-004**).
- A **delivered-anywhere query** answers "does event X have ANY terminal delivery to ANY target?" — consumed by WP08 to enforce coalescing immutability.
- Re-recording an already-successful `(event_id, target_id)` yields `duplicate` with no corruption and unchanged event IDs (**NFR-003**).

**Acceptance criteria satisfied**: FR-002, FR-004, FR-015; C-003; NFR-003. Honors contract **§3 (Journal And Ledger)**. Tests assert observable ledger/on-disk state, not internal call order (**NFR-001**); they cover the full outcome matrix per **NFR-002**.

## Context & Constraints

**Prerequisite WP (`dependencies: ["WP04"]`)** — WP04 stands up the `src/specify_cli/delivery/` package, `delivery/__init__.py`, `delivery/interfaces.py` (the `DeliveryLedger` Protocol stub you implement here), and `delivery/targets.py` (the Delivery Target Registry). From WP04 you get:
- `delivery/targets.py` → the `target_id` your ledger rows reference. Target identity is `(url_hash, team_slug, user_email)`; the ledger keys on the surrogate `target_id`, so target identity changes are WP04's concern, not yours.
- `delivery/interfaces.py` → the `DeliveryLedger` Protocol whose method signatures (selection, record, `delivered_anywhere`) you must satisfy so WP07/WP08 bind to the abstraction (**C-001** seam).

**Reference docs** (read for detail, do not summarize back):
- `kitty-specs/event-sync-retention-delivery-01KVYWRG/spec.md` — FR-002, FR-004, FR-015; NFR-002, NFR-003; C-003; Key Entities → *Delivery Ledger*; "Content rejection vs transient failure" edge case.
- `kitty-specs/event-sync-retention-delivery-01KVYWRG/plan.md` — IC-04, IC-04a, IC-05 (the dispatcher that consumes your selection query), IC-05a (terminal-failed), IC-02a (delivered-anywhere).
- `kitty-specs/event-sync-retention-delivery-01KVYWRG/contracts/event-sync-delivery-contract.md` — **§3 (Journal And Ledger)** is the binding boundary for this WP; §4 (DeliveryReceiver result vocabulary your states must mirror).

**Architectural constraints to honor**:
- **Contract §3**: successful + duplicate delivery UPDATE `delivery_ledger`; they do NOT delete journal rows. Terminal-failed outcomes write a terminal-failed ledger state, are excluded from future automatic selection, stay inspectable, and require explicit operator action to retry. (The retry trigger itself is operator/CLI; the ledger only models the state.)
- **C-003 (single active target, ledger shaped for many)**: MVP delivers to one operator-selected target, but the per-`(event_id, target_id)` row shape and indexes must support many targets later **without a schema break**. Do not bake "one target" assumptions into the schema (e.g. no per-event single-status column that ignores target).
- **FR-001 boundary**: the ledger NEVER deletes a journal event. Deletion only ever happens via explicit `sync gc`/`sync archive` (WP11), and even then ledger history is preserved. The ledger has no delete-event path at all.
- **Result vocabulary alignment** (contract §4): the receiver maps a delivery to one of `success`, `duplicate`, `pending`, `rejected`, `terminal-failed`, `transient`. Your ledger statuses must be the durable representation of exactly that vocabulary.

**Out-of-map note**: no out-of-map edits expected. Both `owned_files` are new (`tests/delivery/__init__.py` may already exist from WP04; if absent, creating it is acceptable test scaffolding). Do NOT edit `delivery/targets.py`, `delivery/interfaces.py`, `delivery/dispatcher.py` (WP07), `event_journal/*` (WP03/WP08), `queue.py`, `tasks.md`, `spec.md`, `plan.md`, or `meta.json`.

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

## Subtasks & Detailed Guidance

### Subtask T026 [P] – Ledger schema: per-`(event_id, target_id)` row
- **Purpose**: Define the durable per-event/per-target state that answers FR-002's core question. The schema is the load-bearing artifact of the WP — get the columns and PK right and the queries fall out; get the shape wrong and C-003's "grow to many targets" needs a migration.
- **Steps**:
  1. In `src/specify_cli/delivery/ledger.py`, define a `delivery_ledger` SQLite table with columns:
     - `event_id` (text) — references the journal event; never rewritten (**C-005**, NFR-003).
     - `target_id` — references `delivery_targets.target_id` (WP04).
     - `status` — one of the ledger states (T027–T029): `success`, `duplicate`, `pending`, `rejected`, `failed_transient`, `terminal_failed`.
     - `attempt_count` (int) — incremented per delivery attempt.
     - `first_attempted_at`, `last_attempted_at`, `accepted_at`, `completed_at` — ISO-8601 UTC timestamps; nullable until the relevant transition.
     - `server_drain_state` — server-advertised drain state (e.g. `pending`); see T028.
     - `last_http_status` (int, nullable), `last_error` (text, nullable), `last_response_json` (text/JSON blob, nullable).
  2. **Primary key `(event_id, target_id)`** — one row per event per target. This is precisely the shape that supports many targets later (**C-003**): adding target B just adds rows keyed by B's `target_id`; no column change.
  3. Provide a small DAL: `open/init(conn_or_path)` to create the table+indexes idempotently, plus typed accessors. Keep the schema string a single module constant (Sonar S1192: don't repeat the DDL).
- **Files**: `src/specify_cli/delivery/ledger.py`.
- **Parallel?**: Yes `[P]` — schema definition is the WP's first subtask.
- **Validation**:
  - [ ] PK is `(event_id, target_id)`; a second row for the same pair is rejected/upserted (not duplicated).
  - [ ] Table init is idempotent (re-running `init` on an existing DB is a no-op).
  - [ ] No column assumes a single target (no global per-event status).
- **Edge cases**: schema must round-trip a row with all-nullable optional fields unset (a freshly-`pending` row).

### Subtask T027 – Record success/duplicate as terminal-success rows
- **Purpose**: Implement the FR-001 boundary made concrete (contract §3): a successful or duplicate delivery is a ledger UPDATE, never a journal delete. `success` and `duplicate` are both **terminal-success** — the event has reached the target.
- **Steps**:
  1. Add `record_success(event_id, target_id, *, http_status, response_json, at)` and `record_duplicate(...)` (or one `record_outcome` with the outcome enum). Both set `status` to a terminal-success value, set `completed_at`, bump `attempt_count`, and store `last_http_status`/`last_response_json`.
  2. Treat `success` and `duplicate` as equivalent for selection purposes (both mean "delivered to this target") while keeping them **distinct status values** so status reporting (WP11) can tell them apart and so re-delivery can return `duplicate` (NFR-003).
  3. **Never delete a journal event** — `ledger.py` has no path that touches `event_journal` rows. Recording a terminal success only writes/updates the ledger row.
- **Files**: `src/specify_cli/delivery/ledger.py`.
- **Parallel?**: No — depends on T026 schema.
- **Validation**:
  - [ ] Recording success updates the existing `(event_id, target_id)` row to a terminal-success status; the journal row count is unchanged (assert via a journal-count probe, not call order).
  - [ ] `duplicate` is recorded as a distinct status that selection treats as delivered.
- **Edge cases**: recording success for a row that was previously `failed_transient` must transition cleanly (a later attempt succeeded) and update timestamps.

### Subtask T028 – Record pending / rejected / failed_transient states
- **Purpose**: Model the non-terminal and content-rejection outcomes (contract §4 vocabulary; spec "Content rejection vs transient failure" edge case). These are the states the dispatcher records when a delivery is in flight, rejected per-event, or failed at the batch/transport level.
- **Steps**:
  1. `record_pending(event_id, target_id, *, server_drain_state='pending', at)` — sets `status='pending'` and `server_drain_state='pending'`, sets `accepted_at` if the server accepted-but-not-yet-drained.
  2. `record_rejected(event_id, target_id, *, http_status, error, at)` — a **per-event content rejection** records a failure state *without losing the payload* (the journal keeps it). Distinct from terminal-failed (T029): a rejection may be re-attemptable depending on policy; terminal-failed is permanent.
  3. `record_transient(event_id, target_id, *, http_status, error, at)` — a **batch-level transient failure** (401/403/5xx/timeout) bumps `attempt_count`/`last_attempted_at`/`last_error` *without poisoning per-event retry counts* in a way that conflates batch failure with per-event rejection. Keep per-event and batch-level metadata distinguishable.
  4. All three keep the event selectable for a future drain (they are NOT terminal); only terminal-success and terminal-failed leave the selection set.
- **Files**: `src/specify_cli/delivery/ledger.py`.
- **Parallel?**: No — depends on T026.
- **Validation**:
  - [ ] `pending`/`rejected`/`failed_transient` rows remain in the selection set (still draining).
  - [ ] A batch transient failure updates attempt metadata without flipping a per-event content rejection to terminal.
  - [ ] `server_drain_state='pending'` is stored and surfaced.
- **Edge cases**: a transient failure followed by a later success must transition the same row to terminal-success (not leave a stale `failed_transient`).

### Subtask T029 – Terminal-failed state (FR-015 storage)
- **Purpose**: Implement the IC-05a STATE half: a distinct ledger status for **permanent** failures (e.g. an oversized event the server will never accept). The payload is retained, never deleted; the event is parked, inspectable, and out of the automatic drain. (The *selection-exclusion* of this state is consumed by WP07's selection query, T030.)
- **Steps**:
  1. Add a `terminal_failed` status and `record_terminal_failed(event_id, target_id, *, http_status, error, at)`. It sets `status='terminal_failed'`, `completed_at`, and stores the failure detail (`last_http_status`/`last_error`/`last_response_json`).
  2. Terminal-failed is distinct from both terminal-success and the retryable failures (T028): it is permanent and excluded from future automatic selection (T030), but the **journal payload is retained** (contract §3) — never deleted, so it stays inspectable and operator-retryable.
  3. Provide a clear predicate (e.g. `is_terminal_failed(row)` or a status set) that T030's selection and WP11's terminal-failure count both reuse — single source of the "terminal" status set (avoid S1192 duplication).
- **Files**: `src/specify_cli/delivery/ledger.py`.
- **Parallel?**: No — depends on T026.
- **Validation**:
  - [ ] A `terminal_failed` row is excluded from the T030 selection set (drain progresses past it).
  - [ ] The journal payload for a terminal-failed event is NOT deleted (assert journal-count unchanged).
  - [ ] Terminal-failed is distinguishable from `failed_transient` and from `rejected`.
- **Edge cases**: oversized-event scenario is the canonical FR-015 case — model it explicitly so the dispatcher (WP07) and tests share it.

### Subtask T030 – Selection query: undelivered-for-target, excluding terminal-failed
- **Purpose**: This is the query WP07's dispatcher calls (**FR-004**): return the event IDs that *still need delivery* to the active target — i.e. those lacking a terminal-successful delivery for that target — **and excluding terminal-failed** so an oversized/permanent event does not loop the drain.
- **Steps**:
  1. Add `select_undelivered(target_id, *, event_universe) -> list[event_id]` (or a generator). "Undelivered for target" = no ledger row with terminal-success for `(event_id, target_id)` AND no `terminal_failed` row for `(event_id, target_id)`.
  2. The candidate universe is the journal's event IDs (passed in or queried via a narrow read interface) — the ledger answers "which of these lack terminal delivery to this target". Because identity is per-target, an event delivered to target A is still selectable for target B (this is what enables FR-005 re-drain, owned by WP07).
  3. Make the exclusion of terminal-failed explicit and tested — the plan's IC-05a risk note: "forgetting to exclude terminal-failed from the selector would loop the drain on an oversized event."
  4. Keep the function ≤15 complexity; if the SQL/Python branching grows, extract the "terminal status set" predicate (shared with T029/T031).
- **Files**: `src/specify_cli/delivery/ledger.py`.
- **Parallel?**: No — depends on T026–T029.
- **Validation**:
  - [ ] Event delivered (terminal-success) to target A is NOT selected for A, but IS selected for target B.
  - [ ] Terminal-failed event for target A is NOT selected for A (drain progresses).
  - [ ] `pending`/`rejected`/`failed_transient` events ARE selected (still draining).
- **Edge cases**: empty journal → empty selection; an event with a row for a *different* target only → still selectable for the active target.

### Subtask T031 – Delivered-anywhere query
- **Purpose**: Implement the IC-02a QUERY half: "does event X have ANY terminal delivery to ANY target?" WP08's coalescing consumes this to enforce delivered-event immutability — once delivered anywhere, the event is frozen and may not be coalesced/mutated.
- **Steps**:
  1. Add a clear public function `delivered_anywhere(event_id) -> bool` to `ledger.py`, matching the `DeliveryLedger` Protocol signature in WP04's `interfaces.py`.
  2. It returns `True` iff there exists at least one ledger row for `event_id` with a **terminal-success** status (`success` or `duplicate`) for any `target_id`. Decide and document whether `terminal_failed` counts as "delivered anywhere" for immutability purposes — per the coalescing intent (FR-011) the safe answer is that a *terminal delivery* (success/duplicate) freezes the event; align the predicate with WP08's needs and state the choice in the docstring. (Note: contract §3 says "Once delivered anywhere, payload bytes are immutable" — scope `delivered_anywhere` to terminal-success delivery and document it.)
  3. Expose it as a stable public symbol (re-exported via `delivery/__init__.py` is WP04's call; here just ensure the function name/signature match the Protocol so WP08 can import it cleanly).
- **Files**: `src/specify_cli/delivery/ledger.py`.
- **Parallel?**: No — depends on T026/T027.
- **Validation**:
  - [ ] `delivered_anywhere(event_id)` is `True` after a terminal-success to any target; `False` for an event with only `pending`/`rejected`/`failed_transient` rows.
  - [ ] Function signature matches the `DeliveryLedger` Protocol from WP04.
- **Edge cases**: an event with terminal success to target A and `pending` to target B → still "delivered anywhere" (`True`). Document the `terminal_failed` decision.

### Subtask T032 – Index design + tests in `tests/delivery/test_ledger.py`
- **Purpose**: Add the index that makes T030's selection index-assisted (plan: "no full-table rewrite per sync; selection is index-assisted on delivery state"), and lock the full outcome matrix and idempotent re-delivery as observable ledger state (**NFR-002**, **NFR-003**).
- **Steps**:
  1. **Index design**: add an index supporting the selection predicate — e.g. on `(target_id, status)` (and/or `(event_id, target_id, status)`) so "undelivered for target, excluding terminal-failed" is index-assisted, not a full scan. Document the index rationale inline. Keep `init` creating indexes idempotently.
  2. Create `tests/delivery/test_ledger.py`. Use a temp/in-memory SQLite ledger fixture (parallel-safe under `--dist loadfile`). Scenarios:
     - **state transitions**: record each of success / duplicate / pending / rejected / failed_transient / terminal_failed and assert the stored `status` + timestamps + attempt metadata (NFR-002 outcome coverage).
     - **selection**: after recording, assert `select_undelivered(target)` returns exactly the still-draining events, excludes terminal-success AND terminal-failed, and that an event delivered to A is selectable for B.
     - **delivered-anywhere**: assert `delivered_anywhere` flips `True` only on terminal-success to any target.
     - **idempotent re-delivery (NFR-003)**: recording a terminal success for an already-successful `(event_id, target_id)` yields `duplicate` handling with **no corruption** and the event IDs are **unchanged** — assert the row count and `event_id` values are stable.
     - **index present**: assert the selection-supporting index exists (query `sqlite_master`) so the index is part of the locked contract.
  3. Assertions read ledger/DB state and query return values — never internal call order (**NFR-001**).
- **Files**: `tests/delivery/test_ledger.py` (+ `tests/delivery/__init__.py` if not already present).
- **Parallel?**: Tests are file-scoped; safe under `--dist loadfile`.
- **Validation**:
  - [ ] All six outcome states exercised; selection and delivered-anywhere asserted on state.
  - [ ] Idempotent re-delivery yields `duplicate`, no row duplication, unchanged event IDs.
  - [ ] Selection-supporting index is asserted present.
- **Edge cases**: re-running the same record twice (idempotency); an event with mixed per-target states; empty-ledger selection.

## Test Strategy

- **Mandatory test file**: `tests/delivery/test_ledger.py` (owned). Coverage required by **NFR-002**: success, duplicate, pending, transient, rejection, terminal-failed; plus selection-exclusion of terminal-failed (FR-015/FR-004) and idempotent re-delivery (**NFR-003**).
- **Run**:
  ```bash
  PWHEADLESS=1 .venv/bin/pytest tests/delivery/test_ledger.py -q
  ```
  No real-port/daemon resources — collectable under `-n auto --dist loadfile`; no serial `-n0` pass needed for this file.
- **Fixtures/stubs**: temp/in-memory SQLite ledger; a tiny `target_id` factory (or a minimal WP04 target row) and a small set of `event_id`s standing in for journal rows. No HTTP, no real Teamspace, no receiver — receivers/dispatch are WP06/WP07. To assert "journal not deleted" without owning the journal, probe a passed-in event-id universe / count rather than importing WP03 internals.
- **Quality gates**: `.venv/bin/ruff check src/specify_cli/delivery/ledger.py tests/delivery/test_ledger.py` and `.venv/bin/mypy src/specify_cli/delivery/ledger.py` pass with zero issues. Keep `select_undelivered`, `record_*`, and `delivered_anywhere` each ≤15 complexity; share the "terminal status set" predicate (S1192).

## Risks & Mitigations

- **Index design driving dispatcher performance** (plan IC-04 risk): mitigated by T032's explicit `(target_id, status)` index and an assertion that it exists, so selection stays index-assisted and the plan's "no full-table rewrite per sync" goal holds.
- **Looping the drain on an oversized event** (plan IC-05a risk): mitigated by T030 explicitly excluding `terminal_failed` from selection, with a dedicated test that the drain progresses past it.
- **Single-target assumptions baked into schema** (C-003): mitigated by the per-`(event_id, target_id)` PK and per-target rows — adding target B is data, not schema.
- **Conflating batch-transient with per-event rejection** (spec edge case): mitigated by T028 keeping batch-level and per-event metadata distinguishable so a 5xx batch failure does not poison per-event retry state.
- **Deleting a journal event** (FR-001): mitigated by `ledger.py` having no journal-delete path at all; tests assert journal counts are unchanged on every record.

## Review Guidance

A reviewer running `/spec-kitty.review` must verify (tie to contract §3 "Required tests"):
- PK is `(event_id, target_id)` and the schema grows to many targets without a column change (**C-003**).
- Success/duplicate UPDATE the ledger and do NOT delete journal rows (**FR-001** boundary; contract §3).
- Terminal-failed is a distinct, retained, inspectable state EXCLUDED from selection (**FR-015**); the selection query returns undelivered-for-target and an A-delivered event is still selectable for B (**FR-004**, re-drain precursor).
- `delivered_anywhere(event_id)` is a clear public function matching the WP04 Protocol and is correct for the immutability use (consumed by WP08; **FR-011** precursor).
- A selection-supporting index exists; the full outcome matrix and idempotent re-delivery (`duplicate`, no corruption, unchanged event IDs — **NFR-003**) are tested as observable ledger state (**NFR-001/NFR-002**).

## Activity Log
> Entries chronological, appended at END. Format: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <action>`
- 2026-06-29T06:21:37Z – system – Prompt created.
- 2026-06-29T08:26:52Z – claude:opus:python-pedro:implementer – shell_pid=50697 – Assigned agent via action command
