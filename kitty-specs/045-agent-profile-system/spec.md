# Feature Specification: Agent Profile System

**Feature Branch**: `feature/agent-profile-implementation`
**Created**: 2026-02-23
**Status**: In Progress (WP01-WP04, WP06-WP07 complete; WP05, WP08-WP15 planned)
**Target Branch**: `feature/agent-profile-implementation`
**Mission**: software-dev
**Base Branch**: `2.x`

## Overview

### Motivation: Bridging Exploration and Structured Approach

Spec Kitty's mission system provides a rigorous, structured approach to software development — but not every interaction warrants launching a full mission. Ad-hoc requests, quick fixes, code reviews, and exploratory work still need to be as compliant as possible with a project's doctrine and constitution governance. Today, there is no mechanism to carry governance context into these informal interactions.

Agent profiles fill this gap. They provide a lightweight, declarative way to load the right governance context (directives, paradigms, specialization boundaries, collaboration contracts) into any agent interaction — whether that interaction is a full mission run or a quick ad-hoc request. An agent initialized with a profile carries its doctrine awareness, role boundaries, and collaboration rules regardless of whether a mission is active.

This positions agent profiles as the **identity layer** that operates beneath missions: missions orchestrate *what work happens*; profiles govern *who does the work and how they behave*.

### Initialization and Assignment Model

Agent profiles are activated in two ways:

1. **Direct invocation**: A user calls a command (e.g., `spec-kitty agent profile init <profile-id>`) to initialize an agent with a specific profile and start an interactive session. The profile's initialization declaration, doctrine references, and specialization boundaries are loaded into the session context.

2. **Mission assignment**: During mission execution, work packages are assigned by role and profile. The orchestrator selects the best-fit profile for each work package based on the role requirement and weighted matching algorithm.

Future lifecycle integrations may extend profile initialization to other steps — for example, a Bootstrap Bill-style agent conducting the constitution interview, or a reviewer profile being activated automatically during `/spec-kitty.review`.

### What This Feature Delivers

The Agent Profile System introduces a structured identity framework for agents within the doctrine domain. An agent profile is a doctrine artifact that defines an agent's role, capabilities, specialization boundaries, collaboration contracts, and initialization behavior. Profiles follow the two-source loading pattern (shipped defaults + project-level overrides) and are validated against a JSON Schema.

This feature also disambiguates the existing `AgentConfig` (which manages tool installation/availability) from agent identity by renaming it to `ToolConfig`, aligning with the canonical glossary distinction between "tool" (concrete runtime product) and "agent" (logical collaborator identity).

As a quality-of-life addition, this feature ships doctrine templates for `REPO_MAP` and `SURFACES` — structural mapping artifacts that enable agents (and humans) to quickly orient themselves in a repository. These templates follow the Bootstrap Bill pattern from the doctrine reference framework and are available as shipped doctrine templates for project-level generation.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Mission Owner Discovers Available Agent Roles (Priority: P1)

A mission owner wants to see which agent profiles are available in their project so they can assign appropriate roles to work packages.

**Why this priority**: Visibility of available agents is foundational to all assignment and routing decisions.

**Independent Test**: Running `spec-kitty agent profile list` displays a table of all profiles with ID, name, role, routing priority, and source (shipped/project).

**Acceptance Scenarios**:

1. **Given** a fresh project with no custom profiles, **When** the user runs `spec-kitty agent profile list`, **Then** all 7 shipped reference profiles are displayed with source marked as "shipped"
2. **Given** a project with a custom profile in `.kittify/constitution/agents/`, **When** the user runs `spec-kitty agent profile list`, **Then** both shipped and project profiles appear, with project profiles marked as "project"
3. **Given** a project profile that overrides a shipped profile ID, **When** listed, **Then** the merged profile appears once with source marked as "project"

---

### User Story 2 - Mission Owner Inspects Agent Capabilities (Priority: P1)

