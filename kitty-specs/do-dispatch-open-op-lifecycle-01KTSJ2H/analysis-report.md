---
schema_version: 1
artifact_type: spec-kitty.analysis-report
command: /spec-kitty.analyze
mission_slug: do-dispatch-open-op-lifecycle-01KTSJ2H
mission_id: 01KTSJ2H8E5YF2EGJYGAE5Z5Q2
generated_at: '2026-06-10T20:35:35.464853+00:00'
analyzer_agent: unknown
input_artifacts:
  spec.md:
    path: /Users/robert/spec-kitty-dev/spec-kitty-20260610-210527-m9vDkX/spec-kitty/kitty-specs/do-dispatch-open-op-lifecycle-01KTSJ2H/spec.md
    sha256: 119b56f156b45137b025d0b5abea01208ecd7110cb009a9d25e77266772c1a41
  plan.md:
    path: /Users/robert/spec-kitty-dev/spec-kitty-20260610-210527-m9vDkX/spec-kitty/kitty-specs/do-dispatch-open-op-lifecycle-01KTSJ2H/plan.md
    sha256: 58cd4fbb9666c7a35da2d825988e35e09812f331a8001c2c5acd5908ffff911e
  tasks.md:
    path: /Users/robert/spec-kitty-dev/spec-kitty-20260610-210527-m9vDkX/spec-kitty/kitty-specs/do-dispatch-open-op-lifecycle-01KTSJ2H/tasks.md
    sha256: 2a48efe2b2ae01554190ab507a0cac93ce905c3d7e8f69ca89b7724c6295e1af
  charter:
    path: /Users/robert/spec-kitty-dev/spec-kitty-20260610-210527-m9vDkX/spec-kitty/.kittify/charter/charter.md
    sha256: a59cddc8725b34acacd83b9bec24e97b1ae68aa80716b7335c425c6106c18791
verdict: blocked
issue_counts:
  critical: 0
  high:
  medium:
  low:
---

---
schema_version: 1
artifact_type: spec-kitty.analysis-report
command: /spec-kitty.analyze
mission_slug: do-dispatch-open-op-lifecycle-01KTSJ2H
mission_id: 01KTSJ2H8E5YF2EGJYGAE5Z5Q2
generated_at: '2026-06-10T20:26:52.341997+00:00'
analyzer_agent: unknown
input_artifacts:
  spec.md:
    path: /Users/robert/spec-kitty-dev/spec-kitty-20260610-210527-m9vDkX/spec-kitty/kitty-specs/do-dispatch-open-op-lifecycle-01KTSJ2H/spec.md
    sha256: 7e23d24f0f62f1f34985949969067039a1bee7cb055c6f8a4f32eb8cb4a3b697
  plan.md:
    path: /Users/robert/spec-kitty-dev/spec-kitty-20260610-210527-m9vDkX/spec-kitty/kitty-specs/do-dispatch-open-op-lifecycle-01KTSJ2H/plan.md
    sha256: 58cd4fbb9666c7a35da2d825988e35e09812f331a8001c2c5acd5908ffff911e
  tasks.md:
    path: /Users/robert/spec-kitty-dev/spec-kitty-20260610-210527-m9vDkX/spec-kitty/kitty-specs/do-dispatch-open-op-lifecycle-01KTSJ2H/tasks.md
    sha256: 2a48efe2b2ae01554190ab507a0cac93ce905c3d7e8f69ca89b7724c6295e1af
  charter:
    path: /Users/robert/spec-kitty-dev/spec-kitty-20260610-210527-m9vDkX/spec-kitty/.kittify/charter/charter.md
    sha256: a59cddc8725b34acacd83b9bec24e97b1ae68aa80716b7335c425c6106c18791
verdict: blocked
issue_counts:
  critical: 0
  high:
  medium:
  low:
---

# Specification Analysis Report

**Mission**: do-dispatch-open-op-lifecycle-01KTSJ2H · **Date**: 2026-06-10 · **Artifacts**: spec.md, plan.md, tasks.md (+ 6 WP prompts, research.md, data-model.md, contracts/)

