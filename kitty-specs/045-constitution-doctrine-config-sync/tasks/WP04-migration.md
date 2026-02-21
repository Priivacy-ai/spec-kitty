---
work_package_id: WP04
title: Constitution Directory Migration
lane: "done"
dependencies: [WP03]
base_branch: develop
base_commit: 718d113cf8b7ebea6a4d6e072b7f4d08da99fcc3
created_at: '2026-02-16T05:38:52.406406+00:00'
subtasks:
- T026
- T027
- T028
- T029
- T030
- T031
- T032
phase: Phase 3 - Migration and Integration
assignee: ''
agent: "claude"
shell_pid: '634137'
review_status: "approved"
reviewed_by: "Stijn Dejongh"
history:
- timestamp: '2026-02-15T22:11:29Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP04 – Constitution Directory Migration

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.

---

## Review Feedback

> **Populated by `/spec-kitty.review`** – Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially.]*

---

## Objectives & Success Criteria

- Create upgrade migration that moves constitution from old path to new path
- Update all internal code references (6 locations identified in research.md RQ-4)
- Trigger initial YAML extraction during migration (with graceful fallback)
- Handle all migration edge cases (old path exists, new path already exists, no constitution)
- **All tests pass**, **mypy --strict clean**, **ruff clean**

**Success metrics**:
- Migration moves `.kittify/memory/constitution.md` → `.kittify/constitution/constitution.md`
- Dashboard API serves constitution from new path
- Worktree symlinks point to new directory
- Initial extraction runs and produces YAML files
- Migration is idempotent — safe to run multiple times

## Context & Constraints

- **Spec**: `kitty-specs/045-constitution-doctrine-config-sync/spec.md` — FR-3.1 through FR-3.6
- **Plan**: `kitty-specs/045-constitution-doctrine-config-sync/plan.md` — AD-3 (move and update references)
- **Research**: `kitty-specs/045-constitution-doctrine-config-sync/research.md` — RQ-4 (reference list)
- **Depends on WP03**: `sync()` function needed for initial extraction during migration
- **Migration pattern**: Follow existing migrations in `src/specify_cli/upgrade/migrations/`

**References to update** (from research.md RQ-4):
1. `src/specify_cli/dashboard/handlers/api.py` — constitution path construction
2. `src/specify_cli/core/worktree.py` — symlink setup
3. `src/specify_cli/cli/commands/init.py` — directory comment
4. `src/specify_cli/missions/software-dev/command-templates/constitution.md` — location comment
5. `src/specify_cli/upgrade/migrations/m_0_10_8_fix_memory_structure.py` — destination path
6. Agent command templates (12 agents) — path references

**Implementation command**: `spec-kitty implement WP04 --base WP03`

## Subtasks & Detailed Guidance

### Subtask T026 – Create Migration Script

**Purpose**: Implement the upgrade migration that moves the constitution file and creates the new directory (FR-3.1, FR-3.2).

**Steps**:
1. Determine next migration number:
   - Check existing migrations in `src/specify_cli/upgrade/migrations/`
   - Name format: `m_0_XX_0_constitution_directory.py`

2. Create migration file following existing patterns:
   ```python
   """Migration: Move constitution to .kittify/constitution/ directory."""
   from pathlib import Path
   import shutil

   class Migration:
       version = "0.XX.0"
       description = "Move constitution to .kittify/constitution/ directory"

       def apply(self, project_path: Path, dry_run: bool = False) -> list[str]:
           changes = []
           old_path = project_path / ".kittify" / "memory" / "constitution.md"
           new_dir = project_path / ".kittify" / "constitution"
           new_path = new_dir / "constitution.md"

           # Scenario 1: Old path exists, new doesn't → move
           if old_path.exists() and not new_path.exists():
               if not dry_run:
                   new_dir.mkdir(parents=True, exist_ok=True)
                   shutil.move(str(old_path), str(new_path))
               changes.append(f"Moved {old_path} → {new_path}")

           # Scenario 2: Both exist → skip (user already migrated)
           elif old_path.exists() and new_path.exists():
               changes.append(f"Constitution already at {new_path}, old copy at {old_path}")

           # Scenario 3: New exists, old doesn't → skip (already migrated)
           elif new_path.exists() and not old_path.exists():
               changes.append(f"Constitution already at {new_path}")

           # Scenario 4: Neither exists → skip (no constitution)
           else:
               changes.append("No constitution found, skipping migration")

           return changes
   ```

3. Import and register in migration registry (follow existing pattern)

**Files**:
- `src/specify_cli/upgrade/migrations/m_0_XX_0_constitution_directory.py` (new)

**Notes**:
- Must handle all 4 scenarios gracefully
- Do NOT delete `.kittify/memory/` — other files may live there
- Migration must be idempotent

### Subtask T027 – Update Dashboard API Path

**Purpose**: Update the dashboard's constitution endpoint to serve from the new path (FR-3.5, FR-3.6).

**Steps**:
1. Edit `src/specify_cli/dashboard/handlers/api.py`:
   - Find the `handle_constitution()` method (~line 107-132)
   - Change path from `.kittify/memory/constitution.md` to `.kittify/constitution/constitution.md`
   - Add fallback: if new path doesn't exist, try old path (backward compat during migration)

   ```python
   async def handle_constitution(self, request):
       constitution_path = Path(self.project_dir) / ".kittify" / "constitution" / "constitution.md"
       # Fallback to old path for unmigrated projects
       if not constitution_path.exists():
           constitution_path = Path(self.project_dir) / ".kittify" / "memory" / "constitution.md"
       # ... rest of handler
   ```

**Files**:
- `src/specify_cli/dashboard/handlers/api.py`

**Notes**:
- Fallback ensures dashboard works before and after migration
- Once migration is widespread, fallback can be removed in a future version

