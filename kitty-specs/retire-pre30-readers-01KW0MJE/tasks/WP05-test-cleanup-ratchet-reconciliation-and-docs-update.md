---
work_package_id: WP05
title: Test cleanup, ratchet reconciliation, and docs update
dependencies:
- WP04
requirement_refs:
- FR-010
- FR-011
- NFR-002
- NFR-004
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T020
- T021
- T022
- T023
- T024
- T025
agent: claude
history: []
agent_profile: curator-carla
authoritative_surface: tests/architectural/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- tests/specify_cli/test_standalone_tasks_cli_canonical.py
- tests/specify_cli/scripts/test_task_helpers.py
- tests/architectural/test_no_dead_symbols.py
- docs/status-model.md
role: curator
tags: []
---

# Work Package Prompt: WP05 – Test cleanup, ratchet reconciliation, and docs update

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `curator-carla`
- **Role**: `curator`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Convert the legacy-warning test in `test_standalone_tasks_cli_canonical.py` to a hard-reject assertion, remove the stale `is_legacy_format` from the `test_task_helpers.py` `__all__` check, remove the single grandfathered dead-symbol allowlist entry for `specify_cli.scripts.tasks.task_helpers::is_legacy_format` from `test_no_dead_symbols.py`, confirm the architectural test is green, and update `docs/status-model.md` to describe pre-3.0 layout as hard-rejected by active commands.

## Context

After WP01–WP04, the active runtime is clean: guard is wired, shim chain is severed, branches are removed, dashboard is fixed. Two test files still reference the old `is_legacy_format` behavior and one architectural guard has a stale grandfathered allowlist entry.