A mission owner wants to view the full details of a specific agent profile to understand its specialization, collaboration contracts, and operating modes before assigning it to work.

**Why this priority**: Understanding agent capabilities is essential for correct role assignment and handoff planning.

**Independent Test**: Running `spec-kitty agent profile show <profile-id>` renders a complete profile with all 6 sections.

**Acceptance Scenarios**:

1. **Given** a valid profile ID, **When** the user runs `spec-kitty agent profile show implementer`, **Then** the full profile is displayed including purpose, specialization, collaboration contract, mode defaults, and initialization declaration
2. **Given** an invalid profile ID, **When** the user runs `spec-kitty agent profile show nonexistent`, **Then** an error message indicates the profile was not found

---

### User Story 3 - Mission Owner Creates Agent via Interview (Priority: P2)

A mission owner wants to create a new custom agent profile through a guided interview that captures the agent's role, purpose, specialization, collaboration rules, and doctrine references — without needing to know the YAML schema or manually edit files.

**Why this priority**: Lowering the barrier to agent creation is essential for adoption. The interview pattern (established by the constitution compiler) is the canonical way to capture structured governance intent through interactive Q&A. Creating agents should follow the same pattern.

**Independent Test**: Running `spec-kitty agent profile create --interview` walks through a structured questionnaire and produces a valid `.agent.yaml` file in the project's agent directory.

**Acceptance Scenarios**:

1. **Given** the user runs `spec-kitty agent profile create --interview`, **When** they answer each question (role, name, purpose, primary focus, collaboration partners, doctrine references, mode defaults), **Then** a valid `.agent.yaml` is written to `.kittify/constitution/agents/<profile-id>.agent.yaml`
2. **Given** the user selects a role from the enumeration (e.g., `implementer`), **When** the profile is generated, **Then** default capabilities for that role are pre-populated from the shipped role capabilities mapping
3. **Given** the user specifies `specializes-from: implementer`, **When** the profile is generated, **Then** the new profile inherits unspecified fields from the parent and only overrides what the user provided
4. **Given** the user runs `spec-kitty agent profile create --interview --defaults`, **When** using the fast path, **Then** a minimal valid profile is generated with sensible defaults and the user only answers required questions (profile-id, name, purpose, role, primary-focus)
5. **Given** the interview is complete, **When** the profile is written, **Then** the output passes JSON Schema validation

---

### User Story 3b - Mission Owner Creates Agent from Template (Priority: P3)

A mission owner wants to quickly clone a shipped profile as a starting point for manual customization.

**Why this priority**: Template-based creation is a power-user shortcut for those comfortable editing YAML directly. Lower priority than the interview path because it requires schema knowledge.

**Independent Test**: Running `spec-kitty agent profile create --from-template implementer --profile-id my-implementer` creates a new profile file in the project's agent directory.

**Acceptance Scenarios**:

1. **Given** a valid template ID and a new profile ID, **When** the user runs the create command, **Then** a new `.agent.yaml` file is created in the project directory with the updated profile ID
2. **Given** a profile ID that already exists in the project directory, **When** the user attempts to create, **Then** an error prevents overwriting the existing profile

---

### User Story 4 - Mission Owner Views Agent Hierarchy (Priority: P2)

A mission owner wants to understand how agent profiles relate through specialization (parent-child relationships) to plan role inheritance.

**Why this priority**: Hierarchy visualization supports planning decisions about profile reuse and specialization.

**Independent Test**: Running `spec-kitty agent profile hierarchy` renders a tree with summary counts.

**Acceptance Scenarios**:

1. **Given** profiles with no specialization relationships, **When** the user runs `spec-kitty agent profile hierarchy`, **Then** all profiles appear as roots with counts (total, roots, specialized)
2. **Given** a project profile with `specializes-from: implementer`, **When** the hierarchy is displayed, **Then** the child profile appears indented under its parent

---

