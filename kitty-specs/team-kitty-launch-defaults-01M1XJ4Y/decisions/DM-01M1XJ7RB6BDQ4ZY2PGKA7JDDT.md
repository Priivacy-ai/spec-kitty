# Decision Moment `01M1XJ7RB6BDQ4ZY2PGKA7JDDT`

- **Mission:** `team-kitty-launch-defaults-01M1XJ4Y`
- **Origin flow:** `specify`
- **Slot key:** `specify.rules.owned-checkout-under-active-sync`
- **Input key:** `owned_checkout_sync_rule`
- **Status:** `canceled`
- **Created:** `2026-09-07T09:12:24.166340+00:00`
- **Resolved:** `2026-09-07T09:19:58.064748+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

With sync on by default, owned-checkout lane moves (move-task/mark-status --owned-checkout) currently refuse with OWNED_SYNC_UNSUPPORTED. What must hold at launch?

## Options

- Owned-checkout moves must fully participate in hosted sync (fan-out) like any other move
- Owned-checkout moves succeed locally and skip hosted fan-out with a visible warning
- Keep refusing; owned checkouts are a dev-only path
- Other

## Final answer

_(none)_

## Rationale

Question was framed in the retired 'sync' vocabulary (OWNED_SYNC_UNSUPPORTED); operator directed that the live model is Zeitgeist only. Re-asking after reading the Zeitgeist and SaaS repositories.

## Change log

- `2026-09-07T09:12:24.166340+00:00` — opened
- `2026-09-07T09:19:58.064748+00:00` — canceled
