"""Migration 3.2.1: Remove agents.selection block from .kittify/config.yaml.

The preferred_implementer and preferred_reviewer fields were stored in
agents.selection but the methods that would have acted on them were never
called. This migration removes the orphaned selection block from existing
config.yaml files.

Handles both 'agents' and 'tools' root key variants (migration 2.0.1
renamed 'agents' to 'tools' in some projects).

Idempotency
-----------
A config without a selection block returns detect() == False and is
skipped without changes.
"""

from __future__ import annotations

from pathlib import Path

from ruamel.yaml import YAML

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult


@MigrationRegistry.register
class StripSelectionConfigMigration(BaseMigration):
    """Remove agents.selection.preferred_implementer/reviewer from config.yaml."""

    migration_id = "3.2.1_strip_selection_config"
    description = "Remove selection block from .kittify/config.yaml"
    target_version = "3.2.1"

    def detect(self, project_path: Path) -> bool:
        """Return True if any root key has a 'selection' sub-key in config.yaml.

        Checks both 'agents' and 'tools' root keys for a nested 'selection' block.

        Args:
            project_path: Root of the consumer project.

        Returns:
            True if a selection block is found that needs to be removed.
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
        for root_key in ("agents", "tools"):
            section = data.get(root_key)
            if isinstance(section, dict) and "selection" in section:
                return True
        return False

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
        """Remove the 'selection' sub-key from 'agents' and/or 'tools' in config.yaml.

        Preserves all other config keys and YAML formatting (comments, ordering)
        using ruamel.yaml's round-trip parser.

        Idempotent: if no selection block exists, returns success with a note.

        Args:
            project_path: Root of the consumer project.
            dry_run:      When True, report what would change but write nothing.

        Returns:
            MigrationResult with changes_made, errors, and warnings.
        """
        config_file = project_path / ".kittify" / "config.yaml"
        if not config_file.exists():
            return MigrationResult(success=True, changes_made=["No config.yaml found"])

        yaml = YAML()
        yaml.preserve_quotes = True

        try:
            data = yaml.load(config_file) or {}
        except Exception as exc:
            return MigrationResult(success=False, errors=[f"Invalid YAML: {exc}"])

        if not isinstance(data, dict):
            return MigrationResult(success=False, errors=["config.yaml root must be a mapping"])

        changes: list[str] = []
        for root_key in ("agents", "tools"):
            section = data.get(root_key)
            if isinstance(section, dict) and "selection" in section:
                if dry_run:
                    changes.append(f"Would remove: {root_key}.selection")
                else:
                    del section["selection"]
                    changes.append(f"Removed: {root_key}.selection")

        if not changes:
            return MigrationResult(success=True, changes_made=["No selection block found"])

        if not dry_run:
            try:
                with config_file.open("w", encoding="utf-8") as fh:
                    yaml.dump(data, fh)
            except OSError as exc:
                return MigrationResult(success=False, errors=[f"Failed writing config.yaml: {exc}"])

        return MigrationResult(success=True, changes_made=changes)
