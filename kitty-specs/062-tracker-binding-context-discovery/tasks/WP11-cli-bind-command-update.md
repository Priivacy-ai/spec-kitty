---
work_package_id: WP11
title: CLI Bind Command Update
dependencies: [WP09]
requirement_refs:
- FR-003
- FR-004
- FR-005
- FR-006
- FR-007
- FR-008
- FR-017
- FR-019
- FR-020
- NFR-004
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning branch is main. Merge target is main. Actual base_branch may differ for stacked WPs during /spec-kitty.implement.
subtasks: [T053, T054, T055, T056, T057, T058, T059]
history:
- date: '2026-04-04T09:10:15Z'
  action: created
  by: spec-kitty.tasks
authoritative_surface: src/specify_cli/cli/commands/
execution_mode: code_change
owned_files: [src/specify_cli/cli/commands/tracker.py, tests/agent/cli/commands/test_tracker.py]
---

# WP11: CLI Bind Command Update

## Objective

Rewrite the SaaS bind path in `bind_command()`: remove `--project-slug`, add `--bind-ref` and `--select` flags. Implement the discovery flow with candidate selection, re-bind confirmation, and non-interactive modes.

## Context

- **Spec**: FR-003 (discovery bind), FR-004 (--bind-ref), FR-005 (--select N), FR-006 (no --project-slug), FR-007 (no candidates), FR-008 (re-bind warning), Scenarios 1-5, 10
- **Plan**: Discovery Bind Flow diagram
- **Current code**: `src/specify_cli/cli/commands/tracker.py` — `bind_command()` (lines 122-247)
- **Depends on**: WP09 (facade with updated bind)

## Implementation Command

```bash
spec-kitty implement WP11 --base WP09
```

## Subtasks

### T053: Update bind_command() Flags

**Purpose**: Remove --project-slug for SaaS, add --bind-ref and --select.

**Steps**:
1. Update `bind_command()` signature:
   ```python
   @app.command("bind")
   def bind_command(
       provider: str = typer.Option(..., "--provider", help="Provider name"),
       bind_ref: str | None = typer.Option(None, "--bind-ref", help="Binding reference (CI/automation)"),
       select: int | None = typer.Option(None, "--select", help="Auto-select candidate by number"),
       workspace: str | None = typer.Option(None, "--workspace", help="Local provider workspace"),
       doctrine_mode: str = typer.Option("external_authoritative", "--doctrine-mode"),
       field_owners: list[str] = typer.Option([], "--field-owner"),
       credentials: list[str] = typer.Option([], "--credential"),
   ) -> None:
   ```
2. Remove `project_slug` from the signature entirely
3. The SaaS path no longer accepts `--project-slug`

**Files**: `src/specify_cli/cli/commands/tracker.py`

### T054: Discovery Flow

**Purpose**: Call facade bind with discovery, handle all match types.

**Steps**:
1. In the SaaS path:
   ```python
   from specify_cli.sync.project_identity import ensure_identity
   
   identity = ensure_identity(repo_root)
   project_identity = {
       "uuid": str(identity.project_uuid),
       "slug": identity.project_slug,
       "node_id": identity.node_id,
       "repo_slug": identity.repo_slug,
   }
   
   result = _service().bind(
       provider=normalized,
       project_identity=project_identity,
       bind_ref=bind_ref,
       select_n=select,
   )
   ```
2. If result is `BindResult` -> display success (T058 handles re-bind check first)
3. If result is `ResolutionResult` with candidates -> interactive selection (T055)

**Files**: `src/specify_cli/cli/commands/tracker.py`

### T055: Candidate Selection UI

**Purpose**: Numbered list display and user input for candidate selection.

**Steps**:
1. Display candidates:
   ```python
   from rich.console import Console
   console = Console()
   console.print(f"\nMultiple resources found for provider '{normalized}':\n")
   for candidate in result.candidates:
       num = candidate.sort_position + 1
       console.print(f"  {num}. {candidate.display_label} ({candidate.confidence} confidence)")
       console.print(f"     Reason: {candidate.match_reason}")
   ```
