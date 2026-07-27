# Decision Moment `01KQ807NKAS36HJPG6WBQN5C6G`

- **Mission:** `charter-golden-path-e2e-tranche-1-01KQ806X`
- **Origin flow:** `specify`
- **Slot key:** `specify.fixture.choice`
- **Input key:** `fresh_project_fixture_choice`
- **Status:** `resolved`
- **Created:** `2026-04-27T17:36:45.675721+00:00`
- **Resolved:** `2026-04-27T17:36:51.908445+00:00`
- **Other answer:** `false`

## Question

Should the golden-path test use a new fresh_e2e_project fixture (public spec-kitty init from scratch) or reuse the existing e2e_project fixture (which copies .kittify from the source checkout)?

## Options

- fresh_e2e_project (new fixture)
- e2e_project (reuse existing)
- Other

## Final answer

fresh_e2e_project (new fixture). User confirmed the point of this tranche is proving operator-path behavior from a clean project; copying .kittify from the source checkout would weaken the test and preserve the exact class of hidden-coupling failures we want to catch.

## Rationale

_(none)_

## Change log

- `2026-04-27T17:36:45.675721+00:00` — opened
- `2026-04-27T17:36:51.908445+00:00` — resolved (final_answer="fresh_e2e_project (new fixture). User confirmed the point of this tranche is proving operator-path behavior from a clean project; copying .kittify from the source checkout would weaken the test and preserve the exact class of hidden-coupling failures we want to catch.")
