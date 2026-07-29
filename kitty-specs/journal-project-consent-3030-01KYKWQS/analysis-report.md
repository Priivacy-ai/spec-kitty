---
schema_version: 1
artifact_type: spec-kitty.analysis-report
command: /spec-kitty.analyze
mission_slug: journal-project-consent-3030-01KYKWQS
mission_id: 01KYKWQSR6ZA5BMN6B94HYHG2Y
generated_at: '2026-07-29T22:46:23.875677+00:00'
analyzer_agent: unknown
input_artifacts:
  spec.md:
    path: /home/jeroennouws/dev/spec-kitty/kitty-specs/journal-project-consent-3030-01KYKWQS/spec.md
    sha256: f5da327c761b7fecb76086bb2ba7f034ab0b5bfb3d163e6b5fdbf399dfddcc07
  plan.md:
    path: /home/jeroennouws/dev/spec-kitty/kitty-specs/journal-project-consent-3030-01KYKWQS/plan.md
    sha256: a065eaed795d521aeb0b3205e02325e00a1eeddb5eb0a93752f18b3ef3892d0f
  tasks.md:
    path: /home/jeroennouws/dev/spec-kitty/kitty-specs/journal-project-consent-3030-01KYKWQS/tasks.md
    sha256: 1bd0eaaf0670e44586057153ca3b31cdbd90e24304067fd35299649e24d7edda
  charter:
    path: /home/jeroennouws/dev/spec-kitty/.kittify/charter/charter.md
    sha256: cb2dc6cd12aade3d5464997467b7ecdbd3849ea3581207b58c207c3d16fff9b8
verdict: blocked
issue_counts:
  medium: 3
  high: 1
  critical: 0
  low: 1
  info: 0
findings:
- id: H1
  severity: high
  category: charter
  summary: Charter Pre-existing Failure Reporting Rule (a MUST) is still unmet for two pre-existing failures being carried as baseline; reporting is delegated and in flight but not yet confirmed.
- id: I7
  severity: medium
  category: inconsistency
  summary: NFR-007 pins fake-ingress realism to sync/batch.py's _should_probe_advertised_limits while T020 retargets it to _EVENT_SYNC_DISPATCH_BATCH_LIMIT and calls batch.py deleted; WP02 retired the drain but kept the module.
- id: H2
  severity: medium
  category: charter
  summary: Charter standing order 3 requires three mission tracer files seeded at planning; none exist in the dossier.
- id: R1
  severity: medium
  category: coverage
  summary: Plan Complexity Tracking still lists 'two enforcement points (dispatcher + daemon queue drain)' and defers removing the daemon drain, which WP02 already deleted.
- id: S1
  severity: low
  category: inconsistency
  summary: status.json carries a WP03 entry that tasks.md records as deleted and that lanes.json and the board omit.
---

## Specification Analysis Report (re-run)

**Mission**: `journal-project-consent-3030-01KYKWQS` · **Analysed**: 2026-07-30
**Supersedes**: the 2026-07-29 report (2 critical / 3 high / 6 medium / 1 low).
**State**: WP01, WP02, WP09 approved+merged; **WP04 approved+merged**; WP05 next.
Suite on the mission branch: **6 failed / 2320 passed** — 3 dispatcher pins awaiting WP06, 2 new SC-001 reds landed deliberately red, 1 pre-existing.

### Resolved since the last run

Both criticals and two highs are closed, plus four mediums:

| Was | Finding | How it closed |
|---|---|---|
| **C1** CRITICAL | FR-019 had zero task coverage and blocked WP05 | Operator decision recorded in spec.md (**FR-013 × FR-019 reconciliation**): both stores, project-local wins, one resolver, index is a cache. T014 rewritten to the full precedence chain; FR-019 added to WP05's requirements. |
| **I1** CRITICAL | T006 encoded the pre-amendment NFR-005 | T006 split into rule (a) identity-less → stamp and retain, rule (b) non-consenting → never write. **Implemented**: `test_sync_consent_capture_gap_3031` is now green. |
| **I2** HIGH | C-006 claimed NFR-005 forecloses write-path gating | C-006 restated: gating is required and shipped; what remains open is narrower (consenting projects share a store; pre-T006 rows persist until FR-016). |
| **I3** HIGH | plan.md IC-02 quoted superseded NFR-005 as its premise | Premise annotated and re-derived — the FR-010 split survives on the nil-sentinel reason. |
| **I5** MEDIUM | plan.md file map assigned FR-014 to batch.py, FR-012 to daemon enforcement | Map corrected to receivers.py and "drain DELETED". |
| **I6** MEDIUM | tasks.md T008 still ordered C-004's retirement in WP02 | Moved to WP08 with the schema reason stated. |
| **U1** MEDIUM | research.md / data-model.md declared but absent | Dossier tree corrected; that content lives inline in the IC sections. |
| **G1** MEDIUM | C-003's "extend or second vocabulary" undecided | Decided: **separate** representations that never overlap, with the reasoning (drain_blocked_reason is a transient machine-global snapshot; consent is a stable per-project decision). |

