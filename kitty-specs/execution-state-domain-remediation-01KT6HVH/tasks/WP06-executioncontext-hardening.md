---
work_package_id: WP06
title: ExecutionContext Hardening — Route Residue Surfaces
dependencies:
- WP02
- WP04
- WP05
requirement_refs:
- FR-028
- FR-031
- FR-032
- FR-033
- FR-034
- FR-035
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-execution-state-domain-remediation-01KT6HVH
base_commit: 427a014fb0d43f0796f3f6e20175cc868bf72887
created_at: '2026-06-03T12:47:19.673758+00:00'
subtasks:
- T032
- T033
- T034
- T035
- T036
- T037
agent: "claude:claude-sonnet-4-6:python-pedro:implementer"
shell_pid: "40520"
history:
- date: '2026-06-03'
  event: created
  author: spec-kitty
agent_profile: python-pedro
authoritative_surface: src/runtime/next/
execution_mode: code_change
owned_files:
- src/runtime/next/runtime_bridge.py
- src/specify_cli/cli/commands/agent/workflow.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Run `/ad-hoc-profile-load` and specify profile `python-pedro` before reading further.

---

## Objective

Route all remaining residue path-building surfaces through the canonical `resolve_action_context` entry point. Update `feature-runs.json` to carry mission identity. Delete unreachable path-builder helpers. Leave the e2e ratchet green.

## Branch Strategy

- **Planning base**: `main` | **Merge target**: `main`
- **Prerequisites**: WP02 (ratchet green), WP04 (MissionStatus merged), WP05 (MissionRunSnapshot fields merged)
- Start with: `spec-kitty agent action implement WP06 --agent claude`

## Context

`resolve_action_context` in `src/specify_cli/core/execution_context.py` is the canonical OHS entry point for resolving mission execution context. It already fuses planning + execution context correctly. The problem: residue surfaces bypass it and re-derive context independently.

**After WP04 merges**, `agent/status.py` is already fixed. The primary remaining residue surfaces are:
- `runtime_bridge.py` query-mode: derives `feature_dir` from slug without `resolve_action_context`
- `workflow.py` fix-mode: uses independently-resolved `repo_root` / `target_branch`

**Additionally**: This WP updates `feature-runs.json` to include `mission_id` and `mission_slug` (the write site in `runtime_bridge.py`). This was part of #1663 (WP05 schema) but the bridge write belongs to this WP since it owns `runtime_bridge.py`.

**Key reference**: `src/specify_cli/core/execution_context.py` — read `resolve_action_context` signature and return type before starting.

---

## Subtask T032 — Re-run Grep Investigation

**Purpose**: Find all remaining hardcoded path constructions now that WP03 and WP04 have landed.

**Steps**:
1. Run the investigation command:
   ```bash
   grep -rn 'kitty-specs.*mission_slug\|main_repo_root.*kitty\|feature_dir.*slug' \
     src/specify_cli --include='*.py' \
     | grep -v 'status/' \
     | grep -v 'core/execution_context'
   ```
2. Also check `runtime/next/`:
   ```bash
   grep -rn 'kitty-specs.*mission_slug\|kitty.specs.*slug\|feature_dir.*slug' \
     src/runtime/ --include='*.py'
   ```
3. Document what you find. The expected remaining surfaces are:
   - `runtime_bridge.py`: query-mode path construction and feature-runs.json write
   - `workflow.py`: fix-mode independent path/branch resolution
4. If there are unexpected surfaces beyond these, document them and assess whether they belong in WP06 or require a follow-up issue

**Validation**: You have a complete, up-to-date list of remaining bypass surfaces before making any changes.

---

## Subtask T033 — Update feature-runs.json Write in runtime_bridge.py

**Purpose**: Include `mission_id` and `mission_slug` in the `feature-runs.json` index entry when a run is recorded. This completes the #1663 bridge side (WP05 handled the schema side).

