# Contract — Anti-bypass guard (WP3, FR-007)

A structural/architectural test that fails when a new allocation or degrade route computes a parent ref
(or a degrade target) inline instead of routing through the shared seam — naming the offending site.

## Location

`tests/architectural/test_lane_allocation_single_seam.py` (runs in CI's architectural suite alongside
`test_shared_package_boundary.py`).

> **Depends on WP2 AND WP4 (post-plan squad, paula MED).** Assertion 1–2 test WP2's seam; assertion 3
> tests WP4's read companion + migration. Sequence WP3 AFTER both (WP1→WP2→WP4→WP3→WP5); a guard authored
> before WP4 would be red on the un-migrated sites or vacuous. WP3 may be *authored* red-first before WP2
> (a guard naming a not-yet-existent seam is a legitimate red anchor), but it cannot be *approved* until
> WP2 and WP4 land.

## What it asserts

> **Positive def-use, not literal-pattern matching (post-plan squad, debugger MED — anti-fakeability).**
> The guard must NOT key on the literal spelling `coordination_branch if … else mission_branch` — that
> misses a bypass composed from other names (`base or coordination_branch or mission_branch`, or an inline
> `lanes_manifest.mission_branch`). Instead assert **positively**: every value that flows into a
> `_create_lane_worktree` / `_ensure_mission_branch` parent argument, on every route, has its
> data-dependency origin in a call to `resolve_lane_base_or_refuse` (AST def-use / call-graph). A parent
> argument whose origin is any other computed expression is the bypass.

1. **Allocation single-seam (FR-001):** in `src/specify_cli/lanes/worktree_allocator.py`, every parent-ref
   argument passed to a lane-creation/branch-ensure call traces (def-use) to a `resolve_lane_base_or_refuse`
   return. No other function derives a lane parent ref. Anchor on the SYMBOL `resolve_lane_base_or_refuse`
   and the creation-call symbols, not line numbers.
2. **All four routes call the seam:** each of the four route branches (FRESH_COORD, FRESH_LEGACY, REUSE,
   CRASH_RECOVERY) in `allocate_lane_worktree` reaches a `resolve_lane_base_or_refuse` call (or raises
   `UnhonorableBaseError` via it). Assert route coverage via AST, not a bare call count.
3. **Read/degrade family (FR-006/FR-007):** each read-side degrade `try/except` around a coord-surface
   read either calls `resolve_read_dir_or_degrade` or is on the explicit allowlist WITH a rationale that
   satisfies the read-dir-degrade acceptance criterion (names the failed strategy + reason). A new
   un-allowlisted, un-routed degrade `try/except` fails the test, naming `file:line`.

## Failure message contract

On violation the test names the offending `file:line` and the rule ("inline parent-ref computation
outside resolve_lane_base_or_refuse" / "unregistered read-degrade site"), so a future contributor sees
exactly where the bypass is and how to fix it — the recurrence guard's whole purpose.

## Allowlist discipline

The allowlist (for bespoke sites like `status/aggregate.py`) is a small, commented set in the test.
Adding to it requires a rationale comment — the review point where a reviewer decides "this genuinely
cannot use the seam" rather than silently letting a bypass through. This is the structural analogue of
the fail-loud contract: a bypass is either impossible or explicitly, reviewably justified.

## Red-first — deterministic non-vacuity (post-plan squad, debugger MED)

"Introduce a temp bypass by hand" is too weak — a checker that only scans the (already-clean) live module
passes tautologically. Instead: the test parses a **synthetic bypassing function from an in-test AST
fixture** (a string of Python defining a function that computes a parent ref inline / adds an
un-allowlisted degrade `try/except`) and asserts the checker flags THAT fixture's `file:line` with the
right rule. The same checker is then run over the live module and asserted clean. This proves the checker
actually detects bypasses (non-vacuous) AND that the live code is clean — without depending on a
hand-introduced temp edit.
