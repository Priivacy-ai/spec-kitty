---
description: "Work packages for the sync batch-400 poison-isolation mission (#2736)"
---

# Work Packages: Sync batch-400 poison isolation (bisection)

**Inputs**: Design documents from `/kitty-specs/sync-batch-400-poison-isolation-01KXW08B/`
**Prerequisites**: plan.md (required), spec.md (user stories), research/pre-spec-4lens-squad.md

**Tests**: This is a bug-fix mission under ATDD/red-first discipline — testing work is REQUIRED
(the merged `tests/delivery/test_poison_batch_2736.py` is the honest-RED anchor; new acceptance,
guard, and contract tests are authored red-first, marked `@pytest.mark.regression` until green).

**Organization**: Fine-grained subtasks (`Txxx`) roll up into work packages (`WPxx`). Work-package
boundaries respect the no-overlapping-`owned_files` rule: IC-02 (seam) + IC-04 (bisect) merge into
WP02 (both live in `receivers.py`). IC-05 (the LIVE queue disposition fix) is **WP04** (owns
`sync/batch.py`); IC-06 (#2755 retrofit) is **WP05** (owns the guard test; its one-line rewire of
`sync/batch.py` is a declared out-of-map edit sequenced after WP04, avoiding a same-file ownership clash).

**Prompt Files**: Each work package references a matching prompt file in `/tasks/`.

## Subtask Format: `[Txxx] [P?] Description`

- **[P]** indicates the subtask can proceed in parallel (different files/components).
- Include precise file paths or modules.

## Path Conventions

- **Single project**: `src/specify_cli/`, `tests/`.

---

## Work Package WP01: Batch-partition primitive (SSOT leaf) (Priority: P0) 🎯 MVP

