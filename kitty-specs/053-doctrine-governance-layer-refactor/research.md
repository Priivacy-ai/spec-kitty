# Research: Explicit Governance Layer Refactor

## Purpose

Capture the evidence and rationale behind the constitution-centric governance model for feature `053-doctrine-governance-layer-refactor`.

## Referenced Architecture Artifacts

- ADR: `architecture/adrs/2026-02-17-1-explicit-governance-layer-model.md`
- Journey: `architecture/journeys/004-curating-external-practice-into-governance.md`
- Diagram: `architecture/diagrams/explicit-governance-layer-model.puml`

## Synthesized Findings

1. Governance selection should be project-scoped, not mission-inline. Constitution is the right authority boundary.
2. Mission should stay orchestration-focused (state/transition/guard/artifact contract).
3. Pull-based curation is preferred for external practices (candidate -> classify -> adapt -> adopt).
4. Schema validation is required as an early QA gate before runtime behavior is considered active.
5. Tool availability and selected agent profiles belong in constitution-managed configuration.

## Open Questions

1. What is the minimum schema set required for an MVP (mission, directive, tactic, import candidate, profile)?
2. Should `TemplateSet` selection be mandatory in constitution or allow mission defaults?
3. How strict should activation be when constitution references unavailable tools or missing profiles?

## Decisions (2026-02-17)

1. **TemplateSet selection**: optional, with fallback defaults.
   - Constitution is project-level governance, not mission-level.
   - If no template set is selected in constitution, mission-compatible defaults may apply.
2. **Missing profile/tool references**: hard fail.
   - Invalid constitution references must block activation.
3. **MVP schema scope**: minimal set now, based on existing artifacts.
   - Include schemas for: mission, directive, tactic, import candidate, agent profile.
   - Defer template-set and constitution-selection schemas to follow-up refinement features.

## Traceability Notes

- This research artifact summarizes and links architecture decisions.
- Normative rules remain in ADRs and contracts; this file is evidence/context only.
