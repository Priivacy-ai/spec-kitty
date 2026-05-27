---
work_package_id: WP10
title: CI test-mark audit
dependencies:
- WP01
- WP02
- WP03
- WP04
- WP05
- WP06
- WP07
- WP08
- WP09
requirement_refs:
- FR-012
tracker_refs: []
planning_base_branch: feat/pre-doctrine-stabilization-remediation
merge_target_branch: feat/pre-doctrine-stabilization-remediation
branch_strategy: Planning artifacts for this mission were generated on feat/pre-doctrine-stabilization-remediation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/pre-doctrine-stabilization-remediation unless the human explicitly redirects the landing branch.
subtasks:
- T042
- T043
- T044
- T045
agent: claude
history:
- date: '2026-05-27'
  event: created
agent_profile: curator-carla
authoritative_surface: tests/
execution_mode: code_change
owned_files:
- tests/agent/test_context_unit.py
- tests/specify_cli/test_lane_regression_guard.py
role: curator
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load curator-carla
```

---

## Objective

Audit all test files in modules touched by WP01–WP09. Add missing CI-quality `pytestmark` declarations. Verify the existing architectural guard passes without modification.

**Must not begin until WP01–WP09 are all merged into `feat/pre-doctrine-stabilization-remediation`.**

**Closes**: FR-012

---

## Context

The CI fast-run uses `-m "fast and not windows_ci"`. Any test file without a `pytestmark` containing `fast` (or another recognized CI-split mark) is silently excluded from fast CI runs, causing coverage gaps.

**The guard test already exists**: `tests/architectural/test_pytest_marker_convention.py::test_every_test_file_declares_a_pytestmark_marker`. This WP does NOT create a new guard test — it adds the missing marks so the existing guard passes.

**Mark taxonomy** (canonical CI-quality marks — one of these is required):
- `fast` — runs in fast CI jobs
- `unit` — unit-level tests
- `integration` — integration-level tests
- `e2e` — end-to-end tests
- `slow` — slow but not integration
- `contract` — contract tests
- `architectural` — architectural invariants
- `doctrine` — doctrine-layer tests

Additional marks (do not replace a quality mark, add alongside):
- `non_sandbox` — test spawns subprocesses or touches network
- `git_repo` — test requires a real git repository
- `windows_ci` — Windows-specific test

---

## Subtask T042 — Audit all WP01-WP09 touched test directories

**Purpose**: Systematically check every test file in every module directory touched by WP01–WP09 for a missing or wrong CI-quality `pytestmark`.

**Steps**:

1. Run the existing architectural guard to see the current failures:
   ```bash
   pytest tests/architectural/test_pytest_marker_convention.py::test_every_test_file_declares_a_pytestmark_marker -v --tb=long 2>&1
   ```
   This will list every test file without a proper `pytestmark`.

2. Cross-reference the output with the directories touched by this mission:
   - `tests/specify_cli/regression/`
   - `tests/specify_cli/docs/`
   - `tests/specify_cli/cli/`
   - `tests/specify_cli/audit/`
   - `tests/doctrine/`
   - `tests/integration/`
   - `tests/next/`
   - `tests/sync/`
   - `tests/contract/`
   - `tests/agent/`
   - `tests/auth/`
   - `tests/missions/`
   - `tests/charter/`
   - `tests/cross_cutting/`

3. For each file in the above directories that lacks a CI-quality mark: add the appropriate `pytestmark`. Use these guidelines:
   - Tests in `tests/specify_cli/cli/`: `pytest.mark.fast`
   - Tests in `tests/doctrine/`: `pytest.mark.doctrine`
   - Tests in `tests/integration/`: `pytest.mark.integration`
   - Tests in `tests/next/`: `pytest.mark.fast`
   - Tests in `tests/sync/`: `pytest.mark.fast`
   - Tests in `tests/contract/`: `pytest.mark.contract`
   - Tests in `tests/agent/`: `pytest.mark.fast`
   - Tests in `tests/auth/`: `pytest.mark.integration` or `pytest.mark.fast`
   - Tests in `tests/specify_cli/regression/`: `pytest.mark.unit`
   - Tests in `tests/specify_cli/docs/`: `pytest.mark.unit`
   - Tests in `tests/architectural/`: already have `pytest.mark.architectural`
   - Tests in `tests/charter/`: `pytest.mark.unit` or `pytest.mark.fast`
   - Tests in `tests/cross_cutting/`: `pytest.mark.architectural`
   - Tests in `tests/missions/`: `pytest.mark.integration`

4. The mark is added at module level (top of file, after imports):
   ```python
   import pytest
   pytestmark = [pytest.mark.fast]
   # or
   pytestmark = [pytest.mark.fast, pytest.mark.non_sandbox]
   ```

**Validation**:
- [ ] Every test file in the touched directories has a CI-quality mark
- [ ] You have a list of files changed (for the commit message)

---

## Subtask T043 — Add pytestmark to tests/agent/test_context_unit.py

**Purpose**: This is the one known-untagged test file identified at mission start. It must receive a `pytestmark`.

**Steps**:

1. Read the file to understand what kind of tests it contains:
   ```bash
   head -20 tests/agent/test_context_unit.py
   ```

2. Add at the module level (after imports):
   ```python
   import pytest
   pytestmark = [pytest.mark.fast]
   ```
   (Adjust to `[pytest.mark.unit]` if the tests are unit-level without subprocess usage; or `[pytest.mark.fast, pytest.mark.non_sandbox]` if they spawn processes.)

3. Run the file to confirm the mark doesn't break anything:
   ```bash
   pytest tests/agent/test_context_unit.py -v
   ```

**Files**: `tests/agent/test_context_unit.py`

**Validation**:
- [ ] File has `pytestmark` at module level
- [ ] All tests in the file still pass

---

## Subtask T044 — Add category mark to tests/specify_cli/test_lane_regression_guard.py

**Purpose**: This file currently has `pytestmark = pytest.mark.non_sandbox` only. `non_sandbox` is not a CI-quality split mark — it is an execution modifier. The file needs a quality mark (e.g., `pytest.mark.unit`) added alongside `non_sandbox` so it is included in the appropriate fast-run job.

**Steps**:

1. Read the current pytestmark:
   ```bash
   grep -n "pytestmark" tests/specify_cli/test_lane_regression_guard.py
   ```
   Expected: `pytestmark = pytest.mark.non_sandbox`

2. Update to include a quality mark:
   ```python
   pytestmark = [pytest.mark.unit, pytest.mark.non_sandbox]
   ```

3. Run the tests to confirm:
   ```bash
   pytest tests/specify_cli/test_lane_regression_guard.py -v
   ```

**Files**: `tests/specify_cli/test_lane_regression_guard.py`

**Validation**:
- [ ] File has `pytestmark = [pytest.mark.unit, pytest.mark.non_sandbox]`
- [ ] Tests still pass

---

## Subtask T045 — Verify existing architectural guard passes

**Purpose**: After adding all missing marks in T042–T044, confirm the architectural guard test now passes without any modification to the guard itself.

**Steps**:

1. Run the guard test:
   ```bash
   pytest tests/architectural/test_pytest_marker_convention.py::test_every_test_file_declares_a_pytestmark_marker -v 2>&1
   ```

2. If it still fails: there are remaining files without marks. Go back to T042 and add the missing marks.

3. Do NOT modify the guard test itself — only add marks to the failing files.

4. When the guard passes: run a broader set of the touched test files to confirm no regressions:
   ```bash
   pytest tests/agent/ tests/specify_cli/ tests/next/ tests/sync/ -v --tb=short -q 2>&1 | tail -20
   ```

**Validation**:
- [ ] `test_every_test_file_declares_a_pytestmark_marker` passes
- [ ] The guard test file itself was NOT modified
- [ ] No new test failures introduced by adding marks

---

## Branch Strategy

- **Planning/base branch**: `feat/pre-doctrine-stabilization-remediation`
- **Final merge target**: `feat/pre-doctrine-stabilization-remediation`

**CRITICAL PRE-CONDITION**: WP01–WP09 must all be merged before this WP begins. WP10 touches every test directory that the earlier WPs touched — a partial merge creates noise in the mark audit.

To start implementation:
```bash
spec-kitty agent action implement WP10 --agent claude
```

---

## Definition of Done

- [ ] `tests/architectural/test_pytest_marker_convention.py::test_every_test_file_declares_a_pytestmark_marker` passes without modification to the guard
- [ ] `tests/agent/test_context_unit.py` has `pytestmark`
- [ ] `tests/specify_cli/test_lane_regression_guard.py` has `[pytest.mark.unit, pytest.mark.non_sandbox]`
- [ ] No test files added in this WP — only `pytestmark` modifications to existing files
- [ ] No regressions in any touched test module

---

## Risks

| Risk | Likelihood | Mitigation |
|------|-----------|-----------|
| Architectural guard catches files from other (non-touched) modules | Low | Only fix files in the touched-module list; report others as pre-existing |
| Wrong mark choice (e.g., fast when test is integration) | Medium | Read each test file; use slow/integration for tests that create real git repos |
| Some test files have conditional marks that confuse the guard | Low | Read the guard test to understand what it considers acceptable |

---

## Reviewer Guidance

1. Confirm the guard test passes without modification to `test_pytest_marker_convention.py`
2. Confirm `test_lane_regression_guard.py` now has both `unit` AND `non_sandbox`
3. Confirm `test_context_unit.py` has a mark
4. No new test files were created in this WP
</content>