---
work_package_id: WP03
title: Event Journal (append-only) + capture-first
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-003
- FR-017
tracker_refs: []
planning_base_branch: mission/event-sync-retention-delivery
merge_target_branch: mission/event-sync-retention-delivery
branch_strategy: Planning artifacts for this mission were generated on mission/event-sync-retention-delivery. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/event-sync-retention-delivery unless the human explicitly redirects the landing branch.
subtasks:
- T013
- T014
- T015
- T016
- T017
- T018
- T019
phase: Phase 2 - Event Journal
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "38483"
history:
- at: '2026-06-29T06:21:37Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/event_journal/journal.py
create_intent:
- src/specify_cli/event_journal/__init__.py
- src/specify_cli/event_journal/models.py
- src/specify_cli/event_journal/journal.py
- tests/event_journal/test_journal.py
- tests/event_journal/test_capture_first.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/event_journal/__init__.py
- src/specify_cli/event_journal/models.py
- src/specify_cli/event_journal/journal.py
- src/specify_cli/sync/emitter.py
- src/specify_cli/sync/runtime_event_emitter.py
- tests/event_journal/test_journal.py
- tests/event_journal/test_capture_first.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP03 – Event Journal (append-only) + capture-first

## ⚡ Do This First: Load Agent Profile
Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter and behave per its guidance before parsing the rest of this prompt.
- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`
If no profile is specified, run `spec-kitty agent profile list` and select the best match for this WP's `task_type` and `authoritative_surface`.

---

## Objectives & Success Criteria

Stand up the **new `event_journal/` core domain** — a durable, append-only, producer-scoped
local payload store that does **not** know delivery state — and wire **capture-first** into the
emit layer so a Teamspace-bound fact is written to the journal *before* any SaaS/auth/team/
Private-Teamspace/network gate is evaluated. This WP realises plan **IC-01 (partial)** +
**IC-02**. It deliberately does **not** implement coalescing: it builds a *seam* (a no-op
strategy hook) that **WP08** fills once the delivery ledger exists (plan IC-02a).

This WP is complete when:

- **FR-003** (target-independent journal): events are retained in `event_journal` independent of
  any delivery target; the journal has no concept of a server, queue scope, or delivery state.
- **FR-001** (non-destructive): the journal never deletes a payload during normal `sync now`
  (contract §3 first bullet). Deletion is only ever an explicit `gc`/`archive` operation owned by
  another WP (WP11) — this WP must not expose any normal-path delete.
- **FR-017** (capture-first durability): Teamspace-bound facts are written to SQLite **before**
  auth/team/sync/network gates decide whether delivery may proceed (contract §2).
- **C-008** (no silent Teamspace-bound discard): a Teamspace-bound family is never silently
  dropped; the journal write always happens for those families (full OPT_OUT policy is WP09).
- **SC-009**: with SaaS sync disabled, missing auth/team, or a Private-Teamspace gate failure,
  Teamspace-bound events are still captured locally with a drain-blocked/audit reason and are
  deliverable after the blocker clears.
- The **no-coalescing invariant** holds: until WP08 registers a strategy, every produced event is
  a distinct journal row.

Observable acceptance (NFR-001 — tests assert on-disk state + diagnostics, **not** internal call
order): after producing N Teamspace-bound events with sync disabled, the on-disk journal contains
N distinct rows, each carrying a `drain_blocked_reason`, and no delivery was attempted.

## Context & Constraints

**Prerequisite WP — what WP01 hands you:**
- **WP01** (`src/specify_cli/sync/target_authority.py`) resolves the canonical
  `ResolvedSyncTarget` (contract §1): `resolved_server_url`, `user_id`, `team_slug`,
  `derived_queue_scope`, `queue_db_path`, `active_queue_scope_status`, etc. You consume this
  **only** to learn producer identity (`user_id` / `team_slug`) when known, so the journal can be
  producer-scoped. **The journal is producer-scoped (user|team / repo-local), NOT server-scoped.**
  Do not key the journal on `resolved_server_url` or `derived_queue_scope` — those belong to the
  delivery side (WP04/WP05). If identity is not yet known at capture time, the journal still
  writes (capture must not block on identity — FR-017).

**Links:**
- `kitty-specs/event-sync-retention-delivery-01KVYWRG/spec.md` — FR-001, FR-003, FR-017, C-008, SC-009.
- `kitty-specs/event-sync-retention-delivery-01KVYWRG/plan.md` — IC-01, IC-02 (and IC-02a deferral).
- `kitty-specs/event-sync-retention-delivery-01KVYWRG/contracts/event-sync-delivery-contract.md` — §2 (Capture Before Drain), §3 (Journal And Ledger).

**Architectural constraints to honor:**
- **C-001 (separate core domain)**: build the new domain at `src/specify_cli/event_journal/`.
  **Do NOT** reuse or extend `src/specify_cli/events/` (that package already owns event-log
  integration and decision-log surfaces) and **do NOT** add journal logic to
  `src/specify_cli/sync/queue.py`. New event-journal logic lives only in your `owned_files`.
- **Append-only, no coalescing yet** (plan IC-02): the journal records every produced event as a
  distinct row. Coalescing is deferred to WP08.
- **Producer-scoped, not server-scoped** (Key Entities — Event Journal): repo/install/session-
  local; producer identity attached when known; not blocked by auth/team/sync/network gates.
- **Capture before drain** (contract §2): the write precedes the gate evaluation, always.

**Out-of-map edits:** none. Every change lands in an `owned_files` path. You consume WP01's
`target_authority` as a read-only import — you do not edit it. The delivery ledger does not exist
yet; do **not** import from `delivery/` (it is owned by WP04/WP05 and may not exist on your base).

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

### Subtask T013 – Journal schema + Event record model
- **Purpose**: Define the on-disk SQLite schema and the in-memory `Event` record that the
  append-only store reads/writes. Backs FR-003 (target-independent journal) — the model carries
  **no** delivery/target field.
- **Steps**:
  1. In `src/specify_cli/event_journal/models.py`, define a frozen dataclass `Event` (or a
     `NamedTuple`) with exactly these fields: `event_id: str` (the producer's canonical id — never
     rewritten, per C-005), `event_type: str`, `payload: bytes` (raw serialized payload bytes),
     `occurred_at: str` (ISO-8601 UTC, when the fact happened at the producer), `created_at: str`
     (ISO-8601 UTC, when the row was written to the journal), `coalesce_key: str | None` (the
     grouping key WP08's strategy will read; the journal merely stores it), `archived_at: str |
     None` (set only by explicit archive in WP11; `None` for live rows).
  2. Add a `drain_blocked_reason: str | None` field carrying the capture-first audit reason
     (T017). Keep it on the model so a single read returns capture + block state.
  3. Define the SQLite DDL as a module constant in `models.py` (a single `CREATE TABLE IF NOT
     EXISTS event_journal (...)` with a `PRIMARY KEY(event_id)` and an index on
     `(coalesce_key, created_at)` to support WP08 and `(event_type, created_at)` for status). Hoist
     repeated column/SQL literals to named constants (Sonar S1192) if used ≥3×.
  4. Provide pure `row_to_event(row)` / `event_to_params(event)` helpers so journal.py never hand-
     codes column order. These are the deterministic, individually-testable extractions Sonar
     rewards.
- **Files**: `src/specify_cli/event_journal/models.py`; create `src/specify_cli/event_journal/__init__.py`
  exporting `Event` and the public journal API (see T014).
- **Parallel?**: `[P]` — schema/model has no dependency on the other subtasks' code.
- **Validation**:
  - [ ] `Event` is immutable and carries no `target`/`server`/`delivery` field (FR-003).
  - [ ] `event_id` is stored verbatim, never derived or rewritten (C-005).
  - [ ] DDL is idempotent (`IF NOT EXISTS`) and indices exist for coalesce + status reads.
  - [ ] `row_to_event` / `event_to_params` round-trip an `Event` losslessly (test in T019).
- **Edge cases**: `payload` may be empty bytes; `coalesce_key` may be `None`; timestamps must be
  timezone-aware UTC strings (no naive datetimes).

### Subtask T014 – Append-only journal store
- **Purpose**: Implement the authoritative surface `event_journal/journal.py`: a `record`/`append`
  API that writes events and **never deletes** during normal operation. Backs FR-001 and FR-003
  (contract §3 bullet 1).
- **Steps**:
  1. In `src/specify_cli/event_journal/journal.py`, implement an `EventJournal` class (or module-
     level functions over a `Path`) that opens/creates the SQLite DB at a **repo/install/session-
     local, producer-scoped** path. Resolve the base directory from the spec-kitty home; when WP01
     supplies a known `user_id`/`team_slug`, fold them into the journal filename/subdir as the
     producer scope. When identity is unknown, fall back to a producer-anonymous local path —
     capture must never block on identity (FR-017).
  2. Expose `append(event: Event) -> None` (and/or `record(...)`) that INSERTs a row. Use
     `INSERT OR IGNORE` keyed on `event_id` so a duplicate `event_id` is a no-op (idempotent
     capture) rather than a mutation — **never** UPDATE an existing payload here (that mutation is
     exactly the IC-02 risk). Re-appending the same `event_id` must leave stored bytes unchanged.
  3. Expose read helpers the rest of the mission needs without exposing delivery concepts:
     `read_all()`, `read_by_id(event_id)`, `count()`, `oldest_created_at()`. These power WP11
     status (`retained` count, oldest-retained timestamp) but the journal stays delivery-agnostic.
  4. **Do not** add any normal-path `delete`/`DELETE`/`purge` method. The only destructive
     operations (`gc`/`archive`) are owned by WP11; the journal may expose an `archived_at`
     mutation **only** via an explicit `mark_archived(event_id, at)` that sets the marker (no row
     removal) — keep it clearly named and out of the `append`/`record` path.
  5. Keep `append`/`record` under the complexity ceiling (≤15); extract the coalesce-seam call
     (T015) and the producer-scope path resolution into small helpers.
- **Files**: `src/specify_cli/event_journal/journal.py`, `src/specify_cli/event_journal/__init__.py`.
- **Parallel?**: depends on T013's model; sequential after it.
- **Validation**:
  - [ ] No normal-path delete exists; `sync now` can never remove a journal row (FR-001, contract §3).
  - [ ] Re-appending an existing `event_id` does not mutate stored bytes (idempotent capture).
  - [ ] Journal path is producer-scoped (user|team / repo-local), **never** server/URL-scoped.
  - [ ] Journal exposes no target/delivery field or method.
- **Edge cases**: concurrent writers (two processes on the same repo) — rely on SQLite WAL +
  `INSERT OR IGNORE` idempotency; do not crash on a duplicate. Corrupt DB → surface a clear error,
  do not silently swallow (avoid effect-free `except`).

### Subtask T015 – Coalescing seam (default no-op)
- **Purpose**: Build the **pluggable coalescing seam** so WP08 can register a real strategy
  **without editing `journal.py`**. Default behavior is no-op: every produced event is a distinct
  row (plan IC-02 — coalescing deferred to IC-02a/WP08). This is the explicit anti-spaghetti seam.
- **Steps**:
  1. Define a `CoalesceStrategy` protocol/callable type in `journal.py` (or `models.py`) with a
     signature like `coalesce(journal, event) -> CoalesceDecision` where the default returns
     "store as a new distinct row". The journal calls the registered strategy inside `append`;
     with the default no-op strategy it always proceeds to a plain INSERT.
  2. Provide a module-level registration API: `register_coalesce_strategy(strategy)` and
     `reset_coalesce_strategy()` (for test isolation). Store the active strategy in a module-level
     slot defaulting to the no-op. **This registration API is the only contract WP08 needs** — WP08
     calls `register_coalesce_strategy(...)` from `event_journal/coalesce.py` and never touches
     `journal.py`.
  3. Document in a docstring that the seam must hand the strategy enough to query "delivered
     anywhere?" later — but the journal itself must **not** import `delivery/` (it does not know
     delivery state, FR-003). WP08's strategy is what will consult the ledger; the journal just
     invokes the registered hook.
- **Files**: `src/specify_cli/event_journal/journal.py` (seam + registration API),
  `src/specify_cli/event_journal/__init__.py` (export the registration API).
- **Parallel?**: sequential after T014 (it hooks `append`).
- **Validation**:
  - [ ] With no strategy registered (default), every distinct produced event is a distinct row.
  - [ ] `register_coalesce_strategy` / `reset_coalesce_strategy` exist and are exported.
  - [ ] `journal.py` does **not** import anything from `src/specify_cli/delivery/` (FR-003, C-001).
  - [ ] WP08 can register a strategy with zero edits to `journal.py` (seam is sufficient).
- **Edge cases**: a registered strategy that raises must not corrupt the journal — fail the
  `append` loudly rather than partially writing; default path must remain trivially no-op.

### Subtask T016 – Capture-first gating at the emit layer
- **Purpose**: Make Teamspace-bound facts durable in the journal **before** the SaaS-enabled /
  auth / team / Private-Teamspace / network gates are evaluated (contract §2; FR-017). This is the
  core capture-first behavior.
- **Steps**:
  1. In `src/specify_cli/sync/emitter.py` and `src/specify_cli/sync/runtime_event_emitter.py`,
     locate every point where a Teamspace-bound fact is produced and currently gated by
     `SPEC_KITTY_ENABLE_SAAS_SYNC`, auth presence, team presence, Private-Teamspace, or network
     reachability. **Grep all callers** of the existing emit functions before editing (per global
     guidance) so no producer path is missed.
  2. Reorder so the flow is: build the `Event` → **`journal.append(event)`** → *then* evaluate the
     gates to decide drain eligibility. The journal write is unconditional for Teamspace-bound
     families; gates only decide whether/when delivery is attempted, never whether the write
     happens (contract §2 bullet 1–2).
  3. Where the emitter previously short-circuited (e.g. early-returned when sync was disabled),
     replace the early return with: write to journal, then record the blocked reason (T017), then
     return without delivering. The CLI/daemon path that was disabled now leaves a durable row.
  4. Keep the emitter thin: it constructs the `Event` and calls the journal + (later) the
     dispatcher. Delivery itself is WP07's dispatcher — do not implement delivery here.
- **Files**: `src/specify_cli/sync/emitter.py`, `src/specify_cli/sync/runtime_event_emitter.py`.
- **Parallel?**: sequential after T014 (needs the journal API).
- **Validation**:
  - [ ] With `SPEC_KITTY_ENABLE_SAAS_SYNC=0`, a Teamspace-bound fact is written to the journal
        (contract §2 bullet 1; SC-009).
  - [ ] With missing auth or missing team, the fact is still written (contract §2 bullet 1).
  - [ ] The journal write happens **before** the gate evaluation in every Teamspace-bound producer
        path (capture-first — FR-017).
  - [ ] No delivery/network call is made when a gate blocks; only the write + reason record happen.
- **Edge cases**: daemon-lock failure and network failure are "block delivery", not "skip write"
  (contract §2 bullet 1 lists both). A local-only / discardable family is out of scope for full
  OPT_OUT here (WP09) — but Teamspace-bound families always write (T018).

### Subtask T017 – Record `drain_blocked_reason` / audit state
- **Purpose**: When a gate blocks delivery, record *why* on the journal row so status (WP11) can
  show it and later delivery (WP07) can clear it. Block delivery only, never the write
  (contract §2 bullet 3; SC-009).
- **Steps**:
  1. When the emit-layer gate (T016) blocks, set the `drain_blocked_reason` on the event before/at
     write time. Use a small closed vocabulary of reasons — e.g. `saas_disabled`, `missing_auth`,
     `missing_team`, `private_teamspace_gate`, `daemon_lock`, `network_unavailable` — defined as
     named constants (Sonar S1192) in `models.py` or `journal.py`.
  2. Persist the reason in the journal row (the `drain_blocked_reason` column from T013). A later
     successful drain clears it (the clearing write is performed by WP07's dispatcher / WP05's
     ledger; here just ensure the column is writable and read back faithfully).
  3. Provide a journal read that exposes blocked rows + reasons (`read_blocked()` or include the
     reason in `read_all()`), so WP11's `--check --json` `event_journal` section can surface
     blocked-drain diagnostics.
- **Files**: `src/specify_cli/event_journal/journal.py`, `src/specify_cli/event_journal/models.py`,
  `src/specify_cli/sync/emitter.py`, `src/specify_cli/sync/runtime_event_emitter.py`.
- **Parallel?**: sequential after T016.
- **Validation**:
  - [ ] A blocked write records a specific `drain_blocked_reason` (not just a boolean).
  - [ ] The reason is read back exactly as written (round-trip).
  - [ ] Blocking the drain never prevents the write (contract §2 bullet 3).
- **Edge cases**: multiple simultaneous blockers (e.g. disabled **and** missing auth) — record a
  deterministic, single canonical reason (document the precedence) rather than a free-form blob.

### Subtask T018 – Journal-side guard: never silently drop Teamspace-bound facts
- **Purpose**: Enforce C-008 at the journal seam: for Teamspace-bound families the write **always**
  happens. Full OPT_OUT policy (refuse/audit discard) is WP09; here the invariant is simply "the
  journal write is not skippable for Teamspace-bound families".
- **Steps**:
  1. Add a guard in the emit path so that a Teamspace-bound family cannot reach a code path that
     skips the journal write. If a caller passes a flag/intent that would skip the write for a
     Teamspace-bound family, raise (fail loudly) rather than silently dropping — this preserves
     C-008 until WP09 supplies the registered-durable-source classification.
  2. Mark in a docstring + a `# WP09:` comment that the full OPT_OUT/TRASH classification (local-
     only vs Teamspace-bound vs discardable) is WP09's responsibility; WP03 only guarantees the
     Teamspace-bound write happens.