2. Get user selection:
   ```python
   console.print()
   choice = input(f"Select resource (1-{len(result.candidates)}): ")
   try:
       select_n = int(choice.strip())
   except ValueError:
       typer.echo("Invalid selection.", err=True)
       raise typer.Exit(1)
   ```
3. Call bind again with select_n:
   ```python
   final = _service().bind(
       provider=normalized,
       project_identity=project_identity,
       select_n=select_n,
   )
   ```

**Files**: `src/specify_cli/cli/commands/tracker.py`

### T056: --bind-ref Path

**Purpose**: CI/automation bind with host validation.

**Steps**:
1. When `bind_ref` is provided:
   - The facade's `bind()` calls `service.validate_and_bind()`
   - This validates via `bind_validate` endpoint, then persists if valid
2. On invalid ref:
   ```python
   except TrackerServiceError as e:
       typer.echo(f"Error: {e}", err=True)
       raise typer.Exit(1)
   ```
3. On success, display the validated binding details

**Files**: `src/specify_cli/cli/commands/tracker.py`

### T057: --select N Path

**Purpose**: Non-interactive candidate selection.

**Steps**:
1. When `select` is provided:
   - Passed through to `_service().bind(select_n=select)`
   - Service handles auto-selection by sort_position
2. Out-of-range selection handled by service (TrackerServiceError)
3. Display same success message as interactive selection

**Files**: `src/specify_cli/cli/commands/tracker.py`

### T058: Re-bind Confirmation

**Purpose**: Warn when binding already exists (Scenario 10).

**Steps**:
1. Before calling bind, check existing config:
   ```python
   from specify_cli.tracker.config import load_tracker_config
   
   existing = load_tracker_config(repo_root)
   if existing.is_configured and existing.provider in SAAS_PROVIDERS:
       label = existing.display_label or existing.project_slug or existing.binding_ref
       console.print(f"⚠ Existing binding: {label}")
       confirm = input("Replace existing binding? (y/N): ")
       if confirm.strip().lower() != "y":
           typer.echo("Bind cancelled.")
           raise typer.Exit(0)
   ```
2. Skip confirmation for --bind-ref and --select (non-interactive)

**Files**: `src/specify_cli/cli/commands/tracker.py`

### T059: Write CLI Tests

**Purpose**: Test all bind scenarios.

**Steps**:
1. Add to `tests/agent/cli/commands/test_tracker.py`:
   - `test_bind_auto_bind`: mock exact match -> verify success output
   - `test_bind_candidates_interactive`: mock candidates + user input "2" -> verify selection
   - `test_bind_no_candidates`: mock none match -> verify error + exit 1
   - `test_bind_ref_valid`: mock --bind-ref -> verify success
   - `test_bind_ref_invalid`: mock validation failure -> verify error + exit 1
   - `test_bind_select_n`: mock --select 1 -> verify auto-selection
   - `test_bind_select_out_of_range`: mock --select 99 -> verify error + exit 1
   - `test_bind_rebind_confirmed`: mock existing binding + user "y" -> verify new binding
   - `test_bind_rebind_cancelled`: mock existing binding + user "n" -> verify exit 0
   - `test_bind_no_project_slug_flag`: verify --project-slug is not accepted

**Files**: `tests/agent/cli/commands/test_tracker.py`

## Definition of Done

- [ ] `--project-slug` removed from bind_command() for SaaS providers
- [ ] `--bind-ref` validates against host before persisting
- [ ] `--select N` auto-selects without prompts
- [ ] Interactive selection displays numbered candidates
- [ ] Re-bind warns and requires confirmation
- [ ] All tests pass: `python -m pytest tests/agent/cli/commands/test_tracker.py -x -q -k bind`
- [ ] `ruff check src/specify_cli/cli/commands/tracker.py`

## Risks

- **Breaking existing bind tests**: Existing tests may pass `--project-slug`. Update them to use new flags or remove them.
- **input() in tests**: Mock `builtins.input` for interactive selection tests.

## Reviewer Guidance

- Verify `--project-slug` is completely removed from SaaS path (not hidden, not deprecated -- gone)
- Verify re-bind confirmation is skipped for --bind-ref and --select (non-interactive modes)
- Check that error messages never suggest typing raw tracker metadata
