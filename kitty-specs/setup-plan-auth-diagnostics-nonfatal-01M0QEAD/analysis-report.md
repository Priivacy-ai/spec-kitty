---
schema_version: 1
artifact_type: spec-kitty.analysis-report
command: /spec-kitty.analyze
mission_slug: setup-plan-auth-diagnostics-nonfatal-01M0QEAD
mission_id: 01M0QEAD3JBF9264167A5X5P1F
generated_at: '2026-08-23T16:59:07.461662+00:00'
analyzer_agent: codex-adversarial-squad
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
  critical: 1
  low: 1
  medium: 5
  high: 4
  info: 0
findings:
- id: A1
  severity: critical
  category: architecture
  summary: Setup-plan lifecycle emission performs SaaS outbox fan-out, so leaving it unconditional permits a hosted queue write after structural refusal.
- id: U1
  severity: high
  category: underspecification
  summary: WP01 cannot distinguish encrypted-session read failure from logged out because TokenManager swallows storage exceptions outside its owned files.
- id: T1
  severity: high
  category: testability
  summary: The valid encrypted refresh-capable session acceptance proof can be satisfied by a boolean mock and need not exercise the production storage-to-setup-plan chain.
- id: C1
  severity: high
  category: coverage
  summary: WP02 does not require structural preflight evaluation itself to degrade to a diagnostic, so an unexpected probe exception can still preempt local verification.
- id: E1
  severity: high
  category: ambiguity
  summary: The contract does not freeze exact local result and exit semantics for scaffold, insufficient plan, spec failures, and template errors.
- id: E2
  severity: medium
  category: coverage
  summary: Warning attachment is not explicitly tested for separate spec-gate, missing-spec, template-configuration, and generic local-error emitters.
- id: S1
  severity: medium
  category: inconsistency
  summary: The specification describes Authentication State as binary and has no explicit requirement or acceptance scenario for unknown despite the binding tri-state decision.
- id: P1
  severity: medium
  category: coverage
  summary: FR-009 promises sibling local-command documentation parity but no sibling command, documentation surface, or direct parity assertion is owned.
- id: O1
  severity: medium
  category: ownership
  summary: WP02 allows signature-driven adjustments to an unowned read-surface test, leaving ownership and compatibility expectations conditional.
- id: D1
  severity: medium
  category: dependency
  summary: The release dependency on issue 3127 is absent from tasks, tracker metadata, and mission closeout guidance even though the issue remains open and priority P0.
- id: I1
  severity: low
  category: inconsistency
  summary: Prompt-size estimates differ from finalized files and WP02 duplicates one execution-workspace instruction.
---

## Specification Analysis Report

Mission: `setup-plan-auth-diagnostics-nonfatal-01M0QEAD`  
Point-cut: post-tasks `/spec-kitty.analyze` plus final adversarial squad  
Verdict: **BLOCKED pending spec → plan → tasks remediation**

### Squad Method

The post-tasks question was: **Can these artifacts implement issue #3621 without weakening hosted safety, while objectively proving the authoritative local result and every auth/structural diagnostic?**

Three independent profile-loaded, read-only lenses completed:

- `architect-alphonso`: authority, topology, and side-effect seams;
- `debugger-debbie`: live evidence and non-vacuous regression coverage;
- `reviewer-renata`: contract fidelity, anti-laziness, and reviewability.

A fourth `planner-priti` dispatch could not execute because the workspace reported exhausted credits. Three completed lenses satisfy the skill's bounded 3–4 invariant. The main reviewer adjudicated every convergent or consequential finding directly against source. No mission source, spec, plan, or task artifact was remediated by this review.

## Findings