- **Files**: `src/specify_cli/sync/emitter.py`, `src/specify_cli/sync/runtime_event_emitter.py`,
  `src/specify_cli/event_journal/journal.py` (guard helper if shared).
- **Parallel?**: sequential after T016/T017.
- **Validation**:
  - [ ] No emit path can skip the journal write for a Teamspace-bound family (C-008).
  - [ ] A skip attempt fails loudly (raises) rather than silently dropping the fact.
  - [ ] The WP09 boundary is documented (no premature OPT_OUT logic here).
- **Edge cases**: do not over-reach into local-only/discardable classification (that is WP09); a
  non-Teamspace-bound family is not in scope for this guard.

### Subtask T019 – Tests (contract §2 Required tests + SC-009)
- **Purpose**: Prove capture-first durability and the no-coalescing invariant via observable on-
  disk state (NFR-001). Covers contract §2 "Required tests" and SC-009.
- **Steps**:
  1. `tests/event_journal/test_journal.py`:
     - append N distinct events → assert N distinct rows (no-coalescing invariant; distinct rows).
     - `row_to_event`/`event_to_params` round-trip (T013).
     - re-append the same `event_id` → stored bytes unchanged, still N rows (idempotent capture).
     - assert **no** normal-path delete exists / `sync now`-equivalent does not remove rows (FR-001).
     - assert the journal exposes no target/delivery field (FR-003).
  2. `tests/event_journal/test_capture_first.py`:
     - **disabled sync** (`SPEC_KITTY_ENABLE_SAAS_SYNC=0`): produce Teamspace-bound events → assert
       they are durably in the journal with `drain_blocked_reason="saas_disabled"`; no delivery
       attempted (contract §2 bullet 1; SC-009).
     - **missing auth+team**: produce → assert durable with blocked-drain diagnostics (contract §2
       bullet 2; SC-009).
     - assert the write precedes the gate (observe the *result*: a row exists even though the gate
       blocked — do **not** assert call order, per NFR-001).
     - assert a Teamspace-bound family cannot be silently dropped (T018 guard raises).
  3. Use a temp spec-kitty home / `tmp_path` fixture; stub the gate evaluators so no real network
     or auth is needed. Assert on returned diagnostics + on-disk rows.
