---
work_package_id: WP06
title: Documentation & Test Updates
lane: done
history:
- timestamp: '2025-12-17T13:15:00Z'
  lane: planned
  agent: system
  shell_pid: $$
  action: Prompt generated via /spec-kitty.tasks
- timestamp: '2025-12-17T13:50:00Z'
  lane: done
  agent: claude
  shell_pid: $$
  action: All 286 tests pass, documentation and tests updated
activity_log: |-
  - 2025-12-17T13:15:00Z – system – lane=planned – Prompt created
  - 2025-12-17T13:50:00Z – claude – lane=for_review – All 286 tests pass, documentation and tests updated for frontmatter-only lane system
  - 2025-12-17T14:05:00Z – claude-reviewer – shell_pid=$$ – lane=done – Approved: implementation verified
agent: claude
assignee: Claude
phase: Phase 2 - Polish
review_status: ''
reviewed_by: claude-reviewer
shell_pid: $$
subtasks:
- T029
- T030
- T031
- T032
- T033
- T034
- T035
---

# Work Package Prompt: WP06 – Documentation & Test Updates

## Objectives & Success Criteria

Update documentation and tests to reflect the new frontmatter-only lane system:
1. Update AGENTS.md to explain direct lane editing is now correct
2. Update task prompt template to remove directory-based instructions
3. Update tests to use new flat structure and update command

**Success Criteria** (from spec FR-017 to FR-019, SC-005):
- AGENTS.md no longer warns against editing lane field
- Task prompt template explains flat structure
- All existing tests pass (or are updated for new behavior)

## Context & Constraints

**Reference Documents**:
- Spec: `kitty-specs/007-frontmatter-only-lane/spec.md` (FR-017 to FR-019)
- Current templates in `.kittify/templates/`

**Dependencies**: WP02, WP03, WP04, WP05 (need implementation complete to test)

## Subtasks & Detailed Guidance

### Subtask T029 – Update AGENTS.md

**Purpose**: Inform AI agents about the new lane management approach.

**Steps**:
1. Open `.kittify/AGENTS.md`
2. Find sections about lane management
3. Update to reflect new behavior:

   **Remove/Change**:
   - "Never manually edit the `lane:` field"
   - "The lane is determined by the file's directory location"
   - References to moving files between directories

   **Add**:
   ```markdown
   ## Lane Management

   Work packages use the `lane:` frontmatter field as the single source of truth.

   ### Changing Lanes

   **Option 1: Use the update command** (recommended)
   ```bash
   spec-kitty agent workflow implement WP##
   ```

   **Option 2: Edit frontmatter directly**
   You can directly edit the `lane:` field in the WP file:
   ```yaml
   ---
   lane: "done"  # Valid: planned, doing, for_review, done
   ---
   ```

   Both approaches are valid. The update command also appends to the activity log.

   ### File Structure

   All WP files live in a flat `tasks/` directory:
   ```
   kitty-specs/<feature>/tasks/
   ├── WP01-setup.md
   ├── WP02-implement.md
   └── WP03-test.md
   ```

   The lane is stored in frontmatter, NOT determined by subdirectory.
   ```

**Files**: `.kittify/AGENTS.md` (MODIFY)

**Parallel?**: No, key documentation

### Subtask T030 – Update task-prompt-template.md

**Purpose**: New WP files should have correct instructions.

**Steps**:
1. Open `.kittify/templates/task-prompt-template.md`
2. Update frontmatter comment:
   ```yaml
   # Change from:
   spec-kitty agent workflow review WP##

   # To:
   spec-kitty agent workflow review WP##
   ```
3. Remove/update the "Updating Metadata When Changing Lanes" section:

   **Remove**:
   - "IMPORTANT: Never manually edit the `lane:` field."
   - "The lane is determined by the file's directory location"
   - References to file movement

   **Replace with**:
   ```markdown
   ### Updating Lane Status

   To change a work package's lane, either:

   1. **Edit directly**: Change the `lane:` field in frontmatter
   spec-kitty agent workflow implement <WPID>

   The CLI command also updates the activity log automatically.

   Valid lanes: `planned`, `doing`, `for_review`, `done`
   ```

