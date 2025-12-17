---
work_package_id: "WP05"
subtasks:
  - "T025"
  - "T026"
  - "T027"
  - "T028"
title: "Legacy Detection Integration"
phase: "Phase 2 - Polish"
lane: "done"
assignee: ""
agent: "claude"
shell_pid: "$$"
review_status: ""
reviewed_by: "claude-reviewer"
history:
  - timestamp: "2025-12-17T13:15:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: "$$"
    action: "Prompt generated via /spec-kitty.tasks"
  - timestamp: "2025-12-17T17:00:00Z"
    lane: "done"
    agent: "claude"
    shell_pid: "$$"
    action: "Implementation complete - T025-T027 from WP02, T028 dashboard integration"
activity_log: |
  - 2025-12-17T13:15:00Z – system – lane=planned – Prompt created
  - 2025-12-17T17:00:00Z – claude – lane=for_review – Implementation complete
  - 2025-12-17T14:05:00Z – claude-reviewer – shell_pid=$$ – lane=done – Approved: implementation verified
---

# Work Package Prompt: WP05 – Legacy Detection Integration

## Objectives & Success Criteria

Integrate legacy format detection into CLI commands and dashboard to warn users about old format:
1. Display warning when running CLI commands on legacy-format projects
2. Warning should suggest running `spec-kitty upgrade`
3. Warning should NOT block command execution

**Success Criteria** (from spec FR-014 to FR-016, SC-007):
- `tasks_cli.py list 007-feature` on old-format shows upgrade suggestion
- Warning appears once per command, not per WP
- Commands still execute successfully after warning
- Legacy detection is 100% accurate

## Context & Constraints

**Reference Documents**:
- Spec: `kitty-specs/007-frontmatter-only-lane/spec.md` (User Story 4)

**Dependencies**: WP01 (legacy detector), WP02 (CLI refactoring)

## Subtasks & Detailed Guidance

### Subtask T025 – Add legacy detection to CLI entry points

**Purpose**: Warn users when they run commands on old-format projects.

**Steps**:
1. Open `scripts/tasks/tasks_cli.py`
2. Import legacy detector:
   ```python
   from src.specify_cli.legacy_detector import is_legacy_format
   ```
3. Add check helper:
   ```python
   _legacy_warning_shown = False  # Module-level flag

   def check_and_warn_legacy(feature: str, repo_root: Path):
       """Check for legacy format and warn once."""
       global _legacy_warning_shown
       if _legacy_warning_shown:
           return

       feature_path = repo_root / "kitty-specs" / feature
       if is_legacy_format(feature_path):
           show_legacy_warning()
           _legacy_warning_shown = True
   ```
4. Add to command entry points:
   - `update_command()` (was move)
   - `list_command()`
   - `status_command()`

**Files**: `scripts/tasks/tasks_cli.py` (MODIFY)

**Parallel?**: No, core integration

### Subtask T026 – Create warning message function

**Purpose**: Consistent, clear warning format.

**Steps**:
1. Add warning function:
   ```python
   def show_legacy_warning():
       """Display legacy format warning."""
       console.print()
       console.print("[yellow]" + "=" * 60 + "[/yellow]")
       console.print("[bold yellow]Legacy directory-based lanes detected.[/bold yellow]")
       console.print()
       console.print("Your project uses the old lane structure (tasks/planned/, tasks/doing/, etc.).")
       console.print("Run [bold]spec-kitty upgrade[/bold] to migrate to frontmatter-only lanes.")
       console.print()
       console.print("[dim]Benefits of upgrading:[/dim]")
       console.print("[dim]  - No file conflicts during lane changes[/dim]")
       console.print("[dim]  - Direct editing of lane: field supported[/dim]")
       console.print("[dim]  - Better multi-agent compatibility[/dim]")
       console.print("[yellow]" + "=" * 60 + "[/yellow]")
       console.print()
   ```

**Files**: `scripts/tasks/tasks_cli.py` (MODIFY)

**Parallel?**: No, used by T025

### Subtask T027 – Ensure warning doesn't block execution

**Purpose**: Commands should work on both old and new format.

**Steps**:
1. Verify warning is display-only (no `raise` or `exit`)
2. Ensure commands handle both formats during transition:
   - For `list_command`: If legacy format, scan subdirectories
   - For `update_command`: Fail with clear error on legacy format
   - For `status_command`: Works on both formats
3. Add clear error for update on legacy:
   ```python
   def update_command(feature: str, wp_id: str, lane: str, ...):
       repo_root = find_repo_root()
       feature_path = repo_root / "kitty-specs" / feature

       if is_legacy_format(feature_path):
           show_legacy_warning()
           console.print("[red]Error: Cannot use 'update' command on legacy format.[/red]")
           console.print("[red]Run 'spec-kitty upgrade' first, then retry.[/red]")
           raise typer.Exit(1)

       # Continue with update logic...
   ```

**Files**: `scripts/tasks/tasks_cli.py` (MODIFY)

**Parallel?**: No, depends on T025/T026

### Subtask T028 – Add detection to dashboard routes

**Purpose**: Dashboard should also warn about legacy format.

**Steps**:
1. Open `src/specify_cli/dashboard/handlers/features.py`
2. Add legacy detection to feature list/kanban handlers:
   ```python
   def handle_features_list(self, ...):
       features = scan_all_features(repo_root)

       # Add legacy format indicator to each feature
       for feature in features:
           feature["is_legacy"] = is_legacy_format(feature["path"])

       return features

   def handle_kanban(self, feature: str, ...):
       feature_path = repo_root / "kitty-specs" / feature

       is_legacy = is_legacy_format(feature_path)

       return {
           "lanes": scan_feature_kanban(feature_path),
           "is_legacy": is_legacy,
           "upgrade_needed": is_legacy
       }
   ```
3. Frontend can display warning banner when `is_legacy` is true

**Files**: `src/specify_cli/dashboard/handlers/features.py` (MODIFY)

**Parallel?**: Yes, dashboard is independent of CLI

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Warning fatigue | Show once per command invocation, not per WP |
| Blocking users unexpectedly | Only block on `update`, warn on others |
| False positives in detection | Test detection thoroughly in WP01 |

## Definition of Done Checklist

- [ ] Legacy detection check added to CLI commands
- [ ] Consistent warning message displays
- [ ] Warning shows once per command
- [ ] `update` command errors on legacy format (with clear message)
- [ ] `list` and `status` work with warning on legacy format
- [ ] Dashboard indicates legacy format in API responses
- [ ] Commands complete successfully after showing warning (except update)

## Review Guidance

- Test CLI commands on legacy-format project
- Verify warning appears once, not multiple times
- Test `update` command properly blocks on legacy
- Check dashboard API includes legacy indicator
