---
schema_version: 1
artifact_type: spec-kitty.analysis-report
command: /spec-kitty.analyze
mission_slug: design-phase-orchestrator-api-01M1HE6M
mission_id: 01M1HE6MNSX2ED6MXG05SX3K4G
generated_at: '2026-09-02T19:49:03.985228+00:00'
analyzer_agent: claude
input_artifacts:
  spec.md:
    path: kitty-specs/design-phase-orchestrator-api-01M1HE6M/spec.md
    sha256: c8998b21c3853aa289aa2f1aa5dafc1eea680ef28b6f3ff6586c79b60220ce00
  plan.md:
    path: kitty-specs/design-phase-orchestrator-api-01M1HE6M/plan.md
    sha256: ef84ce5bc0ee051049515e8617efeb0955bf89e919c1225630c1aec2a772a156
  tasks.md:
    path: kitty-specs/design-phase-orchestrator-api-01M1HE6M/tasks.md
    sha256: 59c8d48cf89c8349a827fce1fcc554931111dedca491d2cfcf1a906e2caf5101
  charter:
    path: .kittify/charter/charter.yaml
    sha256: 137e5999a27cc10136e65984ca5fbb5e9b7675324065e6cb076f72bcfddebf96
verdict: blocked
issue_counts:
  critical: 0
  high: 1
  medium: 2
  low: 2
  info: 0
findings:
- id: I1
  severity: medium
  category: inconsistency
  summary: "spec.md Clarification 3 (~L680) cites commands.py:1258-1266,1352-1360 for start-implementation/start-review's wp_id/from_lane/to_lane data dicts; post-merge (PR #3826 into main, folded in at 0753bbffa) the actual lines are 1353-1355 and 1447-1449."
