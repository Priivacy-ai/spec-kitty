# Feature Specification: Unified Python CLI for Agents
*Path: [kitty-specs/008-unified-python-cli/spec.md](kitty-specs/008-unified-python-cli/spec.md)*

**Feature Branch**: `008-unified-python-cli`
**Created**: 2025-12-17
**Status**: Draft
**Input**: User description: "Migrate all bash scripts to a unified Python CLI under spec-kitty agent namespace, eliminating worktree script copying and providing agents with a reliable, location-aware command interface"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - AI Agent Executes Workflow Without Path Errors (Priority: P1)

AI agents using spec-kitty slash commands (like `/spec-kitty.implement`, `/spec-kitty.review`) can execute workflows successfully regardless of their current location (main repository or worktree), without encountering path resolution errors or needing to locate bash scripts.

**Why this priority**: This is the core problem being solved. Agents currently struggle with bash scripts, path confusion, and script copying. Until this works reliably, agents cannot effectively use spec-kitty.

**Independent Test**: Can be fully tested by having an AI agent execute any spec-kitty slash command from both main repository and worktree locations, verifying zero path-related errors occur.

**Acceptance Scenarios**:

1. **Given** an AI agent is working in the main repository, **When** it executes `/spec-kitty.implement` (which calls `spec-kitty agent move-task`), **Then** the command succeeds and correctly resolves paths without requiring the agent to specify location context
2. **Given** an AI agent is working in a worktree (`.worktrees/feature-name/`), **When** it executes any `spec-kitty agent` command, **Then** the CLI automatically detects the worktree location and resolves all paths correctly
3. **Given** an AI agent needs to move a task between lanes, **When** it calls `spec-kitty agent move-task WP01 --to doing`, **Then** the task file is moved correctly regardless of whether the agent is in main repo or worktree
4. **Given** bash scripts previously needed to be copied to worktrees, **When** the Python CLI is installed, **Then** no script copying occurs and agents can immediately use `spec-kitty agent` commands

---

### User Story 2 - Existing Projects Upgrade Automatically (Priority: P2)

Users with existing spec-kitty projects (that currently use bash scripts and old slash command templates) can run `spec-kitty upgrade` to automatically migrate their projects to use the new `spec-kitty agent` command interface without manual intervention.

**Why this priority**: Without automatic upgrade, existing users would need to manually update slash commands, delete bash scripts, and reconfigure their projects. This is error-prone and creates adoption friction.

**Independent Test**: Can be tested by creating a spec-kitty project with the old bash-based structure, running `spec-kitty upgrade`, and verifying all slash commands now use `spec-kitty agent` commands and bash scripts are removed.

**Acceptance Scenarios**:

1. **Given** a spec-kitty project using bash scripts in `.kittify/scripts/bash/`, **When** user runs `spec-kitty upgrade`, **Then** all bash scripts are removed and slash command templates are updated to call `spec-kitty agent` commands
2. **Given** a project has custom slash commands referencing bash scripts, **When** upgrade runs, **Then** the migration detects these references and either updates them automatically or warns the user about manual updates needed
3. **Given** a project is in a worktree with copied bash scripts, **When** upgrade runs, **Then** the copied scripts are removed and the worktree is cleaned up
4. **Given** the upgrade migration completes, **When** an AI agent executes any slash command, **Then** the command works correctly with the new Python CLI

---

### User Story 3 - Developers Can Test Agent Workflows (Priority: P3)

Developers contributing to spec-kitty can run unit tests and integration tests for all `spec-kitty agent` commands, ensuring agent workflows are reliable and regression-free.

**Why this priority**: Currently bash scripts are difficult to test, making it hard to catch regressions. While important for quality, this is lower priority than solving the immediate agent pain points.

**Independent Test**: Can be tested by running the test suite (`pytest`) and verifying all agent commands have test coverage showing they work from various locations.

**Acceptance Scenarios**:

1. **Given** a developer modifies path resolution logic, **When** they run unit tests, **Then** tests verify the logic works correctly from main repo, worktrees, and edge cases
2. **Given** a developer adds a new agent command, **When** they run integration tests, **Then** tests verify the command works with JSON output mode and from all locations
3. **Given** a contributor wants to ensure cross-platform compatibility, **When** tests run on CI/CD, **Then** tests pass on Windows, macOS, and Linux

