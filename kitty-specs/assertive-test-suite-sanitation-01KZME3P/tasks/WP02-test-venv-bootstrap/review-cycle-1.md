---
affected_files: []
cycle_number: 1
mission_slug: assertive-test-suite-sanitation-01KZME3P
reproduction_command:
reviewed_at: '2026-08-10T10:46:43Z'
reviewer_agent: user
wp_id: WP02
---

# WP02 Review Cycle 1 — Changes Requested

Reviewer: `reviewer-renata`
Verdict: REJECT

## Blocking findings

### 1. Invalid final cache entries are not recoverable

`tests/conftest.py:795-796` and `tests/conftest.py:836-845` use `shutil.rmtree(..., ignore_errors=True)` for every invalid final path. If the final cache path is a regular file (or symlink), `rmtree` leaves it in place and publication fails.

Independent reproduction created `.pytest_cache/spec-kitty-test-venv` as a regular file, then called `_ensure_test_venv` with the real lease flow and narrow build/validate seams. Result:

```text
NotADirectoryError: [Errno 20] Not a directory: '...spec-kitty-test-venv.build-*' -> '...spec-kitty-test-venv'
```

This violates T008's “invalid published venv … rebuild once” requirement. Add one path-safe removal helper that unlinks files/symlinks and removes directories, use it under the state lock at both sites, and add regular-file plus symlink final-path tests. Never follow/delete an arbitrary symlink target.

### 2. A schema-valid corrupted scanner cache silently disables enforcement

`tests/_support/wall_clock_assertions.py:150-180` validates the input digest and row types, but does not integrity-bind the cached result rows. Independent reproduction scanned a source containing `assert datetime.now()...`, changed only the valid JSON payload's `violations` list to `[]`, and read the same cache again:

```text
first_count 1
second_count_after_valid_json_corruption 0
bypass True
```

This violates T050's fail-closed corruption requirement: a forbidden wall-clock assertion passes without rescanning. Integrity-bind the canonical result payload (for example, a checked SHA-256 over version + input digest + canonical rows); any mismatch must be a cache miss and rescan. Extend the corruption test beyond malformed JSON to a schema-valid omitted/substituted row, and add a real cross-process publication/read test.

### 3. The #3283 causal evidence fails for the wrong reason and the claimed raw artifact is not raw

`WP02.yaml:50-59` describes a live-owner/publication fault, but its command selects only `-k malformed`. `wp02-results.json:32-39` records the base failure as:

```text
AttributeError: module 'tests.conftest' has no attribute '_VENV_STATE_PATH'
```

That does not exercise a slow builder, heartbeat, waiter, lease stealing, partial publication, or #3283's timeout cascade. The cited `bootstrap-failure.txt` is absent from this lane and, on the WP01 dependency lane, is a 403-byte record explicitly labeled “compact planning-time summary”; it is not the raw pre-fix failure required by FR-013/T011/T012.

Replace the synthetic missing-symbol red with a behavior-level pre-fix replay or a controlled fault that restores the old lock/disabled heartbeat and reaches the concurrent Act/oracle. Persist its full raw command/output separately, hash it, and make the ledger's command, fault, oracle, result, and artifact hash all refer to that same run.

### 4. Three clean starts do not exercise the documented parallel suite

`wp02-results.json:67-73` records the integration concurrency test once, then repeats only `test_two_spawned_processes_publish_one_shared_venv` three times. NFR-008 and T012 require three clean-cache starts of the documented parallel suite, proving test bodies begin without sibling lock cascades. A focused helper race is useful but is not that suite.

Run the actual documented parallel command three times from equivalent clean shared-cache state. Record exact commands, cache reset policy, worker topology, body-start proof, outcomes, median, and maximum. Keep Linux/Windows job URLs deferred to WP08 as already planned.

## Verified positives

- Both replay patches apply unchanged to immutable base `28ae75ea998c898aba57364db7a06d2088bd2af2`; all five replayed files are byte-identical to HEAD.
- Patch hashes match the results artifact.
- Focused gates: bootstrap `10 passed, 2 skipped`; scanner `112 passed`; diff-scoped Ruff clean.
- Spawned-process one-builder publication, slow-live waiter, killed-builder recovery, PID reuse, malformed state, unsafe temp-path refusal, POSIX layout, and Windows routing are real production-path tests.
- Focused strict mypy surfaced only pre-existing errors outside WP02-changed lines.

## WP anti-pattern checklist

1. Dead code: **PASS** — new private helpers have live `tests/conftest.py` callers.
2. Synthetic-fixture test: **FAIL** — the recorded bootstrap causal probe fails on a missing symbol, not the claimed concurrency behavior.
3. Silent empty return: **PASS** — scanner cache `None` results are documented misses that rescan.
4. FR coverage: **FAIL** — FR-013/NFR-008 evidence is incomplete/non-causal.
5. Frozen surface: **PASS** — changes remain within WP02 ownership.
6. Locked decision: **FAIL** — schema-valid cache corruption bypasses the required fail-closed wall-clock oracle.
7. Shared-file ownership: **PASS** — no uncoordinated file overlap found.
8. Production fragility: **FAIL** — an invalid final cache file raises during publication instead of recovering.
