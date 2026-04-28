---
work_package_id: WP04
title: Review-cycle counter advances only on real rejections (#676)
dependencies:
- WP03
requirement_refs:
- FR-008
- FR-009
- FR-010
planning_base_branch: release/3.2.0a6-tranche-2
merge_target_branch: release/3.2.0a6-tranche-2
branch_strategy: lane-based
subtasks:
- T018
- T019
- T020
- T021
- T022
history:
- at: '2026-04-28T09:30:00Z'
  by: spec-kitty.tasks
  note: Created as part of tranche-2 specify→plan→tasks pipeline
authoritative_surface: src/specify_cli/cli/commands/agent/workflow.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/workflow.py
- tests/specify_cli/cli/commands/agent/test_review_cycle_counter.py
- tests/integration/test_review_cycle_rejection_only.py
tags: []
---

# WP04 — Review-cycle counter advances only on real rejections (#676)

## Branch Strategy

- **Planning/base branch**: `release/3.2.0a6-tranche-2`
- **Final merge target**: `release/3.2.0a6-tranche-2`
- Lane C, position 2 (after WP03). Implementation command: `spec-kitty agent action implement WP04 --agent claude`.
- WP04 inherits the workspace from the WP03 lane to share the `cli/commands/agent/workflow.py` editing surface safely.

## Objective

The review-cycle counter for a work package advances **only** in response to a real reviewer rejection event. Re-running `spec-kitty agent action implement WPNN` to regenerate the implement prompt is fully idempotent: counter unchanged, no new `review-cycle-N.md` artifact written.

## Context

GitHub issue #676. Today, re-running `agent action implement` (e.g., to refresh a stale prompt) inflates the review-cycle counter and writes a fresh `review-cycle-N.md` file even when no reviewer rejected anything. The counter then misrepresents how many real review rounds the WP has been through.

**FRs**: FR-008, FR-009, FR-010 · **NFR**: NFR-005 · **SC**: SC-004 · **Spec sections**: Scenario 4, Domain Language ("Review cycle") · **Data shape**: [data-model.md §3](../data-model.md)

## Always-true rules

- The counter is monotonic non-decreasing.
- The counter changes by exactly **+1** per real rejection event, never on `implement` reruns.
- For each integer `N` in `[1, count]`, exactly one `review-cycle-N.md` artifact exists.

---

## Subtask T018 — Identify rejection event handler and reclaim/regenerate code path

**Purpose**: Map the existing surfaces before changing them.

**Steps**:

1. In `src/specify_cli/cli/commands/agent/workflow.py`, locate:
   - The path that runs when `spec-kitty agent action implement WPNN` is invoked (call this the **implement entrypoint**).
   - The path that handles a reviewer **rejection** event (call this the **rejection handler**). It may live in a sibling module — note the file:line.
2. List every site that currently:
   - Writes `review-cycle-N.md`.
   - Mutates the counter (whatever name it has — `cycle_count`, `review_round`, etc.).
3. Document this map at the top of the WP's PR description (or in a comment in `workflow.py`).

**Output**: a precise inventory of counter-mutating sites — needed to validate that T019 + T020 close all of them.

---

## Subtask T019 — Move counter advancement into the rejection handler exclusively

**Purpose**: Single source of truth for counter increments.

**Steps**:

1. In the rejection handler (from T018), add (or keep) the single advancement:
   ```python
   def _on_review_rejection(wp_id: str, ...) -> None:
       counter = _read_counter(wp_id)
       new_count = counter + 1
       _write_counter(wp_id, new_count)
       _write_review_cycle_artifact(wp_id, new_count)
   ```
2. The artifact-writing helper MUST be scoped to this handler. Any other site that writes `review-cycle-N.md` becomes a candidate for removal in T020.
3. If multiple paths emit a rejection event, ensure they funnel through one handler — do not duplicate the increment.

**Files to edit**:
- `src/specify_cli/cli/commands/agent/workflow.py` (or the rejection-handler file identified in T018)

**Acceptance**:
- A grep for counter-mutating writes in the codebase returns exactly one site (the rejection handler).

---

## Subtask T020 — Make reclaim/regenerate idempotent

**Purpose**: Eliminate the spurious increment on `implement` reruns.

**Steps**:

1. In the implement entrypoint, remove every counter mutation that runs on a non-rejection path. Specifically:
   - Do not call `_write_counter` from the implement entrypoint.
   - Do not call `_write_review_cycle_artifact` from the implement entrypoint.
2. If the entrypoint uses a "regenerate the implement prompt" path that previously re-emitted a `review-cycle-N.md`, replace that with re-rendering the **implement-prompt** file (a different artifact) without touching the cycle counter.
3. Add an assertion in tests (T021): re-running `implement` against a `for_review` WP three times produces zero counter delta.

**Files to edit**:
- `src/specify_cli/cli/commands/agent/workflow.py`

**Acceptance**:
- After this subtask, `agent action implement WPNN` is observed to be a counter-no-op.

---

## Subtask T021 — Unit tests: ≥3 reruns of implement leave counter unchanged  [P]

**Purpose**: Lock in idempotency.

**Steps**:

1. Create `tests/specify_cli/cli/commands/agent/test_review_cycle_counter.py`.
2. Tests:
   - `test_implement_rerun_does_not_advance_counter`: arrange a WP in `for_review`; run the implement entrypoint 3 times; assert the counter equals the starting value and no new `review-cycle-N.md` file appeared on disk.
   - `test_counter_starts_at_zero_on_fresh_wp`: arrange a freshly-claimed WP; assert counter == 0 and no review-cycle artifacts exist.
   - `test_counter_is_monotonic`: simulate a rejection event 3 times in sequence; assert counter goes 0 → 1 → 2 → 3 and there are exactly three `review-cycle-N.md` artifacts at indices 1, 2, 3.

**Files to create**:
- `tests/specify_cli/cli/commands/agent/test_review_cycle_counter.py` (~140 lines)

---

## Subtask T022 — Integration test: real rejection advances counter exactly once

**Purpose**: End-to-end proof.

**Steps**:

1. Create `tests/integration/test_review_cycle_rejection_only.py`.
2. Test scenario:
   - Set up a mission + WP via the runtime fixtures.
   - Drive the WP to `for_review`.
   - Re-run `agent action implement` 2 times → assert counter unchanged, no new artifact.
   - Trigger a real rejection event (use whichever harness/fixture the existing review-pipeline tests use).
   - Assert counter advanced by exactly 1, exactly one new `review-cycle-N.md` artifact at the new N.
   - Re-run `agent action implement` again → assert counter unchanged.

**Files to create**:
- `tests/integration/test_review_cycle_rejection_only.py` (~120 lines)

---

## Test Strategy

- **Unit**: T021 covers the idempotency contract directly.
- **Integration**: T022 proves the rejection-only advancement end-to-end.
- **Property**: counter is monotonic non-decreasing across the WP lifecycle (asserted in `test_counter_is_monotonic`).
- **Coverage**: ≥ 90% on changed code (NFR-002).
- **Type safety**: `mypy --strict` clean.

## Definition of Done

- [ ] T018 — counter-mutating sites inventoried.
- [ ] T019 — counter advancement only in the rejection handler.
- [ ] T020 — implement entrypoint is counter-no-op.
- [ ] T021 — unit tests pass (idempotency + monotonicity).
- [ ] T022 — integration test passes (rejection advances by exactly one).
- [ ] `mypy --strict` clean on touched modules.

## Risks

- **Risk**: A counter mutation site is missed (e.g., a deeply nested helper).
  **Mitigation**: T018's grep produces an exhaustive inventory; T019 must close every entry; T021 + T022 lock the contract.
- **Risk**: WP03's small edit in `workflow.py` collides with WP04's bigger refactor.
  **Mitigation**: This WP depends on WP03 and runs in the same lane workspace. Pull in WP03's edits first; merge cleanly.
- **Risk**: Removing the implement-side counter write breaks a downstream consumer that read the artifact regardless of counter advancement.
  **Mitigation**: Search for readers of `review-cycle-N.md`; verify only the review pipeline reads them.

## Reviewer guidance

- Confirm there is **exactly one** site that mutates the counter and **exactly one** site that writes `review-cycle-N.md` (both in the rejection handler).
- Check the test that re-runs `implement` 3+ times is a true rerun (not an early-return short-circuit that hides a regression).
- Check the monotonicity property test exists and passes.
- Confirm no behavior changes for the happy review path: legitimate rejections still produce one artifact + one increment each.

## Out of scope

- Changes to the review pipeline's rejection-event protocol.
- New CLI flags or commands.
- Schema migration for projects with already-inflated counters (operators can correct manually if needed; not in this tranche).