### User Story 5 - Doctrine Package Ships in Wheel Distribution (Priority: P1)

The `doctrine` package containing agent profiles, schemas, and shipped reference data must be included in the wheel distribution so that users installing via `pip install spec-kitty-cli` have access to agent profile functionality.

**Why this priority**: Without wheel inclusion, agent profile CLI commands fail at runtime with import errors. This is a distribution blocker.

**Independent Test**: After `pip install spec-kitty-cli`, `from doctrine.agent_profiles import AgentProfile` succeeds and `spec-kitty agent profile list` returns shipped profiles.

**Acceptance Scenarios**:

1. **Given** a wheel built from the source tree, **When** installed in a clean virtual environment, **Then** `import doctrine` succeeds
2. **Given** the installed package, **When** running `spec-kitty agent profile list`, **Then** shipped profiles load from package data without errors
3. **Given** the wheel, **When** inspected with `zipfile`, **Then** it contains `doctrine/agent_profiles/shipped/*.agent.yaml` files

---

### User Story 6 - Existing Projects Migrate ToolConfig Rename (Priority: P2)

Projects using the pre-rename `AgentConfig` API receive deprecation warnings and can upgrade cleanly via spec-kitty's migration system. As part of this migration, the YAML key `agents` in `.kittify/config.yaml` is renamed to `tools` to align with the canonical glossary meaning: the key stores tool identifiers (e.g., "claude", "codex", "opencode"), not agent identities.

**Why this priority**: Backward compatibility ensures existing integrations continue working while guiding users toward the canonical naming. Aligning the YAML key with glossary meaning prevents ongoing confusion between tools and agents.

**Independent Test**: After upgrading, imports from `agent_config` emit deprecation warnings, the new `tool_config` imports work, and config.yaml files with either `agents` or `tools` keys are parsed correctly.

**Acceptance Scenarios**:

1. **Given** code importing `from specify_cli.core.agent_config import AgentConfig`, **When** executed, **Then** a `DeprecationWarning` is emitted and the import succeeds (shim re-exports from `tool_config`)
2. **Given** an existing `.kittify/config.yaml` using the legacy `agents` key, **When** migration runs, **Then** the key is renamed to `tools` and the config loads correctly under `ToolConfig`
3. **Given** a `.kittify/config.yaml` with neither `agents` nor `tools` key, **When** loaded, **Then** defaults are applied without error
4. **Given** the migration system, **When** `spec-kitty upgrade` runs, **Then** the migration is registered and applies without errors
5. **Given** a config.yaml still using the legacy `agents` key (migration not yet run), **When** loaded by `ToolConfig`, **Then** the legacy key is read with a deprecation warning (backward-compatible fallback)

---

### User Story 7 - Agent Matching Selects Best Profile for Task Context (Priority: P3)

The weighted matching algorithm selects the most suitable agent profile for a given task context based on language, framework, file patterns, keywords, workload, and complexity factors.

**Why this priority**: Automated agent selection is a future orchestration enabler. The algorithm is implemented but not yet wired into runtime assignment.

**Independent Test**: Calling `repository.find_best_match(task_context)` returns the profile with the highest weighted score.

**Acceptance Scenarios**:

1. **Given** a task context with `language="python"` and `framework="pytest"`, **When** matched against profiles, **Then** a profile with matching specialization context scores highest
2. **Given** two matching profiles where one has 5 active tasks and the other has 0, **When** matched, **Then** the less-loaded profile scores higher (workload penalty applied)

---

### User Story 8 - Doctrine Ships REPO_MAP and SURFACES Templates (Priority: P2)

A mission owner or bootstrap agent wants to generate `REPO_MAP.md` and `SURFACES.md` files for their project to provide structural orientation for agents and human collaborators. Shipped doctrine templates provide the canonical format. When onboarding a new project via `spec-kitty init`, the bootstrap process offers to generate these structural maps as part of initialization.

