---
work_package_id: WP04
title: Dashboard read-only annotation path update
dependencies:
- WP03
requirement_refs:
- FR-006
- C-003
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
- T017
- T018
- T019
agent: claude
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/dashboard/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/dashboard/scanner.py
- src/specify_cli/dashboard/handlers/features.py
- tests/test_dashboard/test_scanner.py
- tests/test_dashboard/test_api_handler.py
role: implementer
tags: []
---

# Work Package Prompt: WP04 – Dashboard read-only annotation path update

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Update the dashboard's two source files to import `is_legacy_format` from `specify_cli.upgrade.legacy_detector` (the new path), remove the mutation-adjacent `use_legacy` branch from `_get_kanban_task_data_for_feature`, retain the read-only annotation paths in `_build_kanban_stats` and `_process_wp_file`, and fix all affected monkeypatch paths in the two dashboard test files.

## Context

WP03 deleted `src/specify_cli/legacy_detector.py`. The dashboard (`scanner.py` and `handlers/features.py`) still imports from the old path — those imports will now raise `ImportError`. This WP fixes the import paths and removes the one remaining mutation-adjacent branch while explicitly retaining the read-only annotation callers per FR-006 (Assumption 4 in the spec).

**Three categories of dashboard is_legacy_format usage** (from `research.md`):

| Location | Line(s) | Nature | Action |
|----------|---------|--------|--------|
| `scanner.py::_build_kanban_stats` | ~703 | Read-only routing signal | RETAIN (update import path only) |
| `scanner.py::_process_wp_file` | ~796 | Read-only annotation decision | RETAIN (update import path only) |
| `scanner.py::_get_kanban_task_data_for_feature` | ~855 | Mutation-adjacent: iterates lane subdirs to build task list | REMOVE the `use_legacy` iteration branch |
| `handlers/features.py::handle_features_list` | ~109 | Pure annotation: `feature["is_legacy"]` | RETAIN (update import path only) |
| `handlers/features.py::handle_kanban_request` | ~162 | Pure annotation | RETAIN (update import path only) |

**Test files affected**: Monkeypatch targets for `is_legacy_format` in test_scanner.py and test_api_handler.py will break because they patch the old import path. Update them to patch via the new module attribute (`scanner.is_legacy_format` after the import is updated) or directly via `specify_cli.upgrade.legacy_detector.is_legacy_format`.

---

### Subtask T015: Update scanner.py import and remove mutation branch

**Purpose**: Fix the broken import and remove the mutation-adjacent lane-iteration branch from `_get_kanban_task_data_for_feature` while retaining the read-only annotation signal callers.

**Steps**:
1. Open `src/specify_cli/dashboard/scanner.py`.

2. **Update import** (around line 16):
   ```python
   # OLD
   from specify_cli.legacy_detector import is_legacy_format
   # NEW
   from specify_cli.upgrade.legacy_detector import is_legacy_format
   ```

3. **Retain `_build_kanban_stats` call** (~line 703): This call uses `is_legacy_format` to route to `_build_legacy_kanban_stats` or `_build_event_log_kanban_stats`. This is a read-only routing signal — do NOT remove it. Verify it remains unchanged after the import update.

4. **Retain `_process_wp_file` call** (~line 796): Uses `is_legacy_format` to set `lane = default_lane` annotation vs. raising `CanonicalStatusNotFoundError`. Read-only — do NOT remove.

5. **Remove the `use_legacy` iteration branch in `_get_kanban_task_data_for_feature`** (~line 855): This branch iterates lane subdirectories (`tasks/planned/`, `tasks/doing/`, etc.) to build the task list. After WP03, the active runtime no longer supports lane-directory iteration. Replace the mutation-adjacent branch with a short-circuit annotation:
   ```python
   def _get_kanban_task_data_for_feature(feature_path: Path, ...) -> ...:
       if is_legacy_format(feature_path):
           # Pre-3.0 layout: return empty task list with annotation only.
           # The boundary guard prevents mutation commands from reaching this path;
           # dashboard read-only scans annotate the feature as legacy without iteration.
           return {"tasks": [], "is_legacy": True}
       # ... rest of flat-layout iteration (unchanged)
   ```
   Adjust the return type and structure to match whatever the function currently returns for the legacy case. The key is: no lane subdirectory traversal; `is_legacy: True` annotation preserved.