- **Files**: `tests/event_journal/test_journal.py`, `tests/event_journal/test_capture_first.py`.
- **Parallel?**: sequential (last); tests exercise prior subtasks.
- **Validation**:
  - [ ] Both required contract §2 scenarios (disabled sync, missing auth/team) are covered.
  - [ ] No-coalescing invariant test present (distinct rows).
  - [ ] Tests assert observable state, not call order (NFR-001).
  - [ ] New branches/helpers from T013–T018 each have a focused test (Sonar new-code coverage).
- **Edge cases**: ensure `reset_coalesce_strategy()` runs in a fixture/teardown so a future WP08
  registration in another test does not leak into these tests.

## Test Strategy
- Mandatory test files (from `owned_files`): `tests/event_journal/test_journal.py`,
  `tests/event_journal/test_capture_first.py`.
- Run:
  ```bash
  PWHEADLESS=1 .venv/bin/pytest tests/event_journal/test_journal.py tests/event_journal/test_capture_first.py -q
  ```
- These are pure-SQLite + stubbed-gate tests (no real ports/daemon), so they are parallel-safe
  under the default `-n auto --dist loadfile`. No `-n0` serial pass is needed for this WP.
- Fixtures: `tmp_path`-based spec-kitty home; gate evaluators stubbed to simulate
  disabled-sync / missing-auth / missing-team without network. Reset the coalesce strategy in
  teardown for isolation.
