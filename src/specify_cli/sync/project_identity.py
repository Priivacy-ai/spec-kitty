"""Project identity management for spec-kitty sync.

Provides:
- ProjectIdentity dataclass with persistence
- Generation of project UUID, slug, and node ID
- Atomic writes to config.yaml
- Graceful backfill for existing projects
- Read-only fallback with in-memory identity
"""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from rich.console import Console
from ruamel.yaml import YAML

from specify_cli.sync.clock import generate_node_id as generate_machine_node_id

logger = logging.getLogger(__name__)


@dataclass
class ProjectIdentity:
    """Unique identity for a spec-kitty project.

    Fields:
        project_uuid: UUID4 identifier, unique per project
        project_slug: Human-readable slug derived from repo name
        node_id: Stable machine identifier (12-char hex)
    """

    project_uuid: UUID | None = None
    project_slug: str | None = None
    node_id: str | None = None

    @property
    def is_complete(self) -> bool:
        """Check if all identity fields are populated."""
        return all([self.project_uuid, self.project_slug, self.node_id])

    def with_defaults(self, repo_root: Path) -> ProjectIdentity:
        """Return new instance with missing fields filled with generated values.

        Args:
            repo_root: Path to repository root for slug derivation

        Returns:
            New ProjectIdentity with all fields populated
        """
        return ProjectIdentity(
            project_uuid=self.project_uuid or generate_project_uuid(),
            project_slug=self.project_slug or derive_project_slug(repo_root),
            node_id=self.node_id or generate_node_id(),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for YAML persistence.

        Returns:
            Dictionary with 'uuid', 'slug', and 'node_id' keys
        """
        return {
            "uuid": str(self.project_uuid) if self.project_uuid else None,
            "slug": self.project_slug,
            "node_id": self.node_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProjectIdentity:
        """Deserialize from dictionary.

        Args:
            data: Dictionary with optional 'uuid', 'slug', 'node_id' keys

        Returns:
            ProjectIdentity instance
        """
        uuid_str = data.get("uuid")
        return cls(
            project_uuid=UUID(uuid_str) if uuid_str else None,
            project_slug=data.get("slug"),
            node_id=data.get("node_id"),
        )


def generate_project_uuid() -> UUID:
    """Generate a new UUID4 for project identification.

    Returns:
        Randomly generated UUID4
    """
    return uuid4()


def derive_project_slug(repo_root: Path) -> str:
    """Derive project slug from git remote or directory name.

    Attempts to extract repo name from git remote origin URL.
    Falls back to directory name if no remote is configured.

    Args:
        repo_root: Path to repository root

    Returns:
        Kebab-case project slug
    """
    # Try git remote origin first
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )
        url = result.stdout.strip()

        # Handle both SSH and HTTPS URLs
        # SSH: git@github.com:user/repo.git
        # HTTPS: https://github.com/user/repo.git
        if url.endswith(".git"):
            url = url[:-4]

        # Extract repo name from URL
        # For SSH URLs like git@github.com:user/repo, split on : first
        if ":" in url and "@" in url:
            # SSH format: git@host:user/repo
            url = url.split(":")[-1]

        return _normalize_slug(url.split("/")[-1])

    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    # Fallback to directory name
    return _normalize_slug(repo_root.name)


def _normalize_slug(name: str) -> str:
    """Normalize a name to kebab-case slug.

    Args:
        name: Raw name to normalize

    Returns:
        Lowercase kebab-case slug
    """
    return name.lower().replace("_", "-").replace(" ", "-")


def generate_node_id() -> str:
    """Generate stable machine identifier.

    Reuses LamportClock's stable machine ID for consistency.

    Returns:
        12-character hex string
    """
    return generate_machine_node_id()


def is_writable(path: Path) -> bool:
    """Check if path (or its parent directory) is writable.

    Args:
        path: Path to check

    Returns:
        True if the path can be written to
    """
    if path.exists():
        return os.access(path, os.W_OK)
    # Check parent directory if file doesn't exist yet
    parent = path.parent
    if parent.exists():
        return os.access(parent, os.W_OK)
    return False


def atomic_write_config(config_path: Path, identity: ProjectIdentity) -> None:
    """Atomically write identity to config.yaml (temp file + rename).

    Uses the POSIX-compliant os.replace() for atomic rename.
    Temp file is created in the same directory to ensure same filesystem.

    Args:
        config_path: Path to config.yaml
        identity: ProjectIdentity to persist

    Raises:
        OSError: If write fails
    """
    yaml = YAML()
    yaml.preserve_quotes = True

    # Ensure parent directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing config or create new
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            config = yaml.load(f) or {}
    else:
        config = {}

    # Update project section
    config["project"] = identity.to_dict()

    # Write to temp file in same directory (ensures same filesystem)
    fd, tmp_path = tempfile.mkstemp(
        dir=config_path.parent,
        prefix=".config.yaml.",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            yaml.dump(config, f)
        os.replace(tmp_path, config_path)  # Atomic on POSIX
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def load_identity(config_path: Path) -> ProjectIdentity:
    """Load identity from config.yaml, returning empty if not found.

    Handles malformed config gracefully with warning.

    Args:
        config_path: Path to config.yaml

    Returns:
        ProjectIdentity (may have None fields if not found)
    """
    if not config_path.exists():
        return ProjectIdentity()

    yaml = YAML()
    try:
        with open(config_path, encoding="utf-8") as f:
            config = yaml.load(f) or {}
    except Exception as e:
        logger.warning(f"Invalid config.yaml; regenerating identity: {e}")
        return ProjectIdentity()

    project = config.get("project", {})
    if not isinstance(project, dict):
        logger.warning("Invalid 'project' section in config.yaml; regenerating identity")
        return ProjectIdentity()

    return ProjectIdentity.from_dict(project)


def ensure_identity(repo_root: Path) -> ProjectIdentity:
    """Load or generate project identity with atomic persistence.

    If identity is incomplete:
    1. Generate missing fields
    2. Attempt to persist if config is writable
    3. Warn if falling back to in-memory identity

    Args:
        repo_root: Path to repository root

    Returns:
        Complete ProjectIdentity (all fields populated)
    """
    config_path = repo_root / ".kittify" / "config.yaml"

    identity = load_identity(config_path)
    if identity.is_complete:
        return identity

    # Generate missing fields
    identity = identity.with_defaults(repo_root)

    # Persist if writable
    if is_writable(config_path):
        try:
            atomic_write_config(config_path, identity)
            logger.debug(f"Persisted project identity to {config_path}")
        except OSError as e:
            logger.warning(f"Failed to persist identity: {e}")
            _warn_in_memory()
    else:
        _warn_in_memory()

    return identity


def _warn_in_memory() -> None:
    """Log warning about using in-memory identity."""
    console = Console(stderr=True)
    console.print(
        "[yellow]Warning: Config not writable; using in-memory identity[/yellow]"
    )
