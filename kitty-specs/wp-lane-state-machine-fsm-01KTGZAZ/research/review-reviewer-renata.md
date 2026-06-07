# Adversarial review — reviewer-renata (opus)

**Change:** `fix/status-genesis-lane-bootstrap` @ `a43aa6a06` — `Lane.GENESIS` + FSM-as-source-of-truth + finalize event-log clobber fix (#1589, #1666).
**Verdict:** **SHIP-WITH-FIXES.**

## Findings

**1. [MEDIUM] Read/write layers do NOT agree on the unseeded-WP default — ADR claim is inaccurate.**
`status/emit.py` `_derive_from_lane` returns `GENESIS` for an unseeded WP, but the read side was never updated: `coordination/status_service.py` (`wp_lane_actor_from_events`) still returns `Lane.PLANNED`, and `coordination/status_transition.py::read_current_wp_state_transactional` fallback returns `Lane.PLANNED`. The ADR asserts "Read and write layers now agree" — false. Consequence: `status/work_package_lifecycle.py::start_implementation_status` reads PLANNED for an unseeded WP → enters the `current_lane == PLANNED` branch → emits batch `[claimed, in_progress]` → batch emit re-derives `from_lane=genesis` → `validate_transition("genesis","claimed")` raises a raw `TransitionError: Illegal transition: genesis -> claimed` instead of a clean `WorkPackageStartRejected`. Falsification ran: direct `emit(... to_lane="claimed")` on an unseeded WP raised; seeding `genesis->planned` first succeeded. Reachability: off happy path (finalize seeds first) but exactly the #1589 split-brain class. Fix: align `wp_lane_actor_from_events` + the transactional read fallback to `GENESIS`; add an explicit `current_lane == GENESIS` branch in `start_implementation_status` raising an actionable error.

**2. [LOW] `genesis` accepted as a valid `to_lane` by schema validation.** `validate.py` adds `Lane.GENESIS.value` to the accepted set for BOTH `from_lane` and `to_lane`; genesis should only be a `from_lane`. Defense-in-depth holds (no `*->genesis` edge) but the schema layer is laxer than intended. Fix: scope the allowance to `from_lane`.

**3. [LOW] Regression test covers the helper in isolation, not the finalize wiring.** `test_finalize_coord_staging.py` pins `_stage_finalize_artifacts_in_coord_worktree` but no test exercises `finalize_tasks` end-to-end to confirm the helper is invoked with the right args and the status files are excluded at the commit call site. Fix (optional): thin integration test asserting the committed coord event log still contains bootstrap lane events after a coord-topology finalize.

## Verified correct (falsification attempts that failed to break it)
- Clobber fix correctly scoped: non-coordination missions still commit primary-checkout status files (skip only in the coord-worktree branch).
- Derived `ALLOWED_TRANSITIONS` exactly equals old 27 edges + 2 genesis edges (set-diff).
- Genesis seed works; no edges into genesis; stray `to_lane=genesis` rejected at transition validation.
- Runtime claim path safe: `runtime_bridge.py` selects claimable WPs via `_find_first_wp_by_lane("planned")`; a genesis WP never materializes.
- Tests genuinely fixed, not weakened (`_seed_planned` performs the real seed; counts increased). 995 status-suite tests pass.
- `ruff` clean; 6 mypy `no-any-return` are all pre-existing on upstream/main.
- ADR accurate except the "read and write layers now agree" claim (Finding 1).
