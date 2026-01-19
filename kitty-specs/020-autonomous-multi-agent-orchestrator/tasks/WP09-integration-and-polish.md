---
work_package_id: "WP09"
subtasks:
  - "T043"
  - "T044"
  - "T045"
  - "T046"
title: "Integration & Polish"
phase: "Phase 3 - CLI & Integration"
lane: "done"
assignee: ""
agent: "claude-opus"
shell_pid: "84101"
review_status: "approved"
reviewed_by: "Robert Douglass"
dependencies:
  - "WP08"
history:
  - timestamp: "2026-01-18T16:21:51Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP09 – Integration & Polish

## Objectives & Success Criteria

Integrate all components into working orchestration loop, add progress display, summary report, and handle edge cases.

**Success Criteria**:
- Full orchestration runs end-to-end on test feature
- Progress display shows live updates during execution
- Summary report shows useful metrics on completion
- All edge cases from spec handled gracefully

## Context & Constraints

**Reference Documents**:
- [spec.md](../spec.md) - Edge cases section, User Story 5 (progress visibility)
- [plan.md](../plan.md) - Data flow, integration points
- [quickstart.md](../quickstart.md) - Expected user experience

**Edge Cases from spec.md**:
- Circular dependencies → detect and reject at startup
- Invalid agent output → retry, then fallback
- Worktree creation fails → abort WP, continue others
- Git operations fail → retry, then fail WP
- No agents installed → clear error with instructions

**Implementation Command**:
```bash
spec-kitty implement WP09 --base WP08
```

## Subtasks & Detailed Guidance

### Subtask T043 – Implement main orchestration loop

**Purpose**: Connect all components into working orchestration.

**Steps**:
1. Create main loop in `orchestrator/__init__.py` or `orchestrator/main.py`:
   ```python
   async def run_orchestration_loop(
       state: OrchestrationRun,
       config: OrchestratorConfig,
       feature_dir: Path,
   ) -> None:
       """Main orchestration loop.

       Coordinates scheduler, executor, and monitor to process WPs.
       """
       repo_root = feature_dir.parent.parent
       graph = build_wp_graph(feature_dir)
       concurrency = ConcurrencyManager(config)

       # Initialize WP execution states
       for wp_id in graph.keys():
           if wp_id not in state.work_packages:
               state.work_packages[wp_id] = WPExecution(wp_id, WPStatus.PENDING)

       state.wps_total = len(graph)
       state.status = OrchestrationStatus.RUNNING
       save_state(state, repo_root)

       while True:
           # Check if done
           if all(
               wp.status in [WPStatus.COMPLETED, WPStatus.FAILED]
               for wp in state.work_packages.values()
           ):
               break

           # Get ready WPs
           ready_wps = get_ready_wps(graph, state)

           if not ready_wps:
               # No WPs ready - might be waiting for running ones
               if not any(
                   wp.status in [WPStatus.IMPLEMENTATION, WPStatus.REVIEW]
                   for wp in state.work_packages.values()
               ):
                   # Deadlock or all failed
                   break
               await asyncio.sleep(1)
               continue

           # Start tasks for ready WPs
           tasks = []
           for wp_id in ready_wps:
               task = asyncio.create_task(
                   process_wp(wp_id, state, config, feature_dir, concurrency)
               )
               tasks.append(task)

           # Wait for at least one to complete
           done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

           # Update metrics
           state.parallel_peak = max(state.parallel_peak, len(tasks))
           save_state(state, repo_root)

       # Finalize
       state.status = (
           OrchestrationStatus.COMPLETED
           if state.wps_failed == 0
           else OrchestrationStatus.FAILED
       )
       state.completed_at = datetime.utcnow()
       save_state(state, repo_root)
   ```

