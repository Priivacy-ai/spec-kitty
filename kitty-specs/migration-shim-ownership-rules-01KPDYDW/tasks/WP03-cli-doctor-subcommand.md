---
work_package_id: WP03
title: CLI Doctor Subcommand
dependencies:
- WP02
requirement_refs:
- FR-009
- NFR-001
- NFR-004
- C-004
- C-007
planning_base_branch: kitty/mission-migration-shim-ownership-rules-01KPDYDW
merge_target_branch: kitty/mission-migration-shim-ownership-rules-01KPDYDW
branch_strategy: Planning artifacts for this feature were generated on kitty/mission-migration-shim-ownership-rules-01KPDYDW. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-migration-shim-ownership-rules-01KPDYDW unless the human explicitly redirects the landing branch.
subtasks:
- T006
agent: "claude"
shell_pid: "1348259"
history:
- date: '2026-04-19'
  event: created
agent_profile: python-implementer
authoritative_surface: src/specify_cli/cli/commands/doctor.py
execution_mode: code_change
mission_id: 01KPDYDWVF8W838HNJK7FC3S7T
mission_slug: migration-shim-ownership-rules-01KPDYDW
owned_files:
- src/specify_cli/cli/commands/doctor.py
tags: []
---

# WP03 — CLI Doctor Subcommand

## Objective

Wire `spec-kitty doctor shim-registry` into the existing doctor command group by adding a new `@app.command` to `src/specify_cli/cli/commands/doctor.py`. The subcommand renders a Rich table, emits correct exit codes, and supports `--json` for CI machine-readable output.

## Context

`doctor.py` already has four subcommands: `command-files`, `state-roots`, `identity`, `sparse-checkout`. Each follows the same pattern:
1. Import business logic from a domain module inside the handler (lazy import — keeps module import cheap).
2. Call `locate_project_root()` and bail with exit 1 if not in a project.
3. Render output (Rich table for human, JSON for `--json`).
4. `raise typer.Exit(N)` with the appropriate exit code.

The new subcommand follows this pattern exactly. **No modifications to existing subcommands.**

The check is **read-only** (C-004): it never writes to the registry or modifies files.

## Branch Strategy

- **Working branch**: `kitty/mission-migration-shim-ownership-rules-01KPDYDW`
- **Merge target**: `main`
- Run: `spec-kitty agent action implement WP03 --agent <name>`

---

## Subtask T006 — Add `shim-registry` Subcommand

**Purpose**: Implement `spec-kitty doctor shim-registry` as a new `@app.command` in `doctor.py`.

**Steps**:

1. **Add the command** after the `sparse-checkout` command (end of file):

