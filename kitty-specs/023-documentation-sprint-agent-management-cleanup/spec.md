# Feature Specification: Documentation Sprint: Agent Management and Cleanup

**Feature Branch**: `023-documentation-sprint-agent-management-cleanup`
**Created**: 2026-01-23
**Status**: Draft
**Input**: User description: "a documentation sprint to bring the user docs in line with the actual current implementation. Check the git history for our ./docs - they were mostly written in a sprint a few days ago. Look at git history in the meantime and read our ./architectur adrs. Then find the documentation (eg jujutsu) that must be removed, and the documentation that has to be adjusted based on user facing api changes like the new agent management architecture."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - New User Manages Agents After Init (Priority: P1)

A new user initializes a spec-kitty project with a single agent (e.g., `opencode`), but later wants to add additional agents (e.g., `claude`, `codex`) to enable multi-agent workflows. They need clear documentation on how to add agents post-init without manually editing configuration files.

**Why this priority**: Core user workflow - agent selection is fundamental to spec-kitty usage, and post-init changes are common. Without clear docs, users resort to manual config editing or repo recreation.

**Independent Test**: Can be fully tested by following the new how-to guide to add/remove agents and verifying filesystem and config.yaml match expectations.

**Acceptance Scenarios**:

1. **Given** a project initialized with only `opencode`, **When** user runs `spec-kitty agent config add claude codex`, **Then** `.claude/commands/` and `.codex/prompts/` directories are created with slash command templates, and `.kittify/config.yaml` lists `[opencode, claude, codex]` under `agents.available`
2. **Given** user wants to see available agents, **When** they run `spec-kitty agent config list`, **Then** they see configured agents with status indicators (✓ = present, ⚠ = configured but missing) and a list of available-but-not-configured agents
3. **Given** user no longer uses `gemini`, **When** they run `spec-kitty agent config remove gemini`, **Then** `.gemini/` directory is deleted and `gemini` is removed from config.yaml

---

### User Story 2 - Existing User Upgrades to 0.12.0 Config-Driven Model (Priority: P1)

An existing spec-kitty 0.11.x user upgrades to 0.12.0 and encounters new config-driven agent management behavior. They previously deleted unwanted agent directories, but migrations recreated them. They need migration documentation explaining the new model and how to prevent directory recreation.

**Why this priority**: Breaking change affecting all 0.11.x users. Without migration guide, users will be confused by behavior changes and may lose trust in upgrade process.

**Independent Test**: Can be tested by simulating 0.11.x → 0.12.0 upgrade with deleted agent directories, following migration guide, and verifying migrations respect config.yaml.

**Acceptance Scenarios**:

1. **Given** user upgraded from 0.11.x with manually deleted agent directories, **When** they read migration guide section "Why Migrations Respect config.yaml", **Then** they understand `.kittify/config.yaml` is now the single source of truth
2. **Given** user wants to prevent directory recreation, **When** they follow migration guide steps to use `spec-kitty agent config remove`, **Then** unwanted agents stay deleted across future upgrades
3. **Given** user has orphaned directories (present but not configured), **When** they run `spec-kitty agent config status`, **Then** orphaned agents are clearly identified with actionable remediation command

---

### User Story 3 - Developer References Agent Config Commands (Priority: P2)

A developer integrating spec-kitty into their CI/CD pipeline needs precise command syntax, flags, and behavior for agent config commands. They need reference documentation with all command options, default behaviors, and examples.

**Why this priority**: Important for automation and scripting, but less urgent than core user workflows. Most users interact via CLI directly, not scripts.

**Independent Test**: Can be tested by verifying all commands, flags, and examples in reference docs match actual CLI help output and implementation.

**Acceptance Scenarios**:

1. **Given** developer needs to automate agent setup, **When** they consult CLI commands reference, **Then** they find complete documentation for `spec-kitty agent config` with all subcommands (list/add/remove/status/sync)
2. **Given** developer wants non-interactive sync, **When** they check `sync` command documentation, **Then** they see flags like `--create-missing` and `--remove-orphaned` with default behaviors clearly stated
3. **Given** developer encounters an error, **When** they check command documentation, **Then** they find error handling behavior (e.g., invalid agent keys show list of valid agents)

---

### User Story 4 - User Audits Agent Sync Status (Priority: P3)

