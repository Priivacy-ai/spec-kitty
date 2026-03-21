"""Managed skill manifest: tracks installed skill files for drift detection."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from specify_cli.core.atomic import atomic_write

logger = logging.getLogger(__name__)

MANIFEST_FILENAME = "skills-manifest.json"


@dataclass
class ManagedFileEntry:
    """A single file installed by the skill manager."""

    skill_name: str  # e.g., "spec-kitty-setup-doctor"
    source_file: str  # Relative within skill dir, e.g., "SKILL.md"
    installed_path: str  # Relative from project root, e.g., ".claude/skills/spec-kitty-setup-doctor/SKILL.md"
    installation_class: str  # "shared-root-capable", "native-root-required", "wrapper-only"
    agent_key: str  # "claude", "codex", etc.
    content_hash: str  # "sha256:<hex>"
    installed_at: str  # ISO 8601 UTC


@dataclass
class ManagedSkillManifest:
    """Top-level manifest tracking all managed skill files."""

    version: int = 1
    created_at: str = ""
    updated_at: str = ""
    spec_kitty_version: str = ""
    entries: list[ManagedFileEntry] = field(default_factory=list)

    def add_entry(self, entry: ManagedFileEntry) -> None:
        """Add a new entry, replacing any existing entry with the same (installed_path, agent_key).

        Shared-root agents intentionally share ``installed_path`` so deduplication
        must include ``agent_key`` to avoid collapsing entries for different agents.
        """
        self.entries = [
            e
            for e in self.entries
            if not (e.installed_path == entry.installed_path and e.agent_key == entry.agent_key)
        ]
        self.entries.append(entry)

    def remove_entries_for_agent(self, agent_key: str) -> list[ManagedFileEntry]:
        """Remove and return all entries for a specific agent."""
        removed = [e for e in self.entries if e.agent_key == agent_key]
        self.entries = [e for e in self.entries if e.agent_key != agent_key]
        return removed

    def find_by_skill(self, skill_name: str) -> list[ManagedFileEntry]:
        """Find all entries for a specific skill."""
        return [e for e in self.entries if e.skill_name == skill_name]

    def find_by_installed_path(self, installed_path: str) -> ManagedFileEntry | None:
        """Find entry by installed path."""
        for e in self.entries:
            if e.installed_path == installed_path:
                return e
        return None


def save_manifest(manifest: ManagedSkillManifest, project_path: Path) -> None:
    """Persist the manifest to .kittify/skills-manifest.json."""
    manifest.updated_at = datetime.now(timezone.utc).isoformat()
    data = asdict(manifest)
    content = json.dumps(data, indent=2) + "\n"
    target = project_path / ".kittify" / MANIFEST_FILENAME
    atomic_write(target, content, mkdir=True)


def load_manifest(project_path: Path) -> ManagedSkillManifest | None:
    """Load manifest from .kittify/skills-manifest.json.

    Returns None if the file is missing or contains malformed JSON.
    """
    target = project_path / ".kittify" / MANIFEST_FILENAME
    if not target.exists():
        return None
    try:
        raw = target.read_text(encoding="utf-8")
        data = json.loads(raw)
        entries = [ManagedFileEntry(**e) for e in data.get("entries", [])]
        return ManagedSkillManifest(
            version=data.get("version", 1),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            spec_kitty_version=data.get("spec_kitty_version", ""),
            entries=entries,
        )
    except (json.JSONDecodeError, TypeError, KeyError) as exc:
        logger.warning("Failed to load skills manifest: %s", exc)
        return None


def clear_manifest(project_path: Path) -> None:
    """Delete the manifest file if it exists."""
    target = project_path / ".kittify" / MANIFEST_FILENAME
    if target.exists():
        target.unlink()


def compute_content_hash(file_path: Path) -> str:
    """Compute sha256 hash of file content."""
    content = file_path.read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    return f"sha256:{digest}"