```python
@app.command(name="shim-registry")
def shim_registry(
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Machine-readable JSON output"),
    ] = False,
) -> None:
    """Check for overdue compatibility shims in the shim registry.

    Reads architecture/2.x/shim-registry.yaml and compares each entry's
    removal_target_release against the current project version. Fails with
    exit code 1 if any shim is overdue (removal release has shipped but
    shim file still exists on disk).

    Exit codes:
      0  All entries are pending, removed, or grandfathered.
      1  At least one entry is overdue — shim must be deleted or window extended.
      2  Configuration error (registry file or pyproject.toml missing/invalid).

    Examples:
        spec-kitty doctor shim-registry
        spec-kitty doctor shim-registry --json
    """
    from specify_cli.compat import (
        RegistrySchemaError,
        ShimStatus,
        check_shim_registry,
    )

    try:
        repo_root = locate_project_root()
    except Exception as exc:
        console.print("[red]Error:[/red] Not in a spec-kitty project")
        raise typer.Exit(2) from exc

    if repo_root is None:
        console.print("[red]Error:[/red] Not in a spec-kitty project")
        raise typer.Exit(2)

    try:
        report = check_shim_registry(repo_root)
    except FileNotFoundError as exc:
        console.print(f"[red]Configuration error:[/red] {exc}")
        raise typer.Exit(2) from exc
    except RegistrySchemaError as exc:
        console.print("[red]Registry schema error:[/red]")
        for err in exc.errors:
            console.print(f"  {err}")
        raise typer.Exit(2) from exc
    except KeyError as exc:
        console.print(f"[red]Configuration error:[/red] missing key {exc} in pyproject.toml")
        raise typer.Exit(2) from exc

    if json_output:
        import json as _json
        output = {
            "project_version": report.project_version,
            "registry_path": str(report.registry_path),
            "entries": [
                {
                    "legacy_path": e.entry.legacy_path,
                    "canonical_import": e.entry.canonical_import,
                    "removal_target_release": e.entry.removal_target_release,
                    "grandfathered": e.entry.grandfathered,
                    "tracker_issue": e.entry.tracker_issue,
                    "status": e.status.value,
                    "shim_exists": e.shim_exists,
                }
                for e in report.entries
            ],
            "has_overdue": report.has_overdue,
            "exit_code": report.recommended_exit_code,
        }
        console.print_json(_json.dumps(output, indent=2))
        raise typer.Exit(report.recommended_exit_code)

    # Human-readable output
    if not report.entries:
        console.print("[green]Shim Registry[/green]: registry is empty — no shims to check.")
        raise typer.Exit(0)

    console.print(f"\n[bold]Shim Registry[/bold] — {len(report.entries)} entry/entries (project version: {report.project_version})\n")

    table = Table(box=None, padding=(0, 2), show_edge=False)
    table.add_column("Legacy Path", style="cyan", min_width=24)
    table.add_column("Canonical Import", min_width=20)
    table.add_column("Removal Target", min_width=14)
    table.add_column("Status", min_width=12)

    _status_styles = {
        ShimStatus.PENDING: "[cyan]pending[/cyan]",
        ShimStatus.OVERDUE: "[bold red]OVERDUE[/bold red]",
        ShimStatus.GRANDFATHERED: "[yellow]grandfathered[/yellow]",
        ShimStatus.REMOVED: "[dim]removed[/dim]",
    }

    for e in report.entries:
        canonical = (
            ", ".join(e.entry.canonical_import)
            if isinstance(e.entry.canonical_import, list)
            else e.entry.canonical_import
        )
        table.add_row(
            e.entry.legacy_path,
            canonical,
            e.entry.removal_target_release,
            _status_styles[e.status],
        )

    console.print(table)
    console.print()

    # Summary footer
    from collections import Counter
    counts = Counter(e.status.value for e in report.entries)
    parts = [f"{v} {k}" for k, v in sorted(counts.items())]
    console.print(f"Summary: {', '.join(parts)}")

    # Per-overdue remediation block (NFR-004)
    if report.has_overdue:
        console.print()
        console.print("[bold red]Overdue shims must be resolved before release:[/bold red]")
        for e in report.entries:
            if e.status == ShimStatus.OVERDUE:
                canonical = (
                    ", ".join(e.entry.canonical_import)
                    if isinstance(e.entry.canonical_import, list)
                    else e.entry.canonical_import
                )
                console.print(f"\n  [red]{e.entry.legacy_path}[/red]")
                console.print(f"    Canonical import : {canonical}")
                console.print(f"    Removal target   : {e.entry.removal_target_release}")
                console.print(f"    Tracker          : {e.entry.tracker_issue}")
                console.print("    Remediation:")
                console.print(f"      Option A: Delete src/specify_cli/{e.entry.legacy_path.replace('.', '/')}.py (or __init__.py)")
                console.print(f"      Option B: Extend removal_target_release in architecture/2.x/shim-registry.yaml with extension_rationale")

    console.print()
    raise typer.Exit(report.recommended_exit_code)
```

2. **Verify integration**:
   ```bash
   spec-kitty doctor shim-registry
   # Expected: "registry is empty — no shims to check." (exit 0)
   spec-kitty doctor shim-registry --json
   # Expected: JSON with entries=[], has_overdue=false
   spec-kitty doctor --help
   # Expected: shim-registry listed in the command group
   ```

**Files**:
- `src/specify_cli/cli/commands/doctor.py` — append new command (~90 lines added)

**Validation**:
- [ ] `spec-kitty doctor shim-registry` exits 0 on empty registry
- [ ] `spec-kitty doctor shim-registry --json` outputs valid JSON
- [ ] `spec-kitty doctor --help` lists `shim-registry`
- [ ] `mypy --strict src/specify_cli/cli/commands/doctor.py` passes
- [ ] Existing doctor subcommands still work (no regressions)

---

## Definition of Done

- [ ] `shim-registry` subcommand added to `doctor.py`
- [ ] Human table output rendered with correct status colors
- [ ] `--json` flag outputs machine-readable JSON matching the schema in `contracts/doctor-shim-registry-cli.md`
- [ ] Exit codes 0/1/2 implemented correctly per spec
- [ ] Overdue remediation block printed with legacy path, canonical import, tracker, and both remediation options
- [ ] All existing `doctor` subcommands pass their tests (zero regressions)
- [ ] `mypy --strict` passes
- [ ] `spec-kitty doctor shim-registry` completes in ≤2 seconds (NFR-001)

## Risks

- The `locate_project_root()` call may return `None` without raising in some project layouts — handle both the `None` path and the exception path (existing pattern in `doctor.py` does both).
- `from collections import Counter` — already in stdlib, no import needed in `pyproject.toml`. Just confirm it's not shadowed.

## Activity Log

- 2026-04-19T13:26:14Z – claude – shell_pid=1345287 – Started implementation via action command
- 2026-04-19T13:27:25Z – claude – shell_pid=1345287 – doctor shim-registry implemented: exits 0 on empty registry, --json works, ruff+mypy pass
- 2026-04-19T13:30:36Z – claude – shell_pid=1348259 – Started review via action command
- 2026-04-19T13:30:53Z – claude – shell_pid=1348259 – Review passed: exits 0 on empty registry, --json valid, listed in doctor --help, ruff clean.
