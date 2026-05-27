---
work_package_id: WP06
title: '`next` CLI exit-code regressions'
dependencies: []
requirement_refs:
- FR-008
tracker_refs: []
planning_base_branch: feat/pre-doctrine-stabilization-remediation
merge_target_branch: feat/pre-doctrine-stabilization-remediation
branch_strategy: Planning artifacts for this mission were generated on feat/pre-doctrine-stabilization-remediation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/pre-doctrine-stabilization-remediation unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-pre-doctrine-test-stabilization-01KSMG8Y
base_commit: fcec446d1be3c2c67d5ce9f0bc36a40133fe6684
created_at: '2026-05-27T12:19:26.318877+00:00'
subtasks:
- T023
- T024
- T025

shell_pid: '39129'
history:
- date: '2026-05-27'
  event: created
agent_profile: debugger-debbie
authoritative_surface: src/specify_cli/next/
execution_mode: code_change
model: claude-sonnet-4-6
owned_files:
- src/specify_cli/next/runtime_bridge.py
- tests/next/test_next_command_integration.py
- tests/next/test_query_mode_unit.py
role: investigator
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load debugger-debbie
```

---

## Objective

Fix `decide_next_via_runtime` returning a `Decision` with the wrong `kind` for terminal states, causing incorrect exit codes. Also fix the mock-target mismatch in `test_query_mode_unit` where the patched function is no longer being invoked.

**Closes**: GitHub issue #1305

---

## Context

The exit-code contract is:
- Terminal states → exit 0
- Blocked states → exit 1 (`typer.Exit(1)`)

The exit-code MAPPING in `src/specify_cli/cli/commands/next_cmd.py` is correct:
```python
if decision.kind == "blocked":
    raise typer.Exit(1)
