# Quickstart: Verifying the Gate-Artifact Merge Driver Unit Gate (#3232)

No data model or API contracts apply (test-only mission over existing pure functions).

## 1. Run the restored gate (SC-001, SC-003)

```bash
PWHEADLESS=1 python -m pytest tests/merge/test_gate_artifact_merge_drivers_2804.py -p no:cacheprovider -q
```

All ~6 unit tests green, `pytest.mark.unit` only, in-memory (no git repo / subprocess), completes in
< 5 s (NFR-003).

## 2. Prove non-vacuity (SC-002)

Each invariant must red when the invariant is removed. Spot-check by temporary mutation (revert after):

- **Take-theirs mutation**: force `_merge_field` / the reconciler to prefer `theirs` — A1/A2 must red
  (filled criterion reset to scaffold; handle dropped).
- **All-scaffold fixture**: point a survival assertion at an all-scaffold input — its negative control
  must already cover this (handle absent, verdict `pending`/`unknown`).
- **A4 domain control**: an invalid `pass_fail` recomputes to `fail` → the admissible-domain assertion
  bites (proves it is not vacuously true).

## 3. Confirm `pending` stays admissible (SC-004, C-002)

A merged document that admits a scaffold row alongside a filled row yields `overall_verdict == pending`
and the gate PASSES (does not demand `pass`). This confirms #3231 was not silently "fixed".

## 4. Scope guard

- `tests/merge/test_issue_2804_merge_resets_gate_artifacts.py` (the integration marker) is unchanged.
- No `src/` change; no arch-guard/baseline update.
