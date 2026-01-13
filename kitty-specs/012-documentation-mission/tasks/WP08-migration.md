---
work_package_id: "WP08"
subtasks:
  - "T047"
  - "T048"
  - "T049"
  - "T050"
  - "T051"
  - "T052"
title: "Mission Installation Migration"
phase: "Phase 1 - Integration"
lane: "doing"
assignee: ""
agent: "pid-final-test"
shell_pid: "45599"
review_status: ""
reviewed_by: ""
dependencies:
  - "WP01"
  - "WP02"
  - "WP03"
  - "WP04"
  - "WP05"
history:
  - timestamp: "2026-01-12T17:18:56Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP08 – Mission Installation Migration

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately (right below this notice).
- **You must address all feedback** before your work is complete. Feedback items are your implementation TODO list.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you changed.

---

## Review Feedback

> **Populated by `/spec-kitty.review`** – Reviewers add detailed feedback here when work needs changes. Implementation must address every item listed below before returning for re-review.

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## ⚠️ Dependency Rebase Guidance

**This WP depends on**:
- WP01 (Mission Infrastructure) - mission.yaml must exist
- WP02 (Core Templates) - Templates must exist
- WP03 (Divio Templates) - Divio templates must exist
- WP04 (Command Templates) - Command templates must exist
- WP05 (Generators) - Not strictly required but should be included

**Before starting work**:
1. Ensure WP01-04 are complete (all mission files created)
2. Verify mission structure is complete:
   ```
   src/specify_cli/missions/documentation/
   ├── mission.yaml
   ├── templates/
   │   ├── *.md
   │   └── divio/*.md
   └── command-templates/*.md
   ```
3. Optionally: WP05 complete (doc_generators.py exists)

**Critical**: This migration copies the entire documentation mission to user projects. All mission files must be finalized before migration is written.

---

## Objectives & Success Criteria

**Goal**: Create a migration that installs the documentation mission to existing spec-kitty projects, copying the mission directory from `src/specify_cli/missions/documentation/` to `.kittify/missions/documentation/`.

**Success Criteria**:
- Migration file created at `src/specify_cli/upgrade/migrations/m_0_12_0_documentation_mission.py`
- Migration detects when documentation mission is missing from user projects
- Migration copies entire documentation mission directory (mission.yaml, templates/, command-templates/)
- Migration does NOT affect existing missions (software-dev, research)
- Migration is idempotent (safe to run multiple times)
- Migration is registered in migration registry
- Migration passes all tests (detection, apply, idempotency, non-interference)

## Context & Constraints

**Prerequisites**:
- Understanding of spec-kitty migration system
- Existing migration examples as reference
- Complete documentation mission in src/specify_cli/missions/documentation/

**Reference Documents**:
- [plan.md](../plan.md) - Migration design (lines 226-236)
- [spec.md](../spec.md) - Migration requirements (implied by mission installation)
- Existing migrations:
  - `src/specify_cli/upgrade/migrations/m_0_9_1_complete_lane_migration.py` (complex example)
  - `src/specify_cli/upgrade/migrations/m_0_6_7_ensure_missions.py` (mission installation example)
- Migration base class: `src/specify_cli/upgrade/migrations/base.py`
- Migration registry: `src/specify_cli/upgrade/registry.py`

**Constraints**:
- Must not break existing missions
- Must not overwrite user customizations (if they customized documentation mission)
- Must be idempotent (detect already-installed mission)
- Must follow migration naming convention: `m_0_12_0_<description>.py`
- Must be registered in registry (decorator or manual registration)
- Must have tests

**Migration System Overview**:
- Migrations live in `src/specify_cli/upgrade/migrations/`
- Each migration is a class inheriting from `BaseMigration`
- Must implement: `migration_id`, `description`, `target_version`, `detect()`, `apply()`
- Registered via `@MigrationRegistry.register` decorator
- Run via `spec-kitty upgrade` command

## Subtasks & Detailed Guidance

### Subtask T047 – Create Migration File

