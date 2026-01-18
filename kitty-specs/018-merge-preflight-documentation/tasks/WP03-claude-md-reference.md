---
work_package_id: "WP03"
subtasks:
  - "T018"
  - "T019"
  - "T020"
  - "T021"
  - "T022"
  - "T023"
  - "T024"
title: "CLAUDE.md Reference Update"
phase: "Phase 2 - Developer Documentation"
lane: "doing"
assignee: ""
agent: "codex"
shell_pid: "56874"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-18T13:21:55Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 – CLAUDE.md Reference Update

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback, update `review_status: acknowledged`.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

Add "Merge & Preflight Patterns" section to CLAUDE.md for developers and AI agents contributing to spec-kitty.

**Success Criteria:**
- A contributor can use CLAUDE.md to understand merge state management without reading source code
- Merge state JSON structure is documented with example
- Pre-flight validation integration points are clear
- Programmatic access code examples are copy-pasteable and functional

## Context & Constraints

**Source Files:**
- `src/specify_cli/merge/state.py` - MergeState dataclass
- `src/specify_cli/merge/preflight.py` - PreflightResult, WPStatus
- `src/specify_cli/merge/__init__.py` - Public API exports

**Location in CLAUDE.md:** After "Workspace-per-Work-Package Development (0.11.0+)" section

**Output Location:** `CLAUDE.md` (add new section)

## Subtasks & Detailed Guidance

### Subtask T018 – Extract MergeState dataclass fields
- **Purpose**: Document state persistence structure
- **Steps**:
  1. Read `src/specify_cli/merge/state.py`
  2. Extract MergeState fields:
     - feature_slug: str
     - target_branch: str
     - wp_order: list[str]
     - completed_wps: list[str]
     - current_wp: str | None
     - has_pending_conflicts: bool
     - strategy: str
     - started_at: str
     - updated_at: str
  3. Note helper methods: remaining_wps, progress_percent, mark_wp_complete, etc.
- **Files**: `src/specify_cli/merge/state.py`
- **Parallel?**: Yes

### Subtask T019 – Extract PreflightResult structure
- **Purpose**: Document validation result format
- **Steps**:
  1. Read `src/specify_cli/merge/preflight.py`
  2. Extract PreflightResult fields:
     - passed: bool
     - wp_statuses: list[WPStatus]
     - errors: list[str]
     - warnings: list[str]
  3. Extract WPStatus fields:
     - wp_id: str
     - worktree_path: Path
     - branch_name: str
     - is_clean: bool
     - error: str | None
- **Files**: `src/specify_cli/merge/preflight.py`
- **Parallel?**: Yes

### Subtask T020 – Extract key function signatures
- **Purpose**: Document public API
- **Steps**:
  1. Read `src/specify_cli/merge/__init__.py` for exports
  2. Document key functions:
     - `save_state(state, repo_root)` - Persist merge state
     - `load_state(repo_root)` - Load merge state
     - `clear_state(repo_root)` - Remove state file
     - `has_active_merge(repo_root)` - Check for in-progress merge
     - `run_preflight(...)` - Run validation
  3. Note module paths for imports
- **Files**: `src/specify_cli/merge/__init__.py`, individual modules
- **Parallel?**: Yes

### Subtask T021 – Write CLAUDE.md section structure
- **Purpose**: Establish section skeleton in CLAUDE.md
- **Steps**:
  1. Find "Workspace-per-Work-Package Development (0.11.0+)" section in CLAUDE.md
  2. Add new section after it: "### Merge & Preflight Patterns (0.11.0+)"
  3. Add subsection headers:
     - **Merge State Persistence**
     - **Pre-flight Validation**
     - **Programmatic Access**
     - **Common Patterns**
- **Files**: `CLAUDE.md`
- **Parallel?**: No (must complete before T022-T024)

### Subtask T022 – Merge state persistence subsection
- **Purpose**: Document state file usage
- **Steps**:
  1. Add content to "Merge State Persistence" subsection
  2. Document:
     - Location: `.kittify/merge-state.json`
     - When created: First WP merge starts
     - When cleared: All WPs merged successfully
     - Structure: Show JSON example with all fields
  3. Include functions: save_state(), load_state(), clear_state(), has_active_merge()
- **Files**: `CLAUDE.md`
- **Parallel?**: Yes (after T021)
- **Example JSON**:
  ```json
  {
    "feature_slug": "017-feature-name",
    "target_branch": "main",
    "wp_order": ["WP01", "WP02", "WP03"],
    "completed_wps": ["WP01"],
    "current_wp": "WP02",
    "has_pending_conflicts": false,
    "strategy": "merge",
    "started_at": "2026-01-18T10:00:00Z",
    "updated_at": "2026-01-18T10:30:00Z"
  }
  ```

### Subtask T023 – Pre-flight validation subsection
- **Purpose**: Document validation integration
- **Steps**:
  1. Add content to "Pre-flight Validation" subsection
  2. Document:
     - Entry point: `run_preflight()` in `merge/preflight.py`
     - Returns: PreflightResult with passed/failed, WP statuses, errors
     - Checks performed: dirty worktrees, missing worktrees, branch existence
  3. Show how merge command uses preflight
- **Files**: `CLAUDE.md`
- **Parallel?**: Yes (after T021)

### Subtask T024 – Programmatic access code examples
- **Purpose**: Enable contributors to work with merge state
- **Steps**:
  1. Add content to "Programmatic Access" subsection
  2. Include code examples:
     ```python
     from specify_cli.merge import load_state, save_state, has_active_merge

     # Check for active merge
     if has_active_merge(repo_root):
         state = load_state(repo_root)
         print(f"Merge in progress: {state.feature_slug}")
         print(f"Progress: {len(state.completed_wps)}/{len(state.wp_order)}")
     ```
  3. Add example for preflight:
     ```python
     from specify_cli.merge import run_preflight

     result = run_preflight(feature_slug, target_branch, repo_root, wp_workspaces)
     if not result.passed:
         for error in result.errors:
             print(f"Error: {error}")
     ```
- **Files**: `CLAUDE.md`
- **Parallel?**: Yes (after T021)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Code examples break | Test all examples before committing |
| Import paths change | Use __init__.py exports, not internal modules |
| Section placement wrong | Explicitly anchor to "Workspace-per-WP" section |

## Definition of Done Checklist

- [ ] All subtasks completed
- [ ] "Merge & Preflight Patterns" section added to CLAUDE.md
- [ ] Merge state JSON structure documented with example
- [ ] PreflightResult structure documented
- [ ] Code examples are copy-pasteable
- [ ] Code examples tested and working
- [ ] Section placed after "Workspace-per-Work-Package Development"

## Review Guidance

1. Verify MergeState fields match state.py exactly
2. Verify PreflightResult fields match preflight.py exactly
3. Test all code examples in Python REPL
4. Check section placement in CLAUDE.md

## Activity Log

- 2026-01-18T13:21:55Z – system – lane=planned – Prompt created.
- 2026-01-18T13:28:04Z – codex – shell_pid=56874 – lane=doing – Started review via workflow command