---

### User Story 4 - Research Validates Migration Approach (Priority: P0)

Before implementation begins, a research phase validates that the proposed migration approach (unified CLI, path resolution strategy, upgrade mechanism) is feasible and identifies any risks or alternative approaches.

**Why this priority**: P0 (prerequisite) because we must validate the approach before committing to implementation. The detailed plan provided needs validation against the actual codebase.

**Independent Test**: Can be tested by reviewing research findings document that answers key validation questions and provides go/no-go recommendation.

**Acceptance Scenarios**:

1. **Given** the proposed plan suggests eliminating all bash scripts, **When** research is conducted, **Then** findings confirm all bash functionality can be migrated to Python or identify exceptions
2. **Given** the plan proposes a specific path resolution strategy, **When** research validates it, **Then** findings confirm it handles all edge cases (symlinks, broken worktrees, Windows) or suggest alternatives
3. **Given** the upgrade migration approach is proposed, **When** research validates it, **Then** findings confirm the migration can safely update existing projects or identify migration risks
4. **Given** research identifies risks or blockers, **When** findings are documented, **Then** alternative approaches or mitigation strategies are provided

---

### Edge Cases

- What happens when an agent executes a command from a broken/incomplete worktree (e.g., symlinks broken)?
- How does the system handle Windows environments where symlinks may not be supported?
- What happens if an agent tries to use `spec-kitty agent` commands in a non-spec-kitty repository?
- How does the upgrade migration handle projects with custom modifications to bash scripts?
- What happens if an agent is in a deeply nested directory within a worktree?
- How does the system behave if `.kittify/` directory is missing or corrupted?
- What happens during upgrade if the project has uncommitted changes or is in a dirty git state?

## Requirements *(mandatory)*

### Functional Requirements

**Research & Validation**:
- **FR-001**: System MUST conduct research phase to validate proposed migration approach before implementation
- **FR-002**: Research MUST validate that all bash script functionality can be migrated to Python or identify exceptions
- **FR-003**: Research MUST validate proposed path resolution strategy handles all edge cases (worktrees, symlinks, Windows) or suggest alternatives
- **FR-004**: Research MUST validate upgrade migration approach can safely update existing projects

**Unified CLI Implementation**:
- **FR-005**: System MUST provide a `spec-kitty agent` command namespace for all agent-facing operations
- **FR-006**: All agent commands MUST support `--json` output mode for agent parsing
- **FR-007**: System MUST automatically detect whether execution is in main repository or worktree
- **FR-008**: System MUST resolve all file paths correctly regardless of execution location
- **FR-009**: Agent commands MUST work identically on Windows, macOS, and Linux
- **FR-010**: System MUST eliminate all bash scripts in `.kittify/scripts/bash/` (approximately 2,600+ lines)
- **FR-011**: System MUST eliminate all bash scripts in `.github/workflows/scripts/`

**Path Resolution**:
- **FR-012**: System MUST walk up directory tree to find repository root (via `.kittify/` marker or git)
- **FR-013**: System MUST detect worktree locations and resolve paths accordingly
- **FR-014**: System MUST handle symlinks correctly (including broken symlinks)
- **FR-015**: System MUST fall back to file copying on Windows when symlinks are not supported

**Upgrade Migration**:
- **FR-016**: System MUST provide `spec-kitty upgrade` migration that updates existing projects to new CLI
- **FR-017**: Upgrade MUST remove all bash scripts from `.kittify/scripts/bash/` in existing projects
- **FR-018**: Upgrade MUST update slash command templates (`.claude/commands/*.md`) to use `spec-kitty agent` commands
- **FR-019**: Upgrade MUST clean up copied bash scripts from all worktrees
- **FR-020**: Upgrade MUST detect and warn about custom modifications to bash scripts that cannot be auto-migrated
- **FR-021**: Upgrade MUST be idempotent (safe to run multiple times)

