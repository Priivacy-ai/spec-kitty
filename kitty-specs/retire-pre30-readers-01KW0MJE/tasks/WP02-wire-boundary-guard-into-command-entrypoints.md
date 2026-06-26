---
work_package_id: WP02
title: Wire boundary guard into command entrypoints
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-002
- FR-005
- C-002
- NFR-006
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
agent: claude
shell_pid: '1028678'
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/scripts/tasks/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/scripts/tasks/tasks_cli.py
- src/specify_cli/cli/commands/agent/tasks.py
role: implementer
tags: []
---

# Work Package Prompt: WP02 – Wire boundary guard into command entrypoints

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Wire `check_pre30_layout` from `specify_cli.upgrade.pre30_guard` into all mutation command entry points in `tasks_cli.py` and `agent/tasks.py`, and remove the now-superseded `_check_legacy_format` warning helper and `list_command` legacy iteration branch from `tasks_cli.py`.

## Context

WP01 created the guard module and tests. This WP makes the guard live by inserting it at the command boundary in the two main task command layers:

1. **`src/specify_cli/scripts/tasks/tasks_cli.py`** (the standalone scripts layer) — currently has a `_check_legacy_format` helper that only warns (does not exit). This warning path is replaced with the hard-reject `check_pre30_layout` call. The `list_command` also has a legacy iteration branch that must be removed once the guard fires before the list body is reached.

2. **`src/specify_cli/cli/commands/agent/tasks.py`** (the typer CLI layer, ~4500 LOC god-module) — add `check_pre30_layout` call in each `@app.command` mutation entry after `feature_path` is resolved, before any `locate_work_package` or `emit_status_transition` call.

**Guard trigger point** (from `contracts/pre30-guard-contract.md`): After `feature_path = resolve_feature_dir_for_mission(...)` (or equivalent), before any WP file is read or event emitted. The guard must NOT fire before mission resolution (to preserve the normal "no kitty-specs found" error path — Scenario A exception case).

**WP03 dependency**: WP03 removes the `use_legacy` branch from `locate_work_package` and the shim chain. This WP only wires the guard — WP03 cleans up what the guard makes dead code.

**Off-limits**: Do not modify `status/store.py`, `status/reducer.py`, or any upgrade migration files (C-004, FR-009).

---

### Subtask T005: Replace _check_legacy_format with check_pre30_layout in tasks_cli.py

**Purpose**: Eliminate the warning-only `_check_legacy_format` helper and replace all its call sites with `check_pre30_layout`, which hard-rejects (exit 1) instead of warning. Also remove the `list_command` legacy iteration branch.

**Steps**:
1. Open `src/specify_cli/scripts/tasks/tasks_cli.py`.

2. **Add import** near the top (after existing imports):
   ```python
   from specify_cli.upgrade.pre30_guard import Pre30LayoutError, check_pre30_layout
   ```

3. **Remove `_check_legacy_format`** (around lines 212–247): Delete the entire function. It currently calls `is_legacy_format` and prints a warning to stderr. Do not preserve the warning — the hard-reject replaces it entirely.

4. **Find every call to `_check_legacy_format`** (there are 2: one in `update_command` ~line 250, one in `list_command` ~line 327). For each call site, replace the pattern:
   ```python
   # OLD (warning-only)
   _check_legacy_format(feature_path, ...)

   # NEW (hard-reject)
   try:
       check_pre30_layout(feature_path)
   except Pre30LayoutError as e:
       print(str(e), file=sys.stderr)
       sys.exit(1)
   ```
   Ensure this replacement appears **after** `feature_path` is resolved but **before** any WP mutation call in the function.

5. **Remove the `list_command` legacy iteration branch** (around lines 325–355): This block iterates lane subdirectories (`tasks/planned/`, etc.) when `use_legacy` is True. After the guard fires at the command boundary, a pre-3.0 project never reaches this code. Delete the entire `use_legacy` branch. The `list_command` should only iterate flat `tasks/WP*.md` files after this change.

6. Remove the now-unused `is_legacy_format` import that was added via `task_helpers` (if it is still in the import block after step 3). Check that `use_legacy` variable references are gone.

7. Run `ruff check src/specify_cli/scripts/tasks/tasks_cli.py` and resolve all issues.

**Files**: `src/specify_cli/scripts/tasks/tasks_cli.py` (modified)

**Validation**:
- `ruff check src/specify_cli/scripts/tasks/tasks_cli.py` — zero issues.
- `grep -n "_check_legacy_format\|use_legacy" src/specify_cli/scripts/tasks/tasks_cli.py` — no output.
- `grep -n "check_pre30_layout" src/specify_cli/scripts/tasks/tasks_cli.py` — shows at least 2 call sites.

---

### Subtask T006: Wire check_pre30_layout into agent/tasks.py mutation commands

**Purpose**: Add the boundary guard to the typer CLI layer so all `spec-kitty agent tasks …` mutation commands hard-reject pre-3.0 projects before any WP is loaded or any event is emitted.

