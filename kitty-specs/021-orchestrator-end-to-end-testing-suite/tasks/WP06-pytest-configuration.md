---
work_package_id: WP06
title: pytest Configuration
lane: "done"
dependencies:
- WP01
subtasks:
- T026
- T027
- T028
- T029
- T030
phase: Phase 1 - Core Tests
assignee: ''
agent: "claude-opus"
shell_pid: "29153"
review_status: "approved"
reviewed_by: "Robert Douglass"
history:
- timestamp: '2026-01-19T09:30:27Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP06 – pytest Configuration

## Implementation Command

```bash
spec-kitty implement WP06 --base WP04
```

Depends on WP01 (availability detection), WP02 (path selection), WP04 (fixture loading).

---

## Objectives & Success Criteria

Set up pytest fixtures and markers for orchestrator tests:

- [ ] `tests/specify_cli/orchestrator/conftest.py` exists and is loaded by pytest
- [ ] Custom markers registered: `orchestrator_*`, `core_agent`, `extended_agent`
- [ ] `available_agents` fixture provides session-scoped agent detection
- [ ] `test_path` fixture provides selected TestPath
- [ ] `test_context` fixture loads checkpoints into isolated TestContext

## Context & Constraints

**Reference Documents**:
- `kitty-specs/021-orchestrator-end-to-end-testing-suite/plan.md` - Marker list
- `kitty-specs/021-orchestrator-end-to-end-testing-suite/data-model.md` - TestContext

**Existing Code**:
- `src/specify_cli/orchestrator/testing/availability.py` - From WP01
- `src/specify_cli/orchestrator/testing/paths.py` - From WP02
- `src/specify_cli/orchestrator/testing/fixtures.py` - From WP03/WP04

**Constraints**:
- Use unique `orchestrator_` prefix for all markers
- Session-scoped fixtures must be cached correctly
- Function-scoped fixtures must provide isolation

---

## Subtasks & Detailed Guidance

### Subtask T026 – Create orchestrator conftest.py

**Purpose**: Central configuration file for orchestrator e2e tests.

**Steps**:
1. Create directory if needed:
   ```bash
   mkdir -p tests/specify_cli/orchestrator
   ```

2. Create `tests/specify_cli/orchestrator/__init__.py` (empty)

3. Create `tests/specify_cli/orchestrator/conftest.py`:
   ```python
   """pytest configuration for orchestrator e2e tests.

   Provides fixtures and markers for testing the multi-agent orchestrator.
   """
   from __future__ import annotations

   import pytest
   from pathlib import Path
   from typing import TYPE_CHECKING

   if TYPE_CHECKING:
       from specify_cli.orchestrator.testing.availability import AgentAvailability
       from specify_cli.orchestrator.testing.paths import TestPath
       from specify_cli.orchestrator.testing.fixtures import TestContext

   # Import will be added as fixtures are implemented
   ```

**Files**:
- `tests/specify_cli/orchestrator/__init__.py` (new, empty)
- `tests/specify_cli/orchestrator/conftest.py` (~20 lines initial)

**Parallel?**: Yes - can proceed with T027

---

### Subtask T027 – Register custom markers

**Purpose**: Prevent pytest warnings and enable selective test execution.

**Steps**:
1. Add markers to `tests/specify_cli/orchestrator/conftest.py`:
   ```python
   def pytest_configure(config):
       """Register custom markers for orchestrator tests."""
       # Availability detection markers
       config.addinivalue_line(
           "markers",
           "orchestrator_availability: tests for agent availability detection"
       )

       # Fixture markers
       config.addinivalue_line(
           "markers",
           "orchestrator_fixtures: tests for fixture loading and management"
       )

       # Test scenario markers
       config.addinivalue_line(
           "markers",
           "orchestrator_happy_path: happy path end-to-end tests"
       )
       config.addinivalue_line(
           "markers",
           "orchestrator_review_cycles: review rejection/approval cycle tests"
       )
       config.addinivalue_line(
           "markers",
           "orchestrator_parallel: parallel execution and dependency tests"
       )
       config.addinivalue_line(
           "markers",
           "orchestrator_smoke: basic smoke tests for agent invocation"
       )

       # Agent tier markers
       config.addinivalue_line(
           "markers",
           "core_agent: test requires core tier agent (fails if unavailable)"
       )
       config.addinivalue_line(
           "markers",
           "extended_agent: test for extended tier agent (skips if unavailable)"
       )

       # Performance markers
       config.addinivalue_line(
           "markers",
           "slow: test expected to take >30 seconds"
       )
   ```

