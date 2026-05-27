---
work_package_id: WP04
title: CLI Validate Command
dependencies:
- WP02
requirement_refs:
- FR-009
- FR-010
- FR-011
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-glossary-seed-file-schema-validation-01KSN752
base_commit: efec054539979268c404cee54726d746657776c4
created_at: '2026-05-27T17:55:39.143075+00:00'
subtasks:
- T016
- T017
- T018
- T019
agent: "claude:opus:implementer-ivan:implementer"
shell_pid: "69303"
history:
- at: '2026-05-27T17:32:55+00:00'
  event: created
  agent: claude
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/cli/commands/
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/glossary.py
- tests/specify_cli/cli/commands/test_glossary_validate.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile:

```
/ad-hoc-profile-load implementer-ivan
```

## Objective

Add `spec-kitty glossary validate <path>` CLI command for manual validation and CI integration. Supports both single-file and directory-wide validation with human-readable and JSON output modes.

## Context

The glossary CLI (`src/specify_cli/cli/commands/glossary.py`) already has a typer app with `list`, `conflicts`, `resolve`, and `show` subcommands. This WP adds `validate` as a new subcommand. The validation logic itself lives in `seed_validation.py` (WP02); this WP is the CLI presentation layer.

See `kitty-specs/glossary-seed-file-schema-validation-01KSN752/contracts/validate-command.md` for the full CLI contract.

## Branch Strategy

- **Planning base branch**: `main`
- **Final merge target**: `main`
- Execution worktrees are allocated per computed lane from `lanes.json`.

## Detailed Guidance

### T016: Add validate Subcommand

**Purpose**: Register the `validate` subcommand on the glossary typer app.

**Steps**:
1. In `src/specify_cli/cli/commands/glossary.py`, add the command:

```python
@app.command("validate")
def validate_cmd(
    path: Path = typer.Argument(
        ...,
        help="Path to a glossary seed file (.yaml) or directory of seed files",
        exists=True,
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output validation results as JSON",
    ),
) -> None:
    """Validate glossary seed file(s) against the schema."""
    if path.is_file():
        _validate_single_file(path, json_output)
    elif path.is_dir():
        _validate_directory(path, json_output)
    else:
        console.print(f"[red]Error: {path} is not a file or directory[/red]")
        raise typer.Exit(1)
```

2. Add imports at the top of the file:
```python
from specify_cli.glossary.seed_validation import validate_seed_file_data, validate_scope_filename
from specify_cli.glossary.exceptions import SeedFileValidationError
```

**Files**: `src/specify_cli/cli/commands/glossary.py`

### T017: Implement Single-File Validation

**Purpose**: Validate one seed file and report results.

**Steps**:
1. Add helper function:

```python
def _validate_single_file(file_path: Path, json_output: bool) -> None:
    """Validate a single glossary seed file."""
    from ruamel.yaml import YAML

    yaml = YAML()
    yaml.preserve_quotes = True

    try:
        data = yaml.load(file_path)
    except Exception as exc:
        if json_output:
            result = {
                "files": [{"path": str(file_path), "valid": False, "term_count": 0,
                           "errors": [{"term_index": None, "term_surface": None,
                                       "field": None, "message": f"YAML parse error: {exc}"}]}],
                "total_files": 1, "valid_files": 0, "invalid_files": 1,
            }
            print(json_lib.dumps(result, indent=2))
        else:
            console.print(f"[red]YAML parse error in {file_path}: {exc}[/red]")
        raise typer.Exit(1)

    try:
        validated = validate_seed_file_data(data, file_path)
        term_count = len(validated.terms)
        if json_output:
            result = {
                "files": [{"path": str(file_path), "valid": True,
                           "term_count": term_count, "errors": []}],
                "total_files": 1, "valid_files": 1, "invalid_files": 0,
            }
            print(json_lib.dumps(result, indent=2))
        else:
            console.print(f"[green]✓[/green] {file_path} — Valid ({term_count} terms)")
    except SeedFileValidationError as exc:
        if json_output:
            errors = [
                {
                    "term_index": e.term_index,
                    "term_surface": e.term_surface,
                    "field": e.field,
                    "message": e.message,
                }
                for e in exc.errors
            ]
            result = {
                "files": [{"path": str(file_path), "valid": False,
                           "term_count": 0, "errors": errors}],
                "total_files": 1, "valid_files": 0, "invalid_files": 1,
            }
            print(json_lib.dumps(result, indent=2))
        else:
            console.print(f"\n[red]Validating {file_path}...[/red]\n")
            for e in exc.errors:
                loc_parts: list[str] = []
                if e.term_index is not None:
                    surface_label = f" '{e.term_surface}'" if e.term_surface else ""
                    loc_parts.append(f"term[{e.term_index}]{surface_label}")
                if e.field:
                    loc_parts.append(e.field)
                loc = " → ".join(loc_parts) if loc_parts else "file"
                console.print(f"  [red]✗[/red] {loc}: {e.message}")
            console.print(f"\n{len(exc.errors)} error(s) in {file_path}")
        raise typer.Exit(1)
```

**Files**: `src/specify_cli/cli/commands/glossary.py`

### T018: Implement Directory Validation

**Purpose**: Validate all `*.yaml` files in a directory, including scope filename validation.

**Steps**:
1. Add helper function:

```python
def _validate_directory(dir_path: Path, json_output: bool) -> None:
    """Validate all glossary seed files in a directory."""
    from ruamel.yaml import YAML

    yaml_files = sorted(dir_path.glob("*.yaml"))
    if not yaml_files:
        if json_output:
            print(json_lib.dumps({"files": [], "total_files": 0,
                                  "valid_files": 0, "invalid_files": 0}, indent=2))
        else:
            console.print(f"[yellow]No .yaml files found in {dir_path}[/yellow]")
        return

    yaml = YAML()
    yaml.preserve_quotes = True
    file_results = []
    invalid_count = 0

    for yaml_file in yaml_files:
        # Check scope filename
        scope = validate_scope_filename(yaml_file)
        if scope is None and not json_output:
            console.print(
                f"[yellow]⚠ {yaml_file.name}: not a recognized scope filename "
                f"(expected one of: {', '.join(f'{s.value}.yaml' for s in GlossaryScope)})[/yellow]"
            )

        try:
            data = yaml.load(yaml_file)
        except Exception as exc:
            file_results.append({
                "path": str(yaml_file), "valid": False, "term_count": 0,
                "errors": [{"term_index": None, "term_surface": None,
                            "field": None, "message": f"YAML parse error: {exc}"}],
            })
            invalid_count += 1
            if not json_output:
                console.print(f"[red]✗ {yaml_file.name}: YAML parse error: {exc}[/red]")
            continue

        try:
            validated = validate_seed_file_data(data, yaml_file)
            file_results.append({
                "path": str(yaml_file), "valid": True,
                "term_count": len(validated.terms), "errors": [],
            })
            if not json_output:
                console.print(f"[green]✓[/green] {yaml_file.name} — Valid ({len(validated.terms)} terms)")
        except SeedFileValidationError as exc:
            errors = [
                {"term_index": e.term_index, "term_surface": e.term_surface,
                 "field": e.field, "message": e.message}
                for e in exc.errors
            ]
            file_results.append({
                "path": str(yaml_file), "valid": False,
                "term_count": 0, "errors": errors,
            })
            invalid_count += 1
            if not json_output:
                console.print(f"\n[red]✗ {yaml_file.name}:[/red]")
                for e in exc.errors:
                    loc_parts: list[str] = []
                    if e.term_index is not None:
                        surface_label = f" '{e.term_surface}'" if e.term_surface else ""
                        loc_parts.append(f"term[{e.term_index}]{surface_label}")
                    if e.field:
                        loc_parts.append(e.field)
                    loc = " → ".join(loc_parts) if loc_parts else "file"
                    console.print(f"    {loc}: {e.message}")

    if json_output:
        print(json_lib.dumps({
            "files": file_results,
            "total_files": len(yaml_files),
            "valid_files": len(yaml_files) - invalid_count,
            "invalid_files": invalid_count,
        }, indent=2))
    else:
        console.print(f"\n[dim]Summary: {invalid_count} of {len(yaml_files)} files failed validation.[/dim]")

    if invalid_count > 0:
        raise typer.Exit(1)
```

2. Add import for `GlossaryScope`:
```python
from specify_cli.glossary.scope import GlossaryScope
```
(This import likely already exists in the file.)

**Files**: `src/specify_cli/cli/commands/glossary.py`

### T019: Write Integration Tests

**Purpose**: Test the CLI validate command with real YAML files.

**Steps**:
1. Create `tests/specify_cli/cli/commands/test_glossary_validate.py`
2. Use `tmp_path` fixture to create test seed files
3. Test cases:
   - **Valid file**: Create valid seed YAML, run validate, assert exit code 0
   - **Invalid surface**: Create seed with non-normalized surface, assert exit code 1, assert error output mentions the surface and normalization
   - **Missing definition**: Assert error output mentions definition
   - **Directory mode**: Create directory with valid and invalid files, assert exit code 1, assert summary output
   - **JSON output**: Test `--json` flag produces valid JSON with correct structure
   - **Empty directory**: Assert no error, exit code 0
   - **Unknown scope filename**: Assert warning in human output
   - **YAML parse error**: Create file with invalid YAML syntax, assert error

4. Use `typer.testing.CliRunner` for CLI invocation:
```python
from typer.testing import CliRunner
from specify_cli.cli.commands.glossary import app

runner = CliRunner()

def test_validate_valid_file(tmp_path):
    seed = tmp_path / "spec_kitty_core.yaml"
    seed.write_text("terms:\n  - surface: hello\n    definition: A greeting\n")
    result = runner.invoke(app, ["validate", str(seed)])
    assert result.exit_code == 0
    assert "Valid" in result.output
```

**Files**: `tests/specify_cli/cli/commands/test_glossary_validate.py`

## Definition of Done

- [ ] `spec-kitty glossary validate <file>` validates a single seed file
- [ ] `spec-kitty glossary validate <dir>` validates all `*.yaml` files in directory
- [ ] Exit code 0 on valid, 1 on invalid
- [ ] Human output shows file, term, field, and message for each error
- [ ] `--json` output matches the contract in `contracts/validate-command.md`
- [ ] Unknown scope filenames produce a warning (not error) in directory mode
- [ ] Integration tests cover valid, invalid, directory, JSON, and edge cases
- [ ] mypy --strict passes

## Risks

- `typer.testing.CliRunner` may not capture all output correctly if `rich` console is used. Use `Console(file=...)` or test with subprocess if needed.

## Reviewer Guidance

- Verify exit codes: 0 for valid, 1 for any error
- Check JSON output structure matches the contract
- Verify scope filename warning is a warning (yellow), not an error (red)
- Confirm the command integrates with the existing glossary typer app (no new app registration needed)

## Activity Log

- 2026-05-27T17:55:39Z – claude:opus:implementer-ivan:implementer – shell_pid=69303 – Assigned agent via action command
- 2026-05-27T18:00:51Z – claude:opus:implementer-ivan:implementer – shell_pid=69303 – Ready for review
- 2026-05-27T18:01:35Z – claude:opus:implementer-ivan:implementer – shell_pid=69303 – Review passed: 20 CLI tests, file/dir/JSON modes all working
