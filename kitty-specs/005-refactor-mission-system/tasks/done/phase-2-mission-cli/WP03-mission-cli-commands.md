---
work_package_id: "WP03"
subtasks:
  - "T017"
  - "T018"
  - "T019"
  - "T020"
  - "T021"
  - "T022"
  - "T023"
  - "T024"
title: "Mission CLI Commands"
phase: "Phase 2 - Mission CLI"
lane: "done"
assignee: "claude"
agent: "claude"
shell_pid: "88714"
history:
  - timestamp: "2025-01-16T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 – Mission CLI Commands

## Objectives & Success Criteria

**Goal**: Implement complete `spec-kitty mission` command group enabling users to list, view, and switch between missions from the command line.

**Success Criteria**:
- `spec-kitty mission list` displays all available missions with descriptions
- `spec-kitty mission current` shows active mission details (name, domain, workflow, validation)
- `spec-kitty mission info <name>` displays specific mission configuration without switching
- `spec-kitty mission switch <name>` validates preconditions and switches missions safely
- Mission switching validates: no active worktrees, git clean, target exists
- Helpful error messages when validation fails
- Integration tests verify all commands work end-to-end
- All 8 subtasks (T017-T024) completed

## Context & Constraints

**Problem Statement**: Mission switching was spec'd in original mission system design but never implemented:
- `set_active_mission()` function exists in mission.py:339-367
- README mentions "planned for a future release" (line 797)
- Spec-code divergence creates confusion

**User Story** (Spec User Story 4):
> "I want to run `spec-kitty mission switch research` to alternate between research and software-dev missions within a single project, so I can conduct research that informs implementation without managing multiple separate projects."

**Use Case**: Research security → implement fixes → research performance → optimize

