# Feature Specification: Agent Profile Domain Model

**Feature Branch**: `047-agent-profile-domain-model`
**Created**: 2026-02-16
**Status**: Draft
**Input**: Create a rich Agent Profile model as a first-class entity in spec-kitty 2.x. Agent profiles define WHO an agent IS — purpose, specialization boundaries, collaboration contracts, reasoning modes, directive adherence, and specialization hierarchy. Design source: doctrine reference repository (`doctrine_ref/`).

## Overview

Spec-kitty 2.x currently conflates two distinct concepts under the term "agent": the **tool stack** (claude, copilot, cursor — the IDE/CLI integration) and the **behavioral identity** (architect, implementer, reviewer — the persona operating under constraints). The existing `AgentConfig` in `agent_config.py` tracks tool availability and selection strategy but knows nothing about *who* an agent is, *what* it specializes in, or *how* it collaborates with other agents.

This feature introduces:

1. **AgentProfile as a domain entity** — a structured YAML document capturing purpose, specialization, collaboration contracts, reasoning modes, and directive adherence. Follows the 6-section structure from the doctrine framework.
2. **Specialization hierarchy** — parent-child inheritance where specialist agents refine a generalist's scope. Routing priority, specialization context (language, frameworks, file patterns, domain keywords), workload awareness, and complexity adjustments.
3. **Separate `src/doctrine/` package** — a new top-level Python package housing reference profiles, tactics, directives, and the AgentProfile domain model. Separated from `specify_cli` to lower contextual scope and improve agentic development velocity.
4. **AgentProfileRepository** — a DDD-style repository service that reads all available profiles (shipped reference profiles from `src/doctrine/agents/` + constitution overrides from `.kittify/constitution/agents/`) with deterministic merge semantics.
5. **ToolConfig rename** — the current `AgentConfig` is renamed to `ToolConfig` to accurately reflect that it manages tool stacks (claude, copilot, cursor), not agent personas.
6. **CLI profile management** — `spec-kitty agents profile list|show|create|edit` commands for managing agent profiles.

### Terminology Correction

Per the project glossary and the language-first architecture approach:

| Current Term | New Term | Refers To |
|---|---|---|
| `AgentConfig` | `ToolConfig` | Which tool stacks are available (claude, copilot, cursor) and selection strategy |
| `agent` (in config.yaml) | `tool` (in config.yaml) | The IDE/CLI integration, not the behavioral persona |
| *(new)* | `AgentProfile` | The behavioral identity: purpose, specialization, collaboration contract, reasoning modes |
| *(new)* | `Agent` | A personification concept for an agentic system operating within constraints and preconfigured bounds |

### Design Source

The doctrine reference repository (`doctrine_ref/`) provides the canonical design:

- **Agent profile template**: `templates/automation/NEW_SPECIALIST.agent.md` — 6-section structure
- **Concrete profiles**: `agents/*.agent.md` (21 profiles: architect, python-pedro, curator, etc.)
- **DDR-011**: Agent Specialization Hierarchy — parent-child inheritance, routing algorithm, workload balancing
- **Directive 005**: Agent Profiles — role specializations and loading patterns
- **Directive 009**: Role Capabilities — canonical verbs per specialist, conflict prevention
- **Directive 007**: Agent Declaration — formal acknowledgment of authority and operational constraints

### Package Architecture

```
src/
├── doctrine/                          # NEW: Separate top-level package
│   ├── __init__.py
│   ├── agents/                        # Reference agent profiles (shipped)
│   │   ├── architect.agent.yaml
│   │   ├── implementer.agent.yaml
│   │   ├── reviewer.agent.yaml
│   │   ├── planner.agent.yaml
│   │   └── ...
│   ├── model/                         # Domain model
│   │   ├── __init__.py
│   │   ├── profile.py                 # AgentProfile entity, value objects
│   │   ├── hierarchy.py               # SpecializationHierarchy, parent-child
│   │   └── capabilities.py            # RoleCapabilities, canonical verbs
│   ├── repository/                    # Repository services
│   │   ├── __init__.py
│   │   └── profile_repository.py      # AgentProfileRepository
│   └── tactics/                       # Reference tactics (future)
│       └── ...
├── specify_cli/
│   ├── orchestrator/
│   │   ├── agent_config.py            # RENAMED → tool_config.py
│   │   └── ...
│   └── cli/commands/
│       └── agents/
│           └── profile.py             # CLI: spec-kitty agents profile ...
```

