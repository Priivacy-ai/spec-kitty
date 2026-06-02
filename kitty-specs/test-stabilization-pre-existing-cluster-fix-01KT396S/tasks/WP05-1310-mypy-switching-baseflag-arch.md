---
work_package_id: WP05
title: '#1310 Residual: mypy, Mission Switching, Base-Flag, Architectural'
dependencies:
- WP04
requirement_refs:
- FR-013
- FR-014
- FR-015
- FR-016
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T023
- T024
- T025
- T026
- T027
- T028
- T029
- T030
agent: claude
history:
- date: '2026-06-02'
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/mission_step_contracts/
execution_mode: code_change
owned_files:
- src/specify_cli/mission_step_contracts/executor.py
- src/specify_cli/missions/**/*.py
- src/specify_cli/cli/commands/implement.py
- tests/missions/test_mission_switching_integration.py
- tests/cli/commands/test_implement_base_flag.py
- tests/cli/test_implement_bulk_edit_planning.py
- tests/architectural/**/*.py
- tests/cross_cutting/test_mypy_strict_mission_step_contracts.py
- tests/init/**/*.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

Fix five remaining #1310 sub-failures:

1. **mypy strict** — `mission_step_contracts/executor.py` fails `mypy --strict`.
2. **Mission switching** — `test_mission_switching_integration` × 2 are blocked by an overly aggressive guard.
3. **Base-flag plumbing** — `--base` flag is not threaded through to the bulk-edit warning gate.
4. **Architectural tests** — a package-boundary constraint is violated.
5. **Init skill** — `test_init_creates_agents_skills_for_codex` may be blocked by an external dependency; skip gracefully if so.

**GitHub issue closed**: #1310 (residual, second half)

---

## Context

These five failures are structurally independent but all live in the same lane (C) as WP04. The init skill failure (T029) may be an external dependency — if the `spec-kitty.checklist` skill package is missing because a WP from another mission hasn't merged, we skip with a clear pytest mark.

---

## Subtasks

### T023 — Run mypy --strict on executor.py and document errors

**Steps**:

1. Run:
   ```bash
   .venv/bin/mypy --strict src/specify_cli/mission_step_contracts/executor.py 2>&1
   ```

2. Document every error:
   - Line number
   - Error code (e.g., `error: Function is missing a return type annotation`)
   - What annotation is needed

3. Common mypy --strict errors to expect:
   - `error: Function is missing a return type annotation [no-untyped-def]`
   - `error: Argument 1 to "X" has incompatible type "Y"; expected "Z" [arg-type]`
   - `error: "X" has no attribute "Y" [attr-defined]`
   - `error: Need type annotation for "X" [var-annotated]`

**Files**: `src/specify_cli/mission_step_contracts/executor.py`

**Output**: Complete list of mypy errors with line numbers.

---

### T024 — Add type annotations to executor.py

**Steps**:

1. For each error from T023, add the correct annotation:

   - **Missing return type**: Add `-> ReturnType:` to the function signature.
   - **Untyped argument**: Add `: Type` to the parameter.
   - **var-annotated**: Add `x: list[str] = []` style annotation.
   - **Missing import**: Add from `typing import Any, Optional, Union` etc. as needed.

2. Run mypy after each annotation batch to confirm progress:
   ```bash
   .venv/bin/mypy --strict src/specify_cli/mission_step_contracts/executor.py
   ```

3. If `executor.py` calls functions from other modules that are not yet mypy-strict, you may need to add `# type: ignore[<code>]` sparingly. Prefer fixing the annotation over suppressing.

4. Do not change the runtime behavior of any function — annotation-only changes.

**Files**: `src/specify_cli/mission_step_contracts/executor.py`

**Validation**: `mypy --strict src/specify_cli/mission_step_contracts/executor.py` exits 0 with no errors.

---

### T025 — Identify mission switching guard condition

**Steps**:

1. Run the failing test to see the error:
   ```bash
   pytest tests/missions/test_mission_switching_integration.py -v -s 2>&1 | head -60
   ```

2. The error message will name the guard condition or the exception raised.

3. Find the mission switching code:
   ```bash
   grep -rn "mission_type\|switch.*mission\|mission.*switch" src/specify_cli/ --include="*.py" | grep -v "test_" | head -20
   ```

4. Read the guard logic. It may be checking:
   - That the current mission type matches the requested type exactly (too strict)
   - That a feature flag is enabled (may be disabled in test context)
   - That a field in `meta.json` is set (may be missing in test fixtures)

5. Record: exact file, line, and condition that blocks the switch.

---

### T026 — Fix mission switching guard

**Steps**:

1. Apply the minimum fix to the guard identified in T025:
   - If the guard checks exact type equality but should allow compatible types: expand the condition.
   - If the guard checks a feature flag: ensure the test fixture enables the flag (prefer fixture fix over production code change).
   - If the guard reads from `meta.json`: ensure the test fixture creates a valid `meta.json`.

2. Prefer fixing the test fixture over changing production logic. Only change production code if the guard is genuinely incorrect for all contexts.

3. Run both integration tests:
   ```bash
   pytest tests/missions/test_mission_switching_integration.py -v 2>&1
   ```

**Files**:
- Production mission switching module (from T025)
- `tests/missions/test_mission_switching_integration.py` (fixture if needed)

