---
schema_version: 1
artifact_type: spec-kitty.analysis-report
command: /spec-kitty.analyze
mission_slug: ci-scoping-gate-reliability-01KZP80D
mission_id: 01KZP80DVZ9JF77DG23CJ6YNR1
generated_at: '2026-08-10T17:02:52.457036+00:00'
analyzer_agent: unknown
input_artifacts:
  spec.md:
    path: /home/stijn/Documents/_code/SDD/fork/spec-kitty/kitty-specs/ci-scoping-gate-reliability-01KZP80D/spec.md
    sha256: bb34fe49dbb12c41a2c073b3cffc2dec7f7acaa253780f4d2d712fcfe4bc9ab2
  plan.md:
    path: /home/stijn/Documents/_code/SDD/fork/spec-kitty/kitty-specs/ci-scoping-gate-reliability-01KZP80D/plan.md
    sha256: 9b61abb2b8cefda33fefd8e20df0c2f92ebe8678fddab69195a74655b99ea06b
  tasks.md:
    path: /home/stijn/Documents/_code/SDD/fork/spec-kitty/kitty-specs/ci-scoping-gate-reliability-01KZP80D/tasks.md
    sha256: 89408cc78c2a07bdc610f77258f97033426024c5a22aa15fc480cbf26d03ff9c
  charter:
    path: /home/stijn/Documents/_code/SDD/fork/spec-kitty/.kittify/charter/charter.yaml
    sha256: b1003d05f2c4dc81836a5391c898cd1dadebb1f222bd4579d1cb0f8fc4168284
verdict: ready
issue_counts:
  high: 0
  critical: 0
  medium: 2
  low: 2
  info: 0
findings:
- id: I1
  severity: medium
  category: inconsistency
  summary: NFR-003 names ci_topology_census.json as a guard that 'stays green with the new group claimed', which reads as add-a-census-row; the authoritative tracer M2 forbids touching the census (a corpus row reds test_ci_topology_worklist). The census stays green precisely by NOT being edited.
- id: I2
  severity: medium
  category: underspecification
  summary: NFR-004 'No double-run' is stated absolutely, but the M1 @pytest.mark.corpus design has a bounded residual overlap (a marked tests/doctrine module also runs in fast-tests-doctrine on push/mixed PRs). NFR-004 must be read as 'no whole-directory re-run', not 'zero test re-run', or a reviewer could hold the implementer to an unachievable literal standard.
- id: A1
  severity: low
  category: ambiguity
  summary: FR-005's 'via a CI trigger/config boolean' implies NEW config is required for the retained whole-tree scan, but tracer M3 establishes that the EXISTING unfiltered push:main run already satisfies FR-005; a schedule/boolean is optional/additive.
- id: T1
  severity: low
  category: terminology
  summary: Spec US3/FR-004 say 'the blocking dead-link check' (singular), but the gate is actually TWO checks (relative_link_fixer --check + related_validator --strict). WP02 correctly scopes both; the singular phrasing could mislead a reader into scoping only one.
---

## Specification Analysis Report

