---
work_package_id: WP06
title: 'Charter CLI: Activate / Deactivate / List / Pack'
dependencies:
- WP03
- WP04
requirement_refs:
- FR-004
- FR-005
- FR-006
- FR-007
- FR-008
- FR-009
- FR-010
- FR-014
tracker_refs: []
planning_base_branch: pr/charter-doctrine-mission-type-configuration
merge_target_branch: pr/charter-doctrine-mission-type-configuration
branch_strategy: Planning artifacts for this mission were generated on pr/charter-doctrine-mission-type-configuration. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/charter-doctrine-mission-type-configuration unless the human explicitly redirects the landing branch.
subtasks:
- T024
- T025
- T026
- T027
- T028
- T029
agent: claude
history:
- at: '2026-05-31T11:44:22Z'
  event: created
  actor: claude
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/charter/
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/charter/activate.py
- src/specify_cli/charter_activate.py
- src/specify_cli/cli/commands/charter/deactivate.py
- src/specify_cli/cli/commands/charter/list_cmd.py
- src/specify_cli/cli/commands/charter/pack.py
- src/specify_cli/cli/commands/charter/_app.py
- tests/specify_cli/cli/commands/charter/test_charter_activate_commands.py
- tests/specify_cli/cli/commands/charter/test_charter_deactivate_commands.py
- tests/specify_cli/cli/commands/charter/test_charter_list_commands.py
role: implementer
tags: []
---

## Do This First: Load Agent Profile

Before reading anything else, load the implementer profile:

```
/ad-hoc-profile-load python-pedro
```

You are implementing as **python-pedro** (Python implementer). Work precisely, fix
only what is described, run validation after each subtask, and do not touch files
outside the `owned_files` list above.

---

## Objective

Extend the `spec-kitty charter` CLI surface with four first-class sub-commands:

- `charter activate <kind> <id> [--cascade ...]` — replaces old `charter activate mission-type`
- `charter deactivate <kind> <id> [--cascade ...]` — new command
- `charter list [--show-available]` — new command, renders 9-row table
- `charter pack consistency-check [--json]` — new sub-command group

The existing `charter_activate.py` reader gap (FR-014) is also closed: activation
now writes to `config.yaml` via `CharterPackManager` instead of writing
`.kittify/overrides/` files that nothing reads.

This WP depends on WP03 (which delivers `ProjectContext`) and WP04 (which delivers
`CharterPackManager`, `YAML_KEY_MAP`, `default.yaml`, and the pack reader used by
`CharterPackManager.list_activated`/`list_available`). Both must be in `approved`
or `done` before you start.

---

## Context

The current `activate.py` exposes only `charter activate mission-type <id>
--action-sequence ...`. That command writes a YAML override file to
`.kittify/overrides/mission-types/`, which `PackContext.from_config()` never reads —
making it a dead write. WP04 introduced `CharterPackManager`, which reads and writes
`config.yaml` keys directly. This WP pivots all CLI activate/deactivate paths to go
through `CharterPackManager`, closing the reader gap (FR-014).

The nine activation kinds (CLI names): `directive`, `tactic`, `styleguide`,
`toolguide`, `paradigm`, `procedure`, `agent-profile`, `mission-step-contract`,
`mission-type`. Their mapping to `config.yaml` keys lives in
`charter.pack_manager.YAML_KEY_MAP` (delivered by WP04).

**ATDD rule**: Every subtask that changes existing behavior MUST update or delete the
affected tests in the same subtask.

---

## Branch Strategy

```
planning_base_branch: pr/charter-doctrine-mission-type-configuration
merge_target_branch:  pr/charter-doctrine-mission-type-configuration
```

All commits go directly onto `pr/charter-doctrine-mission-type-configuration`. Do not
create additional git branches.

---

## Requirement Refs

FR-004, FR-005, FR-006, FR-007, FR-008, FR-009, FR-010, FR-014

---

## Subtasks

---

### T024 — Refactor `activate.py` for all 9 kinds + cascade

**Requirement refs**: FR-004, FR-008, FR-009

**Files**:
- `src/specify_cli/cli/commands/charter/activate.py`
- `tests/specify_cli/cli/commands/charter/test_charter_activate_commands.py`

**Steps**:

1. Read `src/specify_cli/cli/commands/charter/activate.py` in full. The existing
   command is `@charter_activate_app.command("mission-type")` and accepts
   `mission_type_id` + `--action-sequence`. This command and its old API are being
   **replaced**, not extended.

