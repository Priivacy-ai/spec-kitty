# WP02 Review — Cycle 1 (Reviewer Renata)

**Verdict: REJECT (one blocker).** The gate's core mechanics are sound — exact assertion
shapes, strict-xfails, no skips, ruff+mypy clean, 5 passed / 6 strict-xfail / 0 XPASS,
and I confirmed by live probing that the green cells genuinely agree and that a known-RED
cell genuinely diverges (the assertion has real teeth). One coverage gap blocks approval.

## Blocker — Issue 1: `coord-behind` topology is missing and undocumented

The matrix omits the `coord-behind` topology entirely, and the module docstring's
cell→WP map does not mention it.

This is an explicitly-required input class:
- `data-model.md` line 13 lists `coord-behind` as a distinct topology
  ("coord exists but primary is ahead/diverged" → "coord preferred unless empty").
- **NFR-003 (spec.md) enumerates it by name**: the FR-002 test "covers ≥ the
  (no-coord, coord-fresh, **coord-behind**, coord-empty, ambiguous-mid8,
  bare-slug-vs-`<slug>-<mid8>`-handle) input classes."

I probed `coord-behind | slug-mid8` live: it is non-divergent today (all three entry
points agree on the coord dir, like `coord-fresh`), so it is NOT a hidden divergence.
But this is still a false-green vector for the C-004 gate: WP06's DoD asserts "zero xfail
markers remain" and then authorizes deleting a duplicate resolver. If `coord-behind` is
never asserted over, the deletion is green-lit without ever having proven equivalence for
a topology the spec names as in-scope, and a future regression in `coord-behind` handling
would go uncaught.

**How to fix (pick one):**
1. Add `coord-behind` to the `_MATRIX` with both `bare-slug` and `<slug>-<mid8>` cells,
   and a `_build_topology` branch that materialises the populated coord worktree with the
   primary checkout ahead/diverged. The `slug-mid8` cell is GREEN today; the `bare-slug`
   cell will diverge identically to `coord-fresh/bare` (resolver mid8-blind → primary,
   surface/aggregate → coord) and should be `xfail(strict=True, reason="closed by
   WP03/FR-009 ...")`. Add the corresponding rows to the docstring cell→WP map.
2. If the team judges `coord-behind` behaviorally identical to `coord-fresh` for the
   resolution surfaces and not worth a separate cell, **document that explicitly** in the
   module docstring's cell→WP map (a `coord-behind — folds into coord-fresh; no distinct
   resolution behavior` row) so the omission is a recorded decision, not a silent gap.

Option 1 is preferred — the gate is the deletion safety authority, and an exercised cell
is strictly stronger than a documented assumption.

## Non-blocking observations (no action required)

- Assertion shapes verified exact: `Path.resolve()` equality for dirs (Outcome normalizes
  at construction, line 126) and `type is type and error_code == error_code` for errors
  (line 177). Only one `assert ... and` in the module, and it is the prescribed error shape.
- Zero `pytest.skip`; both `xfail` markers carry `strict=True`.
- Live-verified GREEN cells: ambiguous-mid8 (all three raise
  `MISSION_AMBIGUOUS_SELECTOR`; canonical `not is_dir` asserted first so no silent-pick
  false-green) and no-coord/slug-mid8 (identical primary dir).
- Live-verified negative control: `coord-fresh/bare` genuinely diverges (read_path→primary
  vs surface/aggregate→coord), proving `_assert_equivalent` fires on real disagreement.
- xfail→WP mapping correct: coord-fresh/bare→WP03/FR-009; coord-empty/*→WP06/FR-006;
  coord-deleted/*→WP06/FR-006+FR-005; runtime-boundary→WP05/FR-005.
- Fixtures realistic: real git repo, real `.worktrees/<slug>-<mid8>-coord/` layout, real
  26-char ULID; no toy slugs.
- Owned-file-only; zero production code touched; runtime import target
  (`mission_runtime.resolution.resolve_placement_only`) exists and the xfail test runs.

## Anti-pattern checklist
1. Dead code — N/A (test-only WP). 2. Synthetic-fixture — PASS (entry points invoked live;
deleting production resolvers would change outcomes). 3. Silent empty return — PASS (the
broad `except BaseException` captures-and-compares, justified inline). 4. FR coverage —
**FAIL** (FR-002/NFR-003 require coord-behind; absent). 5. Frozen surface — PASS.
6. Locked decision — PASS (no `pytest.skip`, all xfails strict, per T006/T008 MUST-NOTs).
7. Shared-file ownership — PASS (sole owner of the file). 8. Production fragility — N/A.

**VERDICT: REJECT** — add or document the `coord-behind` topology (Issue 1); everything
else is approve-ready and should not be re-litigated on resubmission.