Mission `ci-scoping-gate-reliability-01KZP80D` (#3008 corpus gate + #3147 docs diff-scope). The
artifacts were already remediated by the authoritative post-plan squad
([tracer-squad-findings.md](./tracer-squad-findings.md)); the WP prompts fold B1/M1-M5/N1-N2. No
CRITICAL or HIGH findings — coverage is complete and no charter MUST is violated. The findings below
are wording-precision inconsistencies where the **spec prose** lags the **authoritative tracer**; each
is already handled correctly in the WP prompts, so they are advisory, not blocking.

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| I1 | Inconsistency | MEDIUM | spec.md:78 (NFR-003); tracer M2; WP01 T002 | NFR-003 lists `ci_topology_census.json` among guards that "stay green with the new group claimed" — reads as *add a census row*; M2 forbids it (reds `test_ci_topology_worklist`). | Read NFR-003 as: census stays green because corpus is NON-src and is NOT added. WP01 T002/Context already say "do NOT touch census" — no code change needed; note the reconciliation. |
| I2 | Underspecification | MEDIUM | spec.md:79 (NFR-004); tracer M1; WP01 T003 | "No double-run" stated absolutely; the `-m corpus` marker leaves a bounded residual (marked `tests/doctrine` module runs in both `fast-tests-doctrine` and `fast-tests-corpus` on push/mixed PRs). | Interpret NFR-004 as "no whole-directory re-run"; the bounded marker overlap is accepted per M1. WP01 T003 already states this honestly in the job-header guidance. |
| A1 | Ambiguity | LOW | spec.md:70 (FR-005); tracer M3; WP02 T010 | "via a CI trigger/config boolean" implies new config; M3 says the existing unfiltered `push:main` run already satisfies FR-005. | Treat the existing `push:main` backstop as the FR-005 mechanism; a `schedule:` is optional/additive. WP02 T010 already retains the backstop. |
| T1 | Terminology | LOW | spec.md:41-52 (US3), 69 (FR-004); WP02 | Singular "dead-link check" vs two actual gates (`relative_link_fixer` + `related_validator`). | No change needed — WP02 scopes both. Keep the reviewer aware both must be diff-scoped + fail-closed. |

**Coverage Summary Table:**

| Requirement Key | Has Task? | Task IDs | Notes |
|-----------------|-----------|----------|-------|
| FR-001 corpus paths trigger workflow | ✅ | T001 | Both `pull_request.paths` + `push.paths` |
| FR-002 corpus group + blocking job | ✅ | T002, T003, T004, T005 | 5-edit group pattern + `-m corpus` + gate edge |
| FR-003 narrow corpus globs | ✅ | T001 | Excludes `status.events.jsonl`/notes/trace |
| FR-004 diff-scoped blocking dead-link gate | ✅ | T008, T009, T010, T012 | Both scripts, fail-closed |
| FR-005 retained whole-tree scan (non-blocking) | ✅ | T010 | Existing `push:main` backstop retained |
| NFR-001 corpus gate blocking | ✅ | T004 | `quality-gate.needs` edge |
| NFR-002 no false-trigger on churn | ✅ | T006, T007 | Path-filter + completeness invariant |
| NFR-003 arch invariants co-evolve | ✅ | T006, T007 | See I1 (census reconciliation) |
| NFR-004 no double-run | ✅ | T003, T005 | See I2 (bounded overlap) |
| C-001 no wholesale kitty-specs | ✅ | T001 | |
| C-002 whole-tree scan retained | ✅ | T010 | |
| C-003 reuse canonical CI machinery | ✅ | T002, T003 | Mirrors `docs` group + `fast-tests-docs` |

**Charter Alignment Issues:** None. The mission strengthens architectural-gate discipline
(co-evolves guards, no `# noqa`/skip), uses canonical CI machinery (C-003), and removes a false-green
(corpus skip) + a false-red (docs whole-tree) — all aligned with the charter's quality standing orders.

**Unmapped Tasks:** None. All 12 subtasks map to ≥1 requirement.

**Metrics:**

- Total Requirements: 12 (5 FR + 4 NFR + 3 C); Success Criteria: 4
- Total Tasks (subtasks): 12; Work Packages: 2 (parallel lanes lane-a/lane-b)
- Coverage %: 100% (every FR/NFR/C has ≥1 subtask)
- Ambiguity Count: 1 (A1); Inconsistency/Underspec: 2 (I1, I2); Terminology: 1 (T1)
- Critical Issues Count: 0 (High: 0)

## Next Actions

- **Verdict: READY** — no CRITICAL/HIGH; the implement gate is unblocked.
- The four findings are spec-prose lag already reconciled in the WP prompts; no artifact edits are
  required to proceed. If desired, a later spec touch-up could tighten NFR-003/NFR-004/FR-005 wording,
  but that is optional and out of this mission's scope.
- Proceed: investigate-squad pass (CI-config on blocking gates is high-risk) → `/spec-kitty.implement`
  WP01 + WP02 (python-pedro / sonnet), then per-WP review (reviewer-renata / opus).
