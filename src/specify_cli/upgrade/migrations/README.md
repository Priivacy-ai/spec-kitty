# Migrations — Forward-Staged Convention

*(Q7 resolution: forward-staged migrations convention documented per FR-301.)*

The migration chain target **may lead** `pyproject.toml`'s version. The version
bump is a separate release step, run by the release maintainer after the
migration is verified at HEAD.

## Why

This keeps the migration chain testable and reviewable as a separate
artifact, decoupled from PyPI cut decisions. Pre-release verification
(`spec-kitty doctor upgrade --dry-run`) can target the next version
without forcing a release.

## Convention

- New migration files land at `m_X_Y_Z_<slug>.py` where `X.Y.Z` is the
  **target version**. The version may not yet be in `pyproject.toml`.
- The release process bumps `pyproject.toml` AND tags the release in the
  same commit; the migration is already present in the tag.
- `test_migration_chain_integrity.py` enforces ordering and contiguity of
  the chain. Forward-staged migrations are valid: the gate allows the chain
  target to be ahead of `pyproject.toml`'s current version.

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

- `spec.md FR-301` — forward-staged migrations requirement
- `plan.md Q7` — resolution of the forward-staged convention question
- `tests/architectural/test_migration_chain_integrity.py` — the gate
- `base.py` — `BaseMigration` ABC
- `m_0_9_1_complete_lane_migration.py` — `get_agent_dirs_for_project` helper