2. Alternative: Add to `pytest.ini` or `pyproject.toml`:
   ```ini
   # pytest.ini
   [pytest]
   markers =
       orchestrator_availability: tests for agent availability detection
       orchestrator_fixtures: tests for fixture loading and management
       orchestrator_happy_path: happy path end-to-end tests
       orchestrator_review_cycles: review rejection/approval cycle tests
       orchestrator_parallel: parallel execution and dependency tests
       orchestrator_smoke: basic smoke tests for agent invocation
       core_agent: test requires core tier agent (fails if unavailable)
       extended_agent: test for extended tier agent (skips if unavailable)
       slow: test expected to take >30 seconds
   ```

**Files**:
- `tests/specify_cli/orchestrator/conftest.py` (add ~40 lines)

**Parallel?**: Yes - can proceed with T026

---

### Subtask T028 – Implement available_agents fixture

**Purpose**: Session-scoped fixture that detects and caches agent availability.

**Steps**:
1. Add to `conftest.py`:
   ```python
   import asyncio
   from specify_cli.orchestrator.testing.availability import (
       detect_all_agents,
       get_available_agents,
       AgentAvailability,
       CORE_AGENTS,
       EXTENDED_AGENTS,
   )

   @pytest.fixture(scope="session")
   def available_agents() -> dict[str, AgentAvailability]:
       """Detect all agents at session start.

       Returns:
           Dict mapping agent_id to AgentAvailability
       """
       # Run async detection in sync context
       loop = asyncio.new_event_loop()
       try:
           result = loop.run_until_complete(detect_all_agents())
           return result
       finally:
           loop.close()

   @pytest.fixture(scope="session")
   def available_agent_ids(available_agents: dict[str, AgentAvailability]) -> list[str]:
       """List of agent IDs that are installed and authenticated.

       Returns:
           Sorted list of available agent IDs
       """
       return sorted([
           agent_id for agent_id, avail in available_agents.items()
           if avail.is_available
       ])

   @pytest.fixture(scope="session")
   def core_agents_available(available_agents: dict[str, AgentAvailability]) -> list[str]:
       """List of available core tier agents."""
       return sorted([
           agent_id for agent_id, avail in available_agents.items()
           if avail.is_available and agent_id in CORE_AGENTS
       ])

   @pytest.fixture(scope="session")
   def extended_agents_available(available_agents: dict[str, AgentAvailability]) -> list[str]:
       """List of available extended tier agents."""
       return sorted([
           agent_id for agent_id, avail in available_agents.items()
           if avail.is_available and agent_id in EXTENDED_AGENTS
       ])
   ```

**Files**:
- `tests/specify_cli/orchestrator/conftest.py` (add ~50 lines)

**Parallel?**: No - depends on T026

---

### Subtask T029 – Implement test_path fixture

**Purpose**: Fixture that provides the selected TestPath based on available agents.

**Steps**:
1. Add to `conftest.py`:
   ```python
   from specify_cli.orchestrator.testing.paths import (
       TestPath,
       select_test_path_sync,
       clear_test_path_cache,
   )

   @pytest.fixture(scope="session")
   def test_path(available_agent_ids: list[str]) -> TestPath:
       """Select test path based on available agents.

       Automatically selects 1-agent, 2-agent, or 3+-agent path.

       Returns:
           TestPath with agent assignments

       Raises:
           pytest.skip: If no agents are available
       """
       if not available_agent_ids:
           pytest.skip("No agents available for testing")

       # Clear any cached path from previous sessions
       clear_test_path_cache()

       return select_test_path_sync()

   @pytest.fixture
   def forced_test_path(request):
       """Factory fixture to force a specific test path.

       Usage:
           @pytest.mark.parametrize("path_type", ["1-agent", "2-agent", "3+-agent"])
           def test_something(forced_test_path, path_type):
               path = forced_test_path(path_type)
       """
       def _force_path(path_type: str) -> TestPath:
           clear_test_path_cache()
           return select_test_path_sync(force_path=path_type)

       return _force_path
   ```

2. Add path-specific skip helpers:
   ```python
   @pytest.fixture
   def require_2_agent_path(test_path: TestPath):
       """Skip test if not running 2-agent or 3+-agent path."""
       if test_path.path_type == "1-agent":
           pytest.skip("Test requires at least 2 agents")

   @pytest.fixture
   def require_3_agent_path(test_path: TestPath):
       """Skip test if not running 3+-agent path."""
       if test_path.path_type != "3+-agent":
           pytest.skip("Test requires at least 3 agents")
   ```

