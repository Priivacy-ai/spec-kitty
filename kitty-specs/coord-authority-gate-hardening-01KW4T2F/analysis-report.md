---
schema_version: 1
artifact_type: spec-kitty.analysis-report
command: /spec-kitty.analyze
mission_slug: coord-authority-gate-hardening-01KW4T2F
mission_id: 01KW4T2F7ZHCB41Z4X12TH28D2
generated_at: '2026-06-27T18:04:08.727942+00:00'
analyzer_agent: unknown
input_artifacts:
  spec.md:
    path: /home/stijn/Documents/_code/SDD/fork/spec-kitty/kitty-specs/coord-authority-gate-hardening-01KW4T2F/spec.md
    sha256: 33134fe414a21384bba32ebb9eb0a1f61a33a58dcedb6436ff7318c10618158d
  plan.md:
    path: /home/stijn/Documents/_code/SDD/fork/spec-kitty/kitty-specs/coord-authority-gate-hardening-01KW4T2F/plan.md
    sha256: 143845135cf3a25475579794bfa1504c9c37f22042fc5e416f4ee30b3041519f
  tasks.md:
    path: /home/stijn/Documents/_code/SDD/fork/spec-kitty/kitty-specs/coord-authority-gate-hardening-01KW4T2F/tasks.md
    sha256: 294949148df29a0e2441276855621dfcc40265676eb157d25a9eb8ae276a65f3
  charter:
    path: /home/stijn/Documents/_code/SDD/fork/spec-kitty/.kittify/charter/charter.md
    sha256: d393b068f20eab1bb918c2f53e669d01048f049e8b0f948ff6001fc280517c08
verdict: ready
issue_counts:
  medium: 1
  high: 0
  critical: 0
  low: 2
  info: 0
findings:
- id: I1
  severity: low
  category: inconsistency
  summary: Partition naming drift — spec/SC-003 says 'PRIMARY/STATUS partition'; data-model/contracts/WP04 use 'PRIMARY/COORD' and the live frozenset is _PLACEMENT_ARTIFACT_KINDS. Three labels (STATUS/COORD/PLACEMENT) for one partition.
- id: U1
  severity: low
  category: underspecification
  summary: WP03/T011 says to thread repo_root/main_root into _build_finalized_override_query_decision and update 'the single call site (~:3288)' but does not pin which root object is in scope at that call site; implementer must confirm a repo_root is reachable there.
- id: M1
  severity: medium
  category: coverage
  summary: NFR-003's verbatim full-tests/architectural dry-run is a PR-body deliverable owned by WP02 but produced only at mission-PR time; no single WP DoD can self-verify it pre-merge, so it risks being skipped at the per-WP gate.
---

## Specification Analysis Report

Mission **coord-authority-gate-hardening-01KW4T2F**. Artifacts analyzed: spec.md (8 FR, 5 NFR, 7 C, 6 SC), plan.md (IC-A1/A2/A3, IC-B, IC-C), tasks.md (4 WP / 17 subtasks). This mission was hardened by a post-spec squad, a post-plan squad, and a post-tasks anti-laziness squad (debbie/renata/paula, 2026-06-27); their findings are already folded in, so this pass is a residual consistency check.

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| I1 | Inconsistency | LOW | spec.md SC-003 / data-model.md §6 / WP04 | One partition carries three labels: spec calls it "PRIMARY/STATUS", data-model/WP04 use "PRIMARY/COORD", and the live code frozenset is `_PLACEMENT_ARTIFACT_KINDS`. | Non-blocking; the live frozenset names are authoritative. Optionally note in WP04 that COORD == the `_PLACEMENT_ARTIFACT_KINDS` (STATUS-partition) set so the implementer doesn't second-guess. |
| U1 | Underspecification | LOW | tasks/WP03 T011 | Threading `repo_root`/`main_root` into `_build_finalized_override_query_decision` assumes a repo root is reachable at the ~:3288 call site; not pinned. | Implementer confirms a `repo_root` is in scope at the caller (verified reachable via `_primary_runtime_feature_dir(repo_root, …)` already in the module); add the parameter and pass it. Low risk. |
| M1 | Coverage | MEDIUM | tasks/WP02 (NFR-003) / spec NFR-003 | The verbatim full-`tests/architectural/` dry-run is a PR-body artifact, produced at mission-PR time, not provable inside a single WP's per-review gate. | Accept as a mission-PR deliverable (already flagged in WP02 review guidance + cross-cutting acceptance). Ensure the mission-review / PR step carries it; not a per-WP blocker. |

**Coverage Summary Table:**

| Requirement Key | Has Task? | Task IDs | Notes |
|-----------------|-----------|----------|-------|
| FR-001 one-hop cross-function | ✅ | WP01 / T001,T003,T005 | resolver-vocab widen + module caller index |
| FR-002 identity scope-unify | ✅ | WP02 / T006 | merge/+lanes/+core/worktree_topology.py |
| FR-003 named census + exclusions | ✅ | WP02 / T008,T009 | per-arm stale-pin split |
| FR-004 preview routing | ✅ | WP03 / T011,T012 | caller-only leg-split |
| FR-005 runtime/next scan + floor | ✅ | WP02 / T007 | non-vacuity floor |
| FR-006 partition rationale map | ✅ | WP04 / T014,T015 | net-new + all-kinds anti-mutant |
| FR-007 husk no-op | ✅ | WP04 / T016,T017 | production husk + tasks/-present variant |
| FR-008 attribute-discipline | ✅ | WP01 / T002,T005 | ast.Attribute branch |
| NFR-001 CT7 composite-key | ✅ | all WP / cross-cutting | zero file:line anchors |
| NFR-002 self-mutation + anti-vacuity | ✅ | WP01 T005 / WP02 T010 | per-shape RED/GREEN |
| NFR-003 full-gate dry-run | ⚠️ | WP02 / mission-PR | see M1 (PR-body deliverable) |
| NFR-004 zero false positives | ✅ | WP02 / T008,T010 | census route-or-pin |
| NFR-005 non-positive friction | ✅ | WP04 / cross-cutting | no line-pins |

**Charter Alignment Issues:** None. Plan's Charter Check passed (CT7-conformant content anchors, no-direct-push/PR policy, Terminology Canon — "Mission"/"WP", no `feature*` aliases). The mission's single production edit (FR-004) is explicitly scoped (C-003).

**Unmapped Tasks:** None. All 17 subtasks roll up to a mapped FR/NFR/SC.

**Metrics:**
- Total Requirements: 8 FR + 5 NFR = 13 normative
- Total Tasks: 4 WP / 17 subtasks
- Coverage %: 100% (every FR + NFR has ≥1 task; NFR-003 carried as a mission-PR deliverable)
- Ambiguity Count: 0 unresolved placeholders
- Duplication Count: 0
- Critical Issues Count: 0

## Next Actions

No CRITICAL or HIGH findings → **verdict: ready**. Proceed to `/spec-kitty.implement`. The two LOW + one MEDIUM are advisory and already mitigated in the WP prompts; none blocks implementation. Carry M1 (the full-gate dry-run) into the mission-PR / review step per NFR-003 (gate-unmask-cannot-self-validate).
