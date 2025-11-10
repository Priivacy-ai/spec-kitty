---
work_package_id: "WP04"
subtasks:
  - "T023"
  - "T024"
  - "T025"
  - "T026"
  - "T027"
  - "T028"
  - "T029"
  - "T030"
  - "T031"
  - "T032"
title: "Testing Infrastructure"
phase: "Phase 4 - Quality Assurance"
lane: "done"
assignee: "claude"
agent: "claude"
shell_pid: "64252"
history:
  - timestamp: "2025-11-10T10:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---
*Path: [tasks/planned/WP04-testing-infrastructure.md](tasks/planned/WP04-testing-infrastructure.md)*

# Work Package Prompt: WP04 – Testing Infrastructure

## Objectives & Success Criteria

- Create comprehensive test coverage for GitignoreManager (>90% coverage)
- Write unit tests for all public methods and edge cases
- Update existing tests to work with new implementation
- Add integration tests for complete init flow
- Ensure tests pass on all platforms (Linux, macOS, Windows)

## Context & Constraints

- **Prerequisites**: WP02 complete (methods to test exist)
- **Related Documents**:
  - Existing tests: `tests/test_gitignore_management.py`
  - Test patterns: Review existing test structure
  - Requirements: `kitty-specs/003-auto-protect-agent/spec.md` (acceptance scenarios)
- **Testing Framework**: pytest (existing in project)
- **Constraint**: Must maintain existing test conventions

## Subtasks & Detailed Guidance

### Subtask T023 – Create test_gitignore_manager.py structure
- **Purpose**: Set up new test file for GitignoreManager
- **Steps**:
  1. Create directory `tests/unit/` if it doesn't exist
  2. Create file `tests/unit/test_gitignore_manager.py`
  3. Add imports: pytest, Path, tempfile, GitignoreManager, ProtectionResult
  4. Create TestGitignoreManager class
  5. Add pytest fixtures for temp directories and test files
- **Files**: `tests/unit/test_gitignore_manager.py` (create new)
- **Parallel?**: Yes (independent)
- **Notes**: Follow pytest conventions

### Subtask T024 – Test GitignoreManager.__init__ validation
- **Purpose**: Test initialization and validation logic
- **Steps**:
  1. Test successful initialization with valid directory
  2. Test ValueError raised for non-existent directory
  3. Test ValueError raised for file (not directory)
  4. Test gitignore_path is set correctly
  5. Test marker comment is set
- **Files**: `tests/unit/test_gitignore_manager.py`
- **Parallel?**: Yes (independent test methods)
- **Notes**: Use pytest.raises for exception testing

### Subtask T025 – Test protect_all_agents method
- **Purpose**: Verify all agents are protected correctly
- **Steps**:
  1. Test with no existing .gitignore (file creation)
  2. Test with empty .gitignore
  3. Test with .gitignore containing other entries
  4. Verify all 12 directories are added
  5. Check ProtectionResult is accurate
  6. Verify marker comment is added
- **Files**: `tests/unit/test_gitignore_manager.py`
- **Parallel?**: Yes (independent test methods)
- **Notes**: Assert exact number of directories

### Subtask T026 – Test protect_selected_agents method
- **Purpose**: Verify selective protection works
- **Steps**:
  1. Test with single agent selection
  2. Test with multiple agents
  3. Test with unknown agent name (warning expected)
  4. Test with empty list
  5. Verify only selected directories are added
- **Files**: `tests/unit/test_gitignore_manager.py`
- **Parallel?**: Yes (independent test methods)
- **Notes**: Check warnings for unknown agents

### Subtask T027 – Test duplicate detection logic
- **Purpose**: Ensure duplicates are never created
- **Steps**:
  1. Add entries, then add same entries again
  2. Verify entries_skipped in result
  3. Test with variations (spaces, comments)
  4. Run protect_all_agents twice
  5. Verify file content has no duplicates
- **Files**: `tests/unit/test_gitignore_manager.py`
- **Parallel?**: Yes (independent test methods)
- **Notes**: Critical for idempotency

### Subtask T028 – Test line ending preservation
- **Purpose**: Verify cross-platform compatibility
- **Steps**:
  1. Create .gitignore with Windows line endings (\r\n)
  2. Add entries and verify \r\n preserved
  3. Create .gitignore with Unix line endings (\n)
  4. Add entries and verify \n preserved
  5. Test new file gets platform default
