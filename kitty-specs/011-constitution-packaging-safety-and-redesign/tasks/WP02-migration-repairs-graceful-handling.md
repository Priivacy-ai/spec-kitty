---
work_package_id: "WP02"
subtasks:
  - "T010"
  - "T011"
  - "T012"
  - "T013"
  - "T014"
  - "T015"
  - "T016"
title: "Migration Repairs & Graceful Handling"
phase: "Feature - Track 1 Critical Safety"
lane: "done"
assignee: ""
agent: "claude-sonnet-4-5"
shell_pid: ""
review_status: "approved"
reviewed_by: "claude-sonnet-4-5"
history:
  - timestamp: "2026-01-12T11:30:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
  - timestamp: "2026-01-12T11:45:00Z"
    lane: "done"
    agent: "claude-sonnet-4-5"
    shell_pid: ""
    action: "Code review approved - All migrations implemented correctly with graceful handling and idempotency. 21/21 tests passed."
---

# Work Package Prompt: WP02 – Migration Repairs & Graceful Handling

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately (right below this notice).
- **You must address all feedback** before your work is complete. Feedback items are your implementation TODO list.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you changed.

---

## Review Feedback

> **Populated by `/spec-kitty.review`** – Reviewers add detailed feedback here when work needs changes. Implementation must address every item listed below before returning for re-review.

*[This section is empty initially. Reviewers will populate it if the work is returned from review. If you see feedback here, treat each item as a must-do before completion.]*

---

## Objectives & Success Criteria

**Goal**: Fix 4 existing migrations to handle missing files gracefully + create new migration to remove mission-specific constitutions.

**Success Criteria**:
1. `m_0_7_3_update_scripts.py` handles missing bash scripts gracefully (returns success with warning, not failure)
2. `m_0_10_6_workflow_simplification.py` copies templates BEFORE checking can_apply() (not during)
3. `m_0_10_2_update_slash_commands.py` explicitly removes legacy .toml files
4. `m_0_10_0_python_only.py` explicitly removes `.kittify/scripts/tasks/` directory
5. New `m_0_10_12_constitution_cleanup.py` removes mission constitution directories
6. New migration registered in migration registry
7. All migrations are idempotent (running twice produces same result as running once)
8. Upgrade from 0.6.4 → 0.10.12 completes without manual intervention

**Acceptance Test**:
```bash
# Create 0.6.4 project simulation
mkdir /tmp/test-upgrade
cd /tmp/test-upgrade
# ... setup 0.6.4 structure ...

# Run upgrade
spec-kitty upgrade

# Verify all migrations succeeded
echo $?  # Should be 0

# Run upgrade again (test idempotency)
spec-kitty upgrade
echo $?  # Should be 0 (no errors)
```

---

## Context & Constraints

**Why This Matters**: Migration failures block users from upgrading. Currently, migrations fail partway through due to assumptions about file existence, requiring manual cleanup and deep knowledge of the migration system.

**Related Documents**:
- Spec: `kitty-specs/011-constitution-packaging-safety-and-redesign/spec.md` (FR-021 through FR-027, User Story 4)
- Plan: `kitty-specs/011-constitution-packaging-safety-and-redesign/plan.md` (Migration section)
- Research: `kitty-specs/011-constitution-packaging-safety-and-redesign/research.md` (Research Area 3: Migration Repair Patterns)
- Data Model: `kitty-specs/011-constitution-packaging-safety-and-redesign/data-model.md` (Entity 2: Migration Structure)

**Problem Pattern**: Existing migrations use `can_apply()` to check if files exist in package, then fail if files missing. This breaks when:
1. Package structure changes between versions (files removed)
2. User manually deleted files
3. Earlier migrations already cleaned up files

**Solution Pattern**:
- `can_apply()` should always return `(True, "")` unless structural issues exist
- `apply()` should handle missing files gracefully with warnings, not errors
- All migrations must be idempotent (safe to run multiple times)

**Dependencies**: None (can run in parallel with WP03, WP04)

---

## Subtasks & Detailed Guidance

### Subtask T010 – Fix `m_0_7_3_update_scripts.py` graceful handling

**Purpose**: Make migration succeed even when bash scripts missing from package.

**Current Issue**: Migration checks if bash scripts exist in package (lines 44-55), fails with "Template scripts not found" if missing.