**Why this priority**: Structural mapping artifacts reduce onboarding friction for both agents and humans. Without them, agents lack the topological context needed for efficient routing and file discovery. This is a quality-of-life improvement that compounds across all mission interactions. Integration with the init/bootstrap process ensures new projects start with proper structural orientation.

**Independent Test**: The doctrine package ships template files for REPO_MAP and SURFACES. Running `spec-kitty init` on a new project offers to generate these files from the shipped templates.

**Acceptance Scenarios**:

1. **Given** the doctrine package is installed, **When** a user or agent looks in `src/doctrine/templates/structure/`, **Then** template files for `REPO_MAP.md` and `SURFACES.md` are present with placeholder markers
2. **Given** a REPO_MAP template, **When** populated for a project, **Then** the output describes repository topology: folder purposes, key files, primary languages, build system, and test frameworks
3. **Given** a SURFACES template, **When** populated for a project, **Then** the output describes entry points (CLI, service, library), external integrations, public interfaces, and observability endpoints
4. **Given** a user running `spec-kitty init` on a new project, **When** the bootstrap process reaches the structural mapping step, **Then** the user is offered to generate `REPO_MAP.md` and `SURFACES.md` from the shipped doctrine templates
5. **Given** the user accepts REPO_MAP/SURFACES generation during init, **When** the files are generated, **Then** they are placed in the project's documentation location with placeholder markers ready for customization

---

### User Story 9 - Doctrine Directive Consistency (Priority: P1)

The shipped agent profiles reference 19 directive codes (001-019) by code and name. These directives must exist as files in `src/doctrine/directives/` so the doctrine stack is internally consistent and references resolve.

**Why this priority**: A shipped doctrine stack that references non-existent directives is a consistency violation that undermines trust in the governance framework. Agents loading a profile and following its directive references must find the actual directive content.

**Independent Test**: A consistency test verifies that every directive code referenced by any shipped profile resolves to an existing directive file in `src/doctrine/directives/`, and every directive file's metadata matches the code and name declared in the profile.

**Acceptance Scenarios**:

1. **Given** the 7 shipped profiles reference directive codes 001-019, **When** a consistency test scans profiles and directives, **Then** every referenced code maps to a directive file in `src/doctrine/directives/`
2. **Given** a shipped profile declares `code: "004"` with `name: "Test-Driven Implementation Standard"`, **When** the test loads directive `004`, **Then** the directive's title matches
3. **Given** a directive file exists in `src/doctrine/directives/` that is NOT referenced by any profile, **When** the consistency test runs, **Then** no error is raised (unreferenced directives are allowed)
4. **Given** a new shipped profile is added that references a non-existent directive code, **When** CI runs, **Then** the consistency test fails

---

### User Story 10 - Agent Initialization via CLI (Priority: P2)

A user wants to initialize an agent with a specific profile so that the active tool (e.g., Claude Code, Codex) adheres to the profile's governance context. Initialization configures the tool to operate within the profile's directives, specialization boundaries, collaboration contracts, and mode defaults — not merely display them.

**Why this priority**: Direct invocation is the primary way users interact with agent profiles outside of mission execution. It makes governance context enforceable for ad-hoc work.

**Independent Test**: Running `spec-kitty agent profile init <profile-id>` configures the active tool to adhere to the profile's governance artifacts (directives, specialization, collaboration, mode defaults).

**Acceptance Scenarios**:

1. **Given** a valid profile ID, **When** the user runs `spec-kitty agent profile init implementer`, **Then** the active tool is configured to adhere to the profile's directives, specialization boundaries, collaboration contracts, and mode defaults
2. **Given** an invalid profile ID, **When** the user runs `spec-kitty agent profile init nonexistent`, **Then** an error message indicates the profile was not found
3. **Given** a profile with `specializes-from: implementer`, **When** initialized, **Then** the inherited context from the parent profile is resolved and the tool is configured with the merged governance context

