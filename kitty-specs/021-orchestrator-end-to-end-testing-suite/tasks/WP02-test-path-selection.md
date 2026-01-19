---
work_package_id: "WP02"
subtasks:
  - "T006"
  - "T007"
  - "T008"
  - "T009"
title: "Test Path Selection"
phase: "Phase 0 - Foundation"
lane: "for_review"
assignee: ""
agent: "claude-opus"
shell_pid: "5136"
review_status: ""
reviewed_by: ""
dependencies: ["WP01"]
history:
  - timestamp: "2026-01-19T09:30:27Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 – Test Path Selection

## Implementation Command

```bash
spec-kitty implement WP02 --base WP01
```

Depends on WP01 (needs `detect_all_agents()` and `AgentAvailability`).

---

## Objectives & Success Criteria

Implement the test path model that selects execution paths based on agent availability:

- [ ] `TestPath` dataclass represents selected test configuration
- [ ] Path selection correctly maps: 1 agent → 1-agent, 2 agents → 2-agent, 3+ agents → 3+-agent
- [ ] Agent assignment logic: first for impl, second for review, third for fallback
- [ ] Results cached at module level for session duration

## Context & Constraints

**Reference Documents**:
- `kitty-specs/021-orchestrator-end-to-end-testing-suite/plan.md` - Key decision #3 (Test Path Model)
- `kitty-specs/021-orchestrator-end-to-end-testing-suite/data-model.md` - TestPath definition

**Existing Code**:
- `src/specify_cli/orchestrator/testing/availability.py` - From WP01

**Constraints**:
- Agent selection should be deterministic (sort by agent_id)
- Same-agent mode allowed for 1-agent path
- Must handle edge case of 0 available agents

---

## Subtasks & Detailed Guidance

### Subtask T006 – Implement TestPath dataclass

**Purpose**: Define the data structure for test path configuration.

**Steps**:
1. Open `src/specify_cli/orchestrator/testing/paths.py`
2. Add imports and dataclass:
   ```python
   from __future__ import annotations

   from dataclasses import dataclass
   from typing import Literal

   @dataclass
   class TestPath:
       """Selected test path based on runtime agent availability."""

       path_type: Literal["1-agent", "2-agent", "3+-agent"]
       """The test path variant to execute."""

       available_agents: list[str]
       """List of authenticated agent IDs available for this run."""

       implementation_agent: str
       """Agent to use for implementation phase."""

       review_agent: str
       """Agent to use for review phase."""

       fallback_agent: str | None
       """Third agent for fallback scenarios (None for 1/2-agent paths)."""

       @property
       def is_cross_agent(self) -> bool:
           """True if implementation and review use different agents."""
           return self.implementation_agent != self.review_agent

       @property
       def has_fallback(self) -> bool:
           """True if a fallback agent is available."""
           return self.fallback_agent is not None

       @property
       def agent_count(self) -> int:
           """Number of available agents."""
           return len(self.available_agents)
   ```

**Files**:
- `src/specify_cli/orchestrator/testing/paths.py` (~45 lines)

**Parallel?**: No - must complete before T007-T009

---

### Subtask T007 – Implement path selection logic

**Purpose**: Determine which test path to use based on agent count.

**Steps**:
1. Add path type determination:
   ```python
   def determine_path_type(agent_count: int) -> Literal["1-agent", "2-agent", "3+-agent"]:
       """Determine test path type based on available agent count.

       Args:
           agent_count: Number of available (authenticated) agents

       Returns:
           Path type string

       Raises:
           ValueError: If no agents available
       """
       if agent_count == 0:
           raise ValueError("No agents available for testing")
       elif agent_count == 1:
           return "1-agent"
       elif agent_count == 2:
           return "2-agent"
       else:
           return "3+-agent"
   ```

**Files**:
- `src/specify_cli/orchestrator/testing/paths.py` (add ~20 lines)

**Parallel?**: Yes - once T006 complete

---

### Subtask T008 – Implement agent assignment

**Purpose**: Assign specific agents to implementation, review, and fallback roles.

