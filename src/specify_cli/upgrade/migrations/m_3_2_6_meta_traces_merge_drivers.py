"""Migration 3.2.6: install the meta.json + traces/*.md git merge drivers.

Sibling of ``m_3_1_1_event_log_merge_driver.py``. #2709 / FR-003 / FR-004 / C-006:
the squash mission→target integration (``git merge --squash -X theirs``) must
reconcile target-newer ``meta.json`` acceptance/VCS provenance and ``traces/*.md``
sections instead of clobbering them. Custom merge drivers override ``-X theirs``
on their registered paths, so this migration seeds the ``.gitattributes`` mapping
plus the local ``merge.<driver>.*`` config for both drivers (generalized over a
registry rather than cloning the event-log migration — DIRECTIVE_044).
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult


@dataclass(frozen=True)
class _DriverSpec:
    config_key: str
    name: str
    command: str
    pattern: str

    @property
    def attributes_entry(self) -> str:
        return f"{self.pattern} merge={self.config_key}"


_DRIVERS: tuple[_DriverSpec, ...] = (
    _DriverSpec(
        config_key="spec-kitty-meta",
        name="Spec Kitty mission meta field merge",
        command="spec-kitty merge-driver-meta %O %A %B",
        pattern="kitty-specs/**/meta.json",
    ),
    _DriverSpec(
        config_key="spec-kitty-traces",
        name="Spec Kitty mission traces union merge",
        command="spec-kitty merge-driver-traces %O %A %B",
        pattern="kitty-specs/**/traces/*.md",
    ),
)


def _ensure_line(path: Path, line: str) -> bool:
    """Append ``line`` to ``path`` if it is not already present."""
    existing: list[str] = []
    if path.exists():
        existing = path.read_text(encoding="utf-8").splitlines()
        if line in existing:
            return False
    existing.append(line)
    path.write_text("\n".join(existing).rstrip() + "\n", encoding="utf-8")
    return True


def _git_config(project_path: Path, *args: str) -> str | None:
    """Run ``git config`` in the project and return stdout on success."""
    result = subprocess.run(
        ["git", "config", "--local", *args],
        cwd=project_path,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


@MigrationRegistry.register
class MetaTracesMergeDriverMigration(BaseMigration):
    """Install git merge drivers for meta.json and traces/*.md (#2709)."""

    migration_id = "3.2.6_meta_traces_merge_drivers"
    description = "Install semantic git merge drivers for meta.json and traces/*.md"
    target_version = "3.2.6"

    def _attributes_missing(self, project_path: Path) -> bool:
        attributes_path = project_path / ".gitattributes"
        if not attributes_path.exists():
            return True
        text = attributes_path.read_text(encoding="utf-8")
        return any(driver.attributes_entry not in text for driver in _DRIVERS)

    def _config_missing(self, project_path: Path) -> bool:
        if not (project_path / ".git").exists():
            return False
        for driver in _DRIVERS:
            name = _git_config(project_path, "--get", f"merge.{driver.config_key}.name")
            command = _git_config(project_path, "--get", f"merge.{driver.config_key}.driver")
            if name != driver.name or command != driver.command:
                return True
        return False

    def detect(self, project_path: Path) -> bool:
        return self._attributes_missing(project_path) or self._config_missing(project_path)

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        if not project_path.exists():
            return False, f"Project path does not exist: {project_path}"
        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        changes: list[str] = []
        warnings: list[str] = []

        if dry_run:
            if self.detect(project_path):
                changes.append("Would install meta.json + traces/*.md merge drivers and .gitattributes entries")
            return MigrationResult(success=True, changes_made=changes, warnings=warnings)

        attributes_path = project_path / ".gitattributes"
        is_git_repo = (project_path / ".git").exists()
        for driver in _DRIVERS:
            if _ensure_line(attributes_path, driver.attributes_entry):
                changes.append(f"Added .gitattributes entry: {driver.attributes_entry}")
            if not is_git_repo:
                continue
            if _git_config(project_path, "--get", f"merge.{driver.config_key}.name") != driver.name:
                subprocess.run(
                    ["git", "config", "--local", f"merge.{driver.config_key}.name", driver.name],
                    cwd=project_path,
                    check=True,
                )
                changes.append(f"Configured git merge.{driver.config_key}.name")
            if _git_config(project_path, "--get", f"merge.{driver.config_key}.driver") != driver.command:
                subprocess.run(
                    ["git", "config", "--local", f"merge.{driver.config_key}.driver", driver.command],
                    cwd=project_path,
                    check=True,
                )
                changes.append(f"Configured git merge.{driver.config_key}.driver")

        if not is_git_repo:
            warnings.append("Skipped local git merge-driver config because this project is not a git repository")

        return MigrationResult(success=True, changes_made=changes, warnings=warnings)
