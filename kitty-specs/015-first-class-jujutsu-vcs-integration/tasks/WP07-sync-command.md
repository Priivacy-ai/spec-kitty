---
work_package_id: "WP07"
title: "Sync Command"
subtasks:
  - "T039"
  - "T040"
  - "T041"
  - "T042"
  - "T043"
  - "T044"
phase: "Phase 2 - Command Updates"
lane: "done"
priority: "P2"
dependencies: ["WP03", "WP04"]
assignee: ""
agent: "__AGENT__"
shell_pid: "16064"
review_status: "approved"
reviewed_by: "Robert Douglass"
history:
  - timestamp: "2026-01-17T10:38:23Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP07 – Sync Command

## Objectives & Success Criteria

**Goal**: Implement new `spec-kitty sync` command for workspace synchronization.

**Success Criteria**:
- `spec-kitty sync` updates stale workspace for both VCS backends
- Conflicts reported with file paths and line ranges
- For jj: sync succeeds even with conflicts (stores them)
- For git: sync may fail on conflicts (reports them)
- `--repair` flag attempts workspace recovery
- Command is registered and accessible via CLI

**User Stories Addressed**: US4 (P2), US5 (P2), US6 (P2)
**Requirements**: FR-013, FR-014, FR-015, FR-016, FR-017, FR-018, FR-019

## Context & Constraints

**Reference Documents**:
- `kitty-specs/015-first-class-jujutsu-vcs-integration/contracts/vcs-protocol.py` - sync_workspace signature
- `kitty-specs/015-first-class-jujutsu-vcs-integration/data-model.md` - SyncResult, ConflictInfo

**Architecture Decisions**:
- Unified `sync` command works for both backends
- Key difference: jj sync always succeeds, git may fail on conflicts
- SyncResult includes changes_integrated for automation

**Constraints**:
- Must detect current workspace context automatically
- Conflict reporting should be actionable (file + lines)
- --repair is best-effort (may not recover all scenarios)

## Subtasks & Detailed Guidance

### Subtask T039 – Create sync.py with command structure

**Purpose**: Create the new sync command file.

**Steps**:
1. Create `src/specify_cli/cli/commands/sync.py`
2. Set up basic command structure:
   ```python
   import typer
   from rich.console import Console

   from specify_cli.core.vcs import get_vcs, SyncStatus

   app = typer.Typer()
   console = Console()

   @app.callback(invoke_without_command=True)
   def sync(
       ctx: typer.Context,
       repair: bool = typer.Option(False, "--repair", help="Attempt workspace recovery"),
   ):
       """Synchronize workspace with upstream changes."""
       # Implementation here
   ```

**Files**:
- Create: `src/specify_cli/cli/commands/sync.py`

---

### Subtask T040 – Implement sync workflow

**Purpose**: Implement the core sync logic.

**Steps**:
1. Detect current workspace context:
   ```python
   def _detect_workspace_context() -> tuple[Path, Path]:
       """Detect current workspace and feature paths."""
       cwd = Path.cwd()
       # Check if we're in a worktree
       # Find feature from path or branch name
       return workspace_path, feature_path
   ```
2. Call VCS sync:
   ```python
   vcs = get_vcs(workspace_path)
   result = vcs.sync_workspace(workspace_path)
   ```
3. Display results:
   ```python
   if result.status == SyncStatus.UP_TO_DATE:
       console.print("[green]✓ Already up to date[/green]")
   elif result.status == SyncStatus.SYNCED:
       console.print(f"[green]✓ Synced[/green] - {result.files_updated} files updated")
       _display_changes_integrated(result.changes_integrated)
   elif result.status == SyncStatus.CONFLICTS:
       console.print(f"[yellow]⚠ Synced with conflicts[/yellow]")
       _display_conflicts(result.conflicts)
   elif result.status == SyncStatus.FAILED:
       console.print(f"[red]✗ Sync failed[/red]: {result.message}")
   ```

**Files**:
- Modify: `src/specify_cli/cli/commands/sync.py`

---

### Subtask T041 – Add conflict reporting

**Purpose**: Display conflicts with actionable details.

**Steps**:
1. Implement conflict display:
   ```python
   def _display_conflicts(conflicts: list[ConflictInfo]) -> None:
       console.print(f"\n[yellow]Conflicts ({len(conflicts)} files):[/yellow]")
       for c in conflicts:
           console.print(f"  • {c.file_path}")
           if c.line_ranges:
               for start, end in c.line_ranges:
                   console.print(f"    Lines {start}-{end}")
           console.print(f"    Type: {c.conflict_type.value}")
   ```