**Steps**:
1. Add assignment function:
   ```python
   def assign_agents(
       available_agents: list[str],
       path_type: Literal["1-agent", "2-agent", "3+-agent"]
   ) -> tuple[str, str, str | None]:
       """Assign agents to roles based on path type.

       Args:
           available_agents: Sorted list of available agent IDs
           path_type: The test path type

       Returns:
           Tuple of (implementation_agent, review_agent, fallback_agent)
       """
       if not available_agents:
           raise ValueError("No agents available")

       # Sort for deterministic assignment
       agents = sorted(available_agents)

       if path_type == "1-agent":
           # Same agent for both roles
           return agents[0], agents[0], None

       elif path_type == "2-agent":
           # Different agents, no fallback
           return agents[0], agents[1], None

       else:  # 3+-agent
           # Different agents with fallback
           return agents[0], agents[1], agents[2]
   ```

**Files**:
- `src/specify_cli/orchestrator/testing/paths.py` (add ~30 lines)

**Parallel?**: Yes - once T006 complete

---

### Subtask T009 – Add select_test_path() with caching

**Purpose**: Main entry point that combines detection and path selection.

**Steps**:
1. Add module-level cache:
   ```python
   # Module-level cache
   _test_path_cache: TestPath | None = None

   def clear_test_path_cache() -> None:
       """Clear the cached test path."""
       global _test_path_cache
       _test_path_cache = None
   ```

2. Implement main selection function:
   ```python
   from specify_cli.orchestrator.testing.availability import (
       detect_all_agents,
       get_available_agents,
   )

   async def select_test_path(force_path: str | None = None) -> TestPath:
       """Select test path based on available agents.

       Args:
           force_path: Optional path type to force (for testing)

       Returns:
           TestPath with agent assignments

       Raises:
           ValueError: If no agents available
       """
       global _test_path_cache

       if _test_path_cache is not None and force_path is None:
           return _test_path_cache

       # Detect agents
       await detect_all_agents()
       available = get_available_agents()

       if not available:
           raise ValueError(
               "No agents available for testing. "
               "Install and authenticate at least one agent."
           )

       # Determine path type
       if force_path:
           path_type = force_path
       else:
           path_type = determine_path_type(len(available))

       # Assign agents
       impl_agent, review_agent, fallback = assign_agents(available, path_type)

       test_path = TestPath(
           path_type=path_type,
           available_agents=available,
           implementation_agent=impl_agent,
           review_agent=review_agent,
           fallback_agent=fallback,
       )

       if force_path is None:
           _test_path_cache = test_path

       return test_path
   ```

3. Add synchronous wrapper for pytest:
   ```python
   import asyncio

   def select_test_path_sync(force_path: str | None = None) -> TestPath:
       """Synchronous wrapper for select_test_path."""
       return asyncio.get_event_loop().run_until_complete(
           select_test_path(force_path)
       )
   ```

**Files**:
- `src/specify_cli/orchestrator/testing/paths.py` (add ~60 lines)

**Parallel?**: No - depends on T007 and T008

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| No agents available | Raise clear ValueError with installation instructions |
| Non-deterministic agent order | Sort agents by ID before assignment |
| Cache stale after agent change | Provide `clear_test_path_cache()` function |
| Async/sync mismatch with pytest | Provide sync wrapper function |

## Review Guidance

**Key Acceptance Checkpoints**:
- [ ] `TestPath` correctly represents all path types
- [ ] 1 agent → same agent for impl and review
- [ ] 2 agents → different agents, no fallback
- [ ] 3+ agents → different agents with fallback
- [ ] 0 agents → ValueError with helpful message
- [ ] Cache works (second call returns same object)
- [ ] `force_path` parameter allows overriding for tests

**Code Quality**:
- Deterministic behavior (sorted agent lists)
- Type hints on all functions
- Edge cases handled (0 agents, 1 agent same-agent mode)

## Activity Log

- 2026-01-19T09:30:27Z – system – lane=planned – Prompt created.
- 2026-01-19T09:45:28Z – claude-opus – shell_pid=5136 – lane=doing – Started implementation via workflow command
- 2026-01-19T09:58:21Z – claude-opus – shell_pid=5136 – lane=for_review – Ready for review: Implemented TestPath dataclass, determine_path_type(), assign_agents(), select_test_path() with caching. All 23 tests passing.
