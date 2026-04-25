---
work_package_id: WP02
title: 'ProfileInvocationExecutor.invoke(): action_hint Parameter (#794, partial)'
dependencies: []
requirement_refs:
- FR-009
- FR-010
- FR-011
- FR-012
- FR-017
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-phase6-composition-stabilization-01KQ2JAS
base_commit: 3ae47b14a200ce0d96d43a66260106df5bcc1837
created_at: '2026-04-25T15:15:48.771594+00:00'
subtasks:
- T007
- T008
- T009
- T010
shell_pid: "94539"
agent: "claude:opus:implementer:implementer"
history:
- at: '2026-04-25T15:09:39Z'
  by: tasks
  note: WP created from plan.md
authoritative_surface: src/specify_cli/invocation/
execution_mode: code_change
mission_id: 01KQ2JASW34A4K6HYNS5V41KFK
mission_slug: phase6-composition-stabilization-01KQ2JAS
owned_files:
- src/specify_cli/invocation/executor.py
- tests/specify_cli/invocation/test_invocation_e2e.py
priority: P1
tags: []
---

# WP02 — `ProfileInvocationExecutor.invoke(...)`: `action_hint` Parameter (#794, partial)

## Objective

Add a keyword-only `action_hint: str | None = None` parameter to `ProfileInvocationExecutor.invoke(...)` in `src/specify_cli/invocation/executor.py`. When `profile_hint` is supplied AND `action_hint` is truthy, record `action_hint` as the action; otherwise preserve the existing role-default-verb derivation. Do NOT change the router-backed branch.

This WP is the surface-level kwarg + tests. The call-site update in `mission_step_contracts/executor.py` lives in WP03 (which depends on this WP).

## Branch Strategy

- Planning / base branch: `main`
- Final merge target: `main`
- This WP runs in its own execution lane. The lane workspace is allocated by `finalize-tasks` and resolved by `spec-kitty agent action implement WP02 --agent <name>`.

## Spec Coverage

- FR-009 (kwarg present)
- FR-010 (hint preserved end-to-end on the `profile_hint` branch)
- FR-011 (legacy fallback when `action_hint` is None or empty)
- FR-012 (no regression for non-`profile_hint` callers)
- FR-013 (governance context reads action from record — preserved automatically)
- EDGE-005 (empty-string `action_hint` falls back)

## Context

Read these in this order:
1. `kitty-specs/phase6-composition-stabilization-01KQ2JAS/spec.md` — Scenario D, Scenario E, EDGE-005.
2. `kitty-specs/phase6-composition-stabilization-01KQ2JAS/plan.md` — "Implementation Approach: #794" section.
3. `kitty-specs/phase6-composition-stabilization-01KQ2JAS/contracts/invocation_executor_invoke.md` — behavioral matrix.
4. `kitty-specs/phase6-composition-stabilization-01KQ2JAS/research.md` — R4.
5. `src/specify_cli/invocation/executor.py` — focus on `invoke(...)` (lines 113–139), `_derive_action_from_request(...)`, `InvocationRecord` construction at line 185, `write_started(record)` at line 194.
6. `src/specify_cli/invocation/record.py` — confirm `InvocationRecord.action` field.
7. `tests/specify_cli/invocation/test_invocation_e2e.py` — existing `started`/`completed` patterns.

Do NOT edit:
- `src/specify_cli/invocation/writer.py`, `record.py`, `modes.py` — they remain frozen for this tranche.
- `src/specify_cli/mission_step_contracts/` — that is WP03's surface.
- Any file outside `owned_files`.

## Subtasks

### T007 — Extend `invoke(...)` signature with keyword-only `action_hint`

**Purpose**: Add the new parameter without affecting any existing callers.

**Steps**:
1. Update the signature of `ProfileInvocationExecutor.invoke(...)` to:
   ```python
   def invoke(
       self,
       request_text: str,
       profile_hint: str | None = None,
       actor: str = "unknown",
       mode_of_work: ModeOfWork | None = None,
       *,
       action_hint: str | None = None,
   ) -> InvocationPayload:
       ...
   ```
2. Update the docstring to describe `action_hint`: "Optional caller-supplied action key. When supplied alongside `profile_hint`, this value replaces the role-default-verb derivation. Empty strings are treated as if not supplied."
3. Do not import any new modules.

**Files**:
- `src/specify_cli/invocation/executor.py`

**Validation**:
- [ ] `mypy --strict` passes.
- [ ] All existing callers compile (positional args are unchanged).

### T008 — Apply `action_hint` truthiness inside `profile_hint`-branch