6. Run `ruff check src/specify_cli/dashboard/scanner.py` — zero issues.

**Files**: `src/specify_cli/dashboard/scanner.py` (modified)

**Validation**:
- `grep -n "legacy_detector" src/specify_cli/dashboard/scanner.py` shows only `upgrade.legacy_detector` (no old path).
- `grep -n "use_legacy\|lane_dirs\|tasks/planned\|tasks/doing" src/specify_cli/dashboard/scanner.py` returns zero output (lane-dir iteration gone).
- `ruff check` passes.

---

### Subtask T016: Update handlers/features.py import

**Purpose**: Fix the broken import in `handlers/features.py`. The annotation callers (`feature["is_legacy"]`) are retained without change.

**Steps**:
1. Open `src/specify_cli/dashboard/handlers/features.py`.

2. **Update import** (around line 30):
   ```python
   # OLD
   from specify_cli.legacy_detector import is_legacy_format
   # NEW
   from specify_cli.upgrade.legacy_detector import is_legacy_format
   ```

3. **Verify annotation callers remain unchanged**:
   - `handle_features_list` (~line 109): sets `feature["is_legacy"] = is_legacy_format(...)` — RETAIN.
   - `handle_kanban_request` (~line 162): same annotation pattern — RETAIN.
   Both calls are pure read-only feature metadata — no mutation path through them.

4. Run `ruff check src/specify_cli/dashboard/handlers/features.py` — zero issues.

**Files**: `src/specify_cli/dashboard/handlers/features.py` (modified)

**Validation**:
- `grep -n "legacy_detector" src/specify_cli/dashboard/handlers/features.py` shows only `upgrade.legacy_detector`.
- `ruff check` passes.

---

### Subtask T017: Update monkeypatch targets in test_scanner.py

**Purpose**: Fix test_scanner.py tests that monkeypatch `is_legacy_format` via the old import path.

**Steps**:
1. Open `tests/test_dashboard/test_scanner.py`.
2. Search for all monkeypatch/patch usages of `is_legacy_format`:
   ```bash
   grep -n "is_legacy_format\|legacy_detector" tests/test_dashboard/test_scanner.py
   ```
3. For each `monkeypatch.setattr(scanner, "is_legacy_format", ...)` (or similar) hit, update to patch via the module attribute that `scanner.py` now uses:
   - If the test patches `scanner.is_legacy_format` (the attribute on the scanner module), this **already works** after the import update — the module attribute is still `is_legacy_format`. No change needed for this form.
   - If the test patches `"specify_cli.legacy_detector.is_legacy_format"` as the dotted path, update to `"specify_cli.upgrade.legacy_detector.is_legacy_format"`.
   - If the test patches `"specify_cli.dashboard.scanner.is_legacy_format"`, this form patches the name in the scanner module's namespace and continues to work after the import update. No change needed.
4. Specifically update:
   - `test_build_kanban_stats_handles_absent_and_legacy_paths`
   - `test_process_wp_file_raises_without_canonical_log_for_nonlegacy`
5. Run `pytest tests/test_dashboard/test_scanner.py -v --tb=short` — all tests must pass.

**Files**: `tests/test_dashboard/test_scanner.py` (modified)

**Validation**: `pytest tests/test_dashboard/test_scanner.py -v` — all pass, zero failures.

---

### Subtask T018: Update patch paths in test_api_handler.py

**Purpose**: Fix test_api_handler.py — 3 occurrences of patching `is_legacy_format` via the old path.