2. Add helpful resolution hints:
   ```python
   console.print("\n[dim]To resolve conflicts:[/dim]")
   console.print("[dim]  1. Edit the conflicted files to resolve markers[/dim]")
   console.print("[dim]  2. Continue your work (jj) or commit resolution (git)[/dim]")
   ```

**Files**:
- Modify: `src/specify_cli/cli/commands/sync.py`

---

### Subtask T042 – Add --repair flag

**Purpose**: Implement workspace recovery functionality.

**Steps**:
1. Add repair logic:
   ```python
   if repair:
       console.print("[yellow]Attempting workspace recovery...[/yellow]")
       vcs = get_vcs(workspace_path)

       if vcs.backend == VCSBackend.JUJUTSU:
           # jj: Use operation log to restore
           from specify_cli.core.vcs.jujutsu import jj_undo_operation
           success = jj_undo_operation(workspace_path)
       else:
           # git: Limited recovery via reset
           success = _git_repair(workspace_path)

       if success:
           console.print("[green]✓ Recovery successful[/green]")
       else:
           console.print("[red]✗ Recovery failed[/red]")
           console.print("Manual intervention may be required")
   ```
2. Document limitations in help text

**Files**:
- Modify: `src/specify_cli/cli/commands/sync.py`

**Notes**:
- jj has better recovery via operation log
- git recovery is more limited (may lose work)

---

### Subtask T043 – Register sync command in CLI

**Purpose**: Add sync command to spec-kitty CLI.

**Steps**:
1. Find main CLI registration (likely `src/specify_cli/cli/main.py` or similar)
2. Add sync command:
   ```python
   from specify_cli.cli.commands import sync
   app.add_typer(sync.app, name="sync")
   ```
3. Verify command appears in `spec-kitty --help`

**Files**:
- Modify: `src/specify_cli/cli/main.py` (or equivalent)

---

### Subtask T044 – Create test_sync.py [P]

**Purpose**: Test sync command for both backends.

**Steps**:
1. Create `tests/specify_cli/cli/commands/test_sync.py`
2. Add parametrized tests:
   ```python
   @pytest.mark.parametrize("backend", [
       "git",
       pytest.param("jj", marks=pytest.mark.jj),
   ])
   def test_sync_up_to_date(tmp_path, backend):
       # Create workspace, verify already up to date
       pass

   @pytest.mark.parametrize("backend", [
       "git",
       pytest.param("jj", marks=pytest.mark.jj),
   ])
   def test_sync_with_changes(tmp_path, backend):
       # Create workspace, make changes in base, sync
       pass

   @pytest.mark.jj
   def test_sync_with_conflicts_jj_succeeds(tmp_path):
       # jj: sync should succeed even with conflicts
       pass

   def test_sync_with_conflicts_git_reports(tmp_path):
       # git: sync should report conflicts
       pass
   ```

**Files**:
- Create: `tests/specify_cli/cli/commands/test_sync.py`

**Parallel?**: Yes - can start once T039-T043 scaffolded

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Context detection failure | Clear error messages, fallback prompts |
| Conflict handling differences | Abstract in SyncResult, test both backends |
| Repair data loss | Warn user, document limitations |

## Definition of Done Checklist

- [ ] T039: sync.py created with command structure
- [ ] T040: Sync workflow implemented for both backends
- [ ] T041: Conflict reporting with file paths and lines
- [ ] T042: --repair flag with recovery logic
- [ ] T043: Sync command registered in CLI
- [ ] T044: Parametrized tests pass
- [ ] `spec-kitty sync` works in git workspace
- [ ] `spec-kitty sync` works in jj workspace
- [ ] Conflicts displayed with actionable info

## Review Guidance

**Key Checkpoints**:
1. Verify jj sync succeeds with conflicts (key differentiator)
2. Verify git sync reports conflicts appropriately
3. Verify conflict display is actionable
4. Verify changes_integrated displayed for automation
5. Verify --repair has appropriate warnings
6. Test in both git and jj workspaces

## Activity Log

- 2026-01-17T10:38:23Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-17T12:52:45Z – __AGENT__ – shell_pid=10296 – lane=doing – Started implementation via workflow command
- 2026-01-17T13:00:39Z – __AGENT__ – shell_pid=10296 – lane=for_review – Sync command implemented with git/jj support, conflict reporting, --repair flag, and 21 tests passing
- 2026-01-17T13:04:21Z – __AGENT__ – shell_pid=16064 – lane=doing – Started review via workflow command
- 2026-01-17T13:07:58Z – __AGENT__ – shell_pid=16064 – lane=done – Review passed: sync command correctly implements git/jj workspace synchronization with conflict reporting, --repair flag, and 21 tests
