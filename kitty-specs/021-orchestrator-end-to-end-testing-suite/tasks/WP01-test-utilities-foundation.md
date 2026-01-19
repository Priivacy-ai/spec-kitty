---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
title: "Test Utilities Foundation"
phase: "Phase 0 - Foundation"
lane: "doing"
assignee: ""
agent: "claude-opus"
shell_pid: "10866"
review_status: ""
reviewed_by: ""
dependencies: []
history:
  - timestamp: "2026-01-19T09:30:27Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – Test Utilities Foundation

## Implementation Command

```bash
spec-kitty implement WP01
```

No dependencies - this WP branches from main.

---

## Objectives & Success Criteria

Create the core test utilities module with agent availability detection capabilities:

- [ ] `src/specify_cli/orchestrator/testing/` module exists and is importable
- [ ] `AgentAvailability` dataclass correctly represents agent detection results
- [ ] `detect_all_agents()` returns availability for all 12 agents
- [ ] Auth probe makes lightweight API call with 10s timeout
- [ ] Detection results are cached for session duration

## Context & Constraints

**Reference Documents**:
- `kitty-specs/021-orchestrator-end-to-end-testing-suite/plan.md` - Key decision #2 (Auth Verification)
- `kitty-specs/021-orchestrator-end-to-end-testing-suite/data-model.md` - AgentAvailability definition

**Existing Code**:
- `src/specify_cli/orchestrator/agents/__init__.py` - Agent invoker registry (`get_invoker_registry()`)
- `src/specify_cli/orchestrator/agents/base.py` - `AgentInvoker` base class

**Constraints**:
- Reuse existing agent invoker detection where possible
- Probe timeout must be 10 seconds (configurable via env var)
- Must categorize agents into core tier (5 agents) and extended tier (7 agents)

---

## Subtasks & Detailed Guidance

### Subtask T001 – Create testing module structure

**Purpose**: Establish the new testing subpackage within the orchestrator module.

**Steps**:
1. Create directory: `src/specify_cli/orchestrator/testing/`
2. Create `__init__.py` with public exports:
   ```python
   from specify_cli.orchestrator.testing.availability import (
       AgentAvailability,
       detect_all_agents,
       detect_agent,
       CORE_AGENTS,
       EXTENDED_AGENTS,
   )
   from specify_cli.orchestrator.testing.paths import (
       TestPath,
       select_test_path,
   )
   from specify_cli.orchestrator.testing.fixtures import (
       FixtureCheckpoint,
       WorktreeMetadata,
       TestContext,
       load_checkpoint,
   )

   __all__ = [
       "AgentAvailability",
       "detect_all_agents",
       "detect_agent",
       "CORE_AGENTS",
       "EXTENDED_AGENTS",
       "TestPath",
       "select_test_path",
       "FixtureCheckpoint",
       "WorktreeMetadata",
       "TestContext",
       "load_checkpoint",
   ]
   ```
3. Create empty placeholder files:
   - `availability.py`
   - `paths.py` (WP02 will implement)
   - `fixtures.py` (WP03-04 will implement)

**Files**:
- `src/specify_cli/orchestrator/testing/__init__.py` (new, ~40 lines)
- `src/specify_cli/orchestrator/testing/availability.py` (new, placeholder)
- `src/specify_cli/orchestrator/testing/paths.py` (new, placeholder)
- `src/specify_cli/orchestrator/testing/fixtures.py` (new, placeholder)

**Parallel?**: No - must complete first

---

### Subtask T002 – Implement AgentAvailability dataclass

**Purpose**: Define the data structure for agent detection results.

**Steps**:
1. Open `availability.py`
2. Add imports:
   ```python
   from __future__ import annotations

   from dataclasses import dataclass
   from typing import Literal
   ```
3. Define tier constants:
   ```python
   CORE_AGENTS = frozenset({"claude", "codex", "copilot", "gemini", "opencode"})
   EXTENDED_AGENTS = frozenset({"cursor", "qwen", "augment", "kilocode", "roo", "windsurf", "amazonq"})
   ALL_AGENTS = CORE_AGENTS | EXTENDED_AGENTS
   ```
