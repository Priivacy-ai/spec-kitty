# WP14 review cycle 1 — changes requested

## Blocking issue 1 — causal proof is asserted, not reproducible

FR-003, FR-007, NFR-002, and NFR-007 require a plausible authority-violating fault to reach the live Act and make the intended oracle fail, with a compliant control. The ledger/raw result currently record only prose plus `act_reached: true` / `intended_oracle_failed: true`. Every retained-row `command` is the ordinary green survivor run; deletion rows use the same generic delete/collect/run instruction. There is no fault command, control command, exit/result, failed assertion, or artifact reference that lets a reviewer distinguish an executed red/control probe from a declaration.

This is material for the retained architectural guards. For example, `test_events_tracker_public_imports.py`, `test_no_production_worktree_guard_bypass.py`, and `test_status_sync_boundary.py` prove the scanner with newly created literal fixtures. The mission specification explicitly says a planted searched literal or scanner self-test alone is not causal proof. The live-corpus green assertion is present, but the evidence does not show a controlled production-corpus fault biting.

Fix without expanding deletion scope: run and record a bounded fault/control matrix for each valid survivor family (families may share one probe only when production path, oracle, authority, and fault are actually identical). Record exact command/mechanism, live production corpus, fault change, Act-reached evidence, non-collection failed assertion/outcome, compliant-control outcome, and artifact/output reference. For deletion rows, replace the generic harmless-change claim with the class-specific authority/consumer/unique-boundary search actually performed. If a probe survives, restore or strengthen only the uniquely needed guard.

## Blocking issue 2 — execution environment contradicts itself

`raw/wp14-results.json` records `environment.python: "3.14.5"`, while every ledger row claims `CPython 3.11.15` and the declared `.venv/bin/pytest` actually runs under Python 3.11.15 (`.venv/bin/python --version`). Correct the raw environment to the interpreter that executed the 390-node gate, and ensure hashes/environment IDs refer to that same run.

## Verified passing evidence

- Scope: 46/46 terminal paths; 21 whole-file deletions, 22 reduced files, 3 unchanged survivors.
- Arithmetic: 698 base nodes -> 390 head nodes, net -308.
- Focused gate independently rerun: 390 passed, 0 failed/skipped/xfail in 88.62s.
- Ruff: 22 modified surviving paths, 0 errors.
- Mypy: 41 existing errors in 6 head files vs recorded 60/13 base; deletion-only diff introduces no new signature.
- Ownership: no production, central routing-map, dependency, lockfile, or non-owned WP path changes; WP07 handoff lists all 21 deleted and 25 surviving paths.
- Tracker #1931 remains OPEN, assigned to `robertDouglass`, with the mission comment present.

## Anti-pattern checklist

1. Dead code: N/A — no production API/module additions.
2. Synthetic-fixture test: **FAIL** as causal evidence for multiple retained structural guards; planted detector fixtures are currently the only recorded red mechanism.
3. Silent empty return: N/A — no production path additions.
4. FR coverage: **FAIL** — FR-003/FR-007/NFR-007 are cited but lack reproducible fault/control results.
5. Frozen surface: PASS — production and central routing surfaces unchanged.
6. Locked decision: PASS — no forbidden product/route edits or deletion quota behavior found.
7. Shared-file ownership: PASS — WP14 paths do not overlap another WP's `owned_files`.
8. Production fragility: N/A — no production `raise` additions.

Verdict: CHANGES REQUESTED. Preserve the 698->390 reduction unless executed probes identify a real causal gap.
