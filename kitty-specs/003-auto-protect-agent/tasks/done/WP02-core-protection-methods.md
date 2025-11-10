---
work_package_id: "WP02"
subtasks:
  - "T008"
  - "T009"
  - "T010"
  - "T011"
  - "T012"
  - "T013"
  - "T014"
  - "T015"
title: "Core Protection Methods"
phase: "Phase 2 - Core Implementation"
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
  - timestamp: "2025-11-10T11:05:00Z"
    lane: "doing"
    agent: "claude"
    shell_pid: "61538"
    action: "Started implementation of core protection methods"
  - timestamp: "2025-11-10T11:15:00Z"
    lane: "for_review"
    agent: "claude"
    shell_pid: "61538"
    action: "Completed WP02 - Ready for review"
---
*Path: [tasks/planned/WP02-core-protection-methods.md](tasks/planned/WP02-core-protection-methods.md)*

# Work Package Prompt: WP02 – Core Protection Methods

## Objectives & Success Criteria

- Implement the two main protection methods: `protect_all_agents()` and `protect_selected_agents()`
- Successfully protect agent directories in .gitignore without duplicates
- Handle file creation, permission errors, and special cases gracefully
- Return detailed results via ProtectionResult for user feedback

## Context & Constraints

- **Prerequisites**: WP01 must be complete (GitignoreManager class exists)
- **Related Documents**:
  - Specification: `kitty-specs/003-auto-protect-agent/spec.md` (User stories and requirements)
  - Data model: `kitty-specs/003-auto-protect-agent/data-model.md` (ProtectionResult structure)
  - Research: `kitty-specs/003-auto-protect-agent/research.md` (Technical decisions)
- **Key Requirement**: Must protect ALL agent directories, not just selected ones (per User Story 3)
- **Constraint**: Must preserve existing .gitignore content and formatting

## Subtasks & Detailed Guidance

### Subtask T008 – Implement protect_all_agents() method
- **Purpose**: Add all known agent directories to .gitignore
- **Steps**:
  1. Create method `def protect_all_agents(self) -> ProtectionResult`
  2. Get all directories from AGENT_DIRECTORIES registry
  3. Extract directory paths into a list
  4. Call self.ensure_entries() with all directories
  5. Track which entries were added vs skipped
  6. Build and return ProtectionResult with details
- **Files**: `src/specify_cli/gitignore_manager.py`
- **Parallel?**: No (core functionality)
- **Notes**: This is the primary method used during spec-kitty init

### Subtask T009 – Implement protect_selected_agents() method
- **Purpose**: Add specific agent directories based on selection
- **Steps**:
  1. Create method `def protect_selected_agents(self, agents: List[str]) -> ProtectionResult`
  2. Map agent names to their directories using registry
  3. Handle unknown agent names gracefully (add to warnings)
  4. Call self.ensure_entries() with selected directories
  5. Build and return ProtectionResult
- **Files**: `src/specify_cli/gitignore_manager.py`
- **Parallel?**: No (depends on T008 patterns)
- **Notes**: May not be used initially, but needed for completeness

### Subtask T010 – Add duplicate detection logic
- **Purpose**: Avoid adding entries that already exist in .gitignore
- **Steps**:
  1. In ensure_entries method, read existing lines into a set
  2. Check each new entry against the set before adding
  3. Track skipped entries for reporting
  4. Ensure marker comment isn't duplicated either
- **Files**: `src/specify_cli/gitignore_manager.py`
- **Parallel?**: No (modifies core logic)
- **Notes**: Set operations provide O(1) lookup performance

### Subtask T011 – Implement marker comment system
- **Purpose**: Mark auto-managed sections for clarity
- **Steps**:
  1. Define marker as "# Added by Spec Kitty CLI (auto-managed)"
  2. Check if marker already exists in file
  3. If not present, add marker before first managed entry
  4. Group all managed entries after the marker
  5. Add blank line before marker for readability
