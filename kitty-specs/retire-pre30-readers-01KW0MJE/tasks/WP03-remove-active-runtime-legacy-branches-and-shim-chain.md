---
work_package_id: WP03
title: Remove active runtime legacy branches and shim chain
dependencies:
- WP02
requirement_refs:
- FR-003
- FR-004
- FR-007
- FR-008
- FR-009
- C-001
- C-003
- C-004
- NFR-001
- NFR-002
- NFR-005
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T008
- T009
- T010
- T011
- T012
- T013
- T014
agent: claude
shell_pid: '1213525'
history: []
agent_profile: randy-reducer
authoritative_surface: src/specify_cli/task_utils/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/task_utils/support.py
- src/specify_cli/task_utils/__init__.py
- src/specify_cli/tasks_support.py
- src/specify_cli/scripts/tasks/task_helpers.py
- src/specify_cli/acceptance/__init__.py
- src/specify_cli/legacy_detector.py
role: implementer
tags: []
---

# Work Package Prompt: WP03 – Remove active runtime legacy branches and shim chain

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `randy-reducer`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Remove all `is_legacy_format`/`use_legacy` branches from the active runtime's core functions (`locate_work_package`, `_iter_work_packages`), cut the four-link shim re-export chain, and delete the now-orphaned `src/specify_cli/legacy_detector.py`. Every deletion is preceded by a zero-caller grep verification (C-001 / NFR-001).

## Context

The boundary guard (WP02) now fires before any pre-3.0 project reaches `locate_work_package` or `_iter_work_packages`. That makes the `use_legacy` branches in these functions dead code. This WP does the cleanup:

- **Shim chain** (four links): `legacy_detector.py` → `task_utils/support.py` → `task_utils/__init__.py` / `tasks_support.py` / `task_helpers.py`. The chain is severed by removing `is_legacy_format` from each link's `__all__` and re-export.
- **`locate_work_package`** (`task_utils/support.py`): Remove the `use_legacy` branch (lines ~320–336) that searched lane subdirectories. Post-WP03, the function only handles flat `tasks/WP*.md`.
- **`acceptance/__init__.py::_iter_work_packages`**: Remove the `use_legacy` branch; add a pre-3.0 shape detection skip with a clear log entry (FR-007).
- **`src/specify_cli/legacy_detector.py`**: Delete after confirming zero active-runtime importers remain.

**Pre-condition**: WP02 must be complete (guard wired) before this WP runs. The safety net for removing `use_legacy` branches is the guard — without it, removing these branches would silently break pre-3.0 projects.

**Hard constraint (C-004 / NFR-005)**: Do NOT touch `status/store.py`, `status/reducer.py`, `upgrade/migrations/m_0_9_0_frontmatter_only_lanes.py`, `upgrade/runner.py`, or `upgrade/registry.py`. The upgrade migration's private `_is_legacy_format` is self-contained and must not be changed.

**Deletion safety (C-001 / NFR-001)**: Before deleting any symbol or file, run the grep audit command listed in each subtask and confirm zero callers in `src/`.

---

### Subtask T008: Remove use_legacy branch from task_utils/support.py::locate_work_package

**Purpose**: Make `locate_work_package` flat-layout-only. The boundary guard (WP02) now prevents pre-3.0 projects from reaching this function.

**Steps**:
1. Open `src/specify_cli/task_utils/support.py`.
2. **Grep pre-check**:
   ```bash
   grep -n "is_legacy_format\|use_legacy" src/specify_cli/task_utils/support.py
   ```
   Note the line numbers for the import and the branch.
3. **Remove the import** (around line 14):
   ```python
   from specify_cli.legacy_detector import is_legacy_format
   ```
   Delete this line entirely.
4. **Remove the `use_legacy` branch** in `locate_work_package` (around lines 320–336): Delete the `use_legacy = is_legacy_format(feature_path)` assignment and the entire `if use_legacy:` block that iterates lane subdirectories. The function continues with its flat-layout logic only.
5. If `is_legacy_format` also appears in `__all__` of this file, remove it.
6. Run `ruff check src/specify_cli/task_utils/support.py` — zero issues.
7. Post-check:
   ```bash
   grep -n "is_legacy_format\|use_legacy\|legacy_detector" src/specify_cli/task_utils/support.py
   ```
   Must return zero output.

**Files**: `src/specify_cli/task_utils/support.py` (modified)

**Validation**: Grep post-check returns zero output. `ruff check` passes.

---

### Subtask T009: Remove is_legacy_format from task_utils/__init__.py

**Purpose**: Sever link 2 of the shim chain — `task_utils/__init__.py` re-exports `is_legacy_format` with zero external callers.

**Steps**:
1. Open `src/specify_cli/task_utils/__init__.py`.
2. **Zero-caller pre-check**:
   ```bash
   grep -rn "from specify_cli.task_utils import is_legacy_format\|task_utils.is_legacy_format" src/ tests/
   ```
   Must return zero output (confirms no active caller uses this re-export path).
