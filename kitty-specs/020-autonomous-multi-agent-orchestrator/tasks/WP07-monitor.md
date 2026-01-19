---
work_package_id: "WP07"
subtasks:
  - "T032"
  - "T033"
  - "T034"
  - "T035"
  - "T036"
  - "T037"
title: "Monitor"
phase: "Phase 2 - Core Logic"
lane: "done"
assignee: ""
agent: "claude-opus"
shell_pid: "77775"
review_status: "approved"
reviewed_by: "Robert Douglass"
dependencies:
  - "WP06"
history:
  - timestamp: "2026-01-18T16:21:51Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP07 – Monitor

## Objectives & Success Criteria

Implement completion detection, failure handling, and lane status updates.

**Success Criteria**:
- Exit codes correctly determine success/failure
- JSON output parsed when available
- Retry logic respects configurable limits
- Fallback strategies execute correctly
- Lane status updates via existing commands
- Human escalation pauses orchestration with clear alert

## Context & Constraints

**Reference Documents**:
- [spec.md](../spec.md) - FR-013, FR-014, FR-015, FR-020, FR-021 (failure handling requirements)
- [plan.md](../plan.md) - Monitoring data flow
- [data-model.md](../data-model.md) - FallbackStrategy enum

**Existing Commands**:
- `spec-kitty agent tasks move-task <WPID> --to <lane>` - Lane updates
- `spec-kitty agent tasks mark-status <TID> --status done` - Subtask updates

**Implementation Command**:
```bash
spec-kitty implement WP07 --base WP06
```

## Subtasks & Detailed Guidance

### Subtask T032 – Implement exit code detection

**Purpose**: Determine success/failure from agent exit codes.

**Steps**:
1. Create `src/specify_cli/orchestrator/monitor.py`
2. Implement exit code handling:
   ```python
   def is_success(result: InvocationResult) -> bool:
       """Determine if invocation was successful."""
       return result.exit_code == 0 and result.success

   def classify_failure(result: InvocationResult, agent_id: str) -> FailureType:
       """Classify the type of failure for appropriate handling."""
       if result.exit_code == 124:  # timeout command exit code
           return FailureType.TIMEOUT
       if result.exit_code == 41 and agent_id == "gemini":  # Gemini auth error
           return FailureType.AUTH_ERROR
       if result.exit_code == 42 and agent_id == "gemini":  # Gemini rate limit
           return FailureType.RATE_LIMIT
       if "authentication" in result.stderr.lower():
           return FailureType.AUTH_ERROR
       if "rate limit" in result.stderr.lower():
           return FailureType.RATE_LIMIT
       return FailureType.GENERAL_ERROR

   class FailureType(Enum):
       TIMEOUT = "timeout"
       AUTH_ERROR = "auth_error"
       RATE_LIMIT = "rate_limit"
       GENERAL_ERROR = "general_error"
   ```

**Parallel?**: Yes - can develop alongside T033

---

### Subtask T033 – Implement JSON output parsing

**Purpose**: Extract structured data from agent JSON output.

**Steps**:
1. Implement JSON parsing for agents that support it:
   ```python
   import json

   def parse_json_output(stdout: str) -> dict | None:
       """Parse JSON output from agent, handling JSONL format."""
       # Some agents output JSONL (one JSON per line)
       lines = stdout.strip().split("\n")

       # Try parsing last line as JSON (final result)
       for line in reversed(lines):
           try:
               data = json.loads(line)
               return data
           except json.JSONDecodeError:
               continue

       # Try parsing entire output as JSON
       try:
           return json.loads(stdout)
       except json.JSONDecodeError:
           return None

   def extract_result_data(json_data: dict | None) -> dict:
       """Extract useful fields from parsed JSON."""
       if not json_data:
           return {}

       return {
           "files_modified": json_data.get("files", []),
           "commits_made": json_data.get("commits", []),
           "errors": json_data.get("errors", []),
           "warnings": json_data.get("warnings", []),
       }
   ```

**Notes**:
- Claude outputs JSON with conversation turns
- Codex outputs structured result JSON
- Auggie doesn't output JSON (rely on exit code)

**Parallel?**: Yes

---

### Subtask T034 – Implement retry logic

**Purpose**: Retry failed invocations up to configurable limit.

**Steps**:
1. Implement retry wrapper:
   ```python
   async def execute_with_retry(
       executor_fn: Callable,
       wp_execution: WPExecution,
       config: OrchestratorConfig,
       role: str,
   ) -> InvocationResult:
       """Execute with retry logic.

       Args:
           executor_fn: Async function to execute
           wp_execution: WP execution state to update
           config: Orchestrator config for retry limits
           role: "implementation" or "review"

       Returns:
           Final InvocationResult (success or last failure)
       """
       max_retries = config.max_retries
       retries = getattr(wp_execution, f"{role}_retries")

       while retries <= max_retries:
           result = await executor_fn()

           if is_success(result):
               return result

           retries += 1
           setattr(wp_execution, f"{role}_retries", retries)
           wp_execution.last_error = result.stderr[:500]  # Truncate

           if retries <= max_retries:
               # Log retry attempt
               logger.warning(
                   f"WP {wp_execution.wp_id} {role} failed (attempt {retries}/{max_retries+1}), retrying..."
               )
               # Small delay before retry
               await asyncio.sleep(5)

       return result  # Return last failure
   ```

**Notes**:
- Retry same agent first (may be transient failure)
- Small delay between retries
- Update WP execution state with retry count

---

### Subtask T035 – Implement fallback strategy execution

**Purpose**: Apply fallback strategy when retries exhausted.