2. Replace the entire body of `activate.py` with the new design:

   ```python
   """spec-kitty charter activate — activate a doctrine artifact (FR-004, FR-008)."""

   from __future__ import annotations
   from pathlib import Path
   import typer
   from rich.console import Console
   from charter.pack_manager import CharterPackManager, YAML_KEY_MAP
   from charter.invocation_context import ProjectContext

   __all__ = ["charter_activate_app", "activate_cmd"]

   charter_activate_app = typer.Typer(
       name="activate",
       help="Activate a doctrine artifact for this project.",
       no_args_is_help=True,
   )
   console = Console()

   @charter_activate_app.command()
   def activate_cmd(
       kind: str = typer.Argument(..., help="Activation kind (e.g. directive, agent-profile)."),
       artifact_id: str = typer.Argument(..., help="Artifact ID to activate."),
       cascade: str | None = typer.Option(None, "--cascade",
           help="Enable cascade activation of referenced artifacts."),
       repo_root: Path = typer.Option(Path("."), hidden=True),
   ) -> None:
       """Activate a doctrine artifact by kind and ID (FR-004)."""
       if kind not in YAML_KEY_MAP:
           console.print(f"[red]Error:[/red] Unknown kind '{kind}'. "
                         f"Valid kinds: {', '.join(sorted(YAML_KEY_MAP))}.")
           raise typer.Exit(1)
       ctx = ProjectContext.from_repo(repo_root)
       # WP04 API: cascade is bool. --cascade <any-value> enables it.
       cascade_bool: bool = bool(cascade)
       result = CharterPackManager().activate(ctx, kind, artifact_id, cascade=cascade_bool)
       for msg in result.activated:
           console.print(f"[green]Activated[/green]: {msg}")
       # result.cascade_activated is dict[str, list[str]] — kind → list of IDs
       for kind_name, ids in result.cascade_activated.items():
           for cid in ids:
               console.print(f"[cyan]Cascade-activated[/cyan]: {kind_name}/{cid}")
       for warn in result.warnings:
           console.print(f"[yellow]Warning[/yellow]: {warn}")
   ```

   Adjust imports to match the exact module paths established by WP03. If WP03 uses
   different class/function names, import those instead — do not invent names.

3. **ATDD**: Open `tests/specify_cli/cli/commands/charter/test_charter_activate_commands.py`.
   Find any tests that assert:
   - `--action-sequence` argument
   - `mission-type` as a positional sub-command of activate
   - override file written to `.kittify/overrides/mission-types/`

   Delete or rewrite each such test to match the new `<kind> <id> [--cascade]` API
   and assert that `config.yaml` is updated. Keep tests that do not reference the old
   API. Add at minimum:
   - A test for activating a `directive` kind with a valid ID.
   - A test that activating an unknown kind exits with code 1.
   - A test for `--cascade all` calling `CharterPackManager().activate` with the
     correct `CascadeScope`.

**Validation**:
```bash
cd /home/stijn/Documents/_code/SDD/fork/spec-kitty
pytest tests/specify_cli/cli/commands/charter/test_charter_activate_commands.py -x -v
```
Expected: all tests pass with no references to `--action-sequence` or override files.

---

### T025 — Fix reader gap in `charter_activate.py` (FR-014)

**Requirement refs**: FR-014