**Steps**:
1. Read `runtime_bridge.py` around lines 2043–2080 — find the `feature-runs.json` write site
2. Understand the current structure of the JSON entry being written
3. Update the write to include `mission_id` and `mission_slug`:
   ```python
   # Current (approximate):
   entry = {
       "run_id": run_id,
       "mission_key": mission_type,
       ...
   }
   # Updated:
   entry = {
       "run_id": run_id,
       "mission_key": mission_type,
       "mission_id": mission_id,    # NEW — from start_mission_run return value or local context
       "mission_slug": mission_slug, # NEW
       ...
   }
   ```
4. The values come from the `MissionRunRef` returned by `start_mission_run` after WP05 lands — `ref.mission_id` and `ref.mission_slug`

**Validation**: A new run produces a `feature-runs.json` entry with `mission_id` and `mission_slug` fields populated. Existing entries (missing these fields) still load without error (old entries just lack the fields — no breakage since reading code should use `.get()`).

---

## Subtask T034 — Route runtime_bridge Query-Mode Through resolve_action_context

**Purpose**: Replace independent `feature_dir` derivation in `runtime_bridge` query-mode with `resolve_action_context`.

**Steps**:
1. Read `src/specify_cli/core/execution_context.py` — understand `resolve_action_context` signature:
   ```bash
   grep -n "def resolve_action_context" src/specify_cli/core/execution_context.py
   ```
2. In `runtime_bridge.py`, find the query-mode path construction — look for patterns like:
   ```python
   feature_dir = repo_root / "kitty-specs" / mission_slug
   ```
   or equivalent slug-based derivation outside `status/` and `core/execution_context.py`.
3. Replace with `resolve_action_context`:
   ```python
   from specify_cli.core.execution_context import resolve_action_context

   ctx = resolve_action_context(repo_root=repo_root, mission_slug=mission_slug)
   feature_dir = ctx.feature_dir
   ```
4. If `resolve_action_context` requires more parameters than available at the call site, check what other bridge functions provide and thread through as needed
5. Run `pytest tests/ -x` after the change

**Validation**: `grep -n 'kitty-specs.*mission_slug\|kitty.specs.*slug' src/runtime/next/runtime_bridge.py` (for the query-mode function) returns zero hits for the targeted function.

---

## Subtask T035 — Route workflow.py Fix-Mode Through resolve_action_context

**Purpose**: Replace independently-resolved `repo_root` / `target_branch` in `workflow.py` fix-mode with `resolve_action_context`.

**Steps**:
1. Read `src/specify_cli/cli/commands/agent/workflow.py` — find the `_commit_via_legacy_safe_commit` function or equivalent fix-mode path
2. Understand what repo_root and target_branch values it currently uses and how they're derived
3. Replace the independent derivation with `resolve_action_context`:
   ```python
   from specify_cli.core.execution_context import resolve_action_context

   ctx = resolve_action_context(repo_root=repo_root, mission_slug=mission_slug)
   # Use ctx.target_branch, ctx.main_repo_root, etc.
   ```
4. If `mission_slug` is not available at the fix-mode call site, trace backwards to find where it can be threaded in
5. Run `pytest tests/ -x` after the change

**Validation**: `workflow.py` fix-mode constructs no repo_root or target_branch independently from the context resolver.

---

## Subtask T036 — Delete Unreachable Path-Builder Helpers

**Purpose**: Remove path-builder functions that are made unreachable by T034 and T035.

**Steps**:
1. After T034 and T035, search for now-unused path-builder helpers:
   ```bash
   # Functions that built feature_dir from slug
   grep -n "def.*feature_dir\|def.*kitty.specs\|def.*resolve.*path" \
     src/runtime/next/runtime_bridge.py src/specify_cli/cli/commands/agent/workflow.py
   ```
2. For each candidate function:
   - Check if it has any remaining callers: `grep -rn "function_name" src/`
   - If no callers: delete it
   - If it has callers that were NOT addressed by this WP: file a follow-up issue and leave for now
3. Confirm deletion doesn't break imports or `__all__` references

**Validation**: `pytest tests/ -x` passes after deletions. No import errors.

---

## Subtask T037 — Verify e2e Ratchet Still Green

**Purpose**: Final verification that all ExecutionContext changes maintain CWD-invariance.

