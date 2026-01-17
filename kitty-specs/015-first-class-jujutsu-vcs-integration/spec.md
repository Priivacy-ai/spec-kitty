# Feature Specification: First-Class Jujutsu VCS Integration

**Feature Branch**: `015-first-class-jujutsu-vcs-integration`
**Created**: 2026-01-17
**Status**: Draft
**Input**: Make jujutsu (jj) an equal first-class citizen to git, with jj preferred when available

## Overview

Spec-kitty currently relies exclusively on git for version control operations (worktrees, branches, commits). This feature introduces jujutsu (jj) as a first-class alternative that is preferred when available, while maintaining full git compatibility as a fallback.

**Key Value Proposition**: jj's auto-rebase and conflict-as-data capabilities eliminate the manual coordination overhead when multiple agents work on dependent work packages, enabling true parallel autonomous development.

**DEFERRED TO FUTURE FEATURE**: Dashboard integration with conflict indicators (visual workspace state: clean/stale/conflicted). This spec covers CLI and core functionality only.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Automatic VCS Detection and Selection (Priority: P1)

A developer runs `spec-kitty init` in a new project. The system detects whether jj is installed and available. If jj is available, it becomes the default VCS for new features. The developer sees an informational message about the VCS selection and, if jj is not installed, a recommendation to install it for better multi-agent performance.

**Why this priority**: This is the entry point for all spec-kitty usage. Without proper detection and selection, no other jj features can work.

**Independent Test**: Can be fully tested by running `spec-kitty init` with and without jj installed, verifying correct detection and messaging.

**Acceptance Scenarios**:

1. **Given** jj is installed and in PATH, **When** developer runs `spec-kitty init`, **Then** system selects jj as default VCS and displays confirmation message
2. **Given** jj is NOT installed but git is, **When** developer runs `spec-kitty init`, **Then** system selects git as default and displays info message recommending jj installation
3. **Given** neither jj nor git is installed, **When** developer runs `spec-kitty init`, **Then** system displays error with installation instructions for both tools
4. **Given** jj is installed, **When** developer runs `spec-kitty init --vcs=git`, **Then** system uses git despite jj availability

---

### User Story 2 - Per-Feature VCS Selection (Priority: P1)

A developer creates a new feature with `/spec-kitty.specify`. The VCS choice is recorded in the feature's metadata and locked for the duration of that feature. Different features in the same project can use different VCS backends.

**Why this priority**: Per-feature VCS selection enables gradual adoption and mixed workflows without forcing migration of in-progress work.

**Independent Test**: Create two features, one with git and one with jj, verify each uses its designated VCS for workspace operations.

**Acceptance Scenarios**:

1. **Given** project default is jj, **When** developer creates new feature, **Then** feature's meta.json records `"vcs": "jj"`
2. **Given** feature was created with jj, **When** developer runs `spec-kitty implement WP01`, **Then** system creates jj workspace (not git worktree)
3. **Given** feature A uses git and feature B uses jj, **When** developer works on both, **Then** each feature uses its designated VCS without interference
4. **Given** feature was created with jj, **When** developer attempts to change VCS mid-feature, **Then** system rejects the change with explanation

---

### User Story 3 - Workspace Creation with Jujutsu (Priority: P2)

A developer implements a work package using jj. The system creates a jj workspace instead of a git worktree, enabling jj-specific features like auto-rebase and conflict storage.

**Why this priority**: Workspace creation is the foundation for all implementation work. Must work correctly before auto-rebase benefits can be realized.

**Independent Test**: Run `spec-kitty implement WP01` on a jj-enabled feature, verify jj workspace is created with correct structure.

**Acceptance Scenarios**:

1. **Given** feature uses jj, **When** developer runs `spec-kitty implement WP01`, **Then** system creates `.worktrees/###-feature-WP01/` using `jj workspace add`
2. **Given** feature uses jj with git colocated, **When** workspace is created, **Then** both `.jj/` and `.git/` directories exist in workspace
3. **Given** feature uses jj, **When** developer runs `spec-kitty implement WP02 --base WP01`, **Then** WP02 workspace is created with WP01's changes visible
4. **Given** workspace was created with jj, **When** developer makes file changes, **Then** changes are automatically part of the working-copy commit (no staging required)

---

### User Story 4 - Automatic Rebase of Dependent Workspaces (Priority: P2)

Agent A is working on WP01, Agent B is working on WP02 (which depends on WP01). When Agent A commits changes to WP01, Agent B's workspace automatically sees those changes after syncing, without manual rebase commands.

**Why this priority**: This is the primary productivity benefit of jj - eliminating manual coordination between agents working on dependent work packages.

**Independent Test**: Modify WP01 in one workspace, verify WP02 workspace can sync and see changes without manual rebase.

**Acceptance Scenarios**:

1. **Given** WP02 depends on WP01 and both use jj, **When** WP01 commits changes, **Then** jj records that WP02 needs rebase (auto-rebase queued)
2. **Given** WP02 workspace is stale (WP01 changed), **When** developer runs `spec-kitty sync` in WP02, **Then** workspace files update to include WP01's changes
3. **Given** WP01, WP02, WP03 form a dependency chain, **When** WP01 changes, **Then** both WP02 and WP03 can sync to get updates (chain propagation)
4. **Given** auto-rebase produces conflicts, **When** sync completes, **Then** conflicts are stored in workspace files (operation succeeds, not blocked)

---

### User Story 5 - Non-Blocking Conflict Handling (Priority: P2)

Agent B is working on WP02 when WP01 changes cause a conflict. Instead of blocking the rebase operation, the conflict is stored in the affected files. Agent B can continue working on non-conflicting files and resolve conflicts when convenient.

**Why this priority**: Non-blocking conflicts are what enable true parallel autonomous development - agents don't get stuck waiting for conflict resolution.

**Independent Test**: Create a conflict scenario, verify rebase succeeds with conflict stored, verify agent can continue working.

**Acceptance Scenarios**:

1. **Given** rebase causes conflict in file X, **When** sync completes, **Then** file X contains conflict markers but operation succeeds
2. **Given** workspace has stored conflicts, **When** developer edits non-conflicting files, **Then** work proceeds normally
3. **Given** workspace has stored conflicts, **When** developer runs `/spec-kitty.review`, **Then** system blocks review until conflicts resolved
4. **Given** developer resolves conflicts in file X, **When** file is saved, **Then** jj automatically records resolution (no explicit commit needed)
5. **Given** WP02 resolved conflicts, **When** dependent WP03 syncs, **Then** WP03 receives the resolution (conflict doesn't re-propagate)

---

### User Story 6 - Sync Command for Workspace Updates (Priority: P2)

A developer or agent needs to update their workspace to include upstream changes. The `spec-kitty sync` command handles this for both jj and git backends, abstracting the underlying complexity.

**Why this priority**: Provides unified interface regardless of VCS, essential for agent automation.

**Independent Test**: Run `spec-kitty sync` in stale workspace, verify files update correctly.

**Acceptance Scenarios**:

1. **Given** jj workspace is stale, **When** developer runs `spec-kitty sync`, **Then** system runs `jj workspace update-stale` and reports status
2. **Given** git workspace needs rebase, **When** developer runs `spec-kitty sync`, **Then** system runs appropriate git rebase and reports status
3. **Given** workspace is already up to date, **When** developer runs `spec-kitty sync`, **Then** system reports "already up to date"
4. **Given** sync results in conflicts, **When** command completes, **Then** output lists conflicted files and their line ranges

---

### User Story 7 - Operation Log and Undo (Priority: P3)

A developer makes a mistake and needs to undo recent operations. With jj, the operation log provides complete history of all repository changes, enabling precise undo.

**Why this priority**: Safety net for mistakes, but not on critical path for basic multi-agent workflows.

**Independent Test**: Make several operations, verify operation log shows history, verify undo restores previous state.

**Acceptance Scenarios**:

1. **Given** feature uses jj, **When** developer runs `spec-kitty ops log`, **Then** system displays jj operation history
2. **Given** developer made a mistake, **When** developer runs `spec-kitty ops undo`, **Then** most recent operation is reversed
3. **Given** feature uses git, **When** developer runs `spec-kitty ops log`, **Then** system displays equivalent git reflog information
4. **Given** undo was performed, **When** developer checks workspace state, **Then** files reflect pre-operation state

---

### User Story 8 - Stable Change Identity (Priority: P3)

Work packages maintain stable identity across rebases. When WP02 is rebased multiple times due to WP01 changes, its Change ID remains constant even though commit hashes change.

**Why this priority**: Enables reliable tracking and cross-referencing of work packages across the development lifecycle.

**Independent Test**: Rebase a workspace multiple times, verify Change ID remains constant.

**Acceptance Scenarios**:

1. **Given** WP is created with jj, **When** WP is rebased, **Then** Change ID in metadata remains the same
2. **Given** WP has been rebased 5 times, **When** querying by Change ID, **Then** system finds the current state
3. **Given** git backend is used, **When** tracking identity, **Then** system falls back to branch name (git has no Change ID equivalent)

---

### User Story 9 - Colocated Repository Mode (Priority: P3)

A project uses jj but needs git compatibility for CI/CD, GitHub integration, or team members who haven't adopted jj. Colocated mode maintains both `.jj/` and `.git/` directories.

**Why this priority**: Enables gradual adoption without breaking existing tooling.

**Independent Test**: Create colocated repo, verify both jj and git commands work, verify changes sync between them.

**Acceptance Scenarios**:

1. **Given** project has both jj and git installed, **When** feature is created, **Then** workspace has both `.jj/` and `.git/` directories
2. **Given** colocated workspace, **When** changes made via jj, **Then** git log shows same commits
3. **Given** colocated workspace, **When** changes made via git, **Then** jj log shows same commits after next jj command
4. **Given** jj installed but git NOT installed, **When** feature is created, **Then** workspace has only `.jj/` (pure jj mode)

---

### Edge Cases

- **What happens when jj is installed but broken?** System falls back to git with warning message
- **What happens when workspace becomes corrupted?** `spec-kitty sync --repair` attempts recovery using jj operation log
- **How does system handle very long dependency chains (10+ WPs)?** Same as shorter chains - auto-rebase propagates through entire chain
- **What happens during network issues with remote sync?** Local operations continue; remote sync retried with exponential backoff
- **How are merge conflicts with 3+ parents handled?** jj supports multi-sided conflicts; spec-kitty surfaces all sides to developer
- **What happens if jj is uninstalled mid-feature?** System detects missing tool, provides recovery instructions (reinstall jj or manually convert to git)

## Requirements *(mandatory)*

### Functional Requirements

#### VCS Abstraction Layer
- **FR-001**: System MUST provide a VCS abstraction layer with implementations for both git and jujutsu
- **FR-002**: System MUST detect available VCS tools at runtime (check PATH for `jj` and `git`)
- **FR-003**: System MUST prefer jj when available, falling back to git otherwise
- **FR-004**: System MUST allow explicit VCS override via `--vcs=git` or `--vcs=jj` flags

#### Project and Feature Configuration
- **FR-005**: System MUST store project-level VCS preference in `.kittify/config.yaml`
- **FR-006**: System MUST store per-feature VCS selection in feature's `meta.json`
- **FR-007**: System MUST lock VCS selection at feature creation (cannot change mid-feature)
- **FR-008**: System MUST display informational message during `init` recommending jj installation if not present

#### Workspace Management
- **FR-009**: System MUST create workspaces using `jj workspace add` when feature uses jj
- **FR-010**: System MUST create workspaces using `git worktree add` when feature uses git
- **FR-011**: System MUST support `--base` flag for dependent workspaces in both VCS backends
- **FR-012**: System MUST use colocated mode (both .jj/ and .git/) when both tools are available

#### Synchronization
- **FR-013**: System MUST provide `spec-kitty sync` command that works for both VCS backends
- **FR-014**: System MUST detect stale workspaces and prompt for sync
- **FR-015**: System MUST report conflicts after sync with file paths and line ranges

#### Conflict Handling
- **FR-016**: System MUST allow jj operations to complete even when conflicts exist (non-blocking)
- **FR-017**: System MUST block review command when workspace has unresolved conflicts
- **FR-018**: System MUST block merge command when any WP has unresolved conflicts
- **FR-019**: System MUST display clear conflict status in `spec-kitty status` output

#### Operation History
- **FR-020**: System MUST provide `spec-kitty ops log` to display operation history
- **FR-021**: System MUST provide `spec-kitty ops undo` to reverse recent operations
- **FR-022**: System MUST use jj operation log for jj features, git reflog for git features

#### Testing Requirements
- **FR-023**: System MUST have jj-specific tests that require jj to be installed (skip if unavailable)
- **FR-024**: System MUST NOT mock jj behavior in tests - real jj execution required

### Key Entities

- **VCS**: Abstract version control system interface with `GitVCS` and `JujutsuVCS` implementations
- **Workspace**: An isolated working directory for a specific work package (jj workspace or git worktree)
- **Change**: In jj, a mutable commit with stable Change ID; in git, approximated by branch name
- **Conflict**: In jj, stored data within a commit; in git, blocking state requiring resolution
- **Operation**: In jj, a recorded repository mutation with undo capability; in git, approximated by reflog entry

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Developers can complete a 5-WP feature with dependency chain without any manual rebase commands (when using jj)
- **SC-002**: Time spent on rebase/merge coordination reduced by 80% compared to git-only workflow (measured by eliminated manual rebase commands)
- **SC-003**: 100% of spec-kitty commands work identically whether project uses jj or git (same user experience)
- **SC-004**: Multiple agents can work on dependent WPs simultaneously without blocking each other (parallel development enabled)
- **SC-005**: Conflicts from upstream changes do not block downstream agent work (can continue on non-conflicting files)
- **SC-006**: All repository state changes can be undone within a session (operation log coverage)
- **SC-007**: Existing git-only users experience zero breaking changes (full backward compatibility)

## Assumptions

- jj is stable enough for production use (version 0.20+ recommended)
- Developers have basic familiarity with version control concepts
- CI/CD systems can work with colocated repos (git side visible to standard git tooling)
- Network connectivity is generally available for remote sync operations