**2.x baseline**: `src/specify_cli/orchestrator/agent_config.py` (AgentConfig with available tool list, SelectionStrategy, preferred_implementer/reviewer), `.kittify/config.yaml` (agents.available list), `doctrine_ref/` (external reference repository with 21 agent profiles, approaches, tactics, directives).

## User Scenarios & Testing

### User Story 1 — Load and Query Agent Profiles (Priority: P1)

As a spec-kitty operator, I want to load all available agent profiles (shipped defaults + project customizations) through a single repository service, so that the orchestrator, governance system, and routing provider can query agent capabilities and specializations.

**Why this priority**: The profile repository is the foundation that all consumers depend on. Without loadable profiles, nothing downstream can reference agent identities.

**Independent Test**: Initialize a project with default profiles. Create a custom profile override in `.kittify/constitution/agents/`. Call `AgentProfileRepository.list_all()`. Verify shipped profiles load, the custom override merges correctly, and profiles are queryable by role, specialization, and hierarchy position.

**Acceptance Scenarios**:

1. **Given** a freshly initialized project with no custom profiles, **When** the repository loads profiles, **Then** all shipped reference profiles from `src/doctrine/agents/` are available
2. **Given** a project with a custom profile in `.kittify/constitution/agents/architect.agent.yaml`, **When** the repository loads profiles, **Then** the custom profile overrides the shipped architect profile (field-level merge, custom wins)
3. **Given** a project with a new custom profile `security-specialist.agent.yaml` in `.kittify/constitution/agents/`, **When** the repository loads profiles, **Then** the new profile is available alongside shipped profiles
4. **Given** loaded profiles, **When** querying `repository.find_by_role("implementer")`, **Then** all profiles with role "implementer" (including specialists) are returned

#### Functional Requirements

- **FR-1.1**: The system SHALL provide an `AgentProfileRepository` that loads profiles from two sources: shipped reference profiles (`src/doctrine/agents/`) and project-level profiles (`.kittify/constitution/agents/`).
- **FR-1.2**: Project-level profiles SHALL override shipped profiles with matching profile IDs (field-level merge, project values win).
- **FR-1.3**: Project-level profiles with new IDs (not matching any shipped profile) SHALL be added to the available profile set.
- **FR-1.4**: The repository SHALL support queries: `list_all()`, `get(profile_id)`, `find_by_role(role)`, `find_by_specialization(context)`, `get_hierarchy()`.
- **FR-1.5**: Profile loading SHALL complete in under 200ms for up to 50 profiles (no AI agent invocation — pure YAML parsing).
- **FR-1.6**: Invalid YAML in a profile file SHALL log a warning and skip that profile, not halt loading.

---

### User Story 2 — AgentProfile Entity with 6-Section Structure (Priority: P1)

As a spec-kitty developer, I want a well-defined AgentProfile domain entity with the 6-section structure from the doctrine framework, so that profiles are consistent, validatable, and self-documenting.

**Why this priority**: Equally critical — the entity definition IS the domain model. Without it, the repository has nothing to load, and consumers have nothing to query.

**Independent Test**: Create an AgentProfile instance programmatically with all 6 sections populated. Serialize to YAML. Deserialize back. Verify round-trip fidelity. Validate that required fields reject None values.

**Acceptance Scenarios**:

1. **Given** a YAML file following the agent profile schema, **When** parsed into an AgentProfile instance, **Then** all 6 sections are populated as typed value objects
2. **Given** an AgentProfile instance, **When** serialized to YAML, **Then** the output is human-readable and re-parseable with identical values
3. **Given** a YAML file missing the required "purpose" section, **When** parsed, **Then** a validation error is raised with a clear message identifying the missing section
4. **Given** a profile with `specializes_from: backend-dev`, **When** the parent profile exists, **Then** the child inherits the parent's collaboration contract defaults (overridable per field)

