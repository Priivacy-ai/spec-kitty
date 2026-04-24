---
work_package_id: WP01
title: Register src/runtime in pyproject.toml
dependencies: []
requirement_refs:
- FR-001
- FR-002
planning_base_branch: kitty/mission-runtime-mission-execution-extraction-01KPDYGW
merge_target_branch: kitty/mission-runtime-mission-execution-extraction-01KPDYGW
branch_strategy: Planning artifacts for this feature were generated on kitty/mission-runtime-mission-execution-extraction-01KPDYGW. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-runtime-mission-execution-extraction-01KPDYGW unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-runtime-extraction-remediation-01KPX9DT
base_commit: a7c276d228d7789e0c0e68cfd06e93c9a0c4dabb
created_at: '2026-04-23T14:29:13.699883+00:00'
subtasks:
- T001
- T002
- T003
agent: "claude:claude-sonnet-4-6:python-pedro:reviewer"
shell_pid: "1131467"
history:
- date: '2026-04-23T13:58:27Z'
  author: reviewer-renata
  event: created
agent_profile: python-pedro
authoritative_surface: pyproject.toml
execution_mode: code_change
lane: planned
owned_files:
- pyproject.toml
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading further, load the assigned agent profile for this session:

```
/ad-hoc-profile-load python-pedro
```

Do not begin implementation until the profile is active.

---

## Objective

Register `src/runtime` in `pyproject.toml`'s `packages` list so the `runtime` package is included in wheel builds and is importable in all install modes (editable, non-editable, PyPI). This is the **critical blocking finding** (DRIFT-1) preventing mission #95 from merging to `main`.

**Why this is broken**: The `src/runtime/` package was created by mission #95 but never added to the `packages` list in `pyproject.toml`. As a result, `import runtime` fails with `ModuleNotFoundError` in any installed environment where `src/` is not explicitly on `sys.path`. Pytest currently adds `src/` to `sys.path` automatically, masking the problem during development.

---

## Context

- **File to change**: `pyproject.toml` — one line addition
- **Constraint C-001**: Do NOT modify the `version` field. Only the `packages` list changes.
- **Current packages list** (confirmed from live code):
  ```toml
  packages = ["src/kernel", "src/specify_cli", "src/doctrine", "src/charter"]
  ```
- **Target**:
  ```toml
  packages = ["src/kernel", "src/specify_cli", "src/doctrine", "src/charter", "src/runtime"]
  ```

---

## Subtask T001 — Add `"src/runtime"` to `packages` list

**Purpose**: Make the `runtime` package part of the wheel distribution so `import runtime` works for all users.

**Steps**:

1. Read `pyproject.toml` to find the exact location of the `packages` list. It is under `[tool.hatch.build.targets.wheel]` (or similar hatchling section).

2. Add `"src/runtime"` as the last entry in the `packages` list, preserving the existing format:
   ```toml
   packages = [
     "src/kernel",
     "src/specify_cli",
     "src/doctrine",
     "src/charter",
     "src/runtime"
   ]
   ```
   If the list is single-line, keep it single-line:
   ```toml
   packages = ["src/kernel", "src/specify_cli", "src/doctrine", "src/charter", "src/runtime"]
   ```

3. Verify no other field in `pyproject.toml` was accidentally modified (especially `version`):
   ```bash
   git diff pyproject.toml
   ```
   The diff must show only the `packages` line change.

**Files touched**: `pyproject.toml`

**Validation**: `git diff pyproject.toml` shows exactly one changed line (the `packages` entry). `version` is unchanged.

---

## Subtask T002 — Verify the package is importable

**Purpose**: Confirm that adding the entry to `pyproject.toml` makes `runtime` importable through the normal package installation path.

**Steps**:

1. Run a direct import test (works because the editable install respects `pyproject.toml`):
   ```bash
   python -c "from runtime import PresentationSink, StepContractExecutor, ProfileInvocationExecutor; print('OK')"
   ```
   Expected: prints `OK`, exits 0.

2. Also verify the seams subpackage is accessible:
   ```bash
   python -c "from runtime.seams.presentation_sink import PresentationSink; from runtime.seams._null_sink import NullSink; assert isinstance(NullSink(), PresentationSink); print('seams OK')"
   ```

3. Verify the discovery and orchestration subpackages are accessible:
   ```bash
   python -c "from runtime.discovery import get_kittify_home, resolve_mission; from runtime.orchestration import ensure_runtime; print('subpackages OK')"
   ```

