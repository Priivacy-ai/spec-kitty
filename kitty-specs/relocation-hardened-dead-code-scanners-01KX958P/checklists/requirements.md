# Specification Quality Checklist: Relocation-Hardened Dead-Code Scanners

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-07-11
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs) — *test-infra mission; module paths named are the subject of the work, not incidental tech choices*
- [x] Focused on user value and business needs — *the "user" is the maintainer; value = no code-motion tax*
- [x] Written for non-technical stakeholders — *the honest-downscope table + scenarios are legible*
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Requirement types are separated (Functional / Non-Functional / Constraints)
- [x] IDs are unique across FR-###, NFR-###, and C-### entries
- [x] All requirement rows include a non-empty Status value
- [x] Non-functional requirements include measurable thresholds (0 false-reds / 100% caught / 0 failed / 0 silent exemptions / byte-diff=0)
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (framed as gate-green / caught / 0-failed outcomes)
- [x] All acceptance scenarios are defined (primary + downscoped-exception + 6 bite-preserved + body-sensitivity)
- [x] Edge cases are identified (dangling entry, un-keyable fail-closed, body-sensitivity, migration-helper)
- [x] Scope is clearly bounded (Out of Scope names the ~60-entry relocation forfeit + WS1 + known_modules)
- [x] Dependencies and assumptions identified (WP06 spike corpus, shape census, merged WS1)

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria (the (a–h) bite battery + NFR thresholds)
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification beyond the named surfaces under refactor

## Notes

- **Honest-downscope is load-bearing** (C-001): the relocation promise is explicitly
  scoped to the ~278 simple entries; the ~60 re-export/facade/fan-out entries stay
  module_path-keyed (relocation-forfeit, documented). The spec states this in the
  Overview table, the downscoped-exception scenario, NFR-001, C-001, and Out of Scope —
  no over-promise survives.
- Pre-hardened by a 3-lens WS2-hardening squad (design-completeness / sizing-ownership /
  preserve-bite); those findings are the confirmed research base encoded as FR-001..015.
