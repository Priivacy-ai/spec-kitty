# WP01 Review Cycle 1 — Changes Requested

Reviewer: Reviewer Renata  
Reviewed commit: `1902ce530759b80e2bbaaa1b134fa8c73de8729e`  
Planning base: `kitty/mission-stale-workspace-reproduction-recovery-01KXGR6S`

## Verdict

Changes requested. The independently repeated result is stable at 6 passing and
7 failing test cases, and those seven failures are valid RED evidence candidates;
they are not rejected merely for being RED. The witness is rejected because it
does not yet prove the required entry-point prerequisites and six-surface record
for every row.

## Blocking issue 1 — `move-task` does not prove the intended ordinary pre-review seam

All three stale `move-task` failures show a successful JSON result whose
`pre_review_gate` says `outcome: no_coverage` and `reason: no changed files
detected for this WP — skipping the gate cheaply`. The divergent row can instead
report that gate authorities are unavailable because the imported gate module
belongs to the outer checkout. This is incompatible with the WP prerequisite
that a genuine implementation commit and changed owned file activate the normal,
non-skipped `move-task` path. It leaves the three `move-task` RED classifications
vulnerable to a fixture false-positive: the command may succeed because the
fixture skipped the workspace-requiring gate rather than because the production
seam mishandled stale authority.

Required remediation:

1. Immediately before every CLI invocation, assert the full command-specific
   fixture integrity: real registered worktree, expected current lane assignment,
   persisted relative workspace context, expected branch existence/absence,
   exact status lane, completed subtask, dependency state, lane commit ahead of
   the pinned base, and the expected owned-file diff.
2. Make the ordinary `move-task` fixture reach a real coverage-bearing
   pre-review path. Its JSON must not say `no_coverage`, and it must not import
   gate authorities from the outer repository. Keep the exact argv unchanged and
   do not use `--skip-pre-review-gate`.
3. Reclassify the three stale `move-task` rows only after that integrity guard
   proves the intended production owner was reached.

## Blocking issue 2 — eight matrix rows do not capture/assert all six surfaces

`_changed_path_sets()` is used only by `test_mark_status_is_workspace_free`.
The healthy `move-task` and both expected-success review rows merely check that
COORD moved and the checkouts are clean; they do not assert exact PRIMARY,
COORD, and lane OIDs and every new commit's path set, or the expected WP/tasks
bytes. The RED branches stop at their first failed exit/diagnostic/cleanliness
assertion, so their later atomicity checks are unreachable. For example, the
unavailable review row stops at the missing recovery text before checking the
known PRIMARY dirt and COORD compensation commits. `_assert_refusal_is_atomic()`
also omits `lane_path_exists` and does not compare before/after porcelain.

Required remediation:

1. Build one structured observation/result record per row containing the exact
   argv, exit/stdout/stderr or parsed JSON, event bytes and reduced state,
   WP/tasks bytes, all three OIDs and ordered commit path sets, lock state,
   path/worktree existence, and all relevant porcelain.
2. Assert or compare that complete record for every one of the 12 matrix rows,
   including RED rows. Do not let a first exit-code assertion prevent the other
   surfaces from being recorded and checked. A single structured expected-vs-
   actual comparison or independently named assertions/tests is acceptable.
3. For every successful row, prove exact canonical placement and unchanged
   unrelated refs/bytes. For every refusal row, prove zero OID movement, byte
   identity, no new path/lock, and unchanged clean porcelain.
4. Include the exact planning-base SHA and stable owner/disposition fields in the
   executable row record so the durable matrix can be derived without manual
   reinterpretation.

## Blocking issue 3 — diagnostic latency is not measured

The prompt and NFR-004 require unavailable/divergent refusal to complete within
two seconds in the local fixture. The module imports no monotonic clock and makes
no elapsed-time assertion. Add a deterministic monotonic measurement around the
registered CLI invocation for the non-recoverable rows and assert the specified
bound without sleeps or retries.

## Independent evidence

- Exact focused command, run 1: 6 passed / 7 failed in 54.99 seconds (55.72
  seconds process elapsed).
- Exact focused command, run 2: 6 passed / 7 failed in 53.71 seconds (54.39
  seconds process elapsed).
- Both runs produced the same row classification: four `mark-status` GREEN
  controls, healthy `move-task` GREEN, and seven RED rows across stale
  `move-task` plus all review classifications.
- `ruff check` on the owned module passed.
- Scope/ownership passed for commit `1902ce530`: it adds only
  `tests/specify_cli/cli/commands/agent/test_stale_workspace_transition_contract.py`
  and contains no production monkeypatch.
- A bounded collection-only run was aborted after 12 seconds in the pre-existing
  repository wall-clock scanner. The stack was in
  `tests/_support/wall_clock_assertions.py::_function_bound_names` during
  `pytest_collection_modifyitems`, not in this witness. This needs a separate
  upstream performance report; it is not the reason WP01 is rejected.

## Anti-pattern checklist

1. Dead code: N/A — no production code or public module was added.
2. Synthetic-fixture test: FAIL — the ordinary `move-task` fixture currently
   skips coverage (`no_coverage`) instead of proving the intended pre-review seam.
3. Silent empty return: N/A — no production code was added.
4. FR coverage: FAIL — FR-002 and NFR-004 lack complete executable assertions.
5. Frozen surface: PASS — the implementation commit modifies only the sole owned
   test path.
6. Locked decision: PASS — no production path or cross-command resolver was
   added.
7. Shared-file ownership: PASS — the implementation commit has no shared-file
   overlap.
8. Production fragility: N/A — no production `raise` was added.

