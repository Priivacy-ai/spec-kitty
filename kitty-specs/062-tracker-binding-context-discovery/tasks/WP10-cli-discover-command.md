---
work_package_id: WP10
title: CLI Discover Command
dependencies: [WP09]
requirement_refs:
- FR-001
- FR-002
- NFR-004
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning branch is main. Merge target is main. Actual base_branch may differ for stacked WPs during /spec-kitty.implement.
subtasks: [T047, T048, T049, T050, T051, T052]
history:
- date: '2026-04-04T09:10:15Z'
  action: created
  by: spec-kitty.tasks
authoritative_surface: src/specify_cli/cli/commands/
execution_mode: code_change
owned_files: [src/specify_cli/cli/commands/tracker.py, tests/agent/cli/commands/test_tracker.py]
---

# WP10: CLI Discover Command

## Objective

Add `tracker discover --provider <provider>` command with rich table default output and `--json` flag. Numbered rows align with `--select N` for the bind workflow. This is a new `@app.command("discover")` in `src/specify_cli/cli/commands/tracker.py`.

## Context

- **Spec**: FR-001 (discover displays resources), FR-002 (distinguishes bound/unbound), Scenario 8 (installation-wide discovery)
- **Plan**: CLI Layer in architecture; tracker discover output decision
- **Research**: Decision 3 (rich table + --json)
- **Current code**: `src/specify_cli/cli/commands/tracker.py` — existing commands registered on `typer.Typer()` app
- **Depends on**: WP09 (TrackerService facade with discover())

## Implementation Command

```bash
spec-kitty implement WP10 --base WP09
```

## Subtasks

### T047: Add discover_command()

**Purpose**: Register the new command with typer.

**Steps**:
1. Add to `src/specify_cli/cli/commands/tracker.py`:
   ```python
   @app.command("discover")
   def discover_command(
       provider: str = typer.Option(..., "--provider", help="Provider name"),
       json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
   ) -> None:
       """Discover bindable tracker resources under your installation."""
   ```
2. Inside the command:
   - Call `_service().discover(provider=normalize_provider(provider))`
   - Handle the result (rich table or JSON based on flag)

**Files**: `src/specify_cli/cli/commands/tracker.py`

### T048: Rich Table Output

**Purpose**: Default human-readable output with numbered rows.

**Steps**:
1. Import `rich.table.Table` and `rich.console.Console`
2. Create table with columns: `#`, `Resource`, `Provider`, `Workspace`, `Status`
3. For each resource in results:
   ```python
   status = "● bound" if resource.is_bound else "○ available"
   table.add_row(
       str(resource.sort_position + 1) if hasattr(resource, 'sort_position') else str(idx + 1),
       resource.display_label,
       resource.provider,
       resource.provider_context.get("workspace_name", ""),
       status,
   )
   ```
   Note: BindableResource doesn't have sort_position. Use list index + 1 as display number. The numbering in discover output uses list order (which matches inventory order from host).
4. Print table with `Console().print(table)`

**Files**: `src/specify_cli/cli/commands/tracker.py`

### T049: --json Output

**Purpose**: Machine-readable output for automation.

**Steps**:
1. When `json_output=True`:
   ```python
   import json
   output = [
       {
           "number": idx + 1,
           "candidate_token": r.candidate_token,
           "display_label": r.display_label,
           "provider": r.provider,
           "provider_context": r.provider_context,
           "binding_ref": r.binding_ref,
           "bound_project_slug": r.bound_project_slug,
           "bound_at": r.bound_at,
           "is_bound": r.is_bound,
       }
       for idx, r in enumerate(resources)
   ]
   typer.echo(json.dumps(output, indent=2))
   ```
2. No truncation, preserve all fields

**Files**: `src/specify_cli/cli/commands/tracker.py`

### T050: Error Handling

**Purpose**: Clear errors for no installation, empty results, auth errors.

**Steps**:
1. Catch `TrackerServiceError`:
   ```python
   try:
       resources = _service().discover(provider=normalized)
   except TrackerServiceError as e:
       typer.echo(f"Error: {e}", err=True)
       raise typer.Exit(1)
   ```
2. Empty results (not an error, but inform user):
   ```python
   if not resources:
       typer.echo(f"No bindable resources found for provider '{normalized}'.")
       typer.echo("Verify the tracker is connected in the SaaS dashboard.")
       raise typer.Exit(0)
   ```

**Files**: `src/specify_cli/cli/commands/tracker.py`

### T051: Number Alignment

**Purpose**: Numbering in discover output must align with `--select N` in bind.

**Steps**:
1. Resources are displayed as 1-indexed list (1, 2, 3, ...)
2. When user later runs `tracker bind --select 2`, it selects the 2nd item
3. This alignment is maintained because:
   - discover lists resources in host-returned order
   - bind_resolve returns candidates with sort_position (0-indexed)
   - `--select N` maps to `sort_position = N - 1`
   - discover's list index matches the expected sort_position order
4. Add a comment in the code explaining this alignment

**Files**: `src/specify_cli/cli/commands/tracker.py`

### T052: Write CLI Tests

**Purpose**: Test discover command output and error handling.

**Steps**:
1. Add to `tests/agent/cli/commands/test_tracker.py`:
   - `test_discover_rich_table`: mock service.discover() -> verify table output contains resource labels
   - `test_discover_json_output`: mock -> verify valid JSON output
   - `test_discover_empty_resources`: mock empty list -> verify informational message
   - `test_discover_service_error`: mock TrackerServiceError -> verify error message + exit code 1
   - `test_discover_numbering`: mock 3 resources -> verify numbers 1, 2, 3 in output

**Files**: `tests/agent/cli/commands/test_tracker.py`

## Definition of Done

- [ ] `tracker discover --provider linear` displays rich table with numbered resources
- [ ] `tracker discover --provider linear --json` outputs full JSON payload
- [ ] Empty results produce informational message (not error)
- [ ] Service errors produce error message + exit code 1
- [ ] Numbering is 1-indexed and aligns with --select N
- [ ] All tests pass: `python -m pytest tests/agent/cli/commands/test_tracker.py -x -q -k discover`
- [ ] `ruff check src/specify_cli/cli/commands/tracker.py`

## Reviewer Guidance

- Verify numbering alignment with --select N (1-based display, maps to 0-based sort_position)
- Check that --json output includes all fields (no truncation)
- Verify bound/unbound visual distinction in rich table
