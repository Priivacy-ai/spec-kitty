# Decision Moment `01KZ6X4Y7A3XPK5AJ96AA49XJ9`

- **Mission:** `review-cycle-verdict-seam-rebuild-01KZ2W7W`
- **Origin flow:** `plan`
- **Slot key:** `wp12_arbiter_test_ownership`
- **Input key:** `wp12_arbiter_test_ownership`
- **Status:** `resolved`
- **Created:** `2026-08-04T17:29:10.634241+00:00`
- **Resolved:** `2026-08-04T17:29:13.942943+00:00`
- **Resolved by:** `Stijn Dejongh (operator)`
- **Opened by:** `claude-opus-5`
- **Other answer:** `false`

## Question

WP12 deleted _find_review_cycle_artifact, _persist_in_artifact and _persist_standalone_json per T051-T053. tests/review/test_arbiter.py (44 tests) imports them directly and is owned by NO WP in this mission. Its collection ImportError cascades: _gate_coverage.py::collect_universe runs its own pytest --collect-only over the entire tests/ tree, so --ignore cannot suppress it and 8 further tests/architectural/ files fail -- 26 errors plus 1 failure, one root cause. While red, every subsequent WP's architectural verification is poisoned. How should this be routed?

## Options

- widen-WP12-owned_files-to-include-tests/review/test_arbiter.py
- assign-to-WP13-or-WP14
- author-a-new-WP

## Final answer

widen-WP12-owned_files-to-include-tests/review/test_arbiter.py

## Rationale

OPERATOR-CONFIRMED ('do it'). WP12 deleted the functions, so this test file is its direct fallout and belongs with the change that caused it. Deferring to WP13/WP14 would leave the architectural suite red across at least two more WPs -- and because the gate-coverage collector sweeps the whole tests/ tree, a red collection there poisons the verification of every WP that follows, so deferral has a compounding cost and no benefit. A new WP is disproportionate for rewriting one test file against a retired surface. Legality: no WP owned the file, so no overlap is created; finalize-tasks --validate-only passes at 18 WPs / 0 modified both as a reverted trial and after the edit. Scope is strictly rewriting/removing the tests that exercised the three deleted functions and keeping the rest of the file green -- NOT a licence to restructure the arbiter test suite. Note WP13 and WP14 both own review/arbiter.py and both follow WP12 in dependency order, so a further amendment granting them the same test file stays legal if they need it. FOURTH instance of this deadlock class (WP04/T017 -> WP18; WP18's own missing test home; WP11's tasks_move_task.py; now this). The pattern is consistent and worth recording for WP17: planning-time ownership assignment covered production modules but systematically omitted (a) the test files that pin the surfaces being retired, (b) cross-module compensators, and (c) generated or pinned-gate surfaces. Every instance was caught only at implementation time.

## Change log

- `2026-08-04T17:29:10.634241+00:00` — opened
- `2026-08-04T17:29:13.942943+00:00` — resolved (final_answer="widen-WP12-owned_files-to-include-tests/review/test_arbiter.py")
