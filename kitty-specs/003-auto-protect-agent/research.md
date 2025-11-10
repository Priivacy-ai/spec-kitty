# Research: Auto-protect Agent Directories

**Feature**: Auto-protect Agent Directories
**Branch**: 003-auto-protect-agent
**Date**: 2025-11-10

## Executive Summary

This research documents the technical decisions for implementing comprehensive gitignore management that automatically protects all AI agent directories from being committed to git repositories during spec-kitty initialization.

## Key Decisions

### 1. Architecture Approach

**Decision**: Refactor into comprehensive GitignoreManager system

**Rationale**:
- Current implementation has fragmented gitignore handling (separate functions for Codex vs other agents)
- A unified system provides better maintainability and extensibility
- Allows for future gitignore-related features (patterns, exclusions, etc.)

**Alternatives Considered**:
- A) Extend existing `handle_codex_security` function - Rejected: Would create monolithic function with mixed responsibilities
- B) Keep separate functions for each agent - Rejected: Would lead to code duplication and maintenance burden

**Evidence**:
- Current codebase analysis shows `ensure_gitignore_entries()` at src/specify_cli/__init__.py:689
- Existing `handle_codex_security()` at src/specify_cli/__init__.py:729 only handles .codex/
- Agent directory map at src/specify_cli/__init__.py:1835-1848 lists all known agents

### 2. Implementation Strategy

**Decision**: Create GitignoreManager class/module with these components:

1. **Core Module Structure**:
   - `GitignoreManager` class to encapsulate all gitignore operations
   - Static registry of all agent directories
   - Methods for add, remove, check operations
   - Backward compatibility wrapper for `handle_codex_security`

2. **File Handling Strategy**:
   - Use existing `ensure_gitignore_entries()` logic as foundation
   - Preserve line ending style detection
   - Maintain comment marker system ("# Added by Spec Kitty CLI")

**Rationale**:
- Centralizes all gitignore logic in one place
- Makes testing easier with clear boundaries
- Allows for future enhancements (custom patterns, exclusions)

### 3. Agent Directory Registry

**Decision**: Maintain centralized registry of all agent directories

**Current Agent Directories** (from codebase analysis):
```python
agent_folders = {
    ".claude/",     # Claude Code
    ".codex/",      # Codex
    ".opencode/",   # opencode
    ".windsurf/",   # Windsurf
    ".gemini/",     # Gemini
    ".cursor/",     # Cursor
    ".qwen/",       # Qwen
    ".kilocode/",   # Kilocode
    ".augment/",    # Auggie
    ".github/",     # Copilot (Note: special case - may need selective handling)
    ".roo/",        # Roo Coder
    ".amazonq/"     # Amazon Q
}
```

**Special Considerations**:
- `.github/` is used by GitHub Actions as well as Copilot - may need selective patterns
- All directories use trailing slash to indicate directory (not file)
- Dot prefix is consistent across all agents

### 4. Internal Refactoring

**Decision**: Direct replacement without backward compatibility

**Implementation**:
- Remove `handle_codex_security()` function entirely
- Replace with direct GitignoreManager calls
- Update all internal references

**Rationale**:
- This is an internal function, not a public API
- No external consumers to break
- Cleaner codebase without deprecation overhead
- Simpler implementation and testing

### 5. Error Handling Strategy

**Decision**: Graceful degradation with informative warnings

**Scenarios**:
1. **Read-only .gitignore**: Warn user with instructions to fix permissions
2. **File system errors**: Log error, continue with other operations
3. **Invalid patterns**: Skip invalid entries, log warning
4. **Git repository detection**: Work even if not a git repository

**Rationale**:
- Tool should not fail completely if gitignore operations fail
- Users need clear guidance on how to fix issues
- Security is important but shouldn't block entire init process

## Technical Requirements

### Performance Considerations

- **File I/O**: Single read/write operation per init (no multiple file accesses)
- **Pattern Matching**: Use set operations for O(1) duplicate detection
- **Memory**: Keep entire .gitignore in memory during operation (~10KB typical)

### Testing Strategy

1. **Unit Tests**:
   - Test GitignoreManager methods independently
   - Mock file system operations
   - Test edge cases (empty file, large file, special characters)

2. **Integration Tests**:
   - Test with real file system
   - Test with actual git repositories
   - Test upgrade scenarios (existing .codex/ handling)

3. **Test Coverage Required**:
   - Create new .gitignore
   - Append to existing .gitignore
   - Handle duplicates
   - Preserve formatting
   - Error scenarios

## Implementation Checklist

- [ ] Create GitignoreManager class in new module
- [ ] Migrate ensure_gitignore_entries logic
- [ ] Add comprehensive agent directory registry
- [ ] Remove handle_codex_security function
- [ ] Update init flow to use GitignoreManager
- [ ] Add unit tests for all methods
- [ ] Add integration tests for init flow
- [ ] Update documentation

## Open Questions

1. **Special handling for .github/?** - This directory is used by GitHub Actions workflows as well as Copilot. Should we:
   - Add more specific patterns (e.g., `.github/copilot/` only)?
   - Skip .github/ entirely?
   - Add with a comment explaining the dual use?

2. **Future agent additions?** - How should we handle new agents added after release?
   - Dynamic discovery mechanism?
   - Configuration file?
   - Hardcoded with regular updates?

3. **User overrides?** - Should users be able to exclude certain directories from protection?
   - Environment variable?
   - Configuration file?
   - Command-line flag?

## Risk Assessment

**Low Risk**:
- Well-understood problem domain
- Existing code provides good foundation
- Clear test scenarios

**Medium Risk**:
- .github/ directory dual use may cause confusion
- Line ending handling across platforms

**Mitigation**:
- Comprehensive testing on multiple platforms
- Clear documentation about .github/ handling
- Conservative approach to line endings (preserve existing)

## References

- Existing implementation: `src/specify_cli/__init__.py:689-780`
- Agent registry: `src/specify_cli/__init__.py:1835-1848`
- Tests: `tests/test_gitignore_management.py`
- Related PR: Codex security implementation (CHANGELOG.md:47)