# Feature Specification: Hybrid Prompt and Shim Agent Surface

**Feature Branch**: `058-hybrid-prompt-and-shim-agent-surface`
**Created**: 2026-03-30
**Status**: Draft
**Input**: Complete the 057 thin-shim architecture by restoring full prompts for planning commands while keeping thin shims for execution commands.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Agent Runs Specify in a Fresh Consumer Project (Priority: P1)

A contributor runs `spec-kitty init` in a new project, then invokes `/spec-kitty.specify`. The agent reads the full specify workflow prompt (200+ lines of discovery, template structure, and validation instructions) from `.claude/commands/spec-kitty.specify.md` and successfully conducts the specify workflow without errors, without searching for missing templates, and without hitting "missing required argument" failures.

**Why this priority**: This is the primary broken user journey. Every new consumer project is currently unable to run planning workflows.

**Independent Test**: Run `spec-kitty init` in a temp directory, then verify `.claude/commands/spec-kitty.specify.md` contains the full prompt (not a 3-line shim). Verify the agent can read and follow the instructions.

**Acceptance Scenarios**:

1. **Given** a fresh project after `spec-kitty init`, **When** an agent reads `.claude/commands/spec-kitty.specify.md`, **Then** the file contains the complete specify workflow prompt with discovery gates, branch context instructions, and spec template structure.
2. **Given** a fresh project after `spec-kitty init`, **When** an agent reads `.claude/commands/spec-kitty.plan.md`, **Then** the file contains the complete plan workflow prompt with planning interrogation and phase instructions.
3. **Given** a fresh project after `spec-kitty init`, **When** an agent reads `.claude/commands/spec-kitty.tasks.md`, **Then** the file contains the complete tasks workflow prompt with WP sizing guidance, ownership metadata requirements, and prompt generation rules.

---

### User Story 2 — Agent Runs Implement via Thin Shim (Priority: P1)

A contributor invokes `/spec-kitty.implement WP03` in a consumer project. The agent reads a thin shim from `.claude/commands/spec-kitty.implement.md` which dispatches to `spec-kitty agent shim implement`. The CLI resolves context, creates the worktree, emits the status event, and returns the workspace path and prompt file. The agent works in the worktree.

**Why this priority**: Execution commands must continue working via thin shims. The existing implement and review handlers are the model for CLI-driven commands.

**Independent Test**: Run `spec-kitty init` in a temp directory, then verify `.claude/commands/spec-kitty.implement.md` is a thin shim (3-4 lines). Verify the shim dispatches to a working CLI handler.

**Acceptance Scenarios**:

1. **Given** a project with a feature and WPs, **When** an agent invokes the implement shim, **Then** the CLI creates a worktree, emits a status event, and returns the workspace path.
2. **Given** a project with a feature and a WP in for_review, **When** an agent invokes the review shim, **Then** the CLI generates the review prompt and moves the WP to doing.
3. **Given** a project after init, **When** an agent reads `spec-kitty.implement.md`, **Then** it contains a thin shim (under 5 lines), not a full prompt.

---

### User Story 3 — Existing Consumer Project Upgrades (Priority: P1)

A maintainer of an existing spec-kitty project runs `spec-kitty upgrade`. The migration replaces thin shims for prompt-driven commands with full prompts, while leaving thin shims for CLI-driven commands intact.

**Why this priority**: Existing consumer projects (spec-kitty-saas, spec-kitty-tracker, spec-kitty-planning) are currently broken. They need the migration to restore working slash commands.

**Independent Test**: Set up a project with thin shims for all 16 commands. Run `spec-kitty upgrade`. Verify prompt-driven commands now have full prompts and CLI-driven commands still have thin shims.

**Acceptance Scenarios**:

1. **Given** an existing project with thin shims for all commands, **When** the user runs `spec-kitty upgrade`, **Then** spec-kitty.specify.md is replaced with the full prompt and spec-kitty.implement.md remains a thin shim.
2. **Given** an already-upgraded project, **When** the user runs `spec-kitty upgrade` again, **Then** no changes are made (idempotent).

---

### User Story 4 — Prompt Content Stays Current Across Upgrades (Priority: P2)

When spec-kitty releases a new version with updated prompt content (e.g., new ownership metadata guidance, corrected terminology), `spec-kitty upgrade` refreshes the full prompts from the global runtime without losing any project-specific overrides.

**Why this priority**: Prompt content evolves rapidly. The system must keep consumer projects current.

**Independent Test**: Modify a prompt in the package source, bump the version, run `ensure_runtime()`, then `spec-kitty upgrade` in a consumer project. Verify the prompt was updated.

**Acceptance Scenarios**:

1. **Given** a prompt update in the package, **When** `ensure_runtime()` runs, **Then** `~/.kittify/prompts/` contains the updated prompt.
2. **Given** a consumer project, **When** `spec-kitty upgrade` runs after a runtime refresh, **Then** prompt-driven command files are updated to the latest version.

---

### User Story 5 — CLI-Driven Shim Dispatches to Real Handler (Priority: P2)

An agent invokes `/spec-kitty.accept` via the thin shim. The shim calls `spec-kitty agent shim accept`, which dispatches to the existing `accept.py` CLI handler. The handler runs the acceptance workflow and returns results. No "context resolution failed" errors occur because accept is classified as CLI-driven and doesn't require WP context resolution.

**Why this priority**: Shim entrypoints for CLI-driven commands currently fail because `shim_dispatch()` tries to resolve WP context for all commands.

**Independent Test**: Run `spec-kitty agent shim accept --agent claude --raw-args "--feature 058-test"` and verify it delegates to the accept handler.

**Acceptance Scenarios**:

1. **Given** a CLI-driven command (accept, merge, status, dashboard), **When** invoked via shim, **Then** `shim_dispatch()` delegates to the existing CLI handler without requiring WP context.
2. **Given** a prompt-driven command (specify, plan, tasks), **When** invoked via shim, **Then** `shim_dispatch()` returns immediately (the full prompt file handles the workflow, not the CLI).

---

### Edge Cases

- What happens when a user has custom overrides in `.kittify/overrides/prompts/`? The override takes precedence over the package prompt.
- What happens when the global runtime (`~/.kittify/prompts/`) is stale? `ensure_runtime()` refreshes it on every CLI startup when the version changes.
- What happens when a CLI-driven shim command (e.g., merge) is invoked without `--feature`? The existing handler's error message (with available features list) is shown.
- What happens when both a full prompt and a thin shim exist for the same command? The full prompt wins (it's what the agent reads from `.claude/commands/`).

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Prompt-driven command classification | As a maintainer, I want commands classified as prompt-driven or CLI-driven so that `init` and `upgrade` install the correct file type for each. | High | Open |
| FR-002 | Canonical prompt source | As a maintainer, I want cleaned-up canonical prompts stored in `src/doctrine/prompts/` so that all consumer projects get consistent, up-to-date workflow instructions. | High | Open |
| FR-003 | Full prompt installation on init | As a contributor, I want `spec-kitty init` to install full prompt files for prompt-driven commands so that agents can run planning workflows immediately after init. | High | Open |
| FR-004 | Thin shim installation on init | As a contributor, I want `spec-kitty init` to install thin shims for CLI-driven commands so that execution workflows dispatch to CLI handlers. | High | Open |
| FR-005 | Global runtime prompt deployment | As a maintainer, I want `ensure_runtime()` to deploy prompts to `~/.kittify/prompts/` so that init and upgrade can source them from a consistent location. | High | Open |
| FR-006 | CLI-driven shim dispatch | As an agent, I want `shim_dispatch()` to delegate CLI-driven commands (accept, merge, status, dashboard, tasks-finalize) to their existing CLI handlers so that shim invocations actually work. | Medium | Open |
| FR-007 | Prompt-driven shim passthrough | As an agent, I want `shim_dispatch()` to return immediately for prompt-driven commands so that it doesn't fail on missing WP context. | High | Open |
| FR-008 | Upgrade migration | As a maintainer of an existing project, I want `spec-kitty upgrade` to replace thin shims with full prompts for prompt-driven commands while preserving thin shims for CLI-driven commands. | High | Open |
| FR-009 | Idempotent upgrade | As a maintainer, I want the migration to be idempotent so that running upgrade multiple times produces the same result. | Medium | Open |
| FR-010 | Prompt override support | As a power user, I want to place custom overrides in `.kittify/overrides/prompts/` that take precedence over package prompts. | Low | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Init speed | `spec-kitty init` completes in under 5 seconds including prompt installation. | Performance | Medium | Open |
| NFR-002 | Prompt freshness | After `ensure_runtime()`, prompts in `~/.kittify/prompts/` match the installed package version exactly. | Reliability | High | Open |
| NFR-003 | Test coverage | All new code achieves 90%+ test coverage with pytest. mypy --strict passes. | Quality | High | Open |
| NFR-004 | Agent compatibility | Prompts install correctly for all 12 supported agent directories. | Compatibility | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | No new external dependencies | No new Python package dependencies may be added. | Technical | High | Open |
| C-002 | Backward compatibility | Existing CLI-driven shim behavior must not change. Only prompt-driven commands gain full prompts. | Technical | High | Open |
| C-003 | Python 3.11+ | All code targets Python 3.11+ using typer, rich, ruamel.yaml, pytest, mypy (strict). | Technical | High | Open |
| C-004 | Prompt content is generic | Prompts must not contain dev-repo-specific references (feature 057 slugs, hardcoded paths). They must work in any consumer project. | Content | High | Open |

### Key Entities

- **Prompt-Driven Command**: A slash command whose workflow is defined by rich markdown prompt content that guides an LLM through discovery, decision-making, and artifact generation. Examples: specify, plan, tasks.

- **CLI-Driven Command**: A slash command whose workflow is implemented in Python CLI handlers. The agent invokes a thin shim that dispatches to the handler. Examples: implement, review, merge.

- **Canonical Prompt**: A cleaned-up, generic markdown file in `src/doctrine/prompts/` that contains the full workflow instructions for a prompt-driven command. Deployed to `~/.kittify/prompts/` by `ensure_runtime()` and installed to `.claude/commands/` by `init`.

- **Thin Shim**: A 3-4 line markdown file that tells the agent to run a CLI command. Installed to `.claude/commands/` for CLI-driven commands only.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After `spec-kitty init` in a fresh project, every prompt-driven command file in `.claude/commands/` contains 100+ lines of workflow instructions (not a 3-line shim).
- **SC-002**: After `spec-kitty init` in a fresh project, every CLI-driven command file in `.claude/commands/` contains a thin shim (under 5 lines).
- **SC-003**: An agent can successfully run `/spec-kitty.specify` in a newly initialized consumer project without hitting "missing required argument" errors or searching for template files.
- **SC-004**: `spec-kitty upgrade` in spec-kitty-saas, spec-kitty-tracker, and spec-kitty-planning restores working slash commands for all prompt-driven commands.
- **SC-005**: The 9 canonical prompts in `src/doctrine/prompts/` contain zero references to specific feature slugs, hardcoded dev-repo paths, or `.kittify/missions/` template file paths.
- **SC-006**: CLI-driven shim dispatch (accept, merge, status, dashboard, tasks-finalize) delegates to existing handlers without errors.
