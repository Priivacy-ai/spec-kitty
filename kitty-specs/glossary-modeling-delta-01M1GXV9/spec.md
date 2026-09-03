# Specification: Strengthen Glossary Skills with Model Validation

**Branch**: `codex/glossary-modeling-delta`
**Created**: 2026-09-02
**Status**: Draft
**Request**: add three useful mechanisms from `domain-modeling` to the existing glossary workflow without importing the external skill wholesale.

## User Scenarios and Validation

### Scenario 1 - Cross-Check the Model Against Real Code (P1)

As a domain-model author or reviewer, I want the agent to validate material claims about terms and relationships against available code so that a plausible but false model is not recorded.

**Why P1**: this is the primary guard against semantic drift between documentation and system behavior.

**Independent validation**: give the agent a model description that contradicts names or relationships in code; the result must identify the mismatch and name the inspected surface.

**Acceptance criteria**:

1. **Given** a claim about a term or relationship and available code, **when** the agent refines the model, **then** it checks the claim against relevant types, APIs, or tests before recording a conclusion.
2. **Given** a contradiction between the model and code, **when** the check is complete, **then** the agent does not call the model confirmed and states the concrete mismatch.

### Scenario 2 - Challenge a Term with a Concrete Edge Case (P2)

As a participant in a modeling discussion, I want to test vague terms against one concrete edge scenario so that I can see whether the definition explains real behavior.

**Why P2**: one well-chosen example exposes hidden ambiguity faster than expanding an abstract description.

**Independent validation**: give the agent a vague term such as `status` or `manager`; the result must include a concrete scenario, expected behavior, and a refined definition when ambiguity is found.

**Acceptance criteria**:

1. **Given** an ambiguous or overloaded concept, **when** the agent makes a recommendation, **then** it challenges the concept with at least one concrete edge scenario.
2. **Given** a mismatch between the definition and scenario behavior, **when** the check is complete, **then** the agent refines the term, boundary, or relationship instead of masking the mismatch with more jargon.

### Scenario 3 - Avoid Unnecessary ADRs (P3)

As a project maintainer, I want ADR recommendations only for genuinely consequential decisions so that the decision log remains useful.

**Why P3**: this limits documentation noise without preventing durable decisions from being recorded.

**Independent validation**: evaluate three decisions that each fail one ADR condition; none should receive an ADR recommendation. A decision that passes all three conditions should receive one with a brief rationale.

**Acceptance criteria**:

1. **Given** a decision that is not simultaneously hard to reverse, surprising without context, and subject to a real trade-off, **when** the agent chooses where to record it, **then** it keeps the rationale in the glossary, spec, or plan and does not recommend an ADR.
2. **Given** a decision that passes all three conditions, **when** the agent chooses where to record it, **then** it recommends an ADR and names the conditions that passed.

### Edge Cases

- When code is absent or unavailable, the agent labels the conclusion as an unverified hypothesis and does not invent evidence.
- When a term is already unambiguously defined by the canonical glossary and causes no conflict, the agent need not invent an artificial edge scenario.
- When an ADR already exists, the agent updates or references it instead of creating a duplicate.
- When a change only adjusts local wording without an architectural choice, the ADR gate returns a negative result.

## Requirements

### Functional Requirements

| ID | Name | Requirement | Priority | Status |
|----|------|-------------|----------|--------|
| FR-001 | Model-check routing | The public glossary skill routes domain-model refinement requests to the existing detailed workflow. | High | Open |
| FR-002 | Code cross-check | The detailed workflow requires material claims to be checked against available types, APIs, and tests and requires mismatches to be reported. | High | Open |
| FR-003 | Concrete scenario | The detailed workflow requires an ambiguous term to be challenged with at least one concrete edge scenario. | High | Open |
| FR-004 | Three-condition ADR gate | Recommend an ADR only when the decision is hard to reverse, surprising without context, and involves a real trade-off. | Medium | Open |
| FR-005 | Honest uncertainty | When code or evidence is unavailable, the agent labels the conclusion as a hypothesis. | High | Open |
| FR-006 | Preserve the workflow | The new checks extend canonical work with terms, aliases, conflicts, and semantic drift without creating a parallel process. | High | Open |

### Non-Functional Requirements

| ID | Name | Requirement | Category | Priority | Status |
|----|------|-------------|----------|----------|--------|
| NFR-001 | Narrow diff | The product change touches at most two existing `SKILL.md` files; it adds no new skill or runtime module. | Maintainability | High | Open |
| NFR-002 | Verifiability | All three behavioral scenarios pass, and removing any one mechanism causes its corresponding check to fail meaningfully. | Reliability | High | Open |
| NFR-003 | Compatibility | Existing doctrine skill-pack tests and both modified-skill validators pass. | Compatibility | High | Open |

### Constraints

| ID | Name | Constraint | Category | Priority | Status |
|----|------|------------|----------|----------|--------|
| C-001 | One source of truth | Modify only the canonical repository source; do not edit the installed global projection. | Technical | High | Open |
| C-002 | No external structure | Do not add `CONTEXT.md`, `CONTEXT-MAP.md`, a separate glossary store, or the full external `domain-modeling` workflow. | Scope | High | Open |
| C-003 | No runtime scope | Do not modify the runtime glossary, ADR templates, CLI, registry, or public skill-pack composition. | Scope | High | Open |
| C-004 | Separate delivery gate | Installation/projection of the updated skill remains a separate action after review and merge. | Delivery | Medium | Open |

### Key Entities

- **Domain term**: a canonical name, definition, applicability boundary, and aliases.
- **Model claim**: a verifiable relationship among terms, behavior, and code.
- **Edge scenario**: a concrete situation capable of confirming or disproving a definition's precision.
- **Architectural decision**: a choice among real alternatives evaluated against the three ADR conditions.

## Success Criteria

- **SC-001**: 3 of 3 behavioral checks demonstrate the required agent response.
- **SC-002**: validators accept both modified `SKILL.md` files.
- **SC-003**: the targeted doctrine skill-pack test passes without regressions.
- **SC-004**: the diff adds no new skill, runtime code, glossary store, or ADR template.