- **Files**: `src/specify_cli/gitignore_manager.py`
- **Parallel?**: No (core functionality)
- **Notes**: Preserve existing marker if found

### Subtask T012 – Add .gitignore file creation
- **Purpose**: Handle case where .gitignore doesn't exist
- **Steps**:
  1. Check if self.gitignore_path exists
  2. If not, create empty file with proper permissions
  3. Set appropriate line ending for platform
  4. Continue with normal entry addition
- **Files**: `src/specify_cli/gitignore_manager.py`
- **Parallel?**: No (core functionality)
- **Notes**: Use Path.touch() for creation

### Subtask T013 – Implement result reporting
- **Purpose**: Provide detailed feedback about operations
- **Steps**:
  1. Track all operations during protection
  2. Count entries added vs skipped
  3. Collect any errors or warnings
  4. Populate ProtectionResult dataclass
  5. Include success/failure status
  6. Add method to format result for console output
- **Files**: `src/specify_cli/gitignore_manager.py`
- **Parallel?**: No (integrated with other tasks)
- **Notes**: Be specific about what was done

### Subtask T014 – Special .github/ directory handling
- **Purpose**: Add warning about dual use with GitHub Actions
- **Steps**:
  1. Check if entry being added is `.github/`
  2. Add special comment: "# Note: .github/ also used by GitHub Actions - review before committing"
  3. Place comment on same line or immediately after
  4. Add to warnings in ProtectionResult
  5. Ensure comment is preserved on subsequent runs
- **Files**: `src/specify_cli/gitignore_manager.py`
- **Parallel?**: Yes (after core logic complete)
- **Notes**: This addresses edge case from specification

### Subtask T015 – Permission error handling
- **Purpose**: Handle read-only files gracefully
- **Steps**:
  1. Wrap file operations in try-except blocks
  2. Catch PermissionError specifically
  3. Add clear error message: "Cannot update .gitignore: Permission denied. Run: chmod u+w .gitignore"
  4. Return failure in ProtectionResult with error details
  5. Don't crash the entire init process
- **Files**: `src/specify_cli/gitignore_manager.py`
- **Parallel?**: Yes (after core logic complete)
- **Notes**: User guidance is critical for resolution

## Risks & Mitigations

- **Risk**: File corruption during write operations
  - **Mitigation**: Write to temporary file first, then rename atomically
- **Risk**: Race condition if multiple processes modify .gitignore
  - **Mitigation**: Use file locking or accept last-write-wins
- **Risk**: Large .gitignore files causing performance issues
  - **Mitigation**: Use set operations for O(1) duplicate detection

## Definition of Done Checklist

- [ ] All subtasks completed and validated
- [ ] protect_all_agents() successfully adds all 12 directories
- [ ] protect_selected_agents() works with subset of agents
- [ ] Duplicate entries are never created
- [ ] .gitignore is created if it doesn't exist
- [ ] Permission errors are handled gracefully
- [ ] .github/ directory has special warning comment
- [ ] ProtectionResult accurately reports all operations
- [ ] Existing .gitignore content is preserved

## Review Guidance

- Test with various .gitignore states: non-existent, empty, populated
- Verify duplicate detection works correctly
- Check that marker comments are properly managed
- Ensure error messages are helpful and actionable
- Validate that all 12 agent directories are protected
- Test permission error handling on read-only files

## Activity Log

- 2025-11-10T10:00:00Z – system – lane=planned – Prompt created.
- 2025-11-10T11:05:00Z – claude – shell_pid=61538 – lane=doing – Started implementation
- 2025-11-10T11:15:00Z – claude – shell_pid=61538 – lane=doing – Completed all 8 subtasks (T008-T015)
- 2025-11-10T12:05:00Z – claude – shell_pid=62660 – lane=done – Approved: All 8 subtasks verified, core methods functioning correctly
- 2025-11-10T08:59:49Z – claude – shell_pid=62660 – lane=done – Approved for release