**File**: `src/specify_cli/upgrade/migrations/m_0_7_3_update_scripts.py`

**Current Code** (lines 44-55):
```python
def can_apply(self, project_path: Path) -> tuple[bool, str]:
    """Check if we can find the template scripts."""
    # We need access to the template scripts from the installed package
    import specify_cli

    pkg_root = Path(specify_cli.__file__).parent
    template_script = pkg_root / "scripts" / "bash" / "create-new-feature.sh"

    if not template_script.exists():
        return False, "Template scripts not found in installed package"

    return True, ""
```

**Problem**: If bash scripts removed from package in later version, migration fails instead of skipping gracefully.

**New Code**:
```python
def can_apply(self, project_path: Path) -> tuple[bool, str]:
    """Check if we can apply this migration.

    Always returns True - if template scripts missing from package,
    apply() will handle gracefully with a warning. This allows
    forward compatibility when scripts are removed in later versions.
    """
    # Check if project has .kittify directory
    kittify_dir = project_path / ".kittify"
    if not kittify_dir.exists():
        return False, "No .kittify directory (not a spec-kitty project)"

    # Always allow migration - let apply() handle missing templates
    return True, ""
```

**Update apply() method** (lines 57-100):
```python
def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
    """Copy updated scripts from package templates."""
    changes: list[str] = []
    warnings: list[str] = []
    errors: list[str] = []

    import specify_cli

    pkg_root = Path(specify_cli.__file__).parent

    # Scripts to update
    scripts = [
        ("scripts/bash/create-new-feature.sh", ".kittify/scripts/bash/create-new-feature.sh"),
        ("scripts/bash/common.sh", ".kittify/scripts/bash/common.sh"),
    ]

    # Check if any scripts exist in package
    any_scripts_found = False
    for src_rel, dest_rel in scripts:
        src = pkg_root / src_rel
        if src.exists():
            any_scripts_found = True
            break

    if not any_scripts_found:
        warnings.append(
            "Bash scripts not found in package (removed in later version or never existed). "
            "If you need script updates, they may have been handled by migration 0.10.0 cleanup. "
            "This is not an error."
        )
        # Return success with warning - this is expected if scripts removed
        return MigrationResult(
            success=True,
            changes_made=[],
            errors=[],
            warnings=warnings,
        )

    # Scripts exist, proceed with update
    for src_rel, dest_rel in scripts:
        src = pkg_root / src_rel
        dest = project_path / dest_rel

        if not src.exists():
            warnings.append(f"Template {src_rel} not found in package")
            continue

        if not dest.parent.exists():
            if not dry_run:
                dest.parent.mkdir(parents=True, exist_ok=True)

        if dry_run:
            changes.append(f"Would update {dest_rel}")
        else:
            try:
                shutil.copy2(src, dest)
                changes.append(f"Updated {dest_rel}")
            except OSError as e:
                errors.append(f"Failed to update {dest_rel}: {e}")

    success = len(errors) == 0
    return MigrationResult(
        success=success,
        changes_made=changes,
        errors=errors,
        warnings=warnings,
    )
```

**Key Changes**:
1. `can_apply()` always returns True (unless not a spec-kitty project)
2. `apply()` checks if scripts exist before trying to copy
3. If no scripts found, returns success with warning (not error)
4. Individual script failures become warnings, not errors
5. Migration succeeds even if scripts missing

**Testing**:
```python
# Test 1: Normal case (scripts exist)
assert migration.can_apply(project_path) == (True, "")
result = migration.apply(project_path)
assert result.success == True

# Test 2: Scripts missing from package
# Mock pkg_root to point to empty directory
result = migration.apply(project_path)
assert result.success == True  # Should succeed with warning
assert len(result.warnings) > 0
assert "not found in package" in result.warnings[0]

# Test 3: Idempotency (run twice)
result1 = migration.apply(project_path)
result2 = migration.apply(project_path)
assert result1.success == result2.success
```

---

### Subtask T011 – Fix `m_0_10_6_workflow_simplification.py` copy before validate

**Purpose**: Ensure templates are copied during apply(), not checked during can_apply().

**Current Issue**: Migration checks mission templates exist before copying them (lines 78-94), but templates aren't copied until apply() runs. Catch-22: can't check if templates updated until we copy them.

**File**: `src/specify_cli/upgrade/migrations/m_0_10_6_workflow_simplification.py`

