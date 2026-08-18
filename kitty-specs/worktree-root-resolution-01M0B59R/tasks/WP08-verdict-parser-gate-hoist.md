---
work_package_id: WP08
title: verdict parser + for_review gate hoist
dependencies: []
requirement_refs:
- FR-011
planning_base_branch: fix/worktree-root-resolution
merge_target_branch: fix/worktree-root-resolution
branch_strategy: Planning artifacts for this mission were generated on fix/worktree-root-resolution. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/worktree-root-resolution unless the human explicitly redirects the landing branch.
subtasks:
- T022
- T023
- T024
- T025
phase: Phase 1 - Verdict seam
history:
- at: '2026-08-18T21:17:24Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/lanes/for_review_gate.py
create_intent:
- src/specify_cli/status/review_result_parse.py
- src/specify_cli/lanes/for_review_gate.py
- tests/specify_cli/lanes/test_for_review_gate_parity.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/orchestrator_api/commands.py
- src/specify_cli/status/review_result_parse.py
- src/specify_cli/lanes/for_review_gate.py
- tests/specify_cli/lanes/test_for_review_gate_parity.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP08 – verdict parser + for_review gate hoist

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `implementer-ivan`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks.

---

## Objectives & Success Criteria

Hoist the two verdict-seam primitives out of `orchestrator_api/commands.py` into shared homes so both `agent status emit` (WP09) and `orchestrator-api transition` enforce **one** validator and **one** topology-aware `for_review` gate — with a **surface-neutral error contract**.

Done when:
- `_parse_review_result_json` lives in `status/review_result_parse.py` (co-located with `ReviewResult`); `orchestrator-api transition` delegates to it.
- `_enforce_for_review_commit_gate` lives in `lanes/for_review_gate.py`, returning a **decision object** (never raising the orchestrator envelope `_fail`/`NoReturn`); each surface renders its own failure.
- The gate is topology-aware in **both** directions: a clone with satisfied commits **passes** and a clone with unsatisfied commits **fails** — asserted identically for both surfaces (red-first T025).
- `ruff` + `mypy` clean; no new import cycle; complexity ≤15.

## Context & Constraints

- Independent of WP01 (the verdict seam does not need the checkout-identity guard). Can start immediately. **Gates WP09** (WP09 consumes both hoisted units).
- Shared-package boundary: verified this hoist is intra-`specify_cli` and does not touch the boundary (which only forbids retired external imports).
- **Why `lanes`, not `status`, for the gate**: `status` already has a bidirectional deferred-import cycle with `lanes` (`status/aggregate.py` ↔ `lanes/recovery.py`, under `PLC0415`). The gate imports `lanes._git` + `lanes.worktree_allocator.predict_lane_worktree`, so parking it in `status` risks hardening that cycle. A `lanes`-side leaf avoids it. The parser has no such coupling → `status` is its natural home.
- Anchors (verify at implement time): `orchestrator_api/commands.py:1297` `_parse_review_result_json` (called `:1399`); `:1257` `_enforce_for_review_commit_gate` (called `:1413`, uses `predict_lane_worktree` at `:1281`); `_fail` at `:223` (envelope `NoReturn` — do NOT drag into the CLI); `ReviewResult` at `status/models.py:286`.
- Supporting docs: `spec.md` (FR-011), `data-model.md` (ForReviewCommitGate INV-13/14), `contracts/…` (C-7), `research.md` (Decision 3).

## Branch Strategy

- **Strategy**: lane-per-WP (coord topology)
- **Planning base branch**: fix/worktree-root-resolution
- **Merge target branch**: fix/worktree-root-resolution

> Execution worktrees are allocated per computed lane from `lanes.json`. Do not change these fields manually.

## Subtasks & Detailed Guidance

### Subtask T022 – Hoist `_parse_review_result_json` → `status/review_result_parse.py`

