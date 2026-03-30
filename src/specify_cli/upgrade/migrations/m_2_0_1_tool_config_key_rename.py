"""Migration: rename .kittify/config.yaml key `agents` -> `tools`."""

from __future__ import annotations

from pathlib import Path

from ruamel.yaml import YAML

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult


@MigrationRegistry.register
class ToolConfigKeyRenameMigration(BaseMigration):
    """Rename legacy tool config key from `agents` to canonical `tools`."""

    migration_id = "2.0.1_tool_config_key_rename"
    description = "Rename .kittify/config.yaml key `agents` to `tools`"
    target_version = "2.0.1"

    def detect(self, project_path: Path) -> bool:
        config_file = project_path / ".kittify" / "config.yaml"
        if not config_file.exists():
            return False

        yaml = YAML(typ="safe")
        try:
            data = yaml.load(config_file) or {}
        except Exception:
            return False

        return isinstance(data, dict) and "agents" in data and "tools" not in data

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
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
        config_file = project_path / ".kittify" / "config.yaml"
        if not config_file.exists():
            return MigrationResult(success=True, changes_made=["No config.yaml found"])

        yaml = YAML()
        yaml.preserve_quotes = True

        try:
            data = yaml.load(config_file) or {}
        except Exception as exc:
            return MigrationResult(success=False, errors=[f"Invalid YAML in config.yaml: {exc}"])

        if not isinstance(data, dict):
            return MigrationResult(success=False, errors=["config.yaml root must be a mapping"])

        if "tools" in data:
            return MigrationResult(success=True, changes_made=["Config already uses canonical `tools` key"])

        if "agents" not in data:
            return MigrationResult(success=True, changes_made=["No legacy `agents` key found"])

        if dry_run:
            return MigrationResult(
                success=True,
                changes_made=["Would rename .kittify/config.yaml key `agents` -> `tools`"],
            )

        data["tools"] = data.pop("agents")

        try:
            with config_file.open("w", encoding="utf-8") as fh:
                yaml.dump(data, fh)
        except OSError as exc:
            return MigrationResult(success=False, errors=[f"Failed writing config.yaml: {exc}"])

        return MigrationResult(
            success=True,
            changes_made=["Renamed .kittify/config.yaml key `agents` -> `tools`"],
        )