**Purpose**: When `profile_hint` is set AND `action_hint` is truthy, use it; otherwise preserve the legacy derivation.

**Steps**:
1. Inside the `if profile_hint is not None:` branch, replace:
   ```python
   action = self._derive_action_from_request(request_text, profile.role)
   ```
   with:
   ```python
   if action_hint:
       action = action_hint
   else:
       action = self._derive_action_from_request(request_text, profile.role)
   ```
2. The router-backed branch (`else:` block where `profile_hint is None`) is **unchanged**.
3. Verify the constructed `InvocationRecord(action=action, ...)` line is unchanged in shape.

**Files**:
- `src/specify_cli/invocation/executor.py`

**Validation**:
- [ ] Empty-string `action_hint` falls back to derivation (truthiness, not None-check).
- [ ] Router branch behavior is byte-identical to current main.

### T009 — Add direct unit + e2e tests for `action_hint` behavior

**Purpose**: Lock the new behavior with tests covering FR-009 through FR-012 and EDGE-005.

**Steps**:
1. In `tests/specify_cli/invocation/test_invocation_e2e.py`, add:
   - `test_invoke_with_action_hint_and_profile_hint_records_hint` parametrized over `["specify", "plan", "tasks", "implement", "review"]`. For each key:
     - Call `executor.invoke(request_text=<dummy>, profile_hint="architect-alphonso", action_hint=<key>)`.
     - Read the `started` JSONL line for the returned `payload.invocation_id`.
     - Assert `record["action"] == <key>` AND `payload.action == <key>` (or whatever the existing payload exposes for this field).
   - `test_invoke_profile_hint_only_falls_back_to_derived_action`:
     - Call with `profile_hint="architect-alphonso"` and no `action_hint`.
     - Assert the recorded action equals `_derive_action_from_request(request_text, profile.role)`.
   - `test_invoke_empty_action_hint_falls_back`:
     - Call with `profile_hint="architect-alphonso", action_hint=""`.
     - Assert the recorded action equals the derived role-default verb (same as the previous test).
   - `test_invoke_router_branch_unchanged_with_action_hint`:
     - Call with `profile_hint=None, action_hint="anything"`.
     - Assert the recorded action equals the router decision's `result.action` (NOT `"anything"`).
2. Existing `advise`/`ask`/`do` and router-backed tests MUST continue to pass without modification (FR-012). If they fail, do NOT modify them — fix the implementation.

**Files**:
- `tests/specify_cli/invocation/test_invocation_e2e.py` (~+80–120 lines)

**Validation**:
- [ ] All new tests fail BEFORE T007–T008 land.
- [ ] All new tests pass AFTER T007–T008 land.
- [ ] All existing tests still pass without modification.

### T010 — Verify focused pytest + ruff + mypy --strict

**Purpose**: Confirm WP02's surface is green.

**Steps**:
1. Run from repo root:
   ```bash
   uv run --python 3.13 --extra test python -m pytest \
     tests/specify_cli/invocation/test_invocation_e2e.py \
     tests/specify_cli/invocation/test_writer.py -q

   uv run --python 3.13 python -m ruff check \
     src/specify_cli/invocation/executor.py \
     tests/specify_cli/invocation/test_invocation_e2e.py

   uv run --python 3.13 python -m mypy --strict \
     src/specify_cli/invocation/executor.py
   ```
2. If any command fails, fix the underlying cause.

**Validation**:
- [ ] All three commands exit zero.

## Definition of Done

- [ ] All 4 subtasks completed.
- [ ] `invoke(...)` signature has keyword-only `action_hint: str | None = None`.
- [ ] `profile_hint`-branch uses `action_hint` when truthy.
- [ ] Router branch unchanged.
- [ ] All new and existing tests in `test_invocation_e2e.py` pass.
- [ ] `executor.py` passes `ruff check` and `mypy --strict`.
- [ ] No edits in any file outside `owned_files`.

## Reviewer Guidance

- Verify the `*` separator makes `action_hint` keyword-only.
- Verify the truthiness check (`if action_hint:`) — not `if action_hint is not None:`.
- Verify the router-backed branch is byte-identical.
- Verify no edits leak into `mission_step_contracts/` (that's WP03).

## Risks (per WP)

- **Positional drift**: prevented by `*` keyword-only separator and mypy --strict.
- **Silent legacy-fallback regression**: explicit empty-string and `None` fallback tests; existing tests must pass unchanged.

## Activity Log

- 2026-04-25T15:15:50Z – claude:opus:implementer:implementer – shell_pid=94539 – Assigned agent via action command
