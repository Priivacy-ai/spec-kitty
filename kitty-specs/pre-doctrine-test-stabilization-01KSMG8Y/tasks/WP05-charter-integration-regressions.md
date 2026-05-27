---
work_package_id: WP05
title: Charter integration suite regressions
dependencies: []
requirement_refs:
- FR-007
tracker_refs: []
planning_base_branch: feat/pre-doctrine-stabilization-remediation
merge_target_branch: feat/pre-doctrine-stabilization-remediation
branch_strategy: Planning artifacts for this mission were generated on feat/pre-doctrine-stabilization-remediation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/pre-doctrine-stabilization-remediation unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-pre-doctrine-test-stabilization-01KSMG8Y
base_commit: fcec446d1be3c2c67d5ce9f0bc36a40133fe6684
created_at: '2026-05-27T12:19:22.890341+00:00'
subtasks:
- T017
- T018
- T019
- T020
- T021
- T022

shell_pid: "406663"
agent: "claude:claude-opus-4-7:debugger-debbie:implementer"
history:
- date: '2026-05-27'
  event: created
agent_profile: debugger-debbie
authoritative_surface: src/specify_cli/charter_lint/
execution_mode: code_change
model: claude-opus-4-7
owned_files:
- src/specify_cli/charter_lint/**
- src/specify_cli/cli/commands/charter/synthesize.py
- src/specify_cli/charter_preflight/**
- src/specify_cli/cli/commands/specify.py
- tests/integration/test_charter_lint_lints_all_layers.py
- tests/integration/test_charter_synthesize_fresh.py
- tests/integration/test_documentation_runtime_walk.py
- tests/integration/test_implement_review_retrospect_smoke.py
- tests/integration/test_rejection_cycle.py
- tests/integration/test_specify_plan_commit_boundary.py
role: investigator
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load debugger-debbie
```

---

## Objective

Fix six independent charter integration test failures. Each requires test-driven investigation before touching production code. Run each integration test in isolation before beginning any edits.

**Closes**: GitHub issue #1307

---

## Context

Integration tests are slow. Use `-x` (fail-fast) and `--tb=short` when investigating one test at a time.

**Critical ownership constraints**:
- **`move_task.py` is owned by WP04**. If T021 (rejection-cycle handoff) is rooted in `move_task.py`, coordinate with WP04 — do NOT edit that file in this lane.
- **`runtime_bridge.py` is the primary target of WP06**. If T019 (discover action) requires `runtime_bridge.py` changes, check `src/specify_cli/charter_preflight/` first. Only edit `runtime_bridge.py` from this WP if WP06 has already been reviewed and merged into the feature branch.
- **`src/charter/synthesizer/`** is owned by WP08. T018 must touch only `src/specify_cli/cli/commands/charter/synthesize.py` (the CLI adapter), not the synthesizer library itself.

---

## Subtask T017 — Fix org-layer source name missing in charter lint output

**Purpose**: `test_charter_lint_lints_all_layers` asserts that the lint output includes the org-layer source name. It is currently absent.

**Steps**:

1. Run the test:
   ```bash
   pytest tests/integration/test_charter_lint_lints_all_layers.py -v --tb=long 2>&1 | head -60
   ```

2. Read the test to identify:
   - What string/value is expected in the lint output
   - Which `assert` line is failing

3. Trace the lint output formatting in `src/specify_cli/charter_lint/`:
   ```bash
   find src/specify_cli/charter_lint/ -name "*.py" | xargs grep -l "source\|org.layer\|output" | head -5
   ```

4. Add the missing source name to the lint output.

5. Run the test to confirm:
   ```bash
   pytest tests/integration/test_charter_lint_lints_all_layers.py -v
   ```

**Files**: `src/specify_cli/charter_lint/` (source name formatting path)

**Validation**:
- [ ] `test_charter_lint_lints_all_layers` passes
- [ ] The org-layer source name appears in lint output

---

## Subtask T018 — Fix wrong error class from synthesize_without_charter_md

**Purpose**: `test_synthesize_without_charter_md_fails_actionably` expects a specific error class but gets a different one.

**IMPORTANT**: Fix the CLI adapter ONLY (`src/specify_cli/cli/commands/charter/synthesize.py`). Do NOT touch `src/charter/synthesizer/errors.py` — that path is owned by WP08.

**Steps**:

1. Run the test:
   ```bash
   pytest tests/integration/test_charter_synthesize_fresh.py::test_synthesize_without_charter_md_fails_actionably -v --tb=long 2>&1 | head -60
   ```

2. Identify:
   - What error class is expected
   - What error class is currently raised
   - Whether the mismatch is in the CLI adapter or the synthesizer library

3. If the fix is in the CLI adapter (`synthesize.py`): fix the exception wrapping or error propagation.

4. If the fix requires changing `src/charter/synthesizer/errors.py`: stop and coordinate with WP08 — the error class change belongs in that lane.

5. Run the test to confirm:
   ```bash
   pytest tests/integration/test_charter_synthesize_fresh.py::test_synthesize_without_charter_md_fails_actionably -v
   ```

**Files**: `src/specify_cli/cli/commands/charter/synthesize.py`

**Validation**:
- [ ] `test_synthesize_without_charter_md_fails_actionably` passes
- [ ] No changes made to `src/charter/synthesizer/`

---

## Subtask T019 — Fix discover action blocking despite spec.md authored

**Purpose**: The `discover` action in the runtime walk should not block when `spec.md` is already authored. It is currently blocking.

**IMPORTANT**: Check `src/specify_cli/charter_preflight/` BEFORE touching `runtime_bridge.py`. If the fix is in the preflight logic, stay there. Only edit `runtime_bridge.py` if WP06 has been merged AND the fix cannot be in `charter_preflight/`.

**Steps**:

1. Run the test:
   ```bash
   pytest tests/integration/test_documentation_runtime_walk.py::test_full_advancement_through_six_actions -v --tb=long 2>&1 | head -80
   ```

2. Identify which action is blocking and at what point in the walk:
   - Is it the `discover` action itself?
   - Is it the preflight check that gates `discover`?
   - Is it the runtime's next-action computation?

3. Check `src/specify_cli/charter_preflight/` for the spec.md-authored condition:
   ```bash
   grep -rn "spec.md\|spec_md\|authored\|discover" src/specify_cli/charter_preflight/ | head -20
   ```

4. Fix the blocking condition. If the fix is in `runtime_bridge.py` and WP06 is not yet merged: create a coordination note and revisit after WP06 merges.

5. Run the test to confirm:
   ```bash
   pytest tests/integration/test_documentation_runtime_walk.py::test_full_advancement_through_six_actions -v
   ```

**Files**: `src/specify_cli/charter_preflight/` (preferred) or `src/specify_cli/next/runtime_bridge.py` (only if WP06 merged)

**Validation**:
- [ ] `test_full_advancement_through_six_actions` passes
- [ ] The discover action does not block when spec.md is already authored

---

## Subtask T020 — Fix implement-review-retrospect smoke test failure

**Purpose**: The smoke test for the implement → review → retrospect cycle is failing.

**Steps**:

1. Run the test:
   ```bash
   pytest tests/integration/test_implement_review_retrospect_smoke.py::test_reject_fix_next_retrospect_smoke -v --tb=long 2>&1 | head -80
   ```

2. Identify the failure point in the cycle (which step fails and why).

3. Trace the issue to the correct production file and fix it.

4. Run the test to confirm:
   ```bash
   pytest tests/integration/test_implement_review_retrospect_smoke.py::test_reject_fix_next_retrospect_smoke -v
   ```

**Files**: As identified by test output (likely in `src/specify_cli/cli/commands/` or `src/specify_cli/review/`)

**Validation**:
- [ ] `test_reject_fix_next_retrospect_smoke` passes

---

## Subtask T021 — Fix wrong branch in rejection-cycle handoff

**Purpose**: The rejection cycle reports the wrong branch in the handoff.

**IMPORTANT**: This fix may be in `move_task.py` (owned by WP04) or in the `implement`/`review` path (in scope here). Run the test first to identify the exact file.

**Steps**:

1. Run the test:
   ```bash
   pytest tests/integration/test_rejection_cycle.py::test_implement_uses_review_cycle_artifact_after_review_claim -v --tb=long 2>&1 | head -80
   ```

2. Identify where the wrong branch is set:
   ```bash
   grep -n "branch\|handoff" tests/integration/test_rejection_cycle.py | head -20
   ```

3. If the fix is in `move_task.py`: stop and coordinate with WP04. File a note that this subtask needs WP04 involvement; do not edit `move_task.py` in this lane.

4. If the fix is in `implement.py`, `review.py`, or another path in scope: apply the fix here.

5. Run the test to confirm:
   ```bash
   pytest tests/integration/test_rejection_cycle.py::test_implement_uses_review_cycle_artifact_after_review_claim -v
   ```

**Files**: As identified — NOT `move_task.py` (owned by WP04)

**Validation**:
- [ ] `test_implement_uses_review_cycle_artifact_after_review_claim` passes
- [ ] No changes to `move_task.py` in this lane

---

## Subtask T022 — Fix substantive plan not auto-committed in specify-plan

**Purpose**: `test_setup_plan_commits_substantive_plan` asserts that a substantive plan is auto-committed; it is not being committed.

**Steps**:

1. Run the test:
   ```bash
   pytest tests/integration/test_specify_plan_commit_boundary.py::test_setup_plan_commits_substantive_plan -v --tb=long 2>&1 | head -80
   ```

2. Read the test to understand what "substantive plan" means in this context and at what point the auto-commit should occur.

3. Trace the plan-commit path in `src/specify_cli/cli/commands/specify.py` or the plan setup code:
   ```bash
   grep -rn "setup.plan\|setup_plan\|auto.commit\|commit.*plan" src/specify_cli/cli/ | head -20
   ```

4. Restore or fix the auto-commit call.

5. Run the test to confirm:
   ```bash
   pytest tests/integration/test_specify_plan_commit_boundary.py::test_setup_plan_commits_substantive_plan -v
   ```

**Files**: `src/specify_cli/cli/commands/` (specify or plan setup path)

**Validation**:
- [ ] `test_setup_plan_commits_substantive_plan` passes
- [ ] Plan is auto-committed when it is substantive (real Language/Version values, no placeholders)

---

## Branch Strategy

- **Planning/base branch**: `feat/pre-doctrine-stabilization-remediation`
- **Final merge target**: `feat/pre-doctrine-stabilization-remediation`

**Coordination rules**:
- Do NOT edit `move_task.py` — coordinate with WP04 if T021 requires it
- Do NOT begin `runtime_bridge.py` edits until WP06 is merged — check `charter_preflight/` first for T019
- Do NOT edit `src/charter/synthesizer/` — owned by WP08; T018 stays in the CLI adapter

To start implementation:
```bash
spec-kitty agent action implement WP05 --agent claude
```

---

## Definition of Done

- [ ] `test_charter_lint_lints_all_layers` passes
- [ ] `test_synthesize_without_charter_md_fails_actionably` passes
- [ ] `test_full_advancement_through_six_actions` passes
- [ ] `test_reject_fix_next_retrospect_smoke` passes
- [ ] `test_implement_uses_review_cycle_artifact_after_review_claim` passes
- [ ] `test_setup_plan_commits_substantive_plan` passes
- [ ] No changes to `move_task.py`, `src/charter/synthesizer/`, or `runtime_bridge.py` in this lane (unless WP06 merged)

---

## Risks

| Risk | Likelihood | Mitigation |
|------|-----------|-----------|
| T021 rejection-cycle fix is in move_task.py | Medium | Run test first; coordinate with WP04 if confirmed |
| T019 requires runtime_bridge.py before WP06 merges | Medium | Check charter_preflight/ first; defer if runtime_bridge.py needed |
| Integration tests take >5 minutes each | High | Use `-x --tb=short`; fix one at a time |
| T018 fix is in synthesizer library (WP08 scope) | Low | Stay in CLI adapter only; report to WP08 if deeper fix needed |

---

## Reviewer Guidance

1. All six integration tests must pass
2. No files owned by WP04 (`move_task.py`) or WP08 (`src/charter/synthesizer/`) were modified
3. If `runtime_bridge.py` was modified, confirm WP06 was already merged
</content>

## Activity Log

- 2026-05-27T12:19:23Z – claude:claude-opus-4-7:debugger-debbie:investigator – shell_pid=39129 – Assigned agent via action command
- 2026-05-27T12:40:46Z – claude:claude-opus-4-7:debugger-debbie:investigator – shell_pid=39129 – T017-T022 complete: all 6 charter integration tests pass
- 2026-05-27T12:41:29Z – claude:claude-sonnet-4-6:curator-carla:reviewer – shell_pid=359237 – Started review via action command
- 2026-05-27T12:46:22Z – claude:claude-sonnet-4-6:curator-carla:reviewer – shell_pid=359237 – Moved to planned
- 2026-05-27T12:46:54Z – claude:claude-opus-4-7:debugger-debbie:implementer – shell_pid=406663 – Started implementation via action command
