---
work_package_id: WP01
title: Task Board Progress Semantics
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- NFR-004
- NFR-006
- NFR-007
- C-001
- C-008
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-stable-320-p1-release-confidence-01KQTPZC
base_commit: f6cf56ed5300af79d85330e5a3f58e3f47aa7057
created_at: '2026-05-05T00:36:57.036739+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
agent: "codex:gpt-5:python-pedro:reviewer"
shell_pid: "98406"
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/agent/tasks.py
- src/specify_cli/agent_utils/status.py
- src/specify_cli/status/progress.py
- tests/specify_cli/status/test_progress.py
- tests/specify_cli/status/test_progress_integration.py
- tests/specify_cli/agent_utils/test_status.py
- tests/specify_cli/cli/commands/agent/test_tasks_status_progress.py
role: implementer
tags: []
---

# Work Package Prompt: WP01 - Task Board Progress Semantics

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `codex`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Fix #966 by making task-board progress output internally consistent across approved-only, done-only, mixed, and empty WP states. Preserve useful weighted readiness semantics, but label them explicitly so humans and JSON consumers do not confuse readiness with done-only completion.

Implementation command: `spec-kitty agent action implement WP01 --agent <name>`

## Context

The current `spec-kitty agent tasks status` path computes `done_count` separately from `compute_weighted_progress(...)`. Human output prints `done_count/total` beside the weighted percentage, so an approved-only board can show a done-only numerator with a readiness percentage. The plan contract allows either a done-only display plus weighted readiness peer metric, or a ready-oriented display that explicitly names readiness and the done count.

Branch strategy: planning artifacts were generated on `main`; completed changes must merge back into `main`. During implementation, Spec Kitty may allocate a worktree per computed lane from `lanes.json`; follow the workspace path provided by the implement command.

## Subtasks

### Subtask T001: Identify all task status progress renderers

**Purpose**: Find every status surface in the owned files that combines numerator, denominator, and percentage.

**Steps**:
1. Inspect `src/specify_cli/cli/commands/agent/tasks.py` around the `status` command.
2. Inspect `src/specify_cli/agent_utils/status.py` for parallel rendering or helper output.
3. Inspect `src/specify_cli/status/progress.py` to determine whether additive result fields should live in the progress result or in renderers.
4. Note any JSON key that already carries weighted semantics.

**Files**: read/modify only owned files listed in frontmatter.

**Validation**: You can explain each human and JSON status field's semantics before editing.

### Subtask T002: Define explicit done and weighted/readiness semantics

**Purpose**: Decide the smallest stable output shape that satisfies FR-001 through FR-004.

**Steps**:
1. Keep `done_count` done-only.
2. Compute `done_percentage` as done-only completion.
3. Keep weighted percentage as weighted readiness/progress when needed.
4. Add an explicit label or field such as `progress_semantics`, `weighted_percentage`, or `ready_progress_percentage` if JSON is touched.
5. Avoid changing existing JSON fields incompatibly unless no additive approach works.

**Files**: likely `tasks.py`, possibly `status.py` and `progress.py`.

**Validation**: Approved-only state cannot produce ambiguous output like `Progress: 0/6 (80.0%)`.

### Subtask T003: Update human-readable task status output

**Purpose**: Make the terminal task board clear for operators.

**Steps**:
1. Replace the current contradictory progress line in `src/specify_cli/cli/commands/agent/tasks.py`.
2. Apply the same semantic cleanup in `src/specify_cli/agent_utils/status.py` if that surface prints equivalent output.
3. Keep Rich formatting clean and readable.
4. Preserve existing status-board sections, stale warnings, and next action hints.

**Files**: `src/specify_cli/cli/commands/agent/tasks.py`, `src/specify_cli/agent_utils/status.py`.

**Validation**: Human output names done progress and weighted/ready progress distinctly.

### Subtask T004: Update JSON output if touched

**Purpose**: Keep machine-readable output parseable and semantically explicit.

**Steps**:
1. Add explicit fields rather than silently changing `progress_percentage` meaning when practical.
2. Include `done_count`, `total_wps`, and a done percentage if missing.
3. Include weighted/readiness semantics if `progress_percentage` remains weighted.
4. Ensure warnings and diagnostics do not pollute JSON stdout.

**Files**: `src/specify_cli/cli/commands/agent/tasks.py`; possibly `src/specify_cli/status/progress.py`.

**Validation**: `spec-kitty agent tasks status --json` remains parseable and internally consistent.

### Subtask T005: Add regression coverage

**Purpose**: Prove #966 is fixed and stays fixed.

**Steps**:
1. Add focused tests for approved-only, done-only, mixed approved/done, and empty/no-progress states.
2. Cover `src/specify_cli/agent_utils/status.py` through `tests/specify_cli/agent_utils/test_status.py` if that helper surface changes.
3. Cover human output if practical through CLI runner tests.
4. Cover JSON output if any JSON field is touched.
5. Keep fixtures local and deterministic.

**Files**: `tests/specify_cli/status/test_progress.py`, `tests/specify_cli/status/test_progress_integration.py`, `tests/specify_cli/agent_utils/test_status.py`, and/or `tests/specify_cli/cli/commands/agent/test_tasks_status_progress.py`.

**Validation**: Focused tests fail against the old ambiguous behavior and pass after the change.

### Subtask T006: Run focused verification

**Purpose**: Provide evidence for release confidence.

**Steps**:
1. Run focused progress/status tests.
2. Run relevant agent tasks CLI tests.
3. Record exact commands and outcomes for WP04.

**Files**: no additional source files beyond owned test files.

**Validation**: Start with `uv run pytest tests/specify_cli/status tests/specify_cli/cli/commands/agent -q` and narrow/expand with justification.

## Definition of Done

- Approved-only, done-only, mixed approved/done, and empty states are covered by tests.
- Human output no longer shows a done-only numerator beside an unlabeled weighted percentage.
- JSON output touched by the change remains valid and semantically explicit.
- Existing PR #972 status guarantees are preserved.
- Focused verification command results are available for release evidence.

## Risks

- Existing consumers may rely on `progress_percentage`; prefer additive JSON fields.
- There may be more than one status renderer; inspect owned surfaces before changing behavior.
- Weighted readiness is useful; do not remove it without a strong reason.

## Reviewer Guidance

Reviewers should focus on semantic clarity, JSON compatibility, and whether tests cover the exact #966 repro shape. Confirm no unrelated status lifecycle changes were introduced.

## Activity Log

- 2026-05-05T00:36:58Z – codex:gpt-5:python-pedro:implementer – shell_pid=87063 – Assigned agent via action command
- 2026-05-05T00:47:20Z – codex:gpt-5:python-pedro:implementer – shell_pid=87063 – Ready for review: progress semantics clarified; focused tests, ruff, and progress mypy passed
- 2026-05-05T00:47:30Z – codex:gpt-5:python-pedro:reviewer – shell_pid=98406 – Started review via action command
- 2026-05-05T00:51:58Z – codex:gpt-5:python-pedro:reviewer – shell_pid=98406 – Review passed: progress output separates done-only completion from weighted readiness; JSON adds explicit semantic fields and focused regressions pass