**Purpose**: Create the migration file with proper structure and boilerplate.

**Steps**:
1. Create `src/specify_cli/upgrade/migrations/m_0_12_0_documentation_mission.py`
2. Add imports:
   ```python
   """Migration: Install documentation mission to user projects (v0.12.0)."""

   from __future__ import annotations

   import shutil
   from pathlib import Path

   from ..registry import MigrationRegistry
   from .base import BaseMigration, MigrationResult
   ```
3. Define migration class:
   ```python
   @MigrationRegistry.register
   class InstallDocumentationMission(BaseMigration):
       """Install the documentation mission to user projects.

       This migration copies the documentation mission from the spec-kitty
       installation (src/specify_cli/missions/documentation/) to the user's
       project (.kittify/missions/documentation/).

       The documentation mission enables users to create and maintain software
       documentation following Write the Docs and Divio principles.
       """

       migration_id = "0.12.0_documentation_mission"
       description = "Install documentation mission to user projects"
       target_version = "0.12.0"

       def detect(self, project_path: Path) -> bool:
           """Detect if documentation mission needs to be installed."""
           # Implementation in T048
           pass

       def apply(self, project_path: Path) -> MigrationResult:
           """Copy documentation mission to user project."""
           # Implementation in T049
           pass
   ```

**Files**: `src/specify_cli/upgrade/migrations/m_0_12_0_documentation_mission.py` (new file)

**Parallel?**: No (foundation for other subtasks)

**Notes**:
- Migration naming: `m_0_12_0_<description>.py`
- Version: "0.12.0" (documentation mission release)
- Decorator: `@MigrationRegistry.register` for auto-registration
- Inherits from `BaseMigration`

**Quality Validation**:
- Does file follow naming convention?
- Is class properly decorated for registration?
- Are required methods defined (detect, apply)?

### Subtask T048 – Implement detect() Method

**Purpose**: Implement logic to detect when documentation mission is missing from a user project.

**Steps**:
1. Implement `detect()` method:
   ```python
   def detect(self, project_path: Path) -> bool:
       """Detect if documentation mission needs to be installed.

       Args:
           project_path: Root directory of user's spec-kitty project

       Returns:
           True if documentation mission is missing, False if already installed
       """
       kittify_dir = project_path / ".kittify"

       if not kittify_dir.exists():
           # Not a spec-kitty project, migration doesn't apply
           return False

       missions_dir = kittify_dir / "missions"

       if not missions_dir.exists():
           # Missions directory doesn't exist (very old project)
           # Migration should run to create it
           return True

       doc_mission_dir = missions_dir / "documentation"

       # Check if documentation mission already exists
       if doc_mission_dir.exists() and (doc_mission_dir / "mission.yaml").exists():
           # Already installed
           return False

       # Documentation mission is missing, migration should run
       return True
   ```

**Files**: `src/specify_cli/upgrade/migrations/m_0_12_0_documentation_mission.py` (modified)

**Parallel?**: No (must be implemented before apply)

**Notes**:
- Checks for .kittify/missions/documentation/ directory
- Checks for mission.yaml file (confirms complete installation)
- Returns False if already installed (idempotency)
- Returns False if not a spec-kitty project (safety)
- Returns True if documentation mission missing

**Quality Validation**:
- Does it correctly detect missing mission?
- Does it return False when already installed?
- Does it handle projects without .kittify directory?
- Does it handle projects without missions/ directory?

### Subtask T049 – Implement apply() Method

**Purpose**: Implement logic to copy documentation mission to user project.

