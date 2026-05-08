---
work_package_id: WP07
title: api_types.py Deletion + Architectural Boundary Test
dependencies:
- WP02
- WP03
- WP04
- WP05
- WP06
requirement_refs:
- FR-019
planning_base_branch: feature/645-api-surface-completion-mission-c
merge_target_branch: feature/645-api-surface-completion-mission-c
branch_strategy: Planning artifacts for this feature were generated on feature/645-api-surface-completion-mission-c. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/645-api-surface-completion-mission-c unless the human explicitly redirects the landing branch.
created_at: '2026-05-04T17:07:04Z'
subtasks:
- T033
- T034
- T035
- T036
agent: "copilot:claude-sonnet-4-6:alphonso:reviewer"
shell_pid: "2033268"
history:
- at: '2026-05-04T17:07:04Z'
  event: created
  note: Initial task breakdown
authoritative_surface: tests/architectural/
execution_mode: code_change
lane: planned
mission_id: 01KQSXDASEMGGZNAX3A5FXSEPM
owned_files:
- src/dashboard/api_types.py
- tests/architectural/test_dashboard_boundary.py
tags: []
---

## Objective

With all callers migrated to canonical type locations by WP02–WP06, delete `src/dashboard/api_types.py`. Extend the architectural boundary test to enforce the one-way dependency direction: `specify_cli`, `kernel`, and `status` must never import from the `dashboard` package. Confirm the full test suite is green.

## Context

This is the convergence gate for the TypedDict migration. It depends on WP02, WP03, WP04, WP05, and WP06 all completing successfully. The precondition is simple: zero references to `dashboard.api_types` anywhere in `src/` or `tests/` (except in the file itself, which is being deleted).

The architectural boundary test at `tests/architectural/test_dashboard_boundary.py` already exists and checks some import relationships. This WP extends it to add an assertion that enforces C-009: no module under `src/specify_cli/`, `src/kernel/`, or `src/specify_cli/status/` imports from `src/dashboard/`.

## Branch Strategy

- `planning_base_branch`: `feature/645-api-surface-completion-mission-c`
- `merge_target_branch`: `feature/645-api-surface-completion-mission-c`
- All of WP02, WP03, WP04, WP05, WP06 must be merged to the lane branch before this WP starts.

## Subtask Guide

### T033: Confirm Zero Remaining `dashboard.api_types` References

**Purpose:** Verify that every caller has been updated before attempting deletion. A single missed import will produce an `ImportError` in production.

**Steps:**

1. Run the comprehensive grep across all Python source and test files:

```bash
grep -rn \
  "from dashboard.api_types\|import dashboard.api_types\|from specify_cli.dashboard.api_types\|import specify_cli.dashboard.api_types" \
  src/ tests/ --include="*.py"
```

2. **Expected result:** The only file that appears is `src/dashboard/api_types.py` itself (the module header comment referencing its own path). If any other file appears, that import must be fixed before proceeding.

3. Common fixes if stragglers appear:
   - `src/dashboard/api/routers/*.py` → should have been fixed in WP06. Re-apply the migration map from WP06.
   - `src/dashboard/services/*.py` → should have been fixed in WP05. Re-apply.
   - `src/specify_cli/dashboard/api_types.py` (shim) → should have been deleted or cleaned in WP05.
   - `tests/` files → update test imports to match production canonical locations.

4. Also check for indirect references via `__all__`:
   ```bash
   grep -rn "api_types" src/ tests/ --include="*.py" | grep -v "^src/dashboard/api_types.py"
   ```

5. Record the grep output (empty) in a commit message comment or WP history note as evidence.

**Files:** (audit only — no modifications)

**Validation:**
- [x] Zero matches for `from dashboard.api_types` outside of `src/dashboard/api_types.py` itself
- [x] Zero matches for `from specify_cli.dashboard.api_types` anywhere (shim deleted or emptied in WP05)

---

### T034: Delete `src/dashboard/api_types.py` and Run Targeted Tests

