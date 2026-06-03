# Migrations — Version Alignment Convention

## Why

The upgrade runner selects migrations by comparing project version,
`target_version`, and the installed package version. If a migration target is
newer than the package version, users upgrading to that package will skip that
migration. This is especially dangerous for release candidates: `3.2.0` is
newer than `3.2.0rc35`.

## Convention

- New migration files land at `m_X_Y_Z[_preN]_<slug>.py` where the encoded
  version is the package version that first ships the migration.
- `target_version` must be less than or equal to the current
  `pyproject.toml` version.
- A release PR that adds or retargets migrations must keep `pyproject.toml`,
  `.kittify/metadata.yaml`, migration filenames, and migration `target_version`
  values aligned.
- `test_migration_chain_integrity.py` enforces ordering and contiguity of
  the chain.

## Writing a Migration

```python
# m_0_14_0_my_feature.py
from pathlib import Path
from .base import BaseMigration
from .m_0_9_1_complete_lane_migration import get_agent_dirs_for_project

class Migration(BaseMigration):
    version = "0.14.0"
    description = "Add my-feature support"

    def apply(self, project_path: Path, dry_run: bool = False) -> None:
        # Use config-aware helper — never hardcode AGENT_DIRS
        agent_dirs = get_agent_dirs_for_project(project_path)
        for agent_root, subdir in agent_dirs:
            agent_dir = project_path / agent_root / subdir
            if not agent_dir.exists():
                continue  # respect user deletions
            # ... update files ...
```

Key rules:
- **Always** import `get_agent_dirs_for_project` from `m_0_9_1_complete_lane_migration`.
- **Never** hardcode `AGENT_DIRS` in new migrations.
- **Skip** missing directories (`continue`) — do not recreate them.
- **Idempotent**: migrations may be applied multiple times safely.

## Chain Integrity Gate

`tests/architectural/test_migration_chain_integrity.py` verifies:

1. Every migration file is reachable from the chain manifest.
2. Migration versions are monotonically increasing.
3. No gaps exist between consecutive versions.
4. The chain HEAD is valid (resolves to a real file).

If the gate fails after adding a migration, check:
- The `version` field in your `Migration` class matches the filename.
- There is no existing migration at the same version.
- The new migration is registered in the chain manifest (if required by the
  chain discovery mechanism in `__init__.py`).

## See Also

- `tests/architectural/test_migration_chain_integrity.py` — the gate
- `base.py` — `BaseMigration` ABC
- `m_0_9_1_complete_lane_migration.py` — `get_agent_dirs_for_project` helper
