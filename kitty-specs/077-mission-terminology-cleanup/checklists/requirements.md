# Specification Quality Checklist: Mission Terminology Cleanup and Machine-Facing Alignment

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-04-08
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs) — spec stays at the policy / behavior / acceptance level. References to `typer` appear only in §8 (Verified Drift) and §14 (Assumptions) where they document the *cause* of an existing bug, not a prescription.
- [x] Focused on user value and business needs — operators, agents, and machine-facing consumers all have explicit scenarios.
- [x] Written for non-technical stakeholders — terminology table, scenarios, and acceptance criteria are readable without code context.
- [x] All mandatory sections completed — problem, sequencing, scenarios, FRs/NFRs/Cs, blast radius, acceptance, migration policy, test strategy, work packages, assumptions, open questions, references.

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain — none used; all gaps resolved by the user's brief or by the ADR.
- [x] Requirements are testable and unambiguous — every FR has a verifiable behavior; every NFR has a measurable threshold.
- [x] Requirement types are separated (Functional / Non-Functional / Constraints) — three distinct tables in §5/§6/§7.
- [x] IDs are unique across FR-### / NFR-### / C-### — FR-001..FR-022, NFR-001..NFR-006, C-001..C-011.
- [x] All requirement rows include a non-empty Status value — every row has Required / Locked.
- [x] Non-functional requirements include measurable thresholds — NFR-001 (< 5ms p95), NFR-002 (exactly 1 warning), NFR-003 (env var name), NFR-004 (0 broken links), NFR-005 (≥ 90% coverage), NFR-006 (0 breakages).
- [x] Success criteria are measurable — §10 acceptance criteria are pass/fail with explicit grep checks and exit-code assertions.
- [x] Success criteria are technology-agnostic where possible — acceptance criteria reference behavior and assertions, not specific frameworks. Where they reference grep / CI, that's a verification *method*, not an implementation prescription.
- [x] All acceptance scenarios are defined — §4 covers 7 scenarios + edge cases.
- [x] Edge cases are identified — §4.8.
- [x] Scope is clearly bounded — §2 sequencing, §3.3 explicit non-goals, §11 explicit out-of-scope removal.
- [x] Dependencies and assumptions identified — §14 assumptions, §15 open questions, §17 references.

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria — §10.1 (Scope A) and §10.2 (Scope B) map to FRs.
- [x] User scenarios cover primary flows — operator, agent, runtime, integrator, machine-facing consumer.
- [x] Feature meets measurable outcomes defined in Success Criteria — §10 acceptance gates are concrete.
- [x] No implementation details leak into specification — typer references are diagnostic, not prescriptive. The "small selector-resolution helper" mentioned in WPA3 is the minimum architectural commitment necessary to express the deterministic conflict requirement, and it's framed as a work package outline, not a design spec.

## Sequencing and Non-Goal Discipline

- [x] `#241` is sequenced before `#543` and the sequencing rule is explicit (§2).
- [x] Scope B work packages are gated on Scope A acceptance (C-004, §13.2 preamble).
- [x] All §3.3 non-goals are listed with ❌ markers and reinforced by C-001, C-006, C-008, C-009.
- [x] Migration/deprecation policy for `--feature` is explicit (§11) and removal is out of scope.
- [x] The migration policy is asymmetric: main CLI gets a transitional window, orchestrator-api stays strict. C-010 forbids widening the orchestrator-api envelope.
- [x] The verified dual-flag bug is encoded as both an FR (FR-006) and a regression test requirement (§12.1 case 4, WPA5).
- [x] The orchestrator-api / main-CLI split is named, the reconciliation **direction** is explicit (tighten the main CLI, do not relax the orchestrator-api), and there is a concrete work package (WPA8) and acceptance gate (§10.1 item 10).
- [x] Inverse drift (`--mission` used for blueprint/template selection) is captured: §8.1.2 lists three verified sites (`agent/mission.py:488`, `charter.py:67`, `lifecycle.py:27`); FR-021 makes the canonical state explicit; WPA2b owns the implementation; §10.1 item 14 makes acceptance verifiable; §12.2 adds a CI grep guard; §15 Q3 captures the only remaining design choice.
- [x] Historical mission artifacts under `kitty-specs/**` and `architecture/**` are explicitly out of scope: FR-022 narrows the grep gates; C-011 forbids modifying historical artifacts; §10.1 items 8, 9, and 15 enforce this in acceptance; §13.1 work packages WPA6 and WPA7 reference the narrowed scope.

## Notes

- Open questions in §15 are intentionally minimal after the post-review revision: Q1 (migration window date vs conditions), Q2 (env var naming), and Q3 (one combined suppression env var vs two). Each has a recommended default so planning can proceed without blocking. The previously open question about orchestrator-api deprecation channel is now closed by the asymmetric §11.1 policy.
- All four "do not regress" items from the user's brief are encoded as locked constraints (C-001, C-006, C-008, C-009) and as explicit non-goals in §3.3. C-010 (no widening of the orchestrator-api envelope) and C-011 (no rewriting of historical artifacts) were added during the post-review revision.
- The 299-Markdown blast-radius number from the user's brief was the *unfiltered* count. The actual scope for FR-009 / FR-010 / WPA6 / WPA7 is the much smaller subset under `src/doctrine/skills/**` and `docs/**`. Historical mission artifacts under `kitty-specs/**` (~250 of the 299) and ADRs under `architecture/**` are intentionally excluded from grep gates and from the work-package scope by FR-022 + C-011. This was the most important correction in the post-review revision.
- Post-review changes (2026-04-08): added FR-021 (inverse drift fix), FR-022 (narrowed grep scope), C-010 (do not widen orchestrator-api envelope), C-011 (do not rewrite historical artifacts), §8.1.2 (inverse drift inventory), §8.1.3 (cross-surface split direction), WPA2b (inverse drift work package), §10.1 items 14 and 15 (acceptance for both additions), revised §11.1 (asymmetric migration policy), revised FR-012 (reconciliation direction).