**Steps**:
1. Implement `apply()` method:
   ```python
   def apply(self, project_path: Path) -> MigrationResult:
       """Copy documentation mission to user project.

       Args:
           project_path: Root directory of user's spec-kitty project

       Returns:
           MigrationResult indicating success or failure
       """
       kittify_dir = project_path / ".kittify"
       missions_dir = kittify_dir / "missions"

       # Ensure missions directory exists
       missions_dir.mkdir(parents=True, exist_ok=True)

       # Find source documentation mission
       # The source is in spec-kitty's installation directory
       source_mission = self._find_source_mission()

       if source_mission is None:
           return MigrationResult(
               success=False,
               message="Could not find documentation mission source in spec-kitty installation"
           )

       # Destination
       dest_mission = missions_dir / "documentation"

       # Check if destination already exists (should be caught by detect, but safety check)
       if dest_mission.exists():
           return MigrationResult(
               success=True,
               message="Documentation mission already installed (skipped)",
               changed_files=[]
           )

       # Copy mission directory
       try:
           shutil.copytree(source_mission, dest_mission)

           # Count copied files for reporting
           copied_files = list(dest_mission.rglob("*"))
           file_count = len([f for f in copied_files if f.is_file()])

           return MigrationResult(
               success=True,
               message=f"Documentation mission installed ({file_count} files copied)",
               changed_files=[str(dest_mission)]
           )

       except Exception as e:
           return MigrationResult(
               success=False,
               message=f"Failed to copy documentation mission: {e}"
           )

   def _find_source_mission(self) -> Optional[Path]:
       """Find the documentation mission in spec-kitty's installation.

       Returns:
           Path to source mission directory, or None if not found
       """
       # The source is relative to this migration file
       migrations_dir = Path(__file__).parent
       src_dir = migrations_dir.parent.parent  # Up to src/specify_cli/
       source_mission = src_dir / "missions" / "documentation"

       if source_mission.exists() and (source_mission / "mission.yaml").exists():
           return source_mission

       return None
   ```

**Files**: `src/specify_cli/upgrade/migrations/m_0_12_0_documentation_mission.py` (modified)

**Parallel?**: No (core migration logic)

**Notes**:
- Uses shutil.copytree() to copy entire directory
- Finds source mission relative to migration file location
- Creates missions/ directory if needed
- Checks for existing installation (safety)
- Returns success even if already installed (idempotency)
- Counts copied files for informative message

**Quality Validation**:
- Does it find source mission correctly?
- Does it copy all files (mission.yaml, templates/, command-templates/)?
- Does it handle already-installed case?
- Does it preserve file permissions?
- Is error handling comprehensive?

### Subtask T050 – Test Existing Missions Unaffected

**Purpose**: Ensure migration doesn't break or modify existing missions (software-dev, research).

**Steps**:
1. Add test to verify software-dev mission unchanged:
   ```python
   def test_migration_preserves_software_dev_mission(tmp_path):
       """Verify migration doesn't touch software-dev mission."""
       # Create fake project with software-dev mission
       kittify = tmp_path / ".kittify"
       missions = kittify / "missions"
       software_dev = missions / "software-dev"
       software_dev.mkdir(parents=True)

       # Create dummy mission.yaml
       (software_dev / "mission.yaml").write_text("name: Software Dev Kitty\n")
       original_content = (software_dev / "mission.yaml").read_text()

       # Run migration
       migration = InstallDocumentationMission()
       result = migration.apply(tmp_path)

       assert result.success

       # Verify software-dev unchanged
       after_content = (software_dev / "mission.yaml").read_text()
       assert after_content == original_content
   ```

2. Add test to verify research mission unchanged:
   ```python
   def test_migration_preserves_research_mission(tmp_path):
       """Verify migration doesn't touch research mission."""
       # Similar to software-dev test
       # ...
   ```

3. Add test to verify no other files touched:
   ```python
   def test_migration_only_touches_documentation_mission(tmp_path):
       """Verify migration only modifies .kittify/missions/documentation/."""
       # Create fake project
       kittify = tmp_path / ".kittify"
       kittify.mkdir()

       # Create some files that should NOT be touched
       (kittify / "config.json").write_text("{}")
       (kittify / "memory").mkdir()
       (kittify / "memory" / "notes.md").write_text("# Notes")

       # Run migration
       migration = InstallDocumentationMission()
       result = migration.apply(tmp_path)

       assert result.success

       # Verify other files unchanged
       assert (kittify / "config.json").read_text() == "{}"
       assert (kittify / "memory" / "notes.md").read_text() == "# Notes"

       # Verify only documentation mission was added
       assert (kittify / "missions" / "documentation").exists()
       assert len(list(kittify.glob("*"))) == 3  # config.json, memory/, missions/
   ```