**Steps**:
1. Run the full test suite: `pytest tests/ -x -q`
2. Run the ratchet explicitly: `pytest tests/architectural/test_execution_context_parity.py -v`
3. Run the boundary test: `pytest tests/architectural/test_status_module_boundary.py -v`
4. Run the full architectural suite: `pytest tests/architectural/ -v`
5. If any test fails, fix the regression before committing

**Validation**: All three targeted tests pass. Full test suite green.

---

## Definition of Done

- [ ] `feature-runs.json` write updated to include `mission_id` and `mission_slug`
- [ ] `runtime_bridge` query-mode derives `feature_dir` through `resolve_action_context`
- [ ] `workflow.py` fix-mode routes through `resolve_action_context`
- [ ] Unreachable path-builder helpers deleted
- [ ] `grep -rn 'kitty-specs.*mission_slug\|main_repo_root.*kitty\|feature_dir.*slug' src/ --include='*.py' | grep -v 'status/' | grep -v 'core/execution_context'` returns zero hits
- [ ] e2e ratchet (`test_execution_context_parity.py`) green
- [ ] status boundary test (`test_status_module_boundary.py`) green
- [ ] Full test suite (`pytest tests/ -x`) green

## Risks

- `resolve_action_context` may require mission context that isn't available at some call sites — trace the call stack carefully
- `workflow.py` fix-mode may have complex interactions with `BookkeepingTransaction` — do not change transaction internals
- Deleting path-builder helpers may break internal callers not caught by the initial grep — verify with the test suite after each deletion

## Reviewer Guidance

- Run the grep commands from the Definition of Done to confirm zero remaining hardcoded paths
- Check that `feature-runs.json` entries now include `mission_id` and `mission_slug` (add a test if not already covered)
- Verify `BookkeepingTransaction` in `coordination/transaction.py` is still unchanged
- Confirm the e2e ratchet is green (not just passing — check that it would fail on a known regression)

## Activity Log

- 2026-06-03T12:47:21Z – claude:claude-sonnet-4-6:python-pedro:implementer – shell_pid=31971 – Assigned agent via action command
- 2026-06-03T12:58:18Z – claude:claude-sonnet-4-6:python-pedro:implementer – shell_pid=31971 – Implementation complete. T033: feature-runs.json write updated with mission_id/mission_slug. T034: query_current_state + answer_decision_via_runtime routed through _resolve_read_path. T035: _ensure_target_branch_checked_out uses get_feature_target_branch (canonical). T036: no dead helpers found. Lint: exit 0. Tests: 1113 passed, 1 pre-existing failure (test_detect_false_positive_worktree - unrelated to WP changes, verified by stash test).
- 2026-06-03T12:58:39Z – claude:claude-sonnet-4-6:reviewer-renata:reviewer – shell_pid=38676 – Started review via action command
- 2026-06-03T13:03:49Z – claude:claude-sonnet-4-6:reviewer-renata:reviewer – shell_pid=38676 – Moved to planned
- 2026-06-03T13:04:30Z – claude:claude-sonnet-4-6:python-pedro:implementer – shell_pid=40520 – Started implementation via action command
- 2026-06-03T13:35:37Z – claude:claude-sonnet-4-6:python-pedro:implementer – shell_pid=40520 – Re-implementation cycle 1 complete. Fixed all 5 DoD items from review: (1) query_current_state routes through resolve_action_context(action='tasks'); (2) answer_decision_via_runtime routes through resolve_action_context; (3) _ensure_target_branch_checked_out routes through resolve_action_context with ActionContextError fallback; (4) test_execution_context_parity.py added and passing (2/2 tests green); (5) test_status_module_boundary.py added with WP03 code fixes cherry-picked so all 4 tests pass. Lint: exit 0. Tests: 1113 passed, 4 pre-existing failures (test_detect_false_positive_worktree + 3 architectural test_no_dead_modules/test_no_dead_symbols/test_ratchet_baselines - all confirmed pre-existing on prior commit).
- 2026-06-03T13:44:04Z – claude:claude-sonnet-4-6:python-pedro:implementer – shell_pid=40520 – Moved to planned
