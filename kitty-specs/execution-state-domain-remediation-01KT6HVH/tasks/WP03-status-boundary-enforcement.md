---
work_package_id: WP03
title: status/ Module Boundary Enforcement
dependencies:
- WP02
requirement_refs:
- FR-011
- FR-012
- FR-013
- FR-014
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
- T016
- T017
agent: claude
history:
- date: '2026-06-03'
  event: created
  author: spec-kitty
agent_profile: python-pedro
authoritative_surface: tests/architectural/
execution_mode: code_change
owned_files:
- tests/architectural/test_status_module_boundary.py
- src/specify_cli/missions/**
- src/specify_cli/merge/**
- src/specify_cli/next/**
- src/specify_cli/lanes/**
- src/specify_cli/post_merge/**
- src/specify_cli/agent_utils/**
- src/specify_cli/coordination/**
- src/specify_cli/doc_state.py
- src/specify_cli/gap_analysis.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Run `/ad-hoc-profile-load` and specify profile `python-pedro` before reading further.

---

## Objective

Create an architectural boundary test that enforces the `status/` module facade and fix all bypass imports of `status.*` submodules in the files this WP owns. After this WP, no code outside `status/` (except the explicitly exempted `coordination/status_transition.py`) may import any `status.*` submodule directly.

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target**: `main`
- **Prerequisite**: WP02 (e2e ratchet) must be merged and green before starting
- Start with: `spec-kitty agent action implement WP03 --agent claude`

## Context

`status/__init__.py` has a curated `__all__` of ~35 symbols but ~245 imports bypass it by importing `status.<submodule>` directly. This makes `status/` unrefactorable. The fix is:
1. An architectural test that enforces the boundary
2. Fixing all bypass imports in the files this WP owns

**Scope of this WP**: Fix bypass imports in the directories listed in `owned_files`. WP04 handles `cli/commands/agent/status.py` (that file is fully rewritten). WP06 handles `runtime/next/runtime_bridge.py`.

**Files NOT in scope for this WP**:
- `src/specify_cli/status/` — boundary test exempts all files within the `status/` package itself
- `src/specify_cli/coordination/status_transition.py` — explicitly exempted as internal domain plumbing
- `src/specify_cli/cli/commands/agent/status.py` — owned by WP04
- `src/runtime/next/runtime_bridge.py` — owned by WP06
- `src/specify_cli/status/__init__.py` — owned by WP04 (for MissionStatus export)

**Pattern reference**: `tests/architectural/test_shared_package_boundary.py` — read this entire file before writing the new test.

---

## Subtask T011 — Create test_status_module_boundary.py (pytestarch rule)

**File**: `tests/architectural/test_status_module_boundary.py`

**Purpose**: Declare a pytestarch rule that no module outside `specify_cli.status` may import any `specify_cli.status.*` submodule directly.

**Steps**:
1. Read `tests/architectural/test_shared_package_boundary.py` in full — use its import style and pytestarch rule patterns
2. Create `test_status_module_boundary.py` with a class `TestStatusModuleBoundary`
3. Write the pytestarch rule:
   ```python
   from pytestarch import EvaluableArchitecture, get_evaluable_architecture

   class TestStatusModuleBoundary:
       def test_no_direct_status_submodule_imports(self, evaluable) -> None:
           """No module outside specify_cli.status may import status.* submodules directly."""
           (
               evaluable
               .modules_that()
               .are_not_sub_modules_of("specify_cli.status")
               .should_not()
               .import_modules_that()
               .are_sub_modules_of("specify_cli.status")
               .except_modules_that()
               .are_named("specify_cli.coordination.status_transition")
           )
   ```
4. Add the `evaluable` fixture from the conftest (copy pattern from `test_shared_package_boundary.py`)

**Validation**: Test exists, imports `pytestarch`, defines the boundary rule with the `coordination.status_transition` exemption.

---

## Subtask T012 — Add AST Scanner Pass

**Purpose**: Supplement pytestarch with an AST scan that catches lazy imports (e.g., inside functions) that pytestarch may miss.

**Steps**:
1. In `test_status_module_boundary.py`, add a second test class or method `test_ast_scan_no_direct_status_imports`:
   ```python
   import ast
   import pathlib

   def test_ast_scan_no_direct_status_imports() -> None:
       src_root = pathlib.Path("src")
       violations = []
       exempt_files = {
           src_root / "specify_cli/coordination/status_transition.py",
           # Add other known exemptions
       }
       for py_file in src_root.rglob("*.py"):
           if py_file in exempt_files:
               continue
           # Skip files inside status/ itself
           if "specify_cli/status" in str(py_file):
               continue
           tree = ast.parse(py_file.read_text())
           for node in ast.walk(tree):
               if isinstance(node, (ast.Import, ast.ImportFrom)):
                   if isinstance(node, ast.ImportFrom) and node.module:
                       if (node.module.startswith("specify_cli.status.")
                               and not node.module == "specify_cli.status"):
                           violations.append(f"{py_file}:{node.lineno}: {node.module}")
       assert not violations, f"Direct status submodule imports found:\n" + "\n".join(violations)
   ```

**Validation**: AST scanner detects any `from specify_cli.status.emit import ...` pattern outside `status/` and the exempt files.

---

## Subtask T013 — Add Injection Proof Test

**Purpose**: Prove the scanner actually catches violations (not vacuously passing).

**Steps**:
1. Add a test that writes a synthetic bypass import to a tmp file and asserts the scanner catches it:
   ```python
   def test_ast_scan_catches_injected_violation(tmp_path: pathlib.Path) -> None:
       bad_file = tmp_path / "bad_module.py"
       bad_file.write_text("from specify_cli.status.emit import emit_status_transition\n")
       # Run the AST scan against just this file
       violations = scan_for_bypass_imports([bad_file], exempt_files=set())
       assert len(violations) == 1
       assert "status.emit" in violations[0]
   ```
2. Refactor the AST scanner into a helper function `scan_for_bypass_imports(files, exempt_files)` to make it testable

**Validation**: Injection proof test passes. The scanner function is extractable as a helper.

---

## Subtask T014 — Grep Audit: Enumerate All Bypass Imports

**Purpose**: Identify every file in `owned_files` directories that has a bypass import.

**Steps**:
1. Run the grep:
   ```bash
   grep -rn "from specify_cli\.status\." src/specify_cli/ --include="*.py" \
     | grep -v "^src/specify_cli/status/" \
     | grep -v "status_transition.py" \
     | grep -v "__init__.py"
   ```
2. Also check `src/runtime/next/` to understand the scope there (but DO NOT fix those — WP06 owns them):
   ```bash
   grep -rn "from specify_cli\.status\." src/runtime/ --include="*.py"
   ```
3. Document the count in a comment at the top of `test_status_module_boundary.py`:
   ```python
   # Bypass import audit (2026-06-03): N imports found across M files
   # Fixed by WP03 (non-runtime, non-status, non-status_transition files)
   ```

**Validation**: You have a complete list of bypass imports in the directories this WP owns. Do not proceed to T015 without this list.

---

## Subtask T015 — Fix All Bypass Imports in Owned Files

**Purpose**: Change all bypass imports to use the public facade.

**Steps**:
1. For each bypass import found in T014 (in this WP's owned directories only):
   - `from specify_cli.status.emit import X` → `from specify_cli.status import X`
   - `from specify_cli.status.reducer import X` → `from specify_cli.status import X`
   - `from specify_cli.status.models import X` → `from specify_cli.status import X`
   - etc.

2. **Before changing**: verify that `X` is already in `status/__init__.py`'s `__all__`. If it is NOT:
   - Check if it has genuine external use (callers outside `status/`)
   - If yes: add it to `status/__init__.py` `__all__` (coordinate with WP04 implementer if there's any concern about `__init__.py` ownership)
   - If no external use: rename it `_X` inside the submodule and update all callers

3. Work through files module by module. For each file:
   - Check if the import is now satisfied by the public `__all__`
   - Adjust as needed
   - Run `python -c "import specify_cli.status"` to confirm no import errors

4. Run the full test suite after each batch: `pytest tests/ -x -q`

**Note on scope**: Only fix imports in directories under `owned_files`. Skip `src/specify_cli/cli/commands/agent/status.py` (WP04) and `src/runtime/next/` (WP05/WP06).

**Validation**: `grep -rn "from specify_cli\.status\." src/specify_cli/ --include="*.py" | grep -v "^src/specify_cli/status/"` returns only lines from `coordination/status_transition.py` and `cli/commands/agent/status.py`.

---

## Subtask T016 — Verify coordination/status_transition.py Exemption

**Purpose**: Confirm the exemption for internal domain plumbing is correct and documented.

**Steps**:
1. Read `src/specify_cli/coordination/status_transition.py` — understand which `status/` internals it imports and why
2. Verify that these imports are intentional (it is the transactional coordinator, calling `status.emit`, `status.reducer`, `status.locking`, etc.)
3. In the pytestarch rule (T011), confirm that `.except_modules_that().are_named("specify_cli.coordination.status_transition")` correctly excludes it
4. Add a comment in `test_status_module_boundary.py` explaining the exemption:
   ```python
   # coordination/status_transition.py is exempt: it is internal Mission Management
   # domain plumbing that coordinates transactional status transitions. It is NOT
   # an external caller of status/; it is part of the same bounded module.
   ```

**Validation**: The boundary test passes with `coordination/status_transition.py` in place. The exemption comment is present.

---

## Subtask T017 — Confirm Boundary Test Passes and CI Green

**Steps**:
1. Run `pytest tests/architectural/test_status_module_boundary.py -v` — all tests pass
2. Run `pytest tests/ -x -q` — no regressions
3. Run `pytest tests/architectural/test_execution_context_parity.py -v` — WP02 ratchet still green
4. Commit all changes

**Validation**: All tests pass. The grep audit shows zero bypass imports in the owned directories (except exempted files).

---

## Definition of Done

- [ ] `tests/architectural/test_status_module_boundary.py` exists with pytestarch rule, AST scanner, and injection proof
- [ ] `coordination/status_transition.py` exemption documented and tested
- [ ] All bypass imports in owned directories fixed
- [ ] `pytest tests/architectural/ -v` passes
- [ ] `pytest tests/ -x` passes (no regressions)
- [ ] e2e ratchet (WP02) still green

## Risks

- Some symbols in `__all__` may have been added during WP04's concurrent work — coordinate if there are conflicts on `status/__init__.py`
- ~245 imports could be spread across many small files — batch the fixes by module directory to stay organized
- A symbol may not be in `__all__` but have real external callers — don't blindly rename it private without checking

## Reviewer Guidance

- Run the bypass grep before and after to verify count drops to zero in owned directories
- Check that the pytestarch rule would have caught the original violations (not vacuously passing)
- Verify `coordination/status_transition.py` exemption is explicit and justified in code comment
