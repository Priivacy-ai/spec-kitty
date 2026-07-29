---
schema_version: 1
artifact_type: spec-kitty.analysis-report
command: /spec-kitty.analyze
mission_slug: journal-project-consent-3030-01KYKWQS
mission_id: 01KYKWQSR6ZA5BMN6B94HYHG2Y
generated_at: '2026-07-29T17:43:30.207500+00:00'
analyzer_agent: unknown
input_artifacts:
  spec.md:
    path: /home/jeroennouws/dev/spec-kitty/kitty-specs/journal-project-consent-3030-01KYKWQS/spec.md
    sha256: 616dd6b642e588bb049aca8240ef360ce68188d1267021c3ddb037b45c7a6e22
  plan.md:
    path: /home/jeroennouws/dev/spec-kitty/kitty-specs/journal-project-consent-3030-01KYKWQS/plan.md
    sha256: 2bf37e1ed419968c17be4170905a85249bf37e5663b970e7894355ccba0e1222
  tasks.md:
    path: /home/jeroennouws/dev/spec-kitty/kitty-specs/journal-project-consent-3030-01KYKWQS/tasks.md
    sha256: 01ce83b7b690ff74db46890ac7c8111a413feb0824b649d9a7fc319bf1ca0179
  charter:
    path: /home/jeroennouws/dev/spec-kitty/.kittify/charter/charter.md
    sha256: cb2dc6cd12aade3d5464997467b7ecdbd3849ea3581207b58c207c3d16fff9b8
verdict: blocked
issue_counts:
  critical: 2
  medium: 6
  low: 1
  high: 3
  info: 0
findings:
- id: C1
  severity: critical
  category: coverage
  summary: FR-019 (consent lives in the project, not the machine) has zero task coverage and is declared to partially supersede FR-013, which WP05/T014 implements next.
- id: I1
  severity: critical
  category: inconsistency
  summary: T006 encodes the pre-amendment NFR-005 (identity-less capture stamped, not dropped) and directly contradicts amended NFR-005, which requires non-consenting events to never reach the journal.
- id: I2
  severity: high
  category: inconsistency
  summary: C-006 states that NFR-005 forecloses gating the write path, but amended NFR-005 now mandates exactly that gating.
- id: I3
  severity: high
  category: inconsistency
  summary: plan.md IC-02 justifies splitting FR-010 by quoting the superseded NFR-005 wording verbatim; the premise no longer holds after the amendment.
- id: H1
  severity: high
  category: charter
  summary: Charter Pre-existing Failure Reporting Rule requires a GitHub issue before treating a pre-existing failure as baseline; test_issue_1071_singleton_reconfirmation is carried as accepted baseline with no issue recorded.
- id: U1
  severity: medium
  category: underspecification
  summary: plan.md declares research.md and data-model.md in the mission dossier; both are absent and research/ is empty, while plan.md cites data-model.md as the home of the columns, consent index and conflict rule.
- id: I4
  severity: medium
  category: inconsistency
  summary: NFR-007 pins fake-ingress realism to sync/batch.py's _should_probe_advertised_limits while T020 retargets it to _EVENT_SYNC_DISPATCH_BATCH_LIMIT and calls batch.py deleted; WP02 did not delete it.
- id: I5
  severity: medium
  category: inconsistency
  summary: plan.md Project Structure assigns FR-014 to sync/batch.py and FR-012 to background.py enforcement; both were relocated (FR-014 to delivery/receivers.py, FR-012 to drain deletion).
- id: I6
  severity: medium
  category: inconsistency
  summary: tasks.md T008 still instructs retiring queue.remove_project_events per C-004, which is unachievable in WP02 because the journal has no project_uuid column until WP04.
- id: G1
  severity: medium
  category: coverage
  summary: C-003 mandates an explicit recorded decision on whether project consent extends the drain_blocked_reason vocabulary or forms a second representation; no task records that decision.
- id: H2
  severity: medium
  category: charter
  summary: Charter standing order 3 requires three mission tracer files seeded at planning; none exist in the dossier.
- id: S1
  severity: low
  category: inconsistency
  summary: status.json carries a WP03 entry that tasks.md records as deleted and that lanes.json and the board omit.
---

## Specification Analysis Report