---

### User Story 11 - Mission Schema Supports Optional Agent Profile per Step (Priority: P2)

A mission author wants to specify which agent profile should handle a particular mission state or step, so that the orchestrator can assign the right agent identity for each phase of the workflow.

**Why this priority**: Connecting agent profiles to mission steps is the natural integration point that makes profiles actionable within the structured mission workflow. Without this, profile selection during mission execution remains implicit.

**Independent Test**: The mission schema (`src/doctrine/schemas/mission.schema.yaml`) accepts an optional `agent-profile` field on states and steps. Existing missions without the field continue to validate. The runtime DAG mission format (`mission-runtime.yaml`) also accepts the optional field on steps.

**Example — software-dev mission with profile assignments**:

The software-dev mission could leverage agent profiles per step to assign the right specialist identity at each phase:

- `discovery` / `specify` → `researcher` or analyst profile (research-oriented identity)
- `plan` → `architect` profile (design and architecture focus)
- `tasks_outline` / `tasks_packages` → `planner` profile (decomposition and dependency planning)
- `implement` → `implementer` profile (frontend/backend specialist, potentially specialized per WP)
- `review` → `reviewer` profile (code quality and compliance focus)

This allows the orchestrator to load the correct governance context, specialization boundaries, and collaboration contracts for each phase automatically.

**Acceptance Scenarios**:

1. **Given** the mission schema, **When** a state includes an optional `agent-profile: reviewer` field, **Then** the schema validates successfully
2. **Given** the mission schema, **When** a state omits the `agent-profile` field, **Then** the schema validates successfully (backward compatible)
3. **Given** the runtime DAG format, **When** a step includes `agent-profile: architect`, **Then** the step definition validates successfully
4. **Given** an `agent-profile` value that does not match a known profile ID pattern, **When** validated, **Then** the schema reports a pattern violation
5. **Given** the existing shipped mission definitions (software-dev, research, documentation, plan), **When** validated against the updated schema, **Then** all existing missions validate without modification

---

### User Story 12 - Specialized Profiles Inherit from Parent (Priority: P2)

A project owner creates a specialized agent profile (e.g., "Python Pedro") that declares `specializes-from: implementer`. The specialized profile only needs to declare its delta — overridden fields like `specialization-context`, `primary-focus`, and specific directive references. All other fields (collaboration contract, mode defaults, initialization declaration, avoidance boundaries) are inherited from the parent profile at resolution time.

**Why this priority**: Without field-level inheritance, every specialized profile must manually redeclare all parent fields, making specialization verbose and error-prone. True inheritance enables lightweight child profiles that focus only on what makes them different — which is essential for the "Python Pedro assigned to a Python WP" scenario during mission planning.

**Independent Test**: Calling `repository.resolve_profile("python-pedro")` returns a fully merged profile where child fields override parent fields and all unspecified fields fall through from the parent. Multi-level chains (grandchild → child → parent) resolve correctly.

**Acceptance Scenarios**:

1. **Given** a child profile that only declares `specializes-from`, `profile-id`, `name`, `purpose`, `primary-focus`, and `specialization-context`, **When** resolved, **Then** all other sections (collaboration, mode-defaults, initialization, directive-references) are inherited from the parent
2. **Given** a child profile that overrides `mode-defaults.autonomy-level: high` while the parent has `medium`, **When** resolved, **Then** the child's override wins and all other mode-defaults come from the parent
3. **Given** a three-level chain (grandchild → child → parent), **When** the grandchild is resolved, **Then** fields cascade correctly: grandchild overrides child overrides parent
4. **Given** a child profile that declares `specialization-context.languages: [python]` while the parent has `languages: [python, javascript]` and `frameworks: [django]`, **When** resolved, **Then** the child's `languages` key overrides the parent's (`[python]`), while the parent's `frameworks` key is preserved (`[django]`) — shallow merge within the section
5. **Given** a child profile with an orphaned `specializes-from` reference, **When** resolved, **Then** a warning is emitted and the child is returned as-is without inheritance
6. **Given** a resolved specialist profile, **When** used in weighted matching, **Then** the inherited `specialization-context` fields participate in scoring alongside the child's own fields

