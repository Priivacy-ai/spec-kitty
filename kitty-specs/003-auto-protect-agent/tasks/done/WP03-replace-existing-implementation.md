---
work_package_id: "WP03"
subtasks:
  - "T016"
  - "T017"
  - "T018"
  - "T019"
  - "T020"
  - "T021"
  - "T022"
title: "Replace Existing Implementation"
phase: "Phase 3 - Integration"
lane: "done"
assignee: "claude"
agent: "claude"
shell_pid: "62660"
history:
  - timestamp: "2025-11-10T10:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
  - timestamp: "2025-11-10T11:20:00Z"
    lane: "doing"
    agent: "claude"
    shell_pid: "61538"
    action: "Started replacing existing implementation"
  - timestamp: "2025-11-10T11:35:00Z"
    lane: "for_review"
    agent: "claude"
    shell_pid: "61538"
    action: "Completed WP03 - Ready for review"
---
*Path: [tasks/planned/WP03-replace-existing-implementation.md](tasks/planned/WP03-replace-existing-implementation.md)*

# Work Package Prompt: WP03 – Replace Existing Implementation

## Objectives & Success Criteria

- Completely replace the old `handle_codex_security` function with GitignoreManager
- Integrate GitignoreManager into the spec-kitty init flow
- Ensure ALL agent directories are protected (not just selected ones)
- Remove obsolete functions after verification
- Maintain consistent user experience with improved functionality

## Context & Constraints

- **Prerequisites**: WP02 must be complete (protection methods implemented)
- **Related Documents**:
  - Current implementation: `src/specify_cli/__init__.py` (lines 729-780, 689-726)
  - Plan: `kitty-specs/003-auto-protect-agent/plan.md` (Internal Refactoring section)
  - Specification: `kitty-specs/003-auto-protect-agent/spec.md` (User Story 3)
- **Critical Decision**: Direct replacement without backward compatibility wrapper
- **Constraint**: Must not break the init flow at any point

## Subtasks & Detailed Guidance

### Subtask T016 – Import GitignoreManager in __init__.py
- **Purpose**: Make GitignoreManager available in the main module
- **Steps**:
  1. Open `src/specify_cli/__init__.py`
  2. Add import at top with other imports: `from .gitignore_manager import GitignoreManager, ProtectionResult`
  3. Verify no import errors occur
  4. Keep existing imports for now (will remove later)
- **Files**: `src/specify_cli/__init__.py`
- **Parallel?**: No (must be first)
- **Notes**: Place with other internal imports

### Subtask T017 – Replace handle_codex_security call
- **Purpose**: Use GitignoreManager instead of old function
- **Steps**:
  1. Find where `handle_codex_security` is called (around line 1700-1900)
  2. Replace with:
     ```python
     manager = GitignoreManager(project_path)
     result = manager.protect_all_agents()  # Note: ALL agents, not just selected
     ```
  3. Remove the `selected_agents` parameter usage (we protect all)
  4. Keep the console variable for output
- **Files**: `src/specify_cli/__init__.py`
- **Parallel?**: No (depends on T016)
- **Notes**: Critical change - protect ALL directories per User Story 3

### Subtask T018 – Update console output
- **Purpose**: Show user which directories were protected
- **Steps**:
  1. After GitignoreManager call, check result.modified
  2. If modified, display: `[cyan]Updated .gitignore to exclude AI agent directories:[/cyan]`
  3. List each entry in result.entries_added with bullet points
  4. If result.entries_skipped has items, show count: "({n} already protected)"
  5. Display any warnings (especially for .github/)
  6. Show errors in red if any occurred
- **Files**: `src/specify_cli/__init__.py`
- **Parallel?**: No (depends on T017)
- **Notes**: Use Rich console formatting consistently

### Subtask T019 – Remove handle_codex_security function
- **Purpose**: Clean up obsolete code
- **Steps**:
  1. Locate `handle_codex_security` function definition (line 729)
  2. Delete the entire function (lines 729-780)
  3. Remove any docstring or comments related to it
  4. Verify no other references exist (use grep/search)
- **Files**: `src/specify_cli/__init__.py`
- **Parallel?**: No (after T017 verified working)
- **Notes**: Only remove after testing new implementation

### Subtask T020 – Remove ensure_gitignore_entries function
- **Purpose**: Remove migrated functionality
- **Steps**:
  1. Locate `ensure_gitignore_entries` function (line 689)
  2. Verify it's not called elsewhere (should only be from handle_codex_security)
  3. Delete the entire function (lines 689-726)
  4. Remove related imports if any become unused
- **Files**: `src/specify_cli/__init__.py`
- **Parallel?**: No (after T019)
- **Notes**: This code now lives in GitignoreManager

### Subtask T021 – Update remaining references
- **Purpose**: Ensure no broken references remain
- **Steps**:
  1. Search entire codebase for "handle_codex_security"
  2. Search for "ensure_gitignore_entries"
  3. Check for any comments mentioning these functions
  4. Update or remove any found references
  5. Check test files especially
- **Files**: Various (as found)
- **Parallel?**: No (cleanup task)
- **Notes**: Use grep -r or IDE global search

### Subtask T022 – Verify init flow end-to-end
- **Purpose**: Ensure everything works correctly
- **Steps**:
  1. Create a test directory without .gitignore
  2. Run `spec-kitty init` and select some agents
  3. Verify .gitignore is created with ALL agent directories
  4. Run init again and verify no duplicates
  5. Test with existing .gitignore containing some entries
  6. Test with read-only .gitignore for error handling
  7. Verify console output is clear and informative
- **Files**: N/A (testing task)
- **Parallel?**: No (final verification)
- **Notes**: Document any issues found

## Risks & Mitigations

- **Risk**: Breaking the init flow during refactoring
  - **Mitigation**: Test after each change, keep backup of working code
- **Risk**: Missing references to old functions
  - **Mitigation**: Use comprehensive search across entire codebase
- **Risk**: Different behavior confusing users
  - **Mitigation**: Clear console output explaining what was protected

## Definition of Done Checklist

- [ ] All subtasks completed and validated
- [ ] GitignoreManager successfully integrated into init flow
- [ ] ALL agent directories are protected (not just selected ones)
- [ ] Old functions completely removed
- [ ] No references to old functions remain
- [ ] Console output clearly shows protected directories
- [ ] Init flow works for new and existing projects
- [ ] Error handling works for permission issues
- [ ] No regression in functionality

## Review Guidance

- Run spec-kitty init in various scenarios
- Check that all 12 agent directories appear in .gitignore
- Verify old functions are completely removed
- Ensure no import errors or missing references
- Validate console output is user-friendly
- Test error cases (permissions, corruption)
- Confirm no duplicate entries are created

## Activity Log

- 2025-11-10T10:00:00Z – system – lane=planned – Prompt created.
- 2025-11-10T11:20:00Z – claude – shell_pid=61538 – lane=doing – Started replacing existing implementation
- 2025-11-10T11:35:00Z – claude – shell_pid=61538 – lane=doing – Completed all 7 subtasks (T016-T022)
- 2025-11-10T12:10:00Z – claude – shell_pid=62660 – lane=done – Approved: All 7 subtasks verified, integration successful, old functions removed
- 2025-11-10T09:01:23Z – claude – shell_pid=62660 – lane=done – Approved for release