- **Purpose**: One validator for both surfaces (single canonical authority).
- **Steps**:
  1. Create `src/specify_cli/status/review_result_parse.py` exposing a public `parse_review_result_json(raw) -> ReviewResult` (depends only on `json`, `ReviewResult`, `event_verdicts` — all already in `status`).
  2. Move the body from `orchestrator_api/commands.py:1297` verbatim; keep validation/error semantics identical.
  3. Re-export or import it back in `commands.py` so the transition call site (`:1399`) uses the hoisted function (no behavior change there).
- **Files**: `src/specify_cli/status/review_result_parse.py` (new, ~60 lines), `src/specify_cli/orchestrator_api/commands.py`.
- **Notes**: No new cycle — both surfaces already import `status`.

### Subtask T023 – Hoist the gate → `lanes/for_review_gate.py` with a surface-neutral contract

- **Purpose**: One gate, no envelope leakage.
- **Steps**:
  1. Create `src/specify_cli/lanes/for_review_gate.py` exposing `evaluate_for_review_gate(...) -> GateDecision` where `GateDecision` carries `passed: bool`, `reason`, and any data the caller needs to render a failure — it **returns**, never raises `_fail`.
  2. Move the logic from `commands.py:1257` (including the `predict_lane_worktree` topology check at `:1281`) into the leaf; make it topology-aware such that a clone is evaluated on **commit state**, not failed on topology.
  3. Keep it a leaf: import only `lanes._git` / `lanes.worktree_allocator`; do not import `orchestrator_api` or `status` aggregates.
- **Files**: `src/specify_cli/lanes/for_review_gate.py` (new, ~120 lines).

### Subtask T024 – orchestrator-api transition delegates to both

- **Purpose**: Prove parity from the orchestrator side.
- **Steps**:
  1. In `commands.py`, replace the inline gate call (`:1413`) with `evaluate_for_review_gate(...)` and render the envelope `_fail` from the returned `GateDecision` (envelope stays in the orchestrator, not the leaf).
  2. Replace the inline parse (`:1399`) with the hoisted `parse_review_result_json`.
  3. Confirm no behavior change for existing orchestrator-api transition tests.
- **Files**: `src/specify_cli/orchestrator_api/commands.py`.

### Subtask T025 – Red-first: both-direction gate parity on both surfaces

- **Purpose**: Prevent an always-pass-for-clone fake (NFR-001, contract C-7).
- **Steps**:
  1. In `tests/specify_cli/lanes/test_for_review_gate_parity.py`, assert for {primary, worktree, clone}: satisfied commits → pass; **unsatisfied commits → fail** — identically via `evaluate_for_review_gate` and via the orchestrator-api transition path.
  2. Include the clone-unsatisfied negative case explicitly. `@pytest.mark.regression`, pin #3547.
  3. Author red where meaningful (on base the gate fails a clone on topology rather than commit state).
- **Files**: `tests/specify_cli/lanes/test_for_review_gate_parity.py` (new, ~130 lines).
- **Parallel?**: [P].

## Test Strategy

- `test_for_review_gate_parity.py`: the both-direction matrix above.
- Run existing orchestrator-api transition tests to confirm no regression: `pytest tests/ -k "transition and for_review" -n0 -q`.
- `pytest tests/specify_cli/lanes/test_for_review_gate_parity.py -n0 -q`.

## Risks & Mitigations

- **Risk**: envelope semantics leak into the leaf (breaks the CLI surface in WP09). **Mitigation**: the leaf returns `GateDecision`; only the orchestrator renders `_fail`. Reviewer checks for any `_fail`/`NoReturn` import in the leaf.
- **Risk**: import cycle if the gate lands in `status`. **Mitigation**: gate lives in `lanes`; parser in `status`.

## Review Guidance

- Confirm the leaf never raises the orchestrator envelope and imports no `status` aggregate.
- Confirm both gate directions are asserted on both surfaces.

## Activity Log

- 2026-08-18T21:17:24Z – system – Prompt created.