---

### Edge Cases

- What happens when a shipped profile YAML is malformed? The repository skips it with a warning and continues loading valid profiles.
- What happens when a project profile references a `specializes-from` ID that doesn't exist? Hierarchy validation reports it as an orphaned reference; resolution returns the child as-is with a warning.
- What happens when profile hierarchy contains a cycle? `validate_hierarchy()` detects and reports the cycle; resolution raises an error rather than looping.
- What happens when a custom role string is used instead of a known Role enum value? The role is accepted with a warning; the profile remains functional.
- What happens when a child profile overrides a nested section partially? Shallow merge applies: child keys override parent keys one level deep within the section, parent keys absent from the child are preserved.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide an `AgentProfile` domain model with 6 sections: context sources, purpose, specialization, collaboration contract, mode defaults, and initialization declaration
- **FR-002**: System MUST support a `Role` enumeration with at least: implementer, reviewer, architect, designer, planner, researcher, curator, manager
- **FR-003**: System MUST accept custom role strings beyond the enumeration with a warning
- **FR-004**: System MUST load profiles from two sources: shipped package data and project filesystem, with field-level merge semantics (project overrides shipped)
- **FR-005**: System MUST validate profiles against a JSON Schema (Draft 7)
- **FR-006**: System MUST ship at least 7 reference profiles covering core roles
- **FR-007**: System MUST provide CLI commands: `list`, `show`, `create`, `hierarchy`
- **FR-008**: System MUST detect and report hierarchy cycles and orphaned `specializes-from` references
- **FR-009**: System MUST support weighted context-based matching with configurable factors (language, framework, file patterns, keywords, workload, complexity)
- **FR-010**: System MUST rename `AgentConfig` to `ToolConfig` with a backward-compatible deprecation shim, and rename the YAML key from `agents` to `tools` in `.kittify/config.yaml` to align with the canonical glossary meaning (the key stores tool identifiers, not agent identities)
- **FR-011**: The `doctrine` package MUST be included in the wheel distribution
- **FR-012**: System MUST register an upgrade migration for the ToolConfig rename that also renames the `agents` YAML key to `tools` in `.kittify/config.yaml`, with backward-compatible fallback that reads the legacy `agents` key if `tools` is absent
- **FR-013**: System MUST provide an interactive interview flow (`--interview`) for creating agent profiles, capturing role, purpose, specialization, collaboration, and doctrine references through structured Q&A
- **FR-014**: The interview flow MUST support a fast path (`--defaults`) that pre-populates sensible defaults and only asks required questions
- **FR-015**: The interview flow MUST persist answers and produce a valid `.agent.yaml` that passes JSON Schema validation
- **FR-016**: When a role is selected during the interview, default capabilities MUST be pre-populated from the shipped role capabilities mapping
- **FR-017**: The doctrine package MUST ship directive YAML files in `src/doctrine/directives/` for all 19 codes referenced by shipped profiles (001-019), conforming to `directive.schema.yaml` (schema_version, id, title, intent, tactic_refs, enforcement)
- **FR-018**: A consistency test MUST verify that every directive code referenced by shipped profiles resolves to a directive file whose title matches the declared name
- **FR-019**: System MUST provide a CLI command (`spec-kitty agent profile init <profile-id>`) that configures the active tool to adhere to the profile's governance artifacts (directives, specialization boundaries, collaboration contracts, mode defaults)
- **FR-020**: The doctrine package MUST ship template files for `REPO_MAP.md` and `SURFACES.md` in `src/doctrine/templates/structure/`
- **FR-021**: Templates MUST use placeholder markers (e.g., `{{DATE}}`, `{{TREE_SNIPPET}}`) that can be populated by agents or users for project-specific generation
- **FR-022**: The `spec-kitty init` bootstrap process MUST offer to generate `REPO_MAP.md` and `SURFACES.md` from the shipped doctrine templates as part of project onboarding
- **FR-023**: The mission schema (`mission.schema.yaml`) and runtime DAG format MUST accept an optional `agent-profile` field on states/steps, constrained to the kebab-case profile ID pattern, with no impact on existing missions that omit the field
- **FR-024**: The repository MUST provide a `resolve_profile()` method that walks the `specializes-from` ancestor chain and produces a fully merged profile using shallow merge: child keys override parent keys one level deep within each section, parent keys absent from the child are preserved
- **FR-025**: Profile inheritance resolution MUST support multi-level chains (grandchild → child → parent) with correct cascading precedence (closest descendant wins)
- **FR-026**: The weighted matching algorithm MUST use the resolved (inherited) profile fields when scoring, so that a child profile benefits from its parent's specialization context for any fields it does not override

