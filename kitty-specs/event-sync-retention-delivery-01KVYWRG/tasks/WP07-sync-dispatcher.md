---
work_package_id: WP07
title: Sync Dispatcher
dependencies:
- WP03
- WP05
- WP06
requirement_refs:
- FR-001
- FR-004
- FR-005
- FR-015
tracker_refs: []
planning_base_branch: mission/event-sync-retention-delivery
merge_target_branch: mission/event-sync-retention-delivery
branch_strategy: Planning artifacts for this mission were generated on mission/event-sync-retention-delivery. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/event-sync-retention-delivery unless the human explicitly redirects the landing branch.
subtasks:
- T039
- T040
- T041
- T042
- T043
- T044
- T045
phase: Phase 4 - Dispatch
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "77949"
history:
- at: '2026-06-29T06:21:37Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/delivery/dispatcher.py
create_intent:
- src/specify_cli/delivery/dispatcher.py
- tests/delivery/test_dispatcher.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/delivery/dispatcher.py
- tests/delivery/test_dispatcher.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP07 – Sync Dispatcher

## ⚡ Do This First: Load Agent Profile
Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter and behave per its guidance before parsing the rest of this prompt.
- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`
If no profile is specified, run `spec-kitty agent profile list` and select the best match for this WP's `task_type` and `authoritative_surface`.

---

## Objectives & Success Criteria

This WP implements plan concern **IC-05 (Sync Dispatcher)** plus the selection-exclusion half of **IC-05a (terminal-failed state machine)**. It is the seam where the mission's central behavioral shift becomes observable: **a successful upload stops deleting the local event and instead becomes a ledger update**.

The dispatcher's job is the classic three-phase loop, expressed against the journal + ledger + receiver surfaces stood up by WP03/WP05/WP06:

1. **Select** — pull journal events that lack terminal delivery for the *active* target, excluding terminal-failed rows.
2. **Post** — hand the selected events to the active target's `DeliveryReceiver` (one path for Teamspace / external / stub).
3. **Record** — map each receiver result back to a `delivery_ledger` row; **never delete a journal row**.

Complete when:

- **FR-001 (non-destructive success)** — `success`/`duplicate` outcomes write/update terminal-success ledger rows; the journal payload is never deleted. Verified by an on-disk assertion in `tests/delivery/test_dispatcher.py`.
- **FR-004 (select undelivered-for-target)** — a `sync now` drain posts only events that have no terminal-successful delivery for the active target; already-delivered events are skipped (US1 acceptance scenario 2).
- **FR-005 (re-drain to a new target)** — switching the active target re-selects the same retained events for the new target and delivers them again (US1 acceptance scenario 1; SC-001).
- **FR-015 (terminal-failed handling)** — a `failed_permanent` receiver result writes a terminal-failed ledger state, is excluded from future automatic selection, and stays inspectable; the drain progresses past the oversized event instead of stalling (contract §3; plan IC-05a; SC-007).
- The select/post/record phases each stay at cyclomatic complexity ≤ 15 (ruff `C901` / Sonar `S3776`).
- Tests assert observable CLI output + on-disk/ledger state, **not internal call order** (NFR-001).

## Context & Constraints

**Prerequisite WPs and what they hand you:**

- **WP03 — Event Journal** (`src/specify_cli/event_journal/journal.py`): the append-only payload store keyed by `event_id`. The dispatcher reads candidate events from here and **must not delete from it** during a normal `sync now` (contract §3). Capture-first gating already happened upstream; by the time the dispatcher runs, the events are durable.
- **WP05 — Delivery Ledger** (`src/specify_cli/delivery/ledger.py`): exposes the **selection query** (`undelivered-for-target, excluding terminal-failed`, subtask T030) and the per-outcome state writers (`success`/`duplicate` → terminal-success, `pending`/`rejected`/`failed_transient` → ledger state, terminal-failed → FR-015 state, subtasks T027–T029). The dispatcher consumes these; it does **not** re-implement state transitions. Treat the ledger as the authority for "was X delivered to Y?".
- **WP06 — DeliveryReceiver contract** (`src/specify_cli/delivery/receivers.py`): the single `DeliveryReceiver` protocol (endpoint / auth / per-event result map / retry / gates). The dispatcher depends on this **contract**, never on target-specific conditionals (contract §4). The active receiver is resolved for you (Teamspace, external, or stub) — the dispatcher posts through whichever one is active.

**The behavior being replaced.** Today `SyncQueue.process_batch_results` (`src/specify_cli/sync/queue.py:1668`) treats `success` / `duplicate` / `failed_permanent` identically — **all three DELETE the local row** (documented in its own docstring at `queue.py:1671-1675`). `pending` → no mutation; `rejected` → `retry_count + 1`; `failed_transient` → no mutation. The dispatcher in this WP is the **non-destructive replacement** for the success/duplicate/failed_permanent path: those three stop deleting and become ledger writes. The `pending`/`rejected`/`failed_transient` semantics are already aligned with what we want (no destruction) — the dispatcher mirrors them as ledger state, not as queue mutations. The `queue.py` event-queueing retirement itself is owned by **WP10** — do not edit `queue.py` here; coordinate only.

**Links:**

- `kitty-specs/event-sync-retention-delivery-01KVYWRG/spec.md` — FR-001, FR-004, FR-005, FR-015; US1; edge case "Content rejection vs transient failure".
- `kitty-specs/event-sync-retention-delivery-01KVYWRG/plan.md` — IC-05, IC-05a; Charter Check note on the complexity ceiling.
- `kitty-specs/event-sync-retention-delivery-01KVYWRG/contracts/event-sync-delivery-contract.md` — §3 (Journal And Ledger) and §4 (DeliveryReceiver) are the binding observable behaviors for this WP.

**Architectural constraints to honor:**

- **C-001 (separate domain)** — all dispatcher logic lands in `src/specify_cli/delivery/dispatcher.py`. Do not weave event-delivery logic back into `sync/queue.py` or `src/specify_cli/events/`.
- **C-003 (single active target)** — the dispatcher delivers to exactly one operator-selected active target; **no automatic fan-out**. The selection and recording must remain per-event/per-target shaped so a future many-targets version needs no schema break, but this WP delivers to one target per drain.
- **Contract §3** — never delete journal rows on success/duplicate/terminal-failed; `sync gc`/`sync archive` (WP11) are the only destructive payload operations.
- **NFR-001** — tests assert observable state, not call order.

> **Out-of-map note**: this WP owns only `delivery/dispatcher.py` and its test file. The active-target resolution comes from WP01/WP04 surfaces and the receiver from WP06; consume them, do not duplicate them. If a needed selection/state helper is missing from the WP05 ledger surface, file an upstream gap rather than inlining ledger SQL in the dispatcher.

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

### Subtask T039 – Select phase: resolve active target, pull undelivered events excluding terminal-failed
- **Purpose**: Implement the first dispatcher phase. Resolve the *active* delivery target (from WP01 target authority / WP04 registry), then pull from the WP05 ledger selection query every journal event that lacks a terminal delivery for that target — **excluding terminal-failed rows**. This satisfies FR-004 (select undelivered-for-target) and the IC-05a selection-exclusion (FR-015). `[P]` — this phase is independent of the post/record phases and can be authored first.
- **Steps**:
  1. In `src/specify_cli/delivery/dispatcher.py`, add a `_select_pending(ledger, target, *, limit=None) -> list[Event]` helper (or equivalent) that delegates to the WP05 selection query (T030: "undelivered-for-target, excluding terminal-failed"). Do **not** write the SQL here — call the ledger surface.
  2. Resolve the active target identity (canonical URL + user/team scope) via the WP04 registry, seeded from the WP01 `ResolvedSyncTarget`. The target identity is the key the selection query filters on.
  3. Return journal `Event` records (payload bytes + `event_id`), in a deterministic order (e.g. journal insertion order) so re-runs are reproducible.
  4. If no active target is resolvable, the dispatcher returns a no-op result (nothing to drain) — it does **not** raise; status surfaces report "no active target".
- **Files**: `src/specify_cli/delivery/dispatcher.py`.
- **Parallel?**: Yes (`[P]`) — pure selection logic; no post/record coupling.
- **Validation**:
  - [ ] Selection returns only events with no terminal-successful row for the active target.
  - [ ] Terminal-failed events for the active target are excluded (FR-015 / IC-05a).
  - [ ] Already-successful events for the active target are excluded (FR-004; US1 scenario 2).
  - [ ] No `queue.py` import; selection goes through the WP05 ledger surface only.
- **Edge cases**: an event delivered to target A but never to the now-active target B is **selected** (this is the FR-005 re-drain path). An event with a `pending` (not terminal) ledger row for the active target is still selectable on the next tick (it has no *terminal* delivery yet).

### Subtask T040 – Post phase: deliver via the active target's `DeliveryReceiver`
- **Purpose**: Hand the selected events to the active target's `DeliveryReceiver` (WP06) — one dispatch path that works for Teamspace, external, and stub receivers. This is where the dispatcher's dependency on the **contract** (not on target-specific branching) is enforced (contract §4; FR-014 is owned by WP06 but the dispatcher must consume it correctly).
- **Steps**:
  1. Add `_post(receiver, events) -> list[DeliveryResult]` (or equivalent) that calls the receiver's batch/post method per the `DeliveryReceiver` protocol. The dispatcher does not know which concrete receiver it holds.
  2. Pass the selected `Event` payloads through; the receiver maps each event to one of `success` / `duplicate` / `pending` / `rejected` / `terminal-failed` / `transient` (the receiver owns the mapping; contract §4 result column).
  3. A batch-level transient failure (401/403/5xx/timeout) surfaces as a transient outcome for the affected events — the dispatcher records attempt metadata (T041) but does not poison per-event retry counts (spec edge case "Content rejection vs transient failure").
  4. **No conditional on receiver type** in the dispatcher. If you find yourself writing `if isinstance(receiver, TeamspaceReceiver)`, the gate/branch belongs in the receiver (WP06), not here.
- **Files**: `src/specify_cli/delivery/dispatcher.py`.
- **Parallel?**: No — consumes the selection from T039.
- **Validation**:
  - [ ] One post path drives Teamspace / external / stub equivalently (verified via the stub in tests).
  - [ ] Batch-level transient failure does not advance per-event content-rejection counters.
  - [ ] No target-type conditional in the dispatcher (gates live in the receiver).
- **Edge cases**: an empty selection short-circuits (no receiver call). A receiver that is gated off (e.g. Teamspace with SaaS disabled) is resolved by WP06/WP09 policy *before* the dispatcher runs — the dispatcher posts only through an active, eligible receiver.

### Subtask T041 – Record phase: map receiver results to ledger updates, never delete the journal
- **Purpose**: Map each receiver result to a `delivery_ledger` update via the WP05 state writers. `success`/`duplicate` → **terminal-success** ledger rows; `pending`/`rejected`/`failed_transient` → their already-aligned ledger states. **Never delete a journal event** (FR-001; contract §3). This is the phase that replaces the destructive `process_batch_results` success/duplicate path.
- **Steps**:
  1. Add `_record(ledger, target, results) -> DispatchSummary` (or equivalent) that, for each result, calls the matching WP05 ledger writer:
     - `success` / `duplicate` → terminal-success row for `(event_id, target)` (WP05 T027).
     - `pending` → pending ledger state, re-selectable next tick (WP05 T028).
     - `rejected` → rejection ledger state with the attempt/retry metadata (WP05 T028); a per-event content rejection, payload retained.
     - `failed_transient` → transient ledger state / attempt metadata update only (WP05 T028); no per-event retry-count poisoning.
  2. Build a `DispatchSummary` (counts per outcome: delivered, duplicate, pending, rejected, transient, terminal-failed) that the CLI (WP12) and status (WP11) can render. This is the dispatcher's observable output.
  3. Assert (in code, via the ledger contract) that **no journal delete** occurs in this phase. The journal is read-only to the dispatcher.
- **Files**: `src/specify_cli/delivery/dispatcher.py`.
- **Parallel?**: No — consumes the post results from T040.
- **Validation**:
  - [ ] `success`/`duplicate` produce terminal-success ledger rows (FR-001).
  - [ ] Journal row count is unchanged before vs after a drain (on-disk assertion).
  - [ ] `pending`/`rejected`/`failed_transient` produce the corresponding ledger states without deleting payloads.
  - [ ] `DispatchSummary` exposes per-outcome counts for CLI/status consumption.
- **Edge cases**: re-recording a `success` for an event already terminal-successful on this target is idempotent (NFR-003) — the WP05 writer treats it as a duplicate, no corruption, event ID unchanged.

### Subtask T042 – `failed_permanent` → terminal-failed ledger state (not a delete, not a success)
- **Purpose**: Wire the IC-05a terminal-failed branch. A `failed_permanent` receiver result (e.g. an oversized event the server will never accept) must become a **terminal-failed ledger state** — **NOT a delete** (the old `queue.py` behavior) and **NOT a success**. Terminal-failed rows are excluded from future automatic selection (closing the loop with T039) so the drain progresses past the oversized event, yet the payload stays retained and inspectable (FR-015; plan IC-05a; contract §3; SC-007).
- **Steps**:
  1. In `_record` (T041), route `failed_permanent` / `terminal-failed` receiver results to the WP05 terminal-failed writer (T029) for `(event_id, target)`.
  2. Confirm the T039 selection query excludes terminal-failed for the active target (it does, via WP05 T030) — the dispatcher does not need to re-filter, but a test must prove the next drain skips the oversized event.
  3. Add the terminal-failed count to `DispatchSummary` so status/CLI can show "N terminal-failed" distinctly from delivered/failed-transient.
  4. Document inline why terminal-failed is *not* a delete: the old DELETE achieved drain progress by destroying the payload; we achieve the same progress by selector-exclusion while keeping the payload (FR-015 rationale).
- **Files**: `src/specify_cli/delivery/dispatcher.py`.
- **Parallel?**: No — extends the record phase (T041).
- **Validation**:
  - [ ] An oversized/permanent failure writes a terminal-failed ledger row, not a delete and not a success.
  - [ ] The next `sync now` against the same target does **not** re-select the terminal-failed event (drain progresses — the original bug the old DELETE solved is preserved without destruction).
  - [ ] The terminal-failed payload remains in the journal and is inspectable.
  - [ ] Terminal-failed count appears in `DispatchSummary`.
- **Edge cases**: a single oversized event mixed into a batch of deliverable events must not block the deliverable ones — the deliverable events get terminal-success rows and the oversized one a terminal-failed row in the same drain. Retry of a terminal-failed event happens only via explicit operator action (out of scope here; the dispatcher never auto-retries it).

### Subtask T043 – Re-drain to a new target (FR-005)
- **Purpose**: Prove the central US1 capability — switching the active delivery target re-selects the **same retained events** for the new target and delivers them again, with zero manual SQLite copying (FR-005; SC-001; US1 acceptance scenario 1).
- **Steps**:
  1. No new selection logic is needed if T039 keyed selection on the *active target* — re-drain falls out naturally: after switching to target B, the same N journal events have no terminal-success row for B, so they are re-selected.
  2. Add an integration-style path (exercised by T045 tests) that runs `dispatch` against target A, then against target B, asserting B receives all N events and the journal still holds all N (retention preserved).
  3. Ensure the dispatcher reads the *current* active target each invocation (no caching of a stale target between drains) — this is what makes `sync server <B>` followed by `sync now` deliver to B.
- **Files**: `src/specify_cli/delivery/dispatcher.py`.
- **Parallel?**: No — depends on T039/T040/T041 being in place.
- **Validation**:
  - [ ] After A then B, target B received all N events (SC-001).
  - [ ] All N events remain retained in the journal after both drains (FR-001 / SC-002).
  - [ ] A second drain against A skips the already-successful events (US1 scenario 2).
- **Edge cases**: target B may be a brand-new target with no ledger rows yet — selection treats "no row for B" as undelivered. An event terminal-failed on A is still selectable for B (terminal-failed is per-target).

### Subtask T044 – Complexity discipline: keep select/post/record each ≤ 15
- **Purpose**: Honor the plan's Charter Check (complexity ceiling 15; ruff `C901` / Sonar `S3776`). The dispatcher is explicitly flagged in IC-05 as an at-risk function. Keep the three phases as separate, small helpers so the public `dispatch()` entry point stays a thin orchestrator.
- **Steps**:
  1. Structure `dispatcher.py` as a thin `dispatch(...)` that calls `_select_pending`, `_post`, `_record` in sequence and assembles the `DispatchSummary`.
  2. Keep each helper's cyclomatic complexity ≤ 15 — extract sub-helpers (e.g. result-to-ledger-state mapping as a small lookup table) rather than nesting conditionals.
  3. Prefer a result→writer dispatch table over an `if/elif` ladder for the six outcome kinds (this both lowers complexity and reads clearly).
  4. Run `.venv/bin/ruff check src/specify_cli/delivery/dispatcher.py` and confirm zero `C901` (and zero other) findings; fix the code, never suppress.
- **Files**: `src/specify_cli/delivery/dispatcher.py`.
- **Parallel?**: No — structural concern across all phases.
- **Validation**:
  - [ ] `ruff check` reports zero issues (no `C901`, no warnings) on `dispatcher.py`.
  - [ ] `mypy` reports zero issues on `dispatcher.py`.
  - [ ] No new `# noqa` / `# type: ignore` / per-file ignore added.
  - [ ] Each of select/post/record is independently readable and testable.
