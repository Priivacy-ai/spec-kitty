# Work Packages: Alphabetical Command Listing

**Inputs**: Design documents from `/kitty-specs/alphabetical-command-listing-01KW6N8W/`
**Prerequisites**: plan.md, spec.md

**Tests**: Required for root command listing order and command preservation.

## Work Package WP01: Sort Root Command Listing (Priority: P1)

**Goal**: Show root commands in alphabetical order when users run bare `spec-kitty`.
**Independent Test**: Root command names produced by the CLI command object are sorted and still include representative commands.
**Prompt**: `/tasks/WP01-alphabetical-command-listing.md`
**Requirement Refs**: FR-001, FR-002, FR-003, FR-004, NFR-001, NFR-002, NFR-003, C-001, C-002, C-003

### Included Subtasks

- [x] T001 Sort root command metadata in `src/specify_cli/cli/commands/__init__.py`
- [x] T002 Add regression tests in `tests/specify_cli/cli/commands/test_root_command_order.py`
- [x] T003 Verify sorted order and representative command preservation
- [x] T004 Run targeted root command order tests

### Dependencies

- None.

---

## Dependency & Execution Summary

- **Sequence**: WP01 only.
- **MVP Scope**: WP01 completes the mission.

---

## Requirements Coverage Summary

| Requirement ID | Covered By Work Package(s) |
|----------------|----------------------------|
| FR-001 | WP01 |
| FR-002 | WP01 |
| FR-003 | WP01 |
| FR-004 | WP01 |
| NFR-001 | WP01 |
| NFR-002 | WP01 |
| NFR-003 | WP01 |
| C-001 | WP01 |
| C-002 | WP01 |
| C-003 | WP01 |

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Sort root command metadata | WP01 | P1 | No |
| T002 | Add root ordering tests | WP01 | P1 | Yes |
| T003 | Verify preservation | WP01 | P1 | No |
| T004 | Run targeted tests | WP01 | P1 | No |