**Steps**:
1. Open `tests/test_dashboard/test_api_handler.py`.
2. Search:
   ```bash
   grep -n "is_legacy_format\|legacy_detector" tests/test_dashboard/test_api_handler.py
   ```
   There are 3 occurrences (per `research.md`).
3. For each occurrence, determine the patch form used:
   - `patch.object(features_module, "is_legacy_format", ...)`: patches the attribute on the imported `features.py` module object. This continues to work after the import update in features.py, since the attribute name `is_legacy_format` is unchanged. Verify the test still passes without touching it.
   - `patch("specify_cli.legacy_detector.is_legacy_format", ...)`: Update to `patch("specify_cli.upgrade.legacy_detector.is_legacy_format", ...)`.
   - `patch("specify_cli.dashboard.handlers.features.is_legacy_format", ...)`: This patches the attribute in the features module namespace and continues to work. No change needed.
4. Apply changes and run `pytest tests/test_dashboard/test_api_handler.py -v --tb=short` — all pass.

**Files**: `tests/test_dashboard/test_api_handler.py` (modified)

**Validation**: `pytest tests/test_dashboard/test_api_handler.py -v` — all pass, zero failures.

---

### Subtask T019: Full dashboard test suite and quality gate

**Purpose**: Confirm the entire dashboard test suite passes after all import and patch-path updates.

**Steps**:
1. Run:
   ```bash
   pytest tests/test_dashboard/ -v --tb=short
   ```
   All tests must pass.
2. Run quality gate:
   ```bash
   ruff check src/specify_cli/dashboard/scanner.py src/specify_cli/dashboard/handlers/features.py
   mypy src/specify_cli/dashboard/scanner.py src/specify_cli/dashboard/handlers/features.py
   ```
   Zero issues.

**Files**: No new files; quality and regression checks.

**Validation**: `pytest tests/test_dashboard/` — all pass. `ruff` + `mypy` clean.

---

## Definition of Done

- [ ] `scanner.py` imports `is_legacy_format` from `specify_cli.upgrade.legacy_detector`.
- [ ] `handlers/features.py` imports `is_legacy_format` from `specify_cli.upgrade.legacy_detector`.
- [ ] `_get_kanban_task_data_for_feature` no longer iterates lane subdirectories; returns `{"tasks": [], "is_legacy": True}` for pre-3.0 layout.
- [ ] `_build_kanban_stats` and `_process_wp_file` read-only annotation calls retained unchanged.
- [ ] `handle_features_list` and `handle_kanban_request` `feature["is_legacy"]` annotation retained unchanged.
- [ ] All monkeypatch/patch paths in test_scanner.py and test_api_handler.py updated or verified correct.
- [ ] `pytest tests/test_dashboard/` — all pass.
- [ ] `ruff` + `mypy` clean on `scanner.py` and `handlers/features.py`.
- [ ] No import from the old `specify_cli.legacy_detector` path in any dashboard file.

## Risks

- **`_get_kanban_task_data_for_feature` return type**: The function's return type and callers must accept `{"tasks": [], "is_legacy": True}` — check the call sites and type annotations before cutting the branch.
- **`patch.object` vs. dotted-path patching**: `patch.object(features_module, "is_legacy_format", ...)` patches the attribute in the module namespace and survives import path changes. `patch("specify_cli.legacy_detector.is_legacy_format", ...)` patches the original module and will fail if callers import from the new path. Identify which form each test uses before deciding what to change.

## Reviewer Guidance

- Verify `grep -rn "specify_cli.legacy_detector" src/specify_cli/dashboard/` returns zero output (only `upgrade.legacy_detector` references remain).
- Verify `_build_kanban_stats` and `_process_wp_file` calls are unchanged (diff).
- Confirm `_get_kanban_task_data_for_feature` no longer imports or iterates lane directories.
- Run `pytest tests/test_dashboard/ -v` manually and confirm all green.

---

To implement: `spec-kitty agent action implement WP04 --agent claude`
