"""Classify shim registry entries and produce a health report."""
from __future__ import annotations

import dataclasses
import enum
import tomllib
from pathlib import Path

from packaging.version import Version

from specify_cli.compat.registry import ShimEntry, load_registry


class ShimStatus(enum.Enum):
    PENDING = "pending"
    OVERDUE = "overdue"
    GRANDFATHERED = "grandfathered"
    REMOVED = "removed"


@dataclasses.dataclass(frozen=True)
class ShimStatusEntry:
    entry: ShimEntry
    status: ShimStatus
    shim_exists: bool


@dataclasses.dataclass(frozen=True)
class ShimRegistryReport:
    entries: list[ShimStatusEntry]
    project_version: str
    registry_path: Path

    @property
    def has_overdue(self) -> bool:
        return any(e.status == ShimStatus.OVERDUE for e in self.entries)

    @property
    def recommended_exit_code(self) -> int:
        return 1 if self.has_overdue else 0


def _shim_exists(repo_root: Path, legacy_path: str) -> bool:
    parts = legacy_path.split(".")
    base = repo_root / "src" / Path(*parts)
    return (base.with_suffix(".py")).exists() or (base / "__init__.py").exists()


def _classify(entry: ShimEntry, current: Version, repo_root: Path) -> ShimStatus:
    if entry.grandfathered:
        return ShimStatus.GRANDFATHERED
    exists = _shim_exists(repo_root, entry.legacy_path)
    if not exists:
        return ShimStatus.REMOVED
    if current >= Version(entry.removal_target_release):
        return ShimStatus.OVERDUE
    return ShimStatus.PENDING


def check_shim_registry(repo_root: Path) -> ShimRegistryReport:
    pyproject = repo_root / "pyproject.toml"
    if not pyproject.exists():
        raise FileNotFoundError(f"pyproject.toml not found at {pyproject}")
    with pyproject.open("rb") as fp:
        toml_data = tomllib.load(fp)
    project_version: str = toml_data["project"]["version"]

    registry_path = repo_root / "architecture" / "2.x" / "shim-registry.yaml"
    entries = load_registry(repo_root)
    current = Version(project_version)

    status_entries = [
        ShimStatusEntry(
            entry=e,
            status=_classify(e, current, repo_root),
            shim_exists=_shim_exists(repo_root, e.legacy_path),
        )
        for e in entries
    ]

    return ShimRegistryReport(
        entries=status_entries,
        project_version=project_version,
        registry_path=registry_path,
    )
