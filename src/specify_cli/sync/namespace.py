"""Namespace types for artifact body sync.

Provides:
- NamespaceRef: 5-field canonical namespace tuple for body upload requests
- SupportedInlineFormat: Enum of file extensions eligible for inline upload
- UploadStatus / UploadOutcome: Per-artifact upload result classification
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from specify_cli.identity.project import ProjectIdentity

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class NamespaceRef:
    """Canonical 5-field namespace tuple for body upload requests.

    Every body upload must include these fields to identify the artifact's
    position within the project/mission/branch hierarchy.
    """

    project_uuid: str
    mission_slug: str
    target_branch: str
    mission_type: str
    manifest_version: str

    def __post_init__(self) -> None:
        for field_name in (
            "project_uuid",
            "mission_slug",
            "target_branch",
            "mission_type",
            "manifest_version",
        ):
            value = getattr(self, field_name)
            if not value or not value.strip():
                raise ValueError(f"{field_name} must not be empty or whitespace-only")

    def to_dict(self) -> dict[str, str]:
        """Return all 5 fields as a flat dict for request body construction."""
        return {
            "project_uuid": self.project_uuid,
            "mission_slug": self.mission_slug,
            "target_branch": self.target_branch,
            "mission_type": self.mission_type,
            "manifest_version": self.manifest_version,
        }

    def dedupe_key(self, artifact_path: str, content_hash: str) -> str:
        """Return deterministic 7-field string for body queue deduplication."""
        return (
            f"{self.project_uuid}|{self.mission_slug}|{self.target_branch}"
            f"|{self.mission_type}|{self.manifest_version}"
            f"|{artifact_path}|{content_hash}"
        )

    @classmethod
    def from_context(
        cls,
        identity: ProjectIdentity,
        mission_slug: str,
        target_branch: str,
        mission_type: str,
        manifest_version: str,
    ) -> NamespaceRef:
        """Construct a NamespaceRef from ProjectIdentity and mission metadata."""
        if identity.project_uuid is None:
            raise ValueError(
                "ProjectIdentity.project_uuid is required for body sync"
            )
        return cls(
            project_uuid=str(identity.project_uuid),
            mission_slug=mission_slug,
            target_branch=target_branch,
            mission_type=mission_type,
            manifest_version=manifest_version,
        )


def resolve_manifest_version(mission_type: str) -> str:
    """Resolve manifest version for a mission type.

    Returns the manifest_version from the registry if available,
    otherwise defaults to "1".
    """
    from specify_cli.dossier.manifest import ManifestRegistry

    manifest = ManifestRegistry.load_manifest(mission_type)
    if manifest is not None:
        return manifest.manifest_version
    return "1"


class SupportedInlineFormat(str, Enum):
    """File extensions eligible for inline body upload in v1."""

    MARKDOWN = ".md"
    JSON = ".json"
    YAML = ".yaml"
    YML = ".yml"
    CSV = ".csv"


SUPPORTED_EXTENSIONS: frozenset[str] = frozenset(
    f.value for f in SupportedInlineFormat
)


def is_supported_format(path: str | Path) -> bool:
    """Check if file extension is supported for inline body upload."""
    return Path(path).suffix.lower() in SUPPORTED_EXTENSIONS


class UploadStatus(str, Enum):
    """Classification of an upload attempt result."""

    UPLOADED = "uploaded"
    ALREADY_EXISTS = "already_exists"
    QUEUED = "queued"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass(frozen=True)
class UploadOutcome:
    """Per-artifact upload result."""

    artifact_path: str
    status: UploadStatus
    reason: str
    content_hash: str | None = None
    retryable: bool = False

    def __str__(self) -> str:
        return f"{self.artifact_path}: {self.status.value} ({self.reason})"
