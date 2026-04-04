---
work_package_id: WP06
title: Migration Overhaul
dependencies: [WP01]
requirement_refs:
- FR-002
- FR-003
- FR-006
- FR-007
- FR-008
- FR-009
- FR-015
- FR-017
- FR-018
- FR-019
- FR-020
- NFR-003
planning_base_branch: main
merge_target_branch: main
branch_strategy: 'Planning branch: main. Merge target: main. Depends on WP01 — use spec-kitty implement WP06 --base WP01.'
subtasks: [T032, T033, T034, T035, T036, T037, T038]
history:
- date: '2026-04-04'
  action: created
  by: spec-kitty.tasks
authoritative_surface: src/specify_cli/upgrade/
execution_mode: code_change
owned_files: [src/specify_cli/upgrade/**]
---

# WP06: Migration Overhaul

## Objective

Convert the 5 existing constitution-related migrations to no-op stubs. Add metadata ID normalization to `metadata.py`. Create a comprehensive charter-rename migration that handles all 3 legacy layouts, rewrites generated content, updates agent prompts, and normalizes metadata.

## Context

**Critical design decision (DD-1)**: Old migrations become stubs because the charter-rename migration subsumes all their functionality. This removes ALL "constitution" strings from old migration files. The charter-rename migration is one of only 2 files permitted to contain "constitution" strings (as path literals for detecting old state).

**Metadata normalization (DD-2)**: `_LEGACY_MIGRATION_ID_MAP` in metadata.py rewrites old migration IDs on load, BEFORE the runner loop. This allows changing migration_id class attributes in stubs.

See `kitty-specs/063-universal-charter-rename/research.md` for the detailed rationale.

## Implementation Command

```bash
spec-kitty implement WP06 --base WP01
```

## Subtask T032: Convert m_0_10_12 + m_0_13_0 to stubs

**Purpose**: Replace these two old migrations with no-op stubs.

**Steps**:
1. `git mv src/specify_cli/upgrade/migrations/m_0_10_12_constitution_cleanup.py src/specify_cli/upgrade/migrations/m_0_10_12_charter_cleanup.py`
2. Replace entire content of `m_0_10_12_charter_cleanup.py` with:
```python
"""Stub: superseded by 3.1.1_charter_rename migration."""
from pathlib import Path
from .base import BaseMigration, MigrationRegistry, MigrationResult

@MigrationRegistry.register
class CharterCleanupMigration(BaseMigration):
    migration_id = "0.10.12_charter_cleanup"
    description = "Superseded by 3.1.1_charter_rename"
    target_version = "0.10.12"

    def detect(self, project_path: Path) -> bool:
        return False

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        return False, "Superseded by charter-rename migration"

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        return MigrationResult(success=True, warnings=["Superseded by charter-rename"])
```

3. Same for `m_0_13_0`:
   - `git mv m_0_13_0_update_constitution_templates.py m_0_13_0_update_charter_templates.py`
   - Replace content with identical stub pattern, using:
     - `migration_id = "0.13.0_update_charter_templates"`
     - `class UpdateCharterTemplatesMigration`
     - `target_version = "0.13.0"`

**Validation**: `rg -i constitution` on both files returns zero matches.

## Subtask T033: Convert m_2_0_0 + m_2_0_2 + m_2_1_2 to stubs

**Purpose**: Replace these three old migrations with no-op stubs.

**Steps**: Same pattern as T032 for each file:

1. `m_2_0_0_constitution_directory.py` → `m_2_0_0_charter_directory.py`
   - `migration_id = "2.0.0_charter_directory"`
   - `class CharterDirectoryMigration`
   - `target_version = "2.0.0"`

2. `m_2_0_2_constitution_context_bootstrap.py` → `m_2_0_2_charter_context_bootstrap.py`
   - `migration_id = "2.0.2_charter_context_bootstrap"`
   - `class CharterContextBootstrapMigration`
   - `target_version = "2.0.2"`

3. `m_2_1_2_fix_constitution_doctrine_skill.py` → `m_2_1_2_fix_charter_doctrine_skill.py`
   - `migration_id = "2.1.2_fix_charter_doctrine_skill"`
   - `class FixCharterDoctrineSkillMigration`
   - `target_version = "2.1.2"`

**Validation**: `rg -i constitution` on all 3 files returns zero matches.

## Subtask T034: Add _LEGACY_MIGRATION_ID_MAP to metadata.py

**Purpose**: Bridge old migration IDs in user metadata to new charter-era IDs.

**Steps**:
1. In `src/specify_cli/upgrade/metadata.py`:
   - Add near the top (after imports):
   ```python
   _LEGACY_MIGRATION_ID_MAP: dict[str, str] = {
       "0.10.12_constitution_cleanup": "0.10.12_charter_cleanup",
       "0.13.0_update_constitution_templates": "0.13.0_update_charter_templates",
       "2.0.0_constitution_directory": "2.0.0_charter_directory",
       "2.0.2_constitution_context_bootstrap": "2.0.2_charter_context_bootstrap",
       "2.1.2_fix_constitution_doctrine_skill": "2.1.2_fix_charter_doctrine_skill",
   }
   ```
   - Add a method to `ProjectMetadata`:
   ```python
   def _normalize_legacy_ids(self) -> bool:
       """Rewrite constitution-era migration IDs to charter-era IDs.
       Returns True if any IDs were rewritten."""
       changed = False
       for record in self.applied_migrations:
           new_id = _LEGACY_MIGRATION_ID_MAP.get(record.id)
           if new_id:
               record.id = new_id
               changed = True
       return changed
   ```
   - In `ProjectMetadata.load()` (or `cls.load()`), after reading the YAML, call normalization:
   ```python
   metadata = cls._parse(yaml_data)  # however parsing works
   if metadata._normalize_legacy_ids():
       metadata.save(metadata_dir)
   return metadata
   ```

**Note**: The 5 dictionary keys in `_LEGACY_MIGRATION_ID_MAP` are the ONLY "constitution" strings permitted in this file. They are backward-compatibility lookup keys.

**Validation**: The function works (tested in WP07). The dictionary has exactly 5 entries.

## Subtask T035: Create m_3_1_1_charter_rename.py Phase 1: Layout normalization

**Purpose**: Create the main migration file with layout detection and path moves.

**Steps**:
Create `src/specify_cli/upgrade/migrations/m_3_1_1_charter_rename.py`:

```python
"""Comprehensive charter rename: migrate all constitution-era state."""
from pathlib import Path
import shutil
from .base import BaseMigration, MigrationRegistry, MigrationResult

@MigrationRegistry.register
class CharterRenameMigration(BaseMigration):
    migration_id = "3.1.1_charter_rename"
    description = "Comprehensive charter rename: migrate all constitution-era state"
    target_version = "3.1.1"

    def detect(self, project_path: Path) -> bool:
        kittify = project_path / ".kittify"
        # Layout A: modern constitution directory
        if (kittify / "constitution").exists():
            return True
        # Layout B: legacy memory path
        if (kittify / "memory" / "constitution.md").exists():
            return True
        # Layout C: very old mission-specific constitutions
        missions = kittify / "missions"
        if missions.exists():
            for m in missions.iterdir():
                if m.is_dir() and (m / "constitution").exists():
                    return True
        return False

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        if not self.detect(project_path):
            return False, "No constitution-era state found"
        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        changes: list[str] = []
        errors: list[str] = []
        warnings: list[str] = []
        kittify = project_path / ".kittify"
        charter_dir = kittify / "charter"

        # Phase 1: Layout normalization
        self._normalize_layouts(kittify, charter_dir, dry_run, changes, errors, warnings)
        # Phase 2-4: see T036, T037

        if errors:
            return MigrationResult(success=False, changes_made=changes, errors=errors, warnings=warnings)
        return MigrationResult(success=True, changes_made=changes, warnings=warnings)
```

Phase 1 method `_normalize_layouts()`:
- **Layout C**: Find and remove `.kittify/missions/*/constitution/` directories
- **Layout B**: Move `.kittify/memory/constitution.md` → `.kittify/charter/charter.md` (create charter_dir if needed)
- **Layout A**: Rename `.kittify/constitution/` → `.kittify/charter/`, then rename `charter/constitution.md` → `charter/charter.md`
- **Partial state**: If both `constitution/` and `charter/` exist, merge non-conflicting files from constitution/ into charter/, then remove constitution/
- **Stale Layout B**: If `memory/constitution.md` exists but `charter/charter.md` already exists, remove the stale memory file
- All moves use `shutil.move()` with dry_run guard

**Validation**: Layout detection covers all 3 layouts. Partial state handled.

## Subtask T036: Create m_3_1_1 Phase 2: Content rewriting

**Purpose**: After path moves, rewrite embedded "constitution" references in generated files.

**Steps**: Add `_rewrite_content()` method to the migration:

1. For each text file under `.kittify/charter/` (`.md`, `.yaml`, `.yml`, `.json`):
   - Read file content
   - Case-insensitive replace: `constitution` → `charter`, `Constitution` → `Charter`
   - Write back only if content changed
   - Key files: `charter.md` (header, generator comment), `references.yaml` (source_path entries), `context-state.json`, `governance.yaml`, `directives.yaml`, `metadata.yaml`

2. For deployed agent prompt files across all configured agents:
   - Find all `spec-kitty.*.md` files in agent command directories
   - Replace `spec-kitty constitution context` → `spec-kitty charter context`
   - Replace other "constitution" references in prompt text
   - Use `get_agent_dirs_for_project()` to iterate configured agents

**Validation**: After migration, `rg -i constitution .kittify/charter/` on a test project returns zero matches.

## Subtask T037: Create m_3_1_1 Phases 3-4: Agent artifacts + metadata

**Purpose**: Rename agent artifacts and normalize metadata IDs.

**Steps**: Add methods to the migration:

**Phase 3: Agent artifact rename**
- For each configured agent directory:
  - Rename `spec-kitty.constitution.md` → `spec-kitty.charter.md` (if exists)
  - Rename `spec-kitty-constitution-doctrine/` → `spec-kitty-charter-doctrine/` skill directory (if exists)
  - Update content within renamed files

**Phase 4: Metadata normalization**
- Read `.kittify/metadata.yaml`
- For each applied migration record:
  - Check against `_LEGACY_MIGRATION_ID_MAP` (import from metadata module or duplicate the map)
  - Rewrite old IDs to new IDs
- Write back metadata

**Validation**: After migration, no agent directory contains "constitution" in filenames. Metadata contains only charter-era IDs.

## Subtask T038: Verify migration registration and ordering

**Purpose**: Ensure all migrations register correctly and run in version order.

**Steps**:
1. Verify all 6 migration files (5 stubs + 1 new) are discovered by `auto_discover_migrations()`:
   - All match `m_*.py` pattern
   - All have `@MigrationRegistry.register` decorator
   - All have unique `migration_id` values
2. Verify ordering: stubs at 0.10.12, 0.13.0, 2.0.0, 2.0.2, 2.1.2 — charter-rename at 3.1.1
3. Verify no duplicate registrations (the old class names are gone, new ones are unique)
4. Quick smoke test: `python -c "from specify_cli.upgrade.migrations import MigrationRegistry; print([m.migration_id for m in MigrationRegistry.get_all()])"`

**Validation**: All 6 migrations appear in the registry, sorted by version. No registration errors.

## Definition of Done

- [ ] 5 old migration files renamed and converted to stubs (zero "constitution" in any stub)
- [ ] `_LEGACY_MIGRATION_ID_MAP` added to metadata.py with 5 entries
- [ ] `_normalize_legacy_ids()` method added and called from `load()`
- [ ] `m_3_1_1_charter_rename.py` created with all 4 phases
- [ ] Migration handles Layouts A, B, C, and partial state
- [ ] Content rewriting covers all generated files
- [ ] Agent artifacts renamed by migration
- [ ] Metadata IDs normalized by migration
- [ ] All migrations register and order correctly

## Risks

- **Most complex WP**: The charter-rename migration has many edge cases. Test thoroughly in WP07.
- **Windows paths**: Use `Path` objects, not string manipulation. `shutil.move()` handles cross-device moves.
- **File encoding**: Use `read_text(encoding='utf-8')` explicitly.
- **Concurrent runs**: Migration is guarded by `has_migration()` check — idempotent by design.

## Reviewer Guidance

- Verify Layout C handling: pre-0.10.12 users with `.kittify/missions/*/constitution/`
- Verify partial state: both constitution/ and charter/ exist simultaneously
- Verify content rewriting is case-insensitive but case-preserving
- Verify metadata normalization runs on load (before migration loop)
- Count "constitution" strings in charter-rename migration — should be ~10-15 path literals only