**Files**: `tests/specify_cli/upgrade/migrations/test_m_0_12_0_documentation_mission.py` (new file, created in WP09)

**Parallel?**: Part of testing (WP09)

**Notes**:
- Critical safety check
- Ensures migration is surgical (only adds documentation mission)
- Verifies existing missions untouched
- Verifies no other project files modified

**Quality Validation**:
- Do tests actually verify no changes to software-dev?
- Do tests check research mission too?
- Do tests verify only documentation mission directory created?

### Subtask T051 – Test Migration Idempotency

**Purpose**: Ensure migration can run multiple times safely without duplicating or corrupting data.

**Steps**:
1. Add idempotency test:
   ```python
   def test_migration_is_idempotent(tmp_path):
       """Verify migration can run multiple times safely."""
       # Create fake project
       kittify = tmp_path / ".kittify"
       missions = kittify / "missions"
       missions.mkdir(parents=True)

       migration = InstallDocumentationMission()

       # First run
       result1 = migration.apply(tmp_path)
       assert result1.success

       # Verify mission installed
       doc_mission = missions / "documentation"
       assert doc_mission.exists()
       file_count_1 = len(list(doc_mission.rglob("*")))

       # Second run (should be no-op)
       result2 = migration.apply(tmp_path)
       assert result2.success
       assert "already installed" in result2.message.lower() or "skipped" in result2.message.lower()

       # Verify no changes
       file_count_2 = len(list(doc_mission.rglob("*")))
       assert file_count_1 == file_count_2

       # Third run (verify still idempotent)
       result3 = migration.apply(tmp_path)
       assert result3.success
   ```

2. Add test for detect() idempotency:
   ```python
   def test_migration_detect_after_apply(tmp_path):
       """Verify detect() returns False after apply()."""
       kittify = tmp_path / ".kittify"
       kittify.mkdir()

       migration = InstallDocumentationMission()

       # Before: detect should return True (migration needed)
       assert migration.detect(tmp_path) is True

       # Apply migration
       result = migration.apply(tmp_path)
       assert result.success

       # After: detect should return False (migration not needed)
       assert migration.detect(tmp_path) is False

       # Applying again should be safe
       result2 = migration.apply(tmp_path)
       assert result2.success
   ```

**Files**: `tests/specify_cli/upgrade/migrations/test_m_0_12_0_documentation_mission.py` (modified, created in WP09)

**Parallel?**: Part of testing (WP09)

**Notes**:
- Idempotency is critical for upgrade system
- Users may run migrations multiple times
- Second run should be no-op (or very minimal)
- detect() should return False after successful apply()

**Quality Validation**:
- Does second run succeed?
- Does second run change anything?
- Does detect() return False after apply()?
- Can migration run 3+ times safely?

### Subtask T052 – Register Migration

**Purpose**: Ensure migration is registered and will run during `spec-kitty upgrade`.

**Steps**:
1. Verify `@MigrationRegistry.register` decorator is present on class (should be from T047):
   ```python
   @MigrationRegistry.register
   class InstallDocumentationMission(BaseMigration):
       ...
   ```

2. Test migration registration:
   ```python
   def test_migration_is_registered():
       """Verify migration is registered and discoverable."""
       from specify_cli.upgrade.registry import MigrationRegistry
       from specify_cli.upgrade.migrations.m_0_12_0_documentation_mission import InstallDocumentationMission

       # Check migration is in registry
       migrations = MigrationRegistry.list_migrations()
       migration_ids = [m.migration_id for m in migrations]

       assert "0.12.0_documentation_mission" in migration_ids
   ```

