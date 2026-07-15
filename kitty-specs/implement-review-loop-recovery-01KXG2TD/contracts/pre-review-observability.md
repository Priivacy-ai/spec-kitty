# Contract: `move-task --to for_review` Pre-Review Observability

## Scope

This contract applies only to:

```text
spec-kitty agent tasks move-task WP## --to for_review
```

when the default real pre-review gate is not skipped.

## Human-output mode

- Emit an initial indication within 2 seconds of entering a non-empty gate run.
- While the gate remains active, emit liveness with no gap greater than 30 seconds.
- Do not delay a fast gate merely to emit a heartbeat.
- Label progress as liveness, never as a passing verdict.

## JSON-output mode

- Standard output contains exactly one parseable JSON document for success, gate failure, timeout, or catchable cancellation.
- No progress prose appears before or after that document on standard output.
- Existing result fields remain compatible; new gate metadata, if any, is additive.

## Interruption

- Timeout or catchable cancellation during the gate phase occurs before transition mutation.
- Applicable pre-review recovery writes, including lane-deliverable auto-commit, occur only after the gate permits progress.
- The prior WP lane remains authoritative.
- No event append, materialized status change, WP tracking mutation, placement commit, or new Spec Kitty-owned checkout dirtiness may result from that attempted transition.
- Test-owned writes are outside the zero-residue claim. They must be preserved and surfaced; interruption handling must never reset or restore them.
- Timeout and catchable cancellation are typed outcomes, reported with nonzero exit status, `transition_applied: false`, and no conversion into passing, verified-clean, or generic `no_coverage` outcomes.
- The canonical runner terminates and reaps its child before returning a timeout or catchable-cancellation outcome.
- SIGKILL receives no in-process rollback promise. Recovery establishes truth from the existing event authority.

## Compatibility

- `--skip-pre-review-gate` behavior is unchanged.
- `SPEC_KITTY_SYNC_DISABLE` and `SPEC_KITTY_SYNC_MINIMAL_IMPORT` behavior is unchanged.
- Explicit synchronization disable/minimal-import remains a truthful pre-I/O skip and cannot be represented as passing or verified clean.
- Scope derivation, test execution, baseline comparison, and verdict policy remain owned by `pre_review_gate.py`.
