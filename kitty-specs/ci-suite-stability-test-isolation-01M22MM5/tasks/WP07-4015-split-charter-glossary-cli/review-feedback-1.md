# WP07 Review Feedback — cycle 1 (reviewer-renata, independent)

**Verdict: REJECT** — one low-severity but genuine defect introduced by the split.
Everything else is clean; the fix is a single line.

## What passed (no action needed)

- **All 10 MIXED splits correct.** For every split in the owned subsystems
  (charter/doctrine/glossary/cli) the functional assertion stays on the unmarked
  per-PR test and the timing assertion moved to a `@pytest.mark.performance` test
  using `assert_timing_budget(...)` with the budget value preserved exactly:
  - `test_code_reader.py::test_performance_1000_files` → budget 5.0 (+ functional
    `signals.primary_language == "python"`)
  - `test_performance_envelopes.py::test_compute_freshness_under_2_seconds` → 2.0
  - `test_performance_envelopes.py::test_bounded_resynthesize_under_15_seconds` → 15.0
  - `test_charter_context_spdd_reasons.py::test_performance_under_2s_active` → 2.0
  - `test_chokepoint_overhead.py::test_warm_overhead_p95_under_10ms` → 10
  - `test_resolved_mission_type_context.py::test_action_sequence_hot_path_does_not_resolve_template_mapping` → 100
  - `test_reconcile.py::test_single_mission_reconciles_under_two_seconds` → 2.0
  - `test_doctrine_health_glossary_pack.py::…test_doctor_doctrine_json_completes_under_two_seconds` → 2.0
  - `test_shipped_profiles.py::…test_shipped_profile_load_time` → 2.0
  - `test_entity_pages.py::test_generate_all_500_terms_under_10_seconds` → 10.0
  No functional assert was dropped, weakened, or relocated onto `@performance` (C-003 holds).
- **4 vocab-blocked deletions correct and complete.** `test_unresolved_selector_repeated_calls_fast`,
  `test_warm_resolver_p95_under_5ms`, `test_scaling_is_roughly_linear_in_artifact_count`,
  `test_collect_notices_completes_within_50ms` are gone (grep: zero hits). Each host file
  still collects with its other tests intact (no collateral deletion); unused
  `import time`/`import statistics` cleaned up.
- **Guards green, vocab unchanged.** `test_performance_marker_guard.py` +
  `test_timing_coverage_invariant.py` = 79 passed. `test_performance_marker_guard.py`
  has an empty diff vs the mission base — `TIMING_ASSERTION_VOCABULARY` untouched (C-004 holds).
- **Both lanes execute.** Per-PR (`-m "not performance"`): 470 passed / 14 deselected.
  Nightly (`-m performance`, all 10 relocated tests enumerated in the selection): 22 passed.
- **ruff check + ruff format --check** clean on all 11 files. Scope contained to the four
  owned test dirs.

## Required fix (blocking)

**File:** `tests/charter/evidence/test_code_reader.py` (~line 160)

The `@pytest.mark.timeout(10)` decorator was left on the extracted helper
`_seed_1000_file_tree`, not on a test:

```python
@pytest.mark.timeout(10)
def _seed_1000_file_tree(tmp_path) -> None:
    ...
```

pytest ignores marks on non-test functions, so this decorator is **inert**. As a
result **both** split siblings lost the 10 s safety cap the original
`test_performance_1000_files` carried. That matters here beyond hygiene: the
functional companion `test_collect_detects_primary_language_on_a_1000_file_tree`
runs on the **per-PR** path and creates 1000 files + collects with no timeout — the
exact under-shared-runner-load hang this mission exists to prevent. A silently-ignored
timing marker also directly contradicts this mission's own per-PR/performance
marker-hygiene bar.

**Fix (one line):** move the decorator off the helper and onto the timing test:

```python
def _seed_1000_file_tree(tmp_path) -> None:
    ...


@pytest.mark.timeout(10)  # or @pytest.mark.timeout(2) matching the sibling budgets
def test_collect_detects_primary_language_on_a_1000_file_tree(tmp_path):
    ...


@pytest.mark.performance
@pytest.mark.timeout(10)
def test_performance_1000_files(tmp_path):
    ...
```

At minimum put `@pytest.mark.timeout(10)` back on `test_performance_1000_files`
(and, preferably, guard the per-PR functional companion too). Do **not** leave the
mark dangling on the helper. Re-run the marker guard + the per-PR/`-m performance`
selections after the change.

## Verification commands used
- `pytest tests/architectural/test_performance_marker_guard.py tests/architectural/test_timing_coverage_invariant.py` → 79 passed
- `pytest <11 owned files> -m "not performance"` → 470 passed, 14 deselected
- `pytest tests/{charter,cli,glossary,doctrine} -m performance` (SPEC_KITTY_RUN_PERFORMANCE=1) → 22 passed
- `git diff base -- tests/architectural/test_performance_marker_guard.py` → empty (C-004)
- `ruff check` / `ruff format --check` → clean