**Agent Command Coverage**:
- **FR-022**: System MUST provide agent commands for feature management (`create-feature`, `check-prerequisites`, `setup-plan`)
- **FR-023**: System MUST provide agent commands for task workflow (`move-task`, `mark-status`, `validate-workflow`)
- **FR-024**: System MUST provide agent commands for context management (`update-context`)
- **FR-025**: System MUST provide agent commands for release packaging (`build-release`)

**Testing & Quality**:
- **FR-026**: All agent commands MUST have unit test coverage
- **FR-027**: All agent commands MUST have integration tests verifying they work from various locations
- **FR-028**: System MUST validate all slash commands work with new CLI before release

### Key Entities *(include if feature involves data)*

- **Agent Command**: A Python CLI command under `spec-kitty agent` namespace, designed for AI agents to call programmatically with JSON output support
- **Worktree**: A git worktree directory (`.worktrees/feature-name/`) where agents may execute commands, requiring automatic path resolution
- **Slash Command Template**: Markdown files in `.claude/commands/` that define agent workflows, which reference agent commands
- **Upgrade Migration**: A migration script in `spec-kitty upgrade` that transforms existing projects from bash-based to Python CLI-based architecture
- **Path Resolver**: Component that detects execution location (main repo vs worktree) and resolves file paths correctly

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: AI agents complete all spec-kitty workflows (specify, plan, tasks, implement, review, accept, merge) without path-related errors (0% error rate)
- **SC-002**: Agent commands work identically whether executed from main repository or any worktree location
- **SC-003**: All bash scripts in `.kittify/scripts/bash/` and `.github/workflows/scripts/` are eliminated (approximately 2,600+ lines removed)
- **SC-004**: 100% of existing spec-kitty projects can successfully upgrade via `spec-kitty upgrade` without manual intervention (or with clear warnings for edge cases)
- **SC-005**: Agent retry behavior due to path issues is reduced by 95% or more (measurable via agent error logs)
- **SC-006**: Research phase produces documented findings with go/no-go recommendation and validated approach
- **SC-007**: All agent commands have unit and integration test coverage (90%+ code coverage for agent namespace)
- **SC-008**: Cross-platform compatibility verified on Windows, macOS, and Linux (CI/CD tests pass on all platforms)

## Assumptions *(optional)*

- Existing spec-kitty codebase already uses Python 3.11+ and Typer for CLI framework
- Existing `spec-kitty upgrade` infrastructure can be extended for this migration
- AI agents can parse JSON output from commands
- Most existing projects have not heavily customized bash scripts (custom modifications will require manual migration)
- Git worktrees follow standard structure (`.worktrees/feature-name/`)
- The detailed migration plan provided (7 phases, 11 days) is a starting point subject to validation during research phase

## Out of Scope *(optional)*

- Migrating git hooks (e.g., `pre-commit-task-workflow.sh`) to Python in this phase
- Providing backward compatibility for bash scripts (clean cut migration)
- Supporting non-standard worktree structures
- Migrating non-spec-kitty bash scripts in user codebases
- Creating a daemon mode for long-running agent sessions (future enhancement)

## Dependencies *(optional)*

- Python 3.11+ runtime environment
- Existing spec-kitty codebase (`src/specify_cli/`)
- Git for worktree detection
- Typer CLI framework
- pathlib, Rich, subprocess (existing dependencies)

## Risks & Mitigations *(optional)*

**Risk**: Custom bash script modifications in existing projects cannot be auto-migrated
**Mitigation**: Upgrade migration detects custom modifications and provides clear warnings with migration guide

**Risk**: Windows symlink limitations may cause issues
**Mitigation**: Fall back to file copying on Windows (already implemented pattern in codebase)

**Risk**: Research phase may invalidate proposed approach
**Mitigation**: Research phase is P0 (prerequisite) - implementation only proceeds after validation

**Risk**: Breaking changes during migration period may disrupt active users
**Mitigation**: Clear upgrade documentation, release notes, and automated migration via `spec-kitty upgrade`

**Risk**: Path resolution edge cases (broken symlinks, nested worktrees) may not be fully handled
**Mitigation**: Comprehensive testing of edge cases and graceful error messages when edge cases cannot be handled