**Mission**: `journal-project-consent-3030-01KYKWQS` · **Analysed**: 2026-07-29
**State at analysis**: WP01, WP02, WP09 merged into `feat/journal-project-consent-3030` and sitting at `approved`; WP04 next.

Most findings below are **amendment drift**: the 2026-07-29 operator decisions (absorbing #3031, amending NFR-005) were written into `spec.md` but not propagated into `plan.md` or `tasks.md`. Two of them land directly on WP04, the next work package.

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| C1 | Coverage | CRITICAL | spec.md:327-332; tasks.md (absent) | **FR-019** ("consent lives in the project, not the machine") has **zero tasks**. The spec states it "partially supersedes FR-013's uuid-keyed index — reconcile the two before implementing either". FR-013 is T014 in WP05, the WP after next. | Add a reconciliation task before WP05 starts, or record FR-019 as explicitly deferred. Do not implement T014 until the FR-013/FR-019 relationship is decided. |
| I1 | Inconsistency | CRITICAL | tasks.md:29 (T006); spec.md:245 (NFR-005) | **T006 encodes the superseded NFR-005.** It says identity-less capture is "stamped into a named non-deliverable state … **not** dropped (NFR-005)". Amended NFR-005 says the opposite for non-consenting projects: events "must **never reach the journal**". T006 is a WP04 subtask — the WP about to be implemented. | Restate T006 to separate the two classes: *identity-less* capture (stamped, retained) vs *non-consenting* capture (never written). They are different rules and NFR-005 now only reverses the second. |
| I2 | Inconsistency | HIGH | spec.md:258 (C-006); spec.md:245 (NFR-005) | **C-006 contradicts amended NFR-005.** C-006 reasons "C-005 declines the second; **NFR-005 forecloses the first** [gating the write path]" and concludes the mission secures egress not collection. Amended NFR-005 now *requires* write-path gating for non-consenting projects. | Rewrite C-006's premise. Its conclusion (collection remains open) may still hold for *consenting* projects, but the stated reason is now false. This also feeds the open C-006 escalation. |
| I3 | Inconsistency | HIGH | plan.md:158-165 (IC-02) | plan.md splits FR-010 out on the grounds that mandatory identity "contradicts NFR-005 (**'no event dropped at write time'**)" — quoting the pre-amendment text as the load-bearing premise. | Re-derive the FR-010 split against amended NFR-005. The conclusion may survive (nil-sentinel handling is unchanged) but the argument as written no longer stands. |
| H1 | Charter | HIGH | charter.md:395-397; tests/sync/test_issue_1071_singleton_reconfirmation.py | The charter's **Pre-existing Failure Reporting Rule** is a MUST: an agent encountering pre-existing failures must open a GitHub issue *before* treating them as accepted baseline. `test_issue_1071_singleton_reconfirmation` has been carried as baseline throughout WP02; no issue is recorded in the dossier. | Open the issue (command run, failure summary, why pre-existing), or cite the existing one in the dossier. |
| U1 | Underspecification | MEDIUM | plan.md:74-80 | plan.md's Project Structure declares `research.md` and `data-model.md`; neither exists and `research/` is empty. plan.md cites data-model.md as the home of "journal columns, consent index, conflict rule" — WP04 and WP05's core content. | Either create them or correct the structure block. The decisions currently live inline in plan.md's IC sections; say so. |
| I4 | Inconsistency | MEDIUM | spec.md:247 (NFR-007); tasks.md:43 (T020) | NFR-007 requires the fake ingress to pass `_should_probe_advertised_limits` (`sync/batch.py`). T020 corrects the target to `_EVENT_SYNC_DISPATCH_BATCH_LIMIT` and calls batch.py "the dead daemon path WP02 deletes" — **WP02 did not delete it** (operator decision: un-export only). Both texts are now stale. | Update NFR-007 to the dispatch batch limit, and drop T020's claim that batch.py is deleted. |
| I5 | Inconsistency | MEDIUM | plan.md:97-99 | Project Structure assigns FR-014 to `sync/batch.py` and FR-012 to "`background.py` daemon drain enforces the invariant". Both moved: FR-014 landed in `delivery/receivers.py` (T009, shipped `41bbf8c1e1`); FR-012 became a deletion. | Refresh the file map to match the shipped resolutions. |
| I6 | Inconsistency | MEDIUM | tasks.md:31 (T008) | T008 instructs retiring `queue.remove_project_events` per C-004 inside WP02. Not achievable there: its caller `disable_checkout_sync` needs a journal-side purge, and the journal has no `project_uuid` until WP04. Already corrected in the WP02/WP08 files but not in tasks.md. | Move the C-004 clause out of T008 into WP08's T022, matching the WP files. |
| G1 | Coverage | MEDIUM | spec.md:255 (C-003) | C-003 requires an explicit decision on whether project consent **extends** the `drain_blocked_reason` eligibility vocabulary or is a **second** representation, warning "never ship two representations of one invariant". No task records that decision; T003 splits the vocabulary for a different purpose. | Record the decision in WP04 or WP06 before the column and the gate are both built. |
| H2 | Charter | MEDIUM | charter.md:66-68 | Standing order 3 requires three tracer files (tooling-friction, approach, design-decisions) seeded at planning and appended during implementation. None exist. | Seed them now; this mission has already generated substantial rationale worth capturing. |
| S1 | Inconsistency | LOW | status.json; tasks.md:80 | `status.json` holds a WP03 entry; tasks.md records "**WP03 was deleted**", and lanes.json and the board both show 10 WPs. | Prune the stale WP03 state entry. |

### Coverage Summary

| Requirement | Has Task? | Task IDs | Notes |
|---|---|---|---|
| FR-001 … FR-005 | Yes | T002, T004, T005 | WP01, shipped |
| FR-006, FR-009 | Yes | T012 | WP04 |
| FR-007, FR-008 | Yes | T017, T018 | WP06 |
| FR-010 | Yes | T006 | **See I1** — task text contradicts amended NFR-005 |
| FR-011 | Yes | T013 (count), T021 (surface) | Split across WP04/WP07 |
| FR-012 | Yes | T007, T008 | WP02, shipped |
| FR-013 | Yes | T014 | **See C1** — superseded in part by uncovered FR-019 |
| FR-014 … FR-018 | Yes | T009, T021, T022, T023 | |
| **FR-019** | **No** | — | **Zero coverage (C1)** |
| NFR-001 … NFR-004, NFR-006 | Yes | T011, T012, T018, T019, T022 | |
| NFR-005 | Partial | T006 | Task encodes the pre-amendment rule (I1) |
| NFR-007 | Yes | T020 | Target corrected in tasks, stale in spec (I4) |
| C-001, C-002 | Yes | T010, T012 | |
| C-003 | **No** | — | Decision unrecorded (G1) |
| C-004 | Misassigned | T008 → T022 | (I6) |

### Charter Alignment Issues

- **H1 (HIGH)** — Pre-existing Failure Reporting Rule (MUST) unmet for `test_issue_1071_singleton_reconfirmation`.
- **H2 (MEDIUM)** — Mission tracer files not seeded.
- Consistent with charter: red-main discipline (standing order 9) is well honoured — the four #3031 pins are honest reds carried deliberately, and the issue matrix now records them as `in-mission`.

### Unmapped Tasks

None. Every task T001–T026 maps to at least one requirement.

### Metrics

- Functional requirements: **19** (FR-001…FR-019); NFRs: **7**; Constraints: **7**
- Total tasks: **26**
- FR coverage: **18/19 = 94.7%** (FR-019 uncovered)
- Constraint coverage: **6/7** (C-003 undecided)
- Ambiguity count: 0 unresolved placeholders
- Duplication count: 0
- Critical issues: **2**

### Next Actions

**Verdict: blocked** (2 critical, 3 high).

Neither critical finding requires re-planning — both are text drift from the 2026-07-29 amendments, and both land on the next two work packages:

1. **Before WP04 (immediately next)** — resolve **I1**: restate T006 so identity-less capture and non-consenting capture are separate rules. As written, T006 tells the implementer to do the opposite of what amended NFR-005 and the red pin `test_sync_consent_capture_gap_3031` require.
2. **Before WP05** — resolve **C1**: decide how FR-019 relates to FR-013, or the consent index gets built against a requirement the spec says is partly superseded.
3. **Housekeeping** — I2/I3 (amendment drift in C-006 and plan.md IC-02), then I4/I5/I6/S1.
4. **Charter** — file the H1 issue; seed the H2 tracer files.

Suggested commands: manually edit `tasks.md` T006 and add an FR-019 reconciliation task; edit `spec.md` C-006 and NFR-007; edit `plan.md` IC-02 and the Project Structure block.