3. Test migration can be loaded:
   ```python
   def test_migration_can_be_loaded():
       """Verify migration can be instantiated and has required attributes."""
       from specify_cli.upgrade.migrations.m_0_12_0_documentation_mission import InstallDocumentationMission

       migration = InstallDocumentationMission()

       assert migration.migration_id == "0.12.0_documentation_mission"
       assert migration.description == "Install documentation mission to user projects"
       assert migration.target_version == "0.12.0"
       assert hasattr(migration, "detect")
       assert hasattr(migration, "apply")
   ```

4. Verify migration appears in `spec-kitty upgrade --dry-run`:
   ```bash
   spec-kitty upgrade --dry-run
   # Should list "0.12.0_documentation_mission" migration
   ```

**Files**:
- `src/specify_cli/upgrade/migrations/m_0_12_0_documentation_mission.py` (verified)
- `tests/specify_cli/upgrade/migrations/test_m_0_12_0_documentation_mission.py` (modified)

**Parallel?**: Part of testing (WP09)

**Notes**:
- Registration happens via decorator (automatic)
- Migration must be importable (no syntax errors)
- Registry scans migrations/ directory for decorated classes
- Migration appears in `spec-kitty upgrade` command

**Quality Validation**:
- Is decorator present?
- Does migration appear in registry?
- Can migration be instantiated?
- Does it have required attributes?

## Implementation Details

### Source Mission Location

The documentation mission source lives in spec-kitty's installation:
```
<spec-kitty-installation>/src/specify_cli/missions/documentation/
├── mission.yaml
├── templates/
│   ├── spec-template.md
│   ├── plan-template.md
│   ├── tasks-template.md
│   ├── task-prompt-template.md
│   └── divio/
│       ├── tutorial-template.md
│       ├── howto-template.md
│       ├── reference-template.md
│       └── explanation-template.md
└── command-templates/
    ├── specify.md
    ├── plan.md
    ├── tasks.md
    ├── implement.md
    └── review.md
```

### Destination (User Project)

Copied to user's project:
```
<user-project>/.kittify/missions/documentation/
├── mission.yaml
├── templates/
│   └── [all templates]
└── command-templates/
    └── [all command templates]
```

### Migration Flow

1. **Detect phase**:
   - Check if `.kittify/` exists (is this a spec-kitty project?)
   - Check if `.kittify/missions/documentation/` exists
   - Check if `mission.yaml` exists in that directory
   - Return True if missing, False if present

2. **Apply phase**:
   - Find source mission (walk up from migration file to src/specify_cli/missions/documentation/)
   - Ensure destination missions/ directory exists
   - Copy entire source directory to destination
   - Verify copy succeeded (check mission.yaml exists)
   - Return success with file count

3. **Verification**:
   - User can run `spec-kitty missions list` and see "documentation" mission
   - User can create documentation mission features with `--mission documentation`
   - Mission loads correctly via `get_mission_by_name("documentation")`

## Test Strategy

**Unit Tests** (to be implemented in WP09):

1. Test detection logic:
   ```python
   def test_detect_missing_mission(tmp_path):
       """Migration detects when documentation mission is missing."""
       kittify = tmp_path / ".kittify"
       kittify.mkdir()

       migration = InstallDocumentationMission()
       assert migration.detect(tmp_path) is True

   def test_detect_existing_mission(tmp_path):
       """Migration detects when documentation mission already exists."""
       missions = tmp_path / ".kittify" / "missions" / "documentation"
       missions.mkdir(parents=True)
       (missions / "mission.yaml").write_text("name: Doc")

       migration = InstallDocumentationMission()
       assert migration.detect(tmp_path) is False

   def test_detect_non_kittify_project(tmp_path):
       """Migration returns False for non-spec-kitty projects."""
       # No .kittify directory
       migration = InstallDocumentationMission()
       assert migration.detect(tmp_path) is False
   ```

