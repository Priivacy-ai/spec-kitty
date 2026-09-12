---
schema_version: 1
artifact_type: spec-kitty.analysis-report
command: /spec-kitty.analyze
mission_slug: journal-project-consent-3030-01KYKWQS
mission_id: 01KYKWQSR6ZA5BMN6B94HYHG2Y
generated_at: '2026-07-29T23:56:17.809219+00:00'
analyzer_agent: unknown
input_artifacts:
  spec.md:
    path: /home/jeroennouws/dev/spec-kitty/kitty-specs/journal-project-consent-3030-01KYKWQS/spec.md
    sha256: b1902efb1d49ab476dd0e162ebc2058e4d7a88b8f734231ef5c772956972b3af
  plan.md:
    path: /home/jeroennouws/dev/spec-kitty/kitty-specs/journal-project-consent-3030-01KYKWQS/plan.md
    sha256: a065eaed795d521aeb0b3205e02325e00a1eeddb5eb0a93752f18b3ef3892d0f
  tasks.md:
    path: /home/jeroennouws/dev/spec-kitty/kitty-specs/journal-project-consent-3030-01KYKWQS/tasks.md
    sha256: 437b75159d256002565875193a22208db968159d07cc05b824bd26963180c679
  charter:
    path: /home/jeroennouws/dev/spec-kitty/.kittify/charter/charter.md
    sha256: cb2dc6cd12aade3d5464997467b7ecdbd3849ea3581207b58c207c3d16fff9b8
verdict: ready
issue_counts:
  low: 2
  medium: 0
  critical: 0
  high: 0
  info: 0
findings:
- id: S1
  severity: low
  category: inconsistency
  summary: status.json carries a WP03 entry that tasks.md records as deleted and that lanes.json and the board omit.
- id: R1
  severity: low
  category: coverage
  summary: Plan Complexity Tracking still argues for two enforcement points and defers removing the daemon drain, which WP02 already deleted.
---

## Specification Analysis Report (third pass)

**Mission**: `journal-project-consent-3030-01KYKWQS` · **Analysed**: 2026-07-30
**Supersedes**: 2026-07-29 (2 critical / 3 high) and the second pass (0 critical / 1 high).
**State**: WP01, WP02, WP04, WP05, WP06, WP09 approved + merged. WP07, WP08, WP10, WP11 open.
**Suite on the mission branch**: **2349 passed, 0 failed.**

### The mission's acceptance gate is met

All four absorbed #3031 pins are green, including SC-001's six-project reproduction
(one consented, five with no record, one explicit opt-out, one identity-less):

| Pin | State |
|---|---|
| `test_sync_consent_capture_gap_3031` | green (T006) |
| `test_dispatch_excludes_events_with_recorded_drain_blocked_reason` | green (T003) |
| `test_consent_predicate_must_apply_before_limit_not_after` | green (T018) |
| `test_dispatch_project_consent_3030` | green (T018) |
| `test_sc001_only_the_consented_project_is_delivered` | green (T017/T018) |
| `test_delivered_identities_are_a_subset_of_consented` | green (NFR-001) |

### Resolved since the second pass

| Was | Finding | How it closed |
|---|---|---|
| **H1** HIGH | Charter Pre-existing Failure Reporting Rule unmet | **Both failures folded in rather than filed.** One (`tests/delivery` golden-count) turned out to be the mission's own regression, not pre-existing — the earlier "pre-existing" call had compared against a base that already contained WP01/WP02. Converted the two sites. The other (`test_issue_1071_singleton_reconfirmation`) was genuinely pre-existing and is fixed: its final sweep iterated the whole hardcoded 9401–9425 band while claiming "our allocated range", so any unrelated in-band listener reddened it. The charter rule no longer applies to either. |
| **I7** MEDIUM | NFR-007 vs T020 disagreed on the batch window | NFR-007 retargeted to `_EVENT_SYNC_DISPATCH_BATCH_LIMIT`; T020's claim that batch.py was deleted corrected to "retired, un-exported, not deleted". Fixed before WP07 starts, since T020 is WP07's. |
| **H2** MEDIUM | Tracer files never seeded | All three seeded and backfilled from what actually happened. |

### Open findings

Both LOW, both cosmetic drift in already-shipped work.

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| S1 | Inconsistency | LOW | status.json; tasks.md:80 | `status.json` holds a WP03 entry; tasks.md records "WP03 was deleted", and lanes.json and the board show 10 WPs. Left alone deliberately: status.json is tool-managed and hand-editing risks desync. | Prune via tooling if a supported path exists. |
| R1 | Coverage | LOW | plan.md Complexity Tracking | The table still justifies "two enforcement points (journal dispatcher + daemon queue drain)" and says removing the daemon drain "is a larger change than this P0 should carry unilaterally". WP02 removed it. Downgraded from MEDIUM: the row is stale narrative, and the plan's IC sections and the WP files all record the decision correctly. | Replace with the decision taken. |

### Coverage Summary

| Requirement | Task(s) | State |
|---|---|---|
| FR-001 … FR-005 | T002, T004, T005 | merged |
| FR-006, FR-009 | T012 | merged |
| FR-007, FR-008 | T017, T018 | merged |
| FR-010, NFR-005 | T006(a)+(b) | merged |
| FR-011 | T013 (count), T021 (surface) | count merged; surfacing = WP07 |
| FR-012 | T007, T008 | merged |
| FR-013, FR-019 | T014 | merged, reconciled |
| FR-014 | T009 | merged |
| FR-015 | T021 | WP07 |
| FR-016, FR-017 | T022, T026 | WP08, WP11 |
| FR-018 | T023 | merged |
| NFR-001 … NFR-004, NFR-006 | T011, T012, T018, T019, T022 | NFR-006 = WP08 |
| NFR-007 | T020 | WP07, retargeted |
| C-001 … C-004 | T010, T012, T022 | C-004 = WP08 |

### Charter Alignment

No open issues. Notably well honoured:

- **Red-main discipline (order 9).** Six deliberate reds were carried, each traceable
  to a named requirement, and all six are now green. The issue matrix recorded the
  absorbed issues as `in-mission` throughout rather than claiming premature closure.
- **Single canonical authority (governing principle).** Two chains were collapsed to
  one definition site each — identity (T011) and consent precedence (T014) — both
  with AST guards preventing a second copy.
- **Pre-existing failure rule.** Correctly *not* invoked for the failure the mission
  itself caused; the misattribution was found and corrected rather than used to
  justify filing.

### Metrics

- FR coverage: **19/19 = 100%**; constraints: **7/7**
- Critical: **0** (first pass: 2) · High: **0** (first pass: 3)
- Suite: 2349 passed / 0 failed

### Next Actions

**Verdict: ready.** Nothing blocks WP07, WP08 or WP11.

1. **WP07** (T020, T021) — per-project reporting, reconciled against the journal's
   retained count, **not** `OfflineQueue().get_queue_stats()`, which is empty after
   `sync migrate` and is the source of the incident's false-green.
2. **WP08** (T022) — purge, and it now also owns C-004's retirement of
   `queue.remove_project_events`. Note the two traps recorded in its WP file:
   deleting the call zeroes the user-visible `SyncOptOutResult.removed_events`, and
   the sibling `body_queue.remove_project_tasks` must stay live.
3. **WP11** (T025, T026) — body-upload consent, the last uncovered egress path.
4. **WP10** (T024) — live verification against `spec-kitty-dev`. Needs operator
   involvement; never production.
5. Housekeeping: S1, R1.
