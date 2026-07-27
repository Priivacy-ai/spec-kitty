---
work_package_id: WP02
title: Receiver poison-isolation bisection (P0 MVP)
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-008
- NFR-001
- NFR-002
- NFR-003
- C-002
tracker_refs:
- "#2736"
planning_base_branch: fix/2736-batch-400-poisoning-isolation
merge_target_branch: fix/2736-batch-400-poisoning-isolation
branch_strategy: Planning artifacts for this mission were generated on fix/2736-batch-400-poisoning-isolation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/2736-batch-400-poisoning-isolation unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
- T008
- T009
- T010
- T011
phase: Phase 2 - P0 release-blocker
assignee: ''
agent: "claude"
shell_pid: "1659957"
shell_pid_created_at: "1784430307.1"
history:
- at: '2026-07-19T02:11:31Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/delivery/
create_intent:
- tests/delivery/test_batch_bisection_ordering.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/delivery/receivers.py
- tests/delivery/test_poison_batch_2736.py
- tests/delivery/test_batch_bisection_ordering.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP02 – Receiver poison-isolation bisection (P0 MVP)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave
according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks.

---

## Objectives & Success Criteria

**This is the release-blocking P0.** On a whole-batch HTTP 400 with `>1` event and no per-event `details`
(the poison signature), recursively bisect the batch: split → re-POST **BOTH** halves → recurse to
singletons. The culprit ends `rejected` (non-terminal, retryable — NOT force-parked); every innocent is
delivered (`success`). Ordering is preserved by delivering left-before-right sequentially.

**Done when**:
- `tests/delivery/test_poison_batch_2736.py` is GREEN (regression marker removed).
- `tests/delivery/test_batch_bisection_ordering.py` is GREEN (straddle-order + drain-harness residual-set).
- `tests/delivery/` + `tests/sync/` stay green; the no-poison `sync now` happy path is behaviorally
  unchanged (NFR-001).

## Context & Constraints

- **Plan**: IC-01 (acceptance infra) + IC-02 (seam) + IC-04 (bisection) — merged here because the seam and
  the recursion share `receivers.py` and the acceptance tests are the red-first unit for the fix.
- **Consumes WP01**: `from specify_cli.core.batch_partition import create_aware_midpoint`.
- **Ordering lives HERE, not in the primitive** (alphonso + renata): a batch-spanning create/status pair
  cannot be kept together by any midpoint; the `receipt_index(create) < receipt_index(status)` invariant is
  guaranteed by the **sequential left-before-right recursion**.
- **No server change** (C-002): the strict all-or-nothing 400 is a deliberate boundary.
- Keep `deliver()` / `_post_batch` trivial; put the recursion in a new `_bisect_send` (≈4-5 branches,
  CC-15 safe). `ruff`/`mypy` clean, zero new suppressions.

## Branch Strategy

- **Strategy**: per computed lane from `lanes.json`
- **Planning base branch**: `fix/2736-batch-400-poisoning-isolation`
- **Merge target branch**: `fix/2736-batch-400-poisoning-isolation`

## Subtasks & Detailed Guidance

### Subtask T005 [red] – Ordered receipt log + culprit-singleton assertion

- **Purpose**: Make the merged anchor prove isolation ordering, not just counts.
- **Steps**: In `tests/delivery/test_poison_batch_2736.py`, change `_AllOrNothingBatchPoster.posted_batches`
  from an order-lossy `frozenset` to an **ordered receipt log** (a `list` of the event-id sequence per
  POST, in POST-execution order), plus an `accepted_receipts: list[str]` appended **on the 200/accept branch,
  in POST-execution order (NEVER input order)**. Assert the culprit is **isolated to a size-1 POST** —
  `{culprit} in [set(p) for p in receipt_log if len(p) == 1]` (membership in the singleton POSTs, NOT
  `receipt_log[-1]`: with a left-half culprit, right-half innocents POST after it, so the culprit's singleton
  is not chronologically last). Keep `@pytest.mark.regression` — this stays RED until T009/T010 land.
- **Files**: `tests/delivery/test_poison_batch_2736.py`.

### Subtask T006 [red] – Straddle fixture with teeth + receipt-order

- **Purpose**: Pin the ordering invariant non-fakeably.
- **Steps**: New `tests/delivery/test_batch_bisection_ordering.py`. **Reuse/import `_AllOrNothingBatchPoster`
  from `test_poison_batch_2736.py`** (do NOT re-roll a poster here) so `accepted_receipts` records
  **server-acceptance (200-branch) POST order, never input order** — input order is always create-before-status
  by FIFO, which would make the assertion a tautology and the fixture teeth decorative. Build a straddle
  fixture where (a) the **culprit sits in the create/left half**, and (b) a `wp_id`'s create and status are
  **non-adjacent and on opposite sides of the naive midpoint**. Assert `receipt_index(create) <
  receipt_index(status)` across the accepted receipts. **Strengthen the red-first check (renata): the fixture
  must RED against a PARALLEL / right-before-left bisect** (not merely the unfixed single-POST path) — i.e.
  under a naive/reordering split the create (left half, delivered second) would receipt AFTER the status
  (right half), inverting the index. That is the exact failure US2/SC-003 exist to catch.
- **Files**: `tests/delivery/test_batch_bisection_ordering.py`.

### Subtask T007 [red] – Drain-harness residual-set + NFR-002/003

