# Contract: environment variables and configuration after this mission

| Name | Status | Meaning |
|---|---|---|
| `SPEC_KITTY_SAAS_URL` | kept | environment override of the hosted target |
| `SPEC_KITTY_SAAS_TOKEN` | kept | service-token bearer (counts as authenticated) |
| `SPEC_KITTY_TEAM_SLUG` | kept | scope selector |
| `SPEC_KITTY_SAAS_FANOUT_TIMEOUT` | kept | fan-out bound |
| `SPEC_KITTY_SKIP_PRE_REVIEW_GATE` | new | skip the pre-review regression gate |
| `SPEC_KITTY_NO_MOMENT_HANDLERS` | new | register no moment handlers at import |
| `SPEC_KITTY_ENABLE_SAAS_SYNC` | removed | unknown to the CLI; no effect, no notice |
| `SPEC_KITTY_SYNC_DISABLE` | removed | unknown; no effect |
| `SPEC_KITTY_SYNC_MINIMAL_IMPORT` | removed | unknown; no effect |
| `config.toml [team_kitty] server_url` | new | configured hosted target |
| `config.toml [sync] server_url` | removed | never read |

- `core/env.py` exposes two single-purpose accessors for the new names; the `SYNC_DISABLE_ENV_VARS` tuple and `first_set_sync_disable_env` are deleted.
- `core/secret_redaction.py` printable allowlist and `m_3_2_8_provision_kitty_env.py::GOVERNED_OPERATOR_VARS` list the new names and drop the retired ones; the migration never seeds a retired name again and never writes a value it did not observe.
- `docs/api/environment-variables.md` is the user-facing source for this table.
