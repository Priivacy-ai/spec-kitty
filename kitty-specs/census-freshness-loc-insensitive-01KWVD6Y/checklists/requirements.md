# Specification Quality Checklist: LOC-insensitive census freshness gate

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-07-06
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs) — census/worklist/routing are domain terms, not tech stack
- [x] Focused on user value and business needs (contributor + CI maintenance tax)
- [x] Written for non-technical stakeholders (purpose + primary scenario are plain-language)
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Requirement types are separated (Functional / Non-Functional / Constraints)
- [x] IDs are unique across FR-###, NFR-###, and C-### entries
- [x] All requirement rows include a non-empty Status value
- [x] Non-functional requirements include measurable thresholds
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic
- [x] All acceptance scenarios are defined (primary + 4 anti-tamper + edge cases)
- [x] Edge cases are identified (rank-swap, exactly-at-floor, arch_blind_groups)
- [x] Scope is clearly bounded (Out of Scope section)
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria (SC-001..SC-006 map to FRs)
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- Validation passed. The mission is a narrowly-scoped enforcement-gate change with a
  live reproduction already captured (see mission tracer / plan phase).
- The exact fix mechanism (drop `loc` at the shared derivation, live floor check) is
  recorded as C-001; the *how* is deferred to the plan phase per specify discipline.
- **Post-spec adversarial gate (verdict: minor) folded:**
  - FR-007 order-insensitivity now has a binding success criterion (SC-007) and the
    red-first reproduction (C-003) is required to use a rank-altering churn, so FR-007
    cannot ship vacuously.
  - `arch_blind_groups` LOC-insensitivity removed from scope (unfalsifiable on the
    empty, structurally-pinned-empty surface); recorded in Out of Scope.
  - Refuted finding (`--verify-census`) confirmed the derivation-level fix; C-001 now
    names the shared `live_derived_worklist` derivation so both surfaces are fixed by
    construction. Every FR now maps to at least one binding success criterion.
