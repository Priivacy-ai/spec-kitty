---
work_package_id: "WP04"
subtasks:
  - "T017"
  - "T018"
  - "T019"
  - "T020"
  - "T021"
  - "T022"
  - "T023"
  - "T024"
title: "Migration Command"
phase: "Phase 1 - Core Implementation"
lane: "done"
assignee: ""
agent: "claude"
shell_pid: "$$"
review_status: ""
reviewed_by: "claude-reviewer"
history:
  - timestamp: "2025-12-17T13:15:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: "$$"
    action: "Prompt generated via /spec-kitty.tasks"
  - timestamp: "2025-12-17T16:45:00Z"
    lane: "done"
    agent: "claude"
    shell_pid: "$$"
    action: "Migration implemented using existing upgrade system"
activity_log: |
  - 2025-12-17T13:15:00Z – system – lane=planned – Prompt created
  - 2025-12-17T16:45:00Z – claude – lane=for_review – Implementation complete
  - 2025-12-17T14:05:00Z – claude-reviewer – shell_pid=$$ – lane=done – Approved: implementation verified
---

# Work Package Prompt: WP04 – Migration Command

## Objectives & Success Criteria

Implement the `spec-kitty upgrade` command to migrate projects from directory-based to frontmatter-only lanes:
1. Flatten lane directories (`tasks/planned/`, `tasks/doing/`, etc.) into flat `tasks/`
2. Preserve lane value in frontmatter from source directory
3. Process main repo and all worktrees
4. Require user confirmation before modification

**Success Criteria** (from spec FR-009 to FR-013, SC-004):
- `spec-kitty upgrade` migrates `tasks/planned/WP01.md` to `tasks/WP01.md` with `lane: "planned"` preserved
- User sees explicit warning and must confirm before changes
- All worktrees are migrated in single operation
- Migration handles up to 100 WP files
- Migration is idempotent (safe to run multiple times)

## Context & Constraints

**Reference Documents**:
- Spec: `kitty-specs/007-frontmatter-only-lane/spec.md` (User Story 3)
- Data Model: `kitty-specs/007-frontmatter-only-lane/data-model.md` (Migration Flow)

**Key Decision** (from planning): All-at-once migration (main + worktrees) with single confirmation.

**Dependencies**: WP01 (legacy detection)

**Can run in parallel with**: WP02, WP03

## Subtasks & Detailed Guidance

### Subtask T017 – Create upgrade.py command skeleton

**Purpose**: Establish the command entry point.

**Steps**:
1. Create `src/specify_cli/commands/upgrade.py`
2. Set up basic command structure:
   ```python
   """Migration command to upgrade from directory-based to frontmatter-only lanes."""
   from pathlib import Path
   from typing import List, Tuple
   import typer
   from rich.console import Console

   console = Console()

   def upgrade_command(
       force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompt"),
       dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show what would be changed without modifying files")
   ):
       """Migrate from directory-based to frontmatter-only lanes.

       This command:
       - Moves all WP files from tasks/{lane}/ to flat tasks/
       - Preserves lane value in frontmatter from source directory
       - Processes main kitty-specs/ and all .worktrees/
       - Removes empty lane subdirectories after migration
       """
       repo_root = find_repo_root()
       # Implementation in subsequent subtasks
   ```
3. Register command in CLI app (check existing command registration pattern)

**Files**: `src/specify_cli/commands/upgrade.py` (NEW)

**Parallel?**: No, foundation for other subtasks

### Subtask T018 – Implement feature scanning logic

**Purpose**: Find all features that need migration in main repo and worktrees.

**Steps**:
1. Add scanning function:
   ```python
   def find_features_to_migrate(repo_root: Path) -> List[Tuple[Path, str]]:
       """Find all features with legacy format in main repo and worktrees.

       Returns:
           List of (feature_path, location_label) tuples
           location_label is "main" or "worktree: <name>"
       """
       features = []

       # Scan main kitty-specs/
       main_specs = repo_root / "kitty-specs"
       if main_specs.exists():
           for feature_dir in main_specs.iterdir():
               if feature_dir.is_dir() and is_legacy_format(feature_dir):
                   features.append((feature_dir, "main"))

       # Scan .worktrees/
       worktrees_dir = repo_root / ".worktrees"
       if worktrees_dir.exists():
           for worktree in worktrees_dir.iterdir():
               if worktree.is_dir():
                   wt_specs = worktree / "kitty-specs"
                   if wt_specs.exists():
                       for feature_dir in wt_specs.iterdir():
                           if feature_dir.is_dir() and is_legacy_format(feature_dir):
                               features.append((feature_dir, f"worktree: {worktree.name}"))

       return features
   ```
