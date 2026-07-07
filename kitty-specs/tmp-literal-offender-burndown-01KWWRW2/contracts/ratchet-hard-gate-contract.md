# Contract — /tmp ratchet hard gate (tmp-literal-offender-burndown-01KWWRW2, closes #1842)

## The gate after this mission (`tests/architectural/test_no_tmp_paths_in_tests.py`)

**Invariant**: NO literal `/tmp/` in any `tests/**/*.py` — the gate file included.
- `tmp_ratchet_baseline.txt`: **empty** (comment-only header). `_load_baseline()` returns `frozenset()` (skips `#`/blank lines).
- `_collect_violations(baseline, *, tests_root=_TESTS_ROOT, repo_root=_REPO_ROOT)`: walks `tests_root`, returns `[(rel, [lines])]` for any non-baselined `.py` containing the `/tmp/` needle; `__file__` self-excluded (secondary — the file is genuinely literal-free).
- Needle is fragment-built (`"/" + "tmp" + "/"`); the `/var/tmp/` evasion literal is split `"/var/" + "tmp/"` because it *contains* `/tmp/`.

## Tests (the contract's proofs)
- `test_baseline_is_empty` — `_load_baseline() == frozenset()` (reds if the baseline is re-populated).
- `test_collect_violations_flags_synthetic_offender_with_empty_baseline` — the real empty-baseline path flags exactly a seeded offender + `[]` when removed (NOT via `scan_file_for_tmp_literal`).
- `test_gate_file_itself_is_literal_free` — scans the gate file directly (independent of the `__file__` exclude).
- `test_no_evasion_vector_literals_in_tests` — reds on quote-anchored `/dev/shm/`, `/scratch/`, `/var/tmp/` roots; no false-positive on `.worktrees/scratch/`.

## Removed
- `_BASELINE_FLOOR = 50` and `test_baseline_is_non_empty_anti_vacuous` (the `>50` floor — would fail on an empty baseline).

## Conversion contract (WP01-07)
Every previously-baselined offender is off literal `/tmp`: category-A write-leaks → `tmp_path`/fixtures (none found — all 97 were category-B); category-B path-literals → non-`/tmp` POSIX sentinels (`/nonexistent/...`) with assertion values updated in lockstep, POSIX-absolute preserved for path-validation tests. Genuinely-bare `/tmp` (no trailing slash, testing the redaction allowlist) is left intact (`test_audit_classifiers.py`) and does not trip the trailing-slash needle.