**Steps**:
1. Implement fallback strategies:
   ```python
   async def apply_fallback(
       wp_id: str,
       role: str,
       failed_agent: str,
       config: OrchestratorConfig,
       state: OrchestrationRun,
   ) -> str | None:
       """Apply fallback strategy and return next agent to try.

       Returns:
           Next agent ID to try, or None if no fallback available
       """
       strategy = config.fallback_strategy
       wp_execution = state.work_packages[wp_id]

       if strategy == FallbackStrategy.FAIL:
           # No fallback - fail immediately
           return None

       if strategy == FallbackStrategy.SAME_AGENT:
           # In single-agent mode, just fail after retries
           return None

       if strategy == FallbackStrategy.NEXT_IN_LIST:
           # Try next agent in priority list
           wp_execution.fallback_agents_tried.append(failed_agent)

           candidates = config.defaults.get(role, [])
           for agent_id in candidates:
               if agent_id in wp_execution.fallback_agents_tried:
                   continue
               if not config.agents.get(agent_id, AgentConfig(...)).enabled:
                   continue
               return agent_id

           # All agents tried
           return None

       return None
   ```

2. Integration with monitor loop:
   ```python
   async def handle_failure(wp_id: str, role: str, failed_agent: str, ...):
       next_agent = await apply_fallback(wp_id, role, failed_agent, config, state)
       if next_agent:
           # Retry with next agent
           return await execute_wp_phase(wp_id, role, next_agent, ...)
       else:
           # All fallbacks exhausted
           return await escalate_to_human(wp_id, role, state)
   ```

---

### Subtask T036 – Implement lane status updates

**Purpose**: Update WP lane via existing spec-kitty commands.

**Steps**:
1. Implement lane update wrapper:
   ```python
   import subprocess

   async def update_wp_lane(
       wp_id: str,
       lane: str,
       note: str,
       repo_root: Path,
   ) -> bool:
       """Update WP lane status using spec-kitty command.

       Args:
           wp_id: Work package ID
           lane: Target lane (doing, for_review, done)
           note: Status note
           repo_root: Repository root

       Returns:
           True if successful
       """
       cmd = [
           "spec-kitty", "agent", "tasks", "move-task",
           wp_id,
           "--to", lane,
           "--note", note,
       ]

       result = await asyncio.create_subprocess_exec(
           *cmd,
           cwd=repo_root,
           stdout=asyncio.subprocess.PIPE,
           stderr=asyncio.subprocess.PIPE,
       )
       await result.wait()

       return result.returncode == 0
   ```

2. Lane transitions:
   - Start implementation: `planned` → `doing`
   - Start review: `doing` → `for_review`
   - Complete: `for_review` → `done`
   - Failure: remain in current lane, log error

---

### Subtask T037 – Implement human escalation

**Purpose**: Pause orchestration and alert user when all agents fail.

**Steps**:
1. Implement escalation:
   ```python
   from rich.console import Console
   from rich.panel import Panel

   async def escalate_to_human(
       wp_id: str,
       role: str,
       state: OrchestrationRun,
       console: Console,
   ) -> None:
       """Pause orchestration and alert user.

       Sets state to PAUSED and prints clear instructions.
       """
       state.status = OrchestrationStatus.PAUSED
       wp_execution = state.work_packages[wp_id]
       wp_execution.status = WPStatus.FAILED

       # Save state for resume
       save_state(state, repo_root)

       # Print alert
       console.print(Panel(
           f"[bold red]Orchestration Paused[/bold red]\n\n"
           f"Work package [bold]{wp_id}[/bold] failed during {role}.\n"
           f"All agents exhausted after retries and fallbacks.\n\n"
           f"Last error:\n{wp_execution.last_error}\n\n"
           f"[bold]Options:[/bold]\n"
           f"1. Fix the issue and run: spec-kitty orchestrate --resume\n"
           f"2. Skip this WP and continue: spec-kitty orchestrate --skip {wp_id}\n"
           f"3. Abort: spec-kitty orchestrate --abort",
           title="Human Intervention Required",
           border_style="red",
       ))
   ```

**Notes**:
- State saved so user can resume after fixing
- Clear instructions on how to proceed
- Log file path shown for debugging

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Infinite retry loop | Hard max_retries limit |
| All agents fail | Clear escalation with resume path |
| Lane update race conditions | Single orchestrator owns lane updates |

## Definition of Done Checklist

- [ ] Exit code 0 correctly detected as success
- [ ] Non-zero exit codes classified appropriately
- [ ] JSON output parsed from stdout
- [ ] Retry logic respects max_retries
- [ ] Fallback strategies execute correctly
- [ ] Lane updates use existing commands
- [ ] Human escalation pauses and prints clear message

## Review Guidance

- Test each failure type classification
- Verify retry count tracks correctly
- Test fallback with multiple agents
- Verify lane commands execute correctly
- Check escalation message is actionable

## Activity Log

- 2026-01-18T16:21:51Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-18T19:34:18Z – claude-opus – shell_pid=49898 – lane=doing – Started implementation via workflow command
- 2026-01-18T19:37:59Z – claude-opus – shell_pid=49898 – lane=for_review – Ready for review: Monitor implementation complete with exit code detection (T032), JSON parsing (T033), retry logic (T034), fallback strategies (T035), lane updates (T036), and human escalation (T037). All tests passed.
- 2026-01-19T08:15:08Z – claude-opus – shell_pid=77775 – lane=doing – Started review via workflow command
- 2026-01-19T08:16:57Z – claude-opus – shell_pid=77775 – lane=done – Review passed: Monitor implementation complete with exit code detection, JSON parsing, retry logic (with auth skip), fallback strategies (FAIL/SAME_AGENT/NEXT_IN_LIST), lane status updates via CLI commands, and human escalation with Rich Panel. All 6 subtasks (T032-T037) properly implemented.
