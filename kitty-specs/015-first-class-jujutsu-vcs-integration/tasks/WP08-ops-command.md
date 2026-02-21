---
work_package_id: "WP08"
title: "Ops Command"
subtasks:
  - "T045"
  - "T046"
  - "T047"
  - "T048"
  - "T049"
  - "T050"
phase: "Phase 2 - Command Updates"
lane: "done"
priority: "P3"
dependencies: ["WP03", "WP04"]
assignee: "__AGENT__"
agent: "__AGENT__"
shell_pid: "28708"
review_status: "approved"
reviewed_by: "Robert Douglass"
history:
  - timestamp: "2026-01-17T10:38:23Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP08 – Ops Command

## Objectives & Success Criteria

**Goal**: Implement new `spec-kitty ops` command for operation history and undo.

**Success Criteria**:

- `spec-kitty ops log` shows recent operations
- `spec-kitty ops undo` reverts last operation (jj only)
- For git: uses reflog as operation log equivalent
- For jj: leverages jj operation log
- Capability checking prevents undo on git (graceful error)
- Command is registered and accessible via CLI

**User Stories Addressed**: US7 (P3)
**Requirements**: FR-020, FR-021, FR-022, FR-023

## Context & Constraints

**Reference Documents**:

- `kitty-specs/015-first-class-jujutsu-vcs-integration/contracts/vcs-protocol.py` - OperationInfo
- `kitty-specs/015-first-class-jujutsu-vcs-integration/data-model.md` - OperationInfo fields

**Architecture Decisions**:

- Unified `ops` command with different capabilities per backend
- jj: Full operation log with undo
- git: Reflog as read-only operation history
- Capability checking prevents unavailable operations

**Constraints**:

- undo only available for jj (git has no equivalent)
- Operation log format differs between backends
- Must detect current context (workspace or repo)

**Key jj Commands**:

- `jj op log` - Show operation history
- `jj op undo` - Undo last operation
- `jj op restore <op-id>` - Restore to specific operation

**Key git Commands**:

- `git reflog` - Show reference log (approximate equivalent)

## Subtasks & Detailed Guidance

### Subtask T045 – Create ops.py with command structure

**Purpose**: Create the new ops command file with subcommands.

**Steps**:

1. Create `src/specify_cli/cli/commands/ops.py`
2. Set up command structure with subcommands:

   ```python
   import typer
   from rich.console import Console
   from rich.table import Table

   from specify_cli.core.vcs import get_vcs, VCSBackend

   app = typer.Typer()
   console = Console()

   @app.command()
   def log(
       limit: int = typer.Option(20, "--limit", "-n", help="Number of operations to show"),
   ):
       """Show operation history."""
       pass

   @app.command()
   def undo(
       operation_id: str = typer.Argument(None, help="Operation ID to undo (jj only)"),
   ):
       """Undo last operation (jj only)."""
       pass
   ```

**Files**:

- Create: `src/specify_cli/cli/commands/ops.py`

---

### Subtask T046 – Implement ops log subcommand

**Purpose**: Show operation history for both backends.

**Steps**:

1. Implement log display:

   ```python
   @app.command()
   def log(
       limit: int = typer.Option(20, "--limit", "-n", help="Number of operations to show"),
   ):
       """Show operation history."""
       workspace_path = Path.cwd()
       vcs = get_vcs(workspace_path)

       if vcs.backend == VCSBackend.JUJUTSU:
           from specify_cli.core.vcs.jujutsu import jj_get_operation_log
           ops = jj_get_operation_log(workspace_path, limit=limit)
       else:
           from specify_cli.core.vcs.git import git_get_reflog
           ops = git_get_reflog(workspace_path, limit=limit)

       _display_operations(ops, vcs.backend)
   ```

2. Create table display:

   ```python
   def _display_operations(ops: list[OperationInfo], backend: VCSBackend) -> None:
       table = Table(title=f"Operation History ({backend.value})")
       table.add_column("ID", style="cyan")
       table.add_column("Time", style="dim")
       table.add_column("Description")
       if backend == VCSBackend.JUJUTSU:
           table.add_column("Undoable", style="green")

       for op in ops:
           row = [op.operation_id[:12], op.timestamp.strftime("%Y-%m-%d %H:%M"), op.description]
           if backend == VCSBackend.JUJUTSU:
               row.append("✓" if op.undoable else "")
           table.add_row(*row)

       console.print(table)
   ```

**Files**:

- Modify: `src/specify_cli/cli/commands/ops.py`

---

### Subtask T047 – Implement ops undo subcommand

**Purpose**: Implement operation undo for jj (with capability check).

**Steps**:

1. Implement undo with capability check:

   ```python
   @app.command()
   def undo(
       operation_id: str = typer.Argument(None, help="Operation ID to undo (jj only)"),
   ):
       """Undo last operation (jj only)."""
       workspace_path = Path.cwd()
       vcs = get_vcs(workspace_path)

       # Capability check
       if not vcs.capabilities.supports_operation_undo:
           console.print(f"[red]✗ Undo not supported for {vcs.backend.value}[/red]")
           console.print("[dim]Git does not have reversible operation history.[/dim]")
           console.print("[dim]Consider using 'git reset' or 'git revert' manually.[/dim]")
           raise typer.Exit(1)

       # jj undo
       from specify_cli.core.vcs.jujutsu import jj_undo_operation
       success = jj_undo_operation(workspace_path, operation_id)

       if success:
           console.print("[green]✓ Operation undone[/green]")
       else:
           console.print("[red]✗ Undo failed[/red]")
           raise typer.Exit(1)
   ```