| ID | Category | Severity | Location(s) | Issue | Recommendation |
|---|---|---|---|---|---|
| A1 | Architecture / safety | CRITICAL | `plan.md:68,76,98,152`; `tasks/WP02-setup-plan-local-hosted-separation.md:261-284`; `src/specify_cli/cli/commands/agent/mission_setup_plan.py:585-610`; `src/specify_cli/status/lifecycle_events.py:489-495`; `src/specify_cli/sync/__init__.py:220-264,305-309` | Plan/tasks assert `_emit_spec_plan_phase_events` is local JSONL-only and must remain unconditional. Live code appends JSONL and then calls lifecycle SaaS fan-out; the registered handler can queue an `OfflineQueue` event when sync/scope are present. An authenticated but structurally unsafe invocation can therefore enqueue hosted lifecycle events before the proposed dossier guard. This violates FR-010, C-007, NFR-007, and the user's explicit side-effect boundary. | Add a supported local-only lifecycle-emission mode/seam that preserves JSONL while suppressing hosted fan-out under a denied `HostedSyncDecision`. Expand ownership and ATDD coverage across the status adapter/fan-out seam. Audit all setup-plan event calls, not only dossier sync. |
| U1 | Authority / underspecification | HIGH | `spec.md:126-132`; `plan.md:14-18,74,83,95`; `tasks/WP01-canonical-local-auth-classification.md:22-28,39-50,110-122`; `src/specify_cli/auth/manager.py:17-30`; `src/specify_cli/auth/token_manager.py:137-156,189-203,217-225`; `tests/auth/test_token_manager.py:203-211` | The mission requires unknown to differ from logged out, but WP01 owns only readiness projection files. `get_token_manager()` loads storage before returning; TokenManager catches storage failures, clears session state, and returns `is_authenticated=False`. Existing tests pin that collapse. Readiness cannot recover information already erased. | Expose a backward-compatible typed auth evaluation/load outcome from the canonical auth subsystem, preserving the boolean property for existing consumers. Add token-manager/storage ownership and tests for absent versus unreadable cold load and hot-summary materialization. |
| T1 | Testability / regression fidelity | HIGH | `spec.md:51-73,177`; `tasks/WP01-canonical-local-auth-classification.md:94-100`; `tasks/WP02-setup-plan-local-hosted-separation.md:174-201` | The planned valid-session proof may use `_FakeTokenManager(is_authenticated=True)` or a mocked `AuthStatus.AUTHENTICATED`. That cannot catch the original production chain failure involving encrypted storage, an expired access token, a usable refresh token, and no queue scope. | Require one cross-layer fixture using a real TokenManager over isolated secure/file storage, with expired access-token time and usable refresh semantics. Make queue-scope readers fatal if touched; invoke setup-plan and assert no auth warning. Pair it with a real storage-read failure expecting `SAAS_SYNC_AUTH_UNKNOWN`. |
| C1 | Coverage / control flow | HIGH | `spec.md:18-22,99-124,159,171-173`; `plan.md:31-32,51-68,94-99`; `tasks/WP02-setup-plan-local-hosted-separation.md:216-239`; `src/specify_cli/sync/preflight.py:783-895` | WP02 handles returned non-OK preflight values only. `run_preflight()` does not promise no-raise and calls foreground collection, owner classification, orphan enumeration, and mismatch construction without a setup-plan adapter boundary. An evaluation exception can still preempt local verification. | Add a narrow setup-plan-only no-raise collector: sanitize the exception into `SAAS_SYNC_BOUNDARY_UNSAFE`, deny hosted fan-out/delivery, and continue local verification. Add a rejecting CLI test. Do not change hosted-only commands' refusal semantics. |
| E1 | Ambiguity / exit contract | HIGH | `contracts/setup-plan-result-envelope.md:53-61`; `tasks/WP02-setup-plan-local-hosted-separation.md:174-184`; `src/specify_cli/cli/commands/agent/mission_setup_plan.py:832-890,1029-1118` | “Established nonzero/blocked behavior” conflates distinct current outcomes. A substantive plan, pristine scaffold, populated-but-insufficient plan, non-substantive/uncommitted spec, missing spec, and template/configuration error do not share one result or exit contract. An implementation could change exit semantics while claiming compliance. | Freeze an explicit local-outcome matrix with exact `result`, `phase_complete`, `error_code`/`blocked_reason`, and process exit for each case. Require auth/structural variants to preserve those fields exactly. |
| E2 | Error-path coverage | MEDIUM | `spec.md:131-132`; `contracts/setup-plan-result-envelope.md:58`; `tasks/WP02-setup-plan-local-hosted-separation.md:153-166,241-259`; `mission_setup_plan.py:1097-1118` | Task prose says warnings reach local gate/error emitters, but mandatory result-emitter cases enumerate only success/scaffold/blocked/committed. Separate missing-spec, template-configuration, and generic error payloads can omit warnings while listed tests pass. | Add explicit one-document JSON cases for spec-gate/missing-spec and template-configuration failure under logged-out/unknown auth. State which pre-root errors cannot yet carry structural evidence. |
| S1 | Spec consistency | MEDIUM | `spec.md:126-132,196-205`; `data-model.md` Authentication Classification; Decision Moment `DM-01M0QKMB5KMS0SJWBQ8H8MDK91.md` | Unknown is a binding decision and stable diagnostic in plan/contracts/tasks, but the spec's Key Entity still defines Authentication State as only logged-in or logged-out, and no FR/acceptance scenario explicitly owns unknown distinctness. | Make Authentication State explicitly tri-state and add an acceptance scenario/requirement for unknown distinct from logged out, then map it to the revised WPs. |
| P1 | Policy coverage | MEDIUM | `spec.md:167,250-260`; `tasks/WP02-setup-plan-local-hosted-separation.md:286-331` | FR-009 and DoD require consistency with sibling local Mission commands and documentation, but no sibling command or authoritative documentation surface is named/owned. Setup-plan comments alone can satisfy the task self-referentially. | Name the sibling policy reference and documentation/test surface, add non-overlapping ownership and a parity assertion, or narrow FR-009 explicitly. |
| O1 | Ownership | MEDIUM | `tasks/WP02-setup-plan-local-hosted-separation.md:34-40,286-331` | T011 permits signature adjustments required by unrelated read-surface tests and runs `test_setup_plan_read_surface.py`, but that file is not owned. | Prefer backward-compatible helper defaults so the unowned test needs no edit; otherwise add the exact file to WP02 ownership and rerun finalization. |
| D1 | Release dependency | MEDIUM | `spec.md:193,209-218`; both WP `tracker_refs`; `tasks.md:74-82`; live GitHub issue #3127 | C-006 is release-only, not a code-lane dependency. It is absent from WP tracker/closeout guidance and could be forgotten. A fresh check found #3127 still OPEN, labeled `priority:P0`, with no close timestamp. | Record #3127 as a mission acceptance/release-closeout gate and tracker reference while leaving WP01→WP02 as the code dependency graph. |
| I1 | Editorial consistency | LOW | `tasks.md:38,59`; finalized prompt sizes; `tasks/WP02-setup-plan-local-hosted-separation.md:308-310` | Estimates are ~260/~440 versus 206/391 finalized lines, and one execution-workspace sentence is duplicated. | Correct during remediation. |