- **Edge cases**: if the outcome-mapping table itself grows, keep it a module-level constant (Sonar `S1192` — hoist repeated literals) rather than rebuilding it per call.

### Subtask T045 – Tests in `tests/delivery/test_dispatcher.py`
- **Purpose**: Cover US1 plus the contract §3 "Required tests" with observable on-disk/ledger assertions (NFR-001). A single happy-path drain is insufficient — the A→B replay, the re-sync skip, and the oversized-progress cases are mandatory.
- **Steps**: Author `tests/delivery/test_dispatcher.py` with at least these scenarios, each asserting observable state (journal rows, ledger rows, receiver-recorded events), never call order:
  1. **A→B replay (FR-005 / SC-001, contract §3 row 1)**: produce N events; dispatch to target A (stub receiver) — assert N delivered to A and N still in the journal; switch active target to B; dispatch — assert the same N delivered to B **and** still N retained in the journal.
  2. **Re-sync skips already-successful (FR-004, contract §3 row 2)**: dispatch to A twice — the second drain selects 0 events (all terminal-successful for A) and posts nothing.
  3. **Non-destructive success (FR-001)**: assert journal row count is identical before and after a successful drain; assert a terminal-success ledger row exists for each delivered `(event_id, target)`.
  4. **Oversized / permanent failure progresses the drain (FR-015 / IC-05a, contract §3 row 4)**: a batch with one oversized event mapped to `terminal-failed` by the stub — assert the deliverable events get terminal-success, the oversized event gets a terminal-failed ledger row (not deleted, not success), it remains in the journal/inspectable, and the next drain does not re-select it.
  5. **Idempotent re-delivery (NFR-003)**: re-dispatch the same events to A → `duplicate` outcomes, no corruption, event IDs unchanged.