### Key Entities

- **AgentProfile**: The primary doctrine artifact defining an agent's identity, purpose, specialization, and collaboration contracts. Identified by a kebab-case `profile-id`.
- **Role**: Enumerated responsibility assignment (implementer, reviewer, architect, etc.) with custom role extension.
- **AgentProfileRepository**: Two-source loader that discovers, merges, queries, and persists profiles.
- **TaskContext**: Weighted matching input describing a task's language, framework, complexity, and current agent workload.
- **ToolConfig**: Configuration for which tools are installed/available in a project (renamed from AgentConfig).
- **Directive**: A constraint-oriented governance rule referenced by profile code (e.g., `"004"`). Stored as YAML files in `src/doctrine/directives/` with title, intent, and enforcement level.
- **REPO_MAP**: Structural mapping artifact describing repository topology (folders, key files, languages, build system) for agent and human orientation.
- **SURFACES**: Structural mapping artifact describing entry points, external integrations, public interfaces, and observability endpoints.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 7 shipped reference profiles load and validate without errors
- **SC-002**: CLI commands (`list`, `show`, `create`, `hierarchy`) execute successfully with correct output
- **SC-003**: Project-level profile overrides merge correctly with shipped profiles at field level
- **SC-004**: Hierarchy validation detects cycles and orphaned references in all test scenarios
- **SC-005**: The `doctrine` package is present and importable from a wheel-installed distribution
- **SC-006**: Existing `AgentConfig` imports continue to work via deprecation shim
- **SC-007**: All agent profile tests pass (target: 120+ tests covering model, repository, schema, CLI, and shipped profiles)
- **SC-008**: Interactive interview creates a valid `.agent.yaml` that passes schema validation
- **SC-009**: Fast-path interview (`--defaults`) completes with only 5 required answers
- **SC-010**: All 19 directive files exist in `src/doctrine/directives/` and pass the consistency test against shipped profile references
- **SC-011**: Agent initialization via CLI configures the active tool to adhere to the profile's governance artifacts
- **SC-012**: REPO_MAP and SURFACES templates are present in the doctrine package and contain valid placeholder structure
- **SC-013**: Mission schema accepts optional `agent-profile` on states/steps; existing missions validate without modification
- **SC-014**: A child profile declaring only its delta from the parent resolves to a complete profile with all inherited fields; multi-level chains resolve correctly

## Clarifications

### Session 2026-02-23

- Q: What does "session" mean when `spec-kitty agent profile init` loads profile context? → A: The tool is configured to adhere to the artifacts described in the agent profile — directives, specialization boundaries, collaboration contracts, and mode defaults are enforced in the active tool session, not merely displayed.
- Q: What merge granularity applies when a child profile inherits from a parent? → A: Shallow merge within sections — child keys override parent keys one level deep, parent keys not present in the child are preserved. Consistent across all sections.
- Q: What format should the 19 shipped directive files follow? → A: Follow the established `directive.schema.yaml` pattern (schema_version, id, title, intent, tactic_refs, enforcement) as demonstrated by `test-first.directive.yaml`. All implementation WPs must follow ATDD/TDD (test-first).

