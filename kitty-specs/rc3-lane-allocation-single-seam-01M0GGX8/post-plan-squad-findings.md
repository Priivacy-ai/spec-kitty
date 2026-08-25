# Post-plan adversarial squad — findings & dispositions

Point-cut: post-`/spec-kitty.plan`. Question: *does the M8 plan correctly generalize the #3571 class
without regressing landed M1/#2939/#1848 guardrails, and is the WP slicing grounded in current main?*
4 profile-loaded, read-only lenses: architect-alphonso, debugger-debbie, reviewer-renata, paula-patterns.
All line citations independently verified accurate; all three grounding claims (#2939 exclusion, #1848
ordering, guardrail tests exist) CONFIRMED. Convergent verdict: **sound, honestly grounded, proceed with
conditions.** No inter-lens divergence — findings complement.

| # | Sev | Finding (lens) | Disposition |
|---|-----|----------------|-------------|
| 1 | HIGH | Original seam name `resolve_lane_base_or_degrade` was a misnomer — it honors-or-**raises**, never degrades; `_or_degrade` re-teaches the retired bypass (architect) | **ACCEPTED** — renamed → `resolve_lane_base_or_refuse` across all artifacts; reframed the family as *fail-loud* (write/read degrade-or-refuse; allocate refuse-only) |
| 2 | MED | research D2 says `LaneBaseDecision` has an `optional refusal` field; data-model says refusal is *only* the raise (no field) — contradiction, dead field (architect) | **ACCEPTED** — delete refusal-field language from D2; refusal == exception |
| 3 | MED | Read companion over-generalized (rule-of-three): only 2 genuine degrade consumers (`generator.py:264` ZERO_EVIDENCE, `worktree_topology.py:173` DEGRADE_TO_FEATURE_DIR); FAIL_CLOSED sites re-raise (remove no try/except); aggregate + review_cycle bespoke (architect + reviewer) | **ACCEPTED** — scope helper to the 2 real degrade consumers; park FAIL_CLOSED pass-through + bespoke on the WP3 allowlist; each allowlist entry states which strategy it fails + why |
| 4 | MED | `read_dir_degrade.py` in `mission_runtime/` inherits an undocumented layering constraint: sibling `write_target_degrade.py` uses function-scoped imports + a `test_layer_rules.py` ledger entry to avoid a circular import (architect) | **ACCEPTED** — contract requires deferred imports + ledger entry `_MISSION_RUNTIME_ALLOWED_SPECIFY_CLI` |
| 5 | MED | Fold risks S3776 ceiling (15); `detached_base` already has 2 nesting levels (architect) | **ACCEPTED** — seam is a thin orchestrator delegating to the existing 4 trigger helpers + parent chooser; per-trigger tests; assert ≤15 |
| 6 | MED | Anti-bypass guard partially fakeable: keys on the literal `coordination_branch if…else mission_branch` spelling, misses other ref-name bypasses; red-first unspecified → vacuous pass (debugger + paula) | **ACCEPTED** — positive call-graph/def-use assertion (every parent/degrade assignment flows from a seam call) + deterministic synthetic-bypass AST fixture asserting the checker flags its `file:line` |
| 7 | MED | Missing WP3→WP4 dependency: the guard's read-degrade assertion tests WP4's output but WP3 is sequenced before WP4 (paula) | **ACCEPTED** — WP3 depends on **both** WP2 and WP4; resequence WP1→WP2→WP4→WP3→WP5 (WP5 after WP1) |
| 8 | MED | quickstart guardrail sweep: `reuse_self_heal` + `dep_merge_rollback` match ZERO tests → sweep green while running nothing for #2993/#1915 (debugger) | **ACCEPTED** — real tokens: `2993 or planning_artifacts`, `1915 or rolls_back` |
| 9 | MED | FR-004 "surrogate proxies are removed" is counterfactual — nothing is removed; routing already consults the authority. Closing #3460 as work-M8-did would be dishonest (reviewer) | **ACCEPTED** — FR-004 → "single-authority pinned by anti-divergence guard"; #3460 closure text = "already-satisfied on main, pinned by guard"; do not credit M8 for M1/#3618/WP05 work |
| 10 | MED | WP1 anti-divergence test has no red-first mechanism when zero residual gates exist (C-011 gap) (reviewer) | **ACCEPTED** — prove WP1's test red against a deliberately-introduced temp surrogate gate (same synthetic-red technique as the anti-bypass guard) |
| 11 | MED | Allowlist has no acceptance criterion → rubber-stamp under pressure (reviewer) | **ACCEPTED** — each allowlist entry names which of the 4 strategies it fails + why (checkable) |
| 12 | LOW | `base_honored` near-redundant with `base is None` (raise handles the rest) — keep for logging, not the anti-drop guarantee (architect) | **ACCEPTED** — note in data-model; the exception is the fail-loud mechanism |
| 13 | LOW | `route` stringly-typed while `topology` is an enum (architect) | **ACCEPTED** — add `LaneAllocationRoute` enum |
| 14 | LOW | Atomicity: `detached_base` guard today fires once at the shared pre-create point; relocating into each route must still precede `_create_lane_worktree` (architect) | **ACCEPTED** — red-first test per route: no worktree/branch after `UnhonorableBaseError` |
| 15 | LOW-MED | INV-6 cites a stale `--base` docstring at `:450-453` (that's `_merge_recorded_planning_commit`); the real docstring is `~:279-287` and already says "never smuggled" (reviewer) | **ACCEPTED** — re-anchor INV-6 to `~:279-287`, downgrade to a regression-pin |
| 16 | LOW | quickstart WP1 selector targets `tests/coordination/` but #3460 tests live in `tests/specify_cli/coordination/` (debugger) | **ACCEPTED** — fix selector |
| 17 | LOW | Stale route line numbers in lane-base-seam.md; real: `_resolve_lane_parent:247`, reuse `:321`, crash `:368`, detached `:398`, dependency_lane `:407`, fresh-coord `:414`, fresh-legacy `:428` (paula + debugger) | **ACCEPTED** — update + anchor the AST walk on symbols, not lines |
| 18 | LOW | `_review_cycle_reconcile_doctor.py` migration verdict deferred ("may stay bespoke") (reviewer) | **ACCEPTED** — implement-time decision recorded in the allowlist with the "not a degrade-read" proof |
| 19 | LOW | Co-edit with M5: the one shared hunk is the `generator.py` import region (`:20-33`), not the bodies (M5 at `:1319`, M8 at `:224-299`) (paula) | **ACCEPTED** — WP4 keeps the new degrade import function-local; note the import region in the PR body |
| — | INFO | M8 is a consolidation / anti-divergence refactor, not a #3571 reproduction; net-new *behavior* concentrates in WP5. WP2 red-first = the single-seam invariant (two helpers → one), red on main today. Keep M1's `test_explicit_base_replaces_coord_parent_on_no_dep_lane` as the standing #3571 guard (debugger + reviewer) | **ACCEPTED** — stated plainly in plan/research |

No contested finding was dropped. No divergence required a second-opinion delegate.
