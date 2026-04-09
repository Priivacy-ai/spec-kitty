"""Core dataclasses for bound identity and context tokens.

MissionContext is the canonical identity object that binds a CLI invocation
to a specific project, mission, and work package. It is frozen (immutable)
and serializable to JSON for persistence.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from specify_cli.mission_metadata import mission_identity_fields


@dataclass(frozen=True)
class MissionContext:
    """Immutable bound identity for a CLI invocation.

    Every field is required. The token is an opaque ULID-based identifier
    (``ctx-`` prefix + ULID). All mutable state lives elsewhere; this object
    is a pure identity snapshot.
    """

    token: str  # Opaque ULID: "ctx-01HV..."
    project_uuid: str  # From .kittify/config.yaml project.uuid
    mission_id: str  # From meta.json (currently mission_slug)
    work_package_id: str  # From WP frontmatter (immutable internal ID)
    wp_code: str  # Display alias: "WP03"
    mission_slug: str  # Display alias: "057-canonical-context..."
    target_branch: str  # From meta.json
    authoritative_repo: str  # Absolute path to repo root
    authoritative_ref: str | None  # Git ref for code_change WPs; None for planning_artifact
    owned_files: tuple[str, ...]  # Glob patterns from WP frontmatter
    execution_mode: str  # "code_change" or "planning_artifact"
    dependency_mode: str  # "independent" or "chained"
    created_at: str  # ISO 8601 UTC
    created_by: str  # Agent name
    mission_number: str | None = None  # Canonical mission numeric prefix
    mission_type: str | None = None  # Canonical mission type / blueprint key

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "token": self.token,
            "project_uuid": self.project_uuid,
            "mission_id": self.mission_id,
            "work_package_id": self.work_package_id,
            "wp_code": self.wp_code,
            **mission_identity_fields(
                self.mission_slug,
                self.mission_number,
                self.mission_type,
            ),
            "target_branch": self.target_branch,
            "authoritative_repo": self.authoritative_repo,
            "authoritative_ref": self.authoritative_ref,
            "owned_files": list(self.owned_files),
            "execution_mode": self.execution_mode,
            "dependency_mode": self.dependency_mode,
            "created_at": self.created_at,
            "created_by": self.created_by,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MissionContext:
        """Deserialize from a JSON-compatible dictionary."""
        identity = mission_identity_fields(
            data["mission_slug"],
            data.get("mission_number"),
            data.get("mission_type"),
        )
        return cls(
            token=data["token"],
            project_uuid=data["project_uuid"],
            mission_id=data["mission_id"],
            work_package_id=data["work_package_id"],
            wp_code=data["wp_code"],
            mission_slug=identity["mission_slug"],
            mission_number=identity["mission_number"],
            mission_type=identity["mission_type"],
            target_branch=data["target_branch"],
            authoritative_repo=data["authoritative_repo"],
            authoritative_ref=data.get("authoritative_ref"),
            owned_files=tuple(data["owned_files"]),
            execution_mode=data["execution_mode"],
            dependency_mode=data["dependency_mode"],
            created_at=data["created_at"],
            created_by=data["created_by"],
        )


@dataclass(frozen=True)
class ContextToken:
    """Lightweight reference to a persisted MissionContext.

    Used by callers who only need the token string and the path to the
    persisted JSON file, without loading the full context.
    """

    token: str
    context_path: Path  # Absolute path to persisted JSON
