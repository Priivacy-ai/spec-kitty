"""Migration m_3_2_8_default_charter_pack: write per-kind activation keys.

FR-002 / FR-003 — Existing projects that pre-date the per-kind charter
activation keys (mission charter-pack-activation-layer-01KSYE4V) have no
explicit per-kind entries in their ``.kittify/config.yaml``.

After this mission, the DRG traversal is filtered by the eight per-kind
activation sets (``activated_directives``, ``activated_tactics``,
``activated_styleguides``, ``activated_toolguides``, ``activated_paradigms``,
``activated_procedures``, ``activated_agent_profiles``,
``activated_mission_step_contracts``) as well as ``activated_kinds`` and
``mission_type_activations``.  Without this migration, upgrading a legacy
project would silently expose every doctrine artifact indiscriminately.

This migration writes the default activation values from
``src/charter/packs/default.yaml`` into ``config.yaml`` for projects that
lack any of the above keys.  Only absent keys are written; any key that is
already present (even with an empty list) is left untouched.

Idempotency
-----------
Each of the ten activation keys is written only when absent.  Running the
migration twice is safe: a second run finds all keys present and returns
``success=True`` with zero changes.

Backup
------
If ``.kittify/charter/charter.md`` exists at the time of the migration, it is
backed up to ``.kittify/charter/backups/charter-<ISO-timestamp>.md`` before
any ``config.yaml`` write (NFR-002 / C-008).

Version guard
-------------
``target_version = "3.2.8"`` means this migration NEVER fires against rc
versions such as ``3.2.0rc30`` through the normal upgrade pipeline.  All
tests MUST call ``detect()`` and ``apply()`` directly so the version check
does not interfere.
"""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from rich.console import Console
from ruamel.yaml import YAML

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult

#: The eight per-kind activation keys added by the charter-pack-activation
#: mission.  Mirrors the keys expected by ``CharterPackManager.YAML_KEY_MAP``
#: (excluding ``mission_type_activations`` which uses a different pattern).
_PER_KIND_KEYS: list[str] = [
    "activated_directives",
    "activated_tactics",
    "activated_styleguides",
    "activated_toolguides",
    "activated_paradigms",
    "activated_procedures",
    "activated_agent_profiles",
    "activated_mission_step_contracts",
]

#: Absolute path to the default charter pack shipped with spec-kitty.
#: Resolves to ``src/charter/packs/default.yaml`` relative to the repo root.
#: Four ``.parent`` hops: migrations/ -> upgrade/ -> specify_cli/ -> src/
_DEFAULT_YAML_PATH: Path = (
    Path(__file__).parent.parent.parent.parent / "charter" / "packs" / "default.yaml"
)


@MigrationRegistry.register
class DefaultCharterPackMigration(BaseMigration):
    """Write per-kind activation keys from default.yaml into config.yaml.

    Projects without the per-kind activation keys are silently unfiltered
    (all doctrine artifacts appear).  This migration makes the effective
    default activation explicit so the config always reflects what the
    DRG filter will use.
    """

    migration_id = "3.2.8_default_charter_pack"
    description = (
        "Write per-kind activation keys from default.yaml into "
        ".kittify/config.yaml for projects that lack them (FR-002, FR-003)."
    )
    target_version = "3.2.8"

    def detect(self, project_path: Path) -> bool:
        """Return True when any per-kind activation key is absent from config.yaml.

        Args:
            project_path: Root of the consumer project (.kittify parent).

        Returns:
            True if at least one key from the activation key set is absent.
        """
        kittify_dir = project_path / ".kittify"
        if not kittify_dir.exists():
            return False

        config_file = kittify_dir / "config.yaml"
        if not config_file.exists():
            return False

        yaml = YAML(typ="safe")
        try:
            data = yaml.load(config_file) or {}
        except Exception:
            return False

        if not isinstance(data, dict):
            return False

        all_keys = _PER_KIND_KEYS + ["activated_kinds", "mission_type_activations"]
        return any(key not in data for key in all_keys)

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """Check that config.yaml is present and readable.

        Args:
            project_path: Root of the consumer project.

        Returns:
            (True, "") if safe to proceed; (False, reason) otherwise.
        """
        if self.detect(project_path):
            return True, ""
        return False, "no migration needed"

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Write missing per-kind activation keys into config.yaml.

        Uses ruamel.yaml round-trip mode to preserve existing YAML formatting
        and comments.  Backs up any existing charter.md before writing.

        Args:
            project_path: Root of the consumer project (.kittify parent).
            dry_run:      When True, report what would change but write nothing.

        Returns:
            MigrationResult describing the outcome.
        """
        # Guard — default.yaml missing (broken install)
        if not _DEFAULT_YAML_PATH.exists():
            return MigrationResult(
                success=False,
                errors=[f"default.yaml not found at {_DEFAULT_YAML_PATH}"],
            )

        config_file = project_path / ".kittify" / "config.yaml"
        if not config_file.exists():
            return MigrationResult(
                success=True,
                changes_made=["No .kittify/config.yaml found; nothing to migrate"],
            )

        # Backup charter.md before any config write (NFR-002, C-008)
        charter_md_path = project_path / ".kittify" / "charter" / "charter.md"
        if charter_md_path.exists() and not dry_run:
            backup_dir = project_path / ".kittify" / "charter" / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
            backup_path = backup_dir / f"charter-{timestamp}.md"
            shutil.copy2(charter_md_path, backup_path)
            console = Console()
            console.print(
                f"[yellow]Existing charter backed up to {backup_path}. "
                "Review after upgrade.[/yellow]"
            )

        # Load config with round-trip parser to preserve formatting
        yaml = YAML()
        yaml.preserve_quotes = True
        try:
            data = yaml.load(config_file) or {}
        except Exception as exc:
            return MigrationResult(success=False, errors=[f"Invalid YAML: {exc}"])

        if not isinstance(data, dict):
            return MigrationResult(
                success=False, errors=["config.yaml root must be a mapping"]
            )

        # Load default.yaml with safe loader (values only)
        safe_yaml = YAML(typ="safe")
        defaults = safe_yaml.load(_DEFAULT_YAML_PATH) or {}

        # Incremental write: only write absent keys
        all_keys = _PER_KIND_KEYS + ["activated_kinds", "mission_type_activations"]
        keys_written: list[str] = []
        for key in all_keys:
            if key not in data:
                data[key] = defaults.get(key, [])
                keys_written.append(key)

        if not keys_written:
            return MigrationResult(
                success=True,
                changes_made=["All activation keys already present; no changes needed"],
            )

        if dry_run:
            return MigrationResult(
                success=True,
                changes_made=["dry-run: would write missing keys"],
            )

        try:
            with config_file.open("w", encoding="utf-8") as fh:
                yaml.dump(data, fh)
        except OSError as exc:
            return MigrationResult(
                success=False, errors=[f"Failed writing config.yaml: {exc}"]
            )

        return MigrationResult(success=True, changes_made=keys_written)
