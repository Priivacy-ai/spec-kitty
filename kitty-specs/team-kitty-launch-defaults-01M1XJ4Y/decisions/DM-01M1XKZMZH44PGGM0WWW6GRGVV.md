# Decision Moment `01M1XKZMZH44PGGM0WWW6GRGVV`

- **Mission:** `team-kitty-launch-defaults-01M1XJ4Y`
- **Origin flow:** `specify`
- **Slot key:** `specify.rules.owned-checkout-moments`
- **Input key:** `owned_checkout_moment_rule`
- **Status:** `resolved`
- **Created:** `2026-09-07T09:42:55.729692+00:00`
- **Resolved:** `2026-09-07T09:43:42.724740+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

When an agent moves a work package from an owned checkout on a launch build, does the moment go to the team's Zeitgeist relay exactly as from a lane worktree (delete OWNED_SYNC_UNSUPPORTED), or are owned checkouts private?

## Options

- Publish like any other checkout; delete the guard
- Owned checkouts are private; suppress their moments
- Other

## Final answer

Publish like any other checkout; delete the OWNED_SYNC_UNSUPPORTED guard

## Rationale

_(none)_

## Change log

- `2026-09-07T09:42:55.729692+00:00` — opened
- `2026-09-07T09:43:42.724740+00:00` — resolved (final_answer="Publish like any other checkout; delete the OWNED_SYNC_UNSUPPORTED guard")