### Open findings

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| H1 | Charter | HIGH | charter.md:395-397 | The Pre-existing Failure Reporting Rule is a MUST and two failures are being carried as baseline: `test_issue_1071_singleton_reconfirmation`, and `test_golden_count_ban`'s `tests/delivery: 2 vs 0` (confirmed pre-existing by running the gate at the pre-WP04 base). Reporting has been delegated to the planner and is in flight, but no ticket is confirmed yet. | Confirm the issue exists (or is created) and cite it in the dossier. Downgrades to resolved on confirmation. |
| I7 | Inconsistency | MEDIUM | spec.md NFR-007; tasks.md T020 | NFR-007 requires the fake ingress to pass `_should_probe_advertised_limits` (`sync/batch.py`); T020 corrects the target to `_EVENT_SYNC_DISPATCH_BATCH_LIMIT` **and** asserts batch.py is "the dead daemon path WP02 deletes". WP02 retired the drain and un-exported its entry points but kept the module, so both texts are now inaccurate in different directions. | Update NFR-007 to the dispatch batch limit; drop T020's "deletes" claim. Do before WP07 starts, since T020 is WP07's. |
| H2 | Charter | MEDIUM | charter.md:66-68 | Standing order 3 requires three tracer files (tooling-friction, approach, design-decisions) seeded at planning and appended during implementation. None exist, and this mission has now generated substantial rationale worth capturing — several decisions live only in commit messages. | Seed them and backfill the decisions already made. |
| R1 | Coverage | MEDIUM | plan.md Complexity Tracking | The table still justifies "two enforcement points (journal dispatcher + daemon queue drain)" and says "removing the daemon drain outright is a larger change than this P0 should carry unilaterally". WP02 removed it. The row now argues against work already shipped. | Replace the row with the decision actually taken (removal), so a reviewer does not read it as the current design. |
| S1 | Inconsistency | LOW | status.json; tasks.md:80 | `status.json` holds a WP03 entry; tasks.md records "WP03 was deleted", and lanes.json and the board show 10 WPs. | Prune the stale entry. Left alone so far because status.json is tool-managed and hand-editing it risks desync. |

### Coverage Summary

| Requirement | Has Task? | Task IDs | Notes |
|---|---|---|---|
| FR-001 … FR-005 | Yes | T002, T004, T005 | WP01 merged |
| FR-006, FR-009 | Yes | T012 | WP04 merged |
| FR-007, FR-008 | Yes | T017, T018 | WP06 — next after WP05 |
| FR-010 | Yes | T006(a) | WP04 merged |
| FR-011 | Yes | T013 (count), T021 (surface) | count merged; surfacing in WP07 |
| FR-012 | Yes | T007, T008 | WP02 merged |
| FR-013 | Yes | T014 | now reconciled with FR-019 |
| **FR-019** | **Yes** | **T014** | **was uncovered; now the same resolver** |
| FR-014 … FR-018 | Yes | T009, T021, T022, T023 | T009/T023 merged |
| NFR-001 … NFR-004, NFR-006 | Yes | T011, T012, T018, T019, T022 | |
| NFR-005 | Yes | T006(a)+(b) | both rules now distinct and (b) implemented |
| NFR-007 | Yes | T020 | target inconsistent with spec text (I7) |
| C-001 … C-004 | Yes | T010, T012, T022 | C-004 reassigned to WP08 |
| C-003 | Decided | — | recorded in spec.md |

### Charter Alignment Issues

- **H1 (HIGH)** — Pre-existing Failure Reporting Rule unmet pending ticket confirmation.
- **H2 (MEDIUM)** — tracer files not seeded.
- Well honoured: red-main discipline (standing order 9). The mission carries 6 deliberate reds, each traceable to a named requirement, and the issue matrix records the absorbed issues as `in-mission` rather than claiming premature closure.
- Well honoured: single canonical authority. T011 collapsed four identity-resolution sites into one definition site with an AST guard; the FR-013/FR-019 reconciliation explicitly requires one resolver, not two.

### Unmapped Tasks

None. Every task T001–T026 maps to at least one requirement.

### Metrics

- Functional requirements: **19**; NFRs: **7**; Constraints: **7**
- Total tasks: **26**
- FR coverage: **19/19 = 100%** (was 94.7%)
- Constraint coverage: **7/7** (C-003 now decided)
- Critical issues: **0** (was 2)

### Next Actions

**Verdict: blocked** — on one HIGH only, and that one is procedural rather than design: the pre-existing-failure ticket. Nothing blocks WP05's implementation.

1. **WP05 may proceed.** Its blocker (C1) is resolved and the precedence chain is specified. The one thing to hold it to: encode the chain **once** in `sync/consent.py`, per the same single-definition rule T011 applied to identity.
2. **Confirm the H1 ticket**, then cite it in the dossier.
3. **Before WP07** — fix I7, since T020 belongs to WP07 and currently contradicts NFR-007.
4. **Housekeeping** — R1, H2, S1.
