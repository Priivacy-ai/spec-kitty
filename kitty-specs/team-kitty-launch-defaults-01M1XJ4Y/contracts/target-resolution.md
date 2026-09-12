# Contract: hosted target resolution

Authority: `specify_cli.auth.server_target.resolve_server_target` (single).

| env `SPEC_KITTY_SAAS_URL` | `config.toml [team_kitty] server_url` | Result | `source` |
|---|---|---|---|
| unset | unset | `https://team.spec-kitty.ai` | `packaged_default` |
| unset | `https://spec-kitty-dev.fly.dev` | dev host | `configuration` |
| `https://x` | unset | `https://x` | `environment` |
| `https://x` | `https://x` | `https://x` | `environment` (override mode NONE) |
| `https://x` | `https://y` | **fail closed**: `ServerTargetSplitBrain` naming both | — |
| unset | malformed/blank | packaged default | `packaged_default` |

- The `[sync]` table is never read. A `[sync]` table present in a config file is ignored entirely.
- `get_saas_base_url()` returns the env value or `None`; it no longer raises.
- Every hosted caller (auth login, token refresh, capability mint, admission preflight, tracker readiness, readiness nag) consumes the same resolved target; none may compute its own.
- `MISSING_HOST_CONFIG` can no longer occur; the readiness code for it is removed.