2. Test apply logic:
   ```python
   def test_apply_installs_mission(tmp_path):
       """Migration successfully installs documentation mission."""
       kittify = tmp_path / ".kittify"
       kittify.mkdir()

       migration = InstallDocumentationMission()
       result = migration.apply(tmp_path)

       assert result.success
       assert "installed" in result.message.lower()

       # Verify mission directory exists
       doc_mission = kittify / "missions" / "documentation"
       assert doc_mission.exists()
       assert (doc_mission / "mission.yaml").exists()
       assert (doc_mission / "templates").exists()
       assert (doc_mission / "command-templates").exists()

   def test_apply_copies_all_templates(tmp_path):
       """Migration copies all template files."""
       kittify = tmp_path / ".kittify"
       kittify.mkdir()

       migration = InstallDocumentationMission()
       migration.apply(tmp_path)

       doc_mission = kittify / "missions" / "documentation"

       # Check Divio templates
       assert (doc_mission / "templates" / "divio" / "tutorial-template.md").exists()
       assert (doc_mission / "templates" / "divio" / "howto-template.md").exists()
       assert (doc_mission / "templates" / "divio" / "reference-template.md").exists()
       assert (doc_mission / "templates" / "divio" / "explanation-template.md").exists()

       # Check command templates
       assert (doc_mission / "command-templates" / "specify.md").exists()
       assert (doc_mission / "command-templates" / "plan.md").exists()
   ```

3. Test existing missions preserved (from T050)

4. Test idempotency (from T051)

5. Test registration (from T052)

**Integration Test**:
```python
@pytest.mark.integration
def test_migration_end_to_end(tmp_path):
    """Test full migration workflow including mission loading."""
    # Setup fake project
    kittify = tmp_path / ".kittify"
    kittify.mkdir()

    # Before migration: documentation mission not available
    missions_before = list_available_missions(kittify)
    assert "documentation" not in missions_before

    # Run migration
    migration = InstallDocumentationMission()
    assert migration.detect(tmp_path) is True

    result = migration.apply(tmp_path)
    assert result.success

    # After migration: documentation mission available
    missions_after = list_available_missions(kittify)
    assert "documentation" in missions_after

    # Test mission loading
    doc_mission = get_mission_by_name("documentation", kittify)
    assert doc_mission.name == "Documentation Kitty"
    assert doc_mission.domain == "other"

    # Verify templates loadable
    assert "divio/tutorial-template.md" in doc_mission.list_templates()
```

**Manual Validation**:

1. Test migration on a real project:
   ```bash
   # Create test spec-kitty project
   mkdir -p /tmp/test-project
   cd /tmp/test-project
   spec-kitty init

   # Verify documentation mission NOT present
   spec-kitty missions list
   # Should show: software-dev, research (not documentation)

   # Run upgrade
   spec-kitty upgrade

   # Verify documentation mission NOW present
   spec-kitty missions list
   # Should show: software-dev, research, documentation

   # Verify mission works
   spec-kitty agent feature create-feature "test-docs" --mission documentation --json
   ```

2. Test idempotency:
   ```bash
   # Run upgrade again
   spec-kitty upgrade
   # Should skip documentation mission (already installed)

   # Verify no errors or changes
   ```

3. Test migration doesn't break existing missions:
   ```bash
   # Create feature with software-dev mission
   spec-kitty agent feature create-feature "test-feature" --mission software-dev --json

   # Should work unchanged
   ```

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Copy fails mid-operation | High - partial installation | Use shutil.copytree atomic operation, verify post-copy |
| Source mission not found | High - migration fails | Check source exists before copying, clear error message |
| User customized documentation mission | Medium - overwrites customizations | Only install if directory doesn't exist (skip if present) |
| Breaking existing missions | Critical - project unusable | Test software-dev and research unchanged |
| File permission issues | Medium - templates not readable | Preserve file permissions during copy |
| Path issues (Windows) | Medium - migration fails on Windows | Use Path objects, test cross-platform |

## Definition of Done Checklist

- [ ] Migration file created: `src/specify_cli/upgrade/migrations/m_0_12_0_documentation_mission.py`
- [ ] Migration class defined: `InstallDocumentationMission`
- [ ] Migration decorated with `@MigrationRegistry.register`
- [ ] Migration attributes set:
  - [ ] `migration_id = "0.12.0_documentation_mission"`
  - [ ] `description = "Install documentation mission to user projects"`
  - [ ] `target_version = "0.12.0"`