A user suspects their agent configuration is out of sync (directories present that shouldn't be, or vice versa). They need documentation on how to audit and repair sync issues without manually inspecting filesystem and config.yaml.

**Why this priority**: Edge case for troubleshooting. Most users won't encounter sync issues, but when they do, clear docs prevent frustration.

**Independent Test**: Can be tested by creating intentional sync mismatches (orphaned dirs, missing dirs) and using documented commands to detect and fix them.

**Acceptance Scenarios**:

1. **Given** user has orphaned agent directories (present but not configured), **When** they run `spec-kitty agent config status`, **Then** they see a table showing all agents with "Configured", "Exists", and "Status" columns, with orphaned agents marked as "[red]Orphaned[/red]"
2. **Given** user wants to sync filesystem with config, **When** they run `spec-kitty agent config sync`, **Then** orphaned directories are removed by default (with option to keep via `--keep-orphaned`)
3. **Given** user wants to restore missing configured agents, **When** they run `spec-kitty agent config sync --create-missing`, **Then** missing directories are created with slash command templates

---

### User Story 5 - Opportunistic Documentation Cleanup (Priority: P3)

A user browsing documentation encounters outdated content unrelated to agent management (e.g., incorrect command syntax, references to removed features). They expect documentation to accurately reflect current implementation without obvious errors.

**Why this priority**: Quality-of-life improvement. Not blocking core workflows, but builds user trust in documentation accuracy.

**Independent Test**: Can be tested by code-first validation - cross-referencing all documented commands/features against source code and flagging discrepancies.

**Acceptance Scenarios**:

1. **Given** user reads a how-to guide, **When** they follow documented command syntax, **Then** commands execute successfully without "command not found" or "invalid flag" errors
2. **Given** user reads reference documentation, **When** they check command help output, **Then** documented flags and options match actual `--help` text
3. **Given** user encounters broken internal links, **When** they click documentation cross-references, **Then** all links resolve to existing pages

---

### Edge Cases

- **User adds agent with typo** (e.g., `spec-kitty agent config add cluade`): Command validates against `AGENT_DIR_TO_KEY` values and shows error with list of valid agents
- **User removes agent that doesn't exist**: Command prints dim message "already removed" and continues without error
- **Orphaned directory deletion fails** (permissions issue): `sync` command reports error but continues processing other agents
- **Config.yaml missing or corrupt**: Falls back to all 12 agents (legacy behavior) and warns user
- **User has multiple jj references in docs** (already removed): Audit finds zero jj references, confirms cleanup complete

## Requirements *(mandatory)*

### Functional Requirements

#### Agent Management Documentation

- **FR-001**: Documentation MUST include a new how-to guide `docs/how-to/manage-agents.md` explaining post-init agent management with `spec-kitty agent config` commands
- **FR-002**: How-to guide MUST cover all five subcommands: `list`, `add`, `remove`, `status`, `sync` with examples for each
- **FR-003**: How-to guide MUST explain config-driven model (`.kittify/config.yaml` as single source of truth)
- **FR-004**: Documentation MUST include a migration guide section for 0.11.x → 0.12.0 users explaining why migrations now respect config.yaml
- **FR-005**: Migration guide MUST provide step-by-step instructions for users who previously manually deleted agent directories

#### CLI Reference Updates

- **FR-006**: `docs/reference/cli-commands.md` MUST document `spec-kitty agent config` command group with all subcommands
- **FR-007**: Each subcommand entry MUST include: synopsis, description, arguments (if any), options/flags with defaults, and examples
- **FR-008**: Documentation MUST cross-reference agent config commands from relevant pages (init, configuration, supported-agents)
- **FR-009**: `docs/reference/agent-subcommands.md` MUST list `spec-kitty agent config` in the command index

#### Jujutsu Cleanup

- **FR-010**: Documentation MUST NOT contain references to jujutsu/jj VCS (removed in commit 99b0d84)
- **FR-011**: Documentation MUST NOT contain broken links to removed jj files (auto-rebase-and-conflicts.md, jujutsu-for-multi-agent.md, handle-conflicts-jj.md, use-operation-history.md, jujutsu-workflow.md)
- **FR-012**: VCS detection order documentation MUST reflect git-only behavior (remove jj priority mentions)

#### Opportunistic Updates

- **FR-013**: All documented command syntax MUST match actual CLI help output (validated via code inspection)
- **FR-014**: All documented configuration options MUST match `.kittify/config.yaml` schema (validated against AgentConfig dataclass)
- **FR-015**: All internal documentation links MUST resolve to existing files (no 404s)

#### Code-First Validation

- **FR-016**: All agent config command documentation MUST be validated against `src/specify_cli/cli/commands/agent/config.py` implementation
- **FR-017**: Agent key mappings (e.g., `copilot` → `.github`, `auggie` → `.augment`) MUST be documented based on `AGENT_DIR_TO_KEY` constant
- **FR-018**: Config schema documentation MUST match `AgentConfig` and `AgentSelectionConfig` dataclasses in `src/specify_cli/orchestrator/agent_config.py`
- **FR-019**: Migration behavior documentation MUST reference ADR #6 (Config-Driven Agent Management) for architectural context

### Key Entities

- **AgentConfig**: Configuration object storing list of available agent keys and selection strategy
  - `available`: List of agent keys (e.g., `["claude", "codex", "opencode"]`)
  - `selection`: Nested object with `strategy`, `preferred_implementer`, `preferred_reviewer`

- **Agent Directory Mapping**: Key-to-filesystem mapping for 12 supported agents
  - Special cases: `copilot` → `.github/prompts`, `auggie` → `.augment/commands`, `q` → `.amazonq/prompts`
  - Standard: agent key matches directory name (e.g., `claude` → `.claude/commands`)

- **Orphaned Directory**: Agent directory present on filesystem but not listed in `config.yaml.agents.available`

- **Mission Templates**: Markdown files in `.kittify/missions/software-dev/command-templates/` copied to agent directories with `spec-kitty.` prefix

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: New users can successfully add/remove agents without consulting support or source code (90% success rate based on command discoverability)
- **SC-002**: Existing 0.11.x users upgrading to 0.12.0 understand config-driven behavior within 5 minutes of reading migration guide
- **SC-003**: Zero broken links in documentation after cleanup (validated via link checker)
- **SC-004**: 100% of agent config command syntax in documentation matches actual CLI implementation (validated via code inspection)
- **SC-005**: Zero references to jujutsu/jj remain in user-facing documentation (validated via grep)
- **SC-006**: Agent config commands are discoverable via CLI help and referenced from at least 3 related documentation pages

## Assumptions *(optional)*

- Users upgrading from 0.11.x have already merged or deleted in-progress features (per upgrade prerequisites)
- Agent directory structure (`.claude/commands/`, `.github/prompts/`, etc.) remains stable in 0.12.x
- Mission templates in `.kittify/missions/software-dev/command-templates/` are present for all supported agents
- ADR #6 (Config-Driven Agent Management) accurately documents current implementation
- Commit 99b0d84 represents complete jujutsu removal (no partial cleanup needed)

## Out of Scope *(optional)*

- Creating new documentation for features added after Jan 23, 2026 (future work)
- Comprehensive rewrite of all documentation (only opportunistic fixes)
- Adding documentation for orchestrator agent selection strategies (separate feature)
- Documenting internal migration code (migrations/m_*.py) - out of scope for user docs
- Creating video tutorials or interactive guides (text-only documentation)
- Translating documentation to other languages

## Dependencies *(optional)*

- ADR #6 (Config-Driven Agent Management) must remain accurate reference
- Agent config CLI implementation in `src/specify_cli/cli/commands/agent/config.py` must be stable (no breaking changes during documentation work)
- Mission template structure in `.kittify/missions/` must match expectations for `agent config add` command
- Git history for commits 99b0d84 (jj removal) and b74536b (agent config) must be accessible for validation

## Notes *(optional)*

### Implementation Context

This feature addresses **technical debt** from recent architectural changes:

1. **ADR #6 (Jan 23)**: Introduced config-driven agent management with new CLI commands, but documentation was minimal
2. **Commit 99b0d84 (Jan 23)**: Removed jujutsu support and 5 jj documentation files, but may have left stale references
3. **Documentation sprint (Jan 20-23)**: Major DocFX overhaul focused on merge/preflight docs, but agent management was incomplete

### Validation Strategy

Code-first validation means:

- No manual command testing - rely on source code inspection
- Cross-reference all docs against implementation files
- Use grep/ast parsing to validate command signatures
- Check `AGENT_DIR_TO_KEY` constant for accurate agent mappings
- Verify config schema against dataclass definitions

### Related Documentation

- `architecture/adrs/2026-01-23-6-config-driven-agent-management.md`: Architectural decision record
- `CLAUDE.md`: Project instructions documenting agent management best practices for developers
- `docs/reference/supported-agents.md`: List of 12 supported agents with their directory mappings
- `src/specify_cli/upgrade/migrations/m_0_9_1_complete_lane_migration.py`: Canonical source for `AGENT_DIRS` and `AGENT_DIR_TO_KEY`