3. Remove the re-export line (around line 21) that imports `is_legacy_format` from `support`.
4. Remove `"is_legacy_format"` from `__all__` (around line 47) if present.
5. Run `ruff check src/specify_cli/task_utils/__init__.py` — zero issues.

**Files**: `src/specify_cli/task_utils/__init__.py` (modified)

**Validation**: `grep -n "is_legacy_format" src/specify_cli/task_utils/__init__.py` returns zero output.

---

### Subtask T010: Remove is_legacy_format re-export from tasks_support.py

**Purpose**: Sever link 3 of the shim chain — `tasks_support.py` backward-compat re-export.

**Steps**:
1. Open `src/specify_cli/tasks_support.py`.
2. **Zero-caller pre-check**:
   ```bash
   grep -rn "from specify_cli.tasks_support import is_legacy_format\|tasks_support.is_legacy_format" src/ tests/
   ```
   Must return zero output.
3. Remove the re-export line (around line 22).
4. Run `ruff check src/specify_cli/tasks_support.py` — zero issues.

**Files**: `src/specify_cli/tasks_support.py` (modified)

**Validation**: `grep -n "is_legacy_format" src/specify_cli/tasks_support.py` returns zero output.

---

### Subtask T011: Remove is_legacy_format from task_helpers.py __all__ and re-export

**Purpose**: Sever link 4 of the shim chain — `scripts/tasks/task_helpers.py` re-export and `__all__` entry. The dead-symbol allowlist entry in `test_no_dead_symbols.py` is updated in WP05.

**Steps**:
1. Open `src/specify_cli/scripts/tasks/task_helpers.py`.
2. **Zero-caller pre-check**:
   ```bash
   grep -rn "from specify_cli.scripts.tasks.task_helpers import is_legacy_format\|task_helpers.is_legacy_format" src/ tests/
   ```
   Monkeypatch usages in tests are expected — note them (they will be updated in WP05). There must be zero non-test callers.
3. Remove the re-export line (around line 34).
4. Remove `"is_legacy_format"` from `__all__` (around line 58).
5. Run `ruff check src/specify_cli/scripts/tasks/task_helpers.py` — zero issues.

**Files**: `src/specify_cli/scripts/tasks/task_helpers.py` (modified)

**Validation**:
- `grep -n "is_legacy_format" src/specify_cli/scripts/tasks/task_helpers.py` returns zero output.
- `ruff check` passes.

---

### Subtask T012: Remove use_legacy branch from acceptance/__init__.py::_iter_work_packages

**Purpose**: Make `_iter_work_packages` skip pre-3.0 missions with a clear log entry instead of silently normalizing them through the legacy lane iteration path (FR-007).

**Steps**:
1. Open `src/specify_cli/acceptance/__init__.py`.
2. **Grep pre-check**:
   ```bash
   grep -n "is_legacy_format\|use_legacy\|legacy_detector" src/specify_cli/acceptance/__init__.py
   ```
   Note the import line (around line 36) and the branch site (around line 411).
3. **Remove the import** of `is_legacy_format` (from `specify_cli.task_utils` or wherever it is imported from).
4. **Replace the `use_legacy` branch** in `_iter_work_packages` with a pre-3.0 skip:
   ```python
   # Check for pre-3.0 lane-directory layout and skip if detected
   from specify_cli.upgrade.legacy_detector import is_legacy_format as _is_legacy
   if _is_legacy(feature_path):
       import logging
       logging.getLogger(__name__).warning(
           "Skipping pre-3.0 mission %s: run `spec-kitty upgrade` to migrate before acceptance scan.",
           feature_path.name,
       )
       return
   ```
   Place this check at the top of `_iter_work_packages` (before any lane subdirectory iteration). The function then proceeds with flat-layout-only logic.

   **Note**: Import `is_legacy_format` from `specify_cli.upgrade.legacy_detector` (the relocated path), not from the old `specify_cli.legacy_detector`. Prefer a module-level import (not inline) if the function is called in a tight loop — but given this is an acceptance scan, inline is acceptable for clarity.

5. Remove the old `use_legacy` iteration block (lane subdirectory traversal).
6. Run `ruff check src/specify_cli/acceptance/__init__.py` and `mypy src/specify_cli/acceptance/__init__.py` — zero issues.

**Files**: `src/specify_cli/acceptance/__init__.py` (modified)

**Validation**:
- `grep -n "legacy_detector\|use_legacy" src/specify_cli/acceptance/__init__.py` — only shows the new `upgrade.legacy_detector` import and the `_is_legacy` call; no old `specify_cli.legacy_detector` import.
- `ruff` + `mypy` pass.

---

### Subtask T013: Final zero-caller audit then delete src/specify_cli/legacy_detector.py

**Purpose**: Confirm no active-runtime code remains that imports from `specify_cli.legacy_detector` (the old path), then delete the file to complete the relocation (FR-003, C-001, NFR-001).

