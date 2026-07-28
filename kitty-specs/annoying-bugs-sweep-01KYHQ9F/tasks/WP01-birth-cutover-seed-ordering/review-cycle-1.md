# WP01 Review Cycle 1

## Verdict

Changes requested. The ordinary focused suites pass, but the independent
claim-slot witness required by IC-02 and C-002 remains coupled to the seed
builder and can pass vacuously.

## Blocking Finding

**[HIGH] `src/specify_cli/migration/backfill_runtime_state.py:1361` - Claim-slot
verification derives its denominator from `_build_seed_events` - make the
witness enumerate non-null claim slots directly from `read_legacy_runtime`
output and independently require each deterministic raw claim row.**

`_verify_claim_slot_witnesses()` computes `expected_claim_wps` from
`expected_transitions`. Those transitions come from `_build_seed_events`, the
same builder whose suppression or omission the witness exists to detect. If
that builder emits annotations but suppresses claim transitions, annotation
state satisfies `_has_snapshot_runtime`, `expected_claim_wps` is empty, and
`verify_backfill()` reports a false green even when every raw claim seed is
absent.

Mutation proof used during review:

1. Build and backfill the existing migration fixture.
2. Remove the deterministic raw `claim` row while retaining annotation seeds.
3. Replace `_build_seed_events` with a mutation that returns no transition
   seeds but retains its annotations.
4. Call `verify_backfill()`.

Observed result:

```text
VerifyResult(ok=True, wp_count=1, mismatches=())
```

The review assertion that this result must be non-OK failed. This is the exact
builder/verifier tautology prohibited by plan IC-02 and contradicts the data
model rule that every non-null legacy claim slot requires a matching raw seed
witness.

### Required Remediation

- Derive the claim-witness WP/slot denominator directly from
  `read_legacy_runtime` results plus the independently resolved eligibility
  contract, not from `_build_seed_events` output.
- For every eligible non-null `shell_pid`, `shell_pid_created_at`, and `agent`,
  look up the deterministic raw claim row independently and report a mismatch
  when it is absent or differs.
- Add a focused anti-disable/mutation test that suppresses claim construction
  while annotation seeds remain. It must prove `verify_backfill()` fails, not
  merely that a later snapshot assertion fails.
- Retain the current later-legitimate-writer snapshot semantics and rerun the
  existing focused gates.

## Validation Evidence

- `tests/unit/migration/test_backfill_runtime_state.py`: 42 passed.
- `tests/integration/test_migration_backfill.py`: 9 passed.
- Exact #2985 regression node: 1 passed.
- Real merge caller, coordination and flat topologies: 2 passed.
- Regression marker collection includes the exact #2985 node: 41 selected.
- Ruff: passed.
- Mypy on the migration owner: passed.
- Tracker #2985 is assigned to `stijn-dejongh`; the implementation-start
  comment names this mission.

## WP Anti-Pattern Checklist

1. Dead code: PASS.
2. Synthetic-fixture test: FAIL, because the verification proof shares the
   builder denominator and does not survive the required anti-disable mutation.
3. Silent empty return: PASS.
4. Requirement coverage: FAIL for the independent-witness portion of C-002,
   FR-003, and FR-005.
5. Frozen surface: PASS.
6. Locked decision: PASS.
7. Shared-file ownership: PASS.
8. Production fragility: PASS; new raises are fail-closed ordering guards.
