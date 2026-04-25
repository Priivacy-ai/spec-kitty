---
work_package_id: WP01
title: 'Runtime Bridge: Stop Legacy DAG Fall-Through (#786)'
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-015
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
history:
- at: '2026-04-25T15:09:39Z'
  by: tasks
  note: WP created from plan.md
authoritative_surface: src/specify_cli/next/
execution_mode: code_change
mission_id: 01KQ2JASW34A4K6HYNS5V41KFK
mission_slug: phase6-composition-stabilization-01KQ2JAS
owned_files:
- src/specify_cli/next/runtime_bridge.py
- tests/specify_cli/next/test_runtime_bridge_composition.py
priority: P0
tags: []
---

# WP01 — Runtime Bridge: Stop Legacy DAG Fall-Through (#786)

## Objective

Make composition-backed `software-dev` actions single-dispatch in `src/specify_cli/next/runtime_bridge.py`. After successful composition for an action in `{specify, plan, tasks, implement, review}`, the legacy DAG dispatch handler (the path that runs the action via `runtime_next_step(...)`) MUST NOT execute. Run-state, lane-status events, and prompt progression MUST still advance via a new helper.

This WP is the explicit blocker on `#505` (custom mission loader); landing it first is mission-critical.

## Branch Strategy

- Planning / base branch: `main`
- Final merge target: `main`
- This WP runs in its own execution lane. The lane workspace is allocated by `finalize-tasks` and resolved by `spec-kitty agent action implement WP01 --agent <name>`.

## Spec Coverage

- FR-001 (single-dispatch invariant)
- FR-002 (run-state still advances)
- FR-003 (fixed `tasks` guard semantics preserved)
- FR-004 (no `mission-runtime.yaml` edits)
- FR-005 (`Decision` shape stable)
- FR-015 (negative-condition tests)
- EDGE-002 (non-composed actions unchanged)
- EDGE-003 (helper-failure path)

## Context

Read these in this order:
1. `kitty-specs/phase6-composition-stabilization-01KQ2JAS/spec.md` — Scenario A, EDGE-002, EDGE-003.
2. `kitty-specs/phase6-composition-stabilization-01KQ2JAS/plan.md` — "Implementation Approach: #786" section.
3. `kitty-specs/phase6-composition-stabilization-01KQ2JAS/contracts/runtime_bridge_dispatch.md` — single-dispatch invariant + state diagram.
4. `kitty-specs/phase6-composition-stabilization-01KQ2JAS/research.md` — R1, R2.
5. `src/specify_cli/next/runtime_bridge.py` — focus on lines 393–486 (`_dispatch_via_composition`) and lines 980–991 (`decide_next_via_runtime`).
6. `src/specify_cli/next/decision.py` — the `Decision` dataclass; do not change its shape.
7. `tests/specify_cli/next/test_runtime_bridge_composition.py` — the existing scaffolding you will extend.

Do NOT edit:
- `mission-runtime.yaml` (either copy)
- `tasks.step-contract.yaml`
- `_check_composed_action_guard(...)` body or call site (it must remain BEFORE the new helper)
- Any file outside `owned_files`.

## Subtasks

### T001 — Audit runtime_bridge.py and lock in the design

**Purpose**: Before changing code, walk the runtime bridge and confirm the call sites and primitives `runtime_next_step(...)` uses for lane events and run-state advancement.

**Steps**:
1. Read `src/specify_cli/next/runtime_bridge.py` end-to-end.
2. Locate `_dispatch_via_composition(...)` (lines 393–486). Note where it returns `None` on success (line 485).
3. Locate `_check_composed_action_guard(...)` invocation (lines 480–482). This MUST stay where it is.
4. Locate `decide_next_via_runtime(...)` (line 981) and the unconditional fall-through to `runtime_next_step(...)` (lines 986–991).
5. Locate every emitter / state-write `runtime_next_step(...)` performs that the new helper must reuse: `SyncRuntimeEventEmitter` (initialized lines 764–768), the mission-state advancement primitive, and the next-public-step computation. Confirm those are reachable from `_dispatch_via_composition` scope (or extract a shared helper).
6. Write a 5-line block comment in `runtime_bridge.py` (above `_advance_run_state_after_composition` once you add it in T002) summarizing this single-dispatch invariant — this is the only code comment you should add.