4. **Non-editable install check** (I2 fix): The editable install above confirms the path registration works. To verify the non-editable case is also satisfied (FR-002), run:
   ```bash
   pip install --no-deps -e . --quiet 2>&1 | tail -3
   python -c "import runtime; print(runtime.__file__)"
   ```
   The `__file__` path should point inside `src/runtime/`, not a `.egg-link`. If it does, the package is properly discoverable. Full non-editable (`pip install --no-editable`) testing is deferred to release CI per spec Assumption A2.

**Validation**: All three import commands exit 0. `runtime.__file__` resolves correctly.

---

## Subtask T003 — Run full test suite + CLI smoke tests

**Purpose**: Confirm the `pyproject.toml` change introduces no regressions, and verify CLI entry points still function (NFR-004).

**Steps**:

0. **Capture baseline test count BEFORE the change** (U1 fix — do this before T001, not after):
   ```bash
   git stash && pytest tests/ --ignore=tests/auth -q --tb=no 2>&1 | tail -1 && git stash pop
   ```
   Record the number (e.g., "13026 passed"). This is the NFR-002 baseline.

1. Run CLI smoke tests to verify NFR-004 (C1 fix):
   ```bash
   spec-kitty --version
   spec-kitty next --help
   spec-kitty merge --help
   ```
   All three must exit 0 and print expected output.

2. Run the full test suite:
   ```bash
   pytest tests/ --ignore=tests/auth -q --tb=short 2>&1 | tail -10
   ```
   Count must be ≥ baseline captured in step 0.

3. Verify the architectural boundary tests still pass:
   ```bash
   pytest tests/architectural/ -v -q 2>&1 | tail -5
   ```
   Expected: 12 passed.

4. **Scope guard** (C2 fix): Confirm C-003 and C-004 — no changes to `src/runtime/` or shim directories:
   ```bash
   git diff HEAD -- src/runtime/ src/specify_cli/next/ src/specify_cli/runtime/
   ```
   Expected: empty output (no diff).

**Validation**: CLI smoke tests pass. Full suite passes with count ≥ baseline. Architectural tests: 12 passed. Scope guard returns empty diff.

---

## Branch Strategy

Work in the execution worktree allocated by `spec-kitty agent action implement WP01 --agent claude`.

- **Planning branch**: `kitty/mission-runtime-mission-execution-extraction-01KPDYGW`
- **Merge target**: `kitty/mission-runtime-mission-execution-extraction-01KPDYGW`

---

## After Implementation

```bash
git add pyproject.toml
git commit -m "fix(DRIFT-1): register src/runtime in pyproject.toml packages list

Adds 'src/runtime' to the hatchling packages list so the runtime package
is included in wheel builds and importable in all install modes.

Fixes DRIFT-1 from post-merge review of mission-095
(runtime-mission-execution-extraction-01KPDYGW).
Unblocks merge to main.

Tests: N passed, 0 new failures"

spec-kitty agent tasks mark-status T001 T002 T003 --status done --mission runtime-extraction-remediation-01KPX9DT

spec-kitty agent tasks move-task WP01 --to for_review --mission runtime-extraction-remediation-01KPX9DT --note "pyproject.toml updated; all imports verified; test suite stable"
```

---

## Definition of Done

- [ ] `pyproject.toml` `packages` list includes `"src/runtime"`
- [ ] `version` field is unchanged
- [ ] `from runtime import PresentationSink, StepContractExecutor, ProfileInvocationExecutor` exits 0
- [ ] `from runtime.discovery import get_kittify_home` exits 0
- [ ] `spec-kitty --version` and `spec-kitty next --help` exit 0 (NFR-004)
- [ ] Full test suite passes with count ≥ pre-WP01 baseline (NFR-002)
- [ ] `pytest tests/architectural/ -q` shows 12 passed
- [ ] `git diff HEAD -- src/runtime/ src/specify_cli/next/ src/specify_cli/runtime/` is empty (C-003/C-004)

---

## Reviewer Guidance

- `git diff pyproject.toml` must show exactly the `packages` entry addition — nothing else
- `version` must be identical to the pre-change state
- Confirm all three import-verification commands in T002 pass
- Record the test count and confirm it matches pre-WP baseline

## Activity Log

- 2026-04-23T14:33:31Z – claude – shell_pid=1099573 – pyproject.toml updated with src/runtime; all imports verified (top-level, seams, discovery, orchestration); CLI smoke tests pass; scope guard clean
- 2026-04-23T14:48:17Z – claude:claude-sonnet-4-6:python-pedro:reviewer – shell_pid=1131467 – Started review via action command
- 2026-04-23T14:48:57Z – claude:claude-sonnet-4-6:python-pedro:reviewer – shell_pid=1131467 – Approved: single-line change to pyproject.toml, version unchanged, all imports verified, no scope creep