2. Import `is_legacy_format` from `legacy_detector.py` (WP01)

**Files**: `src/specify_cli/commands/upgrade.py` (MODIFY)

**Parallel?**: No, depends on T017

### Subtask T019 – Implement single-feature migration logic

**Purpose**: Core migration algorithm for one feature.

**Steps**:
1. Add migration function:
   ```python
   def migrate_feature(feature_dir: Path, dry_run: bool = False) -> Tuple[int, int]:
       """Migrate a single feature from directory-based to flat structure.

       Args:
           feature_dir: Path to feature directory (contains tasks/)
           dry_run: If True, only report what would change

       Returns:
           Tuple of (files_migrated, files_skipped)
       """
       tasks_dir = feature_dir / "tasks"
       if not tasks_dir.exists():
           return (0, 0)

       migrated = 0
       skipped = 0

       for lane in ["planned", "doing", "for_review", "done"]:
           lane_dir = tasks_dir / lane
           if not lane_dir.is_dir():
               continue

           for wp_file in lane_dir.glob("WP*.md"):
               target = tasks_dir / wp_file.name

               # Check if already exists in flat directory
               if target.exists():
                   console.print(f"  [yellow]Skip: {wp_file.name} already exists in tasks/[/yellow]")
                   skipped += 1
                   continue

               if dry_run:
                   console.print(f"  [dim]Would move: {lane}/{wp_file.name} → tasks/{wp_file.name}[/dim]")
               else:
                   # Update frontmatter lane field
                   content = wp_file.read_text()
                   updated_content = ensure_lane_in_frontmatter(content, lane)
                   target.write_text(updated_content)
                   wp_file.unlink()  # Remove original

               migrated += 1

       return (migrated, skipped)
   ```

**Files**: `src/specify_cli/commands/upgrade.py` (MODIFY)

**Parallel?**: No, core algorithm

### Subtask T020 – Ensure lane preservation in frontmatter

**Purpose**: Set `lane:` field from source directory if not already correct.

**Steps**:
1. Add helper function:
   ```python
   def ensure_lane_in_frontmatter(content: str, expected_lane: str) -> str:
       """Ensure frontmatter has correct lane field.

       If lane field exists, verify it matches expected (warn if different).
       If lane field missing, add it.
       """
       import re
       import yaml

       # Parse frontmatter
       match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
       if not match:
           # No frontmatter, add it
           return f"---\nlane: \"{expected_lane}\"\n---\n{content}"

       frontmatter_str = match.group(1)
       frontmatter = yaml.safe_load(frontmatter_str) or {}
       body = content[match.end():]

       current_lane = frontmatter.get("lane")

       if current_lane is None:
           # Add lane field
           frontmatter["lane"] = expected_lane
       elif current_lane != expected_lane:
           # Warn about mismatch, use directory as source of truth
           console.print(f"  [yellow]Note: lane field was '{current_lane}', setting to '{expected_lane}' based on directory[/yellow]")
           frontmatter["lane"] = expected_lane

       # Rebuild document
       new_frontmatter = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
       return f"---\n{new_frontmatter}---{body}"
   ```
2. Use ruamel.yaml if available for better formatting preservation

**Files**: `src/specify_cli/commands/upgrade.py` (MODIFY)

**Parallel?**: No, helper for T019

### Subtask T021 – Handle .worktrees/ migration

**Purpose**: Iterate and migrate all worktree features.

**Steps**:
1. Integrate worktree handling into main upgrade flow:
   ```python
   def upgrade_command(...):
       # ... (confirmation logic from T022)

       features = find_features_to_migrate(repo_root)

       if not features:
           console.print("[green]No features need migration - all already use flat structure.[/green]")
           return

       # Group by location for reporting
       main_features = [f for f in features if f[1] == "main"]
       worktree_features = [f for f in features if f[1].startswith("worktree")]

       console.print(f"\n[bold]Migrating {len(features)} feature(s)...[/bold]")

       total_migrated = 0
       total_skipped = 0

       for feature_dir, location in features:
           console.print(f"\n[bold]{feature_dir.name}[/bold] ({location})")
           migrated, skipped = migrate_feature(feature_dir, dry_run)
           total_migrated += migrated
           total_skipped += skipped

       console.print(f"\n[green]Migration complete: {total_migrated} files migrated, {total_skipped} skipped[/green]")
   ```

**Files**: `src/specify_cli/commands/upgrade.py` (MODIFY)

**Parallel?**: Yes, can be developed alongside T019

### Subtask T022 – Add confirmation prompt with warning

**Purpose**: Prevent accidental migration; inform user of changes.

