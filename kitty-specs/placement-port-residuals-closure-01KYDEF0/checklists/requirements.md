# Specification Quality Checklist: Placement-Port Residuals Closure

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-07-25
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
      — NOTE: this is an internal engineering-hardening mission; module/function/port
      names are the domain vocabulary of the residuals, not incidental implementation
      leakage. Named surfaces are confined to the Key Surfaces reference section and
      the Domain Language table by deliberate choice.
- [x] Focused on user value and business needs (safety: enforced partition routing, no silent data loss)
- [x] Written for the maintainer/operator audience (the actual stakeholders for this internal work)
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain (both design forks resolved by operator)
- [x] Requirements are testable and unambiguous
- [x] Requirement types are separated (Functional / Non-Functional / Constraints)
- [x] IDs are unique across FR-###, NFR-###, and C-### entries
- [x] All requirement rows include a non-empty Status value (all Open)
- [x] Non-functional requirements include measurable thresholds (5/5 red-first; 0 evictions; 0 new lint issues; suite green)
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic where the outcome allows (counts, pass/fail gates)
- [x] All acceptance scenarios are defined (each user story has Given/When/Then)
- [x] Edge cases are identified
- [x] Scope is clearly bounded (Out of Scope section present)
- [x] Dependencies and assumptions identified (Assumptions section; C-001 hard sequencing)

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows (5 stories, prioritized P1–P3)
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification beyond the deliberate Key Surfaces reference

## Notes

- Two design forks resolved at spec time by operator decision: A3 = read seed from PRIMARY leg; B2 = degrade to `[]`.
- C-001 records the hard A1→A2 sequencing constraint that /plan and /tasks must honor in WP ordering.
- This is NOT a bulk edit (targeted structural fixes + one helper extraction; no same-string-across-N-files rename).
- Part C (FR-008..FR-012) folded in post-merge per operator decision: green the SIX gate/contract reds PR #2920 merged red into upstream/main (fold-induced `executor.py:1056`/`:1059` + PR-body reds). FR-012 = #2926 (guard-capability MERGE_BOOKKEEPING red at the SAME coord-seed call site as FR-008). Judged per failing-test remediation framework, not retry-to-green.
- Post-spec adversarial squad (architect-alphonso, reviewer-renata, debugger-debbie, planner-priti; profile-loaded, read-only) applied. Convergent corrections folded into the spec:
  - **C-001 rewritten (BLOCKER)**: the write-side gate scans only `CommitTarget`/`safe_commit`, never `write_meta`; `migration/` subtree has ZERO such calls → FR-003 reds nothing and is A1-independent. Gate-green depends on FR-008. Adjudicated from source (grep confirmed).
  - **FR-002 reworded (HIGH)**: only the `tasks/` READ moves to PRIMARY; event write stays COORD (decouples `backfill_runtime_state`). Added to Key Surfaces + owned scope.
  - **FR-004/SC-002/US3-AS3 scoped (HIGH)**: "any module" is `migration/`-subtree-only; `upgrade/migrations/` prefix retained (C-002) — the merged NFR-001 deferred BOTH migration* subtrees.
  - **FR-001** repo_root provenance + resolver-raise-vs-mismatch pre-decided; **FR-008** pre-decided to allow-list; **FR-010** expanded to pin repair flag/positional surface + rename count test; **US4** "identically"→kind-parameterized; **FR-007** parent epic + 3rd Part-C issue (#2923/#2924 orphaned); **C-007** lane cohesion for /plan.
  - Confirmed no-change: FR-011 test judgment correct; all 5 Part C reds live-verified red for the stated reasons; C-003 honored; FR-006 correctly scoped.