**Purpose:** Remove the monolith file. Confirm that the dashboard and specify_cli test suites still pass with no import errors.

**Steps:**

1. Delete the file:
   ```bash
   rm src/dashboard/api_types.py
   ```

2. Run the targeted test suites immediately:
   ```bash
   cd src && pytest ../tests/test_dashboard/ ../tests/specify_cli/dashboard/ -x --tb=short
   ```

3. If any `ImportError` or `ModuleNotFoundError` appears referencing `dashboard.api_types`, find the file and fix the import. Then re-run.

4. Common error patterns and fixes:
   - `ImportError: cannot import name 'GlossaryTermRecord' from 'dashboard.api_types'` → this file was not updated in WP02. Fix: `from specify_cli.glossary.types import GlossaryTermRecord`.
   - `ImportError: cannot import name 'HealthResponse' from 'dashboard.api_types'` → this file was not updated in WP06. Fix: `from kernel.api_types import HealthResponse`.

5. All tests must pass before proceeding to T035.

**Files:** `src/dashboard/api_types.py` (delete)

**Validation:**
- [x] `src/dashboard/api_types.py` does not exist
- [x] `pytest tests/test_dashboard/ tests/specify_cli/dashboard/ -x` exits with code 0
- [x] No `ImportError` or `ModuleNotFoundError` in test output

---

### T035: Extend `tests/architectural/test_dashboard_boundary.py`

**Purpose:** Add an architectural assertion that enforces C-009: modules in `specify_cli`, `kernel`, and `status` must not import from the `dashboard` package. This prevents future regressions.

**Steps:**

1. Open `tests/architectural/test_dashboard_boundary.py` and read the existing tests to understand the import-graph inspection pattern already used.