- [ ] `detect()` method implemented:
  - [ ] Returns False for non-spec-kitty projects
  - [ ] Returns False if documentation mission already exists
  - [ ] Returns True if documentation mission missing
- [ ] `apply()` method implemented:
  - [ ] Finds source mission correctly
  - [ ] Creates missions/ directory if needed
  - [ ] Copies entire documentation mission directory
  - [ ] Verifies copy succeeded
  - [ ] Returns MigrationResult with success and file count
  - [ ] Handles already-installed case (idempotency)
- [ ] `_find_source_mission()` helper implemented:
  - [ ] Finds mission relative to migration file
  - [ ] Verifies mission.yaml exists
  - [ ] Returns None if not found
- [ ] Tests written (6 test functions):
  - [ ] test_detect_missing_mission
  - [ ] test_detect_existing_mission
  - [ ] test_detect_non_kittify_project
  - [ ] test_apply_installs_mission
  - [ ] test_apply_copies_all_templates
  - [ ] test_migration_preserves_software_dev_mission
  - [ ] test_migration_preserves_research_mission
  - [ ] test_migration_only_touches_documentation_mission
  - [ ] test_migration_is_idempotent
  - [ ] test_migration_detect_after_apply
  - [ ] test_migration_is_registered
  - [ ] test_migration_can_be_loaded
  - [ ] test_migration_end_to_end (integration)
- [ ] Manual testing completed on real project
- [ ] Migration verified in `spec-kitty upgrade --dry-run`
- [ ] Documentation mission available after migration
- [ ] Existing missions unaffected (software-dev, research)
- [ ] `tasks.md` in feature directory updated with WP08 status

## Review Guidance

**Key Acceptance Checkpoints**:

1. **Detection Accuracy**: Correctly identifies when migration is needed
2. **Copy Completeness**: All mission files copied (mission.yaml, templates, command-templates)
3. **Existing Mission Safety**: software-dev and research missions untouched
4. **Idempotency**: Multiple runs don't break anything
5. **Registration**: Migration appears in registry and upgrade command
6. **Error Handling**: Clear messages when source not found or copy fails

**Validation Commands**:
```bash
# Check migration file exists
ls -la src/specify_cli/upgrade/migrations/m_0_12_0_documentation_mission.py

# Test import
python -c "from specify_cli.upgrade.migrations.m_0_12_0_documentation_mission import InstallDocumentationMission; print('✓ Migration imports successfully')"

# Test registration
python -c "
from specify_cli.upgrade.registry import MigrationRegistry

migrations = MigrationRegistry.list_migrations()
migration_ids = [m.migration_id for m in migrations]
print('Registered migrations:', migration_ids)
assert '0.12.0_documentation_mission' in migration_ids
print('✓ Migration is registered')
"

# Run tests
pytest tests/specify_cli/upgrade/migrations/test_m_0_12_0_documentation_mission.py -v
```

**Review Focus Areas**:
- Migration class correctly structured (inherits BaseMigration, decorated)
- detect() logic is sound (correct conditions)
- apply() logic is complete (copies all files)
- Error handling is comprehensive (source not found, copy fails)
- Idempotency works (detect False after apply, apply safe to re-run)
- Existing missions unaffected (critical safety check)
- Tests are comprehensive (unit + integration)
- Migration works end-to-end (manual test on real project)

## Activity Log

- 2026-01-12T17:18:56Z – system – lane=planned – Prompt created.
- 2026-01-13T09:20:09Z – test-final – lane=doing – Moved to doing
- 2026-01-13T09:36:31Z – final-integration-test – lane=planned – Moved to planned
- 2026-01-13T09:37:37Z – rollback – lane=planned – Moved to planned
- 2026-01-13T09:38:02Z – pid-final-test – shell_pid=45599 – lane=doing – Started implementation via workflow command
