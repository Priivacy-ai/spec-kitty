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

#: Provenance generation stamped on entries written by the current projector
#: (#1940). Bumped when the projection algorithm changes in a way that should
#: force re-projection; recorded per entry so stale generations are detectable.
PROJECTION_VERSION = 1


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
        # Provenance (#1940). Always written by the current projector so new
        # manifests are full 8-field entries.
        "source_path": entry.source_path,
        "source_hash": entry.source_hash,
        "projection_version": entry.projection_version,
    }


def _opt_str(raw: dict[str, object], key: str) -> str | None:
    """Read an optional string field, defaulting to ``None`` when absent.

    Uses ``raw.get`` (not subscripting) so a legacy 6-field entry that predates
    the provenance keys deserializes cleanly rather than raising ``KeyError``.
    """
    value = raw.get(key)
    return str(value) if value is not None else None


def _opt_int(raw: dict[str, object], key: str) -> int | None:
    """Read an optional int field, defaulting to ``None`` when absent."""
    value = raw.get(key)
    if value is None:
        return None
    if isinstance(value, bool):  # bool is an int subclass; reject it explicitly
        raise TypeError(f"manifest field {key!r} must be an int, got bool")
    if isinstance(value, (int, str)):
        return int(value)
    raise TypeError(f"manifest field {key!r} must be an int, got {type(value)!r}")


def _entry_from_json(raw: dict[str, object]) -> NativeAgentProfile:
    return NativeAgentProfile(
        profile_urn=str(raw["profile_urn"]),
        source_layer=str(raw["source_layer"]),
        tool_key=str(raw["tool_key"]),
        output_path=Path(str(raw["output_path"])),
        format=str(raw["format"]),
        file_hash=_opt_str(raw, "file_hash"),
        source_path=_opt_str(raw, "source_path"),
        source_hash=_opt_str(raw, "source_hash"),
        projection_version=_opt_int(raw, "projection_version"),
    )