**Supporting Documents**:
- Spec: `kitty-specs/005-refactor-mission-system/spec.md` (User Story 4, FR-013 through FR-019)
- Plan: `kitty-specs/005-refactor-mission-system/plan.md` (Architecture Decision #3: Python API-first with CLI wrappers)
- Data Model: `kitty-specs/005-refactor-mission-system/data-model.md` (MissionSwitchValidation model)

**Design Decisions**:
- **Architecture**: Python API-first, Typer CLI as thin wrappers
- **Validation**: Reuse WP01 guards module for git-clean checks
- **Integration**: Extend existing `set_active_mission()` function
- **Output**: Rich console formatting for user-friendly display

**Existing Code to Leverage**:
```python
# src/specify_cli/mission.py - Already exists
def get_active_mission(project_root: Optional[Path] = None) -> Mission
def list_available_missions(kittify_dir: Optional[Path] = None) -> List[str]
def get_mission_by_name(mission_name: str, kittify_dir: Optional[Path] = None) -> Mission
def set_active_mission(mission_name: str, kittify_dir: Optional[Path] = None) -> None
```

**Validation Requirements** (from spec FR-017):
- No active worktrees exist
- No uncommitted git changes
- Target mission exists
- Warning if new mission requires missing artifacts

## Subtasks & Detailed Guidance

### Subtask T017 – Create mission.py CLI module

**Purpose**: Establish Typer command group structure for mission management commands.

**Steps**:
1. Create file: `src/specify_cli/cli/commands/mission.py`
2. Add imports:
   ```python
   """Mission management CLI commands."""
   from pathlib import Path
   from typing import Optional

   import typer
   from rich.console import Console
   from rich.table import Table
   from rich.panel import Panel

   from specify_cli.mission import (
       get_active_mission,
       list_available_missions,
       get_mission_by_name,
       set_active_mission,
       MissionError,
       MissionNotFoundError,
   )
   from specify_cli.guards import validate_git_clean
   ```

3. Create Typer app:
   ```python
   app = typer.Typer(
       name="mission",
       help="Manage Spec Kitty missions (domain modes)",
       no_args_is_help=True
   )

   console = Console()
   ```

4. Add stub functions for each subcommand (implementation in T018-T021):
   ```python
   @app.command("list")
   def list_cmd():
       """List all available missions."""
       pass

   @app.command("current")
   def current_cmd():
       """Show currently active mission."""
       pass

   @app.command("info")
   def info_cmd(mission_name: str = typer.Argument(..., help="Mission name to display")):
       """Show details for a specific mission."""
       pass

   @app.command("switch")
   def switch_cmd(
       mission_name: str = typer.Argument(..., help="Mission name to switch to"),
       force: bool = typer.Option(False, "--force", help="Skip confirmation prompts")
   ):
       """Switch to a different mission."""
       pass
   ```

**Files**: `src/specify_cli/cli/commands/mission.py` (new)

**Parallel?**: No (foundation for other subtasks)

**Notes**: Follow existing init.py command pattern for consistency.

---

### Subtask T018 – Implement list_cmd()

**Purpose**: Display all available missions in formatted table.

**Steps**:
1. Implement list_cmd():
   ```python
   @app.command("list")
   def list_cmd():
       """List all available missions."""
       try:
           kittify_dir = Path.cwd() / ".kittify"
           missions = list_available_missions(kittify_dir)

           if not missions:
               console.print("[yellow]No missions found in .kittify/missions/[/yellow]")
               return

           # Get active mission to highlight it
           try:
               active = get_active_mission()
               active_name = active.path.name
           except MissionError:
               active_name = None

           # Create rich table
           table = Table(title="Available Missions", show_header=True)
           table.add_column("Mission", style="cyan")
           table.add_column("Domain", style="magenta")
           table.add_column("Description", style="white")
           table.add_column("Active", style="green")

           for mission_name in missions:
               try:
                   mission = get_mission_by_name(mission_name, kittify_dir)
                   is_active = "✓" if mission_name == active_name else ""
                   table.add_row(
                       mission.name,
                       mission.domain,
                       mission.description,
                       is_active
                   )
               except Exception as e:
                   # Skip broken missions
                   table.add_row(
                       mission_name,
                       "[red]error[/red]",
                       f"[red]{str(e)}[/red]",
                       ""
                   )

           console.print(table)

       except Exception as e:
           console.print(f"[red]Error listing missions:[/red] {e}")
           raise typer.Exit(1)
   ```

2. Test manually: `spec-kitty mission list`

**Files**: `src/specify_cli/cli/commands/mission.py`

**Parallel?**: Yes (independent from info_cmd and current_cmd)

**Notes**: Use Rich tables for formatted output, similar to other CLI commands.

---

### Subtask T019 – Implement current_cmd()

**Purpose**: Display currently active mission with full configuration details.

**Steps**:
1. Implement current_cmd():
   ```python
   @app.command("current")
   def current_cmd():
       """Show currently active mission."""
       try:
           mission = get_active_mission()

           # Create detailed panel
           details = [
               f"[cyan]Name:[/cyan] {mission.name}",
               f"[cyan]Domain:[/cyan] {mission.domain}",
               f"[cyan]Version:[/cyan] {mission.version}",
               f"[cyan]Path:[/cyan] {mission.path}",
               "",
               "[cyan]Workflow Phases:[/cyan]"
           ]

           for phase in mission.config.workflow.phases:
               details.append(f"  • {phase.name} - {phase.description}")

           details.append("")
           details.append("[cyan]Required Artifacts:[/cyan]")
           for artifact in mission.config.artifacts.required:
               details.append(f"  • {artifact}")

           details.append("")
           details.append("[cyan]Validation Checks:[/cyan]")
           for check in mission.config.validation.checks:
               details.append(f"  • {check}")

           panel = Panel(
               "\n".join(details),
               title="Active Mission",
               border_style="cyan"
           )
           console.print(panel)

       except MissionNotFoundError as e:
           console.print(f"[red]Error:[/red] {e}")
           raise typer.Exit(1)
       except Exception as e:
           console.print(f"[red]Unexpected error:[/red] {e}")
           raise typer.Exit(1)
   ```

2. Test manually: `spec-kitty mission current`

**Files**: `src/specify_cli/cli/commands/mission.py`

**Parallel?**: Yes (independent from list and info)

**Notes**: Display comprehensive details - users reference this to understand active mission.

---

### Subtask T020 – Implement info_cmd()

**Purpose**: Display specific mission details without switching to it.

**Steps**:
1. Implement info_cmd():
   ```python
   @app.command("info")
   def info_cmd(mission_name: str = typer.Argument(..., help="Mission name to display")):
       """Show details for a specific mission."""
       try:
           kittify_dir = Path.cwd() / ".kittify"
           mission = get_mission_by_name(mission_name, kittify_dir)

           # Similar to current_cmd but for specified mission
           details = [
               f"[cyan]Name:[/cyan] {mission.name}",
               f"[cyan]Domain:[/cyan] {mission.domain}",
               f"[cyan]Version:[/cyan] {mission.version}",
               f"[cyan]Description:[/cyan] {mission.description}",
               "",
               "[cyan]Workflow Phases:[/cyan]"
           ]

           for phase in mission.config.workflow.phases:
               details.append(f"  • {phase.name} - {phase.description}")

           details.append("")
           details.append("[cyan]Required Artifacts:[/cyan]")
           for artifact in mission.config.artifacts.required:
               details.append(f"  • {artifact}")

           if mission.config.artifacts.optional:
               details.append("")
               details.append("[cyan]Optional Artifacts:[/cyan]")
               for artifact in mission.config.artifacts.optional:
                   details.append(f"  • {artifact}")

           details.append("")
           details.append("[cyan]Validation Checks:[/cyan]")
           for check in mission.config.validation.checks:
               details.append(f"  • {check}")

           if mission.config.paths:
               details.append("")
               details.append("[cyan]Path Conventions:[/cyan]")
               for key, path in mission.config.paths.items():
                   details.append(f"  • {key}: {path}")

           panel = Panel(
               "\n".join(details),
               title=f"Mission Info: {mission_name}",
               border_style="cyan"
           )
           console.print(panel)

       except MissionNotFoundError as e:
           console.print(f"[red]Mission not found:[/red] {mission_name}")
           console.print(f"\n[yellow]Available missions:[/yellow]")

           missions = list_available_missions(Path.cwd() / ".kittify")
           for m in missions:
               console.print(f"  • {m}")

           raise typer.Exit(1)
       except Exception as e:
           console.print(f"[red]Error:[/red] {e}")
           raise typer.Exit(1)
   ```

2. Test: `spec-kitty mission info research`, `spec-kitty mission info invalid-name`

**Files**: `src/specify_cli/cli/commands/mission.py`

**Parallel?**: Yes (independent from list and current)

**Notes**: Help users explore missions before switching. Include helpful error with available missions list.

---

### Subtask T021 – Implement switch_cmd() with validation

**Purpose**: Core mission switching logic with comprehensive pre-flight validation.

**Steps**:
1. Implement switch_cmd():
   ```python
   @app.command("switch")
   def switch_cmd(
       mission_name: str = typer.Argument(..., help="Mission name to switch to"),
       force: bool = typer.Option(False, "--force", help="Skip confirmation prompts")
   ):
       """Switch to a different mission."""
       try:
           kittify_dir = Path.cwd() / ".kittify"
           project_root = Path.cwd()

           # Validate current state
           console.print("[cyan]Validating mission switch preconditions...[/cyan]")

           # 1. Check for active worktrees
           worktrees_dir = project_root / ".worktrees"
           active_worktrees = []
           if worktrees_dir.exists():
               active_worktrees = [
                   d.name for d in worktrees_dir.iterdir()
                   if d.is_dir() and (d / ".git").exists()
               ]

           if active_worktrees:
               console.print("[red]Cannot switch missions: active features exist[/red]")
               console.print("\n[yellow]Active worktrees:[/yellow]")
               for wt in active_worktrees:
                   console.print(f"  • {wt}")
               console.print("\n[cyan]Suggestion:[/cyan] Complete and merge features first:")
               console.print("  1. cd .worktrees/<feature-name>")
               console.print("  2. Complete feature workflow")
               console.print("  3. /spec-kitty.merge")
               console.print("  4. Then retry mission switch")
               raise typer.Exit(1)

           # 2. Check git is clean
           git_clean_result = validate_git_clean(project_root)
           if not git_clean_result.is_valid:
               console.print("[red]Cannot switch missions: uncommitted changes detected[/red]")
               for error in git_clean_result.errors:
                   console.print(f"  [yellow]{error}[/yellow]")
               console.print("\n[cyan]Suggestion:[/cyan] Commit or stash changes before switching")
               raise typer.Exit(1)

           # 3. Verify target mission exists
           try:
               target_mission = get_mission_by_name(mission_name, kittify_dir)
           except MissionNotFoundError:
               console.print(f"[red]Mission not found:[/red] {mission_name}")
               available = list_available_missions(kittify_dir)
               console.print("\n[yellow]Available missions:[/yellow]")
               for m in available:
                   console.print(f"  • {m}")
               raise typer.Exit(1)

           # 4. Get current mission for comparison
           try:
               current_mission = get_active_mission(project_root)
               current_name = current_mission.path.name
           except MissionError:
               current_name = "unknown"

           if current_name == mission_name:
               console.print(f"[yellow]Already on mission:[/yellow] {target_mission.name}")
               return

           # 5. Check for missing artifacts (warning only)
           warnings = []
           for artifact in target_mission.config.artifacts.required:
               artifact_path = project_root / artifact
               if not artifact_path.exists():
                   warnings.append(f"Target mission requires: {artifact} (not found)")

           # 6. Display switch summary and confirm
           console.print(f"\n[cyan]Switch Summary:[/cyan]")
           console.print(f"  From: {current_mission.name if current_name != 'unknown' else 'Unknown'}")
           console.print(f"  To:   {target_mission.name}")
           console.print(f"  Domain: {target_mission.domain}")

           if warnings:
               console.print(f"\n[yellow]Warnings:[/yellow]")
               for warning in warnings:
                   console.print(f"  • {warning}")
               console.print("\n[dim]You can create missing artifacts after switching.[/dim]")

           if not force:
               confirm = typer.confirm("\nProceed with mission switch?")
               if not confirm:
                   console.print("[yellow]Mission switch cancelled[/yellow]")
                   raise typer.Exit(0)

           # 7. Perform the switch
           console.print("\n[cyan]Switching mission...[/cyan]")
           set_active_mission(mission_name, kittify_dir)

           console.print(f"[green]✓ Switched to mission:[/green] {target_mission.name}")
           console.print(f"\n[cyan]Next steps:[/cyan]")
           console.print("  • Run /spec-kitty.specify to create a new feature")
           console.print("  • New features will use templates from this mission")
           console.print("  • Verify with: spec-kitty mission current")

       except typer.Exit:
           raise
       except Exception as e:
           console.print(f"[red]Error switching mission:[/red] {e}")
           raise typer.Exit(1)
   ```

2. Test all validation scenarios

**Files**: `src/specify_cli/cli/commands/mission.py`

**Parallel?**: No (complex core logic)

**Notes**: Most complex command - extensive validation before switch. Follow spec FR-017 exactly.

---

### Subtask T022 – Register mission command group

**Purpose**: Make mission commands available in main CLI.

**Steps**:
1. Locate main CLI entry point: `src/specify_cli/cli/__init__.py` or `src/specify_cli/__init__.py`
2. Import mission command group:
   ```python
   from specify_cli.cli.commands.mission import app as mission_app
   ```

3. Register with main CLI app:
   ```python
   # Add to main typer app
   app.add_typer(mission_app, name="mission")
   ```

4. Test registration: `spec-kitty mission --help`
5. Verify subcommands show: `spec-kitty --help` should list "mission" group

**Files**: `src/specify_cli/cli/__init__.py` or main CLI entry point

**Parallel?**: No (depends on T017-T021)

**Notes**: Find existing command registration pattern and follow it.

---

### Subtask T023 – Write integration tests

**Purpose**: Validate all mission commands work end-to-end.

**Steps**:
1. Create file: `tests/integration/test_mission_cli.py`
2. Setup test fixtures:
   ```python
   import pytest
   import subprocess
   from pathlib import Path
   import tempfile
   import shutil

   @pytest.fixture
   def test_project(tmp_path):
       """Create temporary spec-kitty project."""
       # Copy .kittify structure
       # Initialize git repo
       # Return project path
       pass

   @pytest.fixture
   def clean_project(test_project):
       """Test project with no worktrees, clean git."""
       # Ensure git status clean
       # Ensure .worktrees/ empty
       return test_project

   @pytest.fixture
   def dirty_project(test_project):
       """Test project with uncommitted changes."""
       # Create uncommitted file
       return test_project
   ```

3. Write integration tests:
   ```python
   def test_mission_list(clean_project):
       """spec-kitty mission list should display missions."""
       result = subprocess.run(
           ["spec-kitty", "mission", "list"],
           cwd=clean_project,
           capture_output=True,
           text=True
       )
       assert result.returncode == 0
       assert "Software Dev Kitty" in result.stdout
       assert "Deep Research Kitty" in result.stdout

   def test_mission_current(clean_project):
       """spec-kitty mission current should show active mission."""
       result = subprocess.run(
           ["spec-kitty", "mission", "current"],
           cwd=clean_project,
           capture_output=True,
           text=True
       )
       assert result.returncode == 0
       assert "Software Dev Kitty" in result.stdout or "Deep Research Kitty" in result.stdout

   def test_mission_info(clean_project):
       """spec-kitty mission info should display mission details."""
       result = subprocess.run(
           ["spec-kitty", "mission", "info", "research"],
           cwd=clean_project,
           capture_output=True,
           text=True
       )
       assert result.returncode == 0
       assert "Deep Research Kitty" in result.stdout
       assert "research" in result.stdout

   def test_mission_switch_clean_project(clean_project):
       """Mission switch should succeed on clean project."""
       # This test needs --force or automated yes
       result = subprocess.run(
           ["spec-kitty", "mission", "switch", "research", "--force"],
           cwd=clean_project,
           capture_output=True,
           text=True
       )
       assert result.returncode == 0
       assert "Switched to mission" in result.stdout

       # Verify symlink updated
       active_link = clean_project / ".kittify" / "active-mission"
       assert active_link.exists()

   def test_mission_switch_dirty_git(dirty_project):
       """Mission switch should fail with uncommitted changes."""
       result = subprocess.run(
           ["spec-kitty", "mission", "switch", "research"],
           cwd=dirty_project,
           capture_output=True,
           text=True
       )
       assert result.returncode == 1
       assert "uncommitted changes" in result.stdout.lower()
   ```

**Files**: `tests/integration/test_mission_cli.py` (new)

**Parallel?**: Yes (can write while commands are being implemented)

**Notes**: Use subprocess to test actual CLI invocation, not just Python functions.

---

### Subtask T024 – Test CLI output formatting

**Purpose**: Verify Rich output looks good and is readable.

**Steps**:
1. Run all commands manually and verify output:
   ```bash
   spec-kitty mission list
   # Check: Table formatted, active mission marked, descriptions readable

   spec-kitty mission current
   # Check: Panel formatted, all details shown, phases listed

   spec-kitty mission info research
   # Check: Complete info displayed, well-formatted

   spec-kitty mission switch research --force
   # Check: Progress shown, confirmation clear, success message helpful
   ```

2. Test error formatting:
   ```bash
   spec-kitty mission switch invalid-mission
   # Check: Error clear, available missions listed

   # Create dirty git state
   echo "test" > temp.txt
   spec-kitty mission switch research
   # Check: Uncommitted changes error clear, suggestions helpful

   # Create active worktree (simulate)
   mkdir .worktrees/test-feature
   spec-kitty mission switch research
   # Check: Active worktrees error clear, suggestions helpful
   ```

3. Verify cross-platform: Test on macOS/Linux/Windows if available

**Files**: Manual testing

**Parallel?**: No (final validation)

**Notes**: User experience matters - output must be professional and helpful.

---

## Test Strategy

**Integration Test Coverage**:

1. **Happy Path Tests**:
   - List missions → displays all
   - Show current → displays active mission
   - Info mission → displays details
   - Switch mission (clean) → succeeds

2. **Error Scenario Tests**:
   - Switch with active worktrees → fails with clear error
   - Switch with dirty git → fails with clear error
   - Switch to non-existent mission → fails with available list
   - Info non-existent mission → fails with available list

3. **Edge Cases**:
   - Switch to same mission → no-op with message
   - Mission with missing artifacts → warns but proceeds
   - Broken active-mission symlink → defaults to software-dev

**Test Execution**:
```bash
# Run integration tests
pytest tests/integration/test_mission_cli.py -v

# Run specific test
pytest tests/integration/test_mission_cli.py::test_mission_switch_clean_project -vv

# Run with coverage
pytest tests/integration/test_mission_cli.py --cov=src/specify_cli/cli/commands/mission
```

---

## Risks & Mitigations

**Risk 1**: Mission switching breaks in-progress work
- **Mitigation**: Strict validation - block if any worktrees exist or git dirty

**Risk 2**: Users confused by switch errors
- **Mitigation**: Clear error messages with step-by-step fix instructions

**Risk 3**: Switch validation too strict (false positives)
- **Mitigation**: Test extensively, allow --force flag for edge cases

**Risk 4**: Performance degradation from validation
- **Mitigation**: Keep validation lightweight, measure <2 second target for switch

**Risk 5**: Cross-platform compatibility issues
- **Mitigation**: Test on Windows, macOS, Linux; use cross-platform Path operations

---

## Definition of Done Checklist

- [ ] `src/specify_cli/cli/commands/mission.py` created with Typer app
- [ ] `list_cmd()` implemented and working
- [ ] `current_cmd()` implemented and working
- [ ] `info_cmd()` implemented and working
- [ ] `switch_cmd()` implemented with all validation
- [ ] Mission command group registered in main CLI
- [ ] `spec-kitty mission --help` shows all subcommands
- [ ] Integration tests in `tests/integration/test_mission_cli.py` pass
- [ ] All error scenarios tested (worktrees, git dirty, missing mission)
- [ ] Rich output formatted professionally
- [ ] Manual testing complete on primary platform
- [ ] No regression in existing mission functionality

---

## Review Guidance

**Critical Checkpoints**:
1. Switch validation must prevent data loss (no switching with active work)
2. Error messages must be actionable (show exact fix steps)
3. Output must be professionally formatted (Rich tables/panels)
4. All commands must handle errors gracefully

**What Reviewers Should Verify**:
- Run `spec-kitty mission list` → see all missions
- Run `spec-kitty mission current` → see active mission
- Run `spec-kitty mission switch <name>` → verify validation works
- Create dirty git state → verify switch blocked
- Create worktree → verify switch blocked
- Check integration test coverage
- Verify error messages are helpful

**Acceptance Criteria from Spec**:
- User Story 4, Acceptance Scenarios 1-6 all pass
- FR-013 through FR-019 all satisfied

---

## Activity Log

- 2025-01-16T00:00:00Z – system – lane=planned – Prompt created via /spec-kitty.tasks
- 2025-11-16T13:01:29Z – codex – shell_pid=56646 – lane=doing – Started implementation
- 2025-11-16T13:07:27Z – codex – shell_pid=56646 – lane=doing – Completed implementation
- 2025-11-16T13:07:47Z – codex – shell_pid=56646 – lane=for_review – Ready for review
- 2025-11-16T13:17:45Z – claude – shell_pid=88714 – lane=done – Code review complete: APPROVED. Complete mission CLI implementation with all 4 commands (list/current/info/switch). All 6 integration tests passing in 2.39s. Excellent validation logic blocks on worktrees and dirty git. Rich formatted output professional. Helper functions well-factored. Registered in CLI properly. Ready for production use.
