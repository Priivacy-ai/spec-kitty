# Specification Quality Checklist: Doctrine Delivery Reachability

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-07-28
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Requirement types are separated (Functional / Non-Functional / Constraints)
- [x] IDs are unique across FR-###, NFR-###, and C-### entries
- [x] All requirement rows include a non-empty Status value
- [x] Non-functional requirements include measurable thresholds
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

**Validation run 2 — post-squad revision.** Run 1's "all items pass" was optimistic: a four-lens
adversarial squad found eleven blockers, six of nine success criteria with a lazy implementation
path, and three FRs with no acceptance scenario. All are folded into the revised spec; see
[research/squad-findings-and-corrections.md](../research/squad-findings-and-corrections.md).

**Run 1's NFR-003 note was wrong and is withdrawn.** It deferred the bound to plan on the grounds
that "the correct number is a grain decision". Half of that is false — the context budget is already
an absolute constant (`BUDGET_DEFAULT = 32_000`, `src/charter/context_renderers/token_budget.py`),
with degradation-to-fetch-stanza implemented. Worse, the original wording ("no action emits the full
activated set verbatim") was satisfiable by **re-introducing a cap**, contradicting FR-013 in the same
document. NFR-003 now forbids truncation outright and carries a shrink-only cardinality ceiling of 90.

**Traceability, re-verified against the revised spec** — US1: FR-001, FR-002 · US2: FR-003, FR-004,
FR-005, FR-006, FR-007, FR-008, FR-019 · US3: FR-009, FR-010, FR-011, FR-012, FR-017, FR-018 · US4:
FR-015, FR-016 · US5: FR-013, FR-014. The three FRs that previously had no acceptance scenario
(scaffold parity, the activation authority, documentation) now have one each — US2 scenarios 5 and 7,
US3 scenarios 6 and 7.

**Operator rulings folded at the squad point-cut (2026-07-28):** close the defect class by extending
the two mechanisms the repo already ships, rather than hand-fixing three instances (C-010); and
migrate absent `activated_<kind>` keys to explicit empty lists rather than leaving absence to mean
"all built-ins" (FR-018). The second required amending NFR-001, which previously forbade any consumer
file mutation — the contradiction is resolved in favour of the ruling, not left standing.

One judgement call carried forward from run 1:

1. **"Written for non-technical stakeholders"** is satisfied at the level this mission admits. The
   primary actor is an autonomous agent consuming governance, and the secondary actor is the
   operator who declares it. Requirement rows are phrased as outcomes ("an artefact is offered at
   the boundary", "an identifier resolves to a path") rather than as mechanisms. The Context section
   necessarily names the three concrete instances because the defect class is otherwise
   indistinguishable from the one Mission A already closed.

2. **NFR-003 is the softest threshold in the set.** "Bounded by the action grain and within the
   existing context budget" is measurable against the current budget mechanism but does not state an
   absolute number, because the correct number is a grain decision that belongs to plan. If plan
   does not fix a concrete bound, this row must be revisited before tasks.

**Traceability**: every FR maps to a user story — US1: FR-001, FR-002 · US2: FR-003, FR-004,
FR-005, FR-006, FR-007, FR-008, FR-018 · US3: FR-009, FR-010, FR-011, FR-012, FR-017 · US4:
FR-015, FR-016 · US5: FR-013, FR-014.

**Deliberate scope exclusions** carry constraint rows rather than being silent: C-002 (no
auto-install), C-004 (vocabulary collapse deferred), C-007 (non-obvious wirings deferred to operator
interview). Three further neighbours — the eight-site kind-vocabulary consolidation, the
runtime/doctrine ratchet widening, and the operating-procedures triage — are inventoried in
[research/drg-writer-and-reachability-inventory.md](../research/drg-writer-and-reachability-inventory.md)
§5 with their tracked issues, and are not in this mission.