**Current Code** (lines 78-94):
```python
def can_apply(self, project_path: Path) -> tuple[bool, str]:
    """Check if we have mission templates to copy from."""
    missions_dir = project_path / ".kittify" / "missions"
    if not missions_dir.exists():
        return False, "No missions directory found"

    # Look for software-dev mission with updated templates
    software_dev_templates = missions_dir / "software-dev" / "command-templates"
    if software_dev_templates.exists():
        # Check if templates have the new workflow commands
        implement = software_dev_templates / "implement.md"
        if implement.exists():
            content = implement.read_text(encoding="utf-8")
            if "spec-kitty agent workflow implement" in content:
                return True, ""

    return False, "Mission templates not updated with workflow commands"
```

**Problem**: This assumes mission templates already have the new workflow commands. But where would they come from? They need to be copied from the package first!

**Solution**: The check is backwards. The migration should:
1. Always return `(True, "")` from `can_apply()` (except structural issues)
2. Copy templates from package during `apply()`
3. If package templates don't have workflow commands, add warning but succeed

**New Code**:
```python
def can_apply(self, project_path: Path) -> tuple[bool, str]:
    """Check if we can apply this migration.

    Always returns True - mission templates will be copied from package
    during apply(). This migration updates slash commands to use workflow
    commands, which requires copying updated templates from the package.
    """
    kittify_dir = project_path / ".kittify"
    if not kittify_dir.exists():
        return False, "No .kittify directory (not a spec-kitty project)"

    # Always allow migration
    return True, ""
```

**Update apply() method** (lines 96-156):
```python
def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
    """Update implement and review slash commands with new workflow-based templates."""
    changes: List[str] = []
    warnings: List[str] = []
    errors: List[str] = []

    # First, ensure mission templates are up to date from package
    import specify_cli
    pkg_root = Path(specify_cli.__file__).parent

    # Check if missions exist in package (after WP01 relocation)
    pkg_missions = pkg_root / "missions" / "software-dev" / "command-templates"

    if not pkg_missions.exists():
        # Fallback: check old location (pre-WP01)
        pkg_missions = pkg_root / ".kittify" / "missions" / "software-dev" / "command-templates"

    if not pkg_missions.exists():
        warnings.append(
            "Mission templates not found in package. "
            "If you've upgraded from an older version, mission templates may need manual update. "
            "This is not critical - slash commands will use default behavior."
        )
        # Continue anyway - don't block migration

    # Copy mission templates from package to project (if they exist)
    project_missions_dir = project_path / ".kittify" / "missions"
    if pkg_missions.exists() and not dry_run:
        software_dev_dest = project_missions_dir / "software-dev" / "command-templates"
        software_dev_dest.mkdir(parents=True, exist_ok=True)

        for template in ["implement.md", "review.md"]:
            src = pkg_missions / template
            if src.exists():
                dest = software_dev_dest / template
                try:
                    shutil.copy2(src, dest)
                    changes.append(f"Updated mission template: software-dev/{template}")
                except OSError as e:
                    warnings.append(f"Failed to copy mission template {template}: {e}")

    # Now update slash commands in ALL agent directories
    templates_to_update = ["implement.md", "review.md"]
    total_updated = 0

    for agent_root, subdir in self.AGENT_DIRS:
        agent_dir = project_path / agent_root / subdir

        if not agent_dir.exists():
            continue

        updated_count = 0
        for template_name in templates_to_update:
            # Source: mission templates (if they exist after copy above)
            source_template = project_missions_dir / "software-dev" / "command-templates" / template_name

            if not source_template.exists():
                # No mission template available, skip this agent
                continue

            dest_filename = f"spec-kitty.{template_name}"
            dest_path = agent_dir / dest_filename

            if dry_run:
                changes.append(f"Would update {agent_root}: {dest_filename}")
            else:
                try:
                    dest_path.write_text(source_template.read_text(encoding="utf-8"), encoding="utf-8")
                    updated_count += 1
                except OSError as e:
                    warnings.append(f"Failed to update {agent_root}/{dest_filename}: {e}")

        if updated_count > 0:
            agent_name = agent_root.strip(".")
            changes.append(f"Updated {updated_count} templates for {agent_name}")
            total_updated += updated_count

    if total_updated > 0:
        changes.append(f"Total: Updated {total_updated} slash command templates")
        changes.append("Templates now use 'spec-kitty agent workflow' commands")
    elif not changes:
        warnings.append("No templates were updated (may have been updated already or missions missing)")

    success = len(errors) == 0
    return MigrationResult(
        success=success,
        changes_made=changes,
        errors=errors,
        warnings=warnings,
    )
```