- **Files**: `tests/delivery/test_dispatcher.py`.
- **Parallel?**: No — depends on all prior subtasks.
- **Validation**:
  - [ ] All five scenarios present and asserting on-disk/ledger state, not call order (NFR-001).
  - [ ] Tests use the WP06 **stub receiver** (no Teamspace credentials) — SC-005 alignment.
  - [ ] `PWHEADLESS=1 .venv/bin/pytest tests/delivery/test_dispatcher.py -q` passes.
- **Edge cases**: assert journal immutability explicitly (byte count or row count before/after); assert the terminal-failed event is queryable through the ledger after the drain (inspectable, FR-015).

## Test Strategy

- **Mandatory test file**: `tests/delivery/test_dispatcher.py` (in `owned_files`).
- **Command**: `PWHEADLESS=1 .venv/bin/pytest tests/delivery/test_dispatcher.py -q`. These are pure unit/integration tests over the journal + ledger + stub receiver — they do **not** bind a real port or a daemon, so they run fine under the default parallel run (`-n auto --dist loadfile`). No `-n0` serial pass is needed for this WP.
- **Fixtures/stubs**: use the WP06 **stub receiver** as the active target — it implements the same `DeliveryReceiver` contract, accepts/records events, and lets the suite (and fork CI) run with **no Teamspace credentials** (SC-005). Build small fixtures that seed the WP03 journal with N events and a WP05 ledger so the dispatcher has real surfaces to drive.
- **Observable-state discipline (NFR-001)**: assert journal row counts, ledger rows for `(event_id, target)`, the per-outcome `DispatchSummary`, and what the stub receiver recorded. Do **not** assert that `_select`→`_post`→`_record` were called in a particular order or with particular mocks.
- Run `.venv/bin/ruff check` and `.venv/bin/mypy` on `dispatcher.py` before review — zero issues required.

