# Specification Quality Checklist: Mission-Surface Resolver Strangler-Finish

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-06-21 (re-scoped to strangler-finish same day)
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details beyond the code-surface anchors a maintainer audience needs
- [x] Focused on the outcome (the three resolution legs agree; coord-empty resolves loudly; coord-deleted hard-fails uniformly)
- [x] Written for the relevant stakeholder (internal developer tooling; primary stakeholder is a maintainer)
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Requirement types are separated (Functional / Non-Functional / Constraints)
- [x] IDs are unique across FR-### (001-008), NFR-### (001-005), C-### (001-005), SC-### (001-008)
- [x] All requirement rows include a non-empty Status value
- [x] Non-functional requirements include measurable thresholds (gate-green-each-step; type+code assertion not weakened; warning test-asserted; byte-identical; zero external callers)
- [x] Success criteria are measurable (31/0 gate; zero callers; mutation flips; zero reach-ins)
- [x] Success criteria are technology-agnostic outcomes
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified (create-window; no-coord; dangling caller; net-new warning)
- [x] Scope is clearly bounded (collapse-convergence + 2 tidies IN; CoordAuthorityUnavailable deletion / acceptance-lane reroute / mission_runtime taxonomy / #2046-redo OUT)
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria (mapped to SC-001..008)
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak beyond the necessary code-surface anchors

## Notes

- **Re-scoped 2026-06-21 to the #2040 strangler-FINISH** after a brownfield check found the R1 safety net
  (audit/guard/differential) + FR-004 typed-error already BUILT + GREEN (mission `01KVGCE8`). The operator
  chose to pull the collapse forward. Basis: `research/collapse-reduction-map-randy.md` +
  `research/collapse-boundary-analysis-alphonso.md`.
- The collapse is a **convergence** (route 3 legs through one body), not a large deletion. The differential
  equivalence gate is the deletion-safety net and stays green at every WP boundary (27/6 → 29/4 → 31/0).
- **Central decision (operator: converge fully):** the aggregate `CoordAuthorityUnavailable` boundary —
  coord-empty drains for free under Option B; coord-deleted converges its exception *spelling* to
  `CoordinationBranchDeleted` (hard-fail preserved, C-001), keeping `CoordAuthorityUnavailable` exported
  (C-003), migrating the `agent status` public contract in the same slice (FR-005).