**Key Changes**:
1. `can_apply()` no longer checks if templates already updated
2. `apply()` copies mission templates from package FIRST
3. Then updates agent slash commands from those mission templates
4. Handles missing package templates gracefully with warnings
5. Checks both new (`pkg_root/missions/`) and old (`.kittify/missions/`) locations for compatibility

**Testing**:
```python
# Test 1: Fresh project, templates need update
result = migration.apply(project_path)
assert result.success == True
assert len(result.changes_made) > 0

# Test 2: Templates already updated (idempotency)
result1 = migration.apply(project_path)
result2 = migration.apply(project_path)
assert result2.success == True
# May have warnings about already updated, but should succeed

# Test 3: Package missing templates
# Mock pkg_root to empty directory
result = migration.apply(project_path)
assert result.success == True  # Succeed with warnings
assert len(result.warnings) > 0
```

---

### Subtask T012 – Fix `m_0_10_2_update_slash_commands.py` .toml removal

**Purpose**: Explicitly remove legacy .toml command files during slash command migration.

**Current Issue**: Migration updates .toml files to .md format but may not remove old .toml files, leaving duplicate command definitions.

**File**: `src/specify_cli/upgrade/migrations/m_0_10_2_update_slash_commands.py`

**Expected Current Behavior** (need to verify):
- Reads `.kittify/commands/*.toml` files
- Creates equivalent `.claude/commands/spec-kitty.*.md` files
- May or may not delete original .toml files

**Required Change**: Ensure .toml files are explicitly removed after conversion.

**Investigation Steps**:
1. Read the migration file to understand current behavior
2. Check if it already removes .toml files
3. If not, add explicit removal step

**Code Pattern to Add** (if missing):
```python
def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
    changes = []
    warnings = []
    errors = []

    # ... existing conversion logic ...

    # AFTER conversion complete, remove legacy .toml files
    commands_dir = project_path / ".kittify" / "commands"
    if commands_dir.exists():
        toml_files = list(commands_dir.glob("*.toml"))

        if toml_files:
            for toml_file in toml_files:
                if dry_run:
                    changes.append(f"Would remove legacy {toml_file.name}")
                else:
                    try:
                        toml_file.unlink()
                        changes.append(f"Removed legacy {toml_file.name}")
                    except OSError as e:
                        warnings.append(f"Failed to remove {toml_file.name}: {e}")

        # If directory now empty, remove it too
        try:
            if not any(commands_dir.iterdir()):
                if not dry_run:
                    commands_dir.rmdir()
                    changes.append("Removed empty .kittify/commands/ directory")
        except OSError:
            pass  # Directory not empty or permission issue, that's OK

    # ... rest of method ...
```

