---
work_package_id: WP02
title: 'Rename ownership enum #1 to WorkProductKind + re-drift guard'
dependencies:
- WP01
requirement_refs:
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
planning_base_branch: rc3-execution-mode-consolidation-01M0GGX1
merge_target_branch: rc3-execution-mode-consolidation-01M0GGX1
branch_strategy: Planning artifacts for this mission were generated on rc3-execution-mode-consolidation-01M0GGX1. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into rc3-execution-mode-consolidation-01M0GGX1 unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
- T010
- T011
- T012
history: []
authoritative_surface: src/specify_cli/ownership/
create_intent:
- tests/architectural/test_execution_mode_no_redrift.py
execution_mode: code_change
owned_files:
- src/specify_cli/ownership/**
- src/specify_cli/core/worktree.py
- src/specify_cli/lanes/compute.py
- src/specify_cli/lanes/implement_support.py
- src/specify_cli/workspace/context.py
- src/specify_cli/cli/commands/agent/mission_parsing.py
- tests/architectural/test_execution_mode_no_redrift.py
- tests/_arch_shard_map.py
- tests/architectural/test_no_dead_symbols.py
- tests/integration/test_planning_artifact_wp.py
- tests/lanes/**
- tests/specify_cli/lanes/**
- tests/specify_cli/ownership/**
- tests/specify_cli/core/test_worktree.py
- tests/specify_cli/test_1716_closeout_regression.py
- tests/tasks/**
- docs/changelog/CHANGELOG.md
tags: []
tracker_refs: []
---

## Objective

Rename the live `specify_cli.ownership.models.ExecutionMode` class to
`WorkProductKind` (member **names and string values UNCHANGED**), update every src and
test consumer with **no back-compat alias**, add the re-drift guard test, and record a
CHANGELOG entry. Behavior-preserving: the only change is the class *symbol* name.

## Context

Once WP01 removes the dead enum #2, the residual footgun is the class *name*: the live
ownership enum is still called `ExecutionMode`, clashing with the external
`spec_kitty_events.status.ExecutionMode`. Renaming the class (not its values) removes
the clash while keeping on-disk WP frontmatter (`execution_mode: code_change |
planning_artifact`) wire-compatible.

Key invariants held constant (do NOT change): the field name `execution_mode`, the
function name `infer_execution_mode`, and the member names/values `CODE_CHANGE =
"code_change"` / `PLANNING_ARTIFACT = "planning_artifact"`. Only the class name and its
references change.

No back-compat alias: leaving `ExecutionMode = WorkProductKind` in the module would
keep the clashing name resolvable and violate FR-003/AC-3. Update all consumers.

**M6 headroom (AC-5):** M6 will later ADD a non-diff completion-mode member to
`WorkProductKind`. The guard test (T006) must assert *absence of the footgun*, never
`WorkProductKind`'s exact member set.

Chosen name `WorkProductKind` is verified collision-free (`git grep WorkProductKind
src/ tests/` → none on the mission base).

### Subtask T006: Red-first — add the re-drift guard test

**Purpose**: Pin the mission's user-observable contract (the footgun cannot return),
RED before the rename lands.

**Steps**:
1. Create `tests/architectural/test_execution_mode_no_redrift.py` asserting:
   - No `class ExecutionMode` appears in any `*.py` under `src/` (scan source text; 0 matches).
   - No enum under `src/` pairs a member valued `"worktree"` with a member valued
     `"code_change"` (the specific retired collision). Implement by importing candidate
     enums or scanning; keep it robust and readable.
   - `"ExecutionMode" not in mission_runtime.__all__` (retired symbol stays gone).
2. Write it so it PERMITS `WorkProductKind` having extra members (e.g. a future
   completion mode) and having a `code_change`-valued member — only the `worktree` +
   `code_change` *pairing on one enum* is forbidden.
3. Run it — on the current tree (enum #1 still named `ExecutionMode`) it MUST be RED.

**Files**: `tests/architectural/test_execution_mode_no_redrift.py` (new, ~60–100 lines)
**Validation**: RED before T007–T010; GREEN after.

### Subtask T007: Rename the class in models.py

**Purpose**: The core rename.

**Steps**:
1. In `src/specify_cli/ownership/models.py`: rename `class ExecutionMode(StrEnum)` →
   `class WorkProductKind(StrEnum)`. Keep members `CODE_CHANGE = "code_change"` and
   `PLANNING_ARTIFACT = "planning_artifact"` verbatim.
2. Update the `OwnershipManifest.execution_mode` field annotation to `WorkProductKind`
   (field NAME stays `execution_mode`).
3. Update in-module docstrings/comments referencing the old class name.

**Files**: `src/specify_cli/ownership/models.py` (modify)
**Validation**: `python -c "from specify_cli.ownership.models import WorkProductKind; print(WorkProductKind.CODE_CHANGE.value)"` prints `code_change`.

### Subtask T008: Update the ownership package internals

**Purpose**: Fix the package's own consumers + public surface.

**Steps**:
1. `src/specify_cli/ownership/__init__.py`: import `WorkProductKind`; in `__all__`
   replace `"ExecutionMode"` with `"WorkProductKind"`.
2. `src/specify_cli/ownership/inference.py`: update import; change
   `infer_execution_mode(...) -> WorkProductKind` (function name unchanged); update
   member references (`.PLANNING_ARTIFACT` / `.CODE_CHANGE`) and docstrings.
3. `src/specify_cli/ownership/validation.py`: update import + member comparisons.

**Files**: `src/specify_cli/ownership/{__init__,inference,validation}.py` (modify)
**Validation**: `mypy --strict src/specify_cli/ownership/` clean.

### Subtask T009: Update remaining src consumers

**Purpose**: Fix the 5 downstream modules.

**Steps** — in each, update the import and member/annotation references (members keep
their names, so only the class symbol changes):
1. `src/specify_cli/core/worktree.py` (import + `WorkProductKind.CODE_CHANGE` default + coercion + `.PLANNING_ARTIFACT` compare).
2. `src/specify_cli/lanes/compute.py` (import + `.PLANNING_ARTIFACT` compare).
3. `src/specify_cli/lanes/implement_support.py` (import + `.PLANNING_ARTIFACT` compare).
4. `src/specify_cli/workspace/context.py` (import + `WorkProductKind(...)` coercions + `.PLANNING_ARTIFACT` compare).
5. `src/specify_cli/cli/commands/agent/mission_parsing.py` (import + `.PLANNING_ARTIFACT.value` + docstring `:data:` ref).

**Files**: the 5 modules above (modify)
**Validation**: `git grep -n "ownership.models import ExecutionMode" src/` returns nothing; `mypy --strict src/` clean.

### Subtask T010: Update test consumers

**Purpose**: Keep the suite green (imports of the renamed class).

**Steps** — update `from specify_cli.ownership.models import ExecutionMode` →
`WorkProductKind` and all `ExecutionMode.` references (members unchanged) in:
`tests/integration/test_planning_artifact_wp.py`,
`tests/lanes/test_compute.py`,
`tests/lanes/test_compute_planning_artifact.py`,
`tests/lanes/test_compute_planning_artifact_deps.py`,
`tests/lanes/test_dependent_wp_scheduling.py`,
`tests/lanes/test_issue_1860_branch_identity_dual_era.py`,
`tests/specify_cli/lanes/test_compute_lane_depths_cycle_safety.py`,
`tests/specify_cli/ownership/test_audit_scope.py`,
`tests/specify_cli/ownership/test_inference.py`,
`tests/specify_cli/core/test_worktree.py` (the `TestExecutionModeDefaults` class-name
label may be kept or renamed for clarity — cosmetic; update any `ExecutionMode` symbol
refs inside).

**Files**: the ~10 test files above (modify)
**Validation**: targeted suites collect + pass (T012).

### Subtask T011: CHANGELOG entry

**Purpose**: Document the change per the Code Review Checklist.

**Steps**:
1. Add an `[Unreleased]` entry to `docs/changelog/CHANGELOG.md` (edit the CANONICAL
   file — the root `CHANGELOG.md` is a symlink to it). Note: dead `mission_runtime`
   `ExecutionMode` retired; ownership `ExecutionMode` renamed to `WorkProductKind`
   (member values unchanged; frontmatter wire-compatible); re-drift guard added.

**Files**: `docs/changelog/CHANGELOG.md` (modify)
**Validation**: entry present under `[Unreleased]`.

### Subtask T012: Verify green + static gates

**Steps**:
1. `pytest tests/architectural/test_execution_mode_no_redrift.py` → GREEN.
2. `pytest tests/specify_cli/ownership/ tests/lanes/ tests/specify_cli/lanes/ tests/specify_cli/core/test_worktree.py tests/integration/test_planning_artifact_wp.py` → GREEN.
3. `grep -rn "class ExecutionMode" src/` → zero.
4. `ruff check .` and `mypy --strict src/` → clean, no new suppressions.

**Files**: none (verification)

## Definition of Done

- [ ] `grep -rn "class ExecutionMode" src/` returns zero.
- [ ] `WorkProductKind` resolves; `CODE_CHANGE="code_change"`, `PLANNING_ARTIFACT="planning_artifact"` unchanged.
- [ ] Old `ExecutionMode` name no longer importable from `specify_cli.ownership.models` (no alias).
- [ ] `infer_execution_mode` and the `execution_mode` field names unchanged.
- [ ] Re-drift guard GREEN and permits an added member on `WorkProductKind`.
- [ ] All targeted suites GREEN; `ruff` + `mypy --strict src/` clean, no new suppressions.
- [ ] `[Unreleased]` CHANGELOG entry added.

## Risks

- **Missed reference** → compile/mypy break (loud, not silent) — rely on `mypy --strict src/` as the completeness check.
- **Guard too strict** would block M6 — assert absence-of-footgun, not an exact member set (AC-5).
- **Frontmatter compat** — guaranteed by holding member string values constant; proven by `test_planning_artifact_wp.py` / `test_inference.py`.

## Reviewer Guidance

- Verify no back-compat alias remains and the old name does not resolve.
- Verify member names/values, the field name, and `infer_execution_mode` are unchanged (behavior preservation).
- Verify the guard permits an added member (mentally add one and confirm it stays green) yet catches a re-introduced `worktree`+`code_change` enum.
- Confirm `tasks_transition_core.py`'s external `spec_kitty_events` `ExecutionMode` is untouched.

Implementation command: `spec-kitty agent action implement WP02 --agent <name>`