## Findings

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| C1 | Coverage | HIGH | spec.md NFR-001; tasks.md | NFR-001 (dispatch latency regression ≤10%) has no measuring task. WP02 mentions it only as a reviewer risk note; no subtask establishes a baseline or measures post-change latency, so the threshold is unverifiable. | Add a validation step to WP02/T010 (timeit-style smoke comparing dispatch wall-clock before/after, or assert propagator submission is non-blocking via spy) or consciously accept review-by-inspection and record that in plan.md. |
| C2 | Coverage | MEDIUM | spec.md NFR-002; WP04 T018 | NFR-002 specifies <5 s at 10,000 Op files, but T018 tests 1,000 files pro-rated (<0.5 s) with the close mocked. The 10k budget is extrapolated, never exercised. | Acceptable trade-off for suite speed; note the extrapolation in WP04's DoD or add an opt-in slow test marker for the full 10k case. |
| I1 | Inconsistency | MEDIUM | data-model.md (migration table) vs WP05 T020 | The data-model migration table says legacy `actor` is "preserved" but does not define missing/empty handling; WP05 introduces a binding `"unrecorded"` placeholder rule (also for `action`, and a `completed_at`→`started_at` fallback) that exists nowhere upstream. | Backfill the `"unrecorded"` rule and `completed_at` fallback into the data-model migration table so the reviewer's normative source matches the WP instruction. |
| I2 | Inconsistency | LOW | spec.md FR-009 vs research.md R5 / WP06 | FR-009 conditions the Stop hook on feasibility ("otherwise documented as follow-up"); research R5 resolved it as feasible and WP06 commits to it unconditionally. Direction is consistent but the spec still reads as undecided. | No action required; optionally tighten FR-009 wording post-R5. The decision trail (R5) already documents the resolution. |
| A1 | Ambiguity | LOW | WP06 T023; spec FR-009 | Session-start open-Ops listing has no performance bound, yet runs on every Claude Code session. "Keep it fast … no git calls" is directional, not measurable. | Optionally bound it (e.g., reuse the NFR-002 scan budget pro-rata). Low risk: the orphan scan is the same code path NFR-002 already constrains. |
| A2 | Ambiguity | LOW | WP05 frontmatter/filename | Migration module name `m_3_2_1_op_record_schema_v2.py` guesses the next release version; the WP flags this itself but the owned_files glob pins the literal name — a rename at implementation time would step outside owned_files. | Implementer should treat the version segment as variable; reviewer should accept the renamed file as in-scope (rationale already in the WP). |
| T1 | Terminology | LOW | spec.md, plan.md, contracts/ | "Op", "invocation", and "profile-invocation" coexist. spec.md's Domain Language section sanctions this (canonical "Op"; CLI surface retains `profile-invocation`), so drift is contained but real for future readers. | None now; the deferred `dispatch` rename mission (#1810) is the natural place to unify the CLI surface. |
| D1 | Duplication | LOW | contracts/cli-do-output.md §Close surface vs contracts/op-record-events.md §Git behavior | Close-surface semantics (idempotency, auto-commit) are stated in both contracts. Currently consistent; dual statement risks future drift. | Keep op-record-events.md as the single normative source for record/git behavior; treat the cli-do-output mention as informative. |

No CRITICAL findings. No charter violations detected.

## Coverage Summary

| Requirement | Has Task? | Task IDs | Notes |
|-------------|-----------|----------|-------|
| FR-001 | ✓ | T006, T010 | |
| FR-002 | ✓ | T008, T009 | |
| FR-003 | ✓ | T011, T012, T014 | |
| FR-004 | ✓ | T001–T003, T005 | |
| FR-005 | ✓ | T002, T004 | File-level readability |
| FR-006 | ✓ | T015, T016 | |
| FR-007 | ✓ | T015, T016, T018 | |
| FR-008 | ✓ | T007 | |
| FR-009 | ✓ | T023, T024, T027 | |
| FR-010 | ✓ | T025, T026 | |
| FR-011 | ✓ | T019–T022 | |
| FR-012 | ✓ | T013 | |
| NFR-001 | ✗ | — | **Finding C1** |
| NFR-002 | partial | T018 | Finding C2 (pro-rated) |
| NFR-003 | ✓ (process) | all WP DoDs | Coverage/mypy/ruff gates in every WP |
| NFR-004 | ✓ | T021, T022 | Idempotency double-run test |
| C-001…C-005 | ✓ (constraints) | — | Carried as WP context/risk notes; C-005 explicitly policed in WP06 |

## Charter Alignment Issues

None. Stack (typer/rich/pydantic/pytest/mypy), 90%+ coverage, mypy --strict, and CLI integration tests are embedded in every WP's Definition of Done. DIRECTIVE_003 satisfied via decision record DM-01KTSJEQANMNEV16WMSAJP6FR1 + research.md rationale entries.

## Unmapped Tasks

None — all 27 subtasks (T001–T027) map to at least one FR/NFR via their WP's `requirement_refs`.

## Metrics

- Total Requirements: 12 FR + 4 NFR + 5 C
- Total Tasks: 27 subtasks across 6 WPs
- Coverage: 12/12 FRs (100%); NFRs 3/4 fully, 1 partial
- Ambiguity Count: 2 (LOW)
- Duplication Count: 1 (LOW)
- Critical Issues Count: 0

## Next Actions

No CRITICAL findings — implementation may proceed. Recommended before `/spec-kitty.implement`:

1. **C1 (HIGH)**: decide NFR-001 verification — cheapest fix is one added assertion in WP02/T010 that propagator submission is non-blocking (spy + no-sleep), which is the only latency-relevant change.
2. **I1 (MEDIUM)**: one-line additions to data-model.md's migration table (`"unrecorded"` placeholder, `completed_at` fallback) so WP05's reviewer has a normative source.
3. C2/A1/A2/I2/T1/D1: proceed as-is; they are documented trade-offs or contained drift.

## Remediation Log (2026-06-10, post-report)

All 8 findings addressed before implementation:
- **C1**: WP02/T010 gained a non-blocking-propagator assertion (NFR-001 now verifiable).
- **C2**: WP04/T018 gained an opt-in `slow`-marked 10k-file test as the authoritative NFR-002 check.
- **I1**: data-model.md migration table backfilled with the `"unrecorded"` placeholder rule and `completed_at`→`started_at` fallback.
- **I2**: spec.md FR-009 and acceptance scenario 7 tightened — Stop hook unconditionally in scope per research R5.
- **A1**: WP06/T023 gained a measurable bound (<0.5 s at 1k Op files, shared with the T018 pro-rata budget).
- **A2**: WP05 owned_files glob loosened to `m_*_op_record_schema_v2.py` so the version segment can match the release at implementation time.
- **T1**: spec.md Domain Language now states explicitly that `profile-invocation` remains the close-command term until #1810.
- **D1**: contracts/cli-do-output.md close-surface section marked informative; op-record-events.md declared normative.