### Subtask T028 – Update Worktree Symlink Path

**Purpose**: Update worktree setup to symlink the new constitution directory instead of memory/.

**Steps**:
1. Edit `src/specify_cli/core/worktree.py`:
   - Find `setup_feature_directory()` function (~line 358-395)
   - Update the symlink source from `.kittify/memory` to `.kittify/constitution`
   - Update any exclude patterns
   - Add fallback: if new dir doesn't exist, fall back to old path

2. Update the relative symlink target:
   - Old: `../../../.kittify/memory`
   - New: `../../../.kittify/constitution`

**Files**:
- `src/specify_cli/core/worktree.py`

**Notes**:
- Windows fallback (file copy) must also be updated
- Verify the relative path calculation is correct for worktree depth

### Subtask T029 – Update Init Command Comment

**Purpose**: Update the directory comment in the init command to reference the new path.

**Steps**:
1. Edit `src/specify_cli/cli/commands/init.py`:
   - Find the directory structure comment (~line 112)
   - Change `.kittify/memory/     (for constitution.md -- project-specific)` to
     `.kittify/constitution/ (for constitution.md and structured config)`

**Files**:
- `src/specify_cli/cli/commands/init.py`

### Subtask T030 – Update Command Template Path References

**Purpose**: Update the constitution command template and any agent templates that reference the old path.

**Steps**:
1. Edit `src/specify_cli/missions/software-dev/command-templates/constitution.md`:
   - Update the output location from `.kittify/memory/constitution.md` to `.kittify/constitution/constitution.md`
   - This is the SOURCE template — agent copies are generated from it

2. Check other command templates for references:
   ```bash
   grep -r ".kittify/memory/constitution" src/specify_cli/missions/
   grep -r ".kittify/memory/constitution" src/specify_cli/templates/
   ```
   - Update any hits

3. **DO NOT edit agent copies** (`.claude/`, `.amazonq/`, etc.) — those are generated

**Files**:
- `src/specify_cli/missions/software-dev/command-templates/constitution.md`
- `src/specify_cli/templates/command-templates/constitution.md` (if it exists and differs)
- Any other template files with references

**Notes**:
- Only edit SOURCE templates under `src/specify_cli/`
- Agent copies will be regenerated via migration

### Subtask T031 – Trigger Initial Sync During Migration

**Purpose**: Run initial YAML extraction after moving the constitution file (FR-3.3, FR-3.4).

**Steps**:
1. In the migration's `apply()` method, after moving the file:
   ```python
   # Trigger initial extraction
   try:
       from specify_cli.constitution.sync import sync
       result = sync(new_path, force=True)
       if result.synced:
           changes.append(f"Initial extraction: {len(result.files_written)} YAML files created")
       elif result.error:
           changes.append(f"Warning: Initial extraction failed: {result.error}")
   except Exception as e:
       changes.append(f"Warning: Initial extraction skipped ({e}). Run 'spec-kitty constitution sync' manually.")
   ```

2. Graceful failure: if sync fails (AI unavailable, import error), log warning but don't block migration (FR-3.4)

**Files**:
- `src/specify_cli/upgrade/migrations/m_0_XX_0_constitution_directory.py`

**Parallel?**: Yes — can be developed alongside T026 in the same file.

### Subtask T032 – Write Migration Tests

**Purpose**: Comprehensive tests for the migration script across all scenarios.

**Steps**:
1. Create `tests/specify_cli/upgrade/migrations/test_constitution_migration.py`:

2. **Scenario tests**:
   - Test: old path exists → file moved to new path
   - Test: both paths exist → skip (no overwrite)
   - Test: new path exists, old doesn't → skip (already migrated)
   - Test: neither exists → skip (no constitution)
   - Test: dry_run mode → no file changes
   - Test: initial sync triggered after move
   - Test: initial sync failure → migration still succeeds (warning only)

3. **Reference update tests**:
   - Test dashboard API serves from new path
   - Test worktree symlinks point to new directory
   - Test init command shows updated path

4. **Idempotency test**:
   - Run migration twice → verify same final state

**Files**:
- `tests/specify_cli/upgrade/migrations/test_constitution_migration.py`

**Target**: 10-14 tests covering all scenarios and reference updates.

## Test Strategy

- **Unit tests**: Migration logic tested with tmp_path fixtures
- **Integration tests**: Full migration scenario (create old structure → migrate → verify)
- **Idempotency test**: Run migration twice
- **Run**: `pytest tests/specify_cli/upgrade/migrations/test_constitution_migration.py -v`
- **Also**: `pytest tests/specify_cli/constitution/ -v` (no regressions)

## Risks & Mitigations

- **Risk**: Missing a code reference → research.md RQ-4 is exhaustive; grep for "memory/constitution" after implementation
- **Risk**: Breaking worktree symlinks → Test with actual worktree creation if possible
- **Risk**: Migration ordering conflicts with other pending migrations → Check migration registry
- **Risk**: `.kittify/memory/` directory has other files → DON'T delete the directory, only move constitution.md

## Review Guidance

- Verify ALL 6 code references are updated (grep for "memory/constitution" should find 0 hits in src/)
- Check migration handles all 4 scenarios
- Ensure dashboard API has fallback for unmigrated projects
- Verify initial sync is graceful (doesn't block migration on failure)
- Check migration is registered in the migration registry

## Activity Log

- 2026-02-15T22:11:29Z – system – lane=planned – Prompt created.
- 2026-02-16T05:49:01Z – claude – shell_pid=634137 – lane=for_review – Moved to for_review
- 2026-02-16T06:01:09Z – claude – shell_pid=634137 – lane=done – Self-review: All 7 subtasks complete, 13 migration tests passing, no critical issues in spec drift analysis.
