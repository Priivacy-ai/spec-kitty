# Decision Moment `01M1XMHB8FWZJR23540JXM6817`

- **Mission:** `team-kitty-launch-defaults-01M1XJ4Y`
- **Origin flow:** `plan`
- **Slot key:** `plan.config.target-key-name`
- **Input key:** `target_config_key`
- **Status:** `resolved`
- **Created:** `2026-09-07T09:52:35.599715+00:00`
- **Resolved:** `2026-09-07T09:53:54.778309+00:00`
- **Opened by:** `cli`
- **Other answer:** `true`

## Question

The configured server address today is config.toml [sync].server_url. Keep that key as-is, or introduce a Team Kitty-vocabulary key with [sync].server_url read as a deprecated alias?

## Options

- Introduce [team_kitty] server_url; keep [sync].server_url as a read-only deprecated alias with a one-time notice
- Keep [sync].server_url unchanged; no rename
- Other

## Final answer

Introduce [team_kitty] server_url as the only key; remove [sync].server_url outright, no alias and no deprecation period (only developers ever set it; sync is dead).

## Rationale

_(none)_

## Change log

- `2026-09-07T09:52:35.599715+00:00` — opened
- `2026-09-07T09:53:54.778309+00:00` — resolved (final_answer="Introduce [team_kitty] server_url as the only key; remove [sync].server_url outright, no alias and no deprecation period (only developers ever set it; sync is dead).")