## Assumptions

- The `doctrine` package follows the same Python 3.11+ requirement as `specify_cli`
- Agent profiles are read-only doctrine artifacts at the shipped level; project-level profiles are the customization mechanism
- The weighted matching algorithm is implemented but not yet integrated into runtime orchestration (future feature)
- The ToolConfig rename migration renames the `agents` YAML key to `tools` in config.yaml, with a backward-compatible fallback that reads the legacy key during the transition period
- All remaining WPs follow ATDD/TDD (test-first) methodology per the test-first directive

## Work Package Summary

### Completed Work Packages

| WP | Title | Status | Description |
|----|-------|--------|-------------|
| WP01 | AgentProfile Domain Model | Done | Pydantic model with 6-section structure, Role enum, value objects, TaskContext |
| WP02 | AgentProfileRepository | Done | Two-source loading, field-level merge, hierarchy, weighted matching, save/delete |
| WP03 | YAML Schema & Validation | Done | JSON Schema (Draft 7), validation utility, file type detection, test fixtures |
| WP04 | Shipped Reference Profiles | Done | 7 profiles (implementer, reviewer, architect, planner, designer, researcher, curator), alias normalization |
| WP06 | ToolConfig Rename | Done | AgentConfig to ToolConfig with deprecation shim, backward-compatible imports |
| WP07 | CLI Commands | Done | `list`, `show`, `create`, `hierarchy` subcommands under `spec-kitty agent profile` |

### Remaining Work Packages

| WP | Title | Status | Description |
|----|-------|--------|-------------|
| WP05 | Doctrine Wheel Packaging | Planned | Add `src/doctrine` to `pyproject.toml` wheel packages so it ships in distribution |
| WP08 | ToolConfig Upgrade Migration | Planned | Register migration in upgrade system for the AgentConfig-to-ToolConfig rename; rename YAML key from `agents` to `tools` in `.kittify/config.yaml` with backward-compatible fallback; update all code that parses the config key |
| WP09 | CI & Test Alignment | Planned | Add `__main__.py` module (done), ensure doctrine tests run in CI, verify wheel contents |
| WP10 | Shipped Directives & Consistency | Planned | Create 19 directive YAML files in `src/doctrine/directives/` matching shipped profile references, plus consistency test that cross-validates profile references against directive files |
| WP11 | Agent Profile Interview | Planned | Interactive `--interview` flow for creating profiles through guided Q&A, with `--defaults` fast path, role-based capability pre-population, and schema validation |
| WP12 | Agent Initialization CLI | Planned | `spec-kitty agent profile init <profile-id>` command that loads profile context into an interactive session |
| WP13 | Doctrine Structure Templates | Planned | Ship REPO_MAP.md and SURFACES.md templates in `src/doctrine/templates/structure/`, adapted from doctrine_ref reference format; integrate with `spec-kitty init` bootstrap process to offer REPO_MAP/SURFACES generation during project onboarding |
| WP14 | Mission Schema Agent Profile Integration | Planned | Add optional `agent-profile` field to mission schema states and runtime DAG steps; validate against kebab-case profile ID pattern; ensure backward compatibility with existing missions. Example: software-dev mission steps could reference `architect` for planning, `implementer` for implementation, `reviewer` for review |
| WP15 | Profile Inheritance Resolution | Planned | Add `resolve_profile()` to `AgentProfileRepository` that walks the `specializes-from` ancestor chain and merges fields bottom-up (child overrides parent at section level); support multi-level chains with cycle-safe traversal; update weighted matching to use resolved profiles for scoring |
