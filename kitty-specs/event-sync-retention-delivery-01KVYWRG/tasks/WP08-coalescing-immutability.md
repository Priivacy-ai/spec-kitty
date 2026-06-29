---
work_package_id: WP08
title: Coalescing with delivered-event immutability
dependencies:
- WP03
- WP05
requirement_refs:
- FR-011
tracker_refs: []
planning_base_branch: mission/event-sync-retention-delivery
merge_target_branch: mission/event-sync-retention-delivery
branch_strategy: Planning artifacts for this mission were generated on mission/event-sync-retention-delivery. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/event-sync-retention-delivery unless the human explicitly redirects the landing branch.
subtasks:
- T046
- T047
- T048
- T049
- T050
phase: Phase 4 - Dispatch
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "65867"
history:
- at: '2026-06-29T06:21:37Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/event_journal/coalesce.py
create_intent:
- src/specify_cli/event_journal/coalesce.py
- tests/event_journal/test_coalesce.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/event_journal/coalesce.py
- tests/event_journal/test_coalesce.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP08 – Coalescing with delivered-event immutability

## ⚡ Do This First: Load Agent Profile
Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter and behave per its guidance before parsing the rest of this prompt.
- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`
If no profile is specified, run `spec-kitty agent profile list` and select the best match for this WP's `task_type` and `authoritative_surface`.

---

## Objectives & Success Criteria

Re-introduce event coalescing **safely**, now that the delivery ledger exists. This WP realises
plan **IC-02a** (deliberately deferred from IC-02 until the ledger could answer "delivered
anywhere?"). It implements `src/specify_cli/event_journal/coalesce.py` and **registers** the
strategy into the no-op seam WP03 built — **without editing `journal.py`**.

The single hard rule (contract §3 coalescing bullet; FR-011): **coalescing may mutate only events
that have no terminal delivery to any target. Once an event is delivered anywhere, its payload
bytes are immutable.** A new coalescible event that arrives after delivery becomes a **new row**,
and the prior is marked **superseded** (never mutated).

This WP is complete when:

- **FR-011** (coalescing honesty): a coalesce attempt against an event with **any** terminal
  delivery leaves its stored payload bytes byte-for-byte unchanged.
- Undelivered events with the same coalesce key collapse correctly (the legitimate coalescing path).
- A delivered event that "would coalesce" instead produces a new row + a `superseded` marker on
  the prior (spec Edge Case "Coalescing after delivery"; contract §3).
- The strategy is registered through WP03's `register_coalesce_strategy(...)` API; **`journal.py`
  is not edited** (the anti-spaghetti seam from plan IC-01/IC-02).
- **NFR-002** delivered-event immutability is proven by a **DB test** (a byte-for-byte assertion),
  not prose.

Observable acceptance (NFR-001 — assert on-disk/ledger state, not call order): after delivering
event E and then producing a coalescible event, the journal shows E's bytes unchanged, a new row
for the incoming event, and a `superseded` marker linking them.

## Context & Constraints

**Prerequisite WPs — what they hand you:**
- **WP03** (`src/specify_cli/event_journal/journal.py`, `models.py`) provides:
  - the append-only `EventJournal` store and the `Event` model (with `coalesce_key`,
    `archived_at`, immutable payload bytes);
  - a **coalescing seam** with a registration API — `register_coalesce_strategy(strategy)` (and
    `reset_coalesce_strategy()`). You register your strategy through this API. **Do NOT edit
    `journal.py`.** The journal calls your strategy inside `append`.
- **WP05** (`src/specify_cli/delivery/ledger.py`) exposes a **delivered-anywhere query** —
  `delivered_anywhere(event_id)` (or the equivalent the ledger publishes). It returns whether the
  event has any *terminal successful* delivery to any target. This is the authority for "is this
  event immutable now?". Consume it via WP05's public surface; do not re-query SQLite for delivery
  state yourself.

**Links:**
- `kitty-specs/event-sync-retention-delivery-01KVYWRG/spec.md` — FR-011, NFR-002, Edge Case
  "Coalescing after delivery".
- `kitty-specs/event-sync-retention-delivery-01KVYWRG/plan.md` — IC-02a (and the IC-02 deferral
  rationale).
- `kitty-specs/event-sync-retention-delivery-01KVYWRG/contracts/event-sync-delivery-contract.md` — §3
  ("Coalescing may mutate only events that have no terminal delivery … Once delivered anywhere,
  payload bytes are immutable").

**Architectural constraints to honor:**
- **C-001 (separate core domain)**: coalescing lives in `src/specify_cli/event_journal/coalesce.py`
  — a new file in the existing journal domain. It must **not** be added to `journal.py`,
  `queue.py`, or `src/specify_cli/events/`.
- **Register, don't edit (the seam contract)**: WP03 built the seam precisely so this WP plugs in
  via `register_coalesce_strategy(...)`. Editing `journal.py` would re-couple the domains and
  re-create the spaghetti the design forbids.
- **No mutation of delivered events** (contract §3; FR-011): the immutability check uses WP05's
  `delivered_anywhere`; a delivered event is never written-over.
- **No event-ID rewriting** (C-005): coalescing never changes an `event_id`.

**Out-of-map edits:** none. You add `coalesce.py` and its test only. You **import** WP03's
registration API and WP05's `delivered_anywhere` query as read consumers; you do not edit those
files. (If WP05's query has a different published name than `delivered_anywhere`, use the name WP05
actually exports — confirm against `src/specify_cli/delivery/ledger.py` before wiring; do not
fabricate a name.)

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

### Subtask T046 – Coalesce only among events with no terminal delivery
- **Purpose**: Implement the core coalescing decision using WP05's delivered-anywhere query, so
  only events with **no terminal delivery to any target** are eligible to be coalesced
  (contract §3; FR-011).
- **Steps**:
  1. In `src/specify_cli/event_journal/coalesce.py`, implement a `CoalesceStrategy` matching the
     protocol WP03's seam expects (the callable/`coalesce(journal, event) -> CoalesceDecision`
     shape). The strategy decides, for an incoming `event`, whether it collapses into an existing
     undelivered event sharing its `coalesce_key`, or is stored as a new row.
  2. Look up candidate prior events with the same `coalesce_key` via the journal's read API
     (e.g. the `(coalesce_key, created_at)` index from WP03 T013). For each candidate, call WP05's
     `delivered_anywhere(candidate.event_id)`:
     - candidate **not** delivered anywhere → eligible to coalesce into (the legitimate path, T050);
     - candidate **delivered** anywhere → ineligible; it is immutable (T047).
  3. If the most-recent eligible candidate is undelivered, collapse: update *that undelivered*
     event per the coalescing semantics (the journal allows writing undelivered rows). If **no**
     eligible undelivered candidate exists (the prior is delivered, or none exists), store the
     incoming event as a new row.
  4. Keep the strategy's decision function deterministic and ≤15 complexity — split "find
     candidates", "classify eligibility", and "decide" into small pure helpers (Sonar S3776 /
     testability). Hoist any repeated literals to named constants (S1192).
- **Files**: `src/specify_cli/event_journal/coalesce.py`.
- **Parallel?**: `[P]` — the decision logic is self-contained once WP03/WP05 surfaces exist.
- **Validation**:
  - [ ] Eligibility is determined **only** via WP05's `delivered_anywhere` (no ad-hoc delivery
        SQL in `coalesce.py`).
  - [ ] Only undelivered events are ever candidates to coalesce into (contract §3; FR-011).
  - [ ] Decision helpers are pure and individually testable.
- **Edge cases**: an event with `coalesce_key is None` is never coalesced (no key → always a
  distinct row). Multiple undelivered candidates → choose deterministically (e.g. newest by
  `created_at`); document the rule.

### Subtask T047 – Delivered → immutable; new row + supersede prior
- **Purpose**: Once an event is delivered anywhere, its payload bytes are immutable. A new
  coalescible event becomes a **new row**, and the prior delivered event is marked **superseded**
  — *without mutating its bytes* (spec Edge Case "Coalescing after delivery"; contract §3; FR-011).
- **Steps**:
  1. When the matched candidate is delivered (per T046), do **not** write over it. Instead INSERT
     the incoming event as a new journal row (via the journal's append path / a write helper the
     journal exposes), preserving its own `event_id` (no ID rewriting — C-005).
  2. Record a `superseded` marker linking the prior delivered event to the new row. Decide a
     representation that does **not** mutate the prior event's payload bytes — e.g. a
     `superseded_by` reference column or a small `superseded` sidecar — and use whatever
     non-payload write surface WP03 exposes (e.g. a marker-setting method analogous to
     `mark_archived`). **The prior event's `payload` bytes are never touched.**
  3. If WP03 did not expose a non-payload marker write you can use, record the supersede marker in a
     way that stays within your `owned_files` (e.g. a dedicated table/row created and managed from
     `coalesce.py`) rather than editing `journal.py`. Prefer the journal's published marker API if
     one exists; only fall back to a coalesce-owned marker store if it does not — and note the
     choice in a docstring.
- **Files**: `src/specify_cli/event_journal/coalesce.py`.
- **Parallel?**: sequential after T046 (shares the decision).
- **Validation**:
  - [ ] A delivered event's `payload` bytes are never written/updated (FR-011, NFR-002).
  - [ ] A post-delivery coalescible event yields a **new** row with its own `event_id` (C-005).
  - [ ] A `superseded` marker links prior→new without mutating the prior payload.
- **Edge cases**: the prior delivered event must remain inspectable and re-drainable (it is not
  archived/deleted by supersession — only marked). Supersession is metadata, not destruction.

### Subtask T048 – Register the coalesce strategy into WP03's seam
- **Purpose**: Plug the strategy into the journal via WP03's registration API so coalescing is
  active **without editing `journal.py`** (the seam contract / anti-spaghetti boundary).
- **Steps**:
  1. In `coalesce.py`, expose an `install()` / `register()` entry point that calls WP03's
     `register_coalesce_strategy(<this strategy>)`. Choose the activation point that matches how the
     mission wires startup (likely invoked from CLI/dispatcher wiring in a later WP, or imported for
     effect) — but the registration *function* lives here, in `coalesce.py`.
  2. **Do not import or edit `journal.py`'s internals** beyond the published `register_coalesce_strategy`
     (and `reset_coalesce_strategy` for tests). Confirm the seam's exact exported names against
     WP03's `event_journal/__init__.py` before wiring; use the real names.
  3. Ensure registration is idempotent / re-entrant safe (registering twice is harmless) so a
     double-import does not stack strategies.
- **Files**: `src/specify_cli/event_journal/coalesce.py`.
- **Parallel?**: sequential after T046/T047.
- **Validation**:
  - [ ] `journal.py` is **unchanged** by this WP (verify the diff touches only `coalesce.py` and
        the test).
  - [ ] The strategy is installed via the published `register_coalesce_strategy` API.
  - [ ] Registration is idempotent.
- **Edge cases**: test isolation — tests must `reset_coalesce_strategy()` in teardown so the
  registered strategy does not leak into other event_journal tests (e.g. WP03's no-coalescing
  invariant test).

### Subtask T049 – REQUIRED DB test: coalesce vs delivered event → bytes unchanged
- **Purpose**: The mandated NFR-002 hard assertion — a coalesce attempt against an event with
  **any** terminal delivery leaves its stored bytes byte-for-byte unchanged. This is a DB-level
  assertion, **not** prose (plan IC-02a risk; contract §3 Required test "Coalescing against a
  delivered event leaves original bytes unchanged").
- **Steps**:
  1. In `tests/event_journal/test_coalesce.py`:
     - append event E (with a `coalesce_key`); capture E's stored `payload` bytes from the DB.
     - record a **terminal successful** delivery for E in the WP05 ledger so
       `delivered_anywhere(E.event_id)` is `True` (use the ledger's public API / a real ledger over
       a temp DB — not a mock that lies about delivery).
     - produce a new coalescible event E2 sharing E's `coalesce_key`, routing through the
       registered strategy (i.e. via `journal.append(E2)` with the strategy installed).
     - **Assert E's stored `payload` bytes are byte-for-byte identical to the captured bytes**
       (read directly from the journal DB) — the hard immutability assertion.
     - Assert E2 exists as its own new row with its own `event_id`, and a `superseded` marker links
       E→E2.
  2. Use real SQLite (journal + ledger over `tmp_path`), not mocks, so the assertion is a genuine
     DB fact (NFR-002).
- **Files**: `tests/event_journal/test_coalesce.py`.
- **Parallel?**: sequential after T046–T048.
- **Validation**:
  - [ ] The test reads E's bytes directly from the DB before and after and asserts equality.
  - [ ] Delivery is recorded via the real WP05 ledger, not a stub that fakes `delivered_anywhere`.
  - [ ] The test fails if any code path mutates a delivered event's payload.
- **Edge cases**: ensure the captured "before" bytes are read from disk (not the in-memory `Event`),
  so a sneaky in-place UPDATE would be caught.

### Subtask T050 – Tests: collapse, superseded marker, no mutation
- **Purpose**: Cover the remaining coalescing behaviors observably (NFR-001): undelivered events
  collapse; the superseded marker is recorded; delivered events are never mutated.
- **Steps** (`tests/event_journal/test_coalesce.py`):
  1. **Undelivered collapse**: append two undelivered events sharing a `coalesce_key` through the
     strategy → assert they collapse (one effective coalesced row per the coalescing semantics);
     neither was delivered, so collapsing is legitimate (T046).
  2. **Superseded marker**: the delivered-then-coalescible scenario (from T049) → assert the
     `superseded` marker links prior→new and the prior remains inspectable/re-drainable (T047).
  3. **No mutation of delivered**: a second delivered event with a later coalescible arrival →
     assert its bytes are unchanged and a new row + marker were produced (reinforces T049 across a
     second path).
  4. **No-key never coalesces**: an event with `coalesce_key is None` → always a distinct row.
  5. **Isolation**: `reset_coalesce_strategy()` in a fixture/teardown.
- **Files**: `tests/event_journal/test_coalesce.py`.
- **Parallel?**: sequential (last).
- **Validation**:
  - [ ] Undelivered collapse, superseded marker, delivered-immutability, and no-key paths each have
        a focused test (Sonar new-code coverage for every new branch/helper).
  - [ ] Tests assert observable on-disk/ledger state, not internal call order (NFR-001).
  - [ ] Teardown resets the strategy so other event_journal tests are unaffected.
- **Edge cases**: a coalesce key shared by one delivered and one undelivered prior — the strategy
  must coalesce into the undelivered one and never the delivered one (mixed-eligibility path).

## Test Strategy
- Mandatory test file (from `owned_files`): `tests/event_journal/test_coalesce.py`.
- Run:
  ```bash
  PWHEADLESS=1 .venv/bin/pytest tests/event_journal/test_coalesce.py -q
  ```
- Pure-SQLite tests (journal + real WP05 ledger over `tmp_path`); no real ports/daemon, so
  parallel-safe under the default `-n auto --dist loadfile`. No `-n0` serial pass needed.
- **Use a real ledger**, not a mock, for `delivered_anywhere` (NFR-002): the immutability
  assertion must be a genuine DB fact. Read payload bytes directly from the journal DB for the
  byte-for-byte assertion.
- Reset the coalesce strategy in teardown so registration does not leak across tests.
- Assert observable state only (NFR-001): stored bytes, row counts, `event_id`s, supersede markers.

## Risks & Mitigations
- **(plan IC-02a risk) Treating delivered-event immutability as prose instead of a DB assertion.**
  This is the documented correctness trap from review. *Mitigation*: T049 is a **required DB test**
  that reads bytes from disk before/after and asserts byte-for-byte equality against a real ledger
  recording a terminal delivery — not a comment, not a mock.
- **Re-coupling the journal domain by editing `journal.py`.** *Mitigation*: register exclusively via
  WP03's `register_coalesce_strategy`; the diff for this WP must touch only `coalesce.py` and its
  test (verify in review).
- **Querying delivery state directly instead of via WP05.** Ad-hoc SQL would drift from the
  ledger's authority. *Mitigation*: eligibility uses WP05's published `delivered_anywhere` query
  only.
- **Mutating a delivered event during the "supersede" write.** *Mitigation*: supersession is a
  metadata marker (reference/sidecar), never a payload write; the prior payload bytes are never
  updated. Covered by T049 + T050.
- **Strategy leakage across tests** (a registered strategy affecting WP03's no-coalescing test).
  *Mitigation*: `reset_coalesce_strategy()` in teardown; idempotent registration.

## Review Guidance
- Verify the diff touches **only** `src/specify_cli/event_journal/coalesce.py` and
  `tests/event_journal/test_coalesce.py`; `journal.py` is unchanged (the seam contract).
- Verify the **contract §3** coalescing rule end-to-end: undelivered events coalesce; a delivered
  event is never mutated; a post-delivery coalescible event becomes a new row + superseded marker.
- Verify the **required NFR-002 DB test** (T049) reads bytes from the DB and asserts byte-for-byte
  immutability against a *real* ledger delivery (not a mock).
- Verify eligibility is determined solely via WP05's `delivered_anywhere` query, and that
  `event_id`s are never rewritten (C-005).
- Confirm `ruff` and `mypy` are clean with zero suppressions, decision helpers are ≤15 complexity,
  and every new branch/helper has a focused test.

## Activity Log
> Entries chronological, appended at END. Format: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <action>`
- 2026-06-29T06:21:37Z – system – Prompt created.
- 2026-06-29T08:52:20Z – claude:opus:python-pedro:implementer – shell_pid=55131 – Assigned agent via action command
- 2026-06-29T09:08:53Z – user – shell_pid=55131 – WP08 lane progression
- 2026-06-29T09:08:55Z – user – shell_pid=55131 – WP08 lane progression
- 2026-06-29T09:14:22Z – claude:opus:python-pedro:implementer – shell_pid=55131 – Ready: coalesce-only-undelivered + immutability DB test; registered via WP03 seam; gates green
- 2026-06-29T09:15:48Z – claude:opus:reviewer-renata:reviewer – shell_pid=65867 – Started review via action command
- 2026-06-29T09:21:25Z – user – shell_pid=65867 – Review passed: immutability mutation-tested. Broke strategy to coalesce-into-delivered -> test_coalesce_against_delivered_event_leaves_bytes_unchanged went RED at the byte-for-byte assert (b'new-bytes'!=b'original-bytes'); reverted, GREEN. ATDD red->green confirmed (coalesce.py absent at test-only commit c708dd397, precedes impl c6c2eeb23). Seam-only diff: both WP08 commits touch ONLY coalesce.py + test_coalesce.py; journal.py unchanged; registers via WP03 register_coalesce_strategy. C-001: no import from specify_cli.delivery (structural DeliveredAnywhereQuery Protocol + injected real SqliteDeliveryLedger). Eligibility solely via delivered_anywhere terminal-success; event_ids never rewritten (C-005); mixed-eligibility collapses into undelivered prior, never delivered. 7 coalesce + 34 event_journal tests pass (no WP03 regression); mypy strict + ruff clean; 3 (not 4) S608 noqa all genuine identifier-only false positives (values via ? placeholders, matching models.py).
