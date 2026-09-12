# Measured baseline for NFR-001 / SC-009

Produced by the post-spec adversarial squad's debugger lens, not asserted.

## Invocation

```
PWHEADLESS=1 uv run pytest \
  tests/review/ \
  tests/status/ \
  tests/regression/test_2646_stale_verdict_closes_via_fr001.py \
  tests/integration/test_review_cycle_rejection_only.py \
  tests/integration/test_ac5_hash_guard.py \
  tests/integration/test_wp_file_hash_stability.py \
  tests/post_merge/test_review_artifact_consistency.py \
  tests/specify_cli/cli/commands/agent/ \
  -q
```

## Result at branch HEAD

`2 failed, 2815 passed, 1 skipped, 2 xfailed in 118.77s` (2820 collected)

## The two failures, attributed

| Test node id | Cause | Reproduces at `8466727eb`? |
|---|---|---|
| `tests/status/test_work_package_lifecycle.py::test_real_implement_and_review_claims_persist_structured_latest_binding` | #3157. `at="2026-08-01T10:00:00+00:00"` (line 252) sorts before the `now()` event emitted by `start_implementation_status`, so the lane never reaches `for_review` and `start_review_status` correctly rejects. Went red when the date passed on 2026-08-01. Product code is correct. | **YES** |
| `tests/specify_cli/cli/commands/agent/test_mission_cli_golden_contract.py::test_command_exposes_exact_flag_surface[acceptance-verdict]` | #3160. Frozen flag contract missing six flags the command grew: `--description --execute --negative-invariant --no-execute --scope --verification-command`. | **YES** |

Merge-base confirmation run, **two-file scope** (the two failing files collect 39
tests): `2 failed, 37 passed in 55.17s` — identical node ids. This is a narrower
invocation than the 2820-test run above; it confirms the two failures reproduce at
the merge-base, not that the whole suite was re-run there.

**Re-verified at HEAD after the spec and plan commits**: identical counts, identical
node ids, no drift.

**Both retained failures are honestly pre-existing to `main`.** Neither C-005 pin
(`test_issue_2804_*`, `test_issue_3086_*`) is inside the affected-suites list, so
C-005 does not bear on this baseline.

## How to verify NFR-001

Re-run the invocation above. The failure node-id set must be a **subset** of the
two rows in this table. Any node id present here and absent from a later run has
either been fixed (state which FR) or removed from the denominator — the latter is
prohibited by NFR-001.

## Coverage caveat

`fast-tests-review` is the only CI shard running `tests/review/` with
`--cov=src/specify_cli/review`, and it is gated on `fast-tests-status`, which is
red from #3157. Until FR-014 lands, this mission's primary write surface produces
no coverage XML in CI and NFR-004 cannot be measured there. Local measurement is
the only option in the interim.
