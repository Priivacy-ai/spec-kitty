# Specification Quality Checklist: Harden the Dead-Symbol Gate

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-06-26
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] Focused on maintainer value (gate sees all symbols, no false flags, no ratchet growth)
- [x] Written so a reviewer can follow each disposition to its evidence
- [x] All mandatory sections completed
- [x] Named artifacts are the subject of the work

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain (auth-trio + strategy decisions resolved up front)
- [x] Requirements testable and unambiguous (each names the exact symbol/pattern/file)
- [x] Requirement types separated (FR / NFR / C)
- [x] IDs unique across FR-### / NFR-### / C-###
- [x] All requirement rows have a Status value
- [x] Non-functional requirements include measurable thresholds (esp. NFR-001 no-false-negative, NFR-003 no-growth)
- [x] Success criteria measurable and verifiable
- [x] Acceptance scenarios defined (incl. the no-false-negative guard)
- [x] Edge cases identified (precision of matcher, baseline re-confirm, deferred auth trio)
- [x] Scope bounded (Out of Scope excludes the big-category burn-down, category_4, and the SaaS wiring)
- [x] Dependencies/assumptions identified (squad classification; #2159/#2152 merge state)

## Feature Readiness

- [x] All FRs have clear acceptance criteria
- [x] User scenario covers the primary flow (gate green, ~107 recognized live, no growth)
- [x] Feature meets measurable Success Criteria
- [x] The key risk (weakening the gate) is guarded by NFR-001 + C-001 (structural matching + regression test)

## Notes

- Requirements basis is the squad-verified disposition table `docs/engineering_notes/2158-dead-symbol-classification.md`.
- The load-bearing risk is FR-002 precision: a too-loose caller matcher would mask real dead code. C-001 (AST/anchored, not substring) + NFR-001 (no-false-negative regression test) are the guards.
- All checklist items pass; spec is ready for `/spec-kitty.plan`.
