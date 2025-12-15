---
work_package_id: "WP05"
subtasks:
  - "T025"
  - "T026"
  - "T027"
  - "T028"
  - "T029"
  - "T030"
title: "Deprecation and Cleanup"
phase: "Phase 4 - Cleanup"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-15T11:55:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP05 – Deprecation and Cleanup

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- Remove `spec-kitty mission switch` command with helpful error message
- Update `spec-kitty mission list` to show source indicators
- Remove `--mission` flag from `spec-kitty init` (if present)
- Remove obsolete `set_active_mission()` function

**Success Metrics** (from spec):
- SC-004: `spec-kitty mission switch` returns "command removed" error
- SC-003: `spec-kitty mission list` shows missions with source (project/built-in)
- SC-005: `spec-kitty init` no longer accepts mission selection

## Context & Constraints

**Reference Documents**:
- Spec: `kitty-specs/006-per-feature-mission/spec.md` (FR-005, FR-006, User Story 5)
- Plan: `kitty-specs/006-per-feature-mission/plan.md` (Phase 4)

**Files to Modify**:
- `src/specify_cli/cli/commands/mission.py` - CLI mission commands
- `src/specify_cli/mission.py` - Core mission module
- `src/specify_cli/cli/commands/init.py` - Init command (if --mission flag exists)

**Constraints**:
- Error messages should be helpful, not just "command not found"
- List output should clearly indicate source of each mission
- Don't break any code that still depends on deprecated functions

## Subtasks & Detailed Guidance

### Subtask T025 – Remove `switch` subcommand from mission CLI

- **Purpose**: Remove obsolete project-level mission switching
- **Files**: `src/specify_cli/cli/commands/mission.py`
- **Steps**:
  1. Find the `switch` command function (likely decorated with `@app.command()`)
  2. Remove or comment out the function
  3. Alternatively, keep the function but change implementation to show error (T026)
  4. If using Typer, can use `hidden=True` to hide from help but keep for error message
- **Parallel?**: No (foundational for T026)

### Subtask T026 – Add helpful error message when switch is attempted

- **Purpose**: Guide users to new per-feature workflow
- **Files**: `src/specify_cli/cli/commands/mission.py`
- **Steps**:
  1. Replace switch command implementation with error:
     ```python
     @app.command()
     def switch(mission: str):
         """[REMOVED] Switch active mission - this command was removed in v0.8.0."""
         console = Console()
         console.print("[bold red]Error:[/bold red] The 'mission switch' command was removed in v0.8.0.")
         console.print()
         console.print("Missions are now selected per-feature during [bold]/spec-kitty.specify[/bold].")
         console.print()
         console.print("New workflow:")
         console.print("  1. Run [bold]/spec-kitty.specify[/bold] to start a new feature")
         console.print("  2. The system will infer and confirm the appropriate mission")
         console.print("  3. Mission is stored in the feature's meta.json")
         console.print()
         console.print("For more info, see: [link]https://github.com/your-org/spec-kitty/blob/main/README.md[/link]")
         raise typer.Exit(1)
     ```
  2. Keep the command visible in help (so users see it's deprecated) or hide it
- **Parallel?**: No (depends on T025)

### Subtask T027 – Update `mission list` with source indicators

- **Purpose**: Show where each mission comes from (project/built-in)
- **Files**: `src/specify_cli/cli/commands/mission.py`
- **Steps**:
  1. Find the `list` command function
  2. Update to use `discover_missions()` from WP01:
     ```python
     from specify_cli.mission import discover_missions

     @app.command("list")
     def list_missions():
         """List all available missions."""
         console = Console()
         missions = discover_missions()

         if not missions:
             console.print("[yellow]No missions found.[/yellow]")
             return

         table = Table(title="Available Missions")
         table.add_column("Key", style="cyan")
         table.add_column("Name", style="green")
         table.add_column("Domain")
         table.add_column("Source", style="dim")

         for key, (mission, source) in sorted(missions.items()):
             table.add_row(
                 key,
                 mission.name,
                 mission.domain,
                 source
             )

         console.print(table)
     ```
  3. Add import for Table from rich if not present
- **Parallel?**: Yes (independent of T025-T026)

### Subtask T028 – Remove `--mission` flag from `spec-kitty init`

- **Purpose**: Init no longer handles mission selection
- **Files**: `src/specify_cli/cli/commands/init.py`
- **Steps**:
  1. Search for `--mission` or `mission` parameter in init command:
     ```bash
     grep -n "mission" src/specify_cli/cli/commands/init.py
     ```
  2. If found, remove the parameter from function signature
  3. Remove any logic that sets active mission during init
  4. If init previously called `set_active_mission()`, remove that call
  5. Update help text if it mentions mission selection
- **Parallel?**: Yes (independent of T025-T027)

### Subtask T029 – Remove `set_active_mission()` function

- **Purpose**: Remove obsolete function that sets project-level mission
- **Files**: `src/specify_cli/mission.py`
- **Steps**:
  1. Find `set_active_mission()` function (around line 492)
  2. Check if any code still calls it:
     ```bash
     grep -r "set_active_mission" --include="*.py" .
     ```
  3. If no callers remain after T028, remove the function entirely
  4. If callers remain, keep function but add deprecation warning:
     ```python
     def set_active_mission(mission_name: str, kittify_dir: Optional[Path] = None) -> None:
         """DEPRECATED: Use per-feature mission selection instead."""
         warnings.warn(
             "set_active_mission is deprecated. Missions are now per-feature.",
             DeprecationWarning,
             stacklevel=2
         )
         # Original implementation or just pass
     ```
- **Parallel?**: Yes (but verify after T028)

### Subtask T030 – Update CLI help text

- **Purpose**: Ensure help reflects new per-feature model
- **Files**: Various CLI files
- **Steps**:
  1. Review `spec-kitty --help` output
  2. Review `spec-kitty mission --help` output
  3. Update docstrings and help text to reflect:
     - Missions are per-feature
     - Selected during `/spec-kitty.specify`
     - Stored in feature's meta.json
  4. Remove any references to "active mission" or "project mission"
  5. Update top-level CLI description if needed
- **Parallel?**: Yes (independent cleanup task)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking code that calls removed functions | Search for all callers before removing |
| Users confused by missing commands | Provide clear, actionable error messages |
| Help text inconsistent | Review all CLI help after changes |

## Definition of Done Checklist

- [ ] `spec-kitty mission switch` returns helpful error message
- [ ] `spec-kitty mission list` shows source indicators (project/built-in)
- [ ] `spec-kitty init` no longer has `--mission` flag
- [ ] `set_active_mission()` removed or deprecated
- [ ] All CLI help text updated to reflect per-feature model
- [ ] No orphaned code referencing removed functionality

## Review Guidance

- Run `spec-kitty mission switch foo` → should show helpful error
- Run `spec-kitty mission list` → should show table with Source column
- Run `spec-kitty init --help` → should not show --mission option
- Verify error message explains new workflow clearly
- Check no deprecated functions are called in production code

## Activity Log

- 2025-12-15T11:55:00Z – system – lane=planned – Prompt created.
