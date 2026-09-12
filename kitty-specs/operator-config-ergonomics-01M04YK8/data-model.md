# Data Model: Operator Config & Install Ergonomics

These are configuration/infrastructure entities (no persistent DB). Invariants are the testable heart of the mission.

## KittyEnvFile (two-tier)
- **Locations**: home-tier `${SPEC_KITTY_HOME}/.kitty.env`; per-repo `<repo>/.kittify/.kitty.env`.
- **Shape**: newline-delimited `KEY=VALUE`; `export ` prefix tolerated; surrounding quotes stripped; full-line `#` comments; values literal (no in-value interpolation).
- **Contents**: path vars (excl. `SPEC_KITTY_HOME`) incl. `SPEC_KITTY_PACKS_ROOT`; sync vars (`SPEC_KITTY_ENABLE_SAAS_SYNC`, `SPEC_KITTY_SAAS_URL`, `SPEC_KITTY_SAAS_TOKEN`, `SPEC_KITTY_ORG_TOKEN`, `SPEC_KITTY_TEAM_SLUG`); beta var `SPEC_KITTY_PRERELEASE`.
- **Invariants**:
  - I1: precedence real-env > per-repo > home (tiers merged `{**home, **repo}` then a single `setdefault`).
  - I2: MUST NOT define `SPEC_KITTY_HOME` (locator) — such a line is ignored-with-warning.
  - I3: seeded into `os.environ` before any spec-kitty import.
  - I4: gitignored + claudeignored; never committed.
  - I5: malformed line → skipped + debug log; absent file → warn-continue; present-but-unreadable → fail loud.

## ConfigPointer (`.kittify/config.yaml` `env_file`)
- **Field**: `env_file: ${SPEC_KITTY_HOME}/.kitty.env` (the sole expansion this key introduces).
- **Invariants**: resolved once at bootstrap (not by the ~30 config readers); lives outside any `extra="forbid"` pydantic block; committed (no secret — a path only).

## EnvExpansionSeam (`kernel/env_expand.py`)
- **API**: `expand_env_template(raw, *, inject_defaults: bool, environ=None) -> str`; `UnresolvedEnvTokenError`; `_DEFAULT_INJECTORS` registry; `get_packs_root_default() -> Path` (kernel/paths).
- **Invariants**:
  - E1: `inject_defaults=False` → surviving token raises (resolution fields).
  - E2: `inject_defaults=True` → surviving `${SPEC_KITTY_PACKS_ROOT}` substitutes `get_packs_root_default()` = `get_built_in_pack_root().parent`.
  - E3: `org_pack_config._expand_path_template` delegates with `inject_defaults=False` — fail-loud contract byte-preserved.

## ProvenanceToken
- **Form**: `${SPEC_KITTY_PACKS_ROOT}/built-in/<kind>/<file>` in `charter.yaml` catalog `source_path` and `agent_profiles_manifest.json` `source_path`.
- **Producer**: one shared path→token normalizer consumed by both carriers.
- **Invariants**: P1 no absolute path ever serialized (incl. when `SPEC_KITTY_PACKS_ROOT=<abs>` is exported); P2 byte-identical across editable/wheel.

## SecretAllowlist
- **Shape**: set of printable var names (fail-closed).
- **Invariant**: any var not on the allowlist is never rendered by value in doctor/`sync status`/logs.

## ReleaseChannelPreference
- **Var**: `SPEC_KITTY_PRERELEASE` (default off).
- **Invariants**: off → 0 rc advisories; on → newest PEP 440 pre-release surfaced + pinned `==<rc>` install command.

## Migrations (two, independent)
- **HealProvenanceMigration** (WP1): `detect` = any absolute built-in `source_path`; `apply` rewrites to tokens via the charter-yaml safe round-trip + manifest save; idempotent.
- **ProvisionKittyEnvMigration** (WP2): create `.kitty.env` (seed only already-set values; never `SPEC_KITTY_PACKS_ROOT`), register pointer, add ignore rules; idempotent; ordering coordinated with #3381.
- **Invariant M1**: re-run of either produces zero changes.
