---
work_package_id: "WP05"
subtasks:
  - "T022"
  - "T023"
  - "T024"
  - "T025"
  - "T026"
title: "Scheduler"
phase: "Phase 2 - Core Logic"
lane: "done"
assignee: ""
agent: "claude-opus"
shell_pid: "48486"
review_status: "approved"
reviewed_by: "Robert Douglass"
dependencies:
  - "WP01"
  - "WP04"
history:
  - timestamp: "2026-01-18T16:21:51Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP05 – Scheduler

## Objectives & Success Criteria

Implement WP dependency resolution and agent assignment logic.

**Success Criteria**:

- Dependency graph built from WP frontmatter
- Ready WP detection correctly identifies WPs with satisfied dependencies
- Agent selection respects roles and priorities
- Concurrency limits enforced via semaphores
- Single-agent mode handles both roles with delay

## Context & Constraints

**Reference Documents**:

- [spec.md](../spec.md) - FR-001, FR-002, FR-003, FR-004, FR-017 (scheduling requirements)
- [plan.md](../plan.md) - Scheduling loop description
- [data-model.md](../data-model.md) - OrchestratorConfig for priorities

**Existing Modules**:

- `src/specify_cli/core/dependency_graph.py` - Reuse for graph operations

**Implementation Command**:

```bash
spec-kitty implement WP05 --base WP04
```

## Subtasks & Detailed Guidance

### Subtask T022 – Implement dependency graph reading

**Purpose**: Build dependency graph from WP frontmatter.

**Steps**:

1. Create `src/specify_cli/orchestrator/scheduler.py`
2. Implement graph building:

   ```python
   from specify_cli.core.dependency_graph import DependencyGraph

   def build_wp_graph(feature_dir: Path) -> dict[str, list[str]]:
       """Build WP dependency graph from task frontmatter.

       Returns:
           Dict mapping WP ID to list of dependency WP IDs.
           e.g., {"WP02": ["WP01"], "WP03": ["WP01", "WP02"]}
       """
       tasks_dir = feature_dir / "tasks"
       graph = {}

       for wp_file in tasks_dir.glob("WP*.md"):
           # Parse frontmatter
           frontmatter = parse_frontmatter(wp_file)
           wp_id = frontmatter.get("work_package_id")
           deps = frontmatter.get("dependencies", [])
           graph[wp_id] = deps

       return graph
   ```

3. Validate graph (no cycles, all deps exist):

   ```python
   def validate_graph(graph: dict[str, list[str]]) -> None:
       """Raise error if graph has cycles or invalid references."""
       # Use existing DependencyGraph for validation
       ...
   ```

**Notes**:

- Reuse existing `DependencyGraph` class for cycle detection
- Parse frontmatter with ruamel.yaml

---

### Subtask T023 – Implement ready WP detection

**Purpose**: Find WPs whose dependencies are all satisfied.

**Steps**:

1. Implement ready detection:

   ```python
   def get_ready_wps(
       graph: dict[str, list[str]],
       state: OrchestrationRun,
   ) -> list[str]:
       """Return WP IDs that are ready to execute.

       A WP is ready if:
       1. All dependencies are in "done" lane (completed status)
       2. WP itself is in "pending" status
       """
       ready = []
       for wp_id, deps in graph.items():
           wp_state = state.work_packages.get(wp_id)

           # Skip if not pending
           if wp_state and wp_state.status != WPStatus.PENDING:
               continue

           # Check all deps completed
           all_deps_done = all(
               state.work_packages.get(dep_id, WPExecution(dep_id, WPStatus.PENDING)).status == WPStatus.COMPLETED
               for dep_id in deps
           )

           if all_deps_done:
               ready.append(wp_id)

       return ready
   ```

**Notes**:

- WP with no dependencies is immediately ready
- Only return pending WPs (skip running/completed/failed)

---

### Subtask T024 – Implement agent selection by role and priority

**Purpose**: Select the best available agent for a given role.

**Steps**:

1. Implement selection logic:

   ```python
   def select_agent(
       config: OrchestratorConfig,
       role: str,  # "implementation" or "review"
       exclude_agent: str | None = None,  # For cross-agent review
       state: OrchestrationRun | None = None,
   ) -> str | None:
       """Select highest-priority available agent for role.

       Args:
           config: Orchestrator configuration
           role: "implementation" or "review"
           exclude_agent: Agent to exclude (for cross-agent review)
           state: Current state (for health tracking)

       Returns:
           Agent ID or None if no agent available
       """
       candidates = config.defaults.get(role, [])

       for agent_id in candidates:
           agent_config = config.agents.get(agent_id)
           if not agent_config:
               continue
           if not agent_config.enabled:
               continue
           if role not in agent_config.roles:
               continue
           if agent_id == exclude_agent:
               continue

           # Check if agent is available (not at concurrency limit)
           if _agent_at_limit(agent_id, agent_config, state):
               continue

           return agent_id

       return None
   ```

