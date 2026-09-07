# Decision Moment `01M1XM170GDEH668X4GFJDVFK6`

- **Mission:** `team-kitty-launch-defaults-01M1XJ4Y`
- **Origin flow:** `specify`
- **Slot key:** `specify.rules.hosted-target-default`
- **Input key:** `hosted_target_default_rule`
- **Status:** `resolved`
- **Created:** `2026-09-07T09:43:46.960851+00:00`
- **Resolved:** `2026-09-07T09:45:22.915018+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

On a launch build with nothing configured, auth login and capability minting target https://team.spec-kitty.ai. What wins when a config.toml [sync].server_url or SPEC_KITTY_SAAS_URL is also present?

## Options

- env var > config.toml > packaged default; a config pointing at another host silently wins over the packaged default
- env var > packaged default; config.toml server_url is retired with the sync vocabulary
- Other

## Final answer

env var > config.toml server_url > packaged default; config pointing at another host wins over the packaged default without split-brain; split-brain guard only for env-vs-config disagreement. Plus: the resolved target and its source must be visible to the user via auth login / auth status.

## Rationale

_(none)_

## Change log

- `2026-09-07T09:43:46.960851+00:00` — opened
- `2026-09-07T09:45:22.915018+00:00` — resolved (final_answer="env var > config.toml server_url > packaged default; config pointing at another host wins over the packaged default without split-brain; split-brain guard only for env-vs-config disagreement. Plus: the resolved target and its source must be visible to the user via auth login / auth status.")
