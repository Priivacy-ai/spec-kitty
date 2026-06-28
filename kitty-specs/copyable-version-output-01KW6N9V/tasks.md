# Work Packages: Copyable Version Output

**Inputs**: Design documents from `/kitty-specs/copyable-version-output-01KW6N9V/`
**Prerequisites**: plan.md, spec.md

**Tests**: Required for version output order and banner absence.

## Work Package WP01: Make Version Output Copyable (Priority: P1)

**Goal**: Make `spec-kitty --version` start with the version line and avoid large ASCII art.
**Independent Test**: Version callback output begins with `spec-kitty-cli version` and does not include the banner/tagline before the version.
**Prompt**: `/tasks/WP01-copyable-version-output.md`
**Requirement Refs**: FR-001, FR-002, FR-003, FR-004, NFR-001, NFR-002, NFR-003, NFR-004, C-001, C-002, C-003

### Included Subtasks

- [ ] T001 Update version callback in `src/specify_cli/__init__.py`
- [ ] T002 Add version output tests in `tests/specify_cli/cli/commands/test_version_output.py`
- [ ] T003 Verify `--version` and `-v` output starts with the copyable version line
- [ ] T004 Run targeted version output tests

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
| NFR-004 | WP01 |
| C-001 | WP01 |
| C-002 | WP01 |
| C-003 | WP01 |

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Update version callback | WP01 | P1 | No |
| T002 | Add version output tests | WP01 | P1 | Yes |
| T003 | Verify version flags | WP01 | P1 | No |
| T004 | Run targeted tests | WP01 | P1 | No |