- **Files**: `tests/unit/test_gitignore_manager.py`
- **Parallel?**: Yes (independent test methods)
- **Notes**: Use binary mode to verify bytes

### Subtask T029 – Test error handling scenarios
- **Purpose**: Verify graceful error handling
- **Steps**:
  1. Test read-only .gitignore file
  2. Test corrupted .gitignore (binary content)
  3. Test directory without write permissions
  4. Verify appropriate errors in ProtectionResult
  5. Ensure no exceptions bubble up
- **Files**: `tests/unit/test_gitignore_manager.py`
- **Parallel?**: Yes (independent test methods)
- **Notes**: Use os.chmod for permission tests

### Subtask T030 – Update existing test_gitignore_management.py
- **Purpose**: Fix tests broken by removing old functions
- **Steps**:
  1. Remove tests for handle_codex_security
  2. Remove tests for ensure_gitignore_entries
  3. Update any integration tests to use GitignoreManager
  4. Fix import statements
  5. Ensure all tests pass
- **Files**: `tests/test_gitignore_management.py`
- **Parallel?**: No (depends on understanding changes)
- **Notes**: May need to rewrite some tests

### Subtask T031 – Add integration tests for init flow
- **Purpose**: Test complete end-to-end flow
- **Steps**:
  1. Create test that simulates full spec-kitty init
  2. Mock user input for agent selection
  3. Verify .gitignore is created/updated correctly
  4. Test multiple init runs (idempotency)
  5. Test with various starting states
- **Files**: `tests/integration/test_init_flow.py` (create if needed)
- **Parallel?**: No (complex integration)
- **Notes**: May need to mock Rich console

### Subtask T032 – Add edge case tests
- **Purpose**: Test boundary conditions and special cases
- **Steps**:
  1. Test .github/ directory special handling
  2. Test very large .gitignore files (performance)
  3. Test special characters in paths
  4. Test empty marker comment sections
  5. Test concurrent modifications (if relevant)
- **Files**: `tests/unit/test_gitignore_manager.py`
- **Parallel?**: No (after main tests complete)
- **Notes**: Focus on specification edge cases

## Test Strategy

- **Unit Tests**: Focus on individual methods in isolation
- **Integration Tests**: Test the complete flow
- **Fixtures**: Use pytest fixtures for temp directories
- **Mocking**: Mock file I/O where appropriate for unit tests
- **Coverage**: Run `pytest --cov=src/specify_cli/gitignore_manager --cov-report=html`
- **Platform Testing**: Ensure CI runs on Linux, macOS, Windows

## Risks & Mitigations

- **Risk**: Tests being platform-specific
  - **Mitigation**: Use pathlib, test on all platforms in CI
- **Risk**: Flaky tests due to file system
  - **Mitigation**: Use proper teardown, temp directories
- **Risk**: Missing edge cases
  - **Mitigation**: Refer to specification edge cases section

## Definition of Done Checklist

- [ ] All subtasks completed and validated
- [ ] Unit test file created with all test methods
- [ ] >90% code coverage for GitignoreManager
- [ ] All tests pass locally
- [ ] Existing tests updated and passing
- [ ] Integration tests cover main scenarios
- [ ] Edge cases from specification tested
- [ ] Tests pass on all platforms (CI verification)
- [ ] No test warnings or deprecations

## Review Guidance

- Run full test suite: `pytest tests/`
- Check coverage report for gaps
- Verify tests are independent (run in random order)
- Ensure proper test naming conventions
- Check that fixtures are properly scoped
- Validate error scenarios are tested
- Review that acceptance scenarios from spec are covered

## Activity Log

- 2025-11-10T10:00:00Z – system – lane=planned – Prompt created.
- 2025-11-10T09:06:23Z – claude – shell_pid=63275 – lane=doing – Started implementation of testing infrastructure
- 2025-11-10T09:20:00Z – claude – shell_pid=63275 – lane=doing – Completed all 10 subtasks (T023-T032)
- 2025-11-10T09:12:59Z – claude – shell_pid=63275 – lane=for_review – Testing infrastructure complete - ready for review
- 2025-11-10T10:25:00Z – claude – shell_pid=64252 – lane=done – Approved: All 25 tests passing, comprehensive coverage achieved
- 2025-11-10T09:19:49Z – claude – shell_pid=64252 – lane=done – Approved for release - comprehensive testing achieved
