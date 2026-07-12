# Mission Specification: Short Help Flag

**Mission Branch**: `short-help-flag-01KW6N7D`
**Created**: 2026-06-28
**Status**: Draft
**Input**: User description: "add an expected `-h`. Currently we only have `--help`; make sure the `-h` works anywhere `--help` works."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Request Root Help With a Short Flag (Priority: P1)

A CLI user can run `spec-kitty -h` and receive the same help information they would receive from `spec-kitty --help`.

**Why this priority**: The root help command is the most common first contact for users exploring the CLI and establishes the expected shorthand behavior.

**Independent Test**: Can be tested by comparing the help output and exit behavior of `spec-kitty -h` and `spec-kitty --help`.

**Acceptance Scenarios**:

1. **Given** a user is at any location where the CLI can be invoked, **When** the user runs `spec-kitty -h`, **Then** the CLI shows root help successfully.
2. **Given** root help is available with `--help`, **When** the user requests root help with `-h`, **Then** the result is equivalent for user-facing help content and success/failure behavior.

---

### User Story 2 - Request Command and Subcommand Help With a Short Flag (Priority: P1)

A CLI user can append `-h` anywhere they currently append `--help`, including command groups and nested subcommands.

**Why this priority**: The user explicitly requires consistency across the command surface, not only at the root command.

**Independent Test**: Can be tested by selecting representative root, command-group, and nested subcommand help locations and verifying `-h` works anywhere `--help` works.

**Acceptance Scenarios**:

1. **Given** a command group supports `--help`, **When** a user runs that command group with `-h`, **Then** the CLI shows the command group's help successfully.
2. **Given** a nested subcommand supports `--help`, **When** a user runs that nested subcommand with `-h`, **Then** the CLI shows the nested subcommand's help successfully.
3. **Given** a help location has command-specific options or subcommands, **When** the user requests help with `-h`, **Then** those same user-facing details are visible as they are with `--help`.

---

### Edge Cases

- `-h` should be treated as a help request, not as an unknown option, at every command path where `--help` is accepted.
- `-h` should not change the behavior of non-help short options if any exist or are added later.
- Help output should preserve existing exit behavior and not trigger command side effects.
- The user-facing help content for `-h` should not drift from `--help` over time.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Root short help | As a CLI user, I want `spec-kitty -h` to show root help so that the common short help flag works as expected. | High | Open |
| FR-002 | Command-group short help | As a CLI user, I want `-h` to work for every command group where `--help` works so that help access is consistent. | High | Open |
| FR-003 | Nested subcommand short help | As a CLI user, I want `-h` to work for every nested subcommand where `--help` works so that deep workflows are easy to inspect. | High | Open |
| FR-004 | Help parity | As a CLI user, I want `-h` help content and exit behavior to match `--help` so that either flag is interchangeable for help. | High | Open |
| FR-005 | No command side effects | As a CLI user, I want `-h` to display help without running the target command's action so that asking for help is safe. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Command-surface coverage | Automated tests must verify `-h` for the root command, at least two command groups, and at least two nested subcommands. | Testability | High | Open |
| NFR-002 | Parity threshold | For tested command paths, `-h` and `--help` must produce equivalent user-facing help content and the same exit status in 100% of cases. | Consistency | High | Open |
| NFR-003 | Safe help behavior | Help requests using `-h` must not create, modify, or delete project files in 100% of tested help invocations. | Reliability | High | Open |
| NFR-004 | Discoverability | Root help output must make the availability of help clear without requiring users to know implementation details. | Usability | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Exact scope | `-h` must work anywhere `--help` works across the CLI command surface. | Product | High | Open |
| C-002 | Preserve long help | Existing `--help` behavior must remain available and compatible. | Compatibility | High | Open |
| C-003 | Independent PR | This mission must remain independently reviewable from autocompletion, alphabetical command listing, and version output missions. | Delivery | High | Open |

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `spec-kitty -h` shows root help with the same exit status as `spec-kitty --help`.
- **SC-002**: `-h` works for 100% of tested command groups and nested subcommands where `--help` works.
- **SC-003**: For every tested command path, `-h` and `--help` expose equivalent user-facing help content.
- **SC-004**: Help invocations using `-h` complete without mutating project files in all automated tests.

## Assumptions

- "Anywhere `--help` works" includes root commands, command groups, and nested subcommands exposed through the CLI.
- Exact byte-for-byte output identity is not required if the CLI framework includes invocation-specific formatting, but user-facing help content and exit behavior must be equivalent.
