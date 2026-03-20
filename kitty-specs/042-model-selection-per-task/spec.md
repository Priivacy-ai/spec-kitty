# Feature Specification: Model Selection per Task

**Feature Branch**: `042-model-selection-per-task`
**Created**: 2026-03-09
**Status**: Draft

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Configure Global Model Mapping (Priority: P1)

A developer uses spec-kitty across multiple projects and wants planning tasks (specify, plan) to use a more capable model (e.g., Opus) while implementation tasks use a faster, cheaper model (e.g., Sonnet). They configure this once globally and it applies everywhere.

**Why this priority**: This is the core value of the feature. Without a working config, nothing else functions.

**Independent Test**: User edits the global config, runs `spec-kitty upgrade` on any project, then inspects the generated command files to confirm the `model:` field is present with the correct value.

**Acceptance Scenarios**:

1. **Given** a global config with `specify: claude-opus-4-6` and `implement: claude-sonnet-4-6`, **When** the user runs `spec-kitty upgrade`, **Then** the `specify` command file for all configured agents contains `model: claude-opus-4-6` in its frontmatter, and the `implement` command file contains `model: claude-sonnet-4-6`.

2. **Given** no model config is set, **When** the user runs `spec-kitty upgrade`, **Then** command files are generated without a `model:` field (existing behaviour preserved).

3. **Given** a partial model config (only some commands mapped), **When** the user runs `spec-kitty upgrade`, **Then** only the mapped commands receive a `model:` field; unmapped commands are unaffected.

---

### User Story 2 - Model Config Survives Upgrades (Priority: P2)

A user has configured their model mapping. After a new version of spec-kitty is released, they run `spec-kitty upgrade`. Their model preferences should be re-applied to the freshly generated command files automatically — they should not need to re-configure anything.

**Why this priority**: Without this, users lose their config on every upgrade, making the feature impractical.

**Independent Test**: Set config, run upgrade, verify models are injected. Bump spec-kitty version, run upgrade again, verify models are still injected correctly.

**Acceptance Scenarios**:

1. **Given** a global model mapping is set and command files already have `model:` fields, **When** `spec-kitty upgrade` re-generates command files, **Then** the `model:` values are re-applied from the config (not lost).

---

### User Story 3 - Multi-Agent Support (Priority: P3)

A user has multiple agents configured (e.g., Claude Code and OpenCode). When they set a model mapping, it should be applied to all agents that support model selection in their command frontmatter. Agents that don't support it are silently skipped.

**Why this priority**: Agents are a core spec-kitty concept. Model selection should work for all configured agents, not just Claude Code.

**Independent Test**: Configure two agents. Set model mapping. Run upgrade. Inspect command files for both agents — both should have `model:` where supported.

**Acceptance Scenarios**:

1. **Given** Claude Code and OpenCode are configured and both support `model:` in frontmatter, **When** `spec-kitty upgrade` runs, **Then** both agents' command files contain the configured model values.

2. **Given** an agent whose command format does not support `model:` frontmatter, **When** `spec-kitty upgrade` runs, **Then** that agent's files are left unchanged and no error is raised.

---

### Edge Cases

- What happens when the user specifies an invalid or unknown model name? → Config is accepted as-is; spec-kitty does not validate model names (user is responsible for using models they have access to).
- What happens if a command name in the config doesn't match any known command (e.g., typo `"spceify"`)? → Unknown keys are ignored; a warning is shown listing unrecognised command names.
- What happens if the global config file is malformed YAML? → Upgrade aborts with a clear error message pointing to the config file.
- What happens if a command file has no existing YAML frontmatter block? → spec-kitty creates one with just the `model:` field.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST support a global configuration file where users define a mapping of spec-kitty command names to model strings (e.g., `specify: claude-opus-4-6`).
- **FR-002**: The configuration MUST be stored in a well-known global location (e.g., `~/.config/spec-kitty/config.yaml`), separate from any project-level config.
- **FR-003**: During `spec-kitty upgrade`, the system MUST read the global model mapping and inject a `model:` field into the YAML frontmatter of each matching agent command file.
- **FR-004**: The injection MUST apply to all agents configured in the project's `.kittify/config.yaml` that support `model:` frontmatter in their command files.
- **FR-005**: Agents whose command file format does not support `model:` frontmatter MUST be skipped silently (no error raised).
- **FR-006**: If no global model config exists, `spec-kitty upgrade` MUST proceed unchanged (backwards-compatible, no breaking change).
- **FR-007**: Unrecognised command names in the model config MUST produce a warning (not an error) listing the unknown keys.
- **FR-008**: A malformed global config file MUST cause `spec-kitty upgrade` to abort with a descriptive error message.
- **FR-009**: The feature MUST be documented so users know the config file location and the valid command name keys.

### Key Entities

- **Global Model Config**: A YAML file at a well-known user-level path. Contains a `models:` section mapping command names (e.g., `specify`, `plan`, `implement`) to model strings (e.g., `claude-opus-4-6`).
- **Command Name**: One of the spec-kitty slash command names without the `spec-kitty.` prefix (e.g., `specify`, `plan`, `tasks`, `implement`, `review`, `accept`, `merge`).
- **Agent Command File**: A markdown file inside an agent directory (e.g., `.claude/commands/spec-kitty.specify.md`) that may have YAML frontmatter.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can configure their preferred model per task in a single file and have it applied across all projects without repeating the configuration.
- **SC-002**: After running `spec-kitty upgrade`, 100% of configured command files for supported agents contain the `model:` value from the global config.
- **SC-003**: Running `spec-kitty upgrade` with a model config takes no measurably longer than without one (injection is not a performance bottleneck).
- **SC-004**: Zero existing tests break when the feature is disabled (no global config present).

## Assumptions

- The `model:` frontmatter field is the correct injection point for Claude Code and other agents that follow the same open standard for skill/command frontmatter.
- The user is responsible for choosing valid model identifiers for the agents and subscriptions they use; spec-kitty does not validate model names.
- The global config location (`~/.config/spec-kitty/`) follows XDG conventions and is appropriate for a CLI tool.
- The set of command names that can be mapped corresponds to the known spec-kitty slash commands (specify, plan, tasks, implement, review, accept, merge, clarify, status, checklist, analyze, research).
