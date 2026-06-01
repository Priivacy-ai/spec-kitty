"""Migration m_3_2_7_activate_builtin_mission_types: add mission_type_activations.

FR-019 — Existing projects that pre-date the charter mission-type-activation
feature (mission charter-doctrine-mission-type-configuration-01KSWJVX) have no
explicit ``mission_type_activations`` entry in their ``.kittify/config.yaml``.

After this mission, DRG traversal is activation-filtered (FR-018).  Without
this migration, upgrading a legacy project would silently make all mission types
invisible to charter-mediated resolution — breaking every existing project.

This migration writes ``mission_type_activations: [software-dev, documentation,
research, plan]`` into ``config.yaml`` for projects that lack the key, preserving
all prior functionality transparently.

Idempotency
-----------
If ``mission_type_activations`` is already present and non-empty the migration
is a no-op: it never removes or replaces existing configuration.
"""

from __future__ import annotations

from pathlib import Path

from ruamel.yaml import YAML

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult

#: IDs of the four built-in mission types shipped with spec-kitty.
#: Must match the IDs in ``src/charter/pack_context._BUILTIN_MISSION_TYPE_IDS``
#: and the keys used by ``PackContext.from_config()`` (key: ``mission_type_activations``).
_BUILTIN_MISSION_TYPES: list[str] = ["software-dev", "documentation", "research", "plan"]


@MigrationRegistry.register
class ActivateBuiltinMissionTypesMigration(BaseMigration):
    """Add mission_type_activations to .kittify/config.yaml for legacy projects.

    Projects without the ``mission_type_activations`` key are treated as
    implicitly activating all four built-ins (backward-compat behaviour in
    ``PackContext.from_config()``).  This migration makes that implicit
    activation explicit so the config always reflects the effective state.
    """

    migration_id = "3.2.7_activate_builtin_mission_types"
    description = (
        "Add mission_type_activations: [software-dev, documentation, research, plan] "
        "to .kittify/config.yaml for projects that do not yet have the key (FR-019)."
    )
    target_version = "3.2.7"

    def detect(self, project_path: Path) -> bool:
        """Return True when config.yaml exists but lacks mission_type_activations.

        Args:
            project_path: Root of the consumer project (.kittify parent).

        Returns:
            True if the migration needs to run.
        """
        config_file = project_path / ".kittify" / "config.yaml"
        if not config_file.exists():
            return False
        yaml = YAML(typ="safe")
        try:
            data = yaml.load(config_file) or {}
        except Exception:
            return False
        if not isinstance(data, dict):
            return False
        existing = data.get("mission_type_activations")
        # Needs migration when key is absent or empty
        return not (isinstance(existing, list) and existing)

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """Check that config.yaml is readable if it exists.

        Args:
            project_path: Root of the consumer project.

        Returns:
            (True, "") if safe to proceed; (False, reason) otherwise.
        """
        config_file = project_path / ".kittify" / "config.yaml"
        if not config_file.exists():
            return True, ""
        if not config_file.is_file():
            return False, "config path exists but is not a file"
        try:
            config_file.read_text(encoding="utf-8")
            return True, ""
        except OSError as exc:
            return False, f"config file not readable: {exc}"

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Write mission_type_activations into config.yaml when absent.

        Uses ruamel.yaml round-trip parser to preserve existing YAML
        formatting and comments.  Only adds the new key; never removes or
        overwrites existing configuration.

        Args:
            project_path: Root of the consumer project (.kittify parent).
            dry_run:      When True, report what would change but write nothing.

        Returns:
            MigrationResult describing the outcome.
        """
        config_file = project_path / ".kittify" / "config.yaml"

        if not config_file.exists():
            return MigrationResult(
                success=True,
                changes_made=["No .kittify/config.yaml found; nothing to migrate"],
            )

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

        # Idempotency check — skip if already present and non-empty
        existing = data.get("mission_type_activations")
        if isinstance(existing, list) and existing:
            return MigrationResult(
                success=True,
                changes_made=["mission_type_activations already present; no changes needed"],
            )

        change_description = (
            f"Added mission_type_activations: {_BUILTIN_MISSION_TYPES}"
        )

        if dry_run:
            return MigrationResult(
                success=True,
                changes_made=[f"Would add: {change_description}"],
            )

        data["mission_type_activations"] = _BUILTIN_MISSION_TYPES

        try:
            with config_file.open("w", encoding="utf-8") as fh:
                yaml.dump(data, fh)
        except OSError as exc:
            return MigrationResult(
                success=False, errors=[f"Failed writing config.yaml: {exc}"]
            )

        return MigrationResult(success=True, changes_made=[change_description])