#### Functional Requirements

- **FR-2.1**: The `AgentProfile` entity SHALL include these sections, following the doctrine template structure:
  - **Frontmatter** (YAML metadata): `profile_id`, `name`, `description`, `capabilities` (list — allowed actions/tools this agent can use, e.g., read, write, bash, browse), `specializes_from` (optional parent ID), `routing_priority` (0-100, default 50), `max_concurrent_tasks` (positive int), `specialization_context` (optional)
  - **Section 1 — Context Sources**: Which doctrine layers and directives this agent loads
  - **Section 2 — Purpose**: 2-3 line mandate — what the agent exists to do and not do
  - **Section 3 — Specialization**: `primary_focus`, `secondary_awareness`, `avoidance_boundary`, `success_definition`
  - **Section 4 — Collaboration Contract**: `handoff_to` (list), `handoff_from` (list), `works_with` (list), `output_artifacts` (list), `operating_procedures` (list), `canonical_verbs` (list of allowed action verbs)
  - **Section 5 — Mode Defaults**: Available reasoning modes with descriptions and use cases
  - **Section 6 — Initialization Declaration**: Template text for agent startup acknowledgment
- **FR-2.2**: `SpecializationContext` SHALL be a value object with optional fields: `languages` (list), `frameworks` (list), `file_patterns` (list of glob patterns), `domain_keywords` (list), `writing_style` (list), `complexity_preference` (list of low/medium/high).
- **FR-2.3**: Required fields SHALL be: `profile_id`, `name`, `purpose`, `specialization` (at minimum `primary_focus`). All other fields SHALL have sensible defaults.
- **FR-2.4**: The `AgentProfile` entity SHALL be a dataclass (or Pydantic model) in `src/doctrine/model/profile.py`.
- **FR-2.5**: Profiles SHALL support a `role` field with values from a controlled vocabulary: `implementer`, `reviewer`, `architect`, `planner`, `researcher`, `curator`, `manager`, or custom roles.
- **FR-2.6**: The profile schema SHALL be versioned (field `schema_version` in frontmatter) to support future migrations.

---

### User Story 3 — Specialization Hierarchy (Priority: P1)

As the spec-kitty orchestrator, when selecting an agent for a task, I want to traverse a specialization hierarchy where specialist agents inherit from and refine generalist agents, so that the most appropriate agent is selected based on task context.

**Why this priority**: The hierarchy is what makes profiles more than flat configuration — it enables intelligent routing and fallback. Critical for multi-agent orchestration.

**Independent Test**: Define a hierarchy: `backend-dev` (parent, priority 50) → `python-pedro` (child, priority 80). Query for a Python task. Verify `python-pedro` is preferred. Simulate `python-pedro` overloaded. Verify fallback to `backend-dev`.

**Acceptance Scenarios**:

1. **Given** profiles where `python-pedro` declares `specializes_from: backend-dev`, **When** building the hierarchy, **Then** `python-pedro` is a child of `backend-dev` with inherited collaboration contract defaults
2. **Given** a task with context `{language: python, framework: fastapi}`, **When** querying `hierarchy.find_best_match(context)`, **Then** `python-pedro` (priority 80, language match) is returned over `backend-dev` (priority 50)
3. **Given** `python-pedro` with `max_concurrent_tasks: 5` and 5 active tasks, **When** querying for a Python task, **Then** `backend-dev` is returned (workload fallback)
4. **Given** a profile declaring `specializes_from: nonexistent-agent`, **When** building the hierarchy, **Then** a validation warning is logged and the profile is treated as a root (no parent)
5. **Given** profiles forming a circular hierarchy (A → B → A), **When** building the hierarchy, **Then** a validation error is raised identifying the cycle

#### Functional Requirements

