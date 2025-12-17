# Feature Specification: Frontmatter-Only Lane Management
*Path: [kitty-specs/007-frontmatter-only-lane/spec.md](kitty-specs/007-frontmatter-only-lane/spec.md)*

**Feature Branch**: `007-frontmatter-only-lane`
**Created**: 2025-12-17
**Status**: Draft
**Input**: Replace directory-based lane detection with frontmatter-only lane management. All WP files live in flat tasks/ directory and never move.

## Overview

Currently, Spec Kitty determines a work package's lane by its directory location (`tasks/planned/`, `tasks/doing/`, `tasks/for_review/`, `tasks/done/`). This creates complexity:

- Moving files between directories when lanes change
- Race conditions when multiple agents move files simultaneously
- Mismatch bugs when YAML `lane:` field gets out of sync with directory
- Agents incorrectly editing `lane:` field without moving files

This feature eliminates directory-based lanes entirely. All WP files live in a flat `tasks/` directory and the `lane:` YAML frontmatter field becomes the single source of truth.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Agent Changes Work Package Lane (Priority: P1)

An AI agent working on a feature needs to move a work package from `doing` to `for_review` after completing implementation.

**Why this priority**: This is the core use case - lane transitions happen constantly during feature development. Must work reliably without file conflicts.

**Independent Test**: Agent runs `tasks_cli.py move 007-feature WP04 for_review --note "Ready for review"` and the lane changes without any file system operations.

**Acceptance Scenarios**:

1. **Given** WP04 exists in `tasks/` with `lane: "doing"`, **When** agent runs `tasks_cli.py move 007-feature WP04 for_review`, **Then** the file stays in `tasks/`, `lane:` field updates to `"for_review"`, and activity log is appended
2. **Given** WP04 has `lane: "doing"`, **When** agent directly edits `lane: "for_review"` in the YAML, **Then** the change is valid and the system recognizes WP04 as being in for_review lane
3. **Given** two agents working on WP04 and WP05 simultaneously, **When** both change lanes at the same time, **Then** no file conflicts occur since files don't move

---

### User Story 2 - Developer Views Lane Status (Priority: P1)

A developer or agent needs to see the current status of all work packages for a feature to understand what's in progress, pending review, or complete.

**Why this priority**: Visibility is essential since directory structure no longer provides visual organization.

**Independent Test**: User runs `tasks_cli.py status` from feature worktree and sees a formatted table of all WPs grouped by lane.

**Acceptance Scenarios**:

1. **Given** feature 007 has WP01 (done), WP02 (doing), WP03 (planned), **When** user runs `tasks_cli.py status 007-feature`, **Then** output shows all WPs grouped by lane with clear formatting
2. **Given** user is in `.worktrees/007-feature/` directory, **When** user runs `tasks_cli.py status` (no argument), **Then** system auto-detects feature and shows status
3. **Given** LLM agent completes a task, **When** agent includes status output in end-of-task report, **Then** human can see current lane distribution

---

### User Story 3 - Migrate Existing Project (Priority: P1)

A user with an existing Spec Kitty project using directory-based lanes wants to upgrade to the new flat structure.

**Why this priority**: Backwards compatibility and migration path is critical for adoption.

**Independent Test**: User runs `spec-kitty upgrade` and all WP files are flattened into `tasks/` with correct `lane:` frontmatter preserved.

**Acceptance Scenarios**:

1. **Given** existing feature with `tasks/planned/WP01.md` and `tasks/doing/WP02.md`, **When** user runs `spec-kitty upgrade`, **Then** files move to `tasks/WP01.md` and `tasks/WP02.md` with `lane:` fields matching their original directories
2. **Given** upgrade script is about to modify files, **When** script starts, **Then** user sees explicit warning explaining what will change and must confirm
3. **Given** project has `.worktrees/` with features, **When** upgrade runs, **Then** all worktrees are also migrated
4. **Given** user declines the warning prompt, **When** they choose not to proceed, **Then** no files are modified

---

### User Story 4 - Detect Legacy Format (Priority: P2)

A user opens a project with old directory-based lanes and the system should suggest upgrading.

**Why this priority**: Ensures users don't get confused when mixing old and new systems.

**Independent Test**: User runs any `tasks_cli.py` command on old-format project and sees suggestion to run upgrade.

**Acceptance Scenarios**:

1. **Given** feature has `tasks/planned/` subdirectory with WP files, **When** user runs `tasks_cli.py list 007-feature`, **Then** output includes warning: "Legacy directory-based lanes detected. Run `spec-kitty upgrade` to migrate."
2. **Given** user has branch with old format, **When** they switch to that branch, **Then** detector identifies old format on next tasks_cli.py command
3. **Given** project is already migrated (flat `tasks/`), **When** user runs any command, **Then** no warning is shown

