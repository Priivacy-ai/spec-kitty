---
work_package_id: WP14
title: CLI — charter mission-type list / mission-type list alias / mission-type show
dependencies:
- WP05
- WP13
requirement_refs:
- FR-016
- FR-017
tracker_refs: []
planning_base_branch: feat/doctrine-mission-type-spec-01KSWJVX
merge_target_branch: feat/doctrine-mission-type-spec-01KSWJVX
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-mission-type-spec-01KSWJVX. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-mission-type-spec-01KSWJVX unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-charter-doctrine-mission-type-configuration-01KSWJVX
base_commit: 21f6ebbfc385562681f2210420b1b3a106320a67
created_at: '2026-05-30T20:33:06.956682+00:00'
subtasks:
- T082
- T083
- T084
- T085
- T086
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3430842"
history:
- at: '2026-05-30T17:21:57Z'
  event: created
  note: Initial task breakdown
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/charter_cmd.py
execution_mode: code_change
review_status: acknowledged
owned_files:
- src/specify_cli/cli/commands/charter_cmd.py
- src/specify_cli/cli/main.py
- tests/cli/test_charter_mission_type_commands.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

/ad-hoc-profile-load python-pedro

This profile contains the coding standards, testing requirements, and
architectural constraints you must follow throughout this work package.

---

# Work Package Prompt: WP14 — CLI: charter mission-type list / mission-type list alias / mission-type show

## Context

FR-016 and FR-017 add two user-facing commands for inspecting mission types from the project's perspective (activation-filtered):

- `spec-kitty charter mission-type list` — activated types only (charter-filtered)
- `spec-kitty mission-type list` — alias for charter version
- `spec-kitty mission-type show <id>` — fully resolved definition including action_sequence

These differ from `spec-kitty doctrine mission-type list` (WP13, all types regardless of activation).

## Objective

Add `spec-kitty charter mission-type list`, a top-level `spec-kitty mission-type list` alias, and `spec-kitty mission-type show <id>` to the CLI. Wire them to `charter.existing_mission_types()` and `charter.resolve_action_sequence()`.

## Command Specifications

### spec-kitty charter mission-type list

```
spec-kitty charter mission-type list [--json]
```

Returns: activated mission types for the current project.

Output columns: `id`, `source_layer`, `display_name`, `action_sequence` (space-separated or JSON array).

Example (table):
```
ID             SOURCE       DISPLAY NAME          ACTION SEQUENCE
software-dev   built-in     Software Development  specify, plan, tasks, implement, review
```

### spec-kitty mission-type list (alias)

Identical to `spec-kitty charter mission-type list`. Registered as a top-level command.

### spec-kitty mission-type show <id>

```
spec-kitty mission-type show <id> [--json]
```

Returns: fully resolved MissionType for `<id>` in the current project.

Output: all fields of the resolved `MissionType`:
- `id`
- `display_name`
- `action_sequence` (ordered list)
- `governance_refs` (list, may be empty)
- `template_set` (dict, may be null)
- `source_layer` (where the definition was resolved from)

Raises `UnknownMissionTypeError` if `<id>` is not activated.

## Subtasks

### T082 — Add spec-kitty charter mission-type list

Open `src/specify_cli/cli/commands/charter_cmd.py`. Add a `mission-type` sub-group and `list` command:

```python
@mission_type_app.command("list")
def charter_mission_type_list(
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """List activated mission types for the current project."""
    repo_root = Path.cwd()
    mission_types = existing_mission_types(repo_root)
    ...
```

Use `charter.existing_mission_types(repo_root)` to get the activated list. Then load each type from `MissionTypeRepository` for display metadata.

Include `action_sequence` in the output (call `charter.resolve_action_sequence(id, repo_root)` for each type — or read it directly from the loaded `MissionType` if the repository is already called).

### T083 — Add spec-kitty mission-type list alias

In the top-level CLI (likely `src/specify_cli/cli/main.py` or similar), add:

```python
# Alias: spec-kitty mission-type list → same as spec-kitty charter mission-type list
mission_type_alias_app = typer.Typer(name="mission-type", help="Mission type commands (alias for charter).")
main_app.add_typer(mission_type_alias_app)

@mission_type_alias_app.command("list")
def mission_type_list_alias(...) -> None:
    """Alias for 'spec-kitty charter mission-type list'."""
    charter_mission_type_list(...)  # delegate
```