**Files**: `.kittify/templates/task-prompt-template.md` (MODIFY)

**Parallel?**: Yes, independent of T029

### Subtask T031 – Update/create tasks/README.md template

**Purpose**: Explain flat structure in tasks directories.

**Steps**:
1. Check if `.kittify/templates/tasks-readme-template.md` exists
2. Create or update to explain new structure:
   ```markdown
   # Tasks Directory

   This directory contains work package (WP) prompt files for the feature.

   ## Structure

   All WP files live in this flat directory:
   ```
   tasks/
   ├── WP01-description.md
   ├── WP02-description.md
   └── README.md
   ```

   ## Lane Management

   Each WP file has a `lane:` field in its YAML frontmatter:
   - `planned` - Not yet started
   - `doing` - In progress
   - `for_review` - Ready for review
   - `done` - Complete

   To change a WP's lane:
   ```bash
   spec-kitty agent workflow implement WP##
   ```

   Or edit the `lane:` field directly in the WP file.

   ## Viewing Status

   ```bash
   tasks_cli.py status <feature>
   ```
   ```
3. Update any feature setup scripts that create tasks/README.md

**Files**: `.kittify/templates/tasks-readme-template.md` (NEW or MODIFY)

**Parallel?**: Yes, independent

### Subtask T032 – Update test_tasks_cli_commands.py

**Purpose**: Tests must work with new `update` command and flat structure.