---

### User Story 5 - Dashboard Shows Lane Status (Priority: P2)

Users viewing the Spec Kitty dashboard see work packages organized by lane, reading from frontmatter.

**Why this priority**: Dashboard is a key visibility tool and must reflect the new data model.

**Independent Test**: Dashboard renders WPs in correct lane columns based on `lane:` frontmatter value.

**Acceptance Scenarios**:

1. **Given** WP04 has `lane: "for_review"` in frontmatter, **When** dashboard renders, **Then** WP04 appears in the "For Review" column
2. **Given** WP lane changes from "doing" to "done", **When** dashboard refreshes, **Then** WP moves to "Done" column without page reload issues

---

### Edge Cases

- What happens when `lane:` field is missing from a WP file? System defaults to "planned" and logs warning.
- What happens when `lane:` field has invalid value? System rejects with clear error message listing valid lanes.
- What happens when old-format and new-format features coexist? Detector warns on old-format features; commands work on both but encourage migration.
- What happens during partial migration (upgrade interrupted)? Upgrade script is idempotent - can be re-run safely.

## Requirements *(mandatory)*

### Functional Requirements

**Core Lane Management:**

- **FR-001**: System MUST determine work package lane solely from the `lane:` YAML frontmatter field
- **FR-002**: System MUST NOT use directory location to infer lane status
- **FR-003**: All WP files MUST reside in a flat `tasks/` directory (no subdirectories by lane)
- **FR-004**: The `tasks_cli.py move` command MUST update only the `lane:` frontmatter field, not move files
- **FR-005**: Direct editing of the `lane:` field MUST be valid and supported

**Status Command:**

- **FR-006**: System MUST provide `tasks_cli.py status [feature]` command showing all WPs grouped by lane
- **FR-007**: The status command MUST auto-detect current feature from worktree/branch when feature argument is omitted
- **FR-008**: Status output MUST be structured and readable for both humans and LLM agents

**Migration:**

- **FR-009**: The `spec-kitty upgrade` command MUST migrate directory-based lanes to flat structure
- **FR-010**: Migration MUST preserve the lane value from the source directory in the `lane:` frontmatter
- **FR-011**: Migration MUST process both main `kitty-specs/` and all `.worktrees/*/kitty-specs/` directories
- **FR-012**: Migration MUST display explicit warning before modifying files and require user confirmation
- **FR-013**: Migration MUST be idempotent (safe to run multiple times)

**Detection:**

- **FR-014**: System MUST detect legacy directory-based lane format (presence of `tasks/planned/`, `tasks/doing/`, etc. subdirectories with WP files)
- **FR-015**: When legacy format is detected, system MUST display suggestion to run `spec-kitty upgrade`
- **FR-016**: Detection MUST NOT block command execution, only warn

**Documentation Updates:**

- **FR-017**: Task prompt templates MUST remove warnings about not editing `lane:` field
- **FR-018**: AGENTS.md MUST be updated to reflect that direct `lane:` editing is the correct approach
- **FR-019**: Template instructions MUST explain the flat `tasks/` structure

### Key Entities

- **Work Package (WP)**: Markdown file with YAML frontmatter containing `lane:` field. Lives in `tasks/` directory.
- **Lane**: One of `planned`, `doing`, `for_review`, `done`. Stored in WP frontmatter, not directory path.
- **Feature**: Directory under `kitty-specs/` containing `tasks/` folder with WP files.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Lane transitions complete without any file move operations (0 file renames/moves per transition)
- **SC-002**: Multiple agents can change lanes on different WPs simultaneously without conflicts
- **SC-003**: `tasks_cli.py status` returns accurate lane grouping within 1 second for features with up to 50 WPs
- **SC-004**: Migration completes successfully for existing projects with up to 100 WP files across all features
- **SC-005**: All existing tests pass after refactoring (or are updated to reflect new behavior)
- **SC-006**: Dashboard correctly displays WPs in their frontmatter-defined lanes
- **SC-007**: Legacy format detection identifies old structure with 100% accuracy

## Assumptions

- Users will run `spec-kitty upgrade` when prompted; the system will not auto-migrate
- The `lane:` field already exists in all WP files (current templates include it)
- Phase subdirectories (`tasks/planned/phase-1-foo/`) will be flattened; phase info preserved only in frontmatter `phase:` field
- Dashboard code has access to read frontmatter from WP files

## Out of Scope

- Automatic migration without user confirmation
- Supporting both directory-based and frontmatter-based lanes simultaneously in the same feature (migration is all-or-nothing per feature)
- Changes to how WP files are created (they will simply be created in `tasks/` instead of `tasks/planned/`)
