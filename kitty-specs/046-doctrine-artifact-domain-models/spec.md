# Feature Specification: Doctrine Artifact Domain Models

**Feature Branch**: `046-doctrine-artifact-domain-models`
**Created**: 2026-02-25
**Status**: Draft
**Target Branch**: `main`
**Mission**: software-dev

## Overview

### Motivation

The doctrine package (`src/doctrine/`) contains 7 artifact types — directives, paradigms, tactics, styleguides, toolguides, template sets, and agent profiles — but only agent profiles have a Python domain model and repository service. The remaining artifact types exist as raw YAML files validated by JSON schemas, with no programmatic loading path. This means any code that needs doctrine content must write ad-hoc YAML parsing, which is fragile, duplicative, and cannot enforce schema compliance on write.

Simultaneously, the 19 shipped directives are minimal stubs (~6 lines each) that lack the behavioral depth needed to guide agent execution. The reference corpus (`doctrine_ref/directives/`) demonstrates the target richness: procedures, tactic references, integrity rules, scope definitions, and cross-references to other doctrine layers. Fleshing out the shipped directives while building the domain models ensures there is substantive content worth loading programmatically.

This feature enables the doctrine-merging initiative's core principle: **on-demand loading of additional depth**. Agents and execution code pull in exactly the governance context they need for a specific action without loading unneeded material.

### What This Feature Delivers

1. **Pydantic domain models** for each doctrine artifact type (directives, paradigms, tactics, styleguides, toolguides), following the established `agent_profiles` pattern.

2. **Repository services** for each artifact type with load (shipped + project), list, get-by-id, validate, and create/save capabilities — enabling the curation/import flow to produce schema-compliant files programmatically.

3. **A domain service** that holds references to all repositories, providing a single entry point for on-demand retrieval of any doctrine artifact by type and ID.

4. **Enriched shipped directives** — the 19 existing directive stubs expanded into substantive governance documents with behavioral context, procedures, tactic references, integrity rules, and cross-references to related doctrine artifacts. The directive schema is extended to accommodate the richer structure.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Execution Code Loads a Directive by ID (Priority: P1)

A mission step or agent profile initialization needs to load a specific directive to understand the governance rule it must follow. The code imports the directive repository, calls `get("004")`, and receives a typed `Directive` object with title, intent, enforcement level, tactic references, scope, procedures, and integrity rules.

**Why this priority**: This is the foundational use case — programmatic access to doctrine content replaces ad-hoc YAML parsing everywhere in the codebase.

**Independent Test**: Calling `DirectiveRepository().get("004")` returns a `Directive` object whose `title` matches "Test-Driven Implementation Standard" and whose `tactic_refs` list is non-empty.

**Acceptance Scenarios**:

1. **Given** the doctrine package is installed, **When** code calls `DirectiveRepository().get("004")`, **Then** a `Directive` object is returned with all schema fields populated
2. **Given** a directive ID that does not exist, **When** code calls `DirectiveRepository().get("999")`, **Then** `None` is returned
3. **Given** the repository is initialized, **When** code calls `DirectiveRepository().list_all()`, **Then** all 19 shipped directives plus `test-first` are returned as `Directive` objects

---

### User Story 2 - Execution Code Loads a Tactic by ID (Priority: P1)

A directive references tactics via `tactic_refs`. The execution code needs to load those tactic objects to understand the step-by-step procedure. The code calls `TacticRepository().get("zombies-tdd")` and receives a typed `Tactic` object with steps, references, and metadata.

**Why this priority**: Tactics are the operational layer — the step recipes that agents actually follow. Without typed loading, directive-to-tactic resolution requires manual YAML parsing.

**Independent Test**: Calling `TacticRepository().get("zombies-tdd")` returns a `Tactic` object with 7 steps.

**Acceptance Scenarios**:

1. **Given** the doctrine package is installed, **When** code calls `TacticRepository().get("zombies-tdd")`, **Then** a `Tactic` object is returned with `steps` as a list of `TacticStep` objects
2. **Given** a tactic ID that does not exist, **When** code calls `TacticRepository().get("nonexistent")`, **Then** `None` is returned

---

### User Story 3 - Domain Service Provides Unified Access (Priority: P1)