**Files**:
- `src/specify_cli/charter_activate.py`
- `tests/specify_cli/cli/commands/charter/test_charter_activate_commands.py`
  (any tests specific to `charter_activate.py`'s override-file behavior)

**Steps**:

1. Read `src/specify_cli/charter_activate.py`. Locate `activate_mission_type_override()`.
   It currently:
   - Scans in-flight WPs for removed steps.
   - Writes `.kittify/overrides/mission-types/<id>.yaml`.

2. Refactor the function body so that instead of writing an override YAML file it calls:
   ```python
   from charter.pack_manager import CharterPackManager
   from charter.invocation_context import ProjectContext

   ctx = ProjectContext.from_repo(repo_root)
   CharterPackManager().activate(ctx, "mission-type", mission_type_id, cascade=False)
   ```
   Retain the in-flight WP warning logic (scan for removed steps and emit console
   warnings). Only the final write destination changes.

3. Remove any import or helper function that was solely used for writing the override
   file (e.g., `_write_override_yaml`, path construction for `.kittify/overrides/`).
   If such helpers are also called from elsewhere, leave them in place and note the
   dual use.

4. **ATDD**: Delete or update any test that asserts the override file is written to
   `.kittify/overrides/mission-types/<id>.yaml`. Replace with assertions that
   `config.yaml` now contains the updated `mission_type_activations` key.

**Validation**:
```bash
cd /home/stijn/Documents/_code/SDD/fork/spec-kitty
grep -rn "overrides/mission-types" tests/specify_cli/ | grep -v ".pyc"
```
Expected: zero hits (all override-file assertions removed).

```bash
cd /home/stijn/Documents/_code/SDD/fork/spec-kitty
pytest tests/specify_cli/cli/commands/charter/test_charter_activate_commands.py -x -v
```
Expected: passes.

---

### T026 — Create `deactivate.py`

**Requirement refs**: FR-005, FR-006, FR-007, FR-010

**Files**:
- `src/specify_cli/cli/commands/charter/deactivate.py` (new)

**Steps**:

1. Create `src/specify_cli/cli/commands/charter/deactivate.py`:

   ```python
   """spec-kitty charter deactivate — deactivate a doctrine artifact (FR-005)."""

   from __future__ import annotations
   from pathlib import Path
   import typer
   from rich.console import Console
   from charter.pack_manager import CharterPackManager, YAML_KEY_MAP
   from charter.invocation_context import ProjectContext

   __all__ = ["charter_deactivate_app", "deactivate_cmd"]

   charter_deactivate_app = typer.Typer(
       name="deactivate",
       help="Deactivate a doctrine artifact from this project.",
       no_args_is_help=True,
   )
   console = Console()

   @charter_deactivate_app.command()
   def deactivate_cmd(
       kind: str = typer.Argument(..., help="Activation kind (e.g. directive, agent-profile)."),
       artifact_id: str = typer.Argument(..., help="Artifact ID to deactivate."),
       cascade: str | None = typer.Option(None, "--cascade",
           help="Enable cascade deactivation of exclusively-referenced artifacts."),
       repo_root: Path = typer.Option(Path("."), hidden=True),
   ) -> None:
       """Deactivate a doctrine artifact by kind and ID (FR-005)."""
       if kind not in YAML_KEY_MAP:
           console.print(f"[red]Error:[/red] Unknown kind '{kind}'. "
                         f"Valid kinds: {', '.join(sorted(YAML_KEY_MAP))}.")
           raise typer.Exit(1)
       ctx = ProjectContext.from_repo(repo_root)
       # WP04 API: cascade is bool. --cascade <any-value> enables it.
       cascade_bool: bool = bool(cascade)
       try:
           result = CharterPackManager().deactivate(ctx, kind, artifact_id, cascade=cascade_bool)
       except ValueError as exc:
           # None-state kind: config key absent, migration not yet run
           console.print(f"[red]Error:[/red] {exc}")
           console.print(
               "Kind has no explicit activation set. "
               "Run 'spec-kitty upgrade' first."
           )
           raise typer.Exit(1) from exc
       for msg in result.deactivated:
           console.print(f"[green]Deactivated[/green]: {msg}")
       # result.cascade_deactivated is dict[str, list[str]] — kind → list of IDs
       for kind_name, ids in result.cascade_deactivated.items():
           for cid in ids:
               console.print(f"[cyan]Cascade-deactivated[/cyan]: {kind_name}/{cid}")
       for msg in result.skipped_shared:
           console.print(f"[yellow]Skipped (shared artifact)[/yellow]: {msg}")
       for warn in result.warnings:
           console.print(f"[yellow]Warning[/yellow]: {warn}")
   ```

   Adjust import paths and result attribute names to match what WP03 `CharterPackManager`
   actually returns. If `CharterPackManager.deactivate()` raises a different exception
   type for the None-state case, catch that type instead of `ValueError`.

**Validation**:
```bash
cd /home/stijn/Documents/_code/SDD/fork/spec-kitty
python -c "from specify_cli.cli.commands.charter.deactivate import charter_deactivate_app; print('import ok')"
```
Expected: `import ok`.

---

### T027 — Create `list_cmd.py`

**Requirement refs**: FR-004, FR-005, FR-006, FR-007

**Files**:
- `src/specify_cli/cli/commands/charter/list_cmd.py` (new)

**Note**: The file MUST be named `list_cmd.py`, not `list.py`. `list.py` would
shadow the Python built-in `list`, causing subtle import failures.

**Steps**:

1. Create `src/specify_cli/cli/commands/charter/list_cmd.py`:

   ```python
   """spec-kitty charter list — show activated doctrine artifacts per kind."""

   from __future__ import annotations
   from pathlib import Path
   import typer
   from rich.console import Console
   from rich.table import Table
   from charter.pack_manager import CharterPackManager
   from charter.invocation_context import ProjectContext

   __all__ = ["charter_list_app", "list_cmd"]

   charter_list_app = typer.Typer(
       name="list",
       help="List activated doctrine artifacts by kind.",
       no_args_is_help=False,
   )
   console = Console()

   #: Display order for the 9 kinds.
   _KIND_ORDER: list[str] = [
       "directive", "tactic", "styleguide", "toolguide",
       "paradigm", "procedure", "agent-profile",
       "mission-step-contract", "mission-type",
   ]

   @charter_list_app.command()
   def list_cmd(
       show_available: bool = typer.Option(
           False, "--show-available",
           help="Also show available-but-not-activated artifacts.",
       ),
       repo_root: Path = typer.Option(Path("."), hidden=True),
   ) -> None:
       """List activated doctrine artifacts for each of the 9 kinds."""
       ctx = ProjectContext.from_repo(repo_root)
       manager = CharterPackManager()
       activated_map = manager.list_activated(ctx)

       table = Table(title="Charter Activation State", show_lines=True)
       table.add_column("Kind", style="bold cyan", no_wrap=True)
       table.add_column("Activated", style="white")
       if show_available:
           table.add_column("Available (not activated)", style="dim")

       for kind in _KIND_ORDER:
           value = activated_map.get(kind)
           if value is None:
               activated_str = "[dim](All built-ins — no explicit activation)[/dim]"
           elif len(value) == 0:
               activated_str = "[yellow](Nothing activated — explicit restriction)[/yellow]"
           else:
               activated_str = ", ".join(sorted(value))

           if show_available:
               available = manager.list_available(ctx, kind)
               activated_set = value or frozenset()
               not_activated = sorted(available - activated_set) if available else []
               available_str = ", ".join(not_activated) if not_activated else "[dim]—[/dim]"
               table.add_row(kind, activated_str, available_str)
           else:
               table.add_row(kind, activated_str)

       console.print(table)
   ```

   Adjust `CharterPackManager.list_activated()` and `list_available()` call signatures
   to match what WP03 actually provides. If the method signatures differ, adapt
   accordingly.

**Validation**:
```bash
cd /home/stijn/Documents/_code/SDD/fork/spec-kitty
python -c "from specify_cli.cli.commands.charter.list_cmd import charter_list_app; print('import ok')"
```
Expected: `import ok`.

---

### T028 — Create `pack.py` and register all new apps in `_app.py`

**Requirement refs**: FR-011

**Files**:
- `src/specify_cli/cli/commands/charter/pack.py` (new)
- `src/specify_cli/cli/commands/charter/_app.py`

**Steps**:

1. Create `src/specify_cli/cli/commands/charter/pack.py`:

   ```python
   """spec-kitty charter pack — charter pack management commands (FR-011)."""

   from __future__ import annotations
   from pathlib import Path
   import typer
   from rich.console import Console
   from charter.invocation_context import ProjectContext

   __all__ = ["charter_pack_app"]

   charter_pack_app = typer.Typer(
       name="pack",
       help="Charter pack management commands.",
       no_args_is_help=True,
   )
   console = Console()

   @charter_pack_app.command("consistency-check")
   def consistency_check_cmd(
       json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
       repo_root: Path = typer.Option(Path("."), hidden=True),
   ) -> None:
       """Run consistency check against activated doctrine artifacts (FR-011)."""
       from charter.consistency_check import run_consistency_check
       ctx = ProjectContext.from_repo(repo_root)
       report = run_consistency_check(ctx)
       if json_output:
           typer.echo(report.to_json())
       else:
           if report.coherent:
               console.print("[green]Charter pack is coherent.[/green]")
           else:
               console.print("[red]Consistency issues found:[/red]")
               for ref in report.unknown_references:
                   console.print(f"  [red]Unknown reference:[/red] {ref}")
               for ref in report.missing_from_doctrine:
                   console.print(f"  [yellow]Missing from doctrine:[/yellow] {ref}")
               for v in report.kind_violations:
                   console.print(f"  [red]Kind violation:[/red] {v}")
               for s in report.suggestions:
                   console.print(f"  [dim]Suggestion:[/dim] {s}")
       raise typer.Exit(0 if report.coherent else 1)
   ```

2. Edit `src/specify_cli/cli/commands/charter/_app.py`. Add three new registrations
   **after** the existing registrations (bundle, mission-type, activate):

   ```python
   from specify_cli.cli.commands.charter.deactivate import charter_deactivate_app
   from specify_cli.cli.commands.charter.list_cmd import charter_list_app
   from specify_cli.cli.commands.charter.pack import charter_pack_app

   charter_app.add_typer(charter_deactivate_app, name="deactivate")
   charter_app.add_typer(charter_list_app, name="list")
   charter_app.add_typer(charter_pack_app, name="pack")
   ```

   Do not remove any existing registrations.

**Validation**:
```bash
cd /home/stijn/Documents/_code/SDD/fork/spec-kitty
python -c "
from specify_cli.cli.commands.charter._app import charter_app
names = [t.name for t in charter_app.registered_groups]
print('registered sub-apps:', names)
assert 'deactivate' in names, 'deactivate missing'
assert 'list' in names, 'list missing'
assert 'pack' in names, 'pack missing'
print('all registrations present')
"
```
Expected: prints `all registrations present` with no assertion errors.

---

### T029 — Update and write CLI tests

**Requirement refs**: FR-004, FR-005, FR-006, FR-007, FR-008, FR-014

**Files**:
- `tests/specify_cli/cli/commands/charter/test_charter_activate_commands.py`
- `tests/specify_cli/cli/commands/charter/test_charter_deactivate_commands.py` (new)
- `tests/specify_cli/cli/commands/charter/test_charter_list_commands.py` (new)

**Steps**:

1. **Update `test_charter_activate_commands.py`** (ATDD for T024/T025):
   - Ensure all old `--action-sequence` and override-file assertions are gone.
   - Ensure coverage of: valid `<kind> <id>` activate, unknown kind → exit 1,
     `--cascade all` invocation, and `config.yaml` mutation.

2. **Create `test_charter_deactivate_commands.py`**:

   Write the following tests using typer `CliRunner` or direct function calls with a
   `tmp_path`-backed project:

   - `test_deactivate_happy_path`: call `deactivate directive some-directive` against
     a project where `activated_directives` contains `"some-directive"` → exit 0,
     ID removed from config.
   - `test_deactivate_unknown_kind_exits_1`: call with `kind="nonsense"` → exit code 1,
     error message contains `"Unknown kind"`.
   - `test_deactivate_none_state_exits_1`: project with no `activated_directives` key
     in config.yaml (migration not run) → `CharterPackManager().deactivate()` raises,
     CLI exits 1, message contains `"spec-kitty upgrade"`.
   - `test_deactivate_cascade`: call with `--cascade all` → all cascaded kinds also
     deactivated in config.
   - `test_deactivate_shared_artifact_skipped`: shared-artifact protection triggers →
     `Skipped (shared artifact)` in output, exit 0.

3. **Create `test_charter_list_commands.py`**:

   - `test_list_all_none_shows_builtin_message`: project with no explicit activation
     keys → all 9 rows show "(All built-ins — no explicit activation)".
   - `test_list_shows_explicit_activations`: project with `activated_directives:
     [python-style-guide]` in config → row for `directive` shows `python-style-guide`.
   - `test_list_show_available_includes_doctrine_entries`: `--show-available` flag
     causes a third column to appear in output with available-but-not-activated items
     from doctrine.

4. Mark all new tests `@pytest.mark.fast` where they use only filesystem/mocks; mark
   integration-level tests (those that require real `CharterPackManager` reads of
   doctrine) with `@pytest.mark.doctrine`.

**Validation**:
```bash
cd /home/stijn/Documents/_code/SDD/fork/spec-kitty
pytest tests/specify_cli/cli/commands/charter/ -x -v
```
Expected: all tests pass. Zero references to `--action-sequence` or
`.kittify/overrides/`.

---

## Definition of Done

Before marking WP06 as `for_review`:

- [ ] `pytest tests/specify_cli/cli/commands/charter/ -x` — passes with no skips.
- [ ] `spec-kitty charter activate directive python-style-guide --repo-root <test-project>`
  runs without error and writes to `config.yaml` (manual spot-check).
- [ ] `spec-kitty charter deactivate directive python-style-guide --repo-root <test-project>`
  runs without error.
- [ ] `spec-kitty charter list --repo-root <test-project>` outputs a 9-row table.
- [ ] `spec-kitty charter pack consistency-check --repo-root <test-project>` exits 0
  or 1 (not crashes).
- [ ] No `--action-sequence` test remnants remain in `test_charter_activate_commands.py`.
- [ ] `ruff check src/specify_cli/cli/commands/charter/` — no lint errors.
- [ ] `mypy src/specify_cli/cli/commands/charter/ --strict` — no type errors.
- [ ] No files outside `owned_files` were modified.
