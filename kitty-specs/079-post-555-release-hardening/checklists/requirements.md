# Specification Quality Checklist: 3.1.1 Post-555 Release Hardening

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-04-09
**Feature**: [spec.md](../spec.md)
**Mission**: 079-post-555-release-hardening

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
  - *Note*: C-010 names typer/rich/ruamel.yaml/pytest/mypy as a charter constraint, not as a HOW-decision being made by this spec. These are project-wide invariants set by the existing repository charter, not implementation choices for this mission. Acceptable per spec quality rules.
- [x] Focused on user value and business needs (release readiness for `3.1.1`)
- [x] Written for the operator + maintainer audience (who are the actual stakeholders for a release-hardening mission of the spec-kitty tool itself)
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
  - Each FR uses MUST/MUST NOT phrasing and has at least one mapped acceptance check (S-1..S-7) and / or verification step (V-1..V-8).
- [x] Requirement types are separated (Functional / Non-Functional / Constraints)
  - Section 7 (FR), Section 8 (NFR), Section 9 (C).
- [x] IDs are unique across FR-###, NFR-###, and C-### entries
  - FR-001..FR-008 (Track 1), FR-101..FR-106 (Track 2), FR-201..FR-206 (Track 3), FR-301..FR-305 (Track 4), FR-401..FR-405 (Track 5), FR-501..FR-506 (Track 6), FR-601..FR-606 (Track 7); NFR-001..NFR-007; C-001..C-012.
  - Track 7 was extended during plan with FR-605 (structured release-prep draft artifact) and FR-606 (CHANGELOG entry presence validation), and C-012 (final CHANGELOG prose / GitHub release notes are out of scope) per the operator's "middle-ground" decision on release-hygiene scope.
- [x] All requirement rows include a non-empty Status value (Proposed)
- [x] Non-functional requirements include measurable thresholds (NFR-001..NFR-007 each carry an explicit threshold column)
- [x] Success criteria are measurable (Acceptance Criteria, Release Gates RG-1..RG-8, Verification Strategy V-1..V-8)
- [x] Success criteria are technology-agnostic (no implementation details leak into goals/release gates)
- [x] All acceptance scenarios are defined (S-1..S-7 plus an Edge Cases list)
- [x] Edge cases are identified (Section 6 "Edge cases the spec must cover")
- [x] Scope is clearly bounded (Section 3 Non-Goals NG-1..NG-8; Section 9 Constraints C-001..C-011)
- [x] Dependencies and assumptions identified (Section 15 Assumptions A-1..A-7; baseline = #555)

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria (mapping table in Section 10 + Release Gates in Section 11)
- [x] User scenarios cover primary flows (S-1..S-7 cover all seven core tracks)
- [x] Mission meets measurable outcomes defined in Success Criteria (G-1..G-7 are mirrored by FRs and Release Gates)
- [x] No implementation details leak into specification (engineering context is referenced via issue numbers / ADR commit, not via prescribed code paths)

## Cross-References

- [x] Issue mapping table present (Section 13)
- [x] All requested issues mapped: #566, #550, #557, #525, #554, #538, #540, #542, #401 (deferred), #416 (out of scope)
- [x] Explicit note that #551, #552, #526 are already covered by merged #555 and MUST NOT be re-spec'd
- [x] Baseline (PR #555, commit `f3d017f6`) is named in the header and referenced from the rollout sequence

## Decisiveness

- [x] Both forcing-function operator decisions are locked in the spec (D-4 implement de-emphasis, D-5 #401 deferred)
- [x] No "future clarification" placeholders remain (Section 17 explicitly states "None")
- [x] Locked product decisions are explicit (D-1..D-5)
- [x] Release gate language is explicit and binary (RG-1..RG-8)

## Notes

- All checklist items pass on the first validation pass.
- Spec is ready for `/spec-kitty.plan`.
- The narrow-slice nature of #525 (Track 4) and Phase-1-only nature of #557 (Track 3) are documented as both functional requirements (FR-305, FR-206) and constraints (C-002, C-003), to make scope-creep at plan/review time obvious to reviewers.
- Track 5 (auth refresh race) is marked release-gating in FR-405; reviewers should treat any plan that skips this track as a release-blocker violation.
- Track 7 (version coherence) is the dogfood-acceptance gate and the last step in the rollout sequence; the plan must not move it earlier in the sequence.

## Post-plan reviewer corrections (applied 2026-04-09)

Two reviewer findings were applied to spec and plan after the initial plan generation:

- **P1 — Track 1 git escape hatch**: An earlier draft of the plan introduced a hidden `--git` opt-in escape hatch that contradicted D-1 / FR-001 / FR-002 / FR-007. The escape hatch is removed. The `--no-git` flag from pre-3.1.1 versions is also removed (it has no meaning under the new model and keeping it as a no-op would be a backward-compat shim that the project's CLAUDE.md forbids). FR-001, FR-002, FR-007, FR-008 and D-1 were tightened to make this absolute under all flag combinations. Spec now explicitly forbids any opt-in path.

- **P2 — Track 6 canonical path**: An earlier draft defined the canonical path as `/spec-kitty.implement` (slash command) which under the hood resolved to `spec-kitty implement` (the legacy CLI). That is just a slash-prefix rename of the legacy path and doesn't actually de-emphasize anything. A second Phase 0 research pass found the actual canonical post-#555 commands: `spec-kitty next` (loop entry, registered at `src/specify_cli/cli/commands/__init__.py:62`) plus `spec-kitty agent action implement` and `spec-kitty agent action review` (per-decision verbs at `src/specify_cli/cli/commands/agent/workflow.py`). These are distinct CLI commands from top-level `spec-kitty implement`. D-4 and FR-501..FR-504 were rewritten to name them concretely. Top-level `spec-kitty implement` is now treated as **internal infrastructure** — `spec-kitty agent action implement` does internally delegate workspace creation to it, but that delegation is an implementation detail, not a user-facing contract.
