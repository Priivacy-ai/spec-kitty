# Feature Specification: Auto-protect Agent Directories
*Path: [kitty-specs/003-auto-protect-agent/spec.md](kitty-specs/003-auto-protect-agent/spec.md)*

**Feature Branch**: `003-auto-protect-agent`
**Created**: 2025-11-10
**Status**: Draft
**Input**: User description: "Running spec-kitty init should not affect the user's git repo. To that end, all of the agent specific directories (eg .codex, .opencode, .claude and all of the others which will demand research), should ALL be added to .gitignore"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Initialize Project with Git Protection (Priority: P1)

As a developer running `spec-kitty init` for the first time, I want all agent-specific directories to be automatically added to .gitignore so that sensitive files and credentials are never accidentally committed to my git repository.

**Why this priority**: Protecting sensitive data is critical for security and must work from the very first initialization.

**Independent Test**: Can be fully tested by running `spec-kitty init`, selecting agents, and verifying that .gitignore contains all agent directories.

**Acceptance Scenarios**:

1. **Given** a project with no .gitignore file, **When** I run spec-kitty init and select Claude and Codex agents, **Then** .gitignore is created with entries for .claude/ and .codex/
2. **Given** a project with an existing .gitignore, **When** I run spec-kitty init and select agents, **Then** agent directories are appended to .gitignore without duplicating existing entries
3. **Given** .gitignore already contains some agent directories, **When** I run spec-kitty init with additional agents, **Then** only missing directories are added

---

### User Story 2 - Reinitialize Without Duplicates (Priority: P2)

As a developer who runs `spec-kitty init` multiple times (to add new agents or reconfigure), I want the tool to intelligently handle existing .gitignore entries so that my file doesn't get polluted with duplicate entries.

**Why this priority**: Users often run init multiple times during project setup, and duplicate entries create confusion and maintenance burden.

**Independent Test**: Can be tested by running `spec-kitty init` twice with the same agent selection and verifying no duplicate entries appear.

**Acceptance Scenarios**:

1. **Given** .gitignore already has .claude/ entry, **When** I run spec-kitty init selecting Claude again, **Then** no duplicate .claude/ entry is added
2. **Given** .gitignore has a commented section for agent directories, **When** I reinitialize, **Then** new entries are added to the existing section, not a new section

---

### User Story 3 - Protect All Known Agent Directories (Priority: P3)

As a developer working with multiple AI agents, I want spec-kitty to protect ALL known agent directories, not just the ones I currently selected, to future-proof my repository against accidental credential exposure.

**Why this priority**: Provides additional safety for users who may add agents later without re-running init.

**Independent Test**: Can be tested by verifying that all directories in the agent registry are added to .gitignore regardless of selection.

**Acceptance Scenarios**:

1. **Given** I only selected Claude agent, **When** spec-kitty init completes, **Then** all known agent directories (.claude/, .codex/, .opencode/, etc.) are added to .gitignore
2. **Given** new agents are added to spec-kitty in future versions, **When** I update and run init, **Then** new agent directories are automatically protected

---

### Edge Cases

- What happens when .gitignore has read-only permissions? System should warn user and provide instructions to fix permissions
- How does system handle .gitignore with non-standard line endings (CRLF vs LF)? System should preserve existing line ending style
- What happens if user manually removed agent directories from .gitignore? System should re-add them on next init
- How does system handle .gitignore with complex patterns that might already cover agent directories? System should still add explicit entries for clarity

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST automatically add all agent-specific directories to .gitignore during spec-kitty init
- **FR-002**: System MUST create .gitignore file if it doesn't exist in the project root
- **FR-003**: System MUST detect and avoid adding duplicate entries to existing .gitignore files
- **FR-004**: System MUST preserve existing .gitignore content and formatting when appending new entries
- **FR-005**: System MUST add a clear comment marker to identify auto-managed entries
- **FR-006**: System MUST include all directories from the agent registry: .claude/, .codex/, .opencode/, .windsurf/, .gemini/, .cursor/, .qwen/, .kilocode/, .augment/, .github/, .roo/, .amazonq/
- **FR-007**: System MUST handle both empty and populated .gitignore files correctly
- **FR-008**: System MUST add directories with trailing slash to indicate they are directories, not files
- **FR-009**: System MUST report to the user when .gitignore has been modified
- **FR-010**: System MUST handle file system errors gracefully with appropriate user messaging

### Key Entities *(include if feature involves data)*

- **Agent Directory Registry**: Central list of all known agent-specific directories that may contain sensitive data
- **Gitignore Entry**: A line in .gitignore file representing a path pattern to exclude from git tracking
- **Auto-managed Section**: A marked section in .gitignore containing entries managed by spec-kitty

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of agent directories are successfully added to .gitignore after running spec-kitty init
- **SC-002**: Zero duplicate entries are created when running spec-kitty init multiple times
- **SC-003**: .gitignore modification completes in under 1 second for typical projects
- **SC-004**: 100% of users avoid accidentally committing agent credentials after using spec-kitty init
- **SC-005**: Existing .gitignore content is preserved with 100% accuracy (no data loss)
- **SC-006**: User receives clear confirmation message within 2 seconds of .gitignore being updated

## Assumptions

- Line ending style (LF vs CRLF) will be auto-detected from existing .gitignore or use system default for new files
- File permissions allow writing to .gitignore (will warn if read-only)
- Project root can be determined from current working directory
- Agent directories always use the same naming pattern (dot prefix + agent name)
- Comment markers use standard git comment syntax (# prefix)