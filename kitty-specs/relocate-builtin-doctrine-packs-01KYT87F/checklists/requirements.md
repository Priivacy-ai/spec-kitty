# Specification Quality Checklist: Relocate Built-In Doctrine to packs/built-in

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-07-30
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs) — *Note: this is an internal code-structure refactor, so the spec intentionally anchors at named seams (`built_in_graph_source()`, `built_in_dir`, `packs/built-in/`, the pack load path). These are the domain objects of the mission, not incidental tech choices; kept at seam granularity, not code-level. HOW to implement is left to `/plan`.*
- [x] Focused on user value and business needs — uniform pack authoring + zero behavioral drift
- [x] Written for non-technical stakeholders — `purpose_tldr`/`purpose_context` + Context section are stakeholder-legible
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain (open layout decision recorded under Assumptions for `/plan`, not as a blocker)
- [x] Requirements are testable and unambiguous
- [x] Requirement types are separated (Functional / Non-Functional / Constraints)
- [x] IDs are unique across FR-###, NFR-###, and C-### entries
- [x] All requirement rows include a non-empty Status value (all `Open`)
- [x] Non-functional requirements include measurable thresholds (324/892 graph parity, 0 skipped profiles, 0 new test failures, 0 mypy/ruff issues, asset counts)
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (framed as outcomes; graph node/edge counts are domain metrics, not implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded (C-002 deferred scope: no code wheel / kernel / shims)
- [x] Dependencies and assumptions identified (Assumptions section)

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows (runtime parity, uniform authoring, packaged install)
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification beyond the seam-level anchors noted above

## Notes

- All items pass. The single intentional deviation is seam-level technical naming, which is inherent to an internal refactor mission and kept above code granularity.
- The target on-disk layout under `packs/built-in/` (per-kind mirror vs manifest-bearing pack) is deferred to `/plan` per the confirmed option-(b) scope (unify onto the org/project load path).