**Goal**: Land the shared pure primitive `core/batch_partition.py` — `split_in_half(events)` (plain
keep-left cut) + `create_aware_midpoint(events, key_of)` (create-aware cut). Ordering-agnostic; placed
in `core/` (neutral leaf both `delivery` and `sync` import downward), NOT `delivery/` (which would create
a `sync → delivery` cycle the layer gate can't catch — alphonso).
**Independent Test**: `pytest tests/core/test_batch_partition.py` — halving math (non-empty left on the
singleton edge), create-aware snap keeps an *adjacent* `wp_id`'s create+status out of different halves,
purity/determinism, element-generic via injected `key_of` (works on `dict` AND `OutboundEvent`).
**Prompt**: `/tasks/WP01-batch-partition-primitive.md`
**Requirement Refs**: FR-003, FR-006

### Included Subtasks

- [x] T001 [P] Red-first `tests/core/test_batch_partition.py`: `split_in_half` halving + singleton non-empty-left; `create_aware_midpoint` adjacent-pair snap via injected `key_of`; purity/determinism
- [x] T002 Implement `split_in_half(events) -> tuple[list, list]` — plain `max(1, len//2)` cut (the genuinely-shared / #2755-relevant midpoint math)
- [x] T003 Implement `create_aware_midpoint(events, key_of) -> int` — snaps the cut off a create/status boundary for an *adjacent* pair; ordering-agnostic (no batch-spanning guarantee)
- [x] T004 Confirm element-generic: `key_of` is a required callable (dict keyed at `aggregate_id`, `OutboundEvent` keyed inside `payload`); NO wp_id sniffing inside the primitive

### Implementation Notes

- Pure module: stdlib only, no I/O, deterministic. `split_in_half` guarantees a non-empty left slice.
- `create_aware_midpoint` returns an index; it does NOT reorder. The ordering guarantee is WP02's job.

### Parallel Opportunities

- T001 (red tests) can be authored alongside T002/T003.

### Dependencies

- None (starting package, P0 foundation).

### Risks & Mitigations

- Leaking a bounded context into the primitive → keep `key_of` injected; never branch on event shape.

---

## Work Package WP02: Receiver poison-isolation bisection (P0 MVP) (Priority: P0) 🎯 MVP

**Goal**: The release-blocking fix — on a whole-batch 400 (>1 event, no per-event `details`), recursively
bisect (split → re-POST BOTH halves → recurse to singletons), isolating the culprit (`rejected`,
non-terminal) and delivering every innocent. Extract the single-attempt seam; add sequential
left-before-right recursion (the ordering guarantee); stand up the drain-harness acceptance.
**Independent Test**: `pytest tests/delivery/test_poison_batch_2736.py tests/delivery/test_batch_bisection_ordering.py`
— all green; `tests/delivery/` + `tests/sync/` stay green; `sync now` happy path behaviorally unchanged.
**Prompt**: `/tasks/WP02-receiver-poison-isolation-bisection.md`
**Requirement Refs**: FR-001, FR-002, FR-003, FR-004, FR-008, NFR-001, NFR-002, NFR-003, C-002

### Included Subtasks

- [ ] T005 [red] Upgrade `_AllOrNothingBatchPoster` in `test_poison_batch_2736.py` to an ordered receipt log (NOT `frozenset`); add the culprit-final-singleton assertion (keep `@pytest.mark.regression` until green)
- [ ] T006 [red] New `tests/delivery/test_batch_bisection_ordering.py` — straddle fixture **with teeth** (culprit in the create/left half; create+status non-adjacent and on opposite sides of the naive midpoint) + `receipt_index(create) < receipt_index(status)`
- [ ] T007 [red] Same file — drain harness: `deliver()` → `ledger.record_result(event_id=r.event_id, target_id=tid, result=r.outcome)` → `set(select_undelivered(...)) == {culprit_id}` + re-drain no-reselection; NFR-002 POST-count bound + termination; NFR-003 no-duplicate-accepted
- [ ] T008 Extract `_attempt_batch_send(events) -> (int | None, Mapping | None)` in `receivers.py` (transport failure → `None` status)
- [ ] T009 Implement `_bisect_send(events)` — split via `create_aware_midpoint`, sequential `left` then `right`, base `len==1` → `_map_400` singleton; **`None` status → all-transient, never recurse**
- [ ] T010 Wire `deliver()` to accumulate exactly one result per input event across sub-POSTs; culprit stays `rejected` (non-terminal, not force-parked); no accepted event re-POSTs (idempotency)
- [ ] T011 Remove `@pytest.mark.regression` from the now-green anchor; confirm NFR-001 (happy path unchanged, `tests/delivery/` + `tests/sync/` green)

### Implementation Notes

- Keep `deliver()`/`_post_batch` trivial; the recursion lives in `_bisect_send` (≈4-5 branches, CC-15 safe).
- Consumes WP01's `create_aware_midpoint` (create-aware cut). The ordering invariant is the sequential
  recursion here, NOT the primitive.

### Parallel Opportunities

- T005–T007 (red acceptance) can be authored before/alongside T008–T010 (impl).

### Dependencies

- Depends on WP01 (consumes `core.batch_partition.create_aware_midpoint`).

### Risks & Mitigations

- **Drain-harness trap**: `record_result` must receive the `DeliveryOutcome` enum (`r.outcome`), NOT the
  `DeliveryResult` object (raises `ValueError` in `_coerce_result_token`). — pedro.
- Splitting a transport failure would multiply transients → `None` status never recurses.

---

## Work Package WP03: CLI FSM force-free contract test (Priority: P2)

**Goal**: Pin `in_progress → planned` (reason-only) and the review-rejection edges (review_ref-only) as
**force-free legal** per `wp_state.py`; document SaaS#509 as the server-side alignment. The CLI must NOT
emit `force` on these edges (question-2: CLI FSM is authoritative).
**Independent Test**: `pytest tests/status/test_wp_state_force_free_contract.py` — asserts via the public
`check_transition` / `can_transition_to` that these edges are legal with reason-only and that the guard
does not consult `ctx.force`.
**Prompt**: `/tasks/WP03-cli-fsm-force-free-contract.md`
**Requirement Refs**: FR-007, C-003

### Included Subtasks

- [x] T012 [red] New `tests/status/test_wp_state_force_free_contract.py`: `wp_state_for("in_progress").check_transition(Lane.PLANNED, ctx_reason_no_force) == (True, None)`
- [x] T013 Assert the review-rejection backward edges (`for_review`/`in_review` → earlier, review_ref-only) are force-free legal; the guard does NOT consult `ctx.force`
- [x] T014 Document SaaS#509 as the server matrix alignment in the module docstring; assert the CLI never emits `force=true` on these edges

### Implementation Notes

- Assert against the PUBLIC API (`check_transition` / `can_transition_to`), not by reaching into `guard_for`.
- Contract test only — no production change (`wp_state.py` already allows these edges force-free).

### Parallel Opportunities

- Fully independent — parallelizable with WP01/WP02/WP04/WP05.

### Dependencies

- None.

### Risks & Mitigations

- Over-reaching into private guards → keep the assertion on the public transition API.

---

## Work Package WP04: Offline-queue LIVE whole-batch-400 disposition fix (Priority: P1)

**Goal**: Fix the **LIVE** whole-batch-400 poison in the offline-queue path. Post-tasks squad correction
(paula, verified): the originally-named `_record_all_events_failed` is DORMANT (all live callers pass
`transient=True`); the live poison is `_parse_error_response`'s no-`details` else-branch
(`sync/batch.py:967-985`), reached from the live `batch_sync` 400 handler (`:1188` → `process_batch_results`
bumps `retry_count` on every `rejected` innocent). Treat the no-adjudication case as transient (mirror the
sibling 403/5xx branch). Leave the per-event `details` path (`:923-966`) unchanged — server-adjudicated.
Does NOT consume the primitive → WP01-independent, ships in parallel-group 0.
**Independent Test**: `pytest tests/sync/test_batch_400_no_details_poison_2736.py` — on a whole-batch 400
with no per-event details, innocents are NOT `rejected` and `retry_count` is NOT bumped; the per-event
`details` path still rejects the named events.
**Prompt**: `/tasks/WP04-offline-queue-live-400-disposition.md`
**Requirement Refs**: FR-005, SC-007, C-001, C-004

### Included Subtasks

- [x] T015 [red] Focused `tests/sync/test_batch_400_no_details_poison_2736.py`: drive the live `batch_sync` 400-no-details path; assert innocents are NOT `rejected`/retry-bumped, AND the per-event `details` path still rejects the named events (regression guard on the adjudicated path)
- [x] T016 Fix `_parse_error_response`'s no-`details` else-branch (`sync/batch.py:967-985`) — treat as transient (no `rejected`, no retry bump), mirroring the sibling 403/5xx `transient=True` branch; do NOT touch the `details` path or import the receiver bisect

### Implementation Notes

- The fix is "mark transient, not rejected" in ONE branch. No primitive dependency.
- The automated pre-review gate DOES cover this (`tests/sync/**` → focused `sync` group), unlike WP05's
  architectural tests (see WP05).

### Dependencies

- None (WP01-independent — parallel-group 0 with WP01/WP03).

### Risks & Mitigations

- Over-reaching into the server-adjudicated `details` path → the T015 regression guard pins it untouched.

---

## Work Package WP05: #2755 SSOT retrofit + single-authority guard (Priority: P2, release-optional)

**Goal**: Close #2755 — rewire `_shrink_events_for_retry:392` onto the PLAIN `split_in_half` (behavior-
preserving: `split_in_half(events)[0]` is textually equal to the inline `events[:max(1,len//2)]`), guarded
by a behavioral-delegation spy (load-bearing) + an AST belt-and-suspenders check. **Off the P0 release
gate.** Owns the guard test; makes the one-line rewire in `sync/batch.py` as a declared out-of-map edit
(sequenced after WP04 to avoid a same-file race).
**Independent Test**: `pytest tests/architectural/test_batch_split_single_authority.py` + the six merged
#2735 tests stay green (no shift — the rewire is behavior-identical).
**Prompt**: `/tasks/WP05-2755-ssot-retrofit-guard.md`
**Requirement Refs**: FR-006, SC-004

### Included Subtasks

- [ ] T017 [red] `tests/architectural/test_batch_split_single_authority.py` behavioral-delegation guard (LOAD-BEARING): spy the real `core.batch_partition.split_in_half` and assert `_shrink_events_for_retry` calls it
- [ ] T018 [red] Same file — AST belt-and-suspenders: a `BinOp` FloorDiv-by-2 over a `len()` of the batch/events param exists in no `src/` module except `core/batch_partition.py`; MUST allowlist `core/batch_partition.py` AND `doc_analysis/gap_analysis.py:392` (live unrelated `len//2`), or scope to the `events`/`batch` identifier
- [ ] T019 Rewire `_shrink_events_for_retry:392` → `split_in_half(events)[0]` (keep-left-drop-rest policy); out-of-map edit in `sync/batch.py` (owned by WP04), recorded with rationale; the six #2735 tests MUST stay green with NO shift
- [ ] T020 Confirm #2755 closed. The rewire is behavior-preserving by construction → any #2735 red is a mechanical bug to FIX. The escape hatch applies ONLY to a documented architectural blocker (e.g. unbreakable import cycle) with operator sign-off recorded in `design-decisions.md` — NEVER a self-inflicted red

### Implementation Notes

- `_shrink_events_for_retry` consumes the PLAIN `split_in_half` — NOT `create_aware_midpoint` (byte-sizing
  must not inherit create-aware snapping).
- **Pre-review-gate blind spot (debbie/F9)**: `tests/architectural/**` lands only in CI's excluded
  `core_misc` catch-all, so the automated pre-review gate returns `no_coverage — excluded scope` — that is
  NOT a pass. Run `PWHEADLESS=1 pytest tests/architectural/ -q` manually and rely on CI `integration-tests-core-misc`.

### Dependencies

- Depends on WP01 (`split_in_half`) and WP04 (same-file `sync/batch.py` sequencing — the rewire is an
  out-of-map edit after WP04's owned change).

### Risks & Mitigations

- The rewire is behavior-identical → near-zero semantic risk; residual risk is a mechanical fumble (import
  cycle, off-by-one) which T017/the #2735 tests catch. NOT deferrable on a self-inflicted red.

---

## Dependency & Execution Summary

- **Sequence**: parallel-group 0 = { WP01 (primitive), WP03 (contract), WP04 (live queue fix) }; after
  WP01 → WP02 (P0 MVP); after WP01+WP04 → WP05 (#2755 retrofit).
- **Parallelization**: WP01 ∥ WP03 ∥ WP04 at the start (disjoint files); then WP02 (needs WP01) runs while
  WP05 (needs WP01+WP04) follows.
- **MVP Scope**: **WP01 + WP02** constitute the P0 release gate (SC-001..003, SC-006). WP03 (FR-007), WP04
  (FR-005 live fix — HIGH but off the P0 gate) and WP05 (FR-006/#2755, release-optional) are off the P0 gate.

---

## Requirements Coverage Summary

| Requirement ID | Covered By Work Package(s) |
|----------------|----------------------------|
| FR-001 | WP02 |
| FR-002 | WP02 |
| FR-003 | WP01, WP02 |
| FR-004 | WP02 |
| FR-005 | WP04 |
| FR-006 | WP01, WP05 |
| FR-007 | WP03 |
| FR-008 | WP02 |
| NFR-001 | WP02 |
| NFR-002 | WP02 |
| NFR-003 | WP02 |
| C-001 | WP04 |
| C-002 | WP02 |
| C-003 | WP03 |
| C-004 | WP04 |

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Red primitive tests | WP01 | P0 | Yes |
| T002 | `split_in_half` | WP01 | P0 | No |
| T003 | `create_aware_midpoint` | WP01 | P0 | No |
| T004 | Element-generic `key_of` | WP01 | P0 | No |
| T005 | Red: ordered receipt log + culprit-singleton | WP02 | P0 | No |
| T006 | Red: straddle fixture with teeth + receipt-order | WP02 | P0 | No |
| T007 | Red: drain-harness ledger residual-set + NFR-002/003 | WP02 | P0 | No |
| T008 | Extract `_attempt_batch_send` seam | WP02 | P0 | No |
| T009 | `_bisect_send` recursion | WP02 | P0 | No |
| T010 | `deliver()` accumulation + idempotency | WP02 | P0 | No |
| T011 | Un-mark regression; NFR-001 green | WP02 | P0 | No |
| T012 | Red: `in_progress→planned` force-free | WP03 | P2 | Yes |
| T013 | Review-rejection edges force-free | WP03 | P2 | No |
| T014 | Document SaaS#509; no force emitted | WP03 | P2 | No |
| T015 | Red: live 400-no-details poison test | WP04 | P1 | Yes |
| T016 | Fix `_parse_error_response` no-details branch | WP04 | P1 | No |
| T017 | Red: behavioral-delegation guard (load-bearing) | WP05 | P2 | Yes |
| T018 | Red: AST `//2` guard (belt+allowlist) | WP05 | P2 | Yes |
| T019 | Rewire `_shrink_events_for_retry` | WP05 | P2 | No |
| T020 | Confirm #2755; hatch (blocker-only) | WP05 | P2 | No |

---

> The combination of `tasks.md` and the bundled prompt files enables a new engineer to deliver any work
> package end-to-end. The P0 (WP01+WP02) is release-blocking; everything else is off that gate.
