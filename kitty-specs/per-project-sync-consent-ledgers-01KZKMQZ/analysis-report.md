---
schema_version: 1
artifact_type: spec-kitty.analysis-report
command: /spec-kitty.analyze
mission_slug: per-project-sync-consent-ledgers-01KZKMQZ
mission_id: 01KZKMQZPJ1DK4ZC99MWM71KGZ
generated_at: '2026-08-12T20:46:26.005063+00:00'
analyzer_agent: unknown
input_artifacts:
  spec.md:
    path: /Users/robert/spec-kitty-dev/repos_2026-08-12_21-41-32/spec-kitty/kitty-specs/per-project-sync-consent-ledgers-01KZKMQZ/spec.md
    sha256: db27a8f6905ff6e703d9efc8cdea5ce145c9fb7eeebd0930fd765801b482f138
  plan.md:
    path: /Users/robert/spec-kitty-dev/repos_2026-08-12_21-41-32/spec-kitty/kitty-specs/per-project-sync-consent-ledgers-01KZKMQZ/plan.md
    sha256: c7e716f7995cdfa8d18755cbc43535d2540e3ce5194698be72913560807b1338
  tasks.md:
    path: /Users/robert/spec-kitty-dev/repos_2026-08-12_21-41-32/spec-kitty/kitty-specs/per-project-sync-consent-ledgers-01KZKMQZ/tasks.md
    sha256: 5f81cc42f4e0ddd2af5a6449bd8a0ad07b58ef6879b130ccbaa9b6bdf3829f5b
  charter:
    path: /Users/robert/spec-kitty-dev/repos_2026-08-12_21-41-32/spec-kitty/.kittify/charter/charter.yaml
    sha256: b0cb6b6b5a27ca8376c5ef29bfa5c87eb64e6dcaa60e7d2330962341932b26c8
verdict: ready
issue_counts:
  critical: 0
  high: 0
  medium: 2
  low: 3
  info: 0
findings:
- id: A1
  severity: medium
  category: inconsistency
  summary: WP09 and WP10 both list tests/architectural/test_egress_consent_boundary.py in owned_files with no dependency edge between them while both are concurrently in lifecycle review, violating the tasks.md sequential-ownership rule.
- id: A2
  severity: medium
  category: inconsistency
  summary: tasks.md readiness note still names WP07 -> WP10 (cli/commands/sync.py) as the only shared-file ownership case, but WP09/WP10 frontmatter now records many arbiter-authorized shared files; the note is stale relative to the WP files.
- id: A3
  severity: low
  category: inconsistency
  summary: WP10 owned_files includes governance/config artifacts (.kittify/charter/charter.yaml, .gitattributes, src/specify_cli/_completion_manifest.json) not anticipated by the plan's project structure; rationale exists only in the WP10 activity log.
- id: A4
  severity: low
  category: underspecification
  summary: WP10 owns WP08 surfaces (src/specify_cli/sync/background.py, tests/sync/test_background*.py) but declares no WP08 dependency; ordering is satisfied de facto because WP08 is approved, yet the dependency graph does not record it.
- id: A5
  severity: low
  category: coverage
  summary: check-prerequisites warns about a missing research/ directory; tasks.md explicitly declares the plan, ADR, contracts, and post-tasks adversarial review the sufficient research record - a documented deviation, informational only.
---

## Specification Analysis Report