**Ratchet note** (spec Assumption 5 + plan IC-05): The grandfathered entry in `test_no_dead_symbols.py` for `specify_cli.scripts.tasks.task_helpers::is_legacy_format` (around line 328) exists because `is_legacy_format` was in `task_helpers.__all__` but had zero callers — the dead-symbol check grandfathered it to avoid a pre-existing failure. WP03 removed it from `__all__`, so the grandfathered entry is now stale and must be removed. **Remove only this one entry** — do not touch unrelated entries. A sibling mission (#2049) is also modifying this allowlist; be surgical.

**Documentation update** (FR-011): `docs/status-model.md` already correctly describes `lane` frontmatter as historical/migration-only in its main body. The required addition is a clear subsection that pre-3.0 lane-directory shapes are actively rejected by commands with a hard error, and that `spec-kitty upgrade` is the mandatory migration step.

---

### Subtask T020: Convert legacy warning test to hard-reject test

**Purpose**: Replace the old `_check_legacy_format` warning test with a test that asserts the new hard-reject behavior (Pre30LayoutError / exit 1 + correct message) — counting toward NFR-004.

**Steps**:
1. Open `tests/specify_cli/test_standalone_tasks_cli_canonical.py`.
2. Search for `test_src_tasks_cli_check_legacy_format_warns_once` (or the test that exercises the old `_check_legacy_format` function).
3. Replace the test body. The new test should:
   - Create a minimal pre-3.0 fixture: `tmp_path/kitty-specs/001-test/tasks/planned/WP01.md` exists.
   - Invoke the command (or call `check_pre30_layout` directly if the test is a unit test).
   - Assert that:
     - The exit code is 1 (non-zero).
     - The output/stderr contains `"Pre-3.0 layout detected"`.
     - The output/stderr contains `"spec-kitty upgrade"`.
     - No files under `kitty-specs/` are modified (NFR-006).

   Example structure (adapt to the actual test framework used in this file):
   ```python
   def test_tasks_cli_rejects_pre30_layout(tmp_path):
       """Hard-reject pre-3.0 layout: exit 1 + correct message, no mutation."""
       feature = tmp_path / "kitty-specs" / "001-test"
       planned = feature / "tasks" / "planned"
       planned.mkdir(parents=True)
       wp = planned / "WP01.md"
       wp.write_text("---\nwork_package_id: WP01\n---\n")

       # Record mtime before command
       mtime_before = wp.stat().st_mtime

       # Run the command — use whatever runner the file uses (e.g., CliRunner, subprocess)
       # Assert exit code 1 and correct message
       # Assert wp.stat().st_mtime == mtime_before (no mutation)
   ```
   Adapt the invocation to match the existing test harness in the file (look at neighboring tests for the correct CLI runner pattern).

4. Rename the test to `test_tasks_cli_rejects_pre30_layout` (or a similarly descriptive name).
5. Run `pytest tests/specify_cli/test_standalone_tasks_cli_canonical.py -v --tb=short` — all pass including the new test.

**Files**: `tests/specify_cli/test_standalone_tasks_cli_canonical.py` (modified)

**Validation**: `pytest tests/specify_cli/test_standalone_tasks_cli_canonical.py -v` — all pass. The converted test explicitly asserts exit 1 + message content.

---

### Subtask T021: Remove is_legacy_format from test_task_helpers.py __all__ assertion

**Purpose**: The `test_task_helpers.py` test that asserts `is_legacy_format` is in `task_helpers.__all__` is now wrong — WP03 removed it from `__all__`.

**Steps**:
1. Open `tests/specify_cli/scripts/test_task_helpers.py`.
2. Search:
   ```bash
   grep -n "is_legacy_format" tests/specify_cli/scripts/test_task_helpers.py
   ```
3. Find the assertion that checks `"is_legacy_format" in task_helpers.__all__` (or imports it from `task_helpers`).
4. Remove only that assertion or the `is_legacy_format` element from the list-based `__all__` check. Do not remove or change other assertions in the same test.
5. If the entire test only checks for `is_legacy_format`, convert it to assert the symbol is NOT in `__all__` (confirming de-export):
   ```python
   def test_task_helpers_does_not_export_is_legacy_format():
       """is_legacy_format was de-exported from task_helpers in mission retire-pre30-readers."""
       import specify_cli.scripts.tasks.task_helpers as th
       assert "is_legacy_format" not in th.__all__
   ```
6. Run `pytest tests/specify_cli/scripts/test_task_helpers.py -v --tb=short` — all pass.

**Files**: `tests/specify_cli/scripts/test_task_helpers.py` (modified)

**Validation**: `pytest tests/specify_cli/scripts/test_task_helpers.py -v` — all pass.

---

### Subtask T022: Remove grandfathered dead-symbol allowlist entry

**Purpose**: Remove the single stale entry `specify_cli.scripts.tasks.task_helpers::is_legacy_format` from the grandfathered allowlist in `test_no_dead_symbols.py`.

**Critical constraint**: Remove ONLY this one entry. Other entries in the grandfathered list belong to other missions (including the in-flight #2049 shrink-ratchet-allowlists mission). Touch nothing else in the file.

**Steps**:
1. Open `tests/architectural/test_no_dead_symbols.py`.
2. Search:
   ```bash
   grep -n "is_legacy_format\|task_helpers" tests/architectural/test_no_dead_symbols.py
   ```
3. Find the entry. It will look like one of:
   - A string `"specify_cli.scripts.tasks.task_helpers::is_legacy_format"` in a list/set.
   - A tuple `("specify_cli.scripts.tasks.task_helpers", "is_legacy_format")`.
4. Remove exactly that line (and its trailing comma if needed for valid Python).
5. Do NOT remove any other entry, even if it looks related.
6. Check Python syntax:
   ```bash
   python3 -c "import ast; ast.parse(open('tests/architectural/test_no_dead_symbols.py').read()); print('syntax OK')"
   ```

**Files**: `tests/architectural/test_no_dead_symbols.py` (modified)

**Validation**: Python syntax check passes. `grep -n "is_legacy_format" tests/architectural/test_no_dead_symbols.py` returns zero output.

---

### Subtask T023: Run test_no_dead_symbols.py to confirm green

**Purpose**: Verify that removing the grandfathered entry leaves the test green (not broken by the entry's absence or by a residual dead symbol).

**Steps**:
1. Run:
   ```bash
   pytest tests/architectural/test_no_dead_symbols.py -v --tb=short
   ```
2. If the test fails because `is_legacy_format` is still somehow present in the import graph (e.g., still in `__all__` somewhere), trace it back to the un-removed shim. Fix the root cause (not by re-adding the grandfathered entry).
3. If the test passes, proceed.

**Files**: No new files; test execution only.

**Validation**: `pytest tests/architectural/test_no_dead_symbols.py -v` — all pass.

---

### Subtask T024: Update docs/status-model.md (FR-011)

**Purpose**: Add a clear subsection stating that pre-3.0 lane-directory layouts are hard-rejected by active commands, and that `spec-kitty upgrade` is the mandatory first step for pre-3.0 projects.

**Steps**:
1. Open `docs/status-model.md`.
2. Read the existing text. The spec notes that line 21 already says `lane` is historical/migration-only. The required addition is a **Troubleshooting** or **Pre-3.0 migration** note.
3. Find the "Troubleshooting" section (around line 358) or the "Migration behavior (for pre-3.0 features)" section (around line 180).
4. Add or expand one subsection. Example text:

   ```markdown
   ### Pre-3.0 layout rejection

   Active `spec-kitty` commands (task, status, acceptance) require a post-3.0
   project layout — flat `tasks/WP*.md` files and `status.events.jsonl` as the
   status source of truth. Commands that encounter a pre-3.0 lane-directory layout
   (`tasks/planned/`, `tasks/doing/`, `tasks/for_review/`, `tasks/done/`
   containing `.md` files) will refuse to proceed:

   ```
   Pre-3.0 layout detected (tasks/planned/ directories or frontmatter lane state).
   Run `spec-kitty upgrade` to migrate before continuing.
   ```

   **Migration path**: Run `spec-kitty upgrade` (or
   `spec-kitty upgrade --migration 0.9.0_frontmatter_only_lanes`) to move WP
   files from lane subdirectories to flat `tasks/`. After upgrade, all active
   commands will work normally.

   The `lane` frontmatter field is historical/migration-only and is not written
   or read by any active command. Status is tracked exclusively through
   `status.events.jsonl`.
   ```

5. Ensure the prose matches the canonical project language (no "feature", use "mission"; no "legacy project", use "pre-3.0 project").
6. Run the terminology guard:
   ```bash
   pytest tests/architectural/test_no_legacy_terminology.py -v
   ```
   Fix any violations before proceeding.

**Files**: `docs/status-model.md` (modified)

**Validation**: `pytest tests/architectural/test_no_legacy_terminology.py -v` — all pass.

---

### Subtask T025: Full test suite green check

**Purpose**: Final CI-equivalent regression run confirming the entire mission is complete and no test suite is broken.

**Steps**:
1. Run the full suite in parallel:
   ```bash
   PWHEADLESS=1 pytest tests/ -n auto --dist loadfile -p no:cacheprovider -v --tb=short 2>&1 | tail -30
   ```
2. Run the architectural tests individually for clarity:
   ```bash
   pytest tests/architectural/ -v --tb=short
   ```
3. Run the upgrade tests:
   ```bash
   pytest tests/upgrade/ -v --tb=short
   ```
4. If any test fails:
   - If it is an existing test broken by this mission's changes: fix it in this WP (within `owned_files`).
   - If it is a pre-existing unrelated failure: record it in the PR description as a pre-existing flake; do NOT retry-to-green.
5. Confirm zero new failures attributable to this mission.

**Files**: No new files; comprehensive regression run.

**Validation**: Full suite green (or pre-existing failures documented). `pytest tests/architectural/` and `pytest tests/upgrade/` — all pass.

---

## Definition of Done

- [ ] `test_standalone_tasks_cli_canonical.py` has a hard-reject test (exit 1 + message check) replacing the old warning test.
- [ ] `test_task_helpers.py` no longer asserts `is_legacy_format` is in `task_helpers.__all__`.
- [ ] `test_no_dead_symbols.py` allowlist entry for `specify_cli.scripts.tasks.task_helpers::is_legacy_format` removed.
- [ ] `pytest tests/architectural/test_no_dead_symbols.py` — green.
- [ ] `docs/status-model.md` has a "Pre-3.0 layout rejection" subsection with the hard-reject message and `spec-kitty upgrade` instructions.
- [ ] `pytest tests/architectural/test_no_legacy_terminology.py` — green.
- [ ] Full test suite: `pytest tests/ -n auto --dist loadfile` — green (no new failures vs. pre-mission baseline).

## Risks

- **In-flight #2049 conflict**: The shrink-ratchet-allowlists mission (#2049) is also modifying `test_no_dead_symbols.py`. If that branch is merged before this WP, re-check the line number of the target entry before removing it. The entry to remove is unambiguously `specify_cli.scripts.tasks.task_helpers::is_legacy_format` — search by content, not line number.
- **Terminology guard false positives**: The new `docs/status-model.md` text should use "pre-3.0 project" not "legacy project". Check for forbidden terms before committing.
- **`test_standalone_tasks_cli_canonical.py` harness**: Look at neighboring tests in the file to match the CLI runner pattern (CliRunner, subprocess invoke, or direct function call) before writing the new test body.

## Reviewer Guidance

- Verify `test_no_dead_symbols.py` diff touches ONLY the `is_legacy_format` entry for `task_helpers` — no other entries modified.
- Verify the new docs section does not use "feature" or "legacy project" terminology.
- Confirm the hard-reject test asserts exit code 1 AND message content (not just one of the two).
- Run `pytest tests/architectural/test_no_dead_symbols.py tests/architectural/test_no_legacy_terminology.py -v` and confirm both green.

---

To implement: `spec-kitty agent action implement WP05 --agent claude`
