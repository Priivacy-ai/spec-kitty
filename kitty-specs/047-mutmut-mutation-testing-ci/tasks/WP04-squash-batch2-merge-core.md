---
work_package_id: WP04
title: Squash Survivors — Batch 2 (merge/, core/)
lane: "done"
dependencies:
- WP03
subtasks:
- T018
- T019
- T020
- T021
- T022
phase: Phase 2 - Squashing Campaign
assignee: ''
agent: ''
shell_pid: ''
review_status: ''
reviewed_by: ''
review_feedback: ''
history:
- timestamp: '2026-03-01T16:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- FR-009
- FR-010
- FR-012
---

# Work Package Prompt: WP04 – Squash Survivors — Batch 2 (merge/, core/)

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check `review_status`. If it says `has_feedback`, read `review_feedback` first.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback, update `review_status: acknowledged`.

---

## Review Feedback

*No feedback yet — this is a fresh work package.*

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ` ```python `, ` ```bash `

---

## Objectives & Success Criteria

- All **killable** surviving mutants in `src/specify_cli/merge/` have been killed by targeted tests.
- All **killable** surviving mutants in `src/specify_cli/core/` have been killed by targeted tests.
- Any **equivalent** mutants are appended to `kitty-specs/047-mutmut-mutation-testing-ci/mutmut-equivalents.md` with rationale.
- Mutation score for the combined `merge/` + `core/` scope is measurably higher than the pre-campaign baseline.
- All existing tests continue to pass.

## Context & Constraints

- **Branch**: `architecture/restructure_and_proposals` (no worktree)
- **Depends on**: WP03 (batch 1 complete; `mutmut-equivalents.md` exists)
- **Spec FR-012**: Killable mutants in the priority scope must be killed.
- **Key files in scope**:
  - `src/specify_cli/merge/state.py` — MergeState dataclass, persistence functions
  - `src/specify_cli/merge/preflight.py` — PreflightResult, WPStatus, validation checks
  - `src/specify_cli/merge/executor.py` — merge execution with state tracking
  - `src/specify_cli/merge/forecast.py` — conflict prediction for dry-run
  - `src/specify_cli/core/` — shared abstractions, dependency graph, protocol definitions
- **Note for merge/ tests**: Preflight and executor require a git repository context.
  Use `tmp_path` with `git init` or mock git calls at the boundary (`subprocess.run`).

**Implementation command** (since WP03 is the dependency):
```bash
spec-kitty implement WP04 --base WP03
```
*(No worktree for this feature — work directly on the branch.)*

## Subtasks & Detailed Guidance

### Subtask T018 – Run mutmut on merge/ and record survivors

**Purpose**: Establish the pre-campaign baseline for `merge/` and identify all
surviving mutants.

**Steps**:
1. Run mutmut scoped to the merge module:
   ```bash
   mutmut run --paths-to-mutate src/specify_cli/merge/
   ```
2. Record surviving mutant IDs:
   ```bash
   mutmut results
   ```
3. Export baseline stats:
   ```bash
   mutmut export-cicd-stats --output out/reports/mutation/mutation-stats-merge-baseline.json
   ```

**Files**: None modified (measurement step).

**Notes**: `merge/` contains state persistence and preflight logic. Mutmut may generate
many mutants here. Run to completion before triaging.

---

### Subtask T019 – Triage and kill merge/ survivors

**Purpose**: Classify surviving mutants in `merge/` and write targeted tests to kill
the killable ones.

**Triage steps**:
1. For each surviving mutant ID from T018, run `mutmut show <id>` and classify:
   - **Killable**: mutation changes meaningful logic (e.g., adds/removes a field check, flips a condition).
   - **Equivalent**: mutation changes cosmetic detail with no observable difference.

