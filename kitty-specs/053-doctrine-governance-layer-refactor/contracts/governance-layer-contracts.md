# Contracts: Governance Layer Model

## Scope

Contract definitions for governance-layer behavior used by feature `053-doctrine-governance-layer-refactor`.

## Referenced Architecture Artifacts

- ADR: `architecture/adrs/2026-02-17-1-explicit-governance-layer-model.md`
- Journey: `architecture/journeys/004-curating-external-practice-into-governance.md`
- Diagram: `architecture/diagrams/explicit-governance-layer-model.puml`

## Contract 1: Mission-Orchestration Boundary

- Mission MUST define orchestration semantics only:
  - states
  - transitions
  - guards
  - required artifacts
- Mission MUST NOT be the source of project-specific governance activation.

## Contract 2: Constitution Activation Authority

- Constitution MUST be the project-level authority for selecting/activating:
  - paradigms
  - directives
  - selected agent profiles
  - available tools
- Runtime governance resolution MUST read constitution selection first.
- Template set selection MAY be omitted in constitution; runtime MAY apply mission-compatible fallback defaults.

## Contract 3: Directive-to-Tactic Invocation

- Active directives MAY invoke tactics.
- If a referenced tactic is missing, validation MUST fail before runtime execution.

## Contract 4: Curation Candidate Traceability

- External practices MUST enter via an import candidate record with:
  - source provenance
  - classification target
  - adaptation notes
  - status
- Candidate adoption MUST produce explicit links to resulting doctrine artifacts.

## Contract 5: Schema Validation Gate

- Governance and curation artifacts MUST pass schema validation in tests/CI.
- Invalid artifacts MUST block activation.
- MVP schema scope for this feature is limited to:
  - mission
  - directive
  - tactic
  - import candidate
  - agent profile
- Template-set and constitution-selection schema contracts are deferred to future refinement features.

## Compliance Hints

- See glossary canonical terms in `glossary/contexts/governance.md` and `glossary/contexts/orchestration.md`.
- Keep these contracts implementation-agnostic; enforce details in schema/tests.