4. Implement dataclass matching data-model.md:
   ```python
   @dataclass
   class AgentAvailability:
       """Result of detecting an agent's availability for testing."""

       agent_id: str
       is_installed: bool
       is_authenticated: bool
       tier: Literal["core", "extended"]
       failure_reason: str | None = None
       probe_duration_ms: int | None = None

       @property
       def is_available(self) -> bool:
           """Agent is available if installed and authenticated."""
           return self.is_installed and self.is_authenticated

       @classmethod
       def get_tier(cls, agent_id: str) -> Literal["core", "extended"]:
           """Determine tier for an agent ID."""
           if agent_id in CORE_AGENTS:
               return "core"
           return "extended"
   ```

**Files**:
- `src/specify_cli/orchestrator/testing/availability.py` (~50 lines)

**Parallel?**: No - dataclass must exist before detection functions

---

### Subtask T003 – Implement is_installed check

**Purpose**: Detect whether an agent's CLI binary is installed and executable.

**Steps**:
1. Add function to `availability.py`:
   ```python
   import shutil
   from specify_cli.orchestrator.agents import get_invoker_registry

   def check_installed(agent_id: str) -> tuple[bool, str | None]:
       """Check if agent CLI is installed.

       Returns:
           Tuple of (is_installed, failure_reason)
       """
       registry = get_invoker_registry()
       invoker_class = registry.get(agent_id)

       if invoker_class is None:
           return False, f"Unknown agent: {agent_id}"

       # Get the CLI command from the invoker
       cli_command = invoker_class.CLI_COMMAND

       # Check if command exists in PATH
       if shutil.which(cli_command) is not None:
           return True, None

       return False, f"CLI not found: {cli_command}"
   ```

2. Note: The `CLI_COMMAND` class attribute may need to be added to agent invokers if not present. Check existing implementation.

**Files**:
- `src/specify_cli/orchestrator/testing/availability.py` (add ~25 lines)

**Parallel?**: Yes - can proceed with T004 once T002 done

**Notes**: May need to check how existing agent invokers expose their CLI command path.

---

### Subtask T004 – Implement probe() auth verification

**Purpose**: Make a lightweight API call to verify the agent is authenticated.

**Steps**:
1. Add probe function to `availability.py`:
   ```python
   import asyncio
   import os
   import time

   PROBE_TIMEOUT = int(os.environ.get("ORCHESTRATOR_PROBE_TIMEOUT", "10"))

   async def probe_agent_auth(agent_id: str) -> tuple[bool, str | None, int]:
       """Probe agent to verify authentication.

       Makes a minimal API call to verify the agent can communicate.

       Returns:
           Tuple of (is_authenticated, failure_reason, duration_ms)
       """
       registry = get_invoker_registry()
       invoker_class = registry.get(agent_id)

       if invoker_class is None:
           return False, f"Unknown agent: {agent_id}", 0

       start_time = time.monotonic()

       try:
           # Create invoker instance
           invoker = invoker_class()

           # Call probe method with timeout
           result = await asyncio.wait_for(
               invoker.probe(),
               timeout=PROBE_TIMEOUT
           )

           duration_ms = int((time.monotonic() - start_time) * 1000)

           if result:
               return True, None, duration_ms
           else:
               return False, "Probe returned failure", duration_ms

       except asyncio.TimeoutError:
           duration_ms = int((time.monotonic() - start_time) * 1000)
           return False, f"Probe timed out after {PROBE_TIMEOUT}s", duration_ms
       except Exception as e:
           duration_ms = int((time.monotonic() - start_time) * 1000)
           return False, f"Probe error: {str(e)}", duration_ms
   ```

2. Add `probe()` method to base invoker if not present:
   ```python
   # In agents/base.py, add to AgentInvoker class:
   async def probe(self) -> bool:
       """Verify agent is authenticated with a minimal API call.

       Override in subclass to implement agent-specific probe.
       Default returns True (assume authenticated if installed).
       """
       return True
   ```

