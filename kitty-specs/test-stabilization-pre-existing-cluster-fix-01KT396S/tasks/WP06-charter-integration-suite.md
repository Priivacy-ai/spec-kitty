---
work_package_id: WP06
title: Charter Integration Suite Stabilization
dependencies:
- WP02
requirement_refs:
- FR-008
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Execution worktree is allocated per lane from lanes.json. Implement on the lane-B worktree branch after WP02 is approved. Pull WP02 changes into the WP06 worktree before starting.
subtasks:
- T031
- T032
- T033
- T034
- T035
agent: claude
history:
- date: '2026-06-02'
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/charter_runtime/
execution_mode: code_change
owned_files:
- src/specify_cli/charter_runtime/**/*.py
- src/charter/**/*.py
- tests/charter/**/*.py
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

Stabilize the charter integration suite so all five sub-suites pass:
1. Charter linting over all layers
2. Synthesize error handling
3. Documentation runtime walk
4. Implement-review smoke tests
5. Specify-plan commit boundary tests

After this WP, `pytest tests/charter/` must be fully green.

**GitHub issue closed**: #1307
**Dependency**: WP02 must be approved first — some integration failures may be downstream of the synthesizer hash regression fixed in WP02.

---

## Context

The charter.py monolith (3328 lines) was split into a per-subcommand package (`src/charter/`) in WP06 of mission `test-stabilization-and-debt-pass-01KSF9HJ`. A `charter_runtime/` umbrella was added in WP08 with `sys.modules` shim re-exports to preserve legacy import paths. The integration tests that previously imported `charter.*` directly may now be hitting broken shim re-exports.

**Key structural files**:
- `src/specify_cli/charter_runtime/__init__.py` — the shim layer. Re-exports symbols from the split package.
- `src/charter/` — the split package. The actual implementations live here.
- Legacy import paths like `from charter.synthesizer import X` should still work via the shim.

**Before starting**: Pull WP02's approved changes into this worktree so the synthesizer fixes are included:
```bash
git merge kitty/mission-...-lane-b  # or rebase — per lane instructions
```

---

## Subtasks

### T031 — Run `pytest tests/charter/ -x` and capture first failure

**Steps**:

1. Ensure WP02 changes are present in this worktree (see Context above).

2. Run:
   ```bash
   pytest tests/charter/ -x --tb=short 2>&1 | head -80
   ```

3. The `-x` flag stops at the first failure. Record:
   - Test name and file
   - The exact import error or exception
   - The import path that fails (e.g., `from specify_cli.charter_runtime.lint import X`)

4. If the first failure is the same synthesizer hash failure that WP02 addressed — confirm WP02 changes are present and retry.

5. If the failure is a different import error, continue to T032.

**Output**: First non-WP02 failure with full import path and error message.

---

### T032 — Trace the failing import through the shim layer

**Steps**:

1. Open `src/specify_cli/charter_runtime/__init__.py`. Read all re-exports.

2. Trace the failing import from T031:
   - The test imports `from specify_cli.charter_runtime.X import Y` (or a variant).
   - The shim at `__init__.py` should re-export `Y` from `src/charter/X.py`.
   - If `Y` is not in the re-exports, it is a missing shim entry.

3. Also check sub-package shims:
   - `src/specify_cli/charter_runtime/lint/__init__.py`
   - `src/specify_cli/charter_runtime/freshness/__init__.py`
   - `src/specify_cli/charter_runtime/facade/__init__.py`

4. For each missing re-export, verify the symbol actually exists in the split package (`src/charter/`). If it was deleted in the split, the test may need to be updated to use the new import path.

**Files**:
- `src/specify_cli/charter_runtime/__init__.py`
- `src/specify_cli/charter_runtime/lint/__init__.py`
- `src/specify_cli/charter_runtime/freshness/__init__.py`
- `src/charter/` (to verify symbols exist)

**Output**: List of missing shim entries with their source module and target symbol.

---

### T033 — Repair missing shim re-exports

**Steps**:

For each missing re-export identified in T032:

1. Locate the symbol in `src/charter/`:
   ```bash
   grep -rn "def Y\|class Y\|^Y = " src/charter/ --include="*.py"
   ```

2. Add the re-export to the appropriate shim `__init__.py`:
   ```python
   # In src/specify_cli/charter_runtime/__init__.py or sub-package __init__
   from charter.X import Y  # noqa: F401  (re-export for legacy compat)
   ```

3. If the symbol was renamed or moved during the split, add both the old and new name:
   ```python
   from charter.new_module import NewName as OldName  # noqa: F401
   from charter.new_module import NewName  # noqa: F401
   ```

4. If the symbol was **deleted** (not just moved), the test that imports it is using a dead import — update the test to use the new API instead of adding a re-export for a non-existent symbol.

**Files**:
- `src/specify_cli/charter_runtime/__init__.py`
- Sub-package `__init__.py` files as needed

---

### T034 — Iterative fix: run and repair remaining shim gaps

**Steps**:

1. After T033, run the full suite again without `-x`:
   ```bash
   pytest tests/charter/ --tb=short -q 2>&1 | tail -40
   ```

2. For each remaining import error:
   - Apply T032 + T033 logic to find and fix the missing re-export.

3. Repeat until `pytest tests/charter/ -q` shows only non-import-error failures (actual test logic failures, not `ImportError` / `AttributeError` from missing shim entries).

4. For any remaining non-import failures:
   - Read the test carefully.
   - If the test is testing behavior that changed in the refactor, update the test to match the new behavior **only if the behavior change was intentional**.
   - Do not change test assertions to hide regressions.

5. Iterate until the full `tests/charter/` suite is green.

**Files**:
- `src/specify_cli/charter_runtime/` (shim files)
- `tests/charter/` (tests that may need import-path updates)

---

### T035 — Confirm all five charter sub-suites pass

**Steps**:

Run each sub-suite explicitly to confirm:

```bash
# 1. Charter linting
pytest tests/charter/ -k "lint" -v 2>&1 | tail -20

# 2. Synthesize error handling
pytest tests/charter/synthesizer/ -v 2>&1 | tail -20

# 3. Documentation runtime walk
pytest tests/charter/ -k "doc or runtime or walk" -v 2>&1 | tail -20

# 4. Implement-review smoke
pytest tests/charter/ -k "implement or review or smoke" -v 2>&1 | tail -20

# 5. Specify-plan commit boundary
pytest tests/charter/ -k "commit or boundary or specify or plan" -v 2>&1 | tail -20
```

Then run the full suite:
```bash
pytest tests/charter/ -q 2>&1
```

Expected: zero failures. If any remain, return to T034.

---

## Branch Strategy

**Planning base branch**: `main`
**Merge target**: `main`
**Execution**: Lane B worktree, after WP02 is in `approved` lane. Run `spec-kitty agent action implement WP06 --agent claude`.

**IMPORTANT**: Before implementing, verify WP02's changes are present in this worktree. The synthesizer fixes are a prerequisite for some integration tests to pass.

---

## Definition of Done

- [ ] `pytest tests/charter/ -q` passes with zero failures
- [ ] All five sub-suites (lint, synthesize error handling, doc walk, implement-review smoke, commit boundary) pass individually
- [ ] No previously-passing charter test regresses
- [ ] `mypy --strict` passes on all modified modules
- [ ] No test assertions were weakened to achieve a pass

## Risks

- **Multiple shim gaps**: There may be more than one broken re-export. The iterative approach (T034) handles this systematically.
- **Intentional deletions**: Some symbols deleted in the split may not need re-exporting — the test should be updated to use the new API. Distinguish between "shim gap" (symbol moved) and "dead import" (symbol deleted).
- **WP02 dependency**: If WP02 is not yet approved when WP06 begins, some failures may be confounding. Wait for WP02 approval.

## Reviewer Guidance

1. Confirm `pytest tests/charter/ -q` is fully green.
2. Confirm no test assertions were weakened.
3. Confirm shim re-exports use `# noqa: F401` comments (they are intentional re-exports, not unused imports).
4. Confirm WP02 changes were present in the worktree when WP06 was implemented (check git log).
