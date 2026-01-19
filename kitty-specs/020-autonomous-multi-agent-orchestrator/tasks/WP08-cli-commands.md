---
work_package_id: "WP08"
subtasks:
  - "T038"
  - "T039"
  - "T040"
  - "T041"
  - "T042"
title: "CLI Commands"
phase: "Phase 3 - CLI & Integration"
lane: "doing"
assignee: ""
agent: "claude-opus"
shell_pid: "77685"
review_status: ""
reviewed_by: ""
dependencies:
  - "WP05"
  - "WP06"
  - "WP07"
history:
  - timestamp: "2026-01-18T16:21:51Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP08 – CLI Commands

## Objectives & Success Criteria

Implement the `spec-kitty orchestrate` CLI command with all options.

**Success Criteria**:
- `spec-kitty orchestrate --feature <slug>` starts orchestration
- `spec-kitty orchestrate --status` shows progress
- `spec-kitty orchestrate --resume` continues paused orchestration
- `spec-kitty orchestrate --abort` stops and cleans up
- Help text is clear and complete

## Context & Constraints

**Reference Documents**:
- [plan.md](../plan.md) - CLI commands section
- [quickstart.md](../quickstart.md) - Usage examples
- [spec.md](../spec.md) - User Story 1, 3, 5 (CLI requirements)

**Existing Patterns**:
- `src/specify_cli/cli/commands/` - Existing command structure
- Uses `typer` for CLI framework

**Implementation Command**:
```bash
spec-kitty implement WP08 --base WP07
```

## Subtasks & Detailed Guidance

### Subtask T038 – Implement `spec-kitty orchestrate --feature`

**Purpose**: Start new orchestration for a feature.

**Steps**:
1. Create `src/specify_cli/cli/commands/orchestrate.py`
2. Implement main command:
   ```python
   import typer
   from rich.console import Console
   from pathlib import Path

   app = typer.Typer()
   console = Console()

   @app.command()
   def orchestrate(
       feature: str = typer.Option(None, "--feature", "-f", help="Feature slug to orchestrate"),
       status: bool = typer.Option(False, "--status", "-s", help="Show orchestration status"),
       resume: bool = typer.Option(False, "--resume", "-r", help="Resume paused orchestration"),
       abort: bool = typer.Option(False, "--abort", "-a", help="Abort and cleanup"),
   ):
       """Orchestrate autonomous feature implementation."""
       if status:
           return show_status()
       if resume:
           return resume_orchestration()
       if abort:
           return abort_orchestration()
       if feature:
           return start_orchestration(feature)

       # Auto-detect feature from current directory
       feature = detect_current_feature()
       if feature:
           return start_orchestration(feature)

       console.print("[red]Error:[/red] No feature specified. Use --feature <slug>")
       raise typer.Exit(1)
   ```

3. Implement start function:
   ```python
   async def start_orchestration(feature_slug: str):
       """Start new orchestration for feature."""
       repo_root = find_repo_root()
       feature_dir = repo_root / "kitty-specs" / feature_slug

       # Validate feature exists
       if not feature_dir.exists():
           console.print(f"[red]Error:[/red] Feature not found: {feature_slug}")
           raise typer.Exit(1)

       # Check for existing orchestration
       if has_active_orchestration(repo_root):
           console.print("[red]Error:[/red] Orchestration already in progress")
           console.print("Use --status to check progress, --resume to continue, or --abort to cancel")
           raise typer.Exit(1)

       # Load config
       config = load_config(repo_root / ".kittify" / "agents.yaml")

       # Build dependency graph
       graph = build_wp_graph(feature_dir)
       validate_graph(graph)

       # Initialize state
       state = OrchestrationRun(
           run_id=str(uuid.uuid4()),
           feature_slug=feature_slug,
           started_at=datetime.utcnow(),
           ...
       )

       # Run orchestration loop
       await run_orchestration_loop(state, config, feature_dir)
   ```

**Notes**:
- Auto-detect feature from current directory if not specified
- Validate feature exists before starting
- Check no other orchestration in progress

---

### Subtask T039 – Implement `spec-kitty orchestrate --status`

**Purpose**: Show current orchestration progress.

