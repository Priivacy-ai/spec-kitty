"""Manifest tracking for projected native agent profile files.

:class:`ProfileManifest` records every native agent profile file this tool has
written, keyed by output path, together with its SHA-256 content hash and the
source profile URN / tool / format. It mirrors the command-skills manifest
pattern: the manifest is the *state* record (what was installed) separate from
the projection *policy* (what should exist).

Stored at ``.kittify/agent_profiles_manifest.json`` (NOT
``tool-surface-profile-manifest.json``). The on-disk format is JSON with
``schema_version: 1``, sorted keys, and a stable entry ordering so it round-trips
losslessly.
"""

from __future__ import annotations

import json
from pathlib import Path

from specify_cli.skills.manifest_store import fingerprint, fingerprint_file

from ..model import NativeAgentProfile

MANIFEST_FILENAME = "agent_profiles_manifest.json"
_KITTIFY_DIR = ".kittify"
SCHEMA_VERSION = 1


def manifest_path_for(project_root: Path) -> Path:
    """Return the canonical manifest path under ``project_root``."""
    return project_root / _KITTIFY_DIR / MANIFEST_FILENAME


def hash_content(content: str) -> str:
    """Return the SHA-256 hex digest of ``content`` (UTF-8 encoded)."""
    return str(fingerprint(content.encode("utf-8")))


def hash_file(path: Path) -> str:
    """Return the SHA-256 hex digest of the file at ``path``."""
    return str(fingerprint_file(path))


class ProfileManifest:
    """Read/write tracker for projected native agent profile files."""

    def __init__(self, manifest_path: Path) -> None:
        self.manifest_path = manifest_path
        self._entries: dict[str, NativeAgentProfile] = {}

    @classmethod
    def load(cls, project_root: Path) -> ProfileManifest:
        """Load the manifest for ``project_root`` (empty when absent)."""
        manifest = cls(manifest_path_for(project_root))
        manifest._read()
        return manifest

    def _read(self) -> None:
        if not self.manifest_path.exists():
            return
        data = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        for raw in data.get("entries", []):
            entry = _entry_from_json(raw)
            self._entries[str(entry.output_path)] = entry

    def record(self, profile: NativeAgentProfile) -> None:
        """Insert or replace the entry for ``profile.output_path``."""
        self._entries[str(profile.output_path)] = profile

    def get_hash(self, output_path: Path) -> str | None:
        """Return the recorded hash for ``output_path`` or ``None``."""
        entry = self._entries.get(str(output_path))
        return entry.file_hash if entry is not None else None

    def all_entries(self) -> list[NativeAgentProfile]:
        """Return every recorded entry, ordered by output path."""
        return [self._entries[key] for key in sorted(self._entries)]

    def remove(self, output_path: Path) -> None:
        """Drop the entry for ``output_path`` if present (no-op otherwise)."""
        self._entries.pop(str(output_path), None)

    def save(self) -> None:
        """Write the manifest to disk, creating ``.kittify/`` as needed."""
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": SCHEMA_VERSION,
            "entries": [_entry_to_json(e) for e in self.all_entries()],
        }
        self.manifest_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def _entry_to_json(entry: NativeAgentProfile) -> dict[str, object]:
    return {
        "profile_urn": entry.profile_urn,
        "source_layer": entry.source_layer,
        "tool_key": entry.tool_key,
        "output_path": str(entry.output_path),
        "format": entry.format,
        "file_hash": entry.file_hash,
    }


def _entry_from_json(raw: dict[str, object]) -> NativeAgentProfile:
    file_hash = raw.get("file_hash")
    return NativeAgentProfile(
        profile_urn=str(raw["profile_urn"]),
        source_layer=str(raw["source_layer"]),
        tool_key=str(raw["tool_key"]),
        output_path=Path(str(raw["output_path"])),
        format=str(raw["format"]),
        file_hash=str(file_hash) if file_hash is not None else None,
    )
