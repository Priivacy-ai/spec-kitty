# Specification Quality Checklist: Review-Cycle Verdict Seam Rebuild

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-08-03
**Revised**: 2026-08-03 (iteration 3, post second adversarial round)
**Feature**: [spec.md](../spec.md)

## How to read this file

Iterations 1 and 2 marked every box `[x]`. Both were wrong, and the *same* box —
"All functional requirements have clear acceptance criteria" — was wrong twice.
This iteration only checks a box where the check was mechanically verified, and
states the verification. Where a property is genuinely partial, the box is left
unchecked rather than argued into compliance.

## Content Quality

- [x] No implementation details (languages, frameworks, APIs) — *adjudicated, see residual risk*
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [ ] **Requirements are testable and unambiguous** — see residual risk 1
- [x] Requirement types are separated (Functional / Non-Functional / Constraints)
- [x] IDs are unique across FR-###, NFR-###, and C-### entries
- [x] All requirement rows include a non-empty Status value
- [x] Non-functional requirements include measurable thresholds — each verified against its source (`max-complexity = 15` in `pyproject.toml`; 90% in `ci-quality.yml`; the 2-second budget in `tests/review/test_cycle.py`)
- [ ] **Success criteria are measurable** — see residual risk 2
- [ ] **Success criteria are technology-agnostic** — see residual risk 3
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified — each now carries its own evidence status
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified — tracker state verified live, including #3044's real children

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria — **verified mechanically this time**: all 22 FRs appear in the traceability matrix, and US1 gained AC7/AC8/AC9 to cover FR-006, FR-013 and FR-015, which had none
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria — all 13 SCs reachable from the matrix; an NFR section was added so SC-008 and SC-009 have homes
- [x] No implementation details leak into specification

## Iteration history

**Iteration 1** — every box `[x]`, self-validated. Four lenses rejected it
unanimously. "All FRs have clear acceptance criteria" was checked while FR-004,
FR-011 and FR-012 had none.

**Iteration 2** — every box `[x]` again. Four lenses rejected it again. The same
box was wrong again, for three *different* FRs. Worse, the rewrite introduced new
false premises: it claimed the artifact was a projection of the status event
(measured false — six fields have no counterpart and `reduce()` never surfaces
`review_result`), cited reproductions `research/` did not contain, set an invalid
`change_mode` value that would have hard-failed the accept gate, and named the
wrong blocker for epic #3044.

**Iteration 3** — this one. Every correction is grounded in a probe the squad ran,
not in a re-reading of the code. Landed as eight separate commits so each is
independently reviewable and revertible.

## Residual risk — stated, not argued away

1. **Testability.** Some requirements remain judgement-dependent. FR-008's
   "reconciled or reported" leaves an implementer choice between a migration and a
   permanent dual-read, and the spec does not pick one. FR-012's "declared
   polarity" needs the census before the declaration set exists. Both are
   deliberate — the census is the mission's first work package and these are the
   requirements that consume its output — but they are not fully testable *today*.

2. **Measurability.** SC-002 and SC-003 depend on fault-injection points the
   implementer selects; injecting where the existing compensator already runs would
   satisfy them without proving anything. SC-003 does not name a kill point.
   Bounding these needs the fault-injection harness to exist first.

3. **Technology-agnosticism.** SC-002, SC-006, SC-008, SC-011 and SC-012 all
   require inspecting implementation structure. Retained deliberately: the
   mission's outcome *is* structural, and a black-box criterion would be
   unfalsifiable here. Flagged so a reviewer adjudicates rather than assumes.

4. **Out-of-domain scope.** FR-018 and FR-019 (#3159, #3160) are retained by
   explicit operator decision. DIRECTIVE_025 permits recorded inclusion; the record
   is in the spec's Revision History. FR-016 is *not* in this category — it is a
   hard prerequisite for measuring the mission at all.

## Prerequisites discharged during review

- **#2804** was closed as COMPLETED while its red-first pin still failed on `main`.
  NFR-001 and SC-009 require retained failures to point at an *open* issue, so it
  was reopened with reproduction evidence.
- **`change_mode`** was set to `"normal"`, which is not a valid value
  (`VALID_CHANGE_MODES` is `frozenset({"bulk_edit"})`). The key was removed; an
  absent key is how a non-bulk mission is represented.

## Notes

- Items left unchecked above are the honest state, not an oversight. They are the
  spec's known weak points and should be re-examined after the census work package
  lands, since three of them depend on its output.
- Squad evidence and the measured baseline are in `../research/`.