**Steps**:
1. Implement status display:
   ```python
   def show_status():
       """Display current orchestration status."""
       repo_root = find_repo_root()
       state = load_state(repo_root)

       if not state:
           console.print("No orchestration in progress")
           return

       # Calculate progress
       total = state.wps_total
       completed = state.wps_completed
       failed = state.wps_failed
       in_progress = sum(
           1 for wp in state.work_packages.values()
           if wp.status in [WPStatus.IMPLEMENTATION, WPStatus.REVIEW]
       )

       # Display
       console.print(Panel(
           f"[bold]Orchestration: {state.feature_slug}[/bold]\n"
           f"Status: {state.status.value}\n"
           f"Progress: {completed}/{total} WPs ({100*completed/total:.1f}%)\n"
           f"\n[bold]Active:[/bold]",
           title="Orchestration Status",
       ))

       # Show active WPs
       for wp_id, wp in state.work_packages.items():
           if wp.status == WPStatus.IMPLEMENTATION:
               agent = wp.implementation_agent
               elapsed = (datetime.utcnow() - wp.implementation_started).seconds
               console.print(f"  {wp_id}: {agent} (implementation) - {elapsed}s")
           elif wp.status == WPStatus.REVIEW:
               agent = wp.review_agent
               elapsed = (datetime.utcnow() - wp.review_started).seconds
               console.print(f"  {wp_id}: {agent} (review) - {elapsed}s")

       # Show completed and pending
       completed_wps = [wp_id for wp_id, wp in state.work_packages.items() if wp.status == WPStatus.COMPLETED]
       pending_wps = [wp_id for wp_id, wp in state.work_packages.items() if wp.status == WPStatus.PENDING]

       console.print(f"\n[green]Completed:[/green] {', '.join(completed_wps) or 'None'}")
       console.print(f"[yellow]Pending:[/yellow] {', '.join(pending_wps) or 'None'}")
   ```

**Parallel?**: Yes - can develop alongside T040, T041

---

### Subtask T040 – Implement `spec-kitty orchestrate --resume`

**Purpose**: Resume paused orchestration.

**Steps**:
1. Implement resume:
   ```python
   async def resume_orchestration():
       """Resume paused orchestration."""
       repo_root = find_repo_root()
       state = load_state(repo_root)

       if not state:
           console.print("[red]Error:[/red] No orchestration to resume")
           raise typer.Exit(1)

       if state.status == OrchestrationStatus.COMPLETED:
           console.print("Orchestration already completed")
           return

       if state.status == OrchestrationStatus.RUNNING:
           console.print("Orchestration is already running")
           return

       # Set to running
       state.status = OrchestrationStatus.RUNNING
       save_state(state, repo_root)

       # Load config and continue
       config = load_config(repo_root / ".kittify" / "agents.yaml")
       feature_dir = repo_root / "kitty-specs" / state.feature_slug

       console.print(f"Resuming orchestration for {state.feature_slug}...")
       await run_orchestration_loop(state, config, feature_dir)
   ```

**Parallel?**: Yes

---

### Subtask T041 – Implement `spec-kitty orchestrate --abort`

**Purpose**: Stop orchestration and clean up.

**Steps**:
1. Implement abort:
   ```python
   async def abort_orchestration():
       """Abort orchestration and cleanup."""
       repo_root = find_repo_root()
       state = load_state(repo_root)

       if not state:
           console.print("No orchestration to abort")
           return

       console.print(f"Aborting orchestration for {state.feature_slug}...")

       # Kill any running processes
       # (This requires tracking PIDs in state, or using process groups)

       # Update state
       state.status = OrchestrationStatus.FAILED
       state.completed_at = datetime.utcnow()
       save_state(state, repo_root)

       # Optionally cleanup worktrees
       cleanup = typer.confirm("Remove created worktrees?", default=False)
       if cleanup:
           for wp_id, wp in state.work_packages.items():
               if wp.worktree_path and wp.worktree_path.exists():
                   # Remove worktree
                   subprocess.run(["git", "worktree", "remove", str(wp.worktree_path), "--force"])

       console.print("[yellow]Orchestration aborted[/yellow]")
   ```

**Parallel?**: Yes

---

### Subtask T042 – Add help text and CLI documentation

**Purpose**: Ensure CLI is well-documented.

**Steps**:
1. Add comprehensive help text:
   ```python
   app = typer.Typer(
       name="orchestrate",
       help="""
       Orchestrate autonomous feature implementation.

       Runs AI agents in parallel to implement work packages,
       with automatic review and fallback handling.

       Examples:
         spec-kitty orchestrate --feature 020-my-feature
         spec-kitty orchestrate --status
         spec-kitty orchestrate --resume
         spec-kitty orchestrate --abort
       """,
   )
   ```

2. Register command in main CLI:
   ```python
   # In src/specify_cli/cli/__init__.py or main.py
   from .commands.orchestrate import app as orchestrate_app
   main_app.add_typer(orchestrate_app, name="orchestrate")
   ```

3. Add `--help` examples for each option

**Notes**:
- Help should show common workflows
- Include example feature slug

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Ctrl+C during orchestration | Signal handler saves state |
| Multiple orchestrations | Check for existing state |
| Orphan processes | Track PIDs in state |

## Definition of Done Checklist

- [ ] `--feature` starts new orchestration
- [ ] `--status` shows progress correctly
- [ ] `--resume` continues from paused state
- [ ] `--abort` stops and offers cleanup
- [ ] Help text is clear and complete
- [ ] Command registered in main CLI

## Review Guidance

- Test each flag works correctly
- Verify error messages are helpful
- Check status output is readable
- Test resume from paused state
- Verify abort cleans up properly

## Activity Log

- 2026-01-18T16:21:51Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-19T08:14:58Z – claude-opus – shell_pid=77685 – lane=doing – Started implementation via workflow command
