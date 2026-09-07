# Data Model: Team Kitty launch defaults for the CLI

## Entities

### HostedTarget
The address hosted operations use, with provenance.

| Field | Type | Rule |
|---|---|---|
| `resolved_server_url` | normalized URL | never blank; trailing slash stripped |
| `source` | `environment` \| `configuration` \| `packaged_default` | exactly one; the only new value is `packaged_default` |
| `environment_server_url` | URL or null | from `SPEC_KITTY_SAAS_URL` |
| `configured_server_url` | URL or null | from `config.toml [team_kitty] server_url`; malformed or blank reads as null |
| `override_mode` | existing enum | unchanged; packaged default never participates in a disagreement |

Invariants:
- `source = environment` iff `environment_server_url` is set and either equals the configured value or no configured value exists.
- `source = configuration` iff no environment value and a configured value exists.
- `source = packaged_default` iff neither exists.
- environment and configuration present and different ⇒ fail closed (`ServerTargetSplitBrain`), unchanged from today.

### AuthenticationState
| State | Meaning | Hosted behavior |
|---|---|---|
| `authenticated` | usable session (refreshable) or service token present | moments publish; readiness may nag on connected-team logout |
| `unauthenticated` | no session, no token | zero hosted requests of any kind |
| `expired_unrefreshable` | stored session cannot be refreshed | treated as unauthenticated; hint eligible |

Transitions: `auth login` → authenticated; `auth logout` → unauthenticated (and resets the sign-in hint marker); refresh failure → expired_unrefreshable.

### SignInHintMarker
Per-machine record under the runtime state root that the one-time sign-in hint was shown.

| Field | Rule |
|---|---|
| `shown_at` | ISO timestamp; written only when the hint is actually printed |
| location | runtime state root (never the project); one per `SPEC_KITTY_HOME` |
| reset | removed by `auth logout` |

Rules: printed only when interactive, not in JSON/help/version/non-TTY output; concurrent invocations may race, the marker is written atomically and the worst case is one duplicate hint.

### Capability (unchanged)
Relay-scoped grant `(team, deployment, repo, kind)` minted by the SaaS, cached under the runtime state root by `zeitgeist_client/credentials.py`. Not modified by this mission; referenced because owned checkouts now use it identically.

### OptOut switches
| Name | Scope | Replaces |
|---|---|---|
| `SPEC_KITTY_SKIP_PRE_REVIEW_GATE` | skips the pre-review regression gate on `--to for_review` | `SPEC_KITTY_SYNC_DISABLE` / `SPEC_KITTY_SYNC_MINIMAL_IMPORT` as gate opt-outs |
| `SPEC_KITTY_NO_MOMENT_HANDLERS` | registers no moment handlers at import (test isolation) | `SPEC_KITTY_SYNC_MINIMAL_IMPORT` |

Neither affects hosted egress semantics beyond its stated scope.

## Retired identifiers (no successor)
`SPEC_KITTY_ENABLE_SAAS_SYNC`, `SPEC_KITTY_SYNC_DISABLE`, `SPEC_KITTY_SYNC_MINIMAL_IMPORT`, `SYNC_DISABLE_ENV_VARS`, `first_set_sync_disable_env`, `is_saas_sync_enabled`, `sync_active`, `saas_sync_disabled_message`, `SAAS_SYNC_ENV_VAR`, `OWNED_SYNC_UNSUPPORTED`, config table `[sync]`.
