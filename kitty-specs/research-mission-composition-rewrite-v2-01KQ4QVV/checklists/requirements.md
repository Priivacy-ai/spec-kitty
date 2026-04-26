# Specification Quality Checklist: Research Mission Composition Rewrite v2

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-04-26
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] Implementation-level identifiers (`MissionTemplate`, `_check_composed_action_guard`, `load_validated_graph`, `resolve_context`) appear deliberately. Audience is spec-kitty contributors and the v1 external review surfaced these as the broken surfaces that must be fixed; using them as domain terms here is precision, not over-specification.
- [x] Focused on operator-observable outcomes (mission starts, advances via composition, guards block missing artifacts, mission-review carries dogfood smoke evidence).
- [x] Audience is appropriate: spec-kitty contributors and reviewers. Domain Language section makes terms explicit.
- [x] All mandatory sections completed: Purpose, User Scenarios & Testing, Requirements (FR / NFR / C), Success Criteria, Key Entities, Assumptions, Dependencies, Out of Scope, Open Questions, Definition of Done.

## Requirement Completeness

- [x] No `[NEEDS CLARIFICATION]` markers remain. Plan-time questions are listed in Open Questions with explicit instructions to resolve at plan time.
- [x] Requirements are testable and unambiguous. Each FR cites either an observable runtime invariant or a code surface; each NFR cites a measurable threshold or hard gate.
- [x] Requirement types are separated: Functional (`FR-001..FR-015`), Non-Functional (`NFR-001..NFR-006`), Constraints (`C-001..C-008`).
- [x] IDs are unique.
- [x] All requirement rows include a non-empty Status value.
- [x] Non-functional requirements include measurable thresholds (test pass-rate, mypy/ruff zero-finding, hard gate on dogfood smoke).
- [x] Success criteria are measurable (SC-001 — `get_or_start_run` succeeds; SC-002 — `get_node` truthy and `artifact_urns` non-empty for all 5 actions; SC-003 — guard returns non-empty failure on empty dir; SC-004 — `grep` confirms no mocks of named surfaces; SC-005 — 4 regression suites pass; SC-006 — mission-review carries smoke evidence).
- [x] Success criteria are technology-agnostic at the outcome level: operator can start and advance a mission, guards fire structured errors, mission-review carries evidence.
- [x] All acceptance scenarios are defined: six Given/When/Then scenarios covering runnability, DRG resolution, guard parity, real-runtime test, no-regression, dogfood smoke.
- [x] Edge cases are identified: composed-step exception, doctrine bundle without DRG node, two consecutive actions sharing a profile, future sixth research action.
- [x] Scope is clearly bounded by Out of Scope and constraints C-004 / C-005 / C-007.
- [x] Dependencies and assumptions identified.

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria — Acceptance Scenarios 1–6 and Success Criteria SC-001..SC-006 map back to FR-001..FR-015.
- [x] User scenarios cover primary flows (full research run via composition) and edge cases (guard failures, exception during composition, missing DRG node).
- [x] Feature meets measurable outcomes defined in Success Criteria.
- [x] No implementation details leak past the intended audience. Implementation choices on coexistence-vs-replacement, DRG authoring approach, and PromptStep binding live in the plan, not the spec.

## Plan-Time Decisions Logged (Open Questions)

These are intentionally deferred to `/spec-kitty.plan`:

- [ ] Resolved at plan time — Coexistence vs replacement of legacy `mission.yaml`.
- [ ] Resolved at plan time — DRG authoring approach (shipped graph vs overlay vs calibration).
- [ ] Resolved at plan time — Guard semantics (delegate to mission.yaml predicates vs re-implement against feature dir).
- [ ] Resolved at plan time — `PromptStep` shape per research action.
- [ ] Resolved at plan time — Which v1 artifacts (from `attempt/research-composition-mission-100-broken` tag) are copied verbatim vs re-authored.

## Lessons baked in from the v1 attempt

- **Mission-review must include dogfood smoke** (NFR-005, C-008, SC-006). Without smoke evidence in the mission-review report, the verdict is UNVERIFIED, not PASS. Codified as a constraint, not a recommendation.
- **Plan-time audit must probe runnability and DRG, not just file shape**. FR-004 / FR-005 / FR-006 explicitly require DRG node existence and non-empty `artifact_urns`, not just `MissionTemplateRepository.get_action_guidelines` returning content.
- **Composed-action guard surface is mission-keyed**. FR-007 / FR-008 explicitly require `_check_composed_action_guard()` to handle research actions with parity to software-dev. Edge case explicitly covers a future sixth action: guards must fail closed.
- **Real-runtime test is non-negotiable**. C-007 prohibits mocks against the listed surfaces; FR-013 requires the live path. The "PARTIAL" label v1 used for FR-007/FR-008 is not available in v2.

## Notes

- Spec adheres to charter directives `DIRECTIVE_003` (decision documentation — Open Questions are explicit) and `DIRECTIVE_010` (specification fidelity — Success Criteria fix observable runtime invariants).
- `change_mode: feature_addition` is correct: this work introduces new identifiers (MissionTemplate file, action graph nodes, new guard branches, new test) rather than renaming existing ones.
- Premortem: top failure modes — (a) authoring a `MissionTemplate` that loads but skips composition because steps don't bind to step contracts, (b) adding action nodes to the graph but missing edges that `resolve_context` walks, (c) guard branches that delegate to mission.yaml predicates without preserving structured-error wording, (d) integration test that calls `get_or_start_run` but mocks the runtime engine internally — each is covered by an FR/NFR.
- Plan-Time Decision items are intentionally unchecked; they unblock at `/spec-kitty.plan`.