# all other kinds fall through to implicit exit 0
```

**Do NOT change `next_cmd.py`.** The regression is that `decide_next_via_runtime` in `src/specify_cli/next/runtime_bridge.py` is returning a `Decision` object with the wrong `.kind` value for terminal states, OR the mock that was supposed to return a controlled `Decision` is no longer being called (call-path bypass).

**Ownership note**: WP05 item 3 (discover-action blocking) may also touch `runtime_bridge.py`. WP06 has priority over `runtime_bridge.py` — WP05 must not begin `runtime_bridge.py` edits until this WP is merged.

---

## Subtask T023 — Investigate decide_next_via_runtime terminal-state return value

**Purpose**: Understand the exact failure mode before editing production code. The mock-not-invoked symptom suggests a call-path bypass; the wrong-kind symptom points to a return-value error in `decide_next_via_runtime` itself.

**Steps**:

1. Run all failing next tests with verbose output:
   ```bash
   pytest tests/next/test_next_command_integration.py tests/next/test_query_mode_unit.py -v --tb=long 2>&1 | head -120
   ```

2. For each failing test, record:
   - The test name and the assertion that fails
   - The expected exit code vs. the actual exit code
   - Whether the mock assertion fails (mock not called)

3. Read `src/specify_cli/next/runtime_bridge.py` to understand the current `decide_next_via_runtime` implementation:
   ```bash
   cat -n src/specify_cli/next/runtime_bridge.py
   ```

4. Read each failing test to identify:
   - What function is being mocked
   - What patch target string is used (e.g. `"specify_cli.next.runtime_bridge.decide_next"`)
   - What the mock should return (which `Decision.kind`)

5. Compare the mock target in the test against the actual import path in `runtime_bridge.py`. If the function was renamed or the delegation chain changed, the mock target is stale.

**Output from this subtask**: A clear diagnosis of whether the bug is:
   - (A) `decide_next_via_runtime` returns wrong `Decision.kind`
   - (B) The mock patch target is stale (function renamed / delegation chain changed)
   - (C) Both

**Validation**:
- [ ] You have a written diagnosis (A, B, or C) before touching production code

---

## Subtask T024 — Fix Decision.kind return for terminal states

**Purpose**: Correct the return value of `decide_next_via_runtime` so terminal states produce `Decision(kind="terminal")` or equivalent, and blocked states produce `Decision(kind="blocked")`.

**Steps**:

1. Using the diagnosis from T023, locate the code path in `runtime_bridge.py` that produces the wrong `Decision.kind`.

2. A terminal state (e.g., `done`, `canceled`) should return a `Decision` that does NOT have `kind="blocked"`.

3. Fix the `kind` computation. The `Decision` model is defined in `src/specify_cli/next/decision.py` (or similar) — read it first:
   ```bash
   find src/specify_cli/next/ -name "decision.py" -o -name "models.py" | head -3
   ```

4. Apply the minimal fix. Do not change `next_cmd.py`.

5. Run the exit-code integration tests to confirm correct exit codes:
   ```bash
   pytest tests/next/test_next_command_integration.py -v --tb=short
   ```

**Files**: `src/specify_cli/next/runtime_bridge.py`

**Validation**:
- [ ] Terminal-state tests exit 0
- [ ] Blocked-state tests exit 1
- [ ] `next_cmd.py` is unchanged

---

## Subtask T025 — Update mock target in test_query_mode_unit.py if needed

**Purpose**: If the diagnosis (T023) identified a stale mock target, update the patch string in `test_query_mode_unit.py` to match the current function path.

**Steps**:

1. If diagnosis is (A) only (wrong return value, mock target is correct): skip this subtask — the mock will start firing correctly after T024.

2. If diagnosis is (B) or (C):
   - Find the current mock patch string in the test:
     ```bash
     grep -n "patch\|mock\|MagicMock" tests/next/test_query_mode_unit.py | head -20
     ```
   - Identify the current import path of the function being mocked
   - Update the patch string to the correct `"module.path.function_name"` form

3. Run the query-mode tests:
   ```bash
   pytest tests/next/test_query_mode_unit.py -v --tb=short
   ```

4. Confirm the mock is actually called (not just that the test passes — check the mock assertion `mock.assert_called_once()` or equivalent).

**Files**: `tests/next/test_query_mode_unit.py`

**Validation**:
- [ ] Mock is invoked (not bypassed)
- [ ] `test_query_mode_unit` passes
- [ ] Mock assertion (assert_called or assert_called_once) does not fail

---

## Branch Strategy

- **Planning/base branch**: `feat/pre-doctrine-stabilization-remediation`
- **Final merge target**: `feat/pre-doctrine-stabilization-remediation`

**Priority note**: WP05 must not edit `runtime_bridge.py` until this WP is merged. This WP should be merged as soon as its tests pass.

To start implementation:
```bash
spec-kitty agent action implement WP06 --agent claude
```

---

## Definition of Done

- [ ] All four failing tests in `test_next_command_integration` pass
- [ ] `test_query_mode_unit` passes with mock invoked
- [ ] Terminal states exit 0; blocked states exit 1
- [ ] `next_cmd.py` is unchanged
- [ ] New tests (if any) carry `[pytest.mark.fast, pytest.mark.unit]`

---

## Risks

| Risk | Likelihood | Mitigation |
|------|-----------|-----------|
| Mock target is buried in a deeply delegated call chain | Medium | Trace call chain from test; use `--tb=long` |
| Fix requires changing the Decision model | Low | Read decision.py before editing runtime_bridge.py |
| WP05 begins runtime_bridge.py edit before WP06 merges | Medium | Communicate merge status; WP05 should check before editing |

---

## Reviewer Guidance

1. Confirm `next_cmd.py` was not modified
2. Confirm terminal states exit 0 and blocked states exit 1 (run the integration tests)
3. Confirm mock assertion passes in `test_query_mode_unit` (mock IS called, not bypassed)
4. Check `runtime_bridge.py` diff — only `decide_next_via_runtime` return value should change
</content>