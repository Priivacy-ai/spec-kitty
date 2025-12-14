"""Spec Kitty upgrade system for migrating projects between versions."""

from __future__ import annotations

from .metadata import MigrationRecord, ProjectMetadata
from .detector import VersionDetector
from .registry import MigrationRegistry
from .runner import MigrationRunner, UpgradeResult

__all__ = [
    "MigrationRecord",
    "ProjectMetadata",
    "VersionDetector",
    "MigrationRegistry",
    "MigrationRunner",
    "UpgradeResult",
]
