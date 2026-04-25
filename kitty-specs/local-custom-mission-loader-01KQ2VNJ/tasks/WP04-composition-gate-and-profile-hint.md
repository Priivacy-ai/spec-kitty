---
work_package_id: WP04
title: Composition Gate Widening + Profile Hint Plumbing
dependencies:
- WP01
- WP03
requirement_refs:
- C-002
- C-003
- FR-006
- FR-010
- FR-012
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T018
- T019
- T020
- T021
- T022
phase: Phase 2 - Loader core
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "38425"
history:
- at: '2026-04-25T17:54:43Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/next/runtime_bridge.py
execution_mode: code_change
owned_files:
- src/specify_cli/next/runtime_bridge.py
- src/specify_cli/mission_step_contracts/executor.py
- tests/specify_cli/next/test_runtime_bridge_composition.py
- tests/next/test_composition_gate_widening.py
role: implementer
tags: []
---

# Work Package Prompt: WP04 – Composition Gate Widening + Profile Hint Plumbing

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load implementer-ivan
```

## Branch Strategy

- **Planning/base branch at prompt creation**: `main`
- **Final merge target for completed work**: `main`
- **Actual execution workspace is resolved later** by `/spec-kitty.implement`. Trust the printed lane workspace.

## Objectives & Success Criteria

Widen `_should_dispatch_via_composition` so any step whose frozen-template entry has `agent_profile` set dispatches via `StepContractExecutor`, AND ensure that `agent_profile` flows into `StepContractExecutionContext.profile_hint`. **Built-in dispatch must remain byte-identical.**

Success criteria:
1. `_should_dispatch_via_composition(mission, step_id, *, run_dir=None)` returns True for `(software-dev, "specify"|...)` AND for any custom mission whose active step has non-empty `agent_profile`.
2. `_dispatch_via_composition` receives `profile_hint=<step.agent_profile>` for custom mission dispatches.
3. Existing 21-case parametrization in `tests/specify_cli/next/test_runtime_bridge_composition.py` passes byte-identical (FR-010 regression trap).
4. `_ACTION_PROFILE_DEFAULTS` is **not** modified.
5. `mypy --strict` clean on the modified files.

## Context & Constraints

- This WP is the **highest-risk** of the implementation phases because the composition path is load-bearing for all five built-in software-dev actions. PR #797 stabilized it; do not regress.
- See [research.md](../research.md) §R-005 for the gate widening decision.
- See [data-model.md](../data-model.md) §State transitions for the dispatch flow.
- Read `src/specify_cli/next/runtime_bridge.py` lines 230-310 (composition dispatch infrastructure) and lines 1140-1210 (the call site) before editing.
- The frozen template lives at `<run_dir>/template.yaml` (or similar; check `_load_frozen_template`).
- Charter constraint: `mypy --strict` must pass.

## Subtasks & Detailed Guidance

### Subtask T018 — Extend `_should_dispatch_via_composition`

- **Purpose**: Allow custom missions with `agent_profile`-tagged steps to dispatch via `StepContractExecutor`.
- **Steps**:
  1. Open `src/specify_cli/next/runtime_bridge.py`.
  2. Locate `_should_dispatch_via_composition(mission: str, step_id: str) -> bool` (~line 297).
  3. Change signature to `_should_dispatch_via_composition(mission: str, step_id: str, *, run_dir: Path | None = None) -> bool`.
  4. New behavior:
     ```python
     def _should_dispatch_via_composition(
         mission: str,
         step_id: str,
         *,
         run_dir: Path | None = None,
     ) -> bool:
         # Existing built-in fast path (PR #797 invariant).
         composed = _COMPOSED_ACTIONS_BY_MISSION.get(mission)
         if composed is not None and _normalize_action_for_composition(step_id) in composed:
             return True

         # New: widen for any mission whose active step has agent_profile set.
         if run_dir is None:
             return False
         profile = _resolve_step_agent_profile(run_dir, step_id)
         return bool(profile)  # treat empty string as falsy
     ```
- **Files**: `src/specify_cli/next/runtime_bridge.py`.
- **Notes**: Built-in dispatch path must execute first AND short-circuit. Do not call `_resolve_step_agent_profile` for built-ins (avoids unnecessary template reloads).

### Subtask T019 — Add `_resolve_step_agent_profile()` helper

- **Purpose**: Read the frozen template and look up the active step.
- **Steps**:
  1. In `runtime_bridge.py`, add immediately after `_should_dispatch_via_composition`:
     ```python
     def _resolve_step_agent_profile(run_dir: Path, step_id: str) -> str | None:
         """Return the agent_profile field on the step matching `step_id` in the frozen template, or None.

         Returns None if the run_dir has no frozen template (run not started),
         or the step is not present.
         """
         try:
             from specify_cli.next._internal_runtime.engine import _load_frozen_template
             template = _load_frozen_template(run_dir)
         except Exception:
             return None

         # _normalize_action_for_composition handles legacy tasks_* substep ids.
         normalized = _normalize_action_for_composition(step_id)

         for step in template.steps:
             if step.id == step_id or step.id == normalized:
                 profile = step.agent_profile
                 return profile if profile else None

         return None
     ```
- **Files**: `src/specify_cli/next/runtime_bridge.py`.
- **Notes**: Function-scoped import of `_load_frozen_template` keeps module-level imports clean and matches the existing pattern in `_advance_run_state_after_composition`.

### Subtask T020 — Thread `profile_hint` into the dispatch call site

- **Purpose**: When the gate fires for a custom mission, pass the resolved `agent_profile` as `profile_hint`.
- **Steps**:
  1. In `runtime_bridge.py`, locate the dispatch call site around line 1158-1180 (inside the function that calls `_dispatch_via_composition`).
  2. Update the gate call to pass `run_dir`:
     ```python
     if (
         result == "success"
         and current_step_id
         and _should_dispatch_via_composition(
             mission_type,
             current_step_id,
             run_dir=Path(run_ref.run_dir),
         )
     ):
     ```
  3. Resolve the profile and pass it through:
     ```python
     resolved_profile = _resolve_step_agent_profile(
         Path(run_ref.run_dir),
         current_step_id,
     )
     composition_failures = _dispatch_via_composition(
         repo_root=repo_root,
         mission=mission_type,
         action=composed_action,
         actor=agent,
         profile_hint=resolved_profile,
         request_text=None,
         mode_of_work=None,
         feature_dir=feature_dir,
         legacy_step_id=current_step_id,
     )
     ```
  4. For built-in `software-dev` dispatch, `resolved_profile` is `None` (built-in templates don't set `agent_profile`). The executor's existing `_resolve_profile_hint` falls back to `_ACTION_PROFILE_DEFAULTS` for built-ins — unchanged.
- **Files**: `src/specify_cli/next/runtime_bridge.py`.
- **Notes**: Confirm `executor.py` does not need changes — `_resolve_profile_hint` already prefers `context.profile_hint` over `_ACTION_PROFILE_DEFAULTS`. **Do not modify `_ACTION_PROFILE_DEFAULTS`** (FR-008).

### Subtask T021 — Unit tests for the gate widening matrix

- **Purpose**: Lock the gate's truth table.
- **Steps**:
  1. Create `tests/next/test_composition_gate_widening.py`.
  2. Cases:
     - `test_builtin_software_dev_specify_returns_true` — `_should_dispatch_via_composition("software-dev", "specify")` → True (run_dir not needed).
     - `test_unknown_mission_no_run_dir_returns_false` — `_should_dispatch_via_composition("custom", "step1")` → False.
     - `test_custom_mission_with_agent_profile_returns_true` — fixture frozen template has `step1.agent_profile = "implementer-ivan"`; gate returns True.
     - `test_custom_mission_without_agent_profile_returns_false` — same step but `agent_profile=None`; gate returns False.
     - `test_resolve_step_agent_profile_returns_none_when_template_missing` — non-existent run_dir → None.
     - `test_resolve_step_agent_profile_normalizes_legacy_tasks_substep` — frozen template has step `tasks` only; lookup by `tasks_outline` resolves via normalization.
  3. Use `tmp_path` to write a minimal frozen template file in the layout `_load_frozen_template` expects (read its source first).
- **Files**: `tests/next/test_composition_gate_widening.py`.
- **Parallel?**: [P].

### Subtask T022 — Extend the existing composition test suite

- **Purpose**: FR-010 regression trap. Built-in dispatch must remain byte-identical post-widening.
- **Steps**:
  1. Open `tests/specify_cli/next/test_runtime_bridge_composition.py`.
  2. **Do not** modify any existing test; only add new tests.
  3. Add a class `TestCustomMissionComposition` with:
     - `test_custom_mission_with_agent_profile_dispatches_via_composition` — set up a custom mission frozen template with one composed step (`agent_profile="implementer-ivan"`), advance the runtime to that step, patch `StepContractExecutor.execute` to return a fake result, assert it was called with `profile_hint="implementer-ivan"`.
     - `test_builtin_software_dev_unchanged_after_widening` — re-run one of the existing parametrized cases, assert the executor was called with `profile_hint=None` (built-ins don't set it; `_ACTION_PROFILE_DEFAULTS` resolves it inside the executor).
  4. Use existing fixtures (`composed_software_dev_project`) where possible; build a sibling `composed_custom_project` fixture if needed.
- **Files**: `tests/specify_cli/next/test_runtime_bridge_composition.py`.
- **Notes**: This file was already touched by the #798 preflight; keep diffs additive. Ensure existing 21 tests still pass.

## Test Strategy (charter required)

```bash
UV_PYTHON=3.13.9 uv run --no-sync pytest tests/specify_cli/next/test_runtime_bridge_composition.py tests/next/test_composition_gate_widening.py tests/next/test_internal_runtime_parity.py tests/architectural/test_shared_package_boundary.py -q
UV_PYTHON=3.13.9 uv run --no-sync mypy --strict src/specify_cli/next/runtime_bridge.py
UV_PYTHON=3.13.9 uv run --no-sync ruff check src/specify_cli/next/runtime_bridge.py tests/next/test_composition_gate_widening.py tests/specify_cli/next/test_runtime_bridge_composition.py
```

The 21-case parametrization in `test_runtime_bridge_composition.py` MUST stay green. If any of those cases fail, the gate widening regressed built-in dispatch — STOP and revert to the failing diff before proceeding.

## Risks & Mitigations

- **Risk (HIGHEST)**: Widening the gate accidentally diverts a built-in dispatch.
  - **Mitigation**: Built-in fast path is the FIRST branch in the gate and short-circuits. T022 explicitly asserts `profile_hint=None` for built-ins.
- **Risk**: `_load_frozen_template` raises before the run is started (e.g., during the very first `decide_next_via_runtime` call).
  - **Mitigation**: `_resolve_step_agent_profile` swallows exceptions and returns None. T021 covers this.
- **Risk**: Importing `_load_frozen_template` at module level creates a circular import.
  - **Mitigation**: Function-scoped import (matches the existing pattern at line 543 area).
- **Risk**: A reviewer or future contributor expands `_ACTION_PROFILE_DEFAULTS` to "fix" custom missions.
  - **Mitigation**: Add a comment above `_ACTION_PROFILE_DEFAULTS` in `executor.py`:
    ```python
    # FR-008 / Phase 6 #505: this table is for built-in missions ONLY.
    # Custom missions MUST resolve profile_hint via PromptStep.agent_profile.
    # See kitty-specs/local-custom-mission-loader-01KQ2VNJ/research.md §R-003.
    ```
    Comment-only addition is allowed; no behavior change.

## Review Guidance

- Reviewer runs `git diff --stat src/specify_cli/next/runtime_bridge.py` and confirms the change is small (target: < 50 lines added).
- Reviewer runs the full 21-case parametrization and confirms PASS.
- Reviewer confirms no `_ACTION_PROFILE_DEFAULTS` entries added.
- Reviewer confirms `_should_dispatch_via_composition` short-circuits for built-ins (no template load on the hot path).

## Activity Log

- 2026-04-25T17:54:43Z -- system -- Prompt created.
- 2026-04-25T18:39:42Z – claude:sonnet:implementer-ivan:implementer – shell_pid=37256 – Started implementation via action command
- 2026-04-25T18:47:37Z – claude:sonnet:implementer-ivan:implementer – shell_pid=37256 – Composition gate widened; built-in dispatch byte-identical (35-case existing suite green, +2 new); custom missions dispatch via agent_profile
- 2026-04-25T18:48:20Z – claude:opus:reviewer-renata:reviewer – shell_pid=38425 – Started review via action command