**Files**:
- `tests/specify_cli/orchestrator/conftest.py` (add ~45 lines)

**Parallel?**: No - depends on T028

---

### Subtask T030 – Implement test_context fixture

**Purpose**: Function-scoped fixture that loads a checkpoint and provides isolated TestContext.

**Steps**:
1. Add to `conftest.py`:
   ```python
   from specify_cli.orchestrator.testing.fixtures import (
       FixtureCheckpoint,
       TestContext,
       load_checkpoint,
       cleanup_test_context,
   )
   from tests.fixtures.orchestrator import get_checkpoint_path, CHECKPOINTS

   @pytest.fixture
   def test_context_factory(test_path: TestPath):
       """Factory fixture for creating test contexts from checkpoints.

       Returns a function that loads a checkpoint by name.

       Usage:
           def test_something(test_context_factory):
               ctx = test_context_factory("wp_created")
               # Use ctx...
       """
       contexts_to_cleanup: list[TestContext] = []

       def _create_context(checkpoint_name: str) -> TestContext:
           """Load a checkpoint and return TestContext."""
           checkpoint_path = get_checkpoint_path(checkpoint_name)

           checkpoint = FixtureCheckpoint(
               name=checkpoint_name,
               path=checkpoint_path,
               orchestrator_version="test",
               created_at=datetime.now(),
           )

           ctx = load_checkpoint(checkpoint, test_path=test_path)
           contexts_to_cleanup.append(ctx)
           return ctx

       yield _create_context

       # Cleanup all created contexts
       for ctx in contexts_to_cleanup:
           cleanup_test_context(ctx)

   @pytest.fixture
   def test_context_wp_created(test_context_factory) -> TestContext:
       """Pre-loaded test context at wp_created checkpoint."""
       return test_context_factory("wp_created")

   @pytest.fixture
   def test_context_wp_implemented(test_context_factory) -> TestContext:
       """Pre-loaded test context at wp_implemented checkpoint."""
       return test_context_factory("wp_implemented")

   @pytest.fixture
   def test_context_review_pending(test_context_factory) -> TestContext:
       """Pre-loaded test context at review_pending checkpoint."""
       return test_context_factory("review_pending")
   ```

2. Add datetime import at top:
   ```python
   from datetime import datetime
   ```

**Files**:
- `tests/specify_cli/orchestrator/conftest.py` (add ~60 lines)

**Parallel?**: No - depends on T028, T029

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Session fixture runs before agents available | Detect at fixture creation, skip if none |
| Marker conflicts with other tests | Use `orchestrator_` prefix consistently |
| Context cleanup fails | Use try/finally and log warnings |
| Async/sync mismatch | Use `asyncio.new_event_loop()` for sync context |

## Review Guidance

**Key Acceptance Checkpoints**:
- [ ] `pytest --collect-only tests/specify_cli/orchestrator/` shows no warnings
- [ ] `available_agents` fixture caches results (single detection per session)
- [ ] `test_path` fixture returns correct path type based on agent count
- [ ] `test_context_factory` creates isolated contexts
- [ ] All contexts cleaned up after test completion
- [ ] Markers work: `pytest -m orchestrator_happy_path`

**Code Quality**:
- Proper fixture scoping (session vs function)
- Type hints on all fixtures
- Clear docstrings explaining usage
- No leaked temp directories after tests

## Activity Log

- 2026-01-19T09:30:27Z – system – lane=planned – Prompt created.
- 2026-01-19T10:03:10Z – claude-opus – shell_pid=14894 – lane=doing – Started implementation via workflow command
- 2026-01-19T10:15:05Z – claude-opus – shell_pid=14894 – lane=for_review – Ready for review: pytest fixtures and markers for orchestrator e2e tests. All 17 tests passing.
- 2026-01-19T10:19:23Z – claude-opus – shell_pid=29153 – lane=doing – Started review via workflow command
- 2026-01-19T10:21:18Z – claude-opus – shell_pid=29153 – lane=done – Review passed: All 5 subtasks (T026-T030) implemented correctly. conftest.py with 9 custom markers registered via pytest_configure(), session-scoped agent detection fixtures, TestPath fixtures with skip helpers, and test_context_factory for isolated checkpoint loading. 17 tests passing. Dependency WP01 is merged.