**Validation**:
- [ ] Lines and seams match the audit notes.
- [ ] No code edits yet.

### T002 — Add `_advance_run_state_after_composition(...)` helper

**Purpose**: Add a composition-specific advancement helper that performs run-state / lane-event / next-step progression without entering the legacy DAG action handler.

**Steps**:
1. Add a new module-level function `_advance_run_state_after_composition(...)` near `_dispatch_via_composition(...)`. Match its parameter list to whatever the existing primitives need (likely `repo_root`, `action`, `mission_handle`/`feature_dir`, plus the same emitter the existing code already constructs).
2. The body must:
   - Emit lane status events via the same `SyncRuntimeEventEmitter` the legacy path uses.
   - Advance mission state via the same primitive `runtime_next_step(...)` calls.
   - Compute the next public step.
   - Return a `Decision` whose field set is identical to what `runtime_next_step(...)` would return for the same advance — but constructed without invoking the legacy DAG action handler.
3. Reuse, don't reimplement: extract a shared helper from `runtime_next_step(...)` if the smallest non-duplicating change requires it. Do NOT add a second mission runner.
4. Type-annotate fully so `mypy --strict` is happy.

**Files**:
- `src/specify_cli/next/runtime_bridge.py` (~+30–60 lines)

**Validation**:
- [ ] mypy --strict passes on `runtime_bridge.py`.
- [ ] No imports added from outside `src/specify_cli/`.
- [ ] No new public symbols.

### T003 — Make `_dispatch_via_composition(...)` return `Decision` on success

**Purpose**: Have `_dispatch_via_composition(...)` return a `Decision` directly on the success path (constructed via `_advance_run_state_after_composition(...)`), so the caller can short-circuit the legacy fall-through.

**Steps**:
1. Inside `_dispatch_via_composition(...)`, after `StepContractExecutor.execute(...)` returns successfully and `_check_composed_action_guard(...)` passes, call `_advance_run_state_after_composition(...)` and return its `Decision`.
2. The early-error return paths (where the function already returns a `Decision`) are unchanged.
3. The function is no longer documented as "returns `None` on success"; update its docstring.

**Files**:
- `src/specify_cli/next/runtime_bridge.py`

**Validation**:
- [ ] Function never returns `None` on the success path.
- [ ] Existing early-error paths are byte-identical.
- [ ] `_check_composed_action_guard(...)` still runs BEFORE the new helper.

### T004 — Update `decide_next_via_runtime(...)` to short-circuit on composition success

**Purpose**: Treat a non-`None` return from `_dispatch_via_composition(...)` as a terminal `Decision`. Do not fall through to `runtime_next_step(...)` for composed actions.

**Steps**:
1. In `decide_next_via_runtime(...)` (line 981), capture the result of `_dispatch_via_composition(...)`.
2. If non-`None`, return it immediately.
3. If `None` (which now means "this action is not in the composition allow-list"), keep the existing fall-through to `runtime_next_step(...)` byte-identical.
4. Do not change the public `Decision` shape.

**Files**:
- `src/specify_cli/next/runtime_bridge.py`

**Validation**:
- [ ] Non-composed actions still reach `runtime_next_step(...)` with no observable change.
- [ ] Composed actions never reach `runtime_next_step(...)` after a successful dispatch.

### T005 — Add negative-condition + advancement + non-composed regression tests

**Purpose**: Lock the single-dispatch invariant with tests that fail loudly if any future change re-introduces the fall-through.