## Convergence and Adjudication

- U1 and C1 were independently confirmed by all three completed lenses and by direct source inspection.
- T1 was independently confirmed by debugger and reviewer lenses; direct inspection shows the prompt explicitly allows a boolean fake.
- A1 was raised by the architecture lens and independently source-confirmed by tracing lifecycle append → adapter → registered sync handler → `OfflineQueue.queue_event`.
- E1 was raised by the reviewer lens and source-confirmed from the command's mixed return/raise paths.
- No consequential disagreement remained. The squad agreed that existing `tests/sync` may own detector mechanics; the setup-plan adapter needs one real wiring case plus structured parametrization, not redundant filesystem integration for every mismatch.

## Requirement Coverage

| Requirement | Status after review | Task/WP | Gap |
|---|---|---|---|
| FR-001 local verification always runs | Incomplete | T006, T008-T010 / WP02 | C1 leaves an exception path that preempts local work. |
| FR-002 auth and queue scope distinct | Planned | T001-T003 / WP01 | Authority boundary must expand per U1. |
| FR-003 no false unauthenticated diagnostic | Incomplete | WP01-WP02 | T1 allows the original storage-chain regression to survive. |
| FR-004 logged-out state nonfatal | Planned | WP02 | Strong normal/blocked coverage. |
| FR-005 verification controls exit | Ambiguous | WP02 | E1 must freeze exact local outcomes. |
| FR-006 structured warnings | Incomplete | WP02 | E2 leaves distinct error emitters unpinned. |
| FR-007 human warning parity | Planned | WP02 | Normal logged-out/structural cases explicit. |
| FR-008 completeness failure primary | Incomplete | WP02 | Exact local matrix missing (E1). |
| FR-009 sibling local-command policy | Incomplete | T011 / WP02 | P1 lacks named authority/owned proof. |
| FR-010 isolate unsafe hosted delivery | Not satisfied by plan | T006-T010 / WP02 | A1 permits lifecycle outbox writes. |
| FR-011 structural diagnostic contract | Incomplete | WP02 | C1 exception path absent. |
| FR-012 local result authoritative | Incomplete | WP02 | E1/C1 prevent objective proof across all local outcomes. |

## Charter Alignment

No charter principle needs changing. The remediation is required to satisfy existing charter rules:

- single authority per invariant (U1);
- ATDD-first and non-vacuous acceptance evidence (T1, C1, E1);
- explicit architectural boundaries and fail-closed hosted safety (A1);
- traceable coordination dependencies (D1);
- reviewable file ownership (O1).

## Metrics

- Total requirements: 26 (12 FR, 7 NFR, 7 constraints)
- Total subtasks: 11 across 2 WPs
- Explicit FR mapping: 12/12
- Fully implementable/aligned FRs at this point-cut: 3/12
- Critical findings: 1
- High findings: 4
- Medium findings: 5
- Low findings: 1
- Completed squad lenses: 3
- Unmapped subtasks: 0
- Ownership overlap reported by finalizer: 0; one conditional ownership omission remains (O1)

## Next Actions

Do not start implementation. Remediate spec, plan, data model/contract, tasks, and WP ownership together; rerun requirement mapping, `finalize-tasks`, and `/spec-kitty.analyze`. The code dependency should remain auth authority first, setup-plan integration second, but the WPs likely need broader owned surfaces or a dedicated lifecycle-side-effect package.

No remediation edits were applied by this analysis or squad.
