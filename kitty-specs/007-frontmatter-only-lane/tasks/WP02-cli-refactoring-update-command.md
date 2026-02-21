---
work_package_id: WP02
title: CLI Refactoring - Update Command
lane: done
history:
- timestamp: '2025-12-17T13:15:00Z'
  lane: planned
  agent: system
  shell_pid: $$
  action: Prompt generated via /spec-kitty.tasks
activity_log: |-
  - 2025-12-17T13:15:00Z – system – lane=planned – Prompt created
  - 2025-12-17T14:05:00Z – claude-reviewer – shell_pid=$$ – lane=done – Approved: implementation verified
agent: claude-reviewer
assignee: ''
phase: Phase 1 - Core Implementation
review_status: ''
reviewed_by: claude-reviewer
shell_pid: $$
subtasks:
- T005
- T006
- T007
- T008
- T009
- T010
- T011
---

# Work Package Prompt: WP02 – CLI Refactoring - Update Command

## Objectives & Success Criteria

Refactor the tasks CLI from directory-based to frontmatter-only lane management:

1. Rename `move` command to `update` (semantic clarity - no files move)
2. Remove all file movement operations from lane transitions
3. Update `locate_work_package()` to search flat `tasks/` directory
4. Ensure the `lane:` frontmatter field is the single source of truth

**Success Criteria** (from spec FR-001 to FR-005):
spec-kitty agent workflow implement WP01

- File stays in `tasks/` directory after lane transition
- Activity log is appended on lane change
- Direct editing of `lane:` field is valid and recognized by system

## Context & Constraints

**Reference Documents**:

- Plan: `kitty-specs/007-frontmatter-only-lane/plan.md` (Files to Modify section)
- Spec: `kitty-specs/007-frontmatter-only-lane/spec.md` (User Story 1)
- Research: `kitty-specs/007-frontmatter-only-lane/research.md` (Codebase Analysis)

**Key Files** (from research):

- `scripts/tasks/tasks_cli.py` - Main CLI, ~897 lines
- `scripts/tasks/task_helpers.py` - WP location, frontmatter utilities
- `src/specify_cli/tasks_support.py` - Duplicate helper functions
- `src/specify_cli/task_metadata_validation.py` - Lane mismatch detection

**Dependencies**: WP01 must be complete (legacy detection, lane utilities)

## Subtasks & Detailed Guidance

### Subtask T005 – Rename move_command() to update_command()

**Purpose**: Semantic clarity - command updates metadata, doesn't move files.

**Steps**:

1. Open `scripts/tasks/tasks_cli.py`
2. Find `move_command()` function (around line 142-301)
3. Rename function to `update_command()`
4. Update CLI registration:

   ```python
   # Change from:
   @app.command("move")
   def move_command(...):
   # To:
   @app.command("update")
   def update_command(...):
   ```

5. Update all internal references to `move_command` → `update_command`
6. Update docstring and help text to reflect metadata-only change

**Files**: `scripts/tasks/tasks_cli.py` (MODIFY)

**Parallel?**: No, this is the core change

### Subtask T006 – Refactor stage_move() to stage_update()

**Purpose**: Remove file movement, keep only frontmatter updates.

**Steps**:

1. Find `stage_move()` function (around line 51-87)
2. Rename to `stage_update()`
3. Remove file movement logic:

   ```python
   # REMOVE these lines:
   target_dir = repo_root / "kitty-specs" / wp.feature / "tasks" / target_lane
   target_dir.mkdir(parents=True, exist_ok=True)
   target = target_dir / wp.path.name
   shutil.move(str(wp.path), str(target))
   ```

4. Keep frontmatter update logic:

   ```python
   wp.frontmatter = set_scalar(wp.frontmatter, "lane", target_lane)
   ```

5. Keep activity log append
6. Update git staging to stage modified file (not moved file):

   ```python
   # Change from staging old and new paths to just current path
   subprocess.run(["git", "add", str(wp.path)], cwd=repo_root, check=True)
   ```

7. Update function signature and docstring

**Files**: `scripts/tasks/tasks_cli.py` (MODIFY)

**Parallel?**: No, depends on T005

### Subtask T007 – Update locate_work_package() in task_helpers.py

**Purpose**: Search flat `tasks/` directory instead of lane subdirectories.

**Steps**:

1. Open `scripts/tasks/task_helpers.py`
2. Find `locate_work_package()` function (around line 289-328)
3. Replace directory iteration logic:

   ```python
   # OLD (remove):
   for subdir in tasks_root.iterdir():
       if subdir.is_dir() and subdir.name in LANES:
           for wp_file in subdir.glob("WP*.md"):
               ...

   # NEW:
   def locate_work_package(feature: str, wp_id: str, repo_root: Path) -> Optional[WorkPackage]:
       """Locate a work package by ID in flat tasks/ directory."""
       tasks_dir = repo_root / "kitty-specs" / feature / "tasks"
       if not tasks_dir.exists():
           return None

       # Search flat directory for WP files
       for wp_file in tasks_dir.glob("WP*.md"):
           content = wp_file.read_text()
           frontmatter, body = split_frontmatter(content)
           if frontmatter.get("work_package_id") == wp_id:
               lane = get_lane_from_frontmatter(wp_file)
               return WorkPackage(
                   path=wp_file,
                   feature=feature,
                   wp_id=wp_id,
                   lane=lane,
                   frontmatter=frontmatter,
                   body=body
               )
       return None
   ```