**Files**:

- Modify: `src/specify_cli/cli/commands/ops.py`

**Notes**:

- Only jj supports true operation undo
- git users get helpful error message with alternatives

---

### Subtask T048 – Add capability checking utility

**Purpose**: Create reusable capability check decorator/function.

**Steps**:

1. Add capability checking utility:

   ```python
   def require_capability(capability: str, backend_name: str | None = None):
       """Decorator to require a VCS capability."""
       def decorator(func):
           @functools.wraps(func)
           def wrapper(*args, **kwargs):
               workspace_path = Path.cwd()
               vcs = get_vcs(workspace_path)

               if not getattr(vcs.capabilities, capability, False):
                   backend = backend_name or vcs.backend.value
                   console.print(f"[red]✗ {capability} not supported for {backend}[/red]")
                   raise typer.Exit(1)

               return func(*args, **kwargs)
           return wrapper
       return decorator
   ```

2. Alternative: inline capability check (simpler, already shown in T047)

**Files**:

- Modify: `src/specify_cli/cli/commands/ops.py` or create utility module

**Notes**:

- Decorator approach is cleaner for multiple commands
- Inline check is simpler for single use case
- Choose based on how many commands need capability checks

---

### Subtask T049 – Register ops command in CLI

**Purpose**: Add ops command to spec-kitty CLI.

**Steps**:

1. Find main CLI registration (likely `src/specify_cli/cli/main.py`)
2. Add ops command:

   ```python
   from specify_cli.cli.commands import ops
   app.add_typer(ops.app, name="ops")
   ```

3. Verify command appears in `spec-kitty --help`
4. Verify subcommands work:
   - `spec-kitty ops --help`
   - `spec-kitty ops log --help`
   - `spec-kitty ops undo --help`

**Files**:

- Modify: `src/specify_cli/cli/main.py` (or equivalent)

---

### Subtask T050 – Create test_ops.py [P]

**Purpose**: Test ops command for both backends.

**Steps**:

1. Create `tests/specify_cli/cli/commands/test_ops.py`
2. Add parametrized tests:

   ```python
   @pytest.mark.parametrize("backend", [
       "git",
       pytest.param("jj", marks=pytest.mark.jj),
   ])
   def test_ops_log_shows_history(tmp_path, backend):
       # Setup repo with some operations
       # Run ops log
       # Verify output contains operations
       pass

   @pytest.mark.jj
   def test_ops_undo_works_for_jj(tmp_path):
       # Setup jj repo
       # Make some operations
       # Run ops undo
       # Verify operation was undone
       pass

   def test_ops_undo_fails_for_git(tmp_path):
       # Setup git repo
       # Run ops undo
       # Verify graceful error message
       pass

   def test_ops_log_respects_limit(tmp_path):
       # Setup repo with many operations
       # Run ops log --limit 5
       # Verify only 5 operations shown
       pass
   ```

**Files**:

- Create: `tests/specify_cli/cli/commands/test_ops.py`

**Parallel?**: Yes - can start once T045-T049 scaffolded

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| User confusion about undo availability | Clear error message with alternatives |
| Operation ID format differences | Truncate display, accept partial IDs |
| jj op log parsing changes | Pin min version, test with CI |

## Definition of Done Checklist

- [x] T045: ops.py created with command structure
- [x] T046: ops log subcommand shows history for both backends
- [x] T047: ops undo subcommand works for jj
- [x] T048: Capability checking implemented
- [x] T049: ops command registered in CLI
- [x] T050: Parametrized tests pass
- [x] `spec-kitty ops log` works in git workspace
- [x] `spec-kitty ops log` works in jj workspace
- [x] `spec-kitty ops undo` works in jj workspace
- [x] `spec-kitty ops undo` gives helpful error in git workspace

## Review Guidance

**Key Checkpoints**:

1. Verify ops log shows meaningful history for both backends
2. Verify undo only available for jj (graceful error for git)
3. Verify operation IDs are usable (not too long)
4. Verify --limit flag works
5. Verify helpful error messages for unsupported operations
6. Test in both git and jj workspaces

## Activity Log

- 2026-01-17T10:38:23Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-17T13:09:21Z – **AGENT** – shell_pid=27357 – lane=doing – Started implementation via workflow command
- 2026-01-17T13:18:11Z – **AGENT** – shell_pid=27357 – lane=for_review – Ready for review: ops command with log, undo, restore subcommands. 19 tests passing.
- 2026-01-17T13:18:51Z – **AGENT** – shell_pid=28708 – lane=doing – Started review via workflow command
- 2026-01-17T13:21:30Z – **AGENT** – shell_pid=28708 – lane=done – Review passed: ops command implemented with log/undo/restore subcommands, capability checking for jj-only features, helpful git alternatives, 19 tests passing