Mission `per-project-sync-consent-ledgers-01KZKMQZ`, analyzed 2026-08-12 on branch `pr/per-project-sync-consent-progress` after the main-reconciliation merge invalidated the previous charter input. Scope per gate instruction: cross-artifact consistency of spec.md / plan.md / tasks.md / WP files, with focus on WP09/WP10 (implemented, awaiting lifecycle review) and WP11 (not started). WP01-WP08 are approved and were not relitigated.

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| A1 | inconsistency | medium | tasks/WP09-aggregate-revocation-crash-matrix.md (owned_files), tasks/WP10-wal-aware-project-store-cutover.md (owned_files), tasks.md "Implementation readiness notes" | Both WP09 and WP10 own `tests/architectural/test_egress_consent_boundary.py`; there is no WP09<->WP10 dependency edge, and both implementations are in flight concurrently. tasks.md requires any shared file to be "sequentially owned with an explicit dependency". | During lifecycle review of WP09/WP10, record which package's edit lineage lands first for this file (or split the file's census rows), and add the ordering to the ownership map. No source change needed for the gate. |
| A2 | inconsistency | medium | tasks.md "Implementation readiness notes" vs WP09/WP10 frontmatter and WP10 Activity Log (2026-08-11/12 arbiter amendments) | The readiness note claims the only shared file is `cli/commands/sync.py` (WP07 -> WP10). The WP frontmatter now shows numerous arbiter-authorized shared surfaces (WP10 x WP02/WP04/WP05/WP06/WP07/WP08 source and test files; WP09 census tests). The amendments are properly logged in the WP files, but tasks.md was never updated, so the two artifacts disagree about the ownership map. | Update the tasks.md readiness note (in a lifecycle-review commit, not now) to reference the WP frontmatter/activity logs as the authoritative ownership record. |
| A3 | inconsistency | low | tasks/WP10-wal-aware-project-store-cutover.md owned_files vs plan.md "Project Structure" | WP10 owns `.kittify/charter/charter.yaml`, `.gitattributes`, and `src/specify_cli/_completion_manifest.json` - governance/config surfaces outside the plan's declared structure. The 2026-08-12 CI-reconciliation activity entries explain why, but neither plan.md nor tasks.md reflects it. | Accept as arbiter-authorized reconciliation; have the WP10 reviewer confirm those edits only restored current-main state and note it in the review record. |
| A4 | underspecification | low | tasks.md dependency graph; tasks/WP10 frontmatter (dependencies: WP04, WP07) vs owned_files overlapping WP08 | WP10 owns `src/specify_cli/sync/background.py` and WP08's background tests (per the 2026-08-12 integration amendment) but declares no dependency on WP08. The ordering hazard is moot - WP08 is approved - but the graph text ("WP10 may progress after WP07") no longer describes the actual surface relationship. | Note the de facto WP08-before-WP10 ordering in the WP10 review; optionally add the edge if tasks are ever re-cut. |
| A5 | coverage | low | check-prerequisites warning; tasks.md "Implementation readiness notes" | `research/` directory is absent. tasks.md explicitly declares the plan, ADR, contracts, and post-tasks adversarial review the sufficient research record, and `research.md`, `data-model.md`, `quickstart.md`, contracts, and traces all exist as the plan lists. | No action; documented deviation. |

### Coverage Summary Table

Every FR, NFR, and Constraint maps to at least one WP via `requirement_refs`; no requirement has zero tasks.

| Requirement group | Covered by | Gaps |
|---|---|---|
| FR-001..FR-011 (identity, store, consent, opt-in/out, context, daemon) | WP01-WP09, WP11 | none |
| FR-012..FR-015, FR-024, FR-029 (migration/quarantine/cutover/layout) | WP10 (plus WP01/WP02/WP04/WP08 for layout authority) | none |
| FR-016..FR-023, FR-025..FR-028, FR-030..FR-032 (admission, epochs, history, attempts) | WP03-WP09 | none |
| FR-019, FR-020, FR-033, FR-034 (cross-repo evidence, attestation, manifest) | WP11 (WP05 attests contract) | none |
| NFR-001..NFR-007 | WP01-WP11 (NFR-006 solely WP11 benchmark; NFR-002 WP10/WP11) | none |
| C-001..C-010 | WP01-WP11 | none |

Pending-work coverage: WP09 carries T040-T043 (SC-004, SC-012 proof matrix), WP10 carries T044-T048 (SC-003, SC-014, User Story 4), WP11 carries T049-T054 (SC-006, SC-008, FR-033/034). Task definitions for all three are concrete, testable, and consistent with spec acceptance scenarios; no TODO placeholders or unmeasurable vague criteria were found in the active WP prompts (WP11's performance gates restate NFR-006's exact thresholds and correctly mark CI timing advisory while keeping the documented local-SSD profile as the release gate).

### Charter Alignment Issues

None found. Specifically checked:

- **Single canonical authority**: plan/tasks establish one consent writer, one layout-generation authority, one connection owner; WP10 explicitly "consumes - not creates" the authority. Aligned.
- **ATDD-first (C-011)**: every behavior-changing WP mandates red-first ATDD; WP01 is declared green-by-design with rationale. Aligned.
- **Reviewer/implementer separation & mission hygiene**: profiles declared per WP; arbiter-authorized ownership amendments are logged. Aligned.
- **Git/workflow discipline**: WP09/WP10/WP11 all prohibit publishing, PR creation, and hosted mutation without separate Human-in-Charge authorization. Aligned.
- **Terminology canon**: no `feature`-as-domain-object usage in the mission artifacts (frontmatter `feature_slug` is a runtime schema field, not prose). Aligned.
- The #3030 supersession (C-001) is recorded as an explicit predecessor-decision supersession with an ADR requirement (T001, WP01 - approved), not a charter exception.

### Unmapped Tasks

None. T001-T054 each belong to exactly one WP, every task ID appears exactly once, and each WP's subtask list matches the subtask index in tasks.md.

### Metrics

- Requirements: 34 FR, 7 NFR, 10 Constraints - 51/51 with WP coverage (100%)
- Success criteria: 14 (SC-001..SC-014), all traceable to WP definitions of done
- Work packages: 11; tasks: 54; WP01-WP08 approved, WP09/WP10 implemented awaiting lifecycle review, WP11 not started
- Findings: 5 total - 0 critical, 0 high, 2 medium, 3 low
- Cross-artifact contradictions blocking implementation: 0
