---
work_package_id: WP03
title: next CLI Exit-Code Contract Fix
dependencies: []
requirement_refs:
- FR-006
- FR-007
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
- T015
agent: claude
history:
- date: '2026-06-02'
  event: created
agent_profile: debugger-debbie
authoritative_surface: src/specify_cli/next/
execution_mode: code_change
owned_files:
- src/specify_cli/next/__init__.py
- src/specify_cli/next/**/*.py
- src/runtime/next/**/*.py
- tests/next/test_next_command_integration.py
- tests/next/test_query_mode_unit.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load debugger-debbie
```

---

## Objective

Fix the `spec-kitty next` CLI so that:
1. Exit codes match the `DecisionKind` contract: `terminal` → 0, `blocked` → non-zero (1), `step` → 0.
2. A `success` result routes to `decide_next`, not `query_next`.

After this WP, the following tests must pass:
- `tests/next/test_next_command_integration.py::test_blocked_result_exit_code`
- `tests/next/test_next_command_integration.py::test_terminal_state_exit_code_zero`
- `tests/next/test_next_command_integration.py::test_advancing_mode_with_result_*`
- `tests/next/test_query_mode_unit.py::test_result_success_calls_decide_not_query`

**GitHub issue closed**: #1305

---

## Context

The `spec-kitty next` command drives the agent decision loop. It accepts a `result` argument (`success`, `failed`, `blocked`) and returns:
- The next step for the agent to execute, OR
- A `blocked` or `terminal` signal telling the agent to stop.

The contract (from `DecisionKind`):
- `DecisionKind.terminal` → CLI exits 0 (all steps done, mission complete or WP complete)
- `DecisionKind.blocked` → CLI exits non-zero (agent cannot proceed)
- `DecisionKind.step` → CLI exits 0 (agent has a next step)

There are two independent failure surfaces:

**Failure 1 (exit-code mapping)**: The Typer CLI command in `src/specify_cli/next/__init__.py` does not correctly call `raise typer.Exit(code=N)` for `blocked` decisions.

**Failure 2 (routing bug)**: When the result is `success`, the engine routes to `query_next` instead of `decide_next`. The `query_next` path is read-only (does not advance state); `decide_next` is the state-advancing path.

**Important**: The shared-package boundary cutover (`shared-package-boundary-cutover-01KQ22DS`) moved the runtime under `src/specify_cli/next/_internal_runtime/`. All imports in tests use this path — do not reference the retired `spec_kitty_runtime` package.

---

## Subtasks

### T011 — Audit exit-code mapping in `src/specify_cli/next/__init__.py`

**Steps**:

1. Read `src/specify_cli/next/__init__.py` in full.

2. Find the Typer command function (likely `def next_command(...)` or similar). Identify how it handles the return value from `decide_next` or `query_next`.

3. Look for the exit-code switch. It should resemble:
   ```python
   if decision.kind == DecisionKind.terminal:
       raise typer.Exit(code=0)
   elif decision.kind == DecisionKind.blocked:
       raise typer.Exit(code=1)
   elif decision.kind == DecisionKind.step:
       raise typer.Exit(code=0)
   ```

4. Record what is actually there. Common bugs:
   - Missing `raise typer.Exit(code=1)` for `blocked` (function returns normally → exit 0)
   - Wrong code (e.g., `code=2` for blocked when test expects non-zero but checks `!= 0`)
   - The exit-code logic is present but never reached due to an earlier exception

**Files**: `src/specify_cli/next/__init__.py`

**Output**: Notes on the current exit-code handling.

---

### T012 — Fix exit-code mapping

**Steps**:

1. Based on T011 findings, apply the correct exit-code switch:
   - `DecisionKind.terminal` → `raise typer.Exit(code=0)`
   - `DecisionKind.blocked` → `raise typer.Exit(code=1)`
   - `DecisionKind.step` → `raise typer.Exit(code=0)` (or return normally, which also exits 0)

2. Ensure the switch is **exhaustive** — add a fallback for any unexpected `DecisionKind` value:
   ```python
   else:
       raise typer.Exit(code=1)  # defensive: unknown kind → blocked
   ```

3. Verify the test expectations match:
   - `test_blocked_result_exit_code`: expects `result.exit_code != 0`
   - `test_terminal_state_exit_code_zero`: expects `result.exit_code == 0`

**Files**: `src/specify_cli/next/__init__.py`

**Validation**: After T014, run the tests to confirm.

---

### T013 — Trace the success→query routing bug

**Steps**:

1. Read `tests/next/test_query_mode_unit.py::test_result_success_calls_decide_not_query`. Understand what it mocks and what it asserts. The test likely mocks both `decide_next` and `query_next` and verifies that `decide_next` is called (not `query_next`) when result is `success`.

2. Read the routing logic in the CLI command. Find the conditional that selects between `decide_next` and `query_next`. It may look like:
   ```python
   if result in ("query", None):
       decision = query_next(agent, mission_slug, repo_root)
   else:
       decision = decide_next(agent, mission_slug, result, repo_root)
   ```
   or the routing may be inside `src/runtime/next/runtime_bridge.py`.

3. Identify the bug: most likely `success` is falling into the `query_next` branch because the condition is wrong (e.g., `if result == "query"` should be `if result in ("query", None)` but `success` is not excluded, or the condition is inverted).

4. Also check `src/runtime/next/_internal_runtime/engine.py` — if the engine itself routes internally, the bug may be there rather than in the CLI wrapper.

**Files**:
- `src/specify_cli/next/__init__.py`
- `src/runtime/next/runtime_bridge.py`
- `src/runtime/next/_internal_runtime/engine.py`
- `tests/next/test_query_mode_unit.py`

**Output**: Exact location and nature of the routing bug.

---

### T014 — Fix result-success routing

**Steps**:

1. Apply the fix identified in T013. The correct routing is:
   - `result` is `None` or `"query"` → call `query_next` (read-only, no state change)
   - `result` is `"success"`, `"failed"`, or `"blocked"` → call `decide_next` (state-advancing)

2. The fix is typically a one-line condition change. Do not refactor the surrounding code.

3. Ensure `decide_next` receives all required arguments (`agent`, `mission_slug`, `result`, `repo_root`).

**Files**: The file identified in T013 as containing the routing bug.

**Validation**: `test_result_success_calls_decide_not_query` passes after T015.

---

### T015 — Run all four failing next tests

**Steps**:

```bash
pytest tests/next/test_next_command_integration.py \
       tests/next/test_query_mode_unit.py \
       -v -k "blocked_result_exit_code or terminal_state_exit_code or advancing_mode or result_success_calls_decide" \
       2>&1