- Assert observable state only (NFR-001): on-disk row counts, stored bytes, `drain_blocked_reason`
  values, returned diagnostics — never internal call ordering.

## Risks & Mitigations
- **(plan IC-02 risk) Re-introducing the in-place `_try_coalesce` mutation.** The old `queue.py`
  coalesced by mutating an existing row in place; that is exactly what must NOT return. *Mitigation*:
  `append` uses `INSERT OR IGNORE` and **never** UPDATEs a payload; coalescing is a no-op seam here
  (T015); WP08 will add real coalescing that creates a *new* row + supersedes the prior (never
  mutates). Add a test asserting re-append leaves bytes unchanged (T019).
- **Leaking delivery state into the journal.** *Mitigation*: the `Event` model and `journal.py`
  carry no target/server/delivery field and import nothing from `delivery/` (FR-003, C-001) —
  enforced by a test (T019) and review.
- **Capture-first regressing to capture-after.** A future refactor could move the gate before the
  write. *Mitigation*: `test_capture_first.py` asserts a durable row exists even when every gate
  blocks (observable result, not call order).
- **Server-scoping the journal by accident** (via WP01's `derived_queue_scope`). *Mitigation*:
  scope the journal on producer identity only; never on `resolved_server_url`/`derived_queue_scope`.

## Review Guidance
- Verify the new domain lives only under `src/specify_cli/event_journal/` and the two emit files;
  nothing was added to `src/specify_cli/events/` or `src/specify_cli/sync/queue.py` (C-001).
- Verify the **contract §2 Required tests** pass: disabled-sync durability, missing-auth/team
  durability with blocked-drain diagnostics, and opt-out-of-Teamspace-bound does not silently drop
  (the T018 guard).
- Verify the **contract §3** first bullet: no normal-path delete; `append` never mutates an
  existing payload (the IC-02 trap).
- Verify the coalescing seam is a registration API WP08 can use without editing `journal.py`, and
  the default is genuinely no-op (distinct rows).
- Verify producer-scoping (not server-scoping) and that the journal imports nothing from `delivery/`.
- Confirm `ruff` and `mypy` are clean with zero suppressions, and each new branch/helper has a test.

## Activity Log
> Entries chronological, appended at END. Format: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <action>`
- 2026-06-29T06:21:37Z – system – Prompt created.
- 2026-06-29T07:49:16Z – claude:opus:python-pedro:implementer – shell_pid=31738 – Assigned agent via action command
- 2026-06-29T08:14:11Z – claude:opus:python-pedro:implementer – shell_pid=31738 – Ready: event_journal + capture-first + no-op coalesce seam; ATDD red->green; 27 tests + ruff + mypy + 100% pkg coverage green
- 2026-06-29T08:15:02Z – claude:opus:reviewer-renata:reviewer – shell_pid=38483 – Started review via action command
- 2026-06-29T08:24:38Z – user – shell_pid=38483 – Review passed: append-only journal (INSERT OR IGNORE, no normal-path delete), producer-scoped/delivery-agnostic, capture-first wired live in _emit BEFORE all gates, no-op coalesce seam WP08 can register without editing journal.py. ATDD red->green verified; 27 tests, 100% pkg cov, mypy/ruff clean, S608 noqa justified (static identifiers). Lone sync failure (test_mission_create_json_strict_when_sync_skips_ingress) is pre-existing/auth-env-dependent: fails identically on base 7ee4a53de where event_journal is absent.
