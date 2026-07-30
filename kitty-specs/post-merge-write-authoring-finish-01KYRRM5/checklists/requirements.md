# Specification Quality Checklist: Post-Consolidation Write Surface and Authoring Finish

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-07-30 (revised post-grounding-squad)
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details in FRs (seam/ADR names appear only in Constraints/Terminology as genuine boundaries)
- [x] Focused on user value (post-consolidation evidence capture; zero-hand-edit authoring; reference visibility)
- [x] Written for the mission's operators/agents as stakeholders
- [x] All mandatory sections completed; binding Terminology section added to close the `merge` overload

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Requirement types separated (16 FR / 4 NFR / 12 C)
- [x] IDs unique across FR/NFR/C
- [x] All requirement rows have a non-empty Status
- [x] NFRs include measurable thresholds (NFR-004 no-new-subprocess-on-happy-path; NFR-001 gate-green + no-second-resolver)
- [x] Success criteria measurable and technology-agnostic (9 SC: exit 0, 0 residue, 0 hand-edited JSON, 0 false-positive gate regressions)
- [x] All acceptance scenarios defined (4 user stories: US1 P1 CONSOLIDATED wiring, US2 P2 authoring, US3 P3 URL refs)
- [x] Edge cases identified (never-created vs deleted Target Ref; squash publish; pre-consolidation no-regression; failed-vs-malformed invariant)
- [x] Scope clearly bounded (C-005 names out-of-scope seams + reconciles the shared-resolver consequence)
- [x] Dependencies/assumptions identified (phase signal, CONSOLIDATED wiring, ADR extension, sequencing C-010)

## Feature Readiness

- [x] All FRs have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes in Success Criteria
- [x] No implementation detail leaks beyond bounded Constraints/Terminology

## Notes — post-grounding-squad revision (2026-07-30)

3-lens profile-loaded squad (paula/architect/priti) run post-spec. Key outcome: the operator identified the two "unfixable as specified" BLOCKERs as **`merge` terminology-overload artifacts**, not design holes. Resolution (recorded in the `design-decisions` tracer):
- **CONSOLIDATED is the vehicle, not a phantom** — wire `SurfaceLocations.consolidated`, phase-resolved E1 (Target Ref tree) vs E2 (repo-root checkout on the Primary Branch). NOT a ref-swap; no new `merge_target_branch` field. Evidence: `artifacts.py:41-52`, `resolution.py:1517` total CONSOLIDATED arm.
- **Surviving squad corrections folded**: internal phase derivation (NFR-001/C-001); scope-leak reconciliation for STATUS_STATE/DECISION_LOG (C-005); single seam-thunk for #3073 (FR-005); FR-007/008 split register/execute; `--diagnose` hardening not a new `--explain` surface (FR-009/C-008); single-regex same-repo URL + provenance round-trip (FR-012/013/C-011); explicit sequencing (C-010); SC-005 fixture corrected to samuelgoff's `spec.md` Input-field URL (SC-008).
- **Operator decisions**: added the #2318 stale-`overall_verdict` sub-bug as FR-010 (not silently dropped); #1738 scoped to same-repo URLs only; FR-006 "terminus fail-closed" **dropped as misdirected** — terminus fires at E1, must stay fail-open (C-009); the genuine E2 retrospective write is an ordinary PRIMARY-kind CONSOLIDATED write (FR-003).
- No [NEEDS CLARIFICATION] markers — all open design questions resolved at spec time.

## Notes — tidy-first #3080 foundation folded (2026-07-30)

Operator folded the "do not make it worse" foundation of #3080 into this mission as a tidy-first enabler (sequenced before Lane A): FR-014 ADR canonicalizes `consolidate` for the lane-consolidation sense (extends the CONSOLIDATED-wiring ADR); FR-015 glossary update; FR-016 CI drift-ratchet guard in `test_no_legacy_terminology.py`. Boyscouting constraint C-012: disambiguate "merge" (lane-consolidation sense) → canonical in new symbols/touched prose/comments; existing public merge-named symbols + git-merge/publish senses stay (→ #3080). Full command/code/docs rename remains #3080. Spec now 16 FR / 4 NFR / 12 C / 11 SC.