4. Use `get_lane_from_frontmatter()` from WP01 to get lane

**Files**: `scripts/tasks/task_helpers.py` (MODIFY)

**Parallel?**: No, core refactoring

### Subtask T008 – Update locate_work_package() in tasks_support.py

**Purpose**: Keep duplicate function in sync.

**Steps**:

1. Open `src/specify_cli/tasks_support.py`
2. Find `locate_work_package()` function (around line 246-281)
3. Apply same changes as T007

**Files**: `src/specify_cli/tasks_support.py` (MODIFY)

**Parallel?**: Yes, same changes as T007

### Subtask T009 – Remove/repurpose detect_lane_mismatch()

**Purpose**: This function detects directory/frontmatter mismatch, which won't exist in new system.

**Steps**:

1. Open `src/specify_cli/task_metadata_validation.py`
2. Find `detect_lane_mismatch()` function (around line 34-76)
3. Options:
   - **Option A (Recommended)**: Remove function entirely and its callers
   - **Option B**: Repurpose to validate lane field exists and is valid
4. If Option A: Find and remove calls to `detect_lane_mismatch()`
5. Also review `repair_lane_mismatch()` (line 79-169) - remove if no longer needed
6. Review `scan_all_tasks_for_mismatches()` (line 234-274) - remove or simplify

**Files**: `src/specify_cli/task_metadata_validation.py` (MODIFY - possibly remove functions)

**Parallel?**: Yes, independent of T007/T008

### Subtask T010 – Update list_command() for flat structure

**Purpose**: List command should scan flat `tasks/` and group by frontmatter lane.

**Steps**:

1. Find `list_command()` function (around line 338-403)
2. Update scanning logic:

   ```python
   # OLD: Iterate through lane directories
   # NEW: Scan flat tasks/ and group by frontmatter
   def list_command(feature: str, ...):
       tasks_dir = repo_root / "kitty-specs" / feature / "tasks"

       # Group WPs by lane from frontmatter
       wps_by_lane = {lane: [] for lane in LANES}

       for wp_file in tasks_dir.glob("WP*.md"):
           content = wp_file.read_text()
           frontmatter, _ = split_frontmatter(content)
           lane = get_lane_from_frontmatter(wp_file)
           wp_id = frontmatter.get("work_package_id", wp_file.stem)
           wps_by_lane[lane].append((wp_id, wp_file.name))

       # Display grouped by lane
       for lane in LANES:
           console.print(f"[bold]{lane.upper()}[/bold]")
           for wp_id, filename in sorted(wps_by_lane[lane]):
               console.print(f"  {wp_id}: {filename}")
   ```

**Files**: `scripts/tasks/tasks_cli.py` (MODIFY)

**Parallel?**: No, depends on T007

### Subtask T011 – Add legacy format check to CLI entry points

**Purpose**: Warn users when running commands on old-format projects.

**Steps**:

1. Import `is_legacy_format` from `src/specify_cli/legacy_detector.py`
2. Add check at start of main commands:

   ```python
   def _check_legacy_format(feature: str, repo_root: Path):
       """Warn if feature uses legacy directory-based lanes."""
       feature_path = repo_root / "kitty-specs" / feature
       if is_legacy_format(feature_path):
           console.print(
               "[yellow]Warning: Legacy directory-based lanes detected.[/yellow]\n"
               "[yellow]Run `spec-kitty upgrade` to migrate to frontmatter-only lanes.[/yellow]"
           )
   ```

3. Call at start of `update_command()`, `list_command()`, `status_command()`
4. Warning should not block execution

**Files**: `scripts/tasks/tasks_cli.py` (MODIFY)

**Parallel?**: No, depends on WP01

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking `rollback` command | Update rollback to use frontmatter-only approach |
| History command depends on move | Verify history_command() still works (append only) |
| Git staging broken after move removal | Test git add on modified file path |
| Existing users expect `move` command | Clean break is intentional; document in release notes |

## Definition of Done Checklist

- [ ] `move` command renamed to `update` in CLI
- [ ] `stage_move()` renamed to `stage_update()` with file movement removed
- [ ] `locate_work_package()` searches flat `tasks/` directory (both files)
- [ ] `detect_lane_mismatch()` removed or repurposed
- [ ] `list_command()` groups WPs by frontmatter lane
- [ ] Legacy format warning added to CLI entry points
- [ ] Activity log still appended on lane changes
- [ ] Git staging works correctly for frontmatter-only changes
- [ ] No file movement occurs during lane transitions

## Review Guidance

- Verify `tasks_cli.py update <feature> <wp> <lane>` works without moving files (historical - later became `spec-kitty agent workflow` commands)
- Check that lane field updates correctly in frontmatter
- Verify activity log is appended
- Test with both new format (flat) and ensure legacy warning appears for old format
- Check rollback_command() still functions correctly
