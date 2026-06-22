# Specification Quality Checklist: Single planning-surface authority + worktree repair

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-06-22
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs) — *resolver/command names are the domain surfaces under fix, not tech choices*
- [x] Focused on user value and business needs (operators stop hitting silent not-found / dead-end recovery)
- [x] Written for non-technical stakeholders (scenarios are operator-facing)
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Requirement types are separated (Functional / Non-Functional / Constraints)
- [x] IDs are unique across FR-###, NFR-###, and C-### entries
- [x] All requirement rows include a non-empty Status value
- [x] Non-functional requirements include measurable thresholds (gate-green, zero-issue lint, complexity ≤15, live-repro)
- [x] Success criteria are measurable (zero unmapped, all legs×handles PRIMARY, guard fails on planted phantom)
- [x] Success criteria are technology-agnostic where user-facing
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified (create-window, coord-deleted, legacy no-mid8, benign no-op repair)
- [x] Scope is clearly bounded (#1890 + #1716 folding #2062/#2063/#2064; #1970 in-slice)
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- This is a refactor/convergence mission: the named code surfaces (resolvers, commands)
  ARE the domain objects under fix, cited for precision; they are not premature
  implementation choices.
- #1970 campsite directive is recorded as C-001 + FR-009..FR-013 per operator mandate.
- #2062 carries C-002 (no close without live repro) per the live-evidence rule.
