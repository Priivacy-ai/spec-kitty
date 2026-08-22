---
work_package_id: WP10
title: Audit registration + value round-trip
dependencies: []
requirement_refs:
- FR-014
- FR-015
- FR-016
planning_base_branch: fix/worktree-root-resolution
merge_target_branch: fix/worktree-root-resolution
branch_strategy: Planning artifacts for this mission were generated on fix/worktree-root-resolution. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/worktree-root-resolution unless the human explicitly redirects the landing branch.
subtasks:
- T030
- T031
- T032
- T033
- T034
phase: Phase 2 - Event-log integrity
history:
- at: '2026-08-18T21:17:46Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/audit/shape_registry.py
create_intent:
- tests/specify_cli/audit/test_status_event_row_shape.py
- tests/specify_cli/status/test_snapshot_round_trip.py
- tests/specify_cli/status/test_reducer_projection_sentinel.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/audit/shape_registry.py
- tests/specify_cli/audit/test_status_event_row_shape.py
- tests/specify_cli/status/test_snapshot_round_trip.py
- tests/specify_cli/status/test_reducer_projection_sentinel.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP10 – Audit registration + value round-trip

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `implementer-ivan`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log.
- **You must address all feedback** before your work is complete.
- **Report progress**: Update the Activity Log as you go.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks.

---

## Objectives & Success Criteria

Close the audit residual so a review-carrying event row audits clean, and guarantee snapshots survive replay **by value**.

Done when:
- `review_result` is registered in the `status_event_row` shape; a review-carrying row audits with **0 `UNKNOWN_SHAPE`**.
- A **new `status_event_row`-scoped** drift test fails when a persisted event shape is unregistered (independent of the existing `meta.json`-scoped `test_shape_registry_writer_parity.py`).
- A **value-equality** round-trip property holds (replayed projection **equals** the snapshot by value, not merely key-presence) with a **non-vacuous** generator (≥1 `review_result`-carrying event); a corrupted-value replay **fails**.
- A **green sentinel** pins the already-fixed reducer projection (`407ea376c4`) — stays green (NFR-004), not red-first.

## Context & Constraints

- Spec: FR-014/FR-015/FR-016, SC-005. Contracts: [C-8](../contracts/resolver-and-verdict-contracts.md).
- **C-001: do NOT re-implement the reducer projection** — it is already correct at `status/reducer.py:210-215` (`407ea376c4`). This WP only *pins* it and *registers/round-trips* around it.
- Verified base anchor: `review_result` is **absent** from the `status_event_row` frozenset at `audit/shape_registry.py:90-111` (the residual). The coordination-key shape is `META_COORDINATION_KEYS` at `:53`.
- **Do NOT repurpose** `tests/audit/test_shape_registry_writer_parity.py` — it is `meta.json`-scoped and tautological (`writer_keys ⊆ audit_keys`, both from the same annotations). Add a NEW `status_event_row`-scoped test instead.
- The coordination-key **writer** migration is a separate WP (WP12) — this WP only handles the **registry** side.

## Branch Strategy

- **Strategy**: coord-lane
- **Planning base branch**: fix/worktree-root-resolution
- **Merge target branch**: fix/worktree-root-resolution

> Populated by `spec-kitty agent mission tasks`. Do NOT change manually.

## Subtasks & Detailed Guidance

### Subtask T030 – Red-first: review_result row emits UNKNOWN_SHAPE

