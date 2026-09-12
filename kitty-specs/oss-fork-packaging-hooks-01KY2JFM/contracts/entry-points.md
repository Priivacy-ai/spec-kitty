# Contract: Packager entry-point groups

## Groups

| Group | Cardinality | Load shape | Fallback |
|---|---|---|---|
| `spec_kitty.cli_package` | 0..n (prefer 1) | `str`, zero-arg callable → `str`, or object with `package_name`/`name` | `packages_distributions` → `"spec-kitty-cli"` |
| `spec_kitty.upgrade_provider` | 0..n | zero-arg callable/type → object with `get_latest` | `PyPIProvider()` |
| `spec_kitty.distribution_profile` | 0..1 preferred | zero-arg callable/type → `DistributionProfile` | synthesize from above / stock |

## Multi-registration

- Upgrade providers: `SPEC_KITTY_UPGRADE_PROVIDER=<entry_point_name>` selects; else first name alphabetically.
- Unknown env name: ignore and use deterministic alphabetical pick (or stock if load fails) — never invent a class.
- Load/construct errors: fall back to stock; never raise to callers.

## Non-goals

- No runtime env var for distribution package **name**.
- No `.kittify/config.yaml` keys for these hooks.
