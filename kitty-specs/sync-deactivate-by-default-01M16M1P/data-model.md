# Data Model: Sync Deactivated By Default

No persistent data entities are introduced or changed. Sync-enabled state is **environment-only** (no config.yaml / meta.json field), which is why no migration is required.

## Arming state (derived, not stored)

`sync_active()` is a pure function of three environment toggles:

- `E` = `SPEC_KITTY_ENABLE_SAAS_SYNC`
- `D` = `SPEC_KITTY_SYNC_DISABLE`
- `M` = `SPEC_KITTY_SYNC_MINIMAL_IMPORT`

`sync_active = E AND NOT (D OR M)` — equivalently `is_saas_sync_enabled() and first_set_sync_disable_env() is None`.

| E | D | M | sync_active | Meaning |
|---|---|---|-------------|---------|
| 0 | 0 | 0 | inactive | bare-install default |
| 1 | 0 | 0 | active | explicit opt-in |
| 1 | 1 | 0 | inactive | disable wins |
| 1 | 0 | 1 | inactive | minimal-import = force-off for arming |
| 1 | 1 | 1 | inactive | disable wins |
| 0 | * | * | inactive | no opt-in |

## Downstream gates (unchanged)

- **Per-project egress consent** (`sync/egress.py`): evaluated only when `sync_active()` is true. Arming does not imply consent (C-007).
- **Pre-review regression gate**: independent of `sync_active()`; governed solely by `SPEC_KITTY_PRE_REVIEW_GATE_DISABLE` (#2801).