- **Purpose**: Prove the residual before fixing (NFR-001).
- **Steps**:
  1. Create `tests/specify_cli/audit/test_status_event_row_shape.py`.
  2. Write a `@pytest.mark.regression` test (pinned to #3543) that builds a `status_event_row` carrying a `review_result` and runs it through the audit shape check.
  3. On base this must be **RED**: the row triggers `UNKNOWN_SHAPE` because `review_result` is unregistered.
- **Files**: `tests/specify_cli/audit/test_status_event_row_shape.py` (new).
- **Validation**: red on base; green after T031.

### Subtask T031 – Register review_result in status_event_row

- **Purpose**: FR-014 — recognize the field so the row audits clean.
- **Steps**:
  1. Add `review_result` to the `status_event_row` shape frozenset at `audit/shape_registry.py:90-111`.
  2. Confirm no other required-key invariants are violated (the field is optional/nullable, matching the reducer's carry-forward semantics).
- **Files**: `src/specify_cli/audit/shape_registry.py`.
- **Validation**: the T030 test goes green; a review-carrying row emits 0 `UNKNOWN_SHAPE`.

### Subtask T032 – New status_event_row-scoped drift test

- **Purpose**: FR-016 — a real assertion that catches a persisted-but-unregistered event shape (the existing test cannot, being `meta.json`-scoped).
- **Steps**:
  1. In `tests/specify_cli/audit/test_status_event_row_shape.py`, add a drift test that enumerates the keys a persisted `status_event_row` actually carries and asserts each is registered.
  2. Make it genuinely falsifiable: add a temporary unregistered key fixture and assert the test would fail (documented, not left enabled).
- **Files**: `tests/specify_cli/audit/test_status_event_row_shape.py`.
- **Validation**: introducing an unregistered persisted key turns the test red.

### Subtask T033 – Value-equality round-trip + non-vacuous generator

- **Purpose**: FR-015 — no snapshot field is lost or corrupted on replay.
- **Steps**:
  1. Create `tests/specify_cli/status/test_snapshot_round_trip.py`.
  2. Generate event logs (property-style) guaranteed to include **≥1 `review_result`-carrying event** (non-vacuous — assert the generator emitted one).
  3. Replay each log via the reducer and assert the replayed projection **equals the snapshot by value** (deep equality on the projected fields), not merely key-presence.
  4. Add a negative case: a replay that preserves the key but corrupts the value MUST fail the assertion (guards the key-only fake).
- **Files**: `tests/specify_cli/status/test_snapshot_round_trip.py` (new).
- **Validation**: passes for faithful replay; the corrupted-value case fails; generator non-vacuity asserted.

### Subtask T034 – Green sentinel for reducer projection (NFR-004)

- **Purpose**: Pin `407ea376c4` so no later change (or a misguided red-hunt) regresses the projection.
- **Steps**:
  1. Create `tests/specify_cli/status/test_reducer_projection_sentinel.py`.
  2. Assert the last-wins + carry-forward projection at `reducer.py:210-215` holds (verdict-carrying override; sticky carry-forward otherwise).
  3. Mark it clearly as a **green sentinel** (green on base and after) — it is NOT a red-first test.
- **Files**: `tests/specify_cli/status/test_reducer_projection_sentinel.py` (new).
- **Validation**: green on base and after; do not modify `reducer.py`.

## Test Strategy (required)

- Run: `PWHEADLESS=1 pytest tests/specify_cli/audit/test_status_event_row_shape.py tests/specify_cli/status/test_snapshot_round_trip.py tests/specify_cli/status/test_reducer_projection_sentinel.py -q`.
- T030 red on `upstream/main`, green after T031; T034 green throughout; T032/T033 falsifiable as described.

## Risks & Mitigations

- **Tautology trap**: reusing the `meta.json`-scoped drift test yields a green that proves nothing. Mitigation: the new test is `status_event_row`-scoped and demonstrably falsifiable.
- **Vacuous property**: a generator that never emits `review_result` passes trivially. Mitigation: assert non-vacuity + the corrupted-value negative case.
- **Scope creep into projection**: C-001 forbids editing the reducer. Mitigation: sentinel only.

## Review Guidance

- Confirm `review_result` registered; the new drift test is falsifiable; round-trip is value-equality with non-vacuous generator + corrupted-value negative; sentinel is green and `reducer.py` untouched.

## Activity Log

- 2026-08-18T21:17:46Z – system – Prompt created.

---

### Updating Status

Status is managed via `status.events.jsonl`. Use `spec-kitty agent tasks move-task WP10 --to <status>`.
