"""Shared runtime-detection helpers used by multiple migrations."""

from __future__ import annotations

from pathlib import Path

from packaging.version import InvalidVersion, Version

from specify_cli.runtime.home import get_kittify_home

from .metadata import ProjectMetadata


def global_runtime_configured() -> bool:
    """Return True when ``~/.kittify`` has been bootstrapped."""
    try:
        home = get_kittify_home()
    except RuntimeError:
        return False
    return (home / "cache" / "version.lock").is_file()


def uses_centralized_runtime(project_path: Path) -> bool:
    """Return True when project state indicates 2.x global runtime usage."""
    if not global_runtime_configured():
        return False

    metadata = ProjectMetadata.load(project_path / ".kittify")
    if metadata is not None:
        try:
            return Version(metadata.version) >= Version("2.0.0")
        except InvalidVersion:
            return False

    return (project_path / "kitty-specs").exists()
