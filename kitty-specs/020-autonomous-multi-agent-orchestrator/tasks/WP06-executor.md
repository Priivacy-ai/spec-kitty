---
work_package_id: "WP06"
subtasks:
  - "T027"
  - "T028"
  - "T029"
  - "T030"
  - "T031"
title: "Executor"
phase: "Phase 2 - Core Logic"
lane: "doing"
assignee: ""
agent: "claude-opus"
shell_pid: "50038"
review_status: ""
reviewed_by: ""
dependencies:
  - "WP02"
  - "WP03"
  - "WP04"
history:
  - timestamp: "2026-01-18T16:21:51Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP06 – Executor

## Objectives & Success Criteria

Implement agent process spawning and management with asyncio.

**Success Criteria**:
- Processes spawn correctly using `asyncio.create_subprocess_exec`
- WP prompt content piped to agent stdin
- stdout/stderr captured to log files
- Timeouts enforced with proper cleanup
- Worktree creation integrated from existing infrastructure

## Context & Constraints

**Reference Documents**:
- [plan.md](../plan.md) - Execution data flow, asyncio decision
- [spec.md](../spec.md) - FR-005, FR-019 (execution and worktree requirements)

**Existing Modules**:
- `src/specify_cli/cli/commands/implement.py` - Worktree creation

**Implementation Command**:
```bash
spec-kitty implement WP06 --base WP04
```
(Requires WP02, WP03 for invokers, WP04 for state)

## Subtasks & Detailed Guidance

### Subtask T027 – Implement async process spawning

**Purpose**: Spawn agent processes using asyncio subprocess.

**Steps**:
1. Create `src/specify_cli/orchestrator/executor.py`
2. Implement process spawning:
   ```python
   import asyncio
   from asyncio.subprocess import Process

   async def spawn_agent(
       invoker: AgentInvoker,
       prompt: str,
       working_dir: Path,
       role: str,
   ) -> tuple[Process, list[str]]:
       """Spawn agent process.

       Returns:
           Tuple of (process, command) for tracking
       """
       cmd = invoker.build_command(prompt, working_dir, role)

       process = await asyncio.create_subprocess_exec(
           *cmd,
           stdin=asyncio.subprocess.PIPE,
           stdout=asyncio.subprocess.PIPE,
           stderr=asyncio.subprocess.PIPE,
           cwd=working_dir,
       )

       return process, cmd
   ```

**Notes**:
- Use `create_subprocess_exec` for proper argument handling
- Set `cwd` to worktree directory
- Capture all streams for logging

---

### Subtask T028 – Implement stdin piping for prompts

**Purpose**: Send WP prompt content to agent via stdin.

**Steps**:
1. Read prompt file and pipe to stdin:
   ```python
   async def execute_agent(
       invoker: AgentInvoker,
       prompt_file: Path,
       working_dir: Path,
       role: str,
       timeout_seconds: int,
   ) -> InvocationResult:
       """Execute agent with prompt via stdin."""
       # Read prompt content
       prompt_content = prompt_file.read_text()

       # Spawn process
       process, cmd = await spawn_agent(invoker, prompt_content, working_dir, role)

       # Send prompt to stdin (for agents that accept stdin)
       if invoker.uses_stdin:
           stdin_data = prompt_content.encode("utf-8")
       else:
           stdin_data = None

       # Wait for completion with timeout
       start_time = time.time()
       try:
           stdout, stderr = await asyncio.wait_for(
               process.communicate(input=stdin_data),
               timeout=timeout_seconds,
           )
           duration = time.time() - start_time

           return invoker.parse_output(
               stdout.decode("utf-8"),
               stderr.decode("utf-8"),
               process.returncode,
           )
       except asyncio.TimeoutError:
           # Handle timeout
           ...
   ```

2. Add `uses_stdin` property to invokers that need it

**Notes**:
- Some agents use stdin (Claude, Codex, Gemini)
- Others use command-line argument (Copilot, Kilocode, Auggie)
- Check invoker's preferred method

---

### Subtask T029 – Implement stdout/stderr capture to log files

**Purpose**: Save agent output for debugging and review.

