# Contracts

## A. #4017 concurrent-defer operator signal (OPERATOR_SIGNAL_CONTRACT)
When a cold-start loser converges to a no-op after re-assess-under-lock:
- **Machine**: exit 0; no `"Global asset input changed"`, no `"global_asset_write_failed"`.
- **Human**: a sentence on an existing operator-visible sink (CLI/log) stating the runtime assets were already materialized by a concurrent peer and nothing was applied.
- **Test obligation (SC-002)**: the deterministic apply-interleave test asserts on the emitted SIGNAL (the human line / log record), not merely the exit code; it is RED-first (reproduces `"Global asset input changed"`) before the fix.

## B. #4015 per-split coverage-mapping (FR-013 / NFR-003 / SC-009)
A committed mapping artifact (table in the WP/review notes or a small file) with one row per split:
`original_test → functional_assertion (retained verbatim, per-PR, unmarked) | timing_assertion (relocated test id, @performance, budget value preserved)`.
Invariant: the set/text of functional assertions on the per-PR path after the sweep ⊇ before. Reviewer diffs this, not faith.