**Steps**:
1. Open `tests/test_tasks_cli_commands.py`
2. Find and update tests:

   **Rename/Update**:
   - `test_move_and_rollback()` → `test_update_and_rollback()`
   - Change `move` command calls to `update`
   - Remove assertions about file location (files don't move)
   - Add assertions about frontmatter `lane:` field

   **Example update**:
   ```python
   def test_update_and_rollback():
       """Test updating WP lane and rolling back."""
       # Setup: Create WP file in flat tasks/
       wp_file = tasks_dir / "WP01-test.md"
       wp_file.write_text("""---
   work_package_id: "WP01"
   lane: "planned"
   ---
   # Test WP
   """)

       # Update lane
       result = runner.invoke(app, ["update", feature, "WP01", "doing"])
       assert result.exit_code == 0

       # Verify file still in same location
       assert wp_file.exists()

       # Verify frontmatter updated
       content = wp_file.read_text()
       assert 'lane: "doing"' in content or "lane: doing" in content

       # Rollback
       result = runner.invoke(app, ["rollback", feature, "WP01"])
       assert result.exit_code == 0

       content = wp_file.read_text()
       assert 'lane: "planned"' in content or "lane: planned" in content
   ```

3. Update `test_move_stages_dirty_source()` → `test_update_stages_changes()`
4. Update or remove `test_move_cleans_stale_target_copy()` (no longer relevant)
5. Add test for legacy format detection

**Files**: `tests/test_tasks_cli_commands.py` (MODIFY)

**Parallel?**: No, key test file

### Subtask T033 – Create test_migration.py

**Purpose**: Test the upgrade command.

**Steps**:
1. Create `tests/test_migration.py`
2. Add tests:
   ```python
   import pytest
   from pathlib import Path
   from src.specify_cli.commands.upgrade import (
       migrate_feature,
       find_features_to_migrate,
       is_legacy_format
   )

   def test_is_legacy_format_detects_old_structure(tmp_path):
       """Legacy format: has lane subdirectories with WP files."""
       feature = tmp_path / "test-feature"
       tasks = feature / "tasks"
       planned = tasks / "planned"
       planned.mkdir(parents=True)
       (planned / "WP01-test.md").write_text("---\nlane: planned\n---\n# WP")

       assert is_legacy_format(feature) is True

   def test_is_legacy_format_new_structure(tmp_path):
       """New format: flat tasks/ with WP files."""
       feature = tmp_path / "test-feature"
       tasks = feature / "tasks"
       tasks.mkdir(parents=True)
       (tasks / "WP01-test.md").write_text("---\nlane: planned\n---\n# WP")

       assert is_legacy_format(feature) is False

   def test_migrate_feature_moves_files(tmp_path):
       """Migration moves files from subdirs to flat."""
       feature = tmp_path / "test-feature"
       tasks = feature / "tasks"
       planned = tasks / "planned"
       planned.mkdir(parents=True)
       (planned / "WP01-test.md").write_text("---\nlane: planned\n---\n# WP")

       migrated, skipped = migrate_feature(feature)

       assert migrated == 1
       assert skipped == 0
       assert (tasks / "WP01-test.md").exists()
       assert not (planned / "WP01-test.md").exists()

   def test_migrate_feature_idempotent(tmp_path):
       """Running migration twice doesn't duplicate files."""
       # Setup already-migrated structure
       feature = tmp_path / "test-feature"
       tasks = feature / "tasks"
       tasks.mkdir(parents=True)
       (tasks / "WP01-test.md").write_text("---\nlane: planned\n---\n# WP")

       migrated, skipped = migrate_feature(feature)

       assert migrated == 0
       assert skipped == 0  # Or 1 if we count existing files
   ```

**Files**: `tests/test_migration.py` (NEW)

**Parallel?**: Yes, independent test file

### Subtask T034 – Update test_scanner.py

**Purpose**: Scanner tests must use frontmatter-based assertions.

**Steps**:
1. Open `tests/test_dashboard/test_scanner.py`
2. Update test fixtures to use flat structure:
   ```python
   @pytest.fixture
   def feature_with_tasks(tmp_path):
       """Create feature with flat tasks structure."""
       feature = tmp_path / "kitty-specs" / "test-feature"
       tasks = feature / "tasks"
       tasks.mkdir(parents=True)

       # Create WPs with different lanes in frontmatter
       (tasks / "WP01-planned.md").write_text(
           '---\nwork_package_id: "WP01"\nlane: "planned"\n---\n'
       )
       (tasks / "WP02-doing.md").write_text(
           '---\nwork_package_id: "WP02"\nlane: "doing"\n---\n'
       )
       return feature
   ```
3. Update assertions to check frontmatter-based grouping:
   ```python
   def test_scan_feature_kanban(feature_with_tasks):
       result = scan_feature_kanban(feature_with_tasks)

       assert len(result["planned"]) == 1
       assert len(result["doing"]) == 1
       assert result["planned"][0]["id"] == "WP01"
       assert result["doing"][0]["id"] == "WP02"
   ```

**Files**: `tests/test_dashboard/test_scanner.py` (MODIFY)

**Parallel?**: Yes, independent test file

### Subtask T035 – Run full test suite and fix regressions

**Purpose**: Ensure all tests pass after changes.

**Steps**:
1. Run full test suite:
   ```bash
   pytest tests/ -v
   ```
2. Identify and fix any failing tests
3. Check for tests that reference:
   - `tasks/planned/`, `tasks/doing/`, etc. directories
   - `move` command (should be `update`)
   - File movement assertions
4. Update or remove obsolete tests
5. Verify coverage of new functionality

**Files**: Various test files

**Parallel?**: No, final verification

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Missing test updates | Run full suite; review each failure |
| Documentation inconsistencies | Cross-reference all docs mentioning lanes |
| Template drift | Update templates before generating new WPs |

## Definition of Done Checklist

- [ ] AGENTS.md updated with new lane management instructions
- [ ] task-prompt-template.md no longer warns against editing lane
- [ ] tasks/README.md template explains flat structure
- [ ] test_tasks_cli_commands.py updated for `update` command
- [ ] test_migration.py created with migration tests
- [ ] test_scanner.py updated for frontmatter-based scanning
- [ ] Full test suite passes
- [ ] No documentation refers to directory-based lanes as current behavior

## Review Guidance

- Verify AGENTS.md is clear for AI agents
- Check template changes apply to new WP generation
- Run full test suite before approving
- Spot-check other documentation for stale lane references