```

Expected: all four named tests pass.

Then run the full next test suite to confirm no regression:
```bash
pytest tests/next/ -q
```

If `test_advancing_mode_with_result_*` uses a parametrize decorator, ensure all parametrize variants pass.

---

## Branch Strategy

**Planning base branch**: `main`
**Merge target**: `main`
**Execution**: Lane A worktree. Run `spec-kitty agent action implement WP03 --agent claude` to enter the workspace.

---

## Definition of Done

- [ ] `test_blocked_result_exit_code` passes (`exit_code != 0`)
- [ ] `test_terminal_state_exit_code_zero` passes (`exit_code == 0`)
- [ ] `test_advancing_mode_with_result_*` (all variants) pass
- [ ] `test_result_success_calls_decide_not_query` passes
- [ ] No other next test regresses
- [ ] `mypy --strict` passes on all modified files
- [ ] No changes outside `owned_files`

## Risks

- **Two independent bugs**: The exit-code and the routing bug may interact. Fix routing first (T013–T014), then verify exit codes — this ordering prevents confounding during debugging.
- **Typer exit semantics**: In CliRunner tests, `raise typer.Exit(code=N)` results in `result.exit_code == N`. Verify this is how the tests are structured.

## Reviewer Guidance

1. Confirm `decide_next` is called when result is `success` (mock assertion in test).
2. Confirm `raise typer.Exit(code=1)` is present for `DecisionKind.blocked`.
3. Run `pytest tests/next/ -q` independently and confirm green.
4. Check that no `spec_kitty_runtime` imports were introduced (retired package).
