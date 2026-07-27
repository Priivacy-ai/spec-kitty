---
work_package_id: WP13
title: CLI — spec-kitty doctrine mission-type list
dependencies:
- WP03
- WP04
requirement_refs:
- FR-013
- FR-014
tracker_refs: []
planning_base_branch: feat/doctrine-mission-type-spec-01KSWJVX
merge_target_branch: feat/doctrine-mission-type-spec-01KSWJVX
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-mission-type-spec-01KSWJVX. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-mission-type-spec-01KSWJVX unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-charter-doctrine-mission-type-configuration-01KSWJVX
base_commit: 9a00f25f59abe8dd171f6abd7cc586f7cc5ec4e4
created_at: '2026-05-30T20:09:28.203674+00:00'
subtasks:
- T077
- T078
- T079
- T080
- T081
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3284029"
history:
- at: '2026-05-30T17:21:57Z'
  event: created
  note: Initial task breakdown
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/doctrine.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/doctrine.py
- tests/cli/test_doctrine_commands.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

/ad-hoc-profile-load python-pedro

This profile contains the coding standards, testing requirements, and
architectural constraints you must follow throughout this work package.

---

# Work Package Prompt: WP13 — CLI: spec-kitty doctrine mission-type list

## Context

FR-013 requires `spec-kitty doctrine mission-type list` to enumerate all doctrine templates. The `spec-kitty doctrine` CLI group already exists. This WP adds the `mission-type` sub-group with a `list` subcommand.

This command lists ALL mission types visible in the doctrine layer (built-in + org overrides + project overrides) — **regardless of activation state**. This is different from `spec-kitty charter mission-type list` (WP14), which lists only activated types.

The command is read-only and works from any project directory.

## Objective

Add `spec-kitty doctrine mission-type list [--kind]` to the existing `doctrine` CLI group. Wire it to `MissionTypeRepository` for layer-aware enumeration. Support `--json` output.

## Command Specification

```
spec-kitty doctrine mission-type list [--json]
```

Output columns:
- `id` — mission type ID (e.g., `software-dev`)
- `source_layer` — `built-in`, `org`, or `project`
- `display_name` — human-readable name

Example output (table mode):
```
ID             SOURCE       DISPLAY NAME
software-dev   built-in     Software Development
documentation  built-in     Documentation
research       built-in     Research
plan           built-in     Plan
```

Example output (`--json`):
```json
[
  {"id": "software-dev", "source_layer": "built-in", "display_name": "Software Development"},
  ...
]
```

## Subtasks

### T077 — Verify doctrine CLI group is registered, then add mission-type sub-group

**Before adding any commands**, run `spec-kitty doctrine --help` (or equivalent) to verify the `doctrine` CLI group is registered in the main CLI. There was a prior incident (PR #1352) where the `spec-kitty doctrine` group was accidentally deregistered and a stale test masked the regression. Confirm the group is present and working before extending it.

If the group is missing: re-register it in the main CLI entry point (check `src/specify_cli/cli/main.py`), add a test that verifies `spec-kitty doctrine --help` exits 0, then proceed.

Open `src/specify_cli/cli/commands/doctrine.py`.

Find the `doctrine` typer app. Add a `mission_type` sub-app:

```python
mission_type_app = typer.Typer(name="mission-type", help="Mission type commands.")
doctrine_app.add_typer(mission_type_app)
```

If the `doctrine_app` structure is different, follow the existing pattern for adding sub-groups.

### T078 — Implement list sub-command

Add the `list` command to `mission_type_app`:

```python
@mission_type_app.command("list")
def mission_type_list(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """List all mission types in the doctrine layer (built-in, org, and project)."""
    ...
```

Implementation:
1. Instantiate `MissionTypeRepository` for the built-in layer
2. If a `PackContext` can be constructed (project has `.kittify/config.yaml`), also scan org and project layers
3. Collect all types with their source_layer annotation
4. Sort by source_layer (built-in first), then by id

Note: this command lists ALL types regardless of activation. An org or project override that provides a new type ID appears here even if not activated.

### T079 — Output formatting: table and JSON

Table output (default): use `rich.table.Table` for consistent formatting with other doctrine commands.

JSON output (`--json` flag): emit a JSON array of dicts with keys `id`, `source_layer`, `display_name`.

Follow the existing pattern in other `doctrine` commands for output formatting.

### T080 — Wire to MissionTypeRepository

`MissionTypeRepository` (from WP03) is the backend. The command:
1. Creates the repository pointing at `src/doctrine/missions/mission_types/` for the built-in layer
2. If org/project overlays exist (from `PackContext`), also creates repositories for those layers
3. Collects and deduplicates: if a type ID appears in multiple layers, the highest-precedence (project) layer wins but all layers are reported (or just the winning one — follow the FR-013 spec: "includes name, kind, source layer, and resolution path")

FR-014: The DRG resolution chain applies: `built-in → org → project`. An org type shadows a built-in type with the same ID; a project type shadows an org type.

### T081 — Tests for doctrine mission-type list

Write (or extend) `tests/cli/test_doctrine_commands.py`:

Test cases:
- Default invocation: returns at least the four built-in types
- All four built-in types appear with `source_layer: built-in`
- `--json` flag: output is valid JSON with the required keys
- No activation required: command works from a directory without `.kittify/config.yaml`
- Error handling: command exits gracefully if doctrine source path is missing

Use `typer.testing.CliRunner` for CLI tests.

## Acceptance Criteria

- [ ] `spec-kitty doctrine mission-type list` command exists and works
- [ ] Returns all four built-in types with `source_layer: built-in`
- [ ] `--json` output is valid JSON array
- [ ] Command does not require `.kittify/config.yaml` to work (built-in layer only is fine)
- [ ] All tests pass
- [ ] `mypy --strict` clean on `src/specify_cli/cli/commands/doctrine.py`

## References

- FR-013: template list command
- FR-014: template DRG layer resolution
- WP03: MissionTypeRepository
- WP14: charter mission-type list (activated-only counterpart)

## Activity Log

- 2026-05-30T20:09:29Z – claude:sonnet:python-pedro:implementer – shell_pid=3225658 – Assigned agent via action command
- 2026-05-30T20:15:43Z – claude:sonnet:python-pedro:implementer – shell_pid=3225658 – Ready for review: added doctrine mission-type list command with table/JSON output, 10 tests all passing, ruff+mypy clean
- 2026-05-30T20:16:12Z – claude:opus:reviewer-renata:reviewer – shell_pid=3258484 – Started review via action command
- 2026-05-30T20:18:51Z – claude:opus:reviewer-renata:reviewer – shell_pid=3258484 – Moved to planned
- 2026-05-30T20:19:24Z – claude:sonnet:python-pedro:implementer – shell_pid=3269780 – Started implementation via action command
- 2026-05-30T20:21:45Z – claude:sonnet:python-pedro:implementer – shell_pid=3269780 – Cycle 2 fix: merged WP03, replaced try/except fallback with direct MissionTypeRepository import
- 2026-05-30T20:22:06Z – claude:opus:reviewer-renata:reviewer – shell_pid=3284029 – Started review via action command
