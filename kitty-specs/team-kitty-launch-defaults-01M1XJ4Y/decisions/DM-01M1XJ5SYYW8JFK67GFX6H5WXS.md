# Decision Moment `01M1XJ5SYYW8JFK67GFX6H5WXS`

- **Mission:** `team-kitty-launch-defaults-01M1XJ4Y`
- **Origin flow:** `specify`
- **Slot key:** `specify.scenario.first-run-after-launch`
- **Input key:** `first_run_scenario`
- **Status:** `resolved`
- **Created:** `2026-09-07T09:11:20.286198+00:00`
- **Resolved:** `2026-09-07T09:12:19.880423+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

After launch, an operator installs the CLI fresh, runs a normal command (e.g. spec-kitty status) with no environment variables set and no auth session: what exactly should they see and what must still work locally?

## Options

- Silent local operation; one-time non-blocking hint to run auth login
- Blocking prompt to log in before any mission command
- Silent local operation with no hint until a hosted command is attempted
- Other

## Final answer

Silent local operation; one-time non-blocking hint to run auth login

## Rationale

_(none)_

## Change log

- `2026-09-07T09:11:20.286198+00:00` — opened
- `2026-09-07T09:12:19.880423+00:00` — resolved (final_answer="Silent local operation; one-time non-blocking hint to run auth login")
