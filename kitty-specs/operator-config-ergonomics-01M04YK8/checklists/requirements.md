# Specification Quality Checklist: Operator Config & Install Ergonomics

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-08-16
**Updated**: 2026-08-16 (post-spec squad revision)
**Feature**: [spec.md](../spec.md) · Design record: [design-record.md](../design-record.md)

## Content Quality

- [x] No implementation details that preclude alternatives (technical anchors named as constraints)
- [x] Focused on operator value and correctness outcomes
- [x] Written to be reviewable by non-implementers (user stories lead)
- [x] All mandatory sections completed (+ Dependencies & Assumptions)

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous (FR-008 allowlist/denylist contradiction resolved → fail-closed allowlist)
- [x] Requirement types are separated (Functional / Non-Functional / Constraints)
- [x] IDs are unique across FR-###, NFR-###, and C-### entries
- [x] All requirement rows include a non-empty Status value
- [x] Non-functional requirements include measurable thresholds (delta-vs-baseline load, 0 secrets, 0 absolute paths, byte-identical)
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic where the outcome allows
- [x] All acceptance scenarios are defined (FR-003→US4.4; FR-006 fail-loud→US2/FR-006 note; FR-008→US2.6; pre-import→US2.4; unreadable→US2.5; re-bake→US1.4)
- [x] Edge cases are identified and each maps to a scenario or gated constraint
- [x] Scope is clearly bounded (rc-cadence producer half → #3047; HOME excluded; no CONFIG_HOME var)
- [x] Dependencies and assumptions identified (dedicated section: #3493/#3494/#3495/#3496, #3047 interface, #3381 migration ordering, #3251/#3022/#2519)

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows (5 prioritized stories P1–P3)
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification beyond named constraints

## Post-spec squad resolutions (3 lenses: reviewer-renata / architect-alphonso / planner-priti)

- FR-008 allowlist vs denylist contradiction → **fail-closed allowlist** (title/body/NFR-004/Key Entities aligned).
- Pre-import shim must beat `__init__.py:36` → FR-004 + US2.4 scenario.
- Two-tier `setdefault` merge order (per-repo over home, then setdefault) → FR-004 + US2.3.
- Present-but-unreadable fails loud → FR-004a + US2.5.
- Doctor config-health + channel facet → FR-010 + US4.4 / US3.4.
- Single shared path→token normalizer for both carriers → FR-001.
- `get_packs_root_default()` = `.parent` arithmetic → FR-006.
- Scaffold must not seed PACKS_ROOT (TEMPLATE_ROOT gate) → C-003a + US4.2.
- Re-bake footgun (PACKS_ROOT=abs exported) → C-003 + US1.4 + SC-001.
- Two independent migrations + doctor.py per-check ownership (#1623) → Dependencies & Assumptions.
- #3047 discovery interface + #3381 migration-ordering → Dependencies & Assumptions.
- Dangling `.kittify/mission-brief.md` reference → replaced by committed [design-record.md](../design-record.md).

## Notes

- The env-templated-vs-repo-relative and HOME-scope decisions were resolved with the operator (token provenance; HOME excluded; located via `SPEC_KITTY_HOME`; two-tier overlay).