The alias must behave identically to the charter version — same output, same flags.

### T084 — Implement spec-kitty mission-type show

Add `show` command to `mission_type_alias_app`:

```python
@mission_type_alias_app.command("show")
def mission_type_show(
    mission_type_id: str = typer.Argument(..., help="Mission type ID."),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Show the fully resolved MissionType definition for the current project."""
    repo_root = Path.cwd()
    ...
```

Implementation:
1. Call `charter.existing_mission_types(repo_root)` to check activation
2. If `mission_type_id` not activated: print `UnknownMissionTypeError` message with registered IDs and exit with code 1
3. Load the `MissionType` from `MissionTypeRepository` with full layer resolution
4. Call `charter.resolve_action_sequence(mission_type_id, repo_root)` to get the live sequence
5. Display all fields: id, display_name, action_sequence, governance_refs, template_set, source_layer

### T085 — Wire to charter.existing_mission_types() and resolve_action_sequence()

Ensure the commands use the charter API (not the doctrine API directly):
- `charter.existing_mission_types(repo_root)` for the activated list
- `charter.resolve_action_sequence(mission_type_id, repo_root)` for the live action sequence
- `MissionTypeRepository` for display metadata (display_name, governance_refs, template_set)

The charter API is the only permitted entry point from `specify_cli.*` — no direct `doctrine.*` imports (C-004).

### T086 — Tests for charter mission-type commands

Write `tests/cli/test_charter_mission_type_commands.py`:

Test cases:
- `spec-kitty charter mission-type list` returns only activated types
- `spec-kitty mission-type list` (alias) returns the same results as charter list
- `spec-kitty mission-type show software-dev` displays full resolved definition with action_sequence
- `spec-kitty mission-type show unknown-type` exits with code 1 and shows `UnknownMissionTypeError` message with registered IDs
- `--json` flag on both list and show produces valid JSON
- Alias behaves identically to `charter mission-type list` (same output, not just same exit code)

Use `typer.testing.CliRunner` and `tmp_path` for test isolation.

## Acceptance Criteria

- [ ] `spec-kitty charter mission-type list` works and returns only activated types
- [ ] `spec-kitty mission-type list` alias produces identical output to charter list
- [ ] `spec-kitty mission-type show <id>` renders fully resolved definition
- [ ] `spec-kitty mission-type show <unknown>` exits with code 1 and lists registered IDs
- [ ] `--json` outputs valid JSON for both commands
- [ ] All tests pass
- [ ] No direct `doctrine.*` imports from `specify_cli.*` (C-004)
- [ ] `mypy --strict` clean

## References

- FR-016: mission-type list CLI
- FR-017: mission-type show CLI
- WP05: charter.existing_mission_types() + resolve_action_sequence()
- WP13: doctrine mission-type list (all-types counterpart)

## Activity Log

- 2026-05-30T20:33:07Z – claude:sonnet:python-pedro:implementer – shell_pid=3325242 – Assigned agent via action command
- 2026-05-30T20:42:15Z – claude:sonnet:python-pedro:implementer – shell_pid=3325242 – Ready for review: charter mission-type list/show commands implemented. FR-016 (charter mission-type list + top-level alias) and FR-017 (mission-type show) complete. 25 tests pass.
- 2026-05-30T20:42:42Z – claude:opus:reviewer-renata:reviewer – shell_pid=3365794 – Started review via action command
- 2026-05-30T20:52:32Z – claude:opus:reviewer-renata:reviewer – shell_pid=3365794 – Moved to planned
- 2026-05-30T20:54:20Z – claude:sonnet:python-pedro:implementer – shell_pid=3401376 – Started implementation via action command
- 2026-05-30T21:04:56Z – claude:sonnet:python-pedro:implementer – shell_pid=3401376 – Cycle 2: fixed docs parity and doctrine boundary test
- 2026-05-30T21:05:27Z – claude:opus:reviewer-renata:reviewer – shell_pid=3430842 – Started review via action command