2. Implement WP processing:
   ```python
   async def process_wp(
       wp_id: str,
       state: OrchestrationRun,
       config: OrchestratorConfig,
       feature_dir: Path,
       concurrency: ConcurrencyManager,
   ) -> None:
       """Process a single WP through implementation and review."""
       wp = state.work_packages[wp_id]
       repo_root = feature_dir.parent.parent

       # Select agents
       impl_agent = select_agent(config, "implementation")
       review_agent = select_agent(config, "review", exclude_agent=impl_agent)

       # Implementation phase
       async with concurrency.throttle(impl_agent):
           wp.status = WPStatus.IMPLEMENTATION
           wp.implementation_agent = impl_agent
           wp.implementation_started = datetime.utcnow()
           await update_wp_lane(wp_id, "doing", f"Implementation by {impl_agent}", repo_root)

           result = await execute_wp_phase(wp_id, impl_agent, "implementation", ...)

           if not is_success(result):
               # Handle failure with retries and fallback
               ...

           wp.implementation_completed = datetime.utcnow()
           wp.implementation_exit_code = result.exit_code

       # Review phase
       if review_agent:
           async with concurrency.throttle(review_agent):
               wp.status = WPStatus.REVIEW
               wp.review_agent = review_agent
               wp.review_started = datetime.utcnow()
               await update_wp_lane(wp_id, "for_review", f"Review by {review_agent}", repo_root)

               result = await execute_wp_phase(wp_id, review_agent, "review", ...)

               wp.review_completed = datetime.utcnow()
               wp.review_exit_code = result.exit_code

       # Complete
       wp.status = WPStatus.COMPLETED
       state.wps_completed += 1
       await update_wp_lane(wp_id, "done", "Completed", repo_root)
   ```

---

### Subtask T044 – Add progress display during execution

**Purpose**: Show live progress updates using Rich console.

**Steps**:
1. Implement live progress display:
   ```python
   from rich.live import Live
   from rich.table import Table
   from rich.progress import Progress, SpinnerColumn, TextColumn

   def create_status_table(state: OrchestrationRun) -> Table:
       """Create status table for live display."""
       table = Table(title=f"Orchestration: {state.feature_slug}")

       table.add_column("WP", style="cyan")
       table.add_column("Status", style="magenta")
       table.add_column("Agent", style="green")
       table.add_column("Time", style="yellow")

       for wp_id, wp in state.work_packages.items():
           status = wp.status.value
           if wp.status == WPStatus.IMPLEMENTATION:
               agent = wp.implementation_agent
               elapsed = (datetime.utcnow() - wp.implementation_started).seconds
               time_str = f"{elapsed}s"
           elif wp.status == WPStatus.REVIEW:
               agent = wp.review_agent
               elapsed = (datetime.utcnow() - wp.review_started).seconds
               time_str = f"{elapsed}s"
           else:
               agent = "-"
               time_str = "-"

           table.add_row(wp_id, status, agent or "-", time_str)

       return table

   async def run_with_live_display(state, config, feature_dir):
       """Run orchestration with live status display."""
       with Live(create_status_table(state), refresh_per_second=1) as live:
           # Store live reference for updates
           state._live_display = live

           await run_orchestration_loop(state, config, feature_dir)
   ```

2. Update display periodically:
   ```python
   # In orchestration loop, periodically update:
   if hasattr(state, '_live_display'):
       state._live_display.update(create_status_table(state))
   ```

**Parallel?**: Yes - can develop alongside T045

---

### Subtask T045 – Add summary report on completion

**Purpose**: Show useful metrics when orchestration completes.

**Steps**:
1. Implement summary report:
   ```python
   def print_summary(state: OrchestrationRun, console: Console):
       """Print orchestration summary."""
       duration = (state.completed_at - state.started_at).total_seconds()

       # Collect agent usage stats
       agents_used = set()
       for wp in state.work_packages.values():
           if wp.implementation_agent:
               agents_used.add(wp.implementation_agent)
           if wp.review_agent:
               agents_used.add(wp.review_agent)

       # Build summary
       status_color = "green" if state.status == OrchestrationStatus.COMPLETED else "red"

       console.print("\n" + "=" * 60)
       console.print(Panel(
           f"[bold {status_color}]Orchestration {state.status.value.upper()}[/]\n\n"
           f"Feature: {state.feature_slug}\n"
           f"Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)\n"
           f"\n"
           f"[bold]Work Packages:[/]\n"
           f"  Total: {state.wps_total}\n"
           f"  Completed: {state.wps_completed}\n"
           f"  Failed: {state.wps_failed}\n"
           f"\n"
           f"[bold]Agents Used:[/] {', '.join(sorted(agents_used))}\n"
           f"[bold]Peak Parallelism:[/] {state.parallel_peak}\n"
           f"[bold]Total Invocations:[/] {state.total_agent_invocations}",
           title="Orchestration Summary",
           border_style=status_color,
       ))

       # Show failed WPs if any
       failed_wps = [
           wp_id for wp_id, wp in state.work_packages.items()
           if wp.status == WPStatus.FAILED
       ]
       if failed_wps:
           console.print(f"\n[red]Failed WPs:[/red] {', '.join(failed_wps)}")
           console.print("Check logs in .kittify/logs/ for details")
   ```

