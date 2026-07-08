# Specification Quality Checklist: Coord/Primary Partition Regression Lock

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-07-07
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs) — requirements describe the placement *seam* behaviourally; concrete module names appear only in Assumptions/Dependencies as raw material, not as prescribed implementation
- [x] Focused on user value and business needs (maintainer never hits split-brain; one authority)
- [x] Written for non-technical stakeholders (Purpose + scenarios are prose)
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Requirement types are separated (Functional / Non-Functional / Constraints)
- [x] IDs are unique across FR-###, NFR-###, and C-### entries
- [x] All requirement rows include a non-empty Status value (Draft)
- [x] Non-functional requirements include measurable thresholds (allow-list count, <30s, 3 runs, ≤15 complexity)
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic
- [x] All acceptance scenarios are defined (2 primary + 2 exception + 1 invariant)
- [x] Edge cases are identified (#2091 empty mid8; #2250 flat-mission error; CWD independence)
- [x] Scope is clearly bounded (Out of Scope + Constraints C-002..C-005)
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- **Post-squad remediation (2026-07-07).** A three-lens scope-check squad
  (architect-alphonso, paula-patterns, planner-priti) reshaped the spec:
  - The placement SSOT (`artifact_home_for`/`MissionArtifactHome` + the two
    frozensets in `mission_runtime/artifacts.py`) and the ratchet
    (`test_no_write_side_rederivation.py`) already exist → FR-001/NFR-001 reworded
    to **extend + lock**, not build (avoids a C-001/Directive-044 self-violation).
  - Inventory corrected: topology is the 2×2 grid bound to
    `routes_through_coordination`; 14 artifact kinds locked via frozensets.
  - #2091/#2250 downgraded from "fix" to verify+close, with the one genuine
    residual (empty-`mid8` guard at the `CoordinationWorkspace` composition seam)
    kept as FR-007 red-first.
  - Added FR-011 (ratchet grammar for `CommitTarget(ref=<checkout>)` blind spot)
    and FR-012 (stored-topology, not husk).
  - Operator decisions folded: (1) whole #1878 strangler → 3.2.x (FR-010);
    (2) this mission is **authoritative** over sibling surfaces (C-005 inverted).
- C-001 remains the binding centerpiece: the seam returning PRIMARY is not license
  to bypass it.
- All checklist items re-validated post-remediation — pass.
