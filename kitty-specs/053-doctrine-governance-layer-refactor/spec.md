# Feature Specification: Explicit Governance Layer Refactor

**Feature Branch**: `[053-doctrine-governance-layer-refactor]`  
**Created**: 2026-02-17  
**Status**: Draft  
**Target Branch**: `develop`  
**Input**: User description: "Refactor Spec Kitty doctrine/governance model to be constitution-centric, with explicit doctrine concepts, curation flow, and schema validation."

## Related Architecture Artifacts

- ADR: `architecture/adrs/2026-02-17-1-explicit-governance-layer-model.md`
- User Journey: `architecture/journeys/004-curating-external-practice-into-governance.md`
- Diagram: `architecture/diagrams/explicit-governance-layer-model.puml`

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Activate Governance by Constitution (Priority: P1)

As a project maintainer, I want constitution-level selections to determine active doctrine behavior so mission orchestration remains stable while governance can vary per project.

**Why this priority**: This is the core architectural boundary and main reason for the refactor.

**Independent Test**: Configure two different constitution selections in two test fixtures; verify the same mission recipe resolves different active doctrine assets.

**Acceptance Scenarios**:

1. **Given** a mission definition and a constitution with selected paradigms/directives/template set, **When** governance resolution runs, **Then** active governance assets are taken from constitution, not mission inline behavior.
2. **Given** a mission with valid orchestration and no constitution selection, **When** execution starts, **Then** system reports missing governance selection or applies explicit defaults per policy.

---

### User Story 2 - Curate External Practice into Canon (Priority: P2)

As a lead developer, I want to pull an external practice (e.g., ZOMBIES TDD) into a curated candidate and adapt it into Spec Kitty doctrine terminology.

**Why this priority**: Enables controlled evolution from external knowledge sources without contaminating core doctrine.

**Independent Test**: Create an import candidate artifact from fixture source, classify/adapt it, and verify mapped doctrine artifact references are stored.

**Acceptance Scenarios**:

1. **Given** a new import candidate with source metadata, **When** it is classified as a target doctrine type, **Then** provenance, mapping, and adaptation notes are persisted.
2. **Given** an approved import candidate, **When** doctrine artifacts are generated/updated, **Then** links to resulting paradigm/directive/tactic artifacts are recorded.

---

### User Story 3 - Validate Governance Artifacts Early (Priority: P3)

As a maintainer, I want schema validation for doctrine artifacts in tests/CI so malformed governance changes fail before runtime.

**Why this priority**: Prevents drift and invalid config from entering feature workflows.

**Independent Test**: Run schema validation tests over valid and invalid fixture files; assert pass/fail behavior.

**Acceptance Scenarios**:

1. **Given** valid doctrine and curation artifacts, **When** schema tests run, **Then** all validations pass.
2. **Given** an invalid doctrine artifact, **When** schema tests run, **Then** CI fails with actionable validation errors.

---

### Edge Cases

- Constitution selects an agent profile not present in `agent-profiles/`.
- Constitution exposes available tools that are not installed or not configured.
- Import candidate classification conflicts with existing canonical terminology.
- Tactic referenced by a directive is missing.
- Template set selected by constitution is incomplete.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST represent mission as orchestration-only contract (states, transitions, guards, required artifacts).
- **FR-002**: System MUST represent constitution as the project-level selector/activator for governance assets.
- **FR-003**: System MUST support explicit doctrine artifact categories: paradigms, directives, tactics, template sets, and agent profiles.
- **FR-004**: System MUST support constitution concepts for selected agent profiles and available tools.
- **FR-005**: System MUST support pull-based curation records (`ImportCandidate`) with source provenance, target mapping, adaptation notes, and status.
- **FR-006**: System MUST provide schema definitions for doctrine/curation artifacts and validate them in automated tests.
- **FR-007**: System MUST provide an architecture ADR and diagram documenting the explicit governance layer model.
- **FR-008**: System MUST provide a user journey describing external-practice curation and constitution activation flow.
- **FR-009**: System MUST update glossary terminology to align with explicit governance layer concepts.

### Key Entities *(include if feature involves data)*

- **Mission**: Orchestration recipe (states/transitions/guards/artifact contract).
- **Constitution**: Per-project governance selector and narrowing layer.
- **Paradigm**: Conceptual framing model.
- **Directive**: Mandatory governance constraint.
- **Tactic**: Step-by-step execution procedure.
- **TemplateSet**: Bundle of artifact templates.
- **AgentProfile**: Behavioral identity with default governance.
- **ImportCandidate**: Pull-based curation record for external ideas.
- **Schema**: Validation contract for doctrine artifacts.
- **Tool**: Runtime execution surface used by orchestration.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Glossary contains canonical definitions for constitution-centric governance selection and related entities with no contradictory mission definition.
- **SC-002**: Architecture includes one ADR and one diagram that match the finalized concept map.
- **SC-003**: Architecture journeys include at least one journey for external practice curation and activation.
- **SC-004**: Governance artifact schema tests can validate at least one valid and one invalid fixture per major artifact type.