---

### T027 — Fix --base flag threading through to bulk-edit gate

**Steps**:

1. Run the failing tests:
   ```bash
   pytest tests/cli/commands/test_implement_base_flag.py \
          tests/cli/test_implement_bulk_edit_planning.py -v -s 2>&1 | head -60
   ```

2. The `--base` flag was added in FR-021 (mission `068-post-merge-reliability-and-release-hardening`). Read `src/specify_cli/cli/commands/implement.py` to find the `--base` parameter.

3. Trace the flag from the CLI parameter through to the bulk-edit gate function:
   - Does `implement.py` accept `base: Optional[str] = None`?
   - Does it pass `base` to the underlying `implement_action()`?
   - Does `implement_action()` pass it to the bulk-edit gate?

4. Find where the flag is dropped and add the missing pass-through. This is typically a parameter that was added to the CLI but not threaded through 1-2 intermediate function calls.

5. The bulk-edit warning should be emitted when `--base` is set and the WP touches bulk-edit-classified files.

**Files**:
- `src/specify_cli/cli/commands/implement.py`
- The intermediate function(s) between CLI and bulk-edit gate

---

### T028 — Fix architectural boundary violation

**Steps**:

1. Run the architectural tests:
   ```bash
   pytest tests/architectural/ -v -s 2>&1 | head -80
   ```

2. The test output will name:
   - The module that violates a boundary
   - The disallowed import pattern
   - The rule being enforced

3. Common boundary violations after the shared-package cutover:
   - A module in `src/specify_cli/` imports directly from `spec_kitty_runtime` (retired)
   - A module imports across package boundaries (e.g., `charter` importing from `specify_cli`)
   - A test imports from a private module (`_internal_runtime`) when it should use the public API

4. Fix the violation:
   - If an import references the retired `spec_kitty_runtime`: replace with `specify_cli.next._internal_runtime.*`
   - If a cross-boundary import: move the shared code to the correct package or create a proper public interface
   - If a test import: update the test to use the public import path

**Files**: The module(s) identified by the architectural tests.

---

### T029 — Handle init skill test

**Steps**:

1. Run the init test:
   ```bash
   pytest tests/init/test_init_minimal_integration.py::test_init_creates_agents_skills_for_codex -v -s 2>&1
   ```

2. The test creates a fresh project and verifies that `spec-kitty.checklist` skill package is created. If it fails because the skill package doesn't exist in the skills registry:

   a. Check if the skill is defined anywhere in the source tree:
      ```bash
      find src/ -name '*checklist*' -o -name '*.skill*' 2>/dev/null | head -10
      ```

   b. If the skill exists in source but isn't registered: this is a code bug — fix the registration.

   c. If the skill doesn't exist at all and requires a separate mission's work: add a skip:
      ```python
      @pytest.mark.skip(reason="spec-kitty.checklist skill not yet implemented; unblocks after <issue/mission>")
      def test_init_creates_agents_skills_for_codex(...):
      ```

3. Document the skip with a link to the blocking issue if applicable.

**Files**: `tests/init/test_init_minimal_integration.py`

---

### T030 — Verify all WP05 target tests green

**Steps**:

```bash
pytest tests/cross_cutting/test_mypy_strict_mission_step_contracts.py \
       tests/missions/test_mission_switching_integration.py \
       tests/cli/commands/test_implement_base_flag.py \
       tests/cli/test_implement_bulk_edit_planning.py \
       tests/architectural/ \
       tests/init/test_init_minimal_integration.py::test_init_creates_agents_skills_for_codex \
       -v 2>&1
```

Expected: all tests pass (or `test_init_creates_agents_skills_for_codex` is explicitly skipped with a reason).

Then run a broader check:
```bash
pytest tests/missions/ tests/cli/ tests/architectural/ tests/cross_cutting/ tests/init/ -q
```

---

## Branch Strategy

**Planning base branch**: `main`
**Merge target**: `main`
**Execution**: Lane C worktree, after WP04 approved. Run `spec-kitty agent action implement WP05 --agent claude`.

---

## Definition of Done

- [ ] `mypy --strict src/specify_cli/mission_step_contracts/executor.py` exits 0
- [ ] `test_mission_switching_integration` × 2 pass
- [ ] `test_implement_base_flag` passes
- [ ] `test_implement_bulk_edit_planning` passes
- [ ] All architectural tests pass
- [ ] `test_init_creates_agents_skills_for_codex` either passes or is explicitly skipped with a documented reason
- [ ] `mypy --strict` passes on all modified modules
- [ ] No previously-passing test regresses

## Risks

- **mypy cascade**: Annotating `executor.py` may reveal that callers also need annotations. Limit changes to `executor.py`; use `# type: ignore[<code>]` at call sites in other modules rather than propagating annotation changes beyond owned_files.
- **Init skill external dep**: If the skill genuinely requires an unmerged WP, the skip is correct and acceptable.

## Reviewer Guidance

1. Confirm `mypy --strict` passes on `executor.py` with no suppressions beyond what was already there.
2. Confirm mission switching fix is in the correct location (prefer fixture over production if both work).
3. Confirm `--base` flag is threaded to the bulk-edit gate — not just accepted at the CLI level.
4. Confirm any `pytest.mark.skip` has a specific reason with an issue or mission reference.
