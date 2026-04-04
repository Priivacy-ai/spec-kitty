---
work_package_id: WP12
title: CLI Status --all
dependencies: []
requirement_refs:
- FR-013
- FR-014
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: main
base_commit: 67b13f1213ef228677dd06baba7239d4310aa95b
created_at: '2026-04-04T11:25:29.363157+00:00'
subtasks: [T060, T061, T062, T063]
shell_pid: '18365'
history:
- date: '2026-04-04T09:10:15Z'
  action: created
  by: spec-kitty.tasks
authoritative_surface: tests/agent/cli/commands/
execution_mode: code_change
owned_files: [tests/agent/cli/commands/test_tracker_status.py]
---

# WP12: CLI Status --all

## Objective

Add `--all` flag to `tracker status` for installation-wide summary. Output format is clearly different from project-scoped status.

## Context

- **Spec**: FR-014 (status --all), Scenario 9 (installation-wide status)
- **Plan**: Facade evolution in plan.md
- **Current code**: `src/specify_cli/cli/commands/tracker.py` — `status_command()` exists
- **Depends on**: WP09 (facade with status(all=))

## Implementation Command

```bash
spec-kitty implement WP12 --base WP09
```

## Subtasks

### T060: Add --all Flag

**Purpose**: New flag on existing status command.

**Steps**:
1. Update `status_command()` signature to add:
   ```python
   all_installations: bool = typer.Option(False, "--all", help="Show installation-wide status"),
   ```
2. Pass to facade:
   ```python
   result = _service().status(all=all_installations)
   ```

**Files**: `src/specify_cli/cli/commands/tracker.py`

### T061: Installation-Wide Output Formatting

**Purpose**: Different output for --all vs project-scoped.

**Steps**:
1. When `all_installations=True`, display a summary:
   ```python
   from rich.console import Console
   from rich.table import Table
   
   console = Console()
   console.print("\n[bold]Installation-wide tracker status[/bold]\n")
   # Format depends on what the SaaS API returns for installation-wide status
   # At minimum, show provider, connected status, and resource count
   ```
2. The exact output format depends on the SaaS response shape for installation-wide status. Use the existing `GET /api/v1/tracker/status/?provider=<provider>` (without project_slug) which already works per the spec.

**Files**: `src/specify_cli/cli/commands/tracker.py`

### T062: Error Handling

**Purpose**: SaaS-only guard and clear errors.

**Steps**:
1. The facade already guards local providers. Catch at CLI level:
   ```python
   try:
       result = _service().status(all=all_installations)
   except TrackerServiceError as e:
       typer.echo(f"Error: {e}", err=True)
       raise typer.Exit(1)
   ```
2. Ensure error message for local provider is clear: "Installation-wide status is only available for SaaS providers."

**Files**: `src/specify_cli/cli/commands/tracker.py`

### T063: Write CLI Tests

**Purpose**: Test --all flag behavior.

**Steps**:
1. Add to `tests/agent/cli/commands/test_tracker.py`:
   - `test_status_all_displays_installation_summary`: mock service.status(all=True) -> verify different output
   - `test_status_all_local_provider_error`: mock local provider -> verify error + exit 1
   - `test_status_default_project_scoped`: verify existing behavior unchanged without --all

**Files**: `tests/agent/cli/commands/test_tracker.py`

## Definition of Done

- [ ] `tracker status --all` shows installation-wide summary
- [ ] Output is visually different from project-scoped status
- [ ] Local provider + --all produces clear error
- [ ] Default `tracker status` (no --all) behavior unchanged
- [ ] All tests pass
- [ ] `ruff check src/specify_cli/cli/commands/tracker.py`

## Reviewer Guidance

- Verify --all output is clearly labeled as installation-wide (not confused with project status)
- Check that default status behavior is completely unchanged
- Note: File ownership overlaps with WP10 and WP11 (all modify tracker.py). Coordinate merge order.
