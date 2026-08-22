# POST-TASKS adversarial squad — findings folded into WP01 (2026-08-21)

Two profile-loaded read-only lenses (reviewer-renata anti-laziness, python-pedro implementer/Sonar)
reviewed the WP01 decomposition. Both confirmed single-WP is correct (atomic; owned_files no-overlap
forbids a clean split). Findings folded into `tasks/WP01-thread-base-lane-allocation.md`:

## HIGH (ship-blockers, folded)

- **F-PT1 (reviewer) — red-first entry must be the in-process `implement(--base)` CLI, not the manual
  `_resolve → create_lane_workspace` chain.** The manual chain either TypeErrors on `upstream/main`
  (false-red) or stays RED forever post-fix (base-less `create_lane_workspace`), tempting an implementer
  to RETAIN the smuggle and leave #3571 unfixed under a green test. → T001 step 3 now MANDATES the CLI
  entry and PROHIBITS the manual chain; T008 swap-back is coherent only via the CLI entry.
- **F-PT2 (implementer) — NFR-004 envelope was contradictory.** `_fail` hard-codes the top-level
  `error_code="LANE_ALLOCATION_FAILED"` and never reads `exc.error_code`/`to_dict()`, so `UNHONORABLE_BASE`
  would only be a message substring and `to_dict()` would be dead new code. → T003 step 5 now requires
  merging `exc.to_dict()` into the `_fail` **data** payload at the allocation catch site; T007 asserts
  `data["error_code"] == "UNHONORABLE_BASE"` (not the top-level code).

## MEDIUM (folded)

- **F-PT3 (implementer) — Sonar S3776 cognitive-nesting.** ruff C901 is safe (~9) but the 4 guards sit
  inside already-nested arms → projected 13–16 band. → T003 step 2 extracts `_guard_base_honorable(...)`
  + `_resolve_lane_parent(...)` helpers (also directly unit-testable for new-code coverage).
- **F-PT4 (reviewer) — AC-4 ABSENT vacuously fakeable.** The success line is emitted via
  `impl_mod.console.print` (rich Console), not stdout; `capsys` misses it → ABSENT always passes. → T006
  step 5 now patches `impl_mod.console.print` for both directions + a positive control.
- **F-PT5 (reviewer) — NFR-003 positive composition unpinned.** No named test asserted BOTH `<base>` AND
  the merged planning commit are ancestors of a no-dep lane (distinct from FR-010's detached-fail). → T001
  step 6 adds the shared-ancestor positive-composition assertion.
- **F-PT6 (reviewer) — `__all__` export instruction inapplicable/harmful.** `worktree_allocator.py` has no
  `__all__`; 16 modules import by name; a single-entry `__all__` would hide the public surface + trip
  C-007. → T003 step 4 rewords: omit, or add a COMPLETE `__all__`.

## LOW (folded)

- **F-PT7 (implementer) — S1192 message location.** Build the message inside `UnhonorableBaseError`
  (`__init__`/`to_dict`) so the 4 raise sites carry no duplicated f-strings + DIR-007 docstring. → T003 step 1.
- **F-PT8 (implementer) — `to_dict()` unit test.** Add a focused test asserting route/wp_id/base keys. → T003 Validation.
- **F-PT9 (both) — FR-011 read locus.** Read the recorded base in `evaluate_for_review_gate` (has `wp_id`),
  via `load_context`/`WorkspaceContext.base_branch` — NOT the wp_id-less `resolve_lane_base_ref`. → T005 step 1.
- **F-PT10 (reviewer) — DoD honesty.** FR-008 is docstring-only (review, not a test); except-tuple listing
  is documentary/untestable. → DoD reworded; marker-baseline wording corrected (gates derive live from
  collection, no static file).

## Confirmed / PASS
- Single-WP is correct (both). Marker-convention SATISFIED (`pytestmark` matches CI-routed markers).
- No-mock clauses survived into AC-3/AC-4; fixture-fidelity gate + FR-010 no-residual + swap-back are
  concrete and non-fakeable (reviewer). ruff C901 has headroom; only Sonar nesting was the exposure (implementer).
