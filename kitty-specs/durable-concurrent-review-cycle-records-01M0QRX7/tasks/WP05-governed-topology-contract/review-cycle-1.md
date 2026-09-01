---
affected_files: []
cycle_number: 1
mission_slug: durable-concurrent-review-cycle-records-01M0QRX7
reproduction_command:
reviewed_at: '2026-08-24T08:16:02Z'
reviewer_agent: user
wp_id: WP05
---

# WP05 review feedback — cycle 1

## Verdict: changes requested

The new topology module reaches the production Typer command, constructs all four canonical topology values with real repositories/worktrees, queries production placement, and passes its focused suite. It does not yet satisfy the WP's independent-oracle requirements, and the integrated issue-pinned production test is red against the dependency state reviewed here.

## Issue 1 — automatic-mode event assertions bypass the production reader

`_events_from_governed_ref()` obtains `status.events.jsonl` with `git show` and then manually decodes each line with `json.loads`. Automatic-mode correlation therefore never exercises `specify_cli.status.store.read_events`, even though T023 explicitly requires authoritative event history to be read using production readers. This can false-green if production decoding, validation, legacy-field handling, or model construction rejects bytes that the test's permissive JSON parser accepts.

Fix the owned test module so every matrix cell's authoritative event assertion passes the governed event bytes through the production reader/model path. If a governed ref is not checked out, materialize the exact `git show` bytes into an isolated temporary mission directory with the required metadata and call `read_events` there, or use an existing production API that reads a governed ref. Do not introduce another event parser in the test.

## Issue 2 — the durable oracle does not prove exact bytes or the exact verdict tuple

`_assert_git_blob()` accepts `expected in shown.stdout`; it never compares the committed blob byte-for-byte with the generated evidence file. `_assert_event_correlation()` accepts either `changes_requested` or `approved` regardless of the requested transition. In local-only mode it also omits explicit mission and WP assertions. These checks do not meet the prompt's requirement that every row correlate the exact event ID, evidence pointer, mission, WP, reviewer, verdict, and committed bytes.

Strengthen the owned test module so:

- the full committed blob equals the exact local evidence bytes captured for that command;
- the expected verdict is passed into the helper (`changes_requested` for planned, `approved` for approved/done) and asserted exactly;
- mission slug/ID, WP ID, reviewer, event ID, and evidence pointer are asserted in both automatic and local-only paths;
- a causal negative control proves the row turns red for a wrong verdict and for altered/truncated committed bytes that still contain the current substring markers.

## Issue 3 — the issue-pinned integrated production-path gate is red

The required downstream run against the exact reviewed branch produced 18 failures and 121 passes:

```text
uv run python -m pytest \
  tests/integration/test_review_durability_matrix.py \
  tests/review/test_cycle.py \
  tests/review/test_verdict_commit_queue.py \
  tests/specify_cli/cli/commands/agent/test_move_task_durability.py \
  tests/integration/review/test_verdict_save_topologies.py \
  -n0 -q --tb=short
```

The release-blocking failures include:

- `test_sc004_two_concurrent_processes_never_clobber_a_verdict_over_50_iterations`: round 0 returns `authoritative_event_mismatch` because the authoritative event has no correlated review result;
- `test_sc004_evidence_commit_mutant_reports_missing_committed_evidence`: returns `unproven_refusal` instead of the required `missing_committed_evidence` cause;
- multiple real-router/topology cells return `persistence_failed`, including exact destination-readback failures;
- the interrupted identical-retry test violates its asserted recovery contract.

WP05 owns only `tests/integration/review/test_verdict_save_topologies.py`, so do not silently change the frozen issue-pinned module or production files from this WP. Coordinate with the orchestrator to reopen the responsible dependency WP(s), restore the issue-pinned production gate, then rerun this exact downstream command before resubmitting WP05. The mission's only declared baseline exception was missing gate-coverage JUnit evidence, not these failures.

## Reproduced checks

- Focused WP05: `15 passed in 42.75s`.
- Ruff: `All checks passed!`.
- Strict mypy: `Success: no issues found in 1 source file`.
- Integrated affected set: `18 failed, 121 passed in 106.87s`.

## WP-level anti-pattern checklist

1. Dead code: N/A — test-only file.
2. Synthetic-fixture test: **FAIL** — production command execution is real, but automatic event interpretation is replaced by a test-local JSON parser and the oracle is permissive enough to accept wrong verdict/partial bytes.
3. Silent empty return: N/A — no production change.
4. FR coverage: **FAIL** — FR-004/FR-007/FR-008 assertions do not prove the exact durable tuple, and the issue-pinned FR-008 production gate is red.
5. Frozen surface: PASS — commit `2892c7de499e52cb5e55f6c9184fd1982f7beeee` adds only the owned file.
6. Locked decision: PASS — no new placement authority or manual authoritative event append was introduced.
7. Shared-file ownership: PASS — only the WP-owned test module changed.
8. Production fragility: N/A — no production change.

