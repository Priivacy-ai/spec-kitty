# WP05 Review Feedback — Cycle 1

## 1. Do not overstate public warn/block evidence

The US3.1 and US3.2 rows currently present the human and structured acceptance surfaces as proven, but their primary nodes are pure `aggregate_verdicts` unit tests: they do not render human output or invoke the public command. The cited US3.1 companion JSON node exercises `NO_NEW_FAILURES`, not the claimed default `NEW_FAILURES` warning path. This conflicts with the document's own limitation that the auto-derived public integration fixture resolves `NO_COVERAGE` (#3694/#3695).

Remedy: make each cell evidence-accurate. Use `N/A — reason` or an explicit blocked/unproven statement where no passing public node exists, and identify #3694/#3695 as the acceptance blocker. Do not imply that a successful public JSON envelope proves the new-regression warn path. If a passing public override node proves a specific block/force behavior, cite that exact node and limit the assertion to what it actually checks.

## 2. Expand every abbreviated pytest node ID

Seven companion references are only parameter suffixes such as `[registered_binding]`, `[True]`, and `[False-True-new_failures]`. They are not independently executable pytest node IDs, despite the preamble saying every node below was collected.

Remedy: repeat the complete module, test function, and parameter ID for every cited node. Re-run collection for the resulting list and retain only exact collecting IDs.

## 3. Finish the issue-matrix rows and expose current accept blockers

The structured issue matrix passes its business-rule validator and has correct verdict semantics, but all three titles still contain the scaffold text `<fill at WP-implementation time>`. Replace them with the live canonical GitHub titles while preserving: #2573 `in-mission` and not release-ready; #2762 `deferred-with-followup`; #3127 `deferred-with-followup` / `waiting_upstream`.

Also record in `release-readiness.md` that a read-only acceptance diagnosis currently remains blocked by the pending acceptance matrix, unchecked `tasks.md` projection, and #3694/#3695 disposition. Distinguish these final-accept blockers from the separate #3127 release prerequisite; WP05 may be evidence-complete while neither final acceptance nor release readiness is claimed.

## Evidence independently verified

- All 30 fully spelled-out node IDs currently collect (24 lane-c, 6 lane-d).
- Lane-c focused suite: 153 passed; Ruff and strict mypy passed.
- Lane-d process/parent suite: 5 passed, 1 native-Windows skip.
- The documented integration subset reproduces 3 `NO_COVERAGE` failures and 2 passes; #3694/#3695 are open and document base reproduction.
- Issue-matrix and canonical status validators pass.
- Live tracker: #3127 is open; #2573 is open and assigned to `stijn-dejongh`; #2762 is open.
- The cited historical Windows run exists and passed at `d060cff9...`; it predates the mission node and is correctly not claimed as mission evidence.
- No canonical `traces/approach.md` or pre-merge `retrospective.yaml` exists; the handoff correctly treats synthetic fixtures as non-operational and requires the post-merge diagnostic-feedback audit.