**Steps**:
1. Add confirmation logic:
   ```python
   def upgrade_command(force: bool = False, dry_run: bool = False):
       repo_root = find_repo_root()
       features = find_features_to_migrate(repo_root)

       if not features:
           console.print("[green]No features need migration.[/green]")
           return

       # Count totals for warning
       main_count = len([f for f in features if f[1] == "main"])
       wt_count = len([f for f in features if f[1].startswith("worktree")])

       # Display warning
       console.print("\n[bold yellow]WARNING: This will migrate your project to frontmatter-only lanes.[/bold yellow]\n")
       console.print("[bold]Changes:[/bold]")
       console.print("  - All WP files will be moved to flat tasks/ directories")
       console.print("  - Lane subdirectories (planned/, doing/, etc.) will be removed")
       console.print("  - The lane: frontmatter field becomes the source of truth\n")

       console.print("[bold]This affects:[/bold]")
       if main_count:
           console.print(f"  - kitty-specs/ ({main_count} feature(s))")
       if wt_count:
           console.print(f"  - .worktrees/ ({wt_count} feature(s))")

       console.print("\n[dim]Tip: Commit your changes before running this command.[/dim]\n")

       if dry_run:
           console.print("[bold]DRY RUN - No files will be modified[/bold]\n")
       elif not force:
           confirm = typer.confirm("Continue?", default=False)
           if not confirm:
               console.print("[yellow]Migration cancelled.[/yellow]")
               raise typer.Exit(0)

       # Proceed with migration...
   ```

**Files**: `src/specify_cli/commands/upgrade.py` (MODIFY)

**Parallel?**: No, must be integrated into main flow

### Subtask T023 – Make migration idempotent

**Purpose**: Safe to run multiple times without data loss.

**Steps**:
1. Add idempotency checks (partially in T019):
   - Skip files already in flat `tasks/`
   - Skip features that don't have lane subdirectories
   - Don't fail on already-migrated features
2. Add reporting for skipped items:
   ```python
   if target.exists():
       # Check if content is identical
       if target.read_text() == updated_content:
           console.print(f"  [dim]Already migrated: {wp_file.name}[/dim]")
       else:
           console.print(f"  [yellow]Conflict: {wp_file.name} exists with different content[/yellow]")
       skipped += 1
       continue
   ```

**Files**: `src/specify_cli/commands/upgrade.py` (MODIFY)

**Parallel?**: No, integrated into T019

### Subtask T024 – Clean up empty lane subdirectories

**Purpose**: Remove empty directories after migration.

**Steps**:
1. Add cleanup at end of feature migration:
   ```python
   def cleanup_empty_lane_dirs(tasks_dir: Path, dry_run: bool = False):
       """Remove empty lane subdirectories after migration."""
       for lane in ["planned", "doing", "for_review", "done"]:
           lane_dir = tasks_dir / lane
           if lane_dir.is_dir():
               # Check if empty (only .gitkeep or nothing)
               contents = list(lane_dir.iterdir())
               if not contents or (len(contents) == 1 and contents[0].name == ".gitkeep"):
                   if dry_run:
                       console.print(f"  [dim]Would remove: {lane}/ directory[/dim]")
                   else:
                       # Remove .gitkeep if present
                       gitkeep = lane_dir / ".gitkeep"
                       if gitkeep.exists():
                           gitkeep.unlink()
                       lane_dir.rmdir()
                       console.print(f"  [dim]Removed empty: {lane}/ directory[/dim]")
   ```
2. Call at end of `migrate_feature()`

**Files**: `src/specify_cli/commands/upgrade.py` (MODIFY)

**Parallel?**: No, final step

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Data loss during migration | Idempotent design; recommend git commit before |
| Partial migration on failure | Transaction-like processing; clear error reporting |
| Worktree sync issues | Process all locations in single operation |
| File permission errors | Clear error messages; don't continue on failure |

## Definition of Done Checklist

- [ ] `spec-kitty upgrade` command created and registered
- [ ] Scans both `kitty-specs/` and `.worktrees/*/kitty-specs/`
- [ ] Moves WP files from `tasks/{lane}/` to `tasks/`
- [ ] Sets `lane:` frontmatter from source directory
- [ ] Displays warning and requires confirmation (unless --force)
- [ ] --dry-run shows changes without modifying files
- [ ] Idempotent - safe to run multiple times
- [ ] Cleans up empty lane subdirectories
- [ ] Handles up to 100 WP files across all features

## Review Guidance

- Test with --dry-run first to verify detection
- Test on project with both main and worktree features
- Verify lane field is correctly set from directory
- Confirm idempotency by running twice
- Check empty directories are removed
