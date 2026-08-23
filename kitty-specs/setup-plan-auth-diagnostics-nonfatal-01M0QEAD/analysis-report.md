---
schema_version: 1
artifact_type: spec-kitty.analysis-report
command: /spec-kitty.analyze
mission_slug: setup-plan-auth-diagnostics-nonfatal-01M0QEAD
mission_id: 01M0QEAD3JBF9264167A5X5P1F
generated_at: '2026-08-23T16:38:36.313649+00:00'
analyzer_agent: codex
input_artifacts:
  spec.md:
    path: /private/var/folders/h5/zqph_vqs3_77ctcqwvr_1b6m0000gn/T/spec-kitty-20260823-154419-r1aDO4/spec-kitty/kitty-specs/setup-plan-auth-diagnostics-nonfatal-01M0QEAD/spec.md
    sha256: 5dd754f3761bf77ebd370d69bc41e6c334839288dc0be348dee91a716f340a40
  plan.md:
    path: /private/var/folders/h5/zqph_vqs3_77ctcqwvr_1b6m0000gn/T/spec-kitty-20260823-154419-r1aDO4/spec-kitty/kitty-specs/setup-plan-auth-diagnostics-nonfatal-01M0QEAD/plan.md
    sha256: ba1dd28f2d348bc3199a7adfd5ebaa1034198d012066e211cce9d199f040e32e
  tasks.md:
    path: /private/var/folders/h5/zqph_vqs3_77ctcqwvr_1b6m0000gn/T/spec-kitty-20260823-154419-r1aDO4/spec-kitty/kitty-specs/setup-plan-auth-diagnostics-nonfatal-01M0QEAD/tasks.md
    sha256: 616e52f3afcf960ddd58995c56384b99f730df7bf73dd931423b2061b4af13da
  charter:
    path: /private/var/folders/h5/zqph_vqs3_77ctcqwvr_1b6m0000gn/T/spec-kitty-20260823-154419-r1aDO4/spec-kitty/.kittify/charter/charter.yaml
    sha256: a90fa5d9fb0187d036a248af499643921f46773f96ad8a37e660a801ee60b641
verdict: blocked
issue_counts:
  medium: 1
  high: 2
  critical: 0
  low: 1
  info: 0
findings:
- id: U1
  severity: high
  category: underspecification
  summary: WP01 cannot distinguish encrypted-session read failure from logged out because TokenManager swallows storage exceptions outside its owned files.
- id: C1
  severity: high
  category: coverage
  summary: WP02 does not require structural preflight evaluation itself to degrade to a diagnostic, so an unexpected probe exception can still preempt local verification.
- id: D1
  severity: medium
  category: dependency
  summary: The
- id: I1
  severity: low
  category: inconsistency
  summary: tasks.md prompt-size estimates and one WP02 instruction differ from finalized prompt text.
---

## Specification Analysis Report

Mission: `setup-plan-auth-diagnostics-nonfatal-01M0QEAD`  
Point-cut: post-tasks, before implementation  
Verdict: **BLOCKED pending cross-artifact remediation**

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|---|---|---|---|---|---|
| U1 | Underspecification / authority | HIGH | `spec.md:126-132,159-170`; `plan.md:14-18,74,83,95`; `tasks/WP01-canonical-local-auth-classification.md:22-28,39-50,110-122`; `src/specify_cli/auth/token_manager.py:137-156,189-203,217-225` | Spec and plan require `unknown` to differ from logged out, but WP01 owns only `readiness/auth.py`. The underlying `TokenManager` catches storage-read/materialization exceptions, clears the session, and makes `is_authenticated` return `False`. A readiness-only change can classify a property exception as unknown but cannot observe the real unreadable encrypted-session case. | Refine the plan and WP01 to expose a tri-state local auth evaluation from the canonical auth subsystem, with ownership/tests for that subsystem. Preserve `is_authenticated` compatibility for existing callers; setup-plan/readiness consumes the new typed result. |
| C1 | Coverage / control flow | HIGH | `spec.md:18-22,99-124,159,171-173`; `plan.md:31-32,51-68,94-99`; `tasks/WP02-setup-plan-local-hosted-separation.md:203-239` | The artifacts promise local verification always completes under structural sync problems, but WP02 only specifies handling a returned non-OK `PreflightResult`. `run_preflight()` is not declared no-raise, and WP02 explicitly rejects generic exception recovery. An unexpected foreground/owner/store evaluation exception could still escape before local verification. | Specify a narrow no-raise setup-plan adapter around structural evidence collection: convert probe evaluation failure to `SAAS_SYNC_BOUNDARY_UNSAFE` with error details, set hosted delivery disallowed, and continue local verification. Do not change fail-closed semantics for hosted-only commands. Add a rejecting acceptance case. |
| D1 | Dependency | MEDIUM | `spec.md:193,209-218`; `tasks.md:1-82`; both WP frontmatter `tracker_refs` | C-006 says final release readiness waits for issue #3127, but neither tasks nor WP metadata/DoD carries that coordination dependency. Runtime dependency graphs only contain WP01→WP02. | Add an explicit non-code release/finalization gate to tasks/WP02 reviewer guidance or mission closeout criteria and reference #3127 in tracker metadata. Do not make local implementation wait unnecessarily if the intended constraint is release-only. |
| I1 | Consistency | LOW | `tasks.md:38,59`; finalized prompt line counts; `tasks/WP02-setup-plan-local-hosted-separation.md:308-310` | Estimated prompt sizes are ~260/~440 while finalized files are 206/391 lines, and WP02 repeats the “run from the WP execution workspace” instruction. | Correct estimates and remove the duplicate sentence during remediation; no behavioral impact. |

