# Data Model: OSS Fork Packaging Hooks

## Entities

### DistributionProfile

| Field | Type | Required | Notes |
|---|---|---|---|
| `package_name` | `str` | yes | Canonical distribution name (e.g. `acme-spec-kitty-cli`) |
| `package_aliases` | `tuple[str, ...]` | no | Ordered fallbacks for installed-version lookup |
| `upgrade_provider` | `type \| LatestVersionProvider \| None` | no | Prefer resolved entry-point instance at runtime |
| `index_url` | `str \| None` | no | Primary simple/PyPI-compatible index for remediation argv |
| `extra_index_url` | `str \| None` | no | Secondary index for remediation argv |
| `data_freshness_seconds` | `int \| None` | no | Overrides “should we re-query?” TTL only |
| `disable_public_pypi_notifier` | `bool` | no | Default `False`; gates `maybe_emit_no_upgrade_notice` |
| `version_label` | `str \| None` | no | `--version` banner; default `package_name` |

**Invariants**:
- `package_name` is never read from a runtime env var.
- Stock profile (no entry points) equals today’s hardcodes.
- At most one loaded profile object preferred; multiple profile entry points → deterministic selection (sorted name) or documented fail-closed to stock (implementer chooses sorted-first to match provider behaviour).

### ResolvedPackageIdentity

Logical result of `resolve_cli_package_name()`:

| Field | Type | Notes |
|---|---|---|
| `name` | `str` | Final distribution name |
| `source` | `"entry_point" \| "packages_distributions" \| "default"` | Provenance for tests/diagnostics |

### LatestVersionResult (existing, extended)

| Field | Type | Notes |
|---|---|---|
| `version` | `str \| None` | Sanitised |
| `source` | `"pypi" \| "simple_index" \| "none"` | Extended with `simple_index` |
| `error` | `str \| None` | Fixed vocabulary tokens |

## Relationships

```
DistributionProfile ──uses──► LatestVersionProvider
resolve_cli_package_name() ──feeds──► DistributionProfile.package_name (synthesized)
spec_kitty.cli_package ──► resolve_cli_package_name
spec_kitty.upgrade_provider ──► resolve_upgrade_provider
spec_kitty.distribution_profile ──► resolve_distribution_profile
```

## State / lifecycle

No persistent mutable state beyond existing upgrade cache file. Resolvers memoize in-process after first success; tests may clear memo via a documented test helper.
