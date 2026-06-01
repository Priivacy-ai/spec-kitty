---
work_package_id: WP04
title: '#1305: next CLI Exit-Code Fix'
dependencies:
- WP03
requirement_refs:
- FR-004
- FR-007
- FR-008
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T014
- T015
- T016
- T017
- T018
agent: claude
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/next/
execution_mode: code_change
owned_files:
- src/specify_cli/next/**
- tests/next/**
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, load your assigned agent profile:

```
/ad-hoc-profile-load python-pedro
```

This configures your Python implementer persona. Proceed only after the profile is loaded.

---

## Objective

Fix the `next` CLI command so it returns exit code `0` in terminal and successful-advance scenarios, and ensure `decide_next` is correctly invoked in all four failing test cases.

---

## Context

Issue #1305 (filed per DIR-013, cluster C99-f) reports that the `next` CLI is returning exit code `1` in scenarios that previously returned `0`, and that `decide_next` mocks are no longer being invoked. Pattern: `assert 1 == 0` in four tests.

**Affected tests**:
- `tests/next/test_next_command_integration.py::test_blocked_result_exit_code`
- `tests/next/test_next_command_integration.py::test_terminal_state_exit_code_zero`
- `tests/next/test_next_command_integration.py::test_advancing_mode_with_result_still_advances_normally`
- `tests/next/test_query_mode_unit.py::test_result_success_calls_decide_not_query`

The most likely root cause: a refactor of `src/specify_cli/next/` moved or renamed `decide_next`, but the test mock targets still reference the old import path.

**Prerequisite**: WP03 must be complete. `tests/sync/` and `tests/contract/` must be green before starting this WP.

---

## Subtask T014 — Reproduce the #1305 Cluster

**Purpose**: Establish the exact failure output before touching any code.

**Steps**:
```bash
pytest tests/next/ -q --tb=long -s -p no:cacheprovider 2>&1 | tee /tmp/wp04-before.txt
```

Record:
- Which of the 4 tests fail
- The exact assertion: `assert 1 == 0` — what does `1` represent (the actual exit code)?
- Whether mock call counts appear in the output (e.g., `decide_next was not called`)

**Validation**:
- [ ] All 4 failing tests reproduced with clear error output
- [ ] If zero failures: mark WP04 complete (stale), report, stop

---

## Subtask T015 — Locate the decide_next Call-Site Divergence

**Purpose**: Find exactly where the test mock target and the actual source diverge.

**Steps**:
1. Find where `decide_next` is defined in source:
   ```bash
   grep -r "def decide_next\|decide_next\s*=" src/specify_cli/next/ --include="*.py"
   grep -r "from.*import.*decide_next\|import.*decide_next" src/specify_cli/next/ --include="*.py"
   ```

2. Find where the tests mock `decide_next`:
   ```bash
   grep -r "decide_next\|mock.*decide\|patch.*decide" tests/next/ --include="*.py"
   ```

3. Compare the mock target path (e.g., `specify_cli.next.command.decide_next`) against the actual import path in the source.

4. Check git log to understand if `decide_next` was recently moved:
   ```bash
   git log --oneline --follow -20 -- src/specify_cli/next/
   ```

5. Read the relevant source files in `src/specify_cli/next/` to understand the current dispatch flow:
   - Which function is the CLI entry point for `next`?
   - How does it call `decide_next` (directly, via import, via dependency injection)?

**Output**: A clear statement of the divergence, e.g.:
> "Source defines `decide_next` in `src/specify_cli/next/decider.py`. Tests mock `specify_cli.next.command.decide_next` but the function was moved to `specify_cli.next.decider.decide_next` in commit `<sha>`."

**Validation**:
- [ ] Root cause identified and documented in a code comment or commit message

---

## Subtask T016 — Fix the Call-Site or Mock Target

**Purpose**: Restore the connection between the test mocks and the actual function being called.

**Decision framework**:

| Scenario | Fix |
|----------|-----|
| `decide_next` was moved/renamed in a refactor | Update test mock paths to match current import |
| `decide_next` is being called via a new wrapper that the test doesn't know about | Update the test to patch at the correct interception point |
| `decide_next` is no longer called (replaced by a different mechanism) | Update test to exercise the new mechanism, preserving intent |
| An early-return or exception prevents reaching `decide_next` | Fix the source to ensure the function is reached in the tested scenarios |

**Steps**:
1. Apply the appropriate fix based on T015 findings.
2. If updating mock paths: change `@patch("specify_cli.next.old.path.decide_next")` to the correct path.
3. If fixing early-return: locate the guard condition in the `next` CLI entry point and adjust it.
4. Run `pytest tests/next/test_query_mode_unit.py::test_result_success_calls_decide_not_query -v --tb=long` to verify the mock is now being invoked.

**Validation**:
- [ ] At least `test_result_success_calls_decide_not_query` passes (the pure unit test)
- [ ] Mock call count is non-zero (mock was invoked)

---

## Subtask T017 — Fix Exit-Code Logic

**Purpose**: Ensure the `next` CLI returns `0` for terminal states and successful advances.

**Steps**:
1. Read the current exit-code logic in the `next` CLI entry point (likely `src/specify_cli/next/__init__.py` or `src/specify_cli/cli/commands/next.py`).

2. Look for where `sys.exit()`, `raise SystemExit()`, or `ctx.exit()` is called. Map each call to the scenario it covers.

3. For the two failing integration tests:
   - `test_terminal_state_exit_code_zero`: terminal state (e.g., all WPs done) should exit 0, not 1.
   - `test_blocked_result_exit_code`: a "blocked" result (no WP claimable) — check what exit code the test expects. The test name says `exit_code` which may not be zero — read the test to confirm.

4. Fix the exit-code computation so each scenario returns the correct code. Minimal change: touch only the exit-code return path, not the decision logic.

**Validation**:
- [ ] `test_terminal_state_exit_code_zero` passes (exit code 0)
- [ ] `test_blocked_result_exit_code` passes (exit code matches test expectation)
- [ ] `test_advancing_mode_with_result_still_advances_normally` passes

---

## Subtask T018 — Full #1305 Verification

**Purpose**: Confirm all 4 tests pass and no regressions in adjacent modules.

**Steps**:
```bash
pytest tests/next/ -q --tb=short -p no:cacheprovider 2>&1 | tee /tmp/wp04-after.txt
```

Then a broader check:
```bash
pytest tests/ -q --tb=no -p no:cacheprovider \
  --ignore=tests/doctrine/ --ignore=tests/charter/ \
  -x 2>&1 | tail -5
```

**FR-007 — Add regression test**: If the root cause was a stale mock path, add an import-path assertion test or update the mock to use `spec_kitty.next.<actual_module>.decide_next` so that future refactors break the test rather than silently changing behavior. Document the regression guard in the commit message.

**FR-008 — Record post-fix results**: Append the verification summary to `docs/p0-baseline-refresh.md`:
```bash
echo "\n## WP04 Post-Fix Results (#1305)" >> docs/p0-baseline-refresh.md
cat /tmp/wp04-after.txt | grep "passed\|failed" | tail -1 >> docs/p0-baseline-refresh.md
```

Commit:
```bash
git add -p
git commit -m "fix(#1305): restore decide_next dispatch and exit-code contract in next CLI"
```

**Validation**:
- [ ] All 4 `tests/next/` tests pass
- [ ] No regressions in `tests/sync/`, `tests/contract/`
- [ ] **FR-007**: Regression guard added/confirmed (documented in commit message)
- [ ] **FR-008**: Post-fix results appended to `docs/p0-baseline-refresh.md`
- [ ] Changes committed

---

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target**: `main`
- **Execution worktree**: Allocated by `lanes.json`.

Implementation command:
```bash
spec-kitty agent action implement WP04 --agent claude
```

---

## Definition of Done

- [ ] `test_blocked_result_exit_code` passes
- [ ] `test_terminal_state_exit_code_zero` passes
- [ ] `test_advancing_mode_with_result_still_advances_normally` passes
- [ ] `test_result_success_calls_decide_not_query` passes
- [ ] `decide_next` is verifiably invoked in mocked tests
- [ ] No regressions in `tests/sync/` or `tests/contract/`
- [ ] **FR-007**: Regression guard added/confirmed
- [ ] **FR-008**: Post-fix results appended to `docs/p0-baseline-refresh.md`
- [ ] Changes committed with issue-scoped message

---

## Risks

- **Intentional refactor**: If `decide_next` was moved as part of a deliberate refactor (not a bug), the correct fix is to update the tests — not to revert the refactor. Check git log.
- **Multiple call paths**: The `next` CLI may have a "query mode" and an "advance mode" with different dispatch. Read both before fixing.
- **Exit-code semantics**: The test `test_blocked_result_exit_code` may expect a non-zero exit for "blocked" — read it before assuming everything should be 0.