## Coverage Summary

| Requirement | Has Task? | Task IDs / WP | Notes |
|---|---|---|---|
| FR-001 local verification always runs | Yes, incomplete | T006, T008-T010 / WP02 | C1: probe-exception path not pinned. |
| FR-002 auth and queue scope distinct | Yes | T001-T003 / WP01 | Queue decoupling is explicit. |
| FR-003 no false unauthenticated diagnostic | Yes | T001-T002, T005-T006 / WP01-WP02 | Refresh-capable/no-scope case explicit. |
| FR-004 logged-out state nonfatal | Yes | T005-T009 / WP02 | Complete/incomplete and human/JSON covered. |
| FR-005 verification controls exit | Yes | T006, T008-T009 / WP02 | Matrix compares primary result across auth states. |
| FR-006 structured warnings | Yes | T005, T007, T009 / WP02 | One JSON envelope specified. |
| FR-007 human warning parity | Yes | T005-T006, T009 / WP02 | Warning—not refusal—language specified. |
| FR-008 completeness failure primary | Yes | T006, T009 / WP02 | Early spec/non-substantive paths called out. |
| FR-009 sibling local-command policy | Yes | T011 / WP02 | Regression boundary present. |
| FR-010 isolate hosted delivery | Yes | T006-T010 / WP02 | Dossier/queue spies required. |
| FR-011 structural diagnostic contract | Yes, incomplete | T005-T009 / WP02 | C1: returned failures covered; thrown evaluation failure absent. |
| FR-012 local result authoritative | Yes | T006, T008-T010 / WP02 | Explicit invariant and matrix. |

## Non-Functional and Constraint Alignment

- NFR-001 through NFR-007 have stated test or review coverage, but NFR-006/NFR-007 inherit C1's missing probe-exception case.
- C-001, C-002, C-003, C-004, C-005, and C-007 are carried into WP non-goals, implementation guidance, or review gates.
- C-006 is not carried into executable planning metadata or closeout guidance (D1).
- No charter MUST conflict was found. ATDD-first, canonical-authority, dependency discipline, cross-platform isolation, and tracer requirements are otherwise represented.

## Unmapped Tasks

None. All T001-T011 belong to exactly one WP and are semantically tied to at least one requirement or constraint.

## Metrics

- Total requirements: 26 (12 FR, 7 NFR, 7 constraints)
- Total subtasks: 11 across 2 WPs
- Explicit FR mapping: 12/12 (100%)
- Effective FR coverage after feasibility review: 10 complete, 2 incomplete
- Ambiguity/underspecification findings: 1
- Duplication findings: 0
- Critical findings: 0
- High findings: 2

## Next Actions

Do not begin `/spec-kitty.implement` yet. Refine the plan/tasks so the canonical auth subsystem can preserve an unknown storage-read state and so setup-plan's structural collection is narrowly no-raise. Carry #3127 into closeout metadata, then rerun task finalization and `/spec-kitty.analyze`.

No remediation was applied by this analysis.
