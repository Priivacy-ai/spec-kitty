# User Journey: Curating External Practice into Governance

**Status**: DRAFT
**Date**: 2026-02-17
**Primary Contexts**: Governance, Curation, Constitution
**Supporting Contexts**: Orchestration, Agent Profiles, Tool Selection
**Related ADR**: [2026-02-17-1-explicit-governance-layer-model](../adrs/2026-02-17-1-explicit-governance-layer-model.md)

---

## Scenario

A lead developer discovers an external practice (for example, ZOMBIES TDD) and wants it to become standard behavior for implementation agents in their Spec Kitty project.

The system should support this as a pull-based flow:

1. capture the external idea as a curated candidate,
2. adapt and classify it into Spec Kitty doctrine concepts,
3. activate it through constitution-level governance selection,
4. and reflect it in implementation behavior.

---

## Actors

| # | Actor | Type | Role in Journey |
|---|-------|------|-----------------|
| 1 | Lead Developer | `human` | Identifies external practice and approves adoption |
| 2 | AI Agent | `llm` | Performs curation analysis and proposes doctrine mapping |
| 3 | Spec-Kitty CLI | `system` | Stores curation artifacts, updates governance artifacts, validates schemas |

---

## Preconditions

1. Project has `doctrine/` structure initialized.
2. Constitution exists and is project authority for governance selection.
3. Schema validation tests are available in `tests/`.
4. Lead developer has identified an external source to curate.

---

## Journey Map

| Phase | Actor(s) | System | Key Events |
|-------|----------|--------|------------|
| 1. Candidate Capture | Lead Developer ↔ AI Agent | Create import candidate record with source/provenance | `ImportCandidateCreated` |
| 2. Classification | AI Agent | Map external idea to target concept (paradigm/directive/tactic/template) | `ImportCandidateClassified` |
| 3. Adaptation | AI Agent ↔ Lead Developer | Propose adapted wording and constraints for Spec Kitty canon | `ImportCandidateAdapted` |
| 4. Governance Integration | AI Agent | Add/update doctrine artifacts and profile defaults | `GovernanceArtifactsUpdated` |
| 5. Constitution Selection | Lead Developer ↔ AI Agent | Activate selected doctrine assets and profile/tool scope in constitution | `ConstitutionSelectionsUpdated` |
| 6. Validation | Spec-Kitty CLI | Run schema and consistency validation in tests/CI | `GovernanceValidationPassed` |
| 7. Operational Use | AI Agent | Implementation runs with newly activated behavior | `BehaviorActivatedForImplementation` |

---

## Coordination Rules

1. External practices are never adopted directly; they must enter through `ImportCandidate`.
2. Classification and adaptation must be explicit before activation.
3. Constitution is the only project-level authority for activation.
4. Schema validation must pass before behavior is considered active.
5. If adaptation is ambiguous, stop and request developer confirmation.

---

## Responsibilities

### Spec-Kitty CLI (Local Runtime)

1. Persist curation records and governance artifact updates.
2. Validate artifacts against schemas.
3. Expose failures as actionable QA errors.

### AI Agent (LLM Context)

1. Analyze source practice and extract applicable concepts.
2. Propose mapping and adapted doctrine representation.
3. Update mission-adjacent behavior via doctrine + constitution (not by embedding ad hoc behavior in mission text).

### Lead Developer (Human Authority)

1. Approve/reject curation mapping and adaptation.
2. Decide activation scope via constitution selections.
3. Confirm final adoption into project standards.

---

## Scope: MVP

### In Scope

1. Candidate-based curation flow for one external source at a time.
2. Mapping to at least one doctrine concept (`Paradigm` or `Directive` or `Tactic`).
3. Constitution update for selected profiles and available tools.
4. Schema validation pass/fail gate.

### Out of Scope (Deferred)

- Automatic harvesting from web/catalogs.
- Bulk multi-candidate ranking/prioritization.
- Organization-wide multi-repo rollout orchestration.

---

## Required Event Set

| # | Event | Emitted By | Phase |
|---|-------|-----------|-------|
| 1 | `ImportCandidateCreated` | AI Agent | 1 |
| 2 | `ImportCandidateClassified` | AI Agent | 2 |
| 3 | `ImportCandidateAdapted` | AI Agent | 3 |
| 4 | `GovernanceArtifactsUpdated` | AI Agent | 4 |
| 5 | `ConstitutionSelectionsUpdated` | AI Agent | 5 |
| 6 | `GovernanceValidationPassed` | CLI | 6 |
| 7 | `BehaviorActivatedForImplementation` | AI Agent | 7 |

---

## Acceptance Scenarios

1. **ZOMBIES TDD adopted as implementation behavior**
   Given a lead developer provides a ZOMBIES TDD source,
   when an import candidate is curated, classified, adapted, and approved,
   then doctrine artifacts are updated,
   and constitution selections activate the behavior for implementation profiles.

2. **Invalid artifact blocked by schema gate**
   Given a malformed curation or doctrine artifact,
   when validation runs,
   then activation is blocked and actionable validation errors are reported.

3. **Constitution authority enforced**
   Given doctrine artifacts exist but constitution selections are not updated,
   when implementation runs,
   then the new behavior is not considered active for project execution.

---

## Design Decisions

| Decision | Rationale | ADR |
|----------|-----------|-----|
| Curation is candidate-first | Preserves provenance and explicit adaptation | [2026-02-17-1](../adrs/2026-02-17-1-explicit-governance-layer-model.md) |
| Constitution is activation authority | Keeps per-project governance explicit and auditable | [2026-02-17-1](../adrs/2026-02-17-1-explicit-governance-layer-model.md) |
| Schema validation is required pre-activation | Provides early QA guardrail for governance changes | [2026-02-17-1](../adrs/2026-02-17-1-explicit-governance-layer-model.md) |

---

## Product Alignment

This journey operationalizes the governance-layer model by showing how external practices become project behavior through curation + constitution selection rather than ad hoc mission prompt edits.
