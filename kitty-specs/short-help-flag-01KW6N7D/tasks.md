# Work Packages: Short Help Flag

**Inputs**: Design documents from `/kitty-specs/short-help-flag-01KW6N7D/`
**Prerequisites**: plan.md, spec.md

**Tests**: Required for root, command group, and nested subcommand `-h` parity with `--help`.

**Organization**: One focused work package owns the CLI-wide short help flag contract.

## Subtask Format: `[Txxx] [P?] Description`

- **[P]** indicates the subtask can proceed in parallel.
- Include precise file paths or modules.

## Path Conventions

- **Single project**: `src/`, `tests/`

---

## Work Package WP01: Add Universal Short Help Flag (Priority: P1)

**Goal**: Make `-h` work anywhere `--help` works across the user-facing CLI.
**Independent Test**: Root, command group, and nested subcommand invocations using `-h` show help and match the success behavior of `--help`.
**Prompt**: `/tasks/WP01-short-help-flag.md`
**Requirement Refs**: FR-001, FR-002, FR-003, FR-004, FR-005, NFR-001, NFR-002, NFR-003, NFR-004, C-001, C-002, C-003

### Included Subtasks

- [ ] T001 Add centralized short-help option configuration for root app and registered commands
- [ ] T002 Add regression tests in `tests/specify_cli/cli/commands/test_short_help_flag.py`
- [ ] T003 Verify `-h` parity for root, command group, and nested subcommand paths
- [ ] T004 Run targeted short-help tests

### Implementation Notes

- Preserve existing `--help` behavior.
- Do not execute command actions while serving help.
- Keep the change local to CLI construction/registration helpers.

### Parallel Opportunities

- Test cases can be drafted alongside implementation once the target paths are selected.

### Dependencies

- None.

### Risks & Mitigations

- Typer may not propagate root context settings to every nested command. Add tests across at least three levels to catch gaps.

---

## Dependency & Execution Summary

- **Sequence**: WP01 only.
- **Parallelization**: Not needed for this small PR.
- **MVP Scope**: WP01 completes the mission.

---

## Requirements Coverage Summary

| Requirement ID | Covered By Work Package(s) |
|----------------|----------------------------|
| FR-001 | WP01 |
| FR-002 | WP01 |
| FR-003 | WP01 |
| FR-004 | WP01 |
| FR-005 | WP01 |
| NFR-001 | WP01 |
| NFR-002 | WP01 |
| NFR-003 | WP01 |
| NFR-004 | WP01 |
| C-001 | WP01 |
| C-002 | WP01 |
| C-003 | WP01 |

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Configure short help | WP01 | P1 | No |
| T002 | Add regression tests | WP01 | P1 | Yes |
| T003 | Verify parity across levels | WP01 | P1 | No |
| T004 | Run targeted tests | WP01 | P1 | No |