## Risks & Mitigations

- **Looping the drain on an oversized event (IC-05a risk)** — if terminal-failed is not excluded from selection, every drain re-posts the oversized event forever. *Mitigation*: T042 routes `failed_permanent` to the WP05 terminal-failed state, and T039 selection excludes it; T045 asserts the next drain skips it.
- **Complexity ceiling (IC-05 risk)** — the dispatcher tends to grow into one big function. *Mitigation*: T044 splits select/post/record into ≤15-complexity helpers and uses a result→writer lookup table.
- **Re-introducing destruction** — accidentally deleting the journal row on success would silently re-break the mission. *Mitigation*: T041 keeps the journal read-only to the dispatcher; T045 asserts journal row count is unchanged across a drain.
- **Leaking target-type conditionals into the dispatcher (contract §4)** — would make the dispatcher know about Teamspace/external/stub. *Mitigation*: post only through the `DeliveryReceiver` contract; T040 validation forbids `isinstance` branching.
- **Split-brain target** — delivering to a target the queue scope did not key on. *Mitigation*: resolve the active target from WP01/WP04 each invocation; never cache a stale target between drains (T043).

## Review Guidance

For `/spec-kitty.review`, verify against the contract's §3 "Required tests" and §4:

- [ ] **FR-001**: a successful drain leaves the journal row count unchanged and writes a terminal-success ledger row (no DELETE; the `queue.py:1668` destructive behavior is gone from this path).
- [ ] **FR-004**: a re-sync against the same target selects only undelivered events (already-successful are skipped).
- [ ] **FR-005 / SC-001**: A→B replay delivers the same retained events to B with no manual SQLite copy and full retention preserved.
- [ ] **FR-015 / IC-05a / SC-007**: an oversized event becomes terminal-failed, is excluded from future selection (drain progresses), and remains inspectable — not deleted, not success.
- [ ] The dispatcher depends on the `DeliveryReceiver` contract, with **no** target-type conditionals (contract §4).
- [ ] select/post/record each ≤15 complexity; `ruff` and `mypy` clean; no new suppressions.
- [ ] Tests assert observable on-disk/ledger state, not call order (NFR-001), and run against the stub receiver with no Teamspace credentials (SC-005).