**Steps**:
1. Implement log capture:
   ```python
   def get_log_path(repo_root: Path, wp_id: str, role: str) -> Path:
       """Get path for agent log file."""
       logs_dir = repo_root / ".kittify" / "logs"
       logs_dir.mkdir(parents=True, exist_ok=True)
       return logs_dir / f"{wp_id}-{role}.log"

   async def execute_with_logging(
       invoker: AgentInvoker,
       prompt_file: Path,
       working_dir: Path,
       role: str,
       timeout_seconds: int,
       log_path: Path,
   ) -> InvocationResult:
       """Execute agent and save output to log file."""
       result = await execute_agent(
           invoker, prompt_file, working_dir, role, timeout_seconds
       )

       # Write log file
       with open(log_path, "w") as f:
           f.write(f"# Agent: {invoker.agent_id}\n")
           f.write(f"# Role: {role}\n")
           f.write(f"# Exit code: {result.exit_code}\n")
           f.write(f"# Duration: {result.duration_seconds:.2f}s\n")
           f.write("\n--- STDOUT ---\n")
           f.write(result.stdout)
           f.write("\n--- STDERR ---\n")
           f.write(result.stderr)

       return result
   ```

**Parallel?**: Yes - can develop alongside T030

---

### Subtask T030 – Implement timeout handling

**Purpose**: Enforce execution timeouts with proper cleanup.

**Steps**:
1. Implement timeout with process cleanup:
   ```python
   async def execute_with_timeout(
       process: Process,
       stdin_data: bytes | None,
       timeout_seconds: int,
   ) -> tuple[bytes, bytes, int]:
       """Wait for process with timeout, kill if exceeded."""
       try:
           stdout, stderr = await asyncio.wait_for(
               process.communicate(input=stdin_data),
               timeout=timeout_seconds,
           )
           return stdout, stderr, process.returncode
       except asyncio.TimeoutError:
           # Graceful termination first
           process.terminate()
           try:
               await asyncio.wait_for(process.wait(), timeout=5.0)
           except asyncio.TimeoutError:
               # Force kill if terminate didn't work
               process.kill()
               await process.wait()

           return b"", b"Execution timed out", -1
   ```

2. Return special exit code for timeout:
   ```python
   TIMEOUT_EXIT_CODE = -1  # Or use 124 like timeout command
   ```

**Parallel?**: Yes

---

### Subtask T031 – Implement worktree creation integration

**Purpose**: Create WP worktree using existing infrastructure.

**Steps**:
1. Integrate with existing implement command:
   ```python
   import subprocess

   async def create_worktree(
       feature_slug: str,
       wp_id: str,
       base_wp: str | None,
       repo_root: Path,
   ) -> Path:
       """Create worktree for WP using existing spec-kitty infrastructure.

       Args:
           feature_slug: Feature identifier (e.g., "020-...")
           wp_id: Work package ID (e.g., "WP01")
           base_wp: Optional base WP for --base flag
           repo_root: Repository root path

       Returns:
           Path to created worktree
       """
       cmd = ["spec-kitty", "implement", wp_id]
       if base_wp:
           cmd.extend(["--base", base_wp])

       result = await asyncio.create_subprocess_exec(
           *cmd,
           cwd=repo_root,
           stdout=asyncio.subprocess.PIPE,
           stderr=asyncio.subprocess.PIPE,
       )
       await result.wait()

       if result.returncode != 0:
           stderr = (await result.stderr.read()).decode()
           raise WorktreeCreationError(f"Failed to create worktree: {stderr}")

       # Return worktree path
       worktree_path = repo_root / ".worktrees" / f"{feature_slug}-{wp_id}"
       return worktree_path
   ```

2. Alternatively, call the Python function directly:
   ```python
   from specify_cli.cli.commands.implement import create_wp_workspace

   worktree_path = create_wp_workspace(feature_slug, wp_id, base_wp)
   ```

**Notes**:
- Use existing infrastructure - don't reimplement worktree logic
- Handle `--base` flag for dependent WPs
- Verify worktree exists after creation

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Zombie processes | Always call process.wait() after terminate/kill |
| Timeout not enforced | Use asyncio.wait_for with explicit cleanup |
| Worktree creation fails | Clear error with instructions |

## Definition of Done Checklist

- [ ] `spawn_agent()` creates process correctly
- [ ] Prompt piped to stdin for stdin-based agents
- [ ] stdout/stderr captured to log files
- [ ] Timeout kills process after grace period
- [ ] Worktree created using existing infrastructure
- [ ] Log files contain useful debugging info

## Review Guidance

- Verify process cleanup on timeout
- Check log file format is useful
- Test worktree creation with --base flag
- Verify stdin piping works for Claude/Codex

## Activity Log

- 2026-01-18T16:21:51Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-18T19:08:31Z – claude-opus – shell_pid=48389 – lane=doing – Started implementation via workflow command
- 2026-01-18T19:12:01Z – claude-opus – shell_pid=48389 – lane=for_review – Ready for review: Executor implementation complete with async process spawning (T027), stdin piping (T028), log capture (T029), timeout handling (T030), and worktree integration (T031). All tests passed.
- 2026-01-18T19:34:33Z – claude-opus – shell_pid=50038 – lane=doing – Started review via workflow command