- **Purpose**: Prove delivery-completeness and boundedness across a full drain.
- **Steps**: Stand up a drain harness in the same test file: `deliver()` the poison-containing backlog →
  record each result with **`ledger.record_result(event_id=r.event_id, target_id=tid, result=r.outcome)`**
  (pass the `DeliveryOutcome` enum `r.outcome`, NEVER the `DeliveryResult` object — it raises `ValueError` at
  `record_result` (ledger.py:517; `_coerce_result_token` just returns the garbage token)) → seed a backlog
  with **≥2 innocents** so the residual-set equality is non-trivial → assert `set(select_undelivered(...)) ==
  {culprit_id}` AND a re-drain does NOT re-select the innocents (no re-poison). Add NFR-002
  (`len(receipt_log) <= 2*ceil(log2(N))+1` single-culprit; `<= 2*N-1` all-invalid; no singleton POST appears
  twice — termination) and NFR-003 (accepted `event_id` multiset has no duplicates). No WP07 dispatcher — the
  harness stands up in `tests/delivery/` directly.
- **Files**: `tests/delivery/test_batch_bisection_ordering.py`.

### Subtask T008 – Extract `_attempt_batch_send` seam

- **Purpose**: One clean single-attempt seam the recursion calls.
- **Steps**: Extract `_attempt_batch_send(events) -> (int | None, Mapping | None)` from `_post_batch`. The
  transport-failure branch (`requests.RequestException`) returns `(None, None)`. Existing `tests/delivery/`
  stay green (pure refactor).
- **Files**: `src/specify_cli/delivery/receivers.py`.

### Subtask T009 – Implement `_bisect_send` recursion

- **Purpose**: The core fix.
- **Steps**: `_bisect_send(events) -> list[DeliveryResult]`: call `_attempt_batch_send`. If `status is None`
  → map ALL events to transient, **do NOT recurse** (splitting a transport failure multiplies transients).
  If it's a whole-batch 400 with no per-event `details` AND `len > 1` → split at
  `create_aware_midpoint(events, key_of=<wp_id>)`, then `return _bisect_send(left) + _bisect_send(right)`
  (sequential, never parallel/reorder). Base case `len == 1` → `_map_400` singleton (the fan-out becomes
  correct-by-construction: one event → one `rejected` with its own reason). Otherwise → `map_batch_response`.
- **Files**: `src/specify_cli/delivery/receivers.py`.

### Subtask T010 – `deliver()` accumulation + idempotency

- **Purpose**: One result per input event; no innocent re-POSTs.
- **Steps**: Wire `deliver()` to return exactly one `DeliveryResult` per input event, accumulated across
  sub-POSTs. Innocents `success`, culprit `rejected` (non-terminal — it re-selects and re-delivers once the
  SaaS matrix aligns, SaaS#509). A cross-pass/crash re-post of an already-accepted event returns `duplicate`
  — **add an explicit assertion** (re-post an already-accepted event → outcome `duplicate`), either here or
  folded into T007's re-drain, so the `duplicate` edge (spec line 130) is pinned, not just narrated.
- **Files**: `src/specify_cli/delivery/receivers.py`.

### Subtask T011 – Un-mark regression; confirm NFR-001

- **Purpose**: Flip the anchor green and prove no regression.
- **Steps**: **Marker removal is the ONLY change in T011.** Do NOT weaken or delete the T005/T006/T007
  assertions to reach green — if green requires touching an assertion, the fix (T009/T010) is incomplete:
  STOP and fix the code. Remove `@pytest.mark.regression` from `test_poison_batch_2736.py`. Run
  `tests/delivery/` and `tests/sync/` — all green. Sanity-run a no-poison batch through `deliver()` to confirm
  the happy path is behaviorally unchanged (single POST, no bisection).
- **Files**: `tests/delivery/test_poison_batch_2736.py`.

## Test Strategy

- `PWHEADLESS=1 pytest tests/delivery/ tests/sync/ -q` green at close.
- Run the changed tests RED first (T005–T007) to prove they fail without the fix, then green after
  T008–T010 (delete-the-assertion check: removing the fix must re-red them).
- **⚠️ Pre-review-gate blind spot (debbie/F9) — load-bearing for this P0.** `tests/delivery/**` +
  `src/specify_cli/delivery/**` land ONLY in CI's excluded `core_misc` catch-all, so the automated pre-review
  gate returns `no_coverage — excluded scope` for this WP. **That warn is NOT a pass** — a reviewer must not
  read it as clean. The manual `pytest tests/delivery/` run above + CI `integration-tests-core-misc` are the
  real gate for the release-blocking P0.

## Risks & Mitigations

- **`record_result` `ValueError` trap** → pass `r.outcome` (the enum). Highest "looks-done-but-throws" risk.
- **Transport-failure recursion** → `None` status never splits.
- **CC-15** → recursion isolated in `_bisect_send`; extract a small `_is_poison_400(status, body)` predicate
  if the branch count climbs.

## Review Guidance

- Verify the straddle fixture actually has teeth (culprit in create/left half; create/status opposite sides
  of the naive midpoint) — a toothless fixture passes trivially.
- Verify the culprit stays `rejected` (non-terminal), never force-parked.
- Verify NFR-002/003 assertions are on the ordered receipt log, not narrated.

## Activity Log

- 2026-07-19T02:11:31Z – system – Prompt created.
- 2026-07-19T03:05:26Z – claude – shell_pid=1659957 – Assigned agent via action command