- **FR-3.1**: The `SpecializationHierarchy` SHALL model parent-child relationships between profiles, derived from the `specializes_from` field.
- **FR-3.2**: Child profiles SHALL inherit their parent's collaboration contract, mode defaults, and context sources. Child-level values override inherited values per field.
- **FR-3.3**: The hierarchy SHALL support `find_best_match(task_context)` using weighted context matching: language 40%, framework 20%, file patterns 20%, domain keywords 10%, exact match 10% (per DDR-011).
- **FR-3.4**: Routing priority SHALL be a numeric score (0-100): parents default to 50, specialists typically 60-90.
- **FR-3.5**: Workload awareness SHALL apply penalties: 0-2 active tasks = no penalty, 3-4 = 15% penalty, 5+ = 30% penalty. When a specialist is overloaded, the system falls back to the parent.
- **FR-3.6**: Complexity adjustment SHALL apply: low complexity = specialist +10%, medium = neutral, high complexity = parent +10%, specialist -10%.
- **FR-3.7**: The hierarchy builder SHALL validate: no circular dependencies, all `specializes_from` references resolve, no duplicate `profile_id` values.
- **FR-3.8**: The hierarchy SHALL be representable as a tree for display purposes (`spec-kitty agents profile hierarchy` command).

---

### User Story 4 — ToolConfig Rename and Backward Compatibility (Priority: P2)

As a spec-kitty maintainer, I want the current `AgentConfig` renamed to `ToolConfig` to accurately reflect that it manages tool stacks (not agent personas), while maintaining backward compatibility for existing projects' `config.yaml` files.

**Why this priority**: Terminology correction is important for conceptual clarity but is not a functional blocker. Existing projects must not break.

**Independent Test**: Upgrade a project with existing `config.yaml` containing `agents: {available: [claude, codex]}`. Verify the system reads the old format. Verify new projects use `tools:` key. Verify the AgentProfile model is independent of ToolConfig.

**Acceptance Scenarios**:

1. **Given** an existing `config.yaml` with `agents: {available: [claude]}`, **When** loading config after upgrade, **Then** the system reads the legacy key and returns a valid `ToolConfig`
2. **Given** a new project, **When** `spec-kitty init` creates `config.yaml`, **Then** the key is `tools:` (not `agents:`)
3. **Given** both `agents:` and `tools:` keys present in `config.yaml`, **When** loading config, **Then** `tools:` takes precedence with a deprecation warning about `agents:`

#### Functional Requirements

- **FR-4.1**: The system SHALL rename `AgentConfig` to `ToolConfig` and `agent_config.py` to `tool_config.py` in `src/specify_cli/orchestrator/`.
- **FR-4.2**: The system SHALL maintain backward compatibility by reading the `agents:` key from `config.yaml` when the `tools:` key is absent.
- **FR-4.3**: When reading legacy `agents:` key, the system SHALL log a deprecation notice recommending migration to `tools:`.
- **FR-4.4**: The `SelectionStrategy`, `preferred_implementer`, and `preferred_reviewer` fields SHALL remain on `ToolConfig` — they select tools, not agent personas.
- **FR-4.5**: All internal references to `AgentConfig` SHALL be updated to `ToolConfig`. The public API SHALL re-export `AgentConfig` as a deprecated alias during a transition period.

---

### User Story 5 — CLI Profile Management (Priority: P2)

As a project owner, I want CLI commands to list, inspect, create, and edit agent profiles, so that I can manage my project's agent configuration without manually editing YAML files.

**Why this priority**: CLI management improves usability but is not required for the domain model to function. Profiles can be managed via file editing initially.

**Independent Test**: Run `spec-kitty agents profile list`. Verify all shipped and custom profiles are displayed with name, role, and hierarchy position. Run `spec-kitty agents profile show architect`. Verify full profile details are displayed. Run `spec-kitty agents profile create`. Verify interactive or template-based profile creation in `.kittify/constitution/agents/`.

**Acceptance Scenarios**:

1. **Given** shipped and custom profiles loaded, **When** running `spec-kitty agents profile list`, **Then** a formatted table shows: profile_id, name, role, parent, routing_priority, source (shipped/custom)
2. **Given** a profile `architect`, **When** running `spec-kitty agents profile show architect`, **Then** the full 6-section profile is displayed in formatted output
3. **Given** no custom profiles, **When** running `spec-kitty agents profile create --from-template implementer`, **Then** a new profile YAML is created in `.kittify/constitution/agents/` based on the shipped implementer template
4. **Given** a custom profile exists, **When** running `spec-kitty agents profile edit my-specialist`, **Then** the profile file is opened or its fields are interactively editable
5. **Given** profiles loaded, **When** running `spec-kitty agents profile hierarchy`, **Then** a tree visualization of the specialization hierarchy is displayed

#### Functional Requirements

- **FR-5.1**: The system SHALL provide `spec-kitty agents profile` command group with subcommands: `list`, `show`, `create`, `edit`, `hierarchy`.
- **FR-5.2**: `list` SHALL display a Rich-formatted table with columns: ID, Name, Role, Parent, Priority, Source (shipped/custom/override).
- **FR-5.3**: `show <profile_id>` SHALL display the full profile in formatted Markdown or structured output.
- **FR-5.4**: `create` SHALL support `--from-template <profile_id>` to clone an existing profile as a starting point, writing to `.kittify/constitution/agents/`.
- **FR-5.5**: `create` SHALL support `--interactive` mode that prompts for each section.
- **FR-5.6**: `hierarchy` SHALL display a tree visualization using Rich's Tree component showing parent-child relationships with routing priorities.
- **FR-5.7**: All profile mutations SHALL validate the resulting profile against the schema before writing.

---

### User Story 6 — Shipped Reference Profile Catalog (Priority: P2)

As a spec-kitty user, I want spec-kitty to ship with a catalog of well-crafted reference profiles covering common development roles, so that projects have useful defaults without requiring manual profile creation.

**Why this priority**: Reference profiles provide immediate value — users get intelligent agent behavior out of the box. But the domain model (US1-3) must exist first to define what profiles contain.

**Independent Test**: Install spec-kitty. Verify `src/doctrine/agents/` contains at minimum: architect, implementer, reviewer, planner. Load each profile. Verify it passes schema validation and all required fields are populated with meaningful content.

**Acceptance Scenarios**:

1. **Given** a fresh spec-kitty installation, **When** listing profiles, **Then** at minimum these roles are represented: architect, implementer, reviewer, planner
2. **Given** the shipped architect profile, **When** inspecting its specialization, **Then** it includes: primary_focus (system decomposition, ADRs), avoidance_boundary (coding-level specifics), and collaboration handoffs (to planner, from analyst)
3. **Given** the shipped implementer profile, **When** inspecting its specialization_context, **Then** it includes language-agnostic defaults that can be specialized by child profiles (e.g., python-implementer)
4. **Given** all shipped profiles, **When** building the hierarchy, **Then** a valid tree is formed with no orphaned children or circular references

#### Functional Requirements

- **FR-6.1**: Spec-kitty SHALL ship with reference profiles in `src/doctrine/agents/` covering at minimum: `architect`, `implementer`, `reviewer`, `planner`, `researcher`, `curator`.
- **FR-6.2**: Each shipped profile SHALL be a valid YAML file following the AgentProfile schema with all 6 sections populated.
- **FR-6.3**: Shipped profiles SHALL form a coherent specialization hierarchy (e.g., `python-implementer` specializes `implementer`).
- **FR-6.4**: Shipped profiles SHALL include directive references as a table mapping directive codes to usage rationale (per doctrine pattern).
- **FR-6.5**: Shipped profiles SHALL be loadable without any project-level configuration — they are the defaults.
- **FR-6.6**: The shipped profile catalog SHALL be derived from the doctrine reference repository (`doctrine_ref/agents/`) adapted to the spec-kitty YAML format.

---

### Edge Cases