**Steps**:
1. Read `src/specify_cli/upgrade/migrations/m_0_10_2_update_slash_commands.py`
2. Locate the `apply()` method
3. Check if .toml removal already present
4. If missing, add removal logic AFTER conversion logic
5. Ensure idempotency (if .toml files already gone, don't error)
6. Add changes to MigrationResult

**Verification**:
```python
# Setup: Create project with .toml files
toml_file = project_path / ".kittify" / "commands" / "specify.toml"
toml_file.parent.mkdir(parents=True, exist_ok=True)
toml_file.write_text("[command]\nname = 'specify'\n")

# Run migration
result = migration.apply(project_path)
assert result.success == True

# Verify .toml files removed
assert not toml_file.exists()
assert "Removed legacy" in str(result.changes_made)

# Test idempotency
result2 = migration.apply(project_path)
assert result2.success == True  # Should succeed even if .toml already gone
```

---

### Subtask T013 – Fix `m_0_10_0_python_only.py` tasks/ cleanup verification

**Purpose**: Ensure `.kittify/scripts/tasks/` directory is explicitly removed.

**Current Issue**: Migration may not explicitly remove obsolete Python task helpers in `.kittify/scripts/tasks/`.

**File**: `src/specify_cli/upgrade/migrations/m_0_10_0_python_only.py`

**Expected Cleanup**: This migration removes bash/powershell scripts in favor of Python-only workflow. Should also remove `.kittify/scripts/tasks/` which contained Python helper scripts that are now obsolete.

**Investigation Steps**:
1. Read migration file to check current cleanup logic
2. Verify if `.kittify/scripts/tasks/` removal is explicit
3. If missing, add explicit removal

**Code Pattern to Add** (if missing):
```python
def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
    changes = []
    warnings = []
    errors = []

    # ... existing cleanup logic ...

    # Remove obsolete task helpers directory
    tasks_dir = project_path / ".kittify" / "scripts" / "tasks"
    if tasks_dir.exists():
        if dry_run:
            changes.append("Would remove .kittify/scripts/tasks/ (obsolete task helpers)")
        else:
            try:
                shutil.rmtree(tasks_dir)
                changes.append("Removed .kittify/scripts/tasks/ (obsolete Python task helpers)")
            except OSError as e:
                warnings.append(f"Failed to remove tasks/ directory: {e}")

    # ... rest of method ...
```

**Steps**:
1. Read `src/specify_cli/upgrade/migrations/m_0_10_0_python_only.py`
2. Locate `apply()` method
3. Check if tasks/ directory removal is present
4. If missing, add explicit removal logic
5. Ensure idempotency (if directory already gone, don't error)

**Verification**:
```python
# Setup: Create obsolete tasks directory
tasks_dir = project_path / ".kittify" / "scripts" / "tasks"
tasks_dir.mkdir(parents=True, exist_ok=True)
(tasks_dir / "helper.py").write_text("# obsolete helper")

# Run migration
result = migration.apply(project_path)
assert result.success == True

# Verify tasks/ removed
assert not tasks_dir.exists()
assert "Removed .kittify/scripts/tasks/" in str(result.changes_made)

# Test idempotency
result2 = migration.apply(project_path)
assert result2.success == True  # Should succeed even if directory already gone
```

---

### Subtask T014 – Create `m_0_10_12_constitution_cleanup.py` migration

**Purpose**: Remove mission-specific constitution directories from all missions.

**File**: Create new `src/specify_cli/upgrade/migrations/m_0_10_12_constitution_cleanup.py`

**Template** (from research.md):
```python
"""Migration: Remove mission-specific constitution directories."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import List

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult


@MigrationRegistry.register
class ConstitutionCleanupMigration(BaseMigration):
    """Remove mission-specific constitution directories.

    As of 0.10.12, spec-kitty uses only project-level constitutions
    at .kittify/memory/constitution.md. Mission-specific constitutions
    in .kittify/missions/*/constitution/ are removed.

    This simplifies the constitution system by having a single source
    of truth at the project level, rather than per-mission constitutions
    that caused confusion about which constitution applied.
    """

    migration_id = "0.10.12_constitution_cleanup"
    description = "Remove mission-specific constitution directories"
    target_version = "0.10.12"

    def detect(self, project_path: Path) -> bool:
        """Check if any mission has a constitution directory.

        Returns:
            True if any mission still has a constitution/ subdirectory
        """
        missions_dir = project_path / ".kittify" / "missions"
        if not missions_dir.exists():
            return False

        for mission_dir in missions_dir.iterdir():
            if mission_dir.is_dir():
                constitution_dir = mission_dir / "constitution"
                if constitution_dir.exists():
                    return True

        return False

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """Check if migration can be applied.

        Always returns True - removal is always safe. If constitution
        directories don't exist, that's fine (already cleaned up).

        Returns:
            (True, "") unless project structure is invalid
        """
        kittify_dir = project_path / ".kittify"
        if not kittify_dir.exists():
            return False, "No .kittify directory (not a spec-kitty project)"

        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Remove constitution directories from all missions.

        This migration removes mission-specific constitution directories,
        which are no longer used. Projects should use the project-level
        constitution at .kittify/memory/constitution.md instead.

        Args:
            project_path: Path to the project root
            dry_run: If True, don't actually remove files, just report what would happen

        Returns:
            MigrationResult with success=True and list of removed directories
        """
        changes: List[str] = []
        warnings: List[str] = []
        errors: List[str] = []

        missions_dir = project_path / ".kittify" / "missions"
        if not missions_dir.exists():
            # No missions directory - nothing to clean up
            return MigrationResult(
                success=True,
                changes_made=[],
                warnings=[],
                errors=[]
            )

        # Scan all mission directories
        missions_found = []
        constitutions_removed = []

        for mission_dir in missions_dir.iterdir():
            if not mission_dir.is_dir():
                continue

            missions_found.append(mission_dir.name)
            constitution_dir = mission_dir / "constitution"

            if constitution_dir.exists():
                if dry_run:
                    changes.append(f"Would remove {mission_dir.name}/constitution/")
                else:
                    try:
                        shutil.rmtree(constitution_dir)
                        changes.append(f"Removed {mission_dir.name}/constitution/")
                        constitutions_removed.append(mission_dir.name)
                    except OSError as e:
                        errors.append(f"Failed to remove {mission_dir.name}/constitution/: {e}")

        # Add informative message if any constitutions were removed
        if constitutions_removed:
            warnings.append(
                f"Mission-specific constitutions removed from: {', '.join(constitutions_removed)}. "
                "Spec-kitty now uses a single project-level constitution at "
                ".kittify/memory/constitution.md. Run /spec-kitty.constitution to create "
                "a project constitution if you don't have one yet."
            )
        elif not changes:
            # No constitutions found - that's OK, might have been cleaned up manually
            changes.append("No mission-specific constitutions found (already clean)")

        success = len(errors) == 0
        return MigrationResult(
            success=success,
            changes_made=changes,
            errors=errors,
            warnings=warnings,
        )
```

**Steps**:
1. Create new file: `src/specify_cli/upgrade/migrations/m_0_10_12_constitution_cleanup.py`
2. Copy template code above
3. Ensure proper imports (`shutil`, `Path`, `List`, `MigrationRegistry`, `BaseMigration`, `MigrationResult`)
4. Add docstrings explaining the migration's purpose
5. Implement all three required methods: `detect()`, `can_apply()`, `apply()`
6. Handle edge cases:
   - No missions directory
   - No constitution directories (already cleaned)
   - Permission errors during removal
7. Ensure idempotency (safe to run multiple times)

**Testing Checklist**:
```python
# Test 1: detect() finds constitutions
missions_dir = project_path / ".kittify" / "missions" / "software-dev" / "constitution"
missions_dir.mkdir(parents=True)
(missions_dir / "principles.md").write_text("# Test")
assert migration.detect(project_path) == True

# Test 2: can_apply() always returns True (for spec-kitty projects)
assert migration.can_apply(project_path) == (True, "")

# Test 3: apply() removes constitutions
result = migration.apply(project_path)
assert result.success == True
assert not (project_path / ".kittify" / "missions" / "software-dev" / "constitution").exists()
assert len(result.changes_made) > 0

# Test 4: Idempotency (run twice)
result2 = migration.apply(project_path)
assert result2.success == True
assert "already clean" in str(result2.changes_made) or len(result2.changes_made) == 0

# Test 5: dry_run doesn't actually remove
result = migration.apply(project_path, dry_run=True)
assert "Would remove" in str(result.changes_made)
assert (project_path / ".kittify" / "missions" / "software-dev" / "constitution").exists()
```

---

### Subtask T015 – Register new migration in migration registry

**Purpose**: Ensure `m_0_10_12_constitution_cleanup` is discovered and run during upgrades.

**File**: `src/specify_cli/upgrade/migrations/__init__.py` or registry module

**Steps**:
1. Check how migrations are registered
2. If using `@MigrationRegistry.register` decorator (as in template above):
   - Verify decorator is present in T014 code
   - Import the new migration module in `__init__.py`
3. If using explicit registration:
   - Add registration call in appropriate place

**Expected Registration Pattern**:
```python
# In src/specify_cli/upgrade/migrations/__init__.py

# Import all migration modules to trigger @MigrationRegistry.register decorators
from . import m_0_7_3_update_scripts
from . import m_0_10_0_python_only
from . import m_0_10_2_update_slash_commands
from . import m_0_10_6_workflow_simplification
from . import m_0_10_8_fix_memory_structure
from . import m_0_10_9_repair_templates
from . import m_0_10_12_constitution_cleanup  # ADD THIS LINE

# Registry is populated by decorators on import
```

**Verification**:
```python
# Test: New migration appears in registry
from specify_cli.upgrade.registry import MigrationRegistry

migrations = MigrationRegistry.get_all_migrations()
migration_ids = [m.migration_id for m in migrations]

assert "0.10.12_constitution_cleanup" in migration_ids
```

**Additional Checks**:
1. Verify migration is in correct version order
2. Ensure target_version is "0.10.12"
3. Confirm migration_id follows naming pattern: `X.Y.Z_description`

---

### Subtask T016 – Test migration idempotency (run twice, verify same result)

**Purpose**: Prove all migrations can be run multiple times without errors.

**Test Approach**: For each migration, run it twice on the same project and verify:
1. Both runs succeed
2. Second run produces same or similar result as first
3. No errors on second run (may have warnings like "already clean")

**Test Script Template**:
```python
#!/usr/bin/env python3
"""Test migration idempotency.

This script tests that all migrations can be run multiple times safely.
"""

from pathlib import Path
import tempfile
import shutil

from specify_cli.upgrade.migrations import (
    m_0_7_3_update_scripts,
    m_0_10_0_python_only,
    m_0_10_2_update_slash_commands,
    m_0_10_6_workflow_simplification,
    m_0_10_12_constitution_cleanup,
)

def test_migration_idempotency(migration_class, setup_func=None):
    """Test that a migration can be run twice without errors.

    Args:
        migration_class: The migration class to test
        setup_func: Optional function to setup test project state
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)

        # Setup basic project structure
        kittify = project_path / ".kittify"
        kittify.mkdir()

        # Run setup if provided
        if setup_func:
            setup_func(project_path)

        # Create migration instance
        migration = migration_class()

        # First run
        print(f"\nTesting {migration.migration_id} - Run 1")
        result1 = migration.apply(project_path, dry_run=False)
        print(f"  Success: {result1.success}")
        print(f"  Changes: {len(result1.changes_made)}")
        print(f"  Warnings: {len(result1.warnings)}")
        print(f"  Errors: {len(result1.errors)}")

        assert result1.success, f"First run failed: {result1.errors}"

        # Second run (idempotency test)
        print(f"\nTesting {migration.migration_id} - Run 2 (idempotency)")
        result2 = migration.apply(project_path, dry_run=False)
        print(f"  Success: {result2.success}")
        print(f"  Changes: {len(result2.changes_made)}")
        print(f"  Warnings: {len(result2.warnings)}")
        print(f"  Errors: {len(result2.errors)}")

        assert result2.success, f"Second run failed: {result2.errors}"

        print(f"✓ {migration.migration_id} is idempotent")

def setup_constitution_cleanup(project_path):
    """Setup project with mission constitutions for cleanup test."""
    missions = project_path / ".kittify" / "missions" / "software-dev" / "constitution"
    missions.mkdir(parents=True)
    (missions / "principles.md").write_text("# Test constitution")

def setup_scripts_update(project_path):
    """Setup project with old bash scripts."""
    scripts = project_path / ".kittify" / "scripts" / "bash"
    scripts.mkdir(parents=True)
    (scripts / "create-new-feature.sh").write_text("#!/bin/bash\necho old")

def setup_tasks_cleanup(project_path):
    """Setup project with obsolete tasks directory."""
    tasks = project_path / ".kittify" / "scripts" / "tasks"
    tasks.mkdir(parents=True)
    (tasks / "helper.py").write_text("# obsolete")

def setup_toml_cleanup(project_path):
    """Setup project with legacy .toml files."""
    commands = project_path / ".kittify" / "commands"
    commands.mkdir(parents=True)
    (commands / "specify.toml").write_text("[command]\nname='specify'\n")

def setup_slash_commands(project_path):
    """Setup project with missions for slash command update."""
    missions = project_path / ".kittify" / "missions" / "software-dev" / "command-templates"
    missions.mkdir(parents=True)
    (missions / "implement.md").write_text("# Implement template")

    claude = project_path / ".claude" / "commands"
    claude.mkdir(parents=True)
    (claude / "spec-kitty.implement.md").write_text("# Old implement")

if __name__ == "__main__":
    print("Testing migration idempotency...")

    # Test each migration
    test_migration_idempotency(
        m_0_7_3_update_scripts.UpdateScriptsMigration,
        setup_scripts_update
    )

    test_migration_idempotency(
        m_0_10_0_python_only.PythonOnlyMigration,
        setup_tasks_cleanup
    )

    test_migration_idempotency(
        m_0_10_2_update_slash_commands.UpdateSlashCommandsMigration,
        setup_toml_cleanup
    )

    test_migration_idempotency(
        m_0_10_6_workflow_simplification.WorkflowSimplificationMigration,
        setup_slash_commands
    )

    test_migration_idempotency(
        m_0_10_12_constitution_cleanup.ConstitutionCleanupMigration,
        setup_constitution_cleanup
    )

    print("\n✓ All migrations are idempotent!")
```

**Steps**:
1. Create test script (above template)
2. Run script to test all 5 migrations
3. Fix any migrations that fail idempotency test
4. Document results in migration testing report

**Expected Results**:
- All migrations succeed on first run
- All migrations succeed on second run
- Second run may have fewer changes (already done) but no errors
- Warnings acceptable (e.g., "already clean", "already updated")

**Failure Cases to Fix**:
- Error on second run → Migration not idempotent, needs fixing
- Different errors first vs second run → State dependency issue
- Crash on second run → Missing existence checks

---

## Test Strategy

**Unit Tests**: Each migration should have unit tests covering:
1. `detect()` returns True when migration needed, False when not
2. `can_apply()` handles missing project structure gracefully
3. `apply()` succeeds with expected changes
4. `apply()` idempotency (running twice)
5. `apply()` dry_run doesn't modify files

**Integration Test**: Full upgrade path test (defer to WP06):
- Create 0.6.4 project structure
- Run `spec-kitty upgrade`
- Verify all migrations succeeded
- Run `spec-kitty upgrade` again (idempotency)
- Verify project state correct

**Manual Testing**: Test on real 0.6.4 project (if available).

---

## Risks & Mitigations

| Risk | Impact | Mitigation | Covered By |
|------|--------|------------|------------|
| Breaking existing upgrade paths | Critical | Test with real 0.6.4 project | WP06 integration tests |
| Data loss from aggressive cleanup | High | All migrations use warnings, not errors, for missing files | All subtasks |
| Idempotency failures | Medium | Explicit idempotency testing in T016 | T016 |
| New migration not registered | High | Verify registry import in T015 | T015 |
| Edge cases not handled | Medium | Comprehensive error handling in each migration | T010-T014 |

---

## Definition of Done Checklist

- [ ] All subtasks T010-T016 completed
- [ ] `m_0_7_3_update_scripts.py` handles missing scripts gracefully
- [ ] `m_0_10_6_workflow_simplification.py` copies templates before validating
- [ ] `m_0_10_2_update_slash_commands.py` explicitly removes .toml files
- [ ] `m_0_10_0_python_only.py` explicitly removes tasks/ directory
- [ ] `m_0_10_12_constitution_cleanup.py` created and tested
- [ ] New migration registered in migration system
- [ ] All 5 migrations pass idempotency test
- [ ] Unit tests written for new migration
- [ ] Code review requested from maintainer

---

## Review Guidance

**Key Acceptance Checkpoints**:
1. **Graceful handling**: All migrations succeed even when expected files missing
2. **Idempotency verified**: Run twice test passes for all migrations
3. **New migration complete**: Constitution cleanup migration fully implemented
4. **Registry updated**: New migration appears in `spec-kitty upgrade --list`
5. **Error handling robust**: Migrations use warnings instead of errors for missing files

**Red Flags for Reviewer**:
- Any migration throws exception for missing files
- Second run of migration produces different errors than first run
- New migration not registered (doesn't appear in migration list)
- Hardcoded paths instead of using project_path parameter

**Testing Checklist for Reviewer**:
```bash
# 1. Run idempotency test script
python tests/test_migration_idempotency.py

# 2. Test new migration
spec-kitty agent migration test 0.10.12_constitution_cleanup

# 3. Check migration appears in list
spec-kitty upgrade --list | grep "0.10.12"

# 4. Verify graceful handling
# Create project with missing files, run migrations, verify no errors
```

---

## Activity Log

- 2026-01-12T11:30:00Z – system – lane=planned – Prompt created via /spec-kitty.tasks

---

### Updating Lane Status

To change this work package's lane, either:

1. **Edit directly**: Change the `lane:` field in frontmatter
2. **Use CLI**: `spec-kitty agent tasks move-task WP02 --to <lane> --note "message"`

The CLI command also updates the activity log automatically.

**Valid lanes**: `planned`, `doing`, `for_review`, `done`
- 2026-01-12T10:43:24Z – agent – lane=doing – Started implementation via workflow command
- 2026-01-12T10:48:17Z – unknown – lane=for_review – Ready for review