3. Implement agent-specific probes in each invoker (optional, can default to True)

**Files**:
- `src/specify_cli/orchestrator/testing/availability.py` (add ~45 lines)
- `src/specify_cli/orchestrator/agents/base.py` (add probe method if missing)

**Parallel?**: Yes - can proceed with T003

**Notes**: Some agents may not have easy probe endpoints. Default to True (trust installation) for those.

---

### Subtask T005 – Implement detect_all_agents() with caching

**Purpose**: Detect all agents and cache results for session duration.

**Steps**:
1. Add module-level cache:
   ```python
   from functools import lru_cache

   # Cache at module level
   _agent_cache: dict[str, AgentAvailability] | None = None

   def clear_agent_cache() -> None:
       """Clear the cached agent detection results."""
       global _agent_cache
       _agent_cache = None
   ```

2. Implement detection function:
   ```python
   async def detect_agent(agent_id: str) -> AgentAvailability:
       """Detect availability of a single agent."""
       tier = AgentAvailability.get_tier(agent_id)

       # Check installation
       is_installed, install_reason = check_installed(agent_id)

       if not is_installed:
           return AgentAvailability(
               agent_id=agent_id,
               is_installed=False,
               is_authenticated=False,
               tier=tier,
               failure_reason=install_reason,
           )

       # Probe authentication
       is_authenticated, auth_reason, duration_ms = await probe_agent_auth(agent_id)

       return AgentAvailability(
           agent_id=agent_id,
           is_installed=True,
           is_authenticated=is_authenticated,
           tier=tier,
           failure_reason=auth_reason,
           probe_duration_ms=duration_ms,
       )

   async def detect_all_agents() -> dict[str, AgentAvailability]:
       """Detect availability of all supported agents.

       Results are cached for the session duration.
       Use clear_agent_cache() to force re-detection.
       """
       global _agent_cache

       if _agent_cache is not None:
           return _agent_cache

       results = {}
       for agent_id in sorted(ALL_AGENTS):
           results[agent_id] = await detect_agent(agent_id)

       _agent_cache = results
       return results

   def get_available_agents() -> list[str]:
       """Get list of available (installed + authenticated) agent IDs.

       Must call detect_all_agents() first.
       """
       if _agent_cache is None:
           raise RuntimeError("Call detect_all_agents() first")

       return [
           agent_id for agent_id, avail in _agent_cache.items()
           if avail.is_available
       ]
   ```

**Files**:
- `src/specify_cli/orchestrator/testing/availability.py` (add ~60 lines)

**Parallel?**: No - depends on T003 and T004

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Agent probes slow | 10s timeout per agent; parallel detection possible in future |
| Some agents lack probe capability | Default probe returns True; relies on installation check |
| Agent invoker API changes | Import from existing orchestrator.agents module |
| Cache not cleared between test sessions | Provide explicit `clear_agent_cache()` function |

## Review Guidance

**Key Acceptance Checkpoints**:
- [ ] `from specify_cli.orchestrator.testing import AgentAvailability` works
- [ ] `detect_all_agents()` returns dict with all 12 agents
- [ ] Core vs extended tier categorization is correct
- [ ] Probe timeout is configurable via `ORCHESTRATOR_PROBE_TIMEOUT` env var
- [ ] Cache is used on second call to `detect_all_agents()`

**Code Quality**:
- Async functions use proper async/await patterns
- Type hints on all public functions
- Docstrings explain behavior and return values

## Activity Log

- 2026-01-19T09:30:27Z – system – lane=planned – Prompt created.
- 2026-01-19T09:45:14Z – claude – shell_pid=4819 – lane=doing – Started implementation via workflow command
- 2026-01-19T09:53:24Z – claude – shell_pid=4819 – lane=for_review – Ready for review: Testing module with AgentAvailability dataclass, check_installed(), probe_agent_auth(), and detect_all_agents() with caching. All 12 agents detected (5 core + 7 extended). All success criteria verified.
- 2026-01-19T09:55:17Z – claude-opus – shell_pid=10866 – lane=doing – Started review via workflow command