**Key killable patterns in merge/**:
- `state.py`: Mutations to `MergeState` field defaults or `remaining_wps` computation. Test: assert `remaining_wps` returns the correct list after marking some WPs completed.
- `preflight.py`: Mutations removing a validation check. Test: construct a dirty worktree scenario and assert preflight fails.
- `forecast.py`: Mutations changing conflict detection logic. Test: set up two branches with conflicting edits and assert the forecast correctly identifies them.

**Writing tests**:
1. Look at existing tests for merge/:
   ```bash
   find tests/ -name "*merge*" -o -name "*preflight*" -o -name "*state*" | grep -v status
   ```
2. Add new test functions in the appropriate file or create a new one under `tests/unit/merge/`.
3. For preflight tests that need a git repo:
   ```python
   def test_preflight_dirty_worktree(tmp_path):
       import subprocess
       subprocess.run(["git", "init"], cwd=tmp_path, check=True)
       # ... set up worktree with uncommitted changes ...
       result = run_preflight(...)
       assert not result.passed
       assert any("clean" in e for e in result.errors)
   ```
4. After each batch of new tests, re-run mutmut on the specific file to verify kills.

**Files**: `tests/unit/merge/*.py` (extend or create)

**Validation**:
```bash
pytest tests/unit/merge/ -v
mutmut run --paths-to-mutate src/specify_cli/merge/
mutmut results  # confirm killed count increased
```

---

### Subtask T020 – Run mutmut on core/ and record survivors

**Purpose**: Establish the pre-campaign baseline for `core/` and identify all
surviving mutants.

**Steps**:
1. Run mutmut scoped to the core module:
   ```bash
   mutmut run --paths-to-mutate src/specify_cli/core/
   ```
2. Record survivors:
   ```bash
   mutmut results
   ```
3. Export baseline stats:
   ```bash
   mutmut export-cicd-stats --output out/reports/mutation/mutation-stats-core-baseline.json
   ```

**Files**: None modified (measurement step).

**Notes**: If `core/` is thin (few functions), the run will be fast and there may be
few survivors. Proceed to T021 as soon as the run completes.

---

### Subtask T021 – Triage and kill core/ survivors

**Purpose**: Classify surviving mutants in `core/` and write targeted tests.

**Triage steps**: Same as T019, applied to `core/`.

**Key areas in core/**:
- Dependency graph utilities (if present) — mutations changing graph traversal or cycle detection logic.
- Protocol/ABC definitions — mutations that change method signatures or return type hints are typically equivalent; focus on concrete logic.
- Any validation utilities shared across subsystems.

**Writing tests**:
1. Find existing tests:
   ```bash
   find tests/ -path "*/unit/core/*" -o -path "*/core/test_*"
   ```
2. Add targeted tests under `tests/unit/core/`.
3. Follow the same write → run → verify loop as T019.

**Files**: `tests/unit/core/*.py` (extend or create)

**Validation**:
```bash
pytest tests/unit/core/ -v
mutmut run --paths-to-mutate src/specify_cli/core/
mutmut results
```

---

### Subtask T022 – Update mutmut-equivalents.md with batch 2 findings

**Purpose**: Document all equivalent mutants found in `merge/` and `core/` alongside
the batch 1 entries from WP03.

**Steps**:
1. Open `kitty-specs/047-mutmut-mutation-testing-ci/mutmut-equivalents.md`.
2. Append a new section for batch 2:

```markdown
### merge/ equivalents

| Mutant ID | File | Line | Mutation | Rationale |
|-----------|------|------|----------|-----------|
| ... | ... | ... | ... | ... |

### core/ equivalents

| Mutant ID | File | Line | Mutation | Rationale |
|-----------|------|------|----------|-----------|
| ... | ... | ... | ... | ... |
```

3. If no equivalent mutants were found, add: "No equivalent mutants identified in this batch."

**Files**: `kitty-specs/047-mutmut-mutation-testing-ci/mutmut-equivalents.md` (update)

## Risks & Mitigations

- **merge/ tests require git repo**: Use `tmp_path` + `git init` for filesystem-level tests; mock `subprocess.run` for tests focused on the merge logic above the git layer.
- **core/ is thin or has no killable mutants**: If `core/` generates fewer than 5 mutants and most are equivalent, complete T021 quickly and move on — don't over-engineer tests for a thin module.
- **Pre-existing test failures in merge/**: Run `pytest tests/ -k merge` before starting T019 to ensure the baseline is clean. If there are pre-existing failures, fix them before adding new tests (don't mask the signal).

## Review Guidance

- Confirm surviving mutant count in `merge/` is lower after new tests than the T018 baseline.
- Confirm surviving mutant count in `core/` is lower after new tests than the T020 baseline.
- Spot-check 2–3 of the new tests for merge/: do they actually exercise the preflight/state logic?
- Confirm `mutmut-equivalents.md` has been updated with batch 2 entries.
- Run `pytest tests/ -v --tb=short` to confirm no regressions.

## Activity Log

- 2026-03-01T16:00:00Z – system – lane=planned – Prompt created.