**Steps**:
1. Open `src/specify_cli/cli/commands/agent/tasks.py`. This is a large (~4500 LOC) module; search precisely rather than reading in full.

2. **Add import** at the top of the import block:
   ```python
   from specify_cli.upgrade.pre30_guard import Pre30LayoutError, check_pre30_layout
   ```

3. **Identify mutation commands**: Using `grep -n "@app.command\|feature_path\|locate_work_package\|emit_status_transition" src/specify_cli/cli/commands/agent/tasks.py`, identify each `@app.command` function that calls `locate_work_package(...)` or `emit_status_transition(...)`. These are the mutation entry points.

4. **For each mutation command**, find the line where `feature_path` (or `feature_dir`) is resolved (typically via `resolve_feature_dir_for_mission(repo_root, mission_slug)` or equivalent). Insert the guard call immediately after:
   ```python
   feature_path = resolve_feature_dir_for_mission(repo_root, mission_slug)

   # Boundary guard — must come before any WP mutation
   try:
       check_pre30_layout(feature_path)
   except Pre30LayoutError as e:
       _output_error(json_output, str(e))
       raise typer.Exit(1)
   ```
   Use `_output_error(json_output, str(e))` if that helper is available in the file, otherwise use `typer.echo(str(e), err=True)`.

5. **Read-only commands** (e.g., `status`, `list`-style queries that only read WP files without emitting events) may also be guarded, but focus on any command that calls `locate_work_package` or `emit_status_transition`. If uncertain whether a command mutates, add the guard — the overhead is negligible (NFR-003).

6. Run `ruff check src/specify_cli/cli/commands/agent/tasks.py` and `mypy src/specify_cli/cli/commands/agent/tasks.py`. Resolve issues.

**Files**: `src/specify_cli/cli/commands/agent/tasks.py` (modified)

**Validation**:
- `ruff check src/specify_cli/cli/commands/agent/tasks.py` — zero issues.
- `grep -n "check_pre30_layout" src/specify_cli/cli/commands/agent/tasks.py` — shows guard call sites in the mutation commands.

---

### Subtask T007: Regression check on affected command tests

**Purpose**: Confirm that the guard wiring does not break any existing post-3.0 command tests.

**Steps**:
1. Run the subset of tests covering the modified command layers:
   ```bash
   pytest tests/specify_cli/ -k "tasks" -v --tb=short
   ```
2. If any test fails because it creates a pre-3.0 fixture and expects the old warning behavior (instead of exit 1), note it — it will be updated in WP05. Do NOT modify those tests in this WP.
3. Confirm all post-3.0 fixture tests still pass (exit 0, no "Pre-3.0 layout detected" message).
4. Run `mypy src/specify_cli/scripts/tasks/tasks_cli.py src/specify_cli/cli/commands/agent/tasks.py` — zero issues.

**Files**: No new files; only test execution and quality checks.

**Validation**: All pre-existing post-3.0 tests pass. Any pre-3.0 legacy fixture test failures are noted for WP05 (expected — those tests are updated in WP05).

---

## Definition of Done

- [ ] `_check_legacy_format` function removed from `tasks_cli.py`.
- [ ] `list_command` legacy iteration branch (`use_legacy` block) removed from `tasks_cli.py`.
- [ ] `check_pre30_layout` called at the command boundary in `tasks_cli.py` (at least 2 call sites for `update_command` and `list_command`).
- [ ] `check_pre30_layout` called in each mutation `@app.command` in `agent/tasks.py` after `feature_path` resolves.
- [ ] Hard-reject: a pre-3.0 fixture passed to a wired command produces exit 1 + message containing `"Pre-3.0 layout detected"` and `"spec-kitty upgrade"`.
- [ ] Post-3.0 fixture passed to any wired command proceeds normally (no guard message, no early exit).
- [ ] `ruff check` and `mypy` pass on both modified files.
- [ ] No mutation of pre-3.0 fixture observed before the guard fires (NFR-006).

## Risks

- **`agent/tasks.py` god-module size**: The file is ~4500 LOC. Use `grep` to navigate; do not read the entire file. Focus on `locate_work_package` and `emit_status_transition` call sites.
- **`feature_path` resolution path**: Some commands may use a different variable name (`feature_dir`, `mission_path`). Adapt accordingly — the guard takes any `Path` to the mission directory within `kitty-specs/`.
- **`_output_error` availability**: If the helper is not accessible at the call site, fall back to `typer.echo(str(e), err=True)` before `raise typer.Exit(1)`.

## Reviewer Guidance

- Verify the guard fires **after** mission slug resolution (not before) to preserve the "no kitty-specs found" error path.
- Verify exit code is 1 (not 0) for pre-3.0 rejection.
- Verify the guard does NOT call `spec-kitty upgrade` or import the runner/registry (C-002).
- Spot-check one mutation command in `agent/tasks.py` end-to-end: guard call → `locate_work_package` → `emit_status_transition`.

---

To implement: `spec-kitty agent action implement WP02 --agent claude`
