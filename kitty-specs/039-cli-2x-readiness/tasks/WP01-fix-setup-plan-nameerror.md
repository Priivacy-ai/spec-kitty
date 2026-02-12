---
work_package_id: WP01
title: Fix setup-plan NameError on 2.x
lane: "planned"
dependencies: []
base_branch: main
base_commit: 7bd6c768a80ab89b5c98d40db5e3671178829eec
created_at: '2026-02-12T10:08:27.183442+00:00'
subtasks:
- T001
- T002
- T003
phase: Wave 1 - Independent Fixes
assignee: ''
agent: "claude-opus"
shell_pid: "41559"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-12T12:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP01 – Fix setup-plan NameError on 2.x

## IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.

---

## Review Feedback

> **Populated by `/spec-kitty.review`** – Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially.]*

---

## Implementation Command

```bash
spec-kitty implement WP01
```

No dependencies — branches directly from the 2.x branch.

---

## Objectives & Success Criteria

- `spec-kitty agent feature setup-plan` completes without `NameError: get_feature_mission_key` on 2.x
- `test_planning_workflow.py::test_setup_plan_in_main` passes
- `test_planning_workflow.py::test_full_planning_workflow_no_worktrees` xfail reason investigated and either fixed or re-documented with a clear explanation
- All existing planning and task workflow tests pass (no regressions)

## Context & Constraints

- **Delivery branch**: 2.x (do NOT merge to main)
- **Root cause**: The `get_feature_mission_key` function is used in `src/specify_cli/cli/commands/agent/feature.py` but the import is missing on 2.x. This was fixed on main at commit 5332408f.
- **Complication**: 2.x is 588 commits diverged from main — `feature.py` may differ significantly
- **Test environment issue**: On main, after fixing the NameError, `ModuleNotFoundError: typer` appeared in test-created venvs. This may also manifest on 2.x.
- **Reference**: `kitty-specs/039-cli-2x-readiness/spec.md` (User Story 1), `plan.md` (WP01), `research.md` (R5)

## Subtasks & Detailed Guidance

### Subtask T001 – Apply missing import fix to feature.py on 2.x

- **Purpose**: Resolve the `NameError: get_feature_mission_key is not defined` that blocks `setup-plan`.
- **Steps**:
  1. Check out the 2.x branch: `git checkout 2.x`
  2. Read `src/specify_cli/cli/commands/agent/feature.py` on 2.x to understand its current state
  3. Compare with the fix on main (commit 5332408f) — identify the exact import that was added
  4. The function `get_feature_mission_key` likely lives in `src/specify_cli/mission.py` or a related module. Find its actual location on 2.x:
     ```bash
     grep -r "def get_feature_mission_key" src/specify_cli/
     ```
  5. Add the correct import statement to `feature.py`
  6. Verify the import resolves: `python -c "from specify_cli.cli.commands.agent.feature import *"`
- **Files**: `src/specify_cli/cli/commands/agent/feature.py` (edit)
- **Parallel?**: No — must be done first to unblock T002/T003
- **Notes**: Do NOT blindly cherry-pick from main — the file has likely diverged. Manual application is safer.

### Subtask T002 – Investigate and fix xfail planning workflow test

- **Purpose**: The `test_full_planning_workflow_no_worktrees` test is marked xfail. Determine if the NameError fix resolves it, or if there's a deeper issue.
- **Steps**:
  1. Read the test: `tests/integration/test_planning_workflow.py` (find the xfail-marked test)
  2. Check the xfail reason string — it should describe why it's expected to fail
  3. After applying T001 fix, run the test without the xfail marker:
     ```bash
     python -m pytest tests/integration/test_planning_workflow.py::test_full_planning_workflow_no_worktrees -x -v
     ```
  4. **If it passes**: Remove the xfail marker. Done.
  5. **If it fails with `ModuleNotFoundError: typer`**: This is a test environment issue (typer not installed in test-created venvs). Fix by:
     - Ensuring typer is in `test` dependencies in `pyproject.toml`
     - Or making the test set up the venv with typer installed
     - Or mocking the subprocess that creates the venv
  6. **If it fails for another reason**: Document the failure, update the xfail reason string to be descriptive, and create a follow-up issue
- **Files**: `tests/integration/test_planning_workflow.py` (edit)
- **Parallel?**: No — depends on T001
- **Notes**: The goal is either a passing test or a well-documented xfail with a specific, actionable reason.

### Subtask T003 – Verify all planning workflow tests pass

- **Purpose**: Confirm no regressions from the import fix.
- **Steps**:
  1. Run the full planning workflow test suite:
     ```bash
     python -m pytest tests/integration/test_planning_workflow.py -x -v
     python -m pytest tests/integration/test_task_workflow.py -x -v
     ```
  2. Run the CLI command unit tests for agent feature:
     ```bash
     python -m pytest tests/specify_cli/cli/commands/agent/ -x -v
     ```
  3. Verify all tests pass (excluding pre-existing xfail markers unrelated to this feature)
  4. If any tests fail, investigate and fix — do NOT leave regressions
- **Files**: No changes expected (verification only)
- **Parallel?**: No — depends on T001 and T002
- **Notes**: ~5 planning tests + ~18 task workflow tests should pass. Pre-existing failures from cross-test pollution are acceptable if they fail in the full suite but pass in isolation.

## Test Strategy

- **Primary tests**: `tests/integration/test_planning_workflow.py` (5 tests), `tests/integration/test_task_workflow.py` (18 tests)
- **Run command**: `python -m pytest tests/integration/test_planning_workflow.py tests/integration/test_task_workflow.py -x -v`
- **Baseline**: These tests should pass on 2.x after the fix

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| 2.x `feature.py` differs significantly from main | Read the file first; apply import manually, not via cherry-pick |
| `get_feature_mission_key` doesn't exist on 2.x | Search for the function definition; it may have a different name or location on 2.x |
| Typer missing in test venvs | Ensure typer is in test dependencies; mock venv creation if needed |

## Review Guidance

- Verify the import fix is correct for the 2.x version of feature.py (not a blind copy from main)
- Check that the xfail is either removed (test passes) or updated with a specific, actionable reason
- Run `python -m pytest tests/integration/test_planning_workflow.py tests/integration/test_task_workflow.py -x -v` and verify green

## Activity Log

- 2026-02-12T12:00:00Z – system – lane=planned – Prompt created.
- 2026-02-12T10:08:27Z – claude-opus – shell_pid=41559 – lane=doing – Assigned agent via workflow command
- 2026-02-12T10:10:11Z – claude-opus – shell_pid=41559 – lane=planned – Resetting - workspace branched from wrong base (main instead of 2.x)