- What happens when a profile references a directive that doesn't exist in the shipped doctrine? The directive reference is stored as metadata — the profile remains valid. Governance (044) validates directive availability at hook time, not at profile load time.
- What happens when two custom profiles claim the same `profile_id`? Last-write-wins with a warning. The repository loads files alphabetically; a duplicate ID in a later file overrides the earlier one.
- What happens when a shipped profile is updated in a new spec-kitty version but the user has a custom override? The custom override wins (field-level merge). If the user wants the new shipped values, they can delete their custom override or use `spec-kitty agents profile reset <id>`.
- What happens when no profiles exist (clean install, no `src/doctrine/agents/`)? The repository returns an empty set. The system operates in profile-less mode (backward compatible with current behavior). A warning is logged.
- How does this interact with the existing `config.yaml` agent selection? `ToolConfig` (renamed from AgentConfig) selects which tool stacks are available. `AgentProfile` defines behavioral identity. They are orthogonal — a tool (claude) can operate as any agent profile (architect, implementer). The routing provider (046) maps profiles to tools.

## Requirements

### Functional Requirements

#### Domain Model (`src/doctrine/`)

- **FR-001**: The system SHALL provide a new top-level Python package `src/doctrine/` containing the AgentProfile domain model, reference profiles, and repository service.
- **FR-002**: The `doctrine` package SHALL be importable independently of `specify_cli` (no circular dependencies).
- **FR-003**: The `AgentProfile` entity SHALL be defined in `src/doctrine/model/profile.py` as a dataclass or Pydantic model.
- **FR-004**: The `SpecializationHierarchy` SHALL be defined in `src/doctrine/model/hierarchy.py` with tree-building, cycle detection, and context-matching logic.
- **FR-005**: The `RoleCapabilities` value object SHALL be defined in `src/doctrine/model/capabilities.py` mapping canonical verbs to roles with conflict detection.
- **FR-006**: The `AgentProfileRepository` SHALL be defined in `src/doctrine/repository/profile_repository.py` with two-source loading (shipped + project).

#### Profile Schema

- **FR-007**: Agent profile YAML files SHALL use the extension `.agent.yaml`.
- **FR-008**: The profile schema SHALL include a `schema_version` field (initial value: "1.0") for future migration support.
- **FR-009**: The profile schema SHALL be documented in a JSON Schema or equivalent format for validation.

#### Storage and Loading

- **FR-010**: Shipped reference profiles SHALL be stored in `src/doctrine/agents/` and included in the Python package distribution.
- **FR-011**: Project-level profiles SHALL be stored in `.kittify/constitution/agents/`.
- **FR-012**: The repository SHALL load shipped profiles first, then apply project-level overrides/additions.
- **FR-013**: Profile loading SHALL be deterministic — same files always produce same loaded state.

#### ToolConfig Migration

- **FR-014**: The system SHALL rename `AgentConfig` to `ToolConfig` across the codebase.
- **FR-015**: The system SHALL maintain backward compatibility for `config.yaml` files using the `agents:` key.
- **FR-016**: A deprecation alias `AgentConfig = ToolConfig` SHALL be provided during the transition period.

### Key Entities

- **AgentProfile**: The central domain entity. A behavioral identity for an agentic system: purpose, specialization, collaboration contract, reasoning modes, directive adherence. Identified by `profile_id`. Storable as `.agent.yaml` files.
- **SpecializationContext**: Value object defining when a specialist is preferred: languages, frameworks, file patterns, domain keywords, writing style, complexity preference.
- **SpecializationHierarchy**: Aggregate modeling the parent-child tree of agent profiles with routing priority, workload awareness, and complexity adjustments.
- **RoleCapabilities**: Value object mapping canonical action verbs (audit, synthesize, generate, refine, translate, plan, automate) to agent roles with conflict prevention rules.
- **CollaborationContract**: Value object defining handoff patterns (to/from/with), output artifacts, operating procedures, and escalation rules.
- **AgentProfileRepository**: Repository service providing two-source loading (shipped + project), merge semantics, and query methods.
- **ToolConfig**: Renamed from AgentConfig. Manages tool stack availability (claude, copilot, cursor) and selection strategy. Orthogonal to AgentProfile.

## Success Criteria

### Measurable Outcomes