2. For review, exclude the implementation agent:

   ```python
   # In orchestration logic:
   impl_agent = select_agent(config, "implementation")
   review_agent = select_agent(config, "review", exclude_agent=impl_agent)
   ```

---

### Subtask T025 – Implement concurrency semaphores

**Purpose**: Limit concurrent agent processes.

**Steps**:

1. Create semaphore management:

   ```python
   import asyncio

   class ConcurrencyManager:
       """Manages concurrency limits for orchestration."""

       def __init__(self, config: OrchestratorConfig):
           self.global_semaphore = asyncio.Semaphore(config.global_concurrency)
           self.agent_semaphores: dict[str, asyncio.Semaphore] = {}

           for agent_id, agent_config in config.agents.items():
               self.agent_semaphores[agent_id] = asyncio.Semaphore(
                   agent_config.max_concurrent
               )

       async def acquire(self, agent_id: str) -> None:
           """Acquire both global and agent-specific semaphores."""
           await self.global_semaphore.acquire()
           await self.agent_semaphores[agent_id].acquire()

       def release(self, agent_id: str) -> None:
           """Release both semaphores."""
           self.agent_semaphores[agent_id].release()
           self.global_semaphore.release()

       @asynccontextmanager
       async def throttle(self, agent_id: str):
           """Context manager for throttled execution."""
           await self.acquire(agent_id)
           try:
               yield
           finally:
               self.release(agent_id)
   ```

**Notes**:

- Global semaphore prevents too many total processes
- Per-agent semaphores respect individual limits

---

### Subtask T026 – Implement single-agent mode handling

**Purpose**: Handle case where only one agent is configured.

**Steps**:

1. Detect single-agent mode:

   ```python
   def is_single_agent_mode(config: OrchestratorConfig) -> bool:
       """Check if operating in single-agent mode."""
       if config.single_agent_mode:
           return True

       # Auto-detect: only one agent enabled
       enabled_agents = [
           aid for aid, ac in config.agents.items()
           if ac.enabled
       ]
       return len(enabled_agents) == 1
   ```

2. Handle review in single-agent mode:

   ```python
   async def execute_single_agent_review(
       wp_id: str,
       agent_id: str,
       config: OrchestratorConfig,
       delay_seconds: int = 60,
   ):
       """Execute review with same agent after delay.

       The delay helps the agent "forget" its implementation
       context and review with fresher perspective.
       """
       await asyncio.sleep(delay_seconds)
       # Execute review with same agent
       ...
   ```

**Notes**:

- Single-agent mode: same agent does implementation and review
- Configurable delay between phases (default 60 seconds)
- Log warning that cross-agent review is not available

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Circular dependencies | Validate graph at startup, reject with clear error |
| Deadlock from semaphores | Always acquire global first, then agent-specific |
| Single agent overload | Enforce sequential WPs in single-agent mode |

## Definition of Done Checklist

- [ ] Dependency graph built from WP frontmatter
- [ ] Graph validated for cycles and invalid refs
- [ ] `get_ready_wps()` returns correct WPs
- [ ] Agent selection respects role and priority
- [ ] Cross-agent review excludes implementation agent
- [ ] Global and per-agent semaphores work
- [ ] Single-agent mode detected and handled

## Review Guidance

- Test with various dependency graph shapes (linear, fan-out, diamond)
- Verify agent selection excludes implementation agent for review
- Test semaphore limits are enforced
- Verify single-agent mode delay is applied

## Activity Log

- 2026-01-18T16:21:51Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-18T19:04:58Z – claude-opus – shell_pid=47577 – lane=doing – Started implementation via workflow command
- 2026-01-18T19:08:13Z – claude-opus – shell_pid=47577 – lane=for_review – Ready for review: Scheduler with dependency graph, ready WP detection, agent selection, concurrency semaphores, single-agent mode
- 2026-01-18T19:08:42Z – claude-opus – shell_pid=48486 – lane=doing – Started review via workflow command
- 2026-01-18T19:09:22Z – claude-opus – shell_pid=48486 – lane=done – Review passed: Dependency graph reading with validation (cycles, invalid refs). Ready WP detection sorted by topo order. Agent selection respects roles, priorities, concurrency limits, and cross-agent review exclusion. ConcurrencyManager with global-first semaphore acquisition. Single-agent mode with 60s review delay and auto-detection.
