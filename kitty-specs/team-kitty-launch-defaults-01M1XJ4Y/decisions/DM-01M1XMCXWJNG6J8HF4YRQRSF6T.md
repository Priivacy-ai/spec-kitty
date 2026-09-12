# Decision Moment `01M1XMCXWJNG6J8HF4YRQRSF6T`

- **Mission:** `team-kitty-launch-defaults-01M1XJ4Y`
- **Origin flow:** `plan`
- **Slot key:** `plan.offline-switch.surface`
- **Input key:** `offline_switch_surface`
- **Status:** `resolved`
- **Created:** `2026-09-07T09:50:10.834306+00:00`
- **Resolved:** `2026-09-07T09:52:02.123926+00:00`
- **Opened by:** `cli`
- **Other answer:** `true`

## Question

Where does the offline switch live: environment variable only, environment plus a persisted config.toml key, or also a CLI toggle like the existing 'spec-kitty moments off'?

## Options

- Env var + config.toml key (env wins); no new CLI command
- Env var only
- Env + config + a CLI toggle (spec-kitty hosted off/on/status)
- Other

## Final answer

No offline switch. Authentication state is the switch: no session and no service token means zero hosted requests (fail closed on identity); auth logout/login toggle it; CI carries no token; agent-facing moments keep 'spec-kitty moments off'.

## Rationale

_(none)_

## Change log

- `2026-09-07T09:50:10.834306+00:00` — opened
- `2026-09-07T09:52:02.123926+00:00` — resolved (final_answer="No offline switch. Authentication state is the switch: no session and no service token means zero hosted requests (fail closed on identity); auth logout/login toggle it; CI carries no token; agent-facing moments keep 'spec-kitty moments off'.")