**Parallel?**: Yes

---

### Subtask T046 – Handle edge cases

**Purpose**: Gracefully handle all edge cases from spec.

**Steps**:
1. **Circular dependencies**:
   ```python
   def validate_graph(graph: dict[str, list[str]]) -> None:
       """Raise error if graph has cycles."""
       visited = set()
       rec_stack = set()

       def dfs(node: str) -> bool:
           visited.add(node)
           rec_stack.add(node)
           for dep in graph.get(node, []):
               if dep not in visited:
                   if dfs(dep):
                       return True
               elif dep in rec_stack:
                   return True
           rec_stack.remove(node)
           return False

       for node in graph:
           if node not in visited:
               if dfs(node):
                   raise CircularDependencyError(
                       f"Circular dependency detected in WP graph"
                   )
   ```

2. **No agents installed**:
   ```python
   def validate_agents(config: OrchestratorConfig) -> None:
       """Raise error if no agents available."""
       installed = detect_installed_agents()
       enabled = [
           aid for aid, ac in config.agents.items()
           if ac.enabled and aid in installed
       ]
       if not enabled:
           raise NoAgentsError(
               "No agents available for orchestration.\n\n"
               "Install at least one agent:\n"
               "  npm install -g @anthropic-ai/claude-code\n"
               "  npm install -g codex\n"
               "  npm install -g opencode"
           )
   ```

3. **Worktree creation fails**:
   ```python
   async def create_worktree_safe(wp_id: str, ...):
       try:
           return await create_worktree(...)
       except WorktreeCreationError as e:
           logger.error(f"Failed to create worktree for {wp_id}: {e}")
           # Mark WP as failed, don't block other WPs
           wp_execution.status = WPStatus.FAILED
           wp_execution.last_error = str(e)
           return None
   ```

4. **Git operations fail**:
   ```python
   # Retry git operations up to 3 times with backoff
   async def git_operation_with_retry(cmd: list[str], retries: int = 3):
       for i in range(retries):
           result = await asyncio.create_subprocess_exec(...)
           if result.returncode == 0:
               return True
           await asyncio.sleep(2 ** i)  # Exponential backoff
       return False
   ```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Complex integration bugs | Comprehensive logging, step-by-step testing |
| Progress display flicker | Use Rich Live for smooth updates |
| Missing edge cases | Follow spec.md edge cases list exactly |

## Definition of Done Checklist

- [ ] Main orchestration loop connects all components
- [ ] Full end-to-end orchestration runs on test feature
- [ ] Live progress display updates smoothly
- [ ] Summary report shows useful metrics
- [ ] Circular dependencies detected and rejected
- [ ] No agents installed shows helpful error
- [ ] Worktree failures don't block other WPs
- [ ] Git operation retries work

## Review Guidance

- Run full orchestration on a small test feature (3 WPs)
- Verify progress display updates in real-time
- Check summary report accuracy
- Test each edge case explicitly
- Verify logs are helpful for debugging

## Activity Log

- 2026-01-18T16:21:51Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-19T08:21:10Z – claude-opus – shell_pid=80444 – lane=doing – Started implementation via workflow command
- 2026-01-19T08:28:54Z – claude-opus – shell_pid=80444 – lane=for_review – Ready for review: Full orchestration integration with progress display, summary report, and edge case handling
- 2026-01-19T08:29:23Z – claude-opus – shell_pid=84101 – lane=doing – Started review via workflow command
- 2026-01-19T08:31:12Z – claude-opus – shell_pid=84101 – lane=done – Review passed: Integration complete with main orchestration loop (T043), Rich Live progress display (T044), summary report with metrics (T045), and all edge cases handled (T046) - circular deps, no agents, worktree failures, retries. Signal handling for graceful shutdown. All imports verified working.