- id: I2
  severity: medium
  category: inconsistency
  summary: spec.md Clarification 5 (~L726-727) cites commands.py:1239-1240,1333-1334 (start-implementation/start-review sync_dossier opt-out) and commands.py:1516-1517 (transition's); actual post-merge lines are 1332-1333, 1426-1427, and 1609-1610.
- id: I3
  severity: high
  category: inconsistency
  summary: plan.md Gate Set item 13 (~L549) and tasks/WP03-specify-plan-tasks-verbs.md (~L94) both instruct implementers to follow the start-review pattern at commands.py:1286-1360 as precedent; post-merge that range falls entirely inside start_implementation's body (~1235-1375), not start_review (~1380-1465) — an implementer following the literal citation reads the wrong verb's code.
- id: I4
  severity: low
  category: inconsistency
  summary: spec.md Clarification 1 (~L554) and tasks/WP03-specify-plan-tasks-verbs.md (~L68, L279) cite mission_create.py:627 for create_mission's definition; actual post-merge line is 631.
- id: I5
  severity: low
  category: inconsistency
  summary: "tasks.md's mission-level note ('Same-file write-scope overlap...') states PR #3826 merged into main and this mission branch 'has not yet rebased onto that merge as of this tasks phase' — the branch has since merged main in (HEAD 0753bbffa, 'chore: merge main into mission branch before implementation'), so the rebase-status clause is now stale even though the underlying behavioural re-verification warning remains valid and should be kept."
---

## Specification Analysis Report

Mission: `design-phase-orchestrator-api-01M1HE6M`. Artifacts analyzed: `spec.md`, `plan.md`,
`tasks.md`, `wps.yaml`, `lanes.json`, `reviews/spec.ruling.md`, `tasks/WP01`-`WP09`, and the
project charter (`.kittify/charter/charter.md`), cross-checked against the current tree at
HEAD `0753bbffa` (which folded `origin/main`, including PR #3826's 191-line change to
`src/specify_cli/orchestrator_api/commands.py` and `mission_create.py`, into this mission
branch before this analysis).

### Findings Table

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| I1 | Inconsistency | MEDIUM | spec.md:~680 | `commands.py:1258-1266,1352-1360` cited for start-implementation/start-review's `wp_id`/`from_lane`/`to_lane` data dicts is stale post-merge | Update to `commands.py:1353-1355` (start-implementation) and `commands.py:1447-1449` (start-review) |
| I2 | Inconsistency | MEDIUM | spec.md:~726-727 | `commands.py:1239-1240,1333-1334` and `commands.py:1516-1517` (sync_dossier opt-outs) are stale post-merge | Update to `commands.py:1332-1333` (start-implementation), `commands.py:1426-1427` (start-review), `commands.py:1609-1610` (transition) |
| I3 | Inconsistency | HIGH | plan.md:~549; tasks/WP03-specify-plan-tasks-verbs.md:~94 | `commands.py:1286-1360` cited as the start-review pattern precedent now falls inside start_implementation's body, not start_review's | Update both citations to the current start_review span (~commands.py:1380-1465, data dict at 1447-1449) |
| I4 | Inconsistency | LOW | spec.md:~554; tasks/WP03-specify-plan-tasks-verbs.md:~68,279 | `mission_create.py:627` for `create_mission`'s definition is off by 4 lines post-merge | Update to `mission_create.py:631` |
| I5 | Inconsistency | LOW | tasks.md mission-level note | Claims the mission branch "has not yet rebased onto" PR #3826's merge; the branch has since merged main in (HEAD `0753bbffa`) | Update the note's rebase-status clause to reflect the merge has landed; keep its underlying behavioural re-verification warning for WP03's `create_mission`/`setup_plan` wrapper assumptions |

### Coverage Summary Table

| Requirement Key | Has Task? | Task IDs / WP | Notes |
|-----------------|-----------|----------------|-------|
| FR-001..FR-003 (specify/plan/tasks verbs) | Yes | WP03 (T009-T014) | Covered |
| FR-004/FR-005 (check-prerequisites/record-analysis) | Yes | WP04 (T015-T021) | Covered, incl. NFR-004 SK-93 sub-tests |
| FR-006..FR-009/FR-012 (OriginFlow decision verbs) | Yes | WP05 (T022-T027) | Covered |
| FR-010 (design-status) | Yes | WP06 (T028-T032) | Covered |
| FR-011 (CONTRACT_VERSION bump) | Yes | WP07 (T033-T035) | Covered |
| FR-013 (answer-decision) | Yes | WP08 (T036-T041) | Covered; hard-gated on WP02 |
| FR-014 (seam extraction) | Yes | WP02 (T004-T008) | Covered; sequenced before WP08 per C-005 |
| NFR-001..NFR-005 | Yes | WP01-WP08 (per-WP requirement_refs) | Covered |
| C-001..C-005 | Yes | Distributed across WP01-WP08 | Covered |
| SC-001..SC-008 | Yes | Distributed WP03-WP09 | Covered; SC-007/SC-008 specifically pinned to WP08/WP02 |

Zero requirements with no associated task; zero tasks with no mapped requirement.

### Charter Alignment Issues

None found. New verbs reuse existing service functions (single canonical authority); no
`src/kernel/` touch; ATDD-first discipline stated per-WP; terminology canon respected
(no `feature*` aliases introduced); silent-success class (NFR-002/NFR-004) explicitly
designed against with concrete SK-93 regression tests (SC-005 a/b/c).

### Ruling Traceability (SPEC-FRESH2-001)

Verified end-to-end: the operator ruling requiring `answer-decision` to reach
`_pair_previous_lifecycle_record`/`_emit_mission_next_invoked`/`_write_issuance_lifecycle_record`
via an extracted seam survives into `spec.md` (FR-014, C-005, User Story 5, Clarification 7),
`plan.md` (§(a) target-module decision, WP02/WP08 breakdown), and `tasks.md`
(WP02 = FR-014 seam extraction with the `assert_lifecycle_seam_effects` shared test helper;
WP08 explicitly declares "Hard gate: this WP CANNOT START until WP02 has actually landed" and
extends WP02's own `tests/specify_cli/next/test_next_invocation_lifecycle_seam.py` — the
dual-caller regression test named by SC-008 — rather than creating a new file). No drift found.

### Marker / CI Job Check (issue #3241, ledger SK-144)

All test-adding WPs (WP02-WP08) declare an explicit `pytestmark` in their task files matching
plan.md's Gate Set requirements (`pytest.mark.integration` (+`git_repo` where applicable) for
real-I/O tests, `pytest.mark.fast` for pure in-process verb tests, WP07 preserving the existing
file's marker). No unmarked new test module found.

### lanes.json / wps.yaml Consistency

`lanes.json`'s write scopes match `wps.yaml`'s `owned_files` per WP exactly. The documented
3-lane collapse (WP01-WP06/WP08 into `lane-a` due to shared `owned_files` on `commands.py`/
`next_cmd.py`) is expected and already narrated in tasks.md's mission-level note — not
re-litigated here. The dependency graph is unaffected by the collapse: `lane-b`
(`depends_on_lanes: ["lane-a"]`) matches WP07's dependency on WP03/04/05/06/08 (all in
lane-a); `lane-planning` (`depends_on_lanes: ["lane-a","lane-b"]`) matches WP09's dependency
on WP03-WP08.

### Silent-Success Check

No specified path found that returns `None`/`unknown`/`0` where it should raise/report/refuse.
`record-analysis`'s NFR-004 mechanism (artifact re-read + freshness correlation + time-bound)
and every new verb's `NFR-002` structured-`error_code` requirement are both concretely
testable (SC-004, SC-005 a/b/c) rather than aspirational.

### Metrics

- Total Requirements (FR+NFR+C): 14 FR + 5 NFR + 5 C = 24
- Total Tasks: 46 (T001-T046)
- Coverage %: 100% (all requirements have >=1 associated WP/task)
- Ambiguity Count: 0
- Duplication Count: 0
- Critical Issues Count: 0
- High Issues Count: 1 (I3 — stale actionable pattern-precedent citation)

## Next Actions

- Fix I1-I5 (all stem from the same root cause: PR #3826's merge into `main`, folded into this
  mission branch at `0753bbffa`, shifting line numbers by roughly +93 to +95 lines in
  `orchestrator_api/commands.py` and +4 in `mission_create.py`, after the spec/plan/tasks
  citations were authored against the pre-merge tree).
- Re-run `record-analysis` after the fix to confirm a findings-free, `verdict: ready` report.
- No charter violations, no coverage gaps, no ruling-traceability drift — the mission is
  otherwise ready to proceed to implementation once the citations above are corrected.
