# Specification Quality Checklist: Step authority — step.yaml as single source

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-07-16
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details beyond the necessary code anchors — the spec names authoritative surfaces (`MissionStep`, `extractor.py:835`) because the mission IS about those seams; requirements stay at the behavior level
- [x] Focused on user value and business needs — one place to author a step; graph reads what runtime reads; no routing-authority leak
- [x] Written for stakeholders — the split-brain framing is accessible; identifiers appear as anchors, not implementation prescriptions
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain — the one material fork (3 types lacking step.yaml) was resolved by an operator decision, recorded in FR-005/C-004 + Assumptions
- [x] Requirements are testable and unambiguous
- [x] Requirement types separated (Functional / Non-Functional / Constraints)
- [x] IDs unique across FR-### (12), NFR-### (5), C-### (7)
- [x] All requirement rows have a non-empty Status
- [x] NFRs include measurable thresholds (byte-for-byte parity, 0 accidental orphan growth, 100% override precedence, exit-0 gates)
- [x] Success criteria measurable (0 flat-form edits, byte-for-byte parity, stated DRG counts, 100% override, single source, gates green)
- [x] Success criteria technology-agnostic — expressed as outcomes/counts
- [x] All acceptance scenarios defined
- [x] Edge cases identified (retrospect/scope, template_set null, parity-fail-loud, missing prompt escalates to S-C, DRG delta intentional)
- [x] Scope clearly bounded (C-004 content=S-C, C-005 substeps/guards deferred, C-001 no new NodeKind)
- [x] Dependencies and assumptions identified (Assumptions section: actions/ referenceability, action nodes exist, deterministic projection)

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows (single-authority edit; all-4-types authority; override seam)
- [x] Feature meets measurable outcomes in Success Criteria
- [x] No gratuitous implementation detail leaks

## Notes

- **Revised after post-spec squad (alphonso/paula/renata, all LAND-WITH-EDITS) + operator decisions.** Key changes folded in:
  - **FR-014 added** — `action_sequence`'s order + membership is NOT in `step.yaml` today (12 step.yaml, 5 in sequence; `depends_on` empty on 11/12). Operator chose **relocate** `sequence_index`+`in_action_sequence` onto the step + project. Without this the projection was a false premise.
  - **NFR-001 split** — parity is real only for software-dev (NFR-001a); for the 3 types, projecting back is circular, so it's referential-integrity (NFR-001b).
  - **FR-009 + FR-011 deferred** (operator) → NFR-002 is a clean **0-delta** assertion; C-001 hardened to "no new Relation".
  - **`plan` type has NO prompts** for any sequence step → all 4 hit FR-013 red-test/S-C path (Assumptions corrected).
  - **FR-012 names every consumer** (extractor + runtime_bridge_composition:186/321 + decision:606 + mission_type_profiles:496) — else a retained flat form is a 5th authority.
  - **`recommended_role` = existing `agent_profile`** (no redundant field); only `recommended_model_tier` net-new (+ allowlist, or silently stripped by `extra="forbid"`).
- **Load-bearing properties**: NFR-001a parity (software-dev), NFR-002 zero DRG delta, NFR-003 no routing leak (needs FR-008's live consumer), NFR-006 dispatch invariance, NFR-007 no hot-path I/O.
- **Key plan-phase risks for the post-plan squad**: (1) where the projection seam lives (layering — doctrine extractor vs charter runtime must share ONE); (2) `MissionType` model↔step-repo caching (NFR-007); (3) the `plan`-type red-test set.
- All items pass. Ready for `/spec-kitty.plan`.