2. Add the following test function (adapt the import-graph inspection pattern to match what's already in the file):

```python
import ast
import os
from pathlib import Path
import pytest


SRC_ROOT = Path(__file__).parent.parent.parent / "src"

# Packages that must NEVER import from dashboard.*
FORBIDDEN_IMPORTERS = [
    SRC_ROOT / "specify_cli",
    SRC_ROOT / "kernel",
]

# The dashboard package root
DASHBOARD_PACKAGE = "dashboard"


def _collect_python_files(root: Path) -> list[Path]:
    """Return all .py files under root."""
    return list(root.rglob("*.py"))


def _extract_imports(source: str) -> list[str]:
    """Return all module names imported by source (top-level only)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports


def test_no_reverse_dependency_dashboard_to_domain():
    """No module in specify_cli or kernel may import from dashboard.*

    Enforces architectural boundary C-009: the dependency direction is
    dashboard → domain (specify_cli, kernel), never the reverse.
    """
    violations: list[tuple[str, str]] = []

    for package_root in FORBIDDEN_IMPORTERS:
        if not package_root.exists():
            continue
        for py_file in _collect_python_files(package_root):
            try:
                source = py_file.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for imported_module in _extract_imports(source):
                if imported_module == DASHBOARD_PACKAGE or \
                        imported_module.startswith(f"{DASHBOARD_PACKAGE}."):
                    violations.append((str(py_file.relative_to(SRC_ROOT)), imported_module))

    if violations:
        lines = "\n".join(f"  {f} imports {m}" for f, m in violations)
        pytest.fail(
            f"C-009 violation: {len(violations)} module(s) in specify_cli/kernel "
            f"import from dashboard.*:\n{lines}"
        )
```

3. Run the new test: `cd src && pytest ../tests/architectural/test_dashboard_boundary.py::test_no_reverse_dependency_dashboard_to_domain -v`

4. If it fails, investigate the import causing the violation:
   - If it's in test infrastructure (e.g., a conftest), it may be acceptable as a test-only dependency. Consider scoping the check to `src/` only (not `tests/`).
   - If it's a real production import, it must be refactored before WP07 can complete.

5. Ensure the new test coexists with all existing tests in the file.

**Files:** `tests/architectural/test_dashboard_boundary.py` (update)

**Validation:**
- [x] `test_no_reverse_dependency_dashboard_to_domain` function is present
- [x] The test passes: `pytest tests/architectural/test_dashboard_boundary.py -v` exits with code 0
- [x] Existing tests in the file are unchanged and still pass

---

### T036: Run Full Test Suite

**Purpose:** Final gate — confirm CI-equivalent green state after deletion and architectural test addition.

**Steps:**

1. Run the full test suite from the `src/` directory:
   ```bash
   cd src && pytest ../tests/ -x --tb=short
   ```

2. If any test fails:
   - `ImportError` from `dashboard.api_types`: find the file and fix the import (it was missed in T033's audit).
   - `AssertionError` in `test_dashboard_boundary.py`: investigate which `specify_cli` or `kernel` module still imports from `dashboard`.
   - Any other failure: investigate and fix before marking WP07 done.

3. Run mypy on the complete `src/` tree as a final check:
   ```bash
   cd src && mypy --strict specify_cli/ kernel/ dashboard/ --ignore-missing-imports
   ```
   (Use `--ignore-missing-imports` only if the full project has known unresolved stubs; otherwise remove it.)

4. Confirm that `src/dashboard/api_types.py` does not exist in the repository after all tests pass.

**Files:** (no new files — full-suite verification)

**Validation:**
- [x] `pytest ../tests/ -x --tb=short` exits with code 0 from `src/`
- [x] `mypy` passes on the key packages
- [x] `src/dashboard/api_types.py` is absent

---

## Definition of Done

- [x] `src/dashboard/api_types.py` is deleted from the repository
- [x] Zero references to `dashboard.api_types` or `specify_cli.dashboard.api_types` remain in any `src/` or `tests/` file
- [x] `tests/architectural/test_dashboard_boundary.py` contains `test_no_reverse_dependency_dashboard_to_domain`
- [x] The architectural boundary test passes
- [x] All existing architectural tests still pass
- [x] Full test suite (`pytest tests/ -x`) exits with code 0

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Missed import not caught by T033 grep | High | T034 deletion immediately reveals any missed import as an `ImportError` |
| Architectural test catches a legitimate cross-package reference in test infrastructure | Medium | Scope the check to `src/` only (not `tests/`); test infra may validly import dashboard types |
| mypy errors surface after deletion (e.g., inferred types differ) | Low | Run `mypy --strict` in T036 before declaring done |
| Full test suite takes too long | Low | Use `-x` to stop on first failure; run `tests/test_dashboard/` first for fast feedback |

## Reviewer Guidance

1. Confirm `src/dashboard/api_types.py` is absent from the working tree (`git status` should not show it).
2. Run the T033 grep command and confirm zero output.
3. Review the new test in `test_dashboard_boundary.py` — confirm it uses AST inspection (not string grep) and correctly identifies the `dashboard` package as the forbidden import target.
4. Run `pytest tests/ -x` and confirm fully green.
5. Confirm the architectural test is in `tests/architectural/` (not `tests/test_dashboard/`).

Implement command: `spec-kitty agent action implement WP07 --agent <name>`

## Activity Log

- 2026-05-04T18:07:47Z – copilot:claude-sonnet-4-6:alphonso:implementer – shell_pid=1992830 – Started implementation via action command
- 2026-05-04T18:28:37Z – copilot:claude-sonnet-4-6:alphonso:implementer – shell_pid=1992830 – dashboard/api_types.py deleted; C-009 architectural test added; full suite green
- 2026-05-04T18:29:27Z – copilot:claude-sonnet-4-6:alphonso:reviewer – shell_pid=2033268 – Started review via action command
- 2026-05-04T18:30:59Z – copilot:claude-sonnet-4-6:alphonso:reviewer – shell_pid=2033268 – Review passed: dashboard/api_types.py deleted with zero remaining callers; C-009 arch test added and passes
