---
work_package_id: WP01
title: Foundation - Legacy Detection & Shared Utilities
lane: done
history:
- timestamp: '2025-12-17T13:15:00Z'
  lane: planned
  agent: system
  shell_pid: $$
  action: Prompt generated via /spec-kitty.tasks
activity_log: |-
  - 2025-12-17T13:15:00Z – system – lane=planned – Prompt created
  - 2025-12-17T12:11:54Z – claude – shell_pid=63393 – lane=doing – Started implementation
  - 2025-12-17T14:00:00Z – claude-reviewer – shell_pid=$$ – lane=done – Approved: All deliverables met, tests pass
  - 2025-12-17T14:05:00Z – claude-reviewer – shell_pid=$$ – lane=done – Approved: implementation verified
agent: claude-reviewer
assignee: Claude
phase: Phase 0 - Foundation
review_status: ''
reviewed_by: claude-reviewer
shell_pid: $$
subtasks:
- T001
- T002
- T003
- T004
---

# Work Package Prompt: WP01 – Foundation - Legacy Detection & Shared Utilities

## Objectives & Success Criteria

Create the foundation components that all other work packages depend on:
1. Legacy format detection (`is_legacy_format()`) to identify old directory-based structure
2. Shared utility (`get_lane_from_frontmatter()`) to read lane from YAML frontmatter
3. Consolidated LANES constant documentation

**Success Criteria**:
- `is_legacy_format(feature_path)` returns `True` when `tasks/planned/`, `tasks/doing/`, etc. subdirectories contain .md files
- `get_lane_from_frontmatter(wp_path)` correctly extracts `lane:` field from WP frontmatter
- Missing `lane:` field defaults to "planned" with warning logged
- Invalid `lane:` value raises clear error with valid options

## Context & Constraints

**Reference Documents**:
- Plan: `kitty-specs/007-frontmatter-only-lane/plan.md`
- Spec: `kitty-specs/007-frontmatter-only-lane/spec.md`
- Research: `kitty-specs/007-frontmatter-only-lane/research.md`
- Data Model: `kitty-specs/007-frontmatter-only-lane/data-model.md`

**Key Decisions** (from research.md):
- Clean break: No hybrid mode, new format only after migration
- Default lane: "planned" when `lane:` field missing

**Valid Lanes**: `planned`, `doing`, `for_review`, `done`

## Subtasks & Detailed Guidance

### Subtask T001 – Create legacy_detector.py

**Purpose**: Provide a clean function to detect whether a feature uses old directory-based lanes.

**Steps**:
1. Create file `src/specify_cli/legacy_detector.py`
2. Implement `is_legacy_format(feature_path: Path) -> bool`:
   ```python
   def is_legacy_format(feature_path: Path) -> bool:
       """Check if feature uses legacy directory-based lanes.

       Returns True if tasks/{lane}/ subdirectories exist AND contain .md files.
       """
       tasks_dir = feature_path / "tasks"
       if not tasks_dir.exists():
           return False

       lane_dirs = ["planned", "doing", "for_review", "done"]
       for lane in lane_dirs:
           lane_path = tasks_dir / lane
           if lane_path.is_dir():
               # Check if there are any .md files (not just .gitkeep)
               md_files = list(lane_path.glob("*.md"))
               if md_files:
                   return True
       return False
   ```
3. Add docstring explaining detection criteria

**Files**: `src/specify_cli/legacy_detector.py` (NEW)

**Parallel?**: Yes, independent of T002/T003

### Subtask T002 – Add get_lane_from_frontmatter() to task_helpers.py

**Purpose**: Centralize lane extraction from WP frontmatter.

**Steps**:
1. Open `scripts/tasks/task_helpers.py`
2. Add utility function:
   ```python
   def get_lane_from_frontmatter(wp_path: Path, warn_on_missing: bool = True) -> str:
       """Extract lane from WP file frontmatter.

       Args:
           wp_path: Path to the work package markdown file
           warn_on_missing: If True, log warning when lane field is missing

       Returns:
           Lane value (planned, doing, for_review, done)

       Raises:
           ValueError: If lane value is not valid
       """
       content = wp_path.read_text()
       frontmatter, _ = split_frontmatter(content)

       lane = frontmatter.get("lane")

       if lane is None:
           if warn_on_missing:
               console.print(f"[yellow]Warning: {wp_path.name} missing lane field, defaulting to 'planned'[/yellow]")
           return "planned"

       if lane not in LANES:
           raise ValueError(
               f"Invalid lane '{lane}' in {wp_path.name}. "
               f"Valid lanes: {', '.join(LANES)}"
           )

       return lane
   ```
3. Ensure `split_frontmatter()` is available (already exists in file)

**Files**: `scripts/tasks/task_helpers.py` (MODIFY)

**Parallel?**: Yes, can proceed alongside T003

### Subtask T003 – Add get_lane_from_frontmatter() to tasks_support.py

**Purpose**: Keep utility in sync between both helper files.

**Steps**:
1. Open `src/specify_cli/tasks_support.py`
2. Add same `get_lane_from_frontmatter()` function as T002
3. Ensure imports match (Path, LANES, split_frontmatter, console)

**Files**: `src/specify_cli/tasks_support.py` (MODIFY)

**Parallel?**: Yes, same changes as T002

**Note**: Long-term, consider extracting to shared module to avoid duplication.

### Subtask T004 – Document LANES constant location

**Purpose**: Ensure clear source of truth for valid lanes.

**Steps**:
1. Verify LANES is defined in both:
   - `scripts/tasks/task_helpers.py:14`
   - `src/specify_cli/tasks_support.py:14`
2. Add comment to both indicating they must stay in sync:
   ```python
   # IMPORTANT: Keep in sync with src/specify_cli/tasks_support.py (or task_helpers.py)
   LANES: Tuple[str, ...] = ("planned", "doing", "for_review", "done")
   ```
3. Consider future consolidation (out of scope for this WP)

**Files**:
- `scripts/tasks/task_helpers.py` (MODIFY - add comment)
- `src/specify_cli/tasks_support.py` (MODIFY - add comment)

**Parallel?**: No, simple documentation task

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Inconsistent implementations between helper files | Use identical code; add comment noting sync requirement |
| Edge case: tasks/ doesn't exist | Return False for legacy detection; handle gracefully |
| Edge case: lane subdirectory empty except .gitkeep | Check for .md files specifically, not just directory existence |

## Definition of Done Checklist

- [ ] `src/specify_cli/legacy_detector.py` created with `is_legacy_format()` function
- [ ] `get_lane_from_frontmatter()` added to `scripts/tasks/task_helpers.py`
- [ ] `get_lane_from_frontmatter()` added to `src/specify_cli/tasks_support.py`
- [ ] LANES constant documented with sync comments
- [ ] Functions handle missing lane (default to "planned" with warning)
- [ ] Functions raise clear error for invalid lane values
- [ ] Code follows existing style in the files

## Review Guidance

- Verify legacy detection correctly distinguishes old vs new format
- Verify lane extraction handles edge cases (missing, invalid)
- Check warning/error messages are clear and actionable
- Ensure no breaking changes to existing function signatures

## Activity Log

- 2025-12-17T12:11:54Z – claude – shell_pid=63393 – lane=doing – Started implementation