- **SC-001**: All shipped reference profiles pass schema validation and load in under 200ms on a project with up to 50 profiles.
- **SC-002**: The specialization hierarchy correctly routes tasks to the most appropriate agent with at least 90% accuracy on a test suite of 20 task-context scenarios.
- **SC-003**: Projects with existing `config.yaml` using `agents:` key continue to work after the ToolConfig rename with zero configuration changes.
- **SC-004**: The `doctrine` package has zero import dependencies on `specify_cli` (verified by import analysis).
- **SC-005**: A new project can list, inspect, and create custom profiles using only CLI commands within 2 minutes.
- **SC-006**: Profile override merge semantics are deterministic — loading the same shipped + custom files always produces identical repository state.

## Scope Boundaries

### In Scope

- `AgentProfile` domain entity with 6-section structure
- `SpecializationHierarchy` with parent-child inheritance, context matching, workload and complexity adjustments
- `AgentProfileRepository` with two-source loading and merge semantics
- New `src/doctrine/` top-level package
- Shipped reference profile catalog (architect, implementer, reviewer, planner, researcher, curator + language specialists)
- `ToolConfig` rename from `AgentConfig` with backward compatibility
- CLI profile management (`spec-kitty agents profile list|show|create|edit|hierarchy`)
- Profile YAML schema with versioning

### Out of Scope

- Governance hooks and rule evaluation — owned by Feature 044
- Model routing and fallback chains — owned by Feature 046
- Constitution parsing and YAML extraction — owned by Feature 045
- Bootstrap profile selection interview — owned by Feature 042
- Tactics and directives as loadable entities (future — `src/doctrine/tactics/` and `src/doctrine/directives/` are placeholders)
- Agent-to-agent runtime communication or task delegation
- Profile versioning history (git handles this)
- Visual profile editor or dashboard integration

## Dependencies

- **Feature 045** (Constitution Sync) — profiles stored in `.kittify/constitution/agents/` are part of the constitution directory managed by 045. 045 may need an additional WP to handle profile YAML files alongside `agents.yaml`.
- **Feature 044** (Governance + Doctrine Provider) — consumes profiles for agent-task validation at governance hooks. 044's planning phase should reference the profile model from this spec.
- **Feature 046** (Routing Provider) — consumes the specialization hierarchy and context matching for model-level routing decisions. 046's routing profiles should align with agent profiles.
- **Feature 042** (Bootstrap) — bootstrap's agent profile selection phase (US4) presents and configures profiles defined by this spec.

## Glossary Alignment

| Term | Definition (per project glossary) |
|------|-----------------------------------|
| **Agent** | A personification concept for an agentic system operating within constraints and preconfigured bounds (agent profiles). Not to be confused with "tool" (the IDE/CLI integration). |
| **Agent Profile** | A structured YAML document defining an agent's behavioral identity: purpose, specialization, collaboration contract, reasoning modes, and directive adherence. The canonical domain entity introduced by this spec. |
| **Tool** | An IDE or CLI integration (claude, copilot, cursor, codex, etc.) that provides the execution environment for an agent. Managed by ToolConfig. |
| **ToolConfig** | Configuration managing which tool stacks are available and how they are selected. Renamed from AgentConfig to correct terminology conflation. |
| **Specialization Hierarchy** | Parent-child tree where specialist agents refine a generalist's scope. Enables intelligent routing with workload fallback. |
| **Specialization Context** | Declarative conditions (languages, frameworks, file patterns, domain keywords) defining when a specialist is preferred over its parent. |
| **Collaboration Contract** | The section of an agent profile defining how it interacts with other agents: handoff patterns, output artifacts, operating procedures, canonical verbs. |
| **Routing Priority** | Numeric score (0-100) determining agent preference when multiple profiles match a task context. Parents default to 50, specialists 60-90. |
| **Canonical Verbs** | The allowed action verbs for a role (audit, synthesize, generate, refine, translate, plan, automate) preventing scope creep and role overlap. |
| **Capabilities** | The list of allowed actions or tools an agent profile can use (e.g., read, write, bash, browse). Distinct from "Tool" (the IDE/CLI integration) — capabilities describe what an agent is permitted to do, not which vendor runtime it runs on. |
| **Reference Profile** | A shipped agent profile in `src/doctrine/agents/` providing defaults. Overridable by project-level profiles. |