**Steps**:
1. In `tests/specify_cli/next/test_runtime_bridge_composition.py`:
   - Add `test_composition_success_skips_legacy_dispatch[<action>]` parametrized over `{specify, plan, tasks, implement, review}`. Patch the legacy DAG action handler entry point (whatever `runtime_next_step(...)` invokes for action dispatch) and assert it is **not called** when `_dispatch_via_composition(...)` succeeds for each action.
   - Add `test_composition_success_advances_run_state_and_lane_events`. Use a fake or recording `SyncRuntimeEventEmitter` and the existing fixtures to assert the expected lane events fire exactly once per call.
   - Add `test_decision_shape_unchanged_for_composed_action`. Snapshot the `Decision` field set against a reference dict (or compare against the legacy-path baseline using a parametrized fixture).
   - Add `test_non_composed_action_uses_legacy_runtime_next_step`. Pick an action that is NOT in the composition allow-list and assert `runtime_next_step(...)` is called.
   - Add `test_advancement_helper_failure_propagates_no_legacy_fallback`. Patch `_advance_run_state_after_composition(...)` to raise; assert the error surfaces via the existing `Decision` error shape AND that the legacy dispatch handler is **not** entered as a fallback.
2. Existing tests for `tasks_outline` / `tasks_packages` / `tasks_finalize` guards MUST continue to pass without modification (FR-003).

**Files**:
- `tests/specify_cli/next/test_runtime_bridge_composition.py` (~+150–200 lines)

**Validation**:
- [ ] All new tests fail BEFORE T002–T004 land.
- [ ] All new tests pass AFTER T002–T004 land.
- [ ] All existing tests still pass without modification.

### T006 — Verify focused pytest + ruff + mypy --strict

**Purpose**: Confirm the WP's surface is green per NFR-001/NFR-002/NFR-003.

**Steps**:
1. Run from repo root:
   ```bash
   uv sync --python 3.13 --extra test

   uv run --python 3.13 --extra test python -m pytest \
     tests/specify_cli/next/test_runtime_bridge_composition.py -q

   uv run --python 3.13 python -m ruff check \
     src/specify_cli/next/runtime_bridge.py \
     tests/specify_cli/next/test_runtime_bridge_composition.py

   uv run --python 3.13 python -m mypy --strict \
     src/specify_cli/next/runtime_bridge.py
   ```
2. If any command fails, fix the underlying cause; do not mute warnings or use `# type: ignore` without justification.

**Validation**:
- [ ] All three commands exit zero.

## Definition of Done

- [ ] All 6 subtasks completed.
- [ ] Existing `test_runtime_bridge_composition.py` tests still pass.
- [ ] New `test_composition_success_skips_legacy_dispatch[...]` tests pass for all 5 composed actions.
- [ ] New advancement, decision-shape, non-composed-regression, and helper-failure tests pass.
- [ ] `runtime_bridge.py` passes `ruff check` and `mypy --strict`.
- [ ] No edits in any file outside `owned_files`.
- [ ] No new dependencies added.
- [ ] No edits to `mission-runtime.yaml` (either copy).

## Reviewer Guidance

- Verify `_check_composed_action_guard(...)` still runs BEFORE `_advance_run_state_after_composition(...)`.
- Verify the new helper does NOT call the legacy DAG action handler (read the body line-by-line).
- Verify the `Decision` field set is identical between composed and legacy paths.
- Confirm no `mission-runtime.yaml` is edited.
- Spot-check that `SyncRuntimeEventEmitter` is reused, not re-instantiated in a divergent way.

## Risks (per WP)

- **Duplicate lane events**: enumerate emissions before adding the helper; the new test asserts each event fires exactly once.
- **Re-introducing the P0 `tasks` guard regression**: keep `_check_composed_action_guard(...)` BEFORE the new helper; existing `tasks_*` guard tests must pass without modification.
- **Helper raises silently and falls back to legacy**: the new `test_advancement_helper_failure_propagates_no_legacy_fallback` test catches this.
