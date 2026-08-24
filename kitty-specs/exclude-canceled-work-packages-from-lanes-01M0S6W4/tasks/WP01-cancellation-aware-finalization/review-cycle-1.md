---
affected_files: []
cycle_number: 1
mission_slug: exclude-canceled-work-packages-from-lanes-01M0S6W4
reproduction_command:
reviewed_at: '2026-08-24T08:43:36Z'
reviewer_agent: user
wp_id: WP01
---

# WP01 Review Feedback — Changes Required

## Issue 1 — Required compatibility and lifecycle acceptance evidence is incomplete

The focused tests pass, but several explicit WP acceptance gates are not exercised through the real finalizer path:

- FR-009 has only a pure-map test that labels `Lane.PLANNED` as “reopened”; it does not append a canceled event followed by a governed current non-canceled event and prove that finalization includes the work package.
- FR-010 has no before/after no-cancellation structural-parity assertion covering execution-lane membership, dependency edges, ownership findings, planning-artifact classification, collapse reporting, and cycle findings.
- The repeated-finalize edge case is missing: no test starts with a persisted nonempty `lanes.json`, cancels the sole prior execution-lane member, re-finalizes, and proves the new manifest has zero lanes and no dangling execution-lane dependency while preserving prompts, `tasks.md`, and lifecycle events.
- Canceled validation bypasses are not paired with eligible controls for empty ownership, invalid authoritative surface, unmatched literal paths, ownership overlap, planning-artifact mode, and collapse influence. Without the control, a passing canceled case does not prove the validator remains active for eligible work.
- Fresh first-finalize/no-event and unavailable coordination-surface behavior are not explicitly exercised at the command boundary.

Add focused command-level tests for these cases. Assertions must inspect the actual `LanesManifest`, diagnostics, and retained artifacts rather than only the pure projection or literal fixtures.

## Issue 2 — The governed 100-WP fixture does not meet its specified shape

`test_finalize_canceled_work_packages_performance.py` writes `dependencies: []` for all 100 work packages. The WP requires a deterministic 100-WP fixture with representative direct edges and canceled nodes, so the benchmark currently measures mostly prompt/status parsing and independent-node handling rather than cancellation-aware dependency projection and lane graph computation.

Add a deterministic, acyclic dependency distribution among eligible nodes plus representative canceled-source edges that do not create stale eligible-to-canceled dependencies. Keep 100 work packages, 10 measured rounds, two warm-ups, and the two-second threshold. Assert the fixture actually contains the intended edge classes before benchmarking.

## Issue 3 — The documented strict-type gate is not reproducible as written

The exact required command fails before analysis:

```text
uv run --extra test mypy --strict ...
error: Failed to spawn: `mypy`
```

`mypy` belongs to the repository's `lint` optional dependency, not `test`. The source does pass with:

```text
uv run --extra lint mypy --strict \
  src/specify_cli/cli/commands/agent/finalization_eligibility.py \
  src/specify_cli/cli/commands/agent/mission_finalize.py
```

Coordinate a planning-artifact correction to `quickstart.md`/the WP evidence so the exact governed command uses `--extra lint`, then rerun and record it. Do not add `mypy` to the test extra solely to mask the command error.

## Passing evidence to preserve

- Commit ordering: acceptance-only RED commit `00134fbdb`; behavior-preserving campsite commit `0f3ea2bce`; functional commit `42a195e01`.
- RED reproduced at `00134fbdb`: 3 expected behavior failures.
- Focused behavior: 69 passed, 1 skipped.
- Existing lane/cycle regressions: 37 passed.
- Architecture/terminology: 42 passed.
- Ruff: clean.
- Changed-line coverage: 92% (threshold 90%).
- Windows-critical collection: one cancellation-policy test collected.
- Governed benchmark: 10 rounds; local maximum/p95 0.767s.
- Strict mypy with the correct `lint` extra: no issues in two source files.