Execution code needs to load doctrine artifacts of different types without managing multiple repository instances. A `DoctrineService` provides a single entry point: `service.directives.get("004")`, `service.tactics.get("zombies-tdd")`, `service.paradigms.get("test-first")`.

**Why this priority**: The domain service is the aggregation point that makes on-demand loading practical. Without it, every consumer must instantiate and manage repositories individually.

**Independent Test**: Constructing `DoctrineService(shipped_root=Path(...))` provides access to all repositories through named attributes, and each repository returns typed objects.

**Acceptance Scenarios**:

1. **Given** a `DoctrineService` initialized with the default shipped root, **When** code accesses `service.directives.list_all()`, **Then** all shipped directives are returned
2. **Given** a `DoctrineService` initialized with a project root, **When** code accesses `service.styleguides.list_all()`, **Then** both shipped and project styleguides are returned with project overrides applied
3. **Given** the service, **When** code accesses `service.agent_profiles`, **Then** the existing `AgentProfileRepository` is returned (not a new implementation)

---

### User Story 4 - Curation Flow Creates Schema-Compliant Artifacts (Priority: P2)

The curation/import flow needs to create new doctrine artifacts (e.g., a tactic adopted from an import candidate) programmatically. Using `TacticRepository().save(tactic)` produces a valid YAML file that passes schema validation, preventing the generation of non-compliant files.

**Why this priority**: Write capability closes the loop — artifacts can be created, validated, and persisted through the same typed interface used for reading.

**Independent Test**: Creating a `Tactic` model instance and calling `repository.save(tactic)` writes a YAML file that validates against `tactic.schema.yaml`.

**Acceptance Scenarios**:

1. **Given** a valid `Tactic` model instance, **When** `repository.save(tactic)` is called, **Then** a `.tactic.yaml` file is written to the project directory
2. **Given** a `Tactic` model with missing required fields, **When** construction is attempted, **Then** Pydantic validation raises an error before any file is written
3. **Given** a `Directive` model instance, **When** `repository.save(directive)` is called, **Then** a `.directive.yaml` file is written that validates against the directive schema

---

### User Story 5 - Enriched Directives Guide Agent Behavior (Priority: P2)

An agent loading directive 014 ("Acceptance Criteria Completeness") receives not just a title and intent, but procedural guidance: when the directive applies, what steps to follow, which tactics to invoke, what integrity rules to check, and what validation criteria to meet. This enables the agent to act on the directive rather than merely acknowledge it.

**Why this priority**: The domain models are only as useful as the content they expose. Minimal stubs provide no actionable guidance. Enriching the 19 directives transforms them from labels into operational governance.

**Independent Test**: Loading directive 004 returns a `Directive` object whose `tactic_refs` contains at least one tactic ID, whose `scope` field describes applicability, and whose `procedures` field contains ordered steps.

**Acceptance Scenarios**:

1. **Given** directive 004 is loaded, **When** its `tactic_refs` field is inspected, **Then** it references `acceptance-test-first`, `tdd-red-green-refactor`, and `zombies-tdd`
2. **Given** directive 014 is loaded, **When** its content is inspected, **Then** it contains `scope`, `procedures`, and `validation_criteria` fields with substantive content drawn from the reference corpus
3. **Given** any of the 19 shipped directives, **When** loaded, **Then** the `intent` field contains more than a single sentence — it provides actionable behavioral context
4. **Given** a directive references tactic IDs in `tactic_refs`, **When** those IDs are looked up in the `TacticRepository`, **Then** each resolves to a valid `Tactic` object (cross-reference integrity)

---

### User Story 6 - Styleguide and Toolguide Models Support Governance Loading (Priority: P2)

Execution code loading an agent profile discovers directive references, which may point to styleguides or toolguides for operational detail. The code calls `service.styleguides.get("kitty-glossary-writing")` and receives a typed `Styleguide` object with scope, principles, and anti-patterns.

**Why this priority**: Completes the artifact type coverage so every doctrine layer is programmatically accessible.

**Independent Test**: `StyleguideRepository().get("kitty-glossary-writing")` returns a `Styleguide` object with `scope == "glossary"` and a non-empty `principles` list.

**Acceptance Scenarios**:

1. **Given** the doctrine package, **When** `StyleguideRepository().list_all()` is called, **Then** all shipped styleguides are returned as `Styleguide` objects
2. **Given** a toolguide ID, **When** `ToolguideRepository().get("powershell-syntax")` is called, **Then** a `Toolguide` object is returned with `guide_path` and `commands` fields
3. **Given** a `Paradigm` ID, **When** `ParadigmRepository().get("test-first")` is called, **Then** a `Paradigm` object with `name` and `summary` is returned

---

### User Story 7 - Directive Schema Supports Enriched Structure (Priority: P2)

The existing `directive.schema.yaml` must be extended to accommodate the richer content structure (scope, procedures, validation criteria, integrity rules) while remaining backward-compatible with the current minimal format. Both minimal and enriched directives validate against the updated schema.

**Why this priority**: Schema evolution must happen before or alongside directive enrichment to ensure all written files are compliant.

**Independent Test**: Both the current minimal `test-first.directive.yaml` and a new enriched directive validate against the updated schema.

**Acceptance Scenarios**:

1. **Given** the updated directive schema, **When** the existing minimal `test-first.directive.yaml` is validated, **Then** it passes (backward compatible)
2. **Given** the updated schema, **When** an enriched directive with `scope`, `procedures`, `integrity_rules`, and `validation_criteria` fields is validated, **Then** it passes
3. **Given** a directive YAML missing the required `id` field, **When** validated, **Then** it fails schema validation

---

### Edge Cases

- What happens when a shipped directive YAML is malformed? The repository skips it with a warning and continues loading valid directives (consistent with agent profile behavior).
- What happens when a project-level directive overrides a shipped directive? Field-level merge applies: project fields override shipped fields, unspecified fields fall through from shipped.
- What happens when a directive references a tactic ID that does not exist? The directive loads successfully; cross-reference integrity is a validation concern, not a loading concern.
- What happens when the doctrine service is constructed with no project root? Only shipped artifacts are loaded; save operations raise `ValueError`.
- What happens when `save()` is called for a shipped artifact type with no project directory configured? A `ValueError` is raised indicating that project_dir is not configured.

## Requirements *(mandatory)*

### Functional Requirements

**Domain Models**

- **FR-001**: System MUST provide a `Directive` Pydantic model with fields for: `id`, `schema_version`, `title`, `intent`, `tactic_refs`, `enforcement`, and optional enriched fields (`scope`, `procedures`, `integrity_rules`, `validation_criteria`)
- **FR-002**: System MUST provide a `Tactic` Pydantic model with fields for: `id`, `schema_version`, `name`, `summary`, `steps` (list of `TacticStep`), and `references`
- **FR-003**: System MUST provide a `Styleguide` Pydantic model with fields for: `id`, `schema_version`, `name`, `scope`, `principles`, and `anti_patterns`
- **FR-004**: System MUST provide a `Toolguide` Pydantic model with fields for: `id`, `schema_version`, `name`, `guide_path`, and `commands`
- **FR-005**: System MUST provide a `Paradigm` Pydantic model with fields for: `id`, `schema_version`, `name`, and `summary`
- **FR-006**: All models MUST use `pydantic.Field(alias=...)` for kebab-case YAML keys, consistent with the `AgentProfile` pattern

**Repositories**

- **FR-007**: System MUST provide repository classes (`DirectiveRepository`, `TacticRepository`, `StyleguideRepository`, `ToolguideRepository`, `ParadigmRepository`) following the `AgentProfileRepository` pattern
- **FR-008**: Each repository MUST support two-source loading (shipped package data + project filesystem) with field-level merge for overrides
- **FR-009**: Each repository MUST provide `list_all()`, `get(id)`, and `save(model)` methods
- **FR-010**: Each repository MUST skip malformed YAML files with a warning (no hard failure on individual file errors)
- **FR-011**: Repository `save()` MUST write YAML files that pass the corresponding JSON schema validation
- **FR-012**: Repository loading MUST use `importlib.resources` for shipped data resolution, with fallback to `Path(__file__).parent` for development

**Domain Service**

