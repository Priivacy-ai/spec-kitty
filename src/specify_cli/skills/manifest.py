"""Skills manifest CRUD — persistence layer for agent-surfaces tracking.

The skills manifest records what Spec Kitty installed in a project so that
upgrades, verification, and drift detection can work reliably.

Manifest location: ``.kittify/agent-surfaces/skills-manifest.yaml``
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

logger = logging.getLogger(__name__)

MANIFEST_PATH: str = ".kittify/agent-surfaces/skills-manifest.yaml"
"""Relative path from project root to the skills manifest file."""


# ---------------------------------------------------------------------------
# Data classes  (T013)
# ---------------------------------------------------------------------------


@dataclass
class ManagedFile:
    """One entry in the skills manifest tracking a Spec-Kitty-managed file.

    Attributes:
        path: File path relative to project root.
        sha256: Content hash (hex digest) for drift detection.
        file_type: Category of managed file (``"wrapper"`` or
            ``"skill_root_marker"``).
    """

    path: str
    sha256: str
    file_type: str


@dataclass
class SkillsManifest:
    """Record of what Spec Kitty installed in a project.

    Serialized to ``.kittify/agent-surfaces/skills-manifest.yaml``.

    Attributes:
        spec_kitty_version: CLI version that wrote this manifest.
        created_at: ISO timestamp of first creation.
        updated_at: ISO timestamp of last update.
        skills_mode: Distribution mode used during install.
        selected_agents: Agent keys selected during init.
        installed_skill_roots: Skill root directories created.
        managed_files: All managed file entries.
    """

    spec_kitty_version: str
    created_at: str
    updated_at: str
    skills_mode: str
    selected_agents: list[str] = field(default_factory=list)
    installed_skill_roots: list[str] = field(default_factory=list)
    managed_files: list[ManagedFile] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------


def _manifest_to_dict(manifest: SkillsManifest) -> dict[str, Any]:
    """Convert a *SkillsManifest* to a plain dict suitable for YAML output."""
    return {
        "spec_kitty_version": manifest.spec_kitty_version,
        "created_at": manifest.created_at,
        "updated_at": manifest.updated_at,
        "skills_mode": manifest.skills_mode,
        "selected_agents": list(manifest.selected_agents),
        "installed_skill_roots": list(manifest.installed_skill_roots),
        "managed_files": [
            {
                "path": mf.path,
                "sha256": mf.sha256,
                "file_type": mf.file_type,
            }
            for mf in manifest.managed_files
        ],
    }


def _dict_to_manifest(data: dict[str, Any]) -> SkillsManifest | None:
    """Reconstruct a *SkillsManifest* from a parsed YAML dict.

    Returns ``None`` when required fields are missing or have wrong types.
    """
    required_fields = (
        "spec_kitty_version",
        "created_at",
        "updated_at",
        "skills_mode",
    )
    for key in required_fields:
        if key not in data:
            logger.warning("Manifest missing required field: %s", key)
            return None

    raw_files = data.get("managed_files", [])
    if not isinstance(raw_files, list):
        logger.warning("managed_files is not a list")
        return None

    managed_files: list[ManagedFile] = []
    for entry in raw_files:
        if not isinstance(entry, dict):
            logger.warning("managed_files entry is not a dict")
            return None
        try:
            managed_files.append(
                ManagedFile(
                    path=str(entry["path"]),
                    sha256=str(entry["sha256"]),
                    file_type=str(entry["file_type"]),
                )
            )
        except KeyError as exc:
            logger.warning("ManagedFile entry missing key: %s", exc)
            return None

    selected_agents = data.get("selected_agents", [])
    if not isinstance(selected_agents, list):
        logger.warning("selected_agents is not a list")
        return None

    installed_skill_roots = data.get("installed_skill_roots", [])
    if not isinstance(installed_skill_roots, list):
        logger.warning("installed_skill_roots is not a list")
        return None

    return SkillsManifest(
        spec_kitty_version=str(data["spec_kitty_version"]),
        created_at=str(data["created_at"]),
        updated_at=str(data["updated_at"]),
        skills_mode=str(data["skills_mode"]),
        selected_agents=[str(a) for a in selected_agents],
        installed_skill_roots=[str(r) for r in installed_skill_roots],
        managed_files=managed_files,
    )


# ---------------------------------------------------------------------------
# Public API  (T014 / T015 / T016)
# ---------------------------------------------------------------------------


def write_manifest(project_root: Path, manifest: SkillsManifest) -> None:
    """Write *manifest* to ``.kittify/agent-surfaces/skills-manifest.yaml``.

    Creates the parent directory tree when it does not exist.
    """
    manifest_path = project_root / MANIFEST_PATH
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    yaml = YAML()
    yaml.default_flow_style = False

    buf = StringIO()
    yaml.dump(_manifest_to_dict(manifest), buf)

    manifest_path.write_text(buf.getvalue(), encoding="utf-8")
    logger.info("Wrote skills manifest to %s", manifest_path)


def load_manifest(project_root: Path) -> SkillsManifest | None:
    """Load the skills manifest from YAML.

    Returns ``None`` when the file is missing, empty, corrupt, or when
    required fields are absent.  **Never raises.**
    """
    manifest_path = project_root / MANIFEST_PATH

    if not manifest_path.exists():
        logger.debug("Manifest file not found: %s", manifest_path)
        return None

    try:
        raw_text = manifest_path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning("Cannot read manifest: %s", exc)
        return None

    if not raw_text.strip():
        logger.debug("Manifest file is empty: %s", manifest_path)
        return None

    yaml = YAML()
    try:
        data = yaml.load(raw_text)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Invalid YAML in manifest: %s", exc)
        return None

    if not isinstance(data, dict):
        logger.warning("Manifest root is not a mapping")
        return None

    return _dict_to_manifest(data)


def compute_file_hash(file_path: Path) -> str:
    """Return the SHA-256 hex digest of *file_path* contents.

    Reads in binary mode for cross-platform consistency.
    """
    h = hashlib.sha256()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()
