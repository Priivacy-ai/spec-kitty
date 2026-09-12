# Contract: DistributionProfile

## Shape

```python
@dataclass(frozen=True)
class DistributionProfile:
    package_name: str
    package_aliases: tuple[str, ...] = ()
    upgrade_provider: object | None = None  # LatestVersionProvider instance or None
    index_url: str | None = None
    extra_index_url: str | None = None
    data_freshness_seconds: int | None = None
    disable_public_pypi_notifier: bool = False
    version_label: str | None = None
```

## Consumers

| Consumer | Fields used |
|---|---|
| `resolve_cli_package_name` / version utils | `package_name`, `package_aliases` |
| session-presence refresh / compat planner | provider + `package_name` |
| `has_fresh_data` path | `data_freshness_seconds` |
| remediation / upgrade_hint | `package_name`, `index_url`, `extra_index_url` |
| `maybe_emit_no_upgrade_notice` | `disable_public_pypi_notifier` |
| `--version` banner | `version_label` or `package_name` |

## Stock profile

`package_name="spec-kitty-cli"`, empty aliases, `PyPIProvider`, no index URLs, default freshness, notifier enabled, `version_label=None` (banner uses package name).