- **FR-013**: System MUST provide a `DoctrineService` class that holds references to all repository instances
- **FR-014**: `DoctrineService` MUST accept optional `shipped_root` and `project_root` parameters, defaulting shipped root to the package data location
- **FR-015**: `DoctrineService` MUST expose repositories as named attributes: `directives`, `tactics`, `styleguides`, `toolguides`, `paradigms`, `agent_profiles`
- **FR-016**: `DoctrineService` MUST reuse the existing `AgentProfileRepository` (not reimplement it)

**Directive Enrichment**

- **FR-017**: The directive schema (`directive.schema.yaml`) MUST be extended with optional fields: `scope`, `procedures`, `integrity_rules`, `validation_criteria`, while remaining backward-compatible with existing minimal directives
- **FR-018**: All 19 shipped directives (001-019) MUST be enriched with substantive content: at minimum `scope`, populated `tactic_refs` where applicable, and expanded `intent`
- **FR-019**: Enriched directives MUST reference existing tactics by ID in `tactic_refs` where a relevant tactic exists in `src/doctrine/tactics/`
- **FR-020**: New tactics, styleguides, or toolguides MAY be created where the `doctrine_ref` reference corpus identifies operational patterns not yet captured in the shipped doctrine
- **FR-021**: All enriched directive files MUST validate against the updated `directive.schema.yaml`
- **FR-024**: New shipped directives MUST be created for `doctrine_ref` concepts that have no corresponding shipped directive (e.g., worklog creation, prompt storage, commit protocol, traceable decisions). Each new directive follows the enriched format from the start.

**Consistency**

- **FR-022**: A consistency test MUST verify that every `tactic_ref` in every shipped directive resolves to an existing tactic file in `src/doctrine/tactics/`
- **FR-023**: All domain models MUST be importable from `doctrine.<artifact_type>` (e.g., `from doctrine.directives import Directive, DirectiveRepository`)

### Key Entities

- **Directive**: A constraint-oriented governance rule with enforcement level, tactic references, scope, procedures, and validation criteria. Identified by a string ID (e.g., `"DIRECTIVE_004"`).
- **Tactic**: A reusable behavioral execution pattern with ordered steps, references, and metadata. Identified by a kebab-case ID (e.g., `"zombies-tdd"`).
- **Styleguide**: A cross-cutting quality convention with scope, principles, and anti-patterns. Identified by a kebab-case ID.
- **Toolguide**: A tool-specific operational guide with guide path and command references. Identified by a kebab-case ID.
- **Paradigm**: A worldview-level framing with name and summary. Identified by a kebab-case ID.
- **DoctrineService**: Aggregation point holding all repository instances for on-demand retrieval.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 6 doctrine artifact types (directive, tactic, styleguide, toolguide, paradigm, agent profile) are loadable as typed Python objects through a single `DoctrineService` entry point
- **SC-002**: All shipped directives (existing 19 + newly created from `doctrine_ref` concepts) contain substantive governance content (scope, expanded intent, tactic references where applicable) — no single-sentence stubs remain
- **SC-003**: Every `tactic_ref` in every shipped directive resolves to an existing tactic file (cross-reference integrity test passes)
- **SC-004**: Creating a model instance and calling `repository.save()` produces a YAML file that passes the corresponding JSON schema validation
- **SC-005**: The existing `AgentProfileRepository` is reused by `DoctrineService` without modification to its public API
- **SC-006**: All domain model tests pass (target: 80+ tests covering models, repositories, service, schema validation, and consistency)
- **SC-007**: Both minimal (existing) and enriched directive formats validate against the updated directive schema (backward compatibility)

## Clarifications

### Session 2026-02-25

- Q: Should this feature only enrich the existing 19 shipped directives, or also create new shipped directives for `doctrine_ref` concepts not yet represented? → A: Enrich existing 19 + create new shipped directives for unrepresented `doctrine_ref` concepts.

## Assumptions

- The `doctrine` package follows the same Python 3.11+ requirement as `specify_cli`
- Cross-artifact aggregation (e.g., resolving a directive into a composite object with embedded tactic objects) is out of scope — the service provides access to individual repositories for on-demand loading
- The `doctrine_ref/` directory (gitignored) serves as reference material for enriching directives; its content is adapted, not copied verbatim
- New tactics or styleguides created during directive enrichment follow the existing schema and naming conventions
- The enriched directive schema fields are all optional to maintain backward compatibility with existing minimal directives
