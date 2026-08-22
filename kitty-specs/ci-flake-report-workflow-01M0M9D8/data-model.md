# Data Model & Contracts: CI Flake-Report Workflow

Phase 1 design output. Defines the artifact schemas, the delta-state cursor, and the classifier signature contract. All JSON is stdlib-serializable; no third-party schema lib (NFR-001).

## 1. `state.json` — delta baseline (FR-004/007/015)

The lineage-critical artifact. Uploaded under a **stable name** independent of the workflow display name; `retention-days: 90`.

```json
{
  "schema": 1,
  "generated_at": "2026-08-22T05:00:00Z",
  "target_workflow": "ci-quality.yml",
  "cursor": {
    "completed_through": "2026-08-21T23:14:07Z",
    "in_progress_low_water": "2026-08-21T22:50:00Z"
  },
  "enumerated_run_ids": [32554963783, 32549865287],
  "lineage": "ok",
  "headline": {
    "window_start": "2026-08-14T23:14:07Z",
    "window_end": "2026-08-21T23:14:07Z",
    "completed_runs": 57,
    "failures": 29,
    "false_red_rate": 0.586,
    "buckets": {"perf_timing_flake": 14, "infra_flake": 3, "real": 12, "needs_review": 0},
    "classifier_coverage": 1.0
  }
}
```

- **`cursor.completed_through`**: half-open upper bound — next run processes completions `>` this. Monotonic; never regresses even under manual `workflow_dispatch` backfill.
- **`cursor.in_progress_low_water`**: earliest still-in-progress run at report time; the next delta re-enumerates from here so a straddling run is counted exactly once when it completes (FR-004).
- **`enumerated_run_ids`**: makes NFR-004 determinism verifiable (FR-015).
- **`lineage`**: `first_run` | `ok` | `lost_baseline` (prior artifact missing/corrupt → 30-day fallback, FR-005/007).

**Read contract**: schema-validate on load; on invalid or missing → `lineage = lost_baseline`/`first_run`, window = trailing 30 days.

## 2. `metrics.json` — headline + delta (FR-002/015)

```json
{
  "schema": 1,
  "window": {"start": "...", "end": "...", "target_workflow": "ci-quality.yml"},
  "denominators": {"total_runs": 100, "completed_runs": 57, "distinct_prs": 41, "prs_with_failure": 11},
  "failures": {"total": 29, "buckets": {"perf_timing_flake": 14, "infra_flake": 3, "real": 12, "needs_review": 0}},
  "false_red_rate": 0.586,
  "classifier_coverage": 1.0,
  "delta_vs_prev": {"false_red_rate": -0.02, "failures": -4, "needs_review": 0},
  "caps_applied": {"classified_failures_cap": 200, "duration_runs_cap": 50, "dropped": 0}
}
```

- **`false_red_rate` (FR-002, pinned)**: `(perf_timing_flake + infra_flake) / (perf_timing_flake + infra_flake + real)`. `needs_review` is **excluded** from this denominator and reported separately.
- **Conclusion taxonomy (FR-001)**: `completed_runs` counts only `{success, failure, timed_out, startup_failure}`; `{cancelled, action_required, skipped, neutral, stale}` are excluded from every metric.
- **`distinct_prs`**: keyed by PR number (fallback `headBranch` for push events); branch-reuse deduped by PR number.
- **`caps_applied.dropped`**: explicit overflow count (no silent truncation, FR-008).

## 3. `durations.json` — per-test aggregates (FR-003)

```json
{
  "schema": 1,
  "runs_sampled": 20,
  "suites_without_durations": ["fast-tests-foo"],
  "tests": [
    {"nodeid": "tests/perf/test_tasks_status_baseline.py::test_tasks_status_p95_within_nfr005_budget",
     "n": 6, "median_s": 30.35, "mean_s": 33.32, "max_s": 39.95, "long_pole": true}
  ]
}
```

- **`long_pole`**: `median_s > 2.0` (FR-003 threshold).
- **`suites_without_durations`**: suites mined but not emitting `--durations` (C-005 disclosure; those tests contribute zero samples).

## 4. `report.md` — human report

Rendered from the three JSONs: headline table, bucket breakdown + false-red rate, delta-vs-previous, duration long-poles, caps/coverage caveats, and the lineage label. Deterministic ordering (NFR-004).

## 5. Classifier signature contract (FR-002)

Ordered evaluation over a completed **failure** run; first decisive rule wins. Signatures prefer **test nodeids** over message substrings (drift-resistant).

```
extract: failed_nodeids  (grep `^FAILED (\S+)` from --log-failed)
         infra_signals   ({logged_out_on_connected_teamspace, digest-mismatch, INTERNALERROR, SystemError, startup_failure})
         gate_signals    (mypy/ruff/golden-count/arch/docs step failures)

is_timing(nodeid): nodeid ∈ TIMING_NODEIDS  OR  matches r"(_under_|within.*budget|_p95_|three_warm_runs|nfr_00\d|completes_in_under|check_nfr_003_latency)"

classify:
  if infra_signals and not failed_nodeids and not gate_signals   -> infra_flake
  if failed_nodeids:
      if any non-timing failed nodeid                            -> real            # mixed => real (actionable)
      else (all timing)                                          -> perf_timing_flake
  if gate_signals                                                -> real
  else                                                           -> needs_review    # honest fallback, never silent
```

- **`TIMING_NODEIDS`** seed set (pinned, versioned in the fixture): `test_tasks_status_p95_within_nfr005_budget`, `test_the_guard_completes_inside_the_budget_on_three_warm_runs`, `test_200_missions_under_5s`, `test_nfr_002_timing_200_missions`, `test_sweep_enumeration_perf_1k_files`, `test_run_consistency_check_completes_within_budget`, `check_nfr_003_latency`.
- **Coverage** = `1 - needs_review/failures`; a rising `needs_review` count signals classifier decay (FR-015 headline).

## 6. Golden fixture (FR-017) — `fixtures/`

```
fixtures/
├── runs.json            # frozen `gh run list` JSON for the reference window
├── logs/<run_id>.log    # frozen `--log-failed` / durations excerpts (trimmed)
└── expected.json        # expected buckets, false_red_rate, per-test medians (± tolerance in NFR-003)
```

`test_flake_report_fidelity.py` feeds `runs.json`+`logs/` through the pure core and asserts against `expected.json` within ±2pp (rate) / ±10% (median). Reproducible after live logs age out (C-006).
