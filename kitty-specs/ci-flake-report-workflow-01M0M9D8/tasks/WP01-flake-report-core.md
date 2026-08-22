---
work_package_id: WP01
title: Flake-report pure core (taxonomy, classification, false-red formula, delta cursor, aggregation)
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-015
- NFR-001
- NFR-004
planning_base_branch: qa/test-hardening
merge_target_branch: qa/test-hardening
branch_strategy: Planning artifacts for this mission were generated on qa/test-hardening. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into qa/test-hardening unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
history: []
agent_profile: python-pedro
authoritative_surface: scripts/ci/
create_intent:
- scripts/ci/flake_report.py
- tests/ci/test_flake_report_core.py
execution_mode: code_change
owned_files:
- scripts/ci/flake_report.py
- tests/ci/test_flake_report_core.py
tags: []
tracker_refs: []
---

# WP01 — Flake-report pure core

**Capability A** · profile: python-pedro · deps: none · refs: FR-001, FR-002, FR-003, FR-004, FR-005, FR-015, NFR-001, NFR-004

## Objective

Build the pure, IO-free core of `scripts/ci/flake_report.py` — deterministic functions with no `gh`/network/filesystem, fully unit-testable. The IO shell/CLI is WP02.

## Subtasks

- **T001 — Conclusion taxonomy (FR-001).** `is_completed(conclusion)` / `is_excluded(conclusion)`: completed = {success, failure, timed_out, startup_failure}; excluded from all metrics = {cancelled, action_required, skipped, neutral, stale}. `tally(runs)` → denominators (total_runs, completed_runs, distinct_prs by PR number w/ headBranch fallback, prs_with_failure).
- **T002 — Classifier (FR-002).** `classify_one(failed_nodeids, log_text, job_names, infra_signals, gate_signals) -> (bucket, reason)` per the data-model signature contract (nodeid-keyed `is_timing`; mixed→real; infra-only→infra_flake; unmatched→needs_review). `TIMING_NODEIDS` seed constant. `false_red_rate(counts)` = (perf_timing_flake+infra_flake)/(…+real), needs_review excluded.
- **T003 — Duration aggregation (FR-003).** `aggregate_durations(samples)` → per-nodeid n/median/mean/max, `long_pole = median>2.0` (stdlib `statistics`).
- **T004 — Delta cursor (FR-004/005).** `resolve_window(prev_state, now)` (half-open on completion time; first_run/lost_baseline → trailing 30d); `advance_cursor(runs)` (monotonic `completed_through`; `in_progress_low_water` so straddling runs enumerate once; re-run/new-attempt keyed on run-id+attempt).
- **T005 — Coverage + determinism (FR-015/NFR-004).** `classifier_coverage(counts)` = 1 − needs_review/failures; stable ordering helpers; record enumerated run-id set into the state model.

## ATDD / tests (`tests/ci/test_flake_report_core.py`)

Red-first per behavior: taxonomy excludes cancelled/action_required from both numerator and denominator; false-red formula matches the squad's 0.586 on synthetic counts; mixed run → real; unmatched → needs_review; half-open boundary (`>` not `>=`); straddling run counted once; re-run new-attempt re-picked; cursor never regresses; long_pole threshold. Use production-shaped nodeids/run ids (realistic-test-data). Zero `ruff`/`mypy --strict` issues; complexity ≤ 15 (extract helpers).

## Done when

All core functions exist with direct unit tests green; no IO in this module's tested surface; NFR-001 clean.
