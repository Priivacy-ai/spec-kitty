---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
  - "T006"
  - "T007"
title: "Create GitignoreManager Module"
phase: "Phase 1 - Foundation"
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
  - timestamp: "2025-11-10T10:45:00Z"
    lane: "doing"
    agent: "claude"
    shell_pid: "61538"
    action: "Started implementation of GitignoreManager module"
  - timestamp: "2025-11-10T11:00:00Z"
    lane: "for_review"
    agent: "claude"
    shell_pid: "61538"
    action: "Completed WP01 - Ready for review"
---
*Path: [tasks/planned/WP01-create-gitignore-manager.md](tasks/planned/WP01-create-gitignore-manager.md)*

# Work Package Prompt: WP01 – Create GitignoreManager Module

## Objectives & Success Criteria

- Create a new `GitignoreManager` class in a separate module within the specify_cli package
- Successfully migrate existing gitignore functionality into a clean, object-oriented design
- Define comprehensive agent directory registry covering all 12 known AI agents
- Ensure the module can be imported and instantiated without errors

## Context & Constraints

- **Prerequisites**: None (this is the foundational work package)
- **Related Documents**:
  - Implementation plan: `kitty-specs/003-auto-protect-agent/plan.md`
  - Data model: `kitty-specs/003-auto-protect-agent/data-model.md`
  - Research decisions: `kitty-specs/003-auto-protect-agent/research.md`
- **Key Decision**: Refactoring into comprehensive GitignoreManager system (not extending existing functions)
- **Constraint**: Must use pathlib for all path operations (cross-platform compatibility)

## Subtasks & Detailed Guidance

### Subtask T001 – Create gitignore_manager.py with class skeleton
- **Purpose**: Establish the new module structure for GitignoreManager
- **Steps**:
  1. Create new file `src/specify_cli/gitignore_manager.py`
  2. Add module docstring explaining purpose
  3. Import necessary dependencies: `from pathlib import Path`, `from dataclasses import dataclass`, `from typing import List, Optional, Set`
  4. Create empty GitignoreManager class with docstring
- **Files**: `src/specify_cli/gitignore_manager.py` (create new)
- **Parallel?**: No (must be first)
- **Notes**: Follow existing code style in specify_cli package

### Subtask T002 – Define AGENT_DIRECTORIES registry
- **Purpose**: Create centralized registry of all AI agent directories
- **Steps**:
  1. Inside gitignore_manager.py, create AGENT_DIRECTORIES constant
  2. Include all 12 directories: `.claude/`, `.codex/`, `.opencode/`, `.windsurf/`, `.gemini/`, `.cursor/`, `.qwen/`, `.kilocode/`, `.augment/`, `.github/`, `.roo/`, `.amazonq/`
  3. Use a list of AgentDirectory objects (to be defined in T004)
  4. Add comment for `.github/` about dual use with GitHub Actions
- **Files**: `src/specify_cli/gitignore_manager.py`
- **Parallel?**: No (depends on T001)
- **Notes**: All directories must have trailing slash

### Subtask T003 – Implement GitignoreManager.__init__ with validation
- **Purpose**: Initialize GitignoreManager with project path validation
- **Steps**:
  1. Add `__init__` method accepting `project_path: Path` parameter
  2. Validate that project_path exists and is a directory
  3. Store project_path as instance variable
  4. Calculate and store gitignore_path as `project_path / ".gitignore"`
  5. Set marker comment as "# Added by Spec Kitty CLI (auto-managed)"
- **Files**: `src/specify_cli/gitignore_manager.py`
- **Parallel?**: No (depends on T001)
- **Notes**: Raise ValueError if project_path is invalid

### Subtask T004 – Create data classes
- **Purpose**: Define structured data types for the system
- **Steps**:
  1. Create `@dataclass` AgentDirectory with fields: name (str), directory (str), is_special (bool), description (str)
  2. Create `@dataclass` ProtectionResult with fields: success (bool), modified (bool), entries_added (List[str]), entries_skipped (List[str]), errors (List[str]), warnings (List[str])
  3. Add type hints and docstrings for all fields
- **Files**: `src/specify_cli/gitignore_manager.py`
- **Parallel?**: No (needed by T002)
- **Notes**: Place data classes before GitignoreManager class

### Subtask T005 – Migrate ensure_gitignore_entries logic
- **Purpose**: Port existing functionality into GitignoreManager.ensure_entries
- **Steps**:
  1. Copy logic from existing `ensure_gitignore_entries` function (src/specify_cli/__init__.py:689-726)
  2. Adapt to use instance variables (self.gitignore_path, self.marker)
  3. Create method signature: `def ensure_entries(self, entries: List[str]) -> bool`
  4. Maintain existing behavior: read file, detect duplicates, add new entries, preserve formatting
  5. Keep the marker comment system intact
- **Files**: `src/specify_cli/gitignore_manager.py`
- **Parallel?**: Yes (once T003 complete)
- **Notes**: Reference existing tests to ensure compatibility

### Subtask T006 – Add line ending detection and preservation
- **Purpose**: Ensure cross-platform compatibility
- **Steps**:
  1. Create helper method `_detect_line_ending(self, content: str) -> str`
  2. Check for '\r\n' (Windows) vs '\n' (Unix/Mac)
  3. Default to system line ending if file is new
  4. Store detected line ending and use consistently
  5. Apply when writing file back
- **Files**: `src/specify_cli/gitignore_manager.py`
- **Parallel?**: Yes (once T003 complete)
- **Notes**: Preserve whatever exists in current file

### Subtask T007 – Implement get_agent_directories class method
- **Purpose**: Provide access to the agent directory registry
- **Steps**:
  1. Add `@classmethod` decorator
  2. Create method `def get_agent_directories(cls) -> List[AgentDirectory]`
  3. Return copy of AGENT_DIRECTORIES list
  4. Add docstring explaining usage
- **Files**: `src/specify_cli/gitignore_manager.py`
- **Parallel?**: No (depends on T002)
- **Notes**: Return copy to prevent external modification

## Risks & Mitigations

- **Risk**: Breaking existing functionality during migration
  - **Mitigation**: Keep original function intact until new implementation is verified
- **Risk**: Path handling differences across operating systems
  - **Mitigation**: Use pathlib exclusively, test on multiple platforms
- **Risk**: Import errors in existing code
  - **Mitigation**: Don't modify imports in __init__.py until WP03

## Definition of Done Checklist

- [ ] All subtasks completed and validated
- [ ] GitignoreManager class can be imported without errors
- [ ] Class can be instantiated with a valid project path
- [ ] ensure_entries method works identically to original
- [ ] Line ending detection works for both Windows and Unix files
- [ ] Agent directory registry contains all 12 directories
- [ ] Code follows existing style guidelines

## Review Guidance

- Verify that the module structure follows Python best practices
- Check that all path operations use pathlib
- Ensure data classes have proper type hints
- Confirm that migrated logic matches original behavior
- Validate that the registry includes all agents from the specification

## Activity Log

- 2025-11-10T10:00:00Z – system – lane=planned – Prompt created.
- 2025-11-10T10:45:00Z – claude – shell_pid=61538 – lane=doing – Started implementation
- 2025-11-10T11:00:00Z – claude – shell_pid=61538 – lane=doing – Completed implementation of GitignoreManager module with all 7 subtasks
- 2025-11-10T12:00:00Z – claude – shell_pid=62660 – lane=done – Approved: All requirements met, module properly structured, 12 agents registered
- 2025-11-10T08:58:42Z – claude – shell_pid=62660 – lane=done – Approved for release