**Steps**:
1. **Comprehensive zero-caller audit**:
   ```bash
   grep -rn "from specify_cli.legacy_detector\|import specify_cli.legacy_detector\|specify_cli.legacy_detector" src/ tests/
   ```
   Expected output: **zero lines** (all callers have been removed in T008–T012 and WP02, or were redirected to `specify_cli.upgrade.legacy_detector` in WP04 for dashboard). If any hits remain, fix them before proceeding.

2. **Verify upgrade namespace is intact**:
   ```bash
   python3 -c "from specify_cli.upgrade.legacy_detector import is_legacy_format, get_legacy_lane_counts, LEGACY_LANE_DIRS; print('upgrade path OK')"
   ```
   Must print `upgrade path OK`.

3. **Delete the original file**:
   ```bash
   rm src/specify_cli/legacy_detector.py
   ```

4. **Verify no import errors** after deletion:
   ```bash
   python3 -c "import specify_cli; print('package import OK')"
   python3 -c "from specify_cli.upgrade.legacy_detector import is_legacy_format; print('upgrade import OK')"
   ```

**Files**: `src/specify_cli/legacy_detector.py` (DELETED)

**Validation**: Both `python3` import checks pass. Grep audit returns zero output.

---

### Subtask T014: Full regression run on upgrade and task-utils tests

**Purpose**: Confirm NFR-002 (upgrade test suite unchanged) and that `locate_work_package` works correctly post-branch-removal.

**Steps**:
1. Run upgrade tests:
   ```bash
   pytest tests/upgrade/ -v --tb=short
   ```
   All must pass with zero failures. The guard tests added in WP01 should remain green.

2. Run task_utils tests:
   ```bash
   pytest tests/ -k "task_utils or support or locate_work_package" -v --tb=short
   ```

3. Run acceptance tests:
   ```bash
   pytest tests/ -k "acceptance" -v --tb=short
   ```

4. If any test creates a pre-3.0 fixture and exercises `locate_work_package` directly (bypassing the command boundary), it may now fail because the legacy branch is gone. Note these failures for WP05 without fixing them here.

5. Run ruff + mypy over all modified files in this WP:
   ```bash
   ruff check src/specify_cli/task_utils/ src/specify_cli/tasks_support.py src/specify_cli/scripts/tasks/task_helpers.py src/specify_cli/acceptance/__init__.py
   mypy src/specify_cli/task_utils/ src/specify_cli/tasks_support.py src/specify_cli/scripts/tasks/task_helpers.py src/specify_cli/acceptance/__init__.py
   ```

**Files**: No new files; regression test execution.

**Validation**: All upgrade tests green. `ruff` + `mypy` clean on all modified files.

---

## Definition of Done

- [ ] `is_legacy_format` import and `use_legacy` branch removed from `task_utils/support.py::locate_work_package`.
- [ ] `is_legacy_format` removed from `task_utils/__init__.py` re-export and `__all__`.
- [ ] `is_legacy_format` removed from `tasks_support.py` re-export.
- [ ] `is_legacy_format` removed from `task_helpers.py` re-export and `__all__`.
- [ ] `acceptance/__init__.py::_iter_work_packages` pre-3.0 `use_legacy` branch replaced with skip + log (imports from `specify_cli.upgrade.legacy_detector`).
- [ ] Zero-caller grep audit on `specify_cli.legacy_detector` (old path) returns zero hits in `src/` and `tests/`.
- [ ] `src/specify_cli/legacy_detector.py` deleted.
- [ ] `from specify_cli.upgrade.legacy_detector import is_legacy_format` imports 0K.
- [ ] Upgrade tests all pass (NFR-002).
- [ ] `ruff` + `mypy` clean on all touched files.
- [ ] Off-limits files untouched: `status/store.py`, `status/reducer.py`, `m_0_9_0_frontmatter_only_lanes.py`, `runner.py`, `registry.py` (C-004, FR-009).

## Risks

- **Partial shim chain**: If any link in the four-link chain is missed, importing `is_legacy_format` from the old path will raise `ImportError` rather than silently succeeding. The zero-caller audit (T013) catches this.
- **`acceptance` broad use**: `_iter_work_packages` is called from `collect_feature_summary` which is called from the orchestrator API (~line 1498). The pre-3.0 skip must log clearly — the orchestrator API will see "skipped" missions in its output for unmigrated projects. This is acceptable behavior per FR-007.
- **Function signature**: Do not change the signature of `locate_work_package` or `_iter_work_packages` — callers must not be updated.

## Reviewer Guidance

- Verify the zero-caller grep audit (T013 output) is clean before the delete.
- Confirm `acceptance/__init__.py` imports from `specify_cli.upgrade.legacy_detector` (new path), not the old path.
- Confirm off-limits files are untouched (diff check against `status/`, `upgrade/migrations/`).
- Run `pytest tests/upgrade/ -v` and confirm zero regressions.

---

To implement: `spec-kitty agent action implement WP03 --agent claude`
