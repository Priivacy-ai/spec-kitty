---
doc_status: active
updated: '2026-08-11'
---

# Assertive Test-Suite Sanitation — Final Report

Closure state: **for-review-with-explicit-gate-misses**  
Evidence commit: `f527f8733b87d567957b771101405478309b8b70`  
Generated: `2026-08-11T06:45:00Z`

## Outcome

The integrated suite is leaner by 64 Python test files, 971 source units, 1,431 collected nodes, and 27,371 Python test LOC. The exact integrated repository suite is green. The 1.3815% SC-003 criterion miss remains explicit and is accepted by the root operator under the user-directed KISS wrap; it is not rewritten as a pass. Current PR CI proves Windows success while Linux/macOS jobs remain in progress. Inherited current-main mypy debt and the narrowly scoped nested-wheel-build sibling exception remain visible.

## Before / after inventory

This table is the frozen pre-maintainer-review census. The reroll restores
three Python guard modules plus one baseline file and renames one support
module; `reroll-disposition-overrides.yaml` is authoritative for that delta.

| Metric | Repaired planning base | Integrated HEAD | Delta |
|---|---:|---:|---:|
| python_test_files | 2731 | 2667 | -64 |
| source_units | 29766 | 28795 | -971 |
| collected_nodes | 37444 | 36013 | -1431 |
| python_test_loc | 833936 | 806565 | -27371 |
| exact_duplicate_groups | 173 | 43 | -130 |
| inert_candidates | 15 | 0 | -15 |
| scanner_candidates | 234 | 131 | -103 |

## Terminal disposition ledger

The generated aggregate contains **1446** rows over **2286** unique identities: 815 DELETE, 519 KEEP, 112 CONSOLIDATE. No `FIX_*`, `TEMPORARY`, expired, renewed, ambiguous, or unowned frozen candidate remains.

Maintainer review after this frozen aggregate reversed three structural-gate
deletions, confirmed the retained zero-orphan successor in the PR operator gate,
and renamed one zero-test support module. GitHub branch protection currently
requires only `drift-detector`; `quality-gate` is operator-enforced, not a
required context. The machine-readable current authority is
`reroll-disposition-overrides.yaml`; raw probe artifacts remain immutable.

Aggregate SHA-256: `6cfa84f91c8a7580773a1ba85af6e46e1776d2ad3f5228d9411260de9f4c1ad2`  
HEAD census SHA-256: `44349d051e845bc13a97babb59eb4034bebb515ab85cc9bc3ba111a6613c9bda`

## Performance criteria

| Measure | Base | HEAD | Change | Verdict |
|---|---:|---:|---:|---|
| frozen changed-route critical path | 62.25s | 61.39s | -1.3815% | MISS: below 15% |
| matched cold wall-clock scanner | 54.42s | 44.66s | -17.93% | PASS |
| full parallel suite | 1538.778s (red) | 1136.45s (green) | -26.15% | informational; environments/commits differ |

SC-003 remains an explicit miss: the comparable frozen-DAG critical-path reduction is 1.3815%, not the required 15%; no threshold was widened and no signal was deleted to manufacture a pass.

## Repaired-base vs integrated-HEAD outcomes

Repaired-base failures were dispositioned; exact integrated HEAD full suite is green. Separate required gates expose inherited/tooling and environment failures rather than hidden suite failures.

- **resolved:** 27 repaired-base call failures plus 3 teardown phase errors were terminally adjudicated; integrated full suite has 0 failures and 0 errors.
- **shared:** No accepted live full-suite red remains at integrated HEAD.
- **head_only:** Project mypy reports 10 redundant-cast errors in six files byte-identical to origin/main; sibling E2E reports two daemon source/executable-boundary failures; neither is represented as a green result.

## Acceptance criteria

| Criterion | Result | Evidence / rationale |
|---|---|---|
| SC-001 | pass | 15 frozen inert candidates terminally owned; HEAD inert candidates=0. |
| SC-002 | pass | Candidate universe exact365/inert15/scanner234 validates with zero missing, ambiguous, or duplicate ownership. |
| SC-003 | fail | Frozen changed-route critical-path reduction is 1.3815%, below 15%. Root operator accepts this recorded miss under the user-directed KISS wrap; no waiver or fabricated pass. |
| SC-004 | fail | Contract and architecture pass; dependent_wp_planning_lane passes after one daemon restart; contract_drift_caught has the narrow nested-wheel-build exception; Windows CI is green; current Linux/macOS CI is still in progress. |
| SC-005 | pass | Three consecutive WP02 clean starts reached real test bodies with no bootstrap cascade. |
| SC-006 | pass | Deterministic aggregate/census, terminal issue rows, and independent approvals for dependency WPs are present. |

## Workflow deviations and review

- Review cap: three cycles per WP; fourth cycles prohibited and not opened.
- Arbiter normalization: content-addressed legacy-shard-normalization.yaml supersedes capped WP06/WP09/WP10 legacy rows without source-shard mutation or cycle 4.
- Independent WP approvals: WP01-WP07 and WP09-WP15 approved before WP08 integration; WP08 independent review still required.
- Remaining closure blockers: Root-accepted SC-003 criterion miss remains red; current Linux/macOS PR jobs are in progress; inherited origin/main mypy debt is recorded separately.

See `issue-matrix.md` and `workflow-evidence.md` for terminal issue and gate details.
