# Contract: Mission-number assignment idempotency

**WP**: WP04 | **FRs**: FR-010, FR-011, FR-012 | **Source bug**: #983

## Pre-condition

`spec-kitty merge` is mid-flow with merge-state file `.kittify/merge-state.json` present and consistent.

## Idempotency rule

The mission-number-assignment step has two read+decide branches:

1. **Read `meta.json.mission_number`** in the mission feature directory.
2. **Compute expected mission number** via the canonical strategy (`max(existing) + 1` inside the merge-state lock).

If `meta.json.mission_number == expected`, the step is a **no-op**: no rewrite of `meta.json`, no commit, no state mutation. Else, the assignment proceeds as today.

After successful execution (whether by no-op or assignment), `MergeState.mission_number_baked = True` is set and persisted.

## Resume semantics

On `spec-kitty merge --resume`:

- Read `MergeState` from disk via `load_state()`.
- If `mission_number_baked == True`, skip the assignment step entirely (no read of `meta.json`, no compute, no commit).
- Else, proceed to the idempotency check above.

## Concurrency

The mission-number-assignment step continues to run inside the existing merge-state lock (`max(existing) + 1` requires it). The idempotency check reads `meta.json` while holding the lock; release follows the existing flow.

## Atomicity (opportunistic)

`meta.json` write — if WP04 implementation also addresses the non-atomic write (current pattern: `Path.write_text(json.dumps(...))`) by switching to temp-file + rename, this is bonus scope and lands in the same WP. Required scope is only the idempotency check + flag.

## Acceptance fixtures

- Simulate partial merge: write `mission_number=115` to `meta.json`, write `MergeState` with `mission_number_baked=False`, fail the merge mid-step, rerun with `--resume`. Expected: no empty mission-number commit; merge completes; `mission_number_baked` becomes `True`.
- Fresh merge (no prior assignment): expected: assignment runs as today; flag set to `True` after success.
- `--resume` on a state where `mission_number_baked == True`: expected: step is skipped without `meta.json` read.

## Invariants

- The mission-number value itself, once written, is never overwritten — even if the computed value changes (e.g., concurrent merges). The lock guarantees serialization; idempotency guarantees no rewrite after success.
