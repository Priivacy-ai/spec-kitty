# Decision Moment `01KZ79PH1EQHFXZ98HA36TAR4X`

- **Mission:** `review-cycle-verdict-seam-rebuild-01KZ2W7W`
- **Origin flow:** `plan`
- **Slot key:** `wp15_real_coord_cell`
- **Input key:** `wp15_real_coord_cell`
- **Status:** `resolved`
- **Created:** `2026-08-04T21:08:29.870549+00:00`
- **Resolved:** `2026-08-04T21:08:32.873541+00:00`
- **Resolved by:** `Stijn Dejongh (operator)`
- **Opened by:** `claude-opus-5`
- **Other answer:** `false`

## Question

WP15's durability matrix 'topology' axis is a patched _skip_target_branch_commit boolean, not a real coord worktree, and the docstring falsely claims the coord fixture is reserved for T069 (nothing uses it). FR-015's topology dimension -- load-bearing because WP04's REVIEW_CYCLE routing changes which ref the commit lands on -- has zero matrix coverage. WP13's revert fix (approved) makes a real coord cell viable once merged into lane-g. Add a real coord cell, or record the gap?

## Options

- add-a-real-coord-worktree-durability-cell
- fix-docstrings-and-record-the-gap

## Final answer

add-a-real-coord-worktree-durability-cell

## Rationale

OPERATOR-CONFIRMED, consistent with the standing instruction that tackling coverage gaps of this class is the mission's purpose. A patched-boolean topology axis discharges FR-015's letter, not its substance -- exactly the failure the WP prompt names -- and the docstring that calls the coord fixture 'reserved for T069' is false (the fixture is imported nowhere and T069's real-git cell is itself single_branch). The WP15 reviewer originally recommended recording-not-filling ONLY because it believed a coord cell would hit the WP11 revert PRIMARY-vs-COORD bug and produce a red WP15 is forbidden to fix; that premise is now void -- WP13 fixed and I approved that revert bug (kind=REVIEW_CYCLE + worktree_root resolution), so a real coord cell should pass once WP13 is merged into lane-g. Scope: (1) merge lane-e's WP13 into lane-g so the revert fix is present; (2) add a genuine coord-worktree durability cell (reuse tests/integration/coord_topology_fixture.py) exercising the COORD-ref commit and the revert landing on the coord ref, with the same commit-removal mutation sensitivity the single_branch cells have; (3) correct the two truthfulness defects unconditionally -- the false 'reserved for T069' docstring, and the SC-004 flakiness mischaracterization ('5/5 alone, 4/4 preceded' is factually wrong; it is a load-window race, red under -n auto and occasionally alone). SC-004 stays UNMET and unweakened regardless -- this ruling adds coverage, it does not touch that probe. The honest CI statement remains that tests/integration is intermittently 8-red (7 base + the SC-004 probe).

## Change log

- `2026-08-04T21:08:29.870549+00:00` — opened
- `2026-08-04T21:08:32.873541+00:00` — resolved (final_answer="add-a-real-coord-worktree-durability-cell")
