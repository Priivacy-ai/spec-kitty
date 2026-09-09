# Specification Quality Checklist: Upgrade No-Migrations Provisioning Fix + `upgrade()` Tidy-First

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-09-08
**Feature**: [spec.md](../spec.md)

## Content Quality

- [~] No implementation details (languages, frameworks, APIs) — **Justified exception**: this is a code-internal bug-fix + refactor mission (#4032). The offending chokepoints (`installer.py:427-428`, `upgrade.py:1421`) and the oracle/guard tests are the *subject* of the work and were named in the operator brief; citing them is necessary and aids traceability. The "stakeholders" are maintainers.
- [x] Focused on user value and business needs — `upgrade` must not fail closed on the projects it exists to repair.
- [~] Written for non-technical stakeholders — audience is maintainers/CI; purpose_tldr/purpose_context carry the stakeholder-legible framing.
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain (the single discovery decision DM-…256P4F was resolved → #4047)
- [x] Requirements are testable and unambiguous
- [x] Requirement types are separated (Functional / Non-Functional / Constraints)
- [x] IDs are unique across FR-###, NFR-###, and C-### entries
- [x] All requirement rows include a non-empty Status value (all `Open`)
- [x] Non-functional requirements include measurable thresholds (exit 0; complexity ≤15; zero guard-attributable failures; byte-identical write path)
- [x] Success criteria are measurable
- [~] Success criteria are technology-agnostic — **Justified exception**: success is *defined by* specific CI gates/tests for this mission (SC-002/SC-003 name the suite, `test_no_stray_noqa_c901_marker`, `test_upgrade_char_net.py`, Ruff C901). Naming them is the point.
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded (C-001/C-003; #4047 split off; Group B excluded)
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria (via US1–US3 Given/When/Then)
- [x] User scenarios cover primary flows (fix, tidy-first, test re-evaluation)
- [x] Feature meets measurable outcomes defined in Success Criteria
- [~] No implementation details leak into specification — intentional and justified as above

## Notes

- Three items marked `[~]` are deliberate, documented exceptions for a code-internal bug-fix/refactor mission, not unaddressed gaps. All requirement-completeness and feature-readiness items pass.
- No [NEEDS CLARIFICATION] markers remain; the lone discovery decision resolved to filing #4047 (4.0.0, with a stability pull-forward note).
