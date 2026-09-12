# Specification Quality Checklist: Meta.json Fail-Closed Read Routing

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-08-10
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs) — *inherent-domain note: this is an internal tech-debt mission whose subject IS the meta.json read seam; requirements name behavioral outcomes (fail loud, one verdict, honest gates), and the seam/gate references in Constraints are the mission's domain boundary, not premature implementation choices.*
- [x] Focused on user value and business needs (fail-loud on corruption; no contradictory lock verdicts; trustworthy gates)
- [x] Written for the affected stakeholders (maintainers and agents on ref-advance / implement / merge paths)
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain (both operator decisions resolved: C-005 absent≠null, C-006 deviation record)
- [x] Requirements are testable and unambiguous
- [x] Requirement types are separated (Functional / Non-Functional / Constraints)
- [x] IDs are unique across FR-###, NFR-###, and C-### entries
- [x] All requirement rows include a non-empty Status value
- [x] Non-functional requirements include measurable thresholds (symbol counts, 0 silent absorptions, gates green from live measurement)
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic where possible (counts of routed sites, silent absorptions, decoder/comparator symbols, gate state)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded (5 sites, one comparator, one governance record; ordered #3229→#3230; #3228 + #3240 folded in)
- [x] Dependencies and assumptions identified (C-001 ordered dependency, C-007 branch-reality reconciliation)

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows (P1 fail-loud, P2 unified comparator, P3 honest gates)
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification beyond the inherent-domain seam/gate boundaries noted above

## Notes

- Items marked incomplete require spec updates before `/spec-kitty.plan`.
- All items pass. The two operator decisions were resolved during discovery (C-005: distinguish absent from null; C-006: record the #3240 deviation rather than register a new baseline).
- **Post-spec adversarial squad (2026-08-10, 4 lenses: structure / anti-laziness / live-gate / sequencing) folded in.** Convergent corrections added: kernel placement of L1 + comparator (C-008, so git-plumbing site A can route without importing `specify_cli`); `ROUTED_CALLEES` extension + margin-based floor re-derivation (C-002/FR-008); malformed-vs-empty boundary (C-010); per-module atomic WPs + floor serialization (C-001/C-009); captured red-first with typed error + site identifier (FR-007); enumeration + completeness gate (FR-010/NFR-001); inline-literal field-set hole closed (NFR-002); `ref_advance`-import ratchet (NFR-004); corrected 5-site taxonomy; FR→site / issue-closure map. Squad confirmed the mission's premises are sound (3 gates green; site A unrouted; diagnosability tests absent).