## Activity Log
> Entries chronological, appended at END. Format: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <action>`
- 2026-06-29T06:21:37Z – system – Prompt created.
- 2026-06-29T09:25:03Z – claude:opus:python-pedro:implementer – shell_pid=74373 – Assigned agent via action command
- 2026-06-29T09:39:18Z – claude:opus:python-pedro:implementer – shell_pid=74373 – for_review (propagate; lane pristine at befc1f36a)
- 2026-06-29T09:39:34Z – claude:opus:reviewer-renata:reviewer – shell_pid=77949 – Started review via action command
- 2026-06-29T09:44:36Z – user – shell_pid=77949 – Review passed: select uses WP05 select_undelivered(target_id,event_universe,limit) with journal.read_all() universe (select_pending=0 in dispatcher); terminal-failed excluded. Post is one contract path (no target-type isinstance; the only isinstance is a Mapping payload-shape check). Record routes terminal_failed->record_terminal_failed (parked/retained/excluded), others->record_result; journal NEVER deleted (journal.count unchanged asserted). A->B replay test asserts real counts (3 to A retained, 3 to B retained). select/post/record each <=15 (ruff C901 clean). mypy/ruff clean, 100% cov, 119 delivery tests pass. ATDD red(184e10414)->green(befc1f36a) verified. D-020 coalesce import-guard SOUND: guarded importlib targets specify_cli.event_journal.coalesce.install; lane-h provides install(ledger:DeliveredAnywhereQuery) and SqliteDeliveryLedger satisfies it via delivered_anywhere, so it WILL activate at merge; degrades to no-op (returns False) in-lane so drain never breaks. VERIFY-POST-MERGE: grep for a live coalesce caller after all lanes combined.
