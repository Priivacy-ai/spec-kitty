# Specification Quality Checklist: Legacy Sparse-Checkout Cleanup and Review-Lock Hardening

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-04-14
**Feature**: [../spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs) in requirements proper. Historical references to specific file paths (`src/specify_cli/...`) appear only in the Dependencies section, which is where those anchors belong, and in the Decision Log / References section for traceability.
- [x] Focused on user value and business needs (no silent data loss, no `--force` required on every review).
- [x] Written for business stakeholders at the scenario and success-criterion level; the requirement section uses stable, reviewable language that is technical where it must be (this is a developer-tool bugfix mission) without leaking implementation choices.
- [x] All mandatory sections completed.

## Requirement Completeness

- [x] No `[NEEDS CLARIFICATION]` markers remain.
- [x] Requirements are testable and unambiguous. Every FR names the observable behaviour (refuse, abort, emit, filter, write, release) rather than an internal state.
- [x] Requirement types are separated (Functional / Non-Functional / Constraints) into three tables.
- [x] IDs are unique across FR-###, NFR-###, and C-### entries.
- [x] All requirement rows include a non-empty Status value (`proposed`).
- [x] Non-functional requirements include measurable thresholds (20 ms, 200 ms, 100%, exactly-once).
- [x] Success criteria are measurable.
- [x] Success criteria are technology-agnostic at the outcome level. (Test-harness references are descriptions of the verification method, not of the feature itself.)
- [x] All acceptance scenarios are defined (Scenarios A–G).
- [x] Edge cases are identified (section 2.3).
- [x] Scope is clearly bounded (section 9 Out of Scope).
- [x] Dependencies and assumptions identified (section 8).

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria (each FR maps to at least one scenario or success criterion).
- [x] User scenarios cover primary flows (remediate, merge, commit, approve, reject, recover, override).
- [x] Feature meets measurable outcomes defined in Success Criteria.
- [x] No implementation details leak into the specification beyond the Dependencies section (which is the correct place for them in a bugfix mission that must name the affected code surfaces).

## Notes

All checklist items pass. The spec is ready to proceed to `/spec-kitty.plan`.

One observation for the plan phase: the hybrid preflight architecture has four cooperating layers (detection primitive, hard-block preflight, commit-time backstop, session-scoped warning). The plan should make the layer boundaries and their shared use of FR-001's primitive explicit early, because getting that split wrong produces either the over-broad "preflight everywhere" outcome this spec rejected, or a thin preflight that fails to prevent the cascade from external HEAD advances.

A second observation: FR-020 (approve-output source-lane anomaly) is either a pure documentation outcome or a real transition-history bug. The plan should treat it as an investigation task before it becomes an implementation task, since the right fix depends on what is actually happening in the lane reducer.
