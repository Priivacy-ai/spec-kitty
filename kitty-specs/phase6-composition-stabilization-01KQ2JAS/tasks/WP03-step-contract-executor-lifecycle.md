---
work_package_id: WP03
title: 'StepContractExecutor: Pass action_hint and Close Invocation Lifecycles (#794+#793)'
dependencies:
- WP02
requirement_refs:
- FR-006
- FR-007
- FR-008
- FR-013
- FR-014
- FR-016
planning_base_branch: main
merge_target_branch: main
branch_strategy: lane_per_wp
subtasks:
- T011
- T012
- T013
- T014
- T015
- T016
history:
- at: '2026-04-25T15:09:39Z'
  by: tasks
  note: WP created from plan.md
authoritative_surface: src/specify_cli/mission_step_contracts/
execution_mode: code_change
mission_id: 01KQ2JASW34A4K6HYNS5V41KFK
mission_slug: phase6-composition-stabilization-01KQ2JAS
owned_files:
- src/specify_cli/mission_step_contracts/executor.py
- tests/specify_cli/mission_step_contracts/test_software_dev_composition.py
priority: P1
tags: []
---

# WP03 — StepContractExecutor: Pass `action_hint` and Close Invocation Lifecycles (#794 completion + #793)

## Objective

In `src/specify_cli/mission_step_contracts/executor.py`, `StepContractExecutor.execute(...)`:

1. **(#794 completion)** Pass `action_hint=selected_contract.action` on every `ProfileInvocationExecutor.invoke(...)` call.
2. **(#793)** Wrap each per-step body in `try/except/else` so that every invocation started by the executor is closed via `ProfileInvocationExecutor.complete_invocation(...)` — `outcome="done"` on success, `outcome="failed"` on exception (and re-raise).

No direct JSONL writes are introduced; all closure flows through the existing `complete_invocation(...)` API.

## Branch Strategy

- Planning / base branch: `main`
- Final merge target: `main`
- This WP **depends on WP02**. Implementation must wait until WP02's `action_hint` kwarg has landed on `main` (or in the shared lane base, depending on lane allocation).
- Resolved via `spec-kitty agent action implement WP03 --agent <name>`.

## Spec Coverage

- FR-006 (`started` paired with `completed` for success)
- FR-007 (`started` paired with `failed` for exception)
- FR-008 (no direct JSONL writes; close via API)
- FR-013 (governance context uses contract action when hint supplied)
- FR-014 (call-site passes `action_hint`)
- FR-016 (e2e regression)
- FR-017 (paired tests)
- EDGE-001 (mid-step exception)
- EDGE-004 (multi-step pairing)

## Context

Read these in this order:
1. `kitty-specs/phase6-composition-stabilization-01KQ2JAS/spec.md` — Scenarios B, C, D; EDGE-001, EDGE-004.
2. `kitty-specs/phase6-composition-stabilization-01KQ2JAS/plan.md` — "Implementation Approach: #793" and "#794" sections.
3. `kitty-specs/phase6-composition-stabilization-01KQ2JAS/contracts/step_contract_executor_lifecycle.md` — pseudocode + outcome semantics.
4. `kitty-specs/phase6-composition-stabilization-01KQ2JAS/research.md` — R3, R5.
5. `src/specify_cli/mission_step_contracts/executor.py` — focus on `execute(...)` (lines 135–192) and the `invoke(...)` call at line 159.
6. `src/specify_cli/invocation/executor.py` — confirm WP02's `action_hint` is in place before starting (this WP depends on WP02).
7. `tests/specify_cli/mission_step_contracts/test_software_dev_composition.py` — existing scaffolding to extend.

Do NOT edit:
- `src/specify_cli/invocation/` — frozen here (was WP02's surface).
- `src/specify_cli/next/` — frozen here (was WP01's surface).
- `mission-runtime.yaml` (either copy).
- `tasks.step-contract.yaml`.
- Any file outside `owned_files`.

## Subtasks

### T011 — Pass `action_hint=selected_contract.action`

**Purpose**: Wire the contract action into every composed `invoke(...)` call.

**Steps**:
1. In `StepContractExecutor.execute(...)`, locate the `invoke(...)` call at line 159.
2. Add `action_hint=selected_contract.action` as a keyword argument:
   ```python
   payload = self._invocation_executor.invoke(
       request_text=<existing>,
       profile_hint=<existing>,
       actor=<existing>,
       mode_of_work=<existing>,
       action_hint=selected_contract.action,
   )
   ```
3. If the contract action accessor is named differently in the codebase (e.g. `selected_contract.action_key`), use that; do not invent. Read the actual contract type's attributes first.

**Files**:
- `src/specify_cli/mission_step_contracts/executor.py`

**Validation**:
- [ ] mypy --strict passes.
- [ ] No new imports needed (the contract is already in scope).

### T012 — Wrap per-step body in `try/except/else` and close lifecycle

**Purpose**: Ensure every invocation started by the executor is closed with a matching `completed` (`done`) or `failed` record.

**Steps**:
1. After the `invoke(...)` call (now passing `action_hint`), wrap the existing per-step body in:
   ```python
   try:
       # existing per-step body — copied verbatim
       ...
   except Exception:
       self._invocation_executor.complete_invocation(
           payload.invocation_id,
           outcome="failed",
       )
       raise
   else:
       self._invocation_executor.complete_invocation(
           payload.invocation_id,
           outcome="done",
       )
   ```
2. The `except Exception` clause MUST re-raise the original exception (do not swallow).
3. The `else` branch contains exactly one statement (the `complete_invocation(...)` call).
4. The try/except is **per-step** — if `execute(...)` iterates multiple contract steps, each step has its own try/except so that pairing is independent (EDGE-004).
5. Do NOT catch `BaseException`; `KeyboardInterrupt` / `SystemExit` are catastrophic and intentionally bypass close.

**Files**:
- `src/specify_cli/mission_step_contracts/executor.py`

**Validation**:
- [ ] On success, every started invocation is closed with `done`.
- [ ] On exception, every started invocation is closed with `failed` and the original exception still propagates.
- [ ] No try/except spans more than one step.

### T013 — Add a one-line code comment at the close site

**Purpose**: Capture the trail-only outcome semantic in code so future readers do not interpret `"done"` as "host LLM finished generation".

**Steps**:
1. Above the `complete_invocation(payload.invocation_id, outcome="done")` line in the `else` branch, add a single comment line:
   ```python
   # outcome describes the composition-step trail only; not host-LLM generation status.
   ```
2. Do NOT add any other comments.

**Files**:
- `src/specify_cli/mission_step_contracts/executor.py`

**Validation**:
- [ ] Exactly one new comment line at the close site.
- [ ] No other comments added or removed.

### T014 — Add lifecycle-pairing tests (success, failure, multi-step)

**Purpose**: Lock FR-006, FR-007, EDGE-001, EDGE-004 with regression tests.

**Steps**:
1. In `tests/specify_cli/mission_step_contracts/test_software_dev_composition.py`, add:
   - `test_composed_action_pairs_started_with_completed`:
     - Run a composed `software-dev/specify` (or any composed action) end-to-end.
     - Glob `.kittify/events/profile-invocations/*.jsonl` for files produced by this run.
     - For each file: assert exactly one record with `event=="started"` AND exactly one record with `event=="completed"` and `outcome=="done"`. No other records.
   - `test_composed_step_failure_writes_failed_completion`:
     - Patch the per-step body (e.g. via dependency injection, monkey-patch on the inner step handler, or a fault-injection fixture) to raise a deterministic exception.
     - Assert the resulting JSONL has paired `started` + `failed` (`outcome=="failed"`).
     - Assert the original exception still propagates out of `execute(...)`.
   - `test_composed_action_multistep_pairing`:
     - If the composed contract has ≥2 steps, run it and assert each invocation is independently paired.
   - `test_composed_action_outcome_is_done_even_though_composition_does_not_run_llm`:
     - Naming-as-documentation regression guard. Run a composed action and assert the success outcome is literally `"done"`. The test name documents the trail-only semantic.

**Files**:
- `tests/specify_cli/mission_step_contracts/test_software_dev_composition.py` (~+150–200 lines)

**Validation**:
- [ ] New tests fail BEFORE T011–T013 land.
- [ ] New tests pass AFTER T011–T013 land.
- [ ] Existing tests in this file still pass without modification.

### T015 — Add governance-context-uses-contract-action and call-site-uses-action-hint tests

**Purpose**: Lock FR-013 and FR-014.

**Steps**:
1. In `tests/specify_cli/mission_step_contracts/test_software_dev_composition.py`, add:
   - `test_step_contract_executor_passes_action_hint`:
     - Use a recording mock or spy on `ProfileInvocationExecutor.invoke(...)`.
     - Run a composed `software-dev/specify` action.
     - Assert every `invoke(...)` call from the executor was invoked with `action_hint=selected_contract.action` (i.e. `"specify"` for the public action's contract steps).
   - `test_governance_context_uses_contract_action_when_hint_supplied`:
     - Run a composed `software-dev/specify` end-to-end.
     - Inspect the started JSONL record (or the governance context payload as exposed by the existing test surface) and assert `action == "specify"` (NOT `"analyze"` or any role-default verb).
   - `test_executor_uses_complete_invocation_api_only`:
     - Monkey-patch `ProfileInvocationExecutor.complete_invocation` and `InvocationWriter.write_started` / `write_completed`.
     - Run a composed action.
     - Assert `complete_invocation` was called exactly once per `invoke` call.
     - Assert `InvocationWriter.write_*` was NOT called from `mission_step_contracts/executor.py` directly (the writer is only reachable via `complete_invocation`).

**Files**:
- `tests/specify_cli/mission_step_contracts/test_software_dev_composition.py` (~+80–120 lines)

**Validation**:
- [ ] All new tests pass.
- [ ] Existing tests still pass without modification.

### T016 — Verify focused pytest + ruff + mypy --strict (and full focused suite)

**Purpose**: Confirm WP03's surface is green AND the full mission-level focused suite is green.

**Steps**:
1. Run the WP-local checks first:
   ```bash
   uv run --python 3.13 --extra test python -m pytest \
     tests/specify_cli/mission_step_contracts/test_software_dev_composition.py -q

   uv run --python 3.13 python -m ruff check \
     src/specify_cli/mission_step_contracts/executor.py \
     tests/specify_cli/mission_step_contracts/test_software_dev_composition.py

   uv run --python 3.13 python -m mypy --strict \
     src/specify_cli/mission_step_contracts/executor.py
   ```
2. Then run the full mission-level focused suite (assumes WP01 and WP02 have already merged into the integration target):
   ```bash
   uv run --python 3.13 --extra test python -m pytest \
     tests/specify_cli/next/test_runtime_bridge_composition.py \
     tests/specify_cli/mission_step_contracts/test_software_dev_composition.py \
     tests/specify_cli/invocation/test_invocation_e2e.py \
     tests/specify_cli/invocation/test_writer.py \
     -q
   ```
3. All commands must exit zero.

**Validation**:
- [ ] WP-local pytest, ruff, mypy --strict all green.
- [ ] Full focused suite green.

## Definition of Done

- [ ] All 6 subtasks completed.
- [ ] Every `invoke(...)` call from `StepContractExecutor.execute(...)` passes `action_hint=selected_contract.action`.
- [ ] Every per-step body is wrapped in `try/except/else` with `complete_invocation(...)` close on both branches.
- [ ] On success, JSONL pair is `started`+`completed` (`outcome="done"`). On exception, pair is `started`+`failed` (`outcome="failed"`); original exception re-raised.
- [ ] One-line trail-only outcome comment present at the close site.
- [ ] All new and existing tests in `test_software_dev_composition.py` pass.
- [ ] `executor.py` passes `ruff check` and `mypy --strict`.
- [ ] Full focused pytest suite green.
- [ ] No edits in any file outside `owned_files`.

## Reviewer Guidance

- Read the full `try/except/else` block; verify the original exception still propagates after `failed` close.
- Confirm the close uses `complete_invocation(...)`, not direct `InvocationWriter.write_completed(...)`.
- Confirm the `else` branch contains only the single close call.
- Confirm the per-step pairing for multi-step composed actions (no shared try/except across steps).
- Confirm `action_hint=selected_contract.action` is passed on every `invoke(...)` call from this module.
- Verify the comment captures the trail-only outcome semantic.

## Risks (per WP)

- **`BaseException` (e.g. `KeyboardInterrupt`)** bypasses close; intentional, consistent with charter expectations.
- **`complete_invocation` raises in the `else` branch**: existing failure mode; do not nest a second try/except.
- **Reviewer mistakes outcome `"done"` for "host LLM finished generation"**: the explicit named test from T014 plus the comment from T013 document the semantic.
- **Multi-step pairing collapses**: explicit multistep test from T014 catches a single shared try/except.
