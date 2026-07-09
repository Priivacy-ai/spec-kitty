"""Persistence layer for ``.kittify/command-skills-manifest.json``.

This module is the canonical source for reading and writing the Skills Manifest
that records every ``.agents/skills/spec-kitty*/SKILL.md`` file that
Spec Kitty has installed on a project.

Invariants
----------
* The on-disk file format is JSON with ``schema_version: 1``, sorted keys,
  2-space indent, and a trailing newline.
* Entries are sorted by ``path`` before every write, so diffs are deterministic.
* Unknown future top-level fields are tolerated on load (a warning is emitted)
  but silently dropped on the next ``save()``.  This provides forward-compatibility
  without silent data loss: callers that care must round-trip through the typed
  dataclass and re-serialize.
* Known fields are strictly typed; type mismatches raise ``ManifestError``.
* Writes are atomic: the new content is written to ``<target>.tmp`` in the same
  directory, fsync'd, and renamed via ``os.replace`` so a crash mid-write cannot
  leave a corrupt file.
* ``ManifestEntry`` is a frozen dataclass for hashability.  Mutations happen via
  the ``with_agent_added`` / ``with_agent_removed`` helpers, which return new
  records.

Dependency notes
----------------
``jsonschema`` (>=4.0) is already listed in ``pyproject.toml`` (it is used by
``specify_cli.mission_v1.schema`` and several ``doctrine`` sub-packages), so no
new dependency is introduced by this module.
"""

from __future__ import annotations

import contextlib
import hashlib
import importlib.resources
import json
import logging
import os
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import jsonschema

from specify_cli.core.time_utils import now_utc_iso

from .manifest_errors import ManifestError

__all__ = [
    "SCHEMA_VERSION",
    "ManifestEntry",
    "SkillsManifest",
    "fingerprint",
    "fingerprint_file",
    "load",
    "remove_unsafe_symlinks",
    "repair_stale_manifest",
    "save",
]

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1
_MANIFEST_FILENAME = "command-skills-manifest.json"
_KITTIFY_DIR = ".kittify"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ManifestEntry:
    """One record per installed skill-package file.

    ``agents`` is stored as a sorted tuple (no duplicates) for hashability.
    The JSON representation uses a list; the load/save boundary coerces between
    the two.
    """

    path: str
    """POSIX-style path relative to repo root (.agents/skills/spec-kitty*/SKILL.md)."""

    content_hash: str
    """64-char lowercase hex SHA-256 of the installed file content."""

    agents: tuple[str, ...]
    """Sorted tuple of agent keys that installed this entry (e.g. ``("codex", "vibe")``)."""

    installed_at: str
    """ISO-8601 UTC timestamp at which the entry was first written."""

    spec_kitty_version: str
    """CLI version string that wrote this entry (e.g. ``"3.2.0"``)."""

    def with_agent_added(self, agent_key: str) -> ManifestEntry:
        """Return a new entry with *agent_key* included in ``agents``."""
        new_agents = tuple(sorted(set(self.agents) | {agent_key}))
        return ManifestEntry(
            path=self.path,
            content_hash=self.content_hash,
            agents=new_agents,
            installed_at=self.installed_at,
            spec_kitty_version=self.spec_kitty_version,
        )

    def with_agent_removed(self, agent_key: str) -> ManifestEntry:
        """Return a new entry with *agent_key* removed from ``agents``."""
        new_agents = tuple(a for a in self.agents if a != agent_key)
        return ManifestEntry(
            path=self.path,
            content_hash=self.content_hash,
            agents=new_agents,
            installed_at=self.installed_at,
            spec_kitty_version=self.spec_kitty_version,
        )


@dataclass
class SkillsManifest:
    """In-memory representation of the skills manifest."""

    schema_version: int = SCHEMA_VERSION
    entries: list[ManifestEntry] = field(default_factory=list)

    def find(self, path: str) -> ManifestEntry | None:
        """Return the entry with the given *path*, or ``None``."""
        for entry in self.entries:
            if entry.path == path:
                return entry
        return None

    def upsert(self, entry: ManifestEntry) -> None:
        """Replace the existing entry for *entry.path*, or append if absent.

        This ensures no two entries share a ``path`` — it replaces by path rather
        than appending a duplicate.
        """
        self.entries = [e for e in self.entries if e.path != entry.path]
        self.entries.append(entry)

    def remove_path(self, path: str) -> None:
        """Remove the entry for *path* (no-op if absent)."""
        self.entries = [e for e in self.entries if e.path != path]


@dataclass
class ManifestRepairResult:
    """Result of a ``repair_stale_manifest()`` or ``remove_unsafe_symlinks()`` call."""

    added: list[str] = field(default_factory=list)
    """Relative paths added to the manifest (were missing from canonical set)."""

    removed: list[str] = field(default_factory=list)
    """Relative paths removed from the manifest (were orphaned / not canonical)."""

    symlinks_removed: list[str] = field(default_factory=list)
    """Absolute paths of unsafe symlink artifacts that were deleted."""

    drifted: list[str] = field(default_factory=list)
    """Relative paths whose on-disk content no longer matches the manifest hash.

    Drifted files are *not* auto-repaired here — they are reported so callers
    can route them through ``run_surface_repair()`` (Rule 3 / prompt policy).
    """

    @property
    def changed(self) -> bool:
        """Return True when any manifest mutations or symlink removals occurred."""
        return bool(self.added or self.removed or self.symlinks_removed)


# ---------------------------------------------------------------------------
# Schema loading (package-bundled)
# ---------------------------------------------------------------------------


def _load_schema() -> dict[str, Any]:
    """Load the bundled JSON schema from ``skills/data/skills-manifest.schema.json``."""
    pkg = importlib.resources.files("specify_cli.skills.data")
    schema_bytes = (pkg / "skills-manifest.schema.json").read_bytes()
    return json.loads(schema_bytes)  # type: ignore[no-any-return]


# Cached at module level so we only parse once per process.
_SCHEMA: dict[str, Any] | None = None


def _get_schema() -> dict[str, Any]:
    global _SCHEMA  # noqa: PLW0603
    if _SCHEMA is None:
        _SCHEMA = _load_schema()
    return _SCHEMA


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _validate_against_schema(data: dict[str, Any]) -> None:
    """Validate *data* against the bundled JSON schema.

    Raises ``ManifestError("schema_validation_failed", errors=[...])`` on failure.
    """
    schema = _get_schema()
    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
    if errors:
        messages = [f"{'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}" for e in errors]
        raise ManifestError("schema_validation_failed", errors=messages)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load(repo_root: Path) -> SkillsManifest:
    """Load the skills manifest from ``<repo_root>/.kittify/command-skills-manifest.json``.

    Returns an empty ``SkillsManifest`` if the file does not exist.

    Forward-compatibility
    ~~~~~~~~~~~~~~~~~~~~~
    Unknown top-level fields (not defined in the schema) are tolerated: a warning
    is logged and the unknown fields are discarded.  On the next ``save()`` call
    only the known fields will be written.  This allows a newer Spec Kitty to
    write extra fields that an older CLI can read without crashing.

    Raises
    ------
    ManifestError("corrupt_json")
        The file exists but cannot be parsed as JSON.
    ManifestError("unsupported_schema_version")
        The ``schema_version`` field is present but not equal to ``1``.
    ManifestError("schema_validation_failed")
        The document is valid JSON but fails schema validation.
    ManifestError("duplicate_path")
        Two or more entries share the same ``path``.
    """
    manifest_path = repo_root / _KITTIFY_DIR / _MANIFEST_FILENAME

    if not manifest_path.exists():
        return SkillsManifest(schema_version=SCHEMA_VERSION, entries=[])

    raw = manifest_path.read_text(encoding="utf-8")

    try:
        data: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ManifestError(
            "corrupt_json",
            path=str(manifest_path),
            detail=str(exc),
        ) from exc

    # Check schema version before full schema validation so we emit a targeted
    # error message rather than a generic "const" failure from jsonschema.
    found_version = data.get("schema_version")
    if found_version != SCHEMA_VERSION:
        raise ManifestError("unsupported_schema_version", found=found_version)

    # Warn about and discard unknown top-level fields BEFORE schema validation.
    # The schema uses `additionalProperties: false`, so unknown fields would
    # otherwise fail validation.  We strip them here to provide
    # forward-compatibility: a newer Spec Kitty can write extra fields that an
    # older CLI tolerates.
    known_top_level = {"schema_version", "entries"}
    unknown = set(data.keys()) - known_top_level
    if unknown:
        warnings.warn(
            f"command-skills-manifest.json contains unknown top-level fields that will be dropped on next save: {sorted(unknown)}",
            stacklevel=2,
        )
        data = {k: v for k, v in data.items() if k in known_top_level}

    # Full schema validation (covers required fields, types, patterns, enums).
    _validate_against_schema(data)

    # Deserialize entries.
    entries: list[ManifestEntry] = []
    seen_paths: set[str] = set()
    for raw_entry in data.get("entries", []):
        entry_path: str = raw_entry["path"]
        if entry_path in seen_paths:
            raise ManifestError("duplicate_path", path=entry_path)
        seen_paths.add(entry_path)

        entries.append(
            ManifestEntry(
                path=entry_path,
                content_hash=raw_entry["content_hash"],
                agents=tuple(sorted(raw_entry["agents"])),
                installed_at=raw_entry["installed_at"],
                spec_kitty_version=raw_entry["spec_kitty_version"],
            )
        )

    return SkillsManifest(schema_version=SCHEMA_VERSION, entries=entries)


def save(repo_root: Path, manifest: SkillsManifest) -> None:
    """Atomically write *manifest* to ``<repo_root>/.kittify/command-skills-manifest.json``.

    Steps
    -----
    1. Validate the manifest against the bundled JSON schema — raises before
       touching disk if the manifest is invalid.
    2. Sort entries by ``path`` ascending.
    3. Serialize with ``json.dumps(..., indent=2, sort_keys=True, ensure_ascii=False)``
       and append a trailing newline.
    4. Write to ``<target>.tmp`` in the same directory, ``os.fsync``, then
       ``os.replace`` to the final path.  This guarantees a crash mid-write
       cannot leave a corrupt file.

    Raises
    ------
    ManifestError("schema_validation_failed")
        The in-memory manifest is invalid — caller bug, not a file problem.
    """
    kittify_dir = repo_root / _KITTIFY_DIR
    kittify_dir.mkdir(parents=True, exist_ok=True)
    target = kittify_dir / _MANIFEST_FILENAME

    # Sort entries deterministically before serialization.
    sorted_entries = sorted(manifest.entries, key=lambda e: e.path)

    data: dict[str, Any] = {
        "schema_version": manifest.schema_version,
        "entries": [
            {
                "path": e.path,
                "content_hash": e.content_hash,
                "agents": sorted(e.agents),
                "installed_at": e.installed_at,
                "spec_kitty_version": e.spec_kitty_version,
            }
            for e in sorted_entries
        ],
    }

    # Validate before touching disk.
    _validate_against_schema(data)

    serialized = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    encoded = serialized.encode("utf-8")

    tmp_path = target.with_suffix(".tmp")
    try:
        with tmp_path.open("wb") as fh:
            fh.write(encoded)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_path, target)
    except Exception:
        # Best-effort cleanup of the temp file; do not mask the original error.
        with contextlib.suppress(OSError):
            tmp_path.unlink(missing_ok=True)
        raise


# ---------------------------------------------------------------------------
# Fingerprint helpers
# ---------------------------------------------------------------------------


def fingerprint(content: bytes) -> str:
    """Return the lowercase hex SHA-256 digest of *content*.

    This is the canonical hashing routine used by the installer, renderer
    snapshot tests, and migration to ensure all components agree on the
    content-hash format stored in ``ManifestEntry.content_hash``.
    """
    return hashlib.sha256(content).hexdigest()  # noqa: TID251 - production raw SHA-256 owner


def fingerprint_file(path: Path) -> str:
    """Return the SHA-256 hex digest of the bytes at *path*.

    Reads the file without following symlinks beyond what the OS normally
    does for ``open()``; callers that need stricter symlink policies should
    resolve the path themselves before calling this function.
    """
    return fingerprint(path.read_bytes())


# ---------------------------------------------------------------------------
# Manifest repair helpers (T028, T029, T030)
# ---------------------------------------------------------------------------

_SKILL_PATH_TEMPLATE = ".agents/skills/spec-kitty.{command}/SKILL.md"
_SKILL_DIR_PREFIX = ".agents/skills/"
_SPEC_KITTY_SKILL_PREFIX = "spec-kitty."
# Placeholder agent key used when synthesizing repair entries with no known owner.
# Must be a valid value in the JSON schema's agents enum.
_REPAIR_PLACEHOLDER_AGENT = "codex"


def repair_stale_manifest(
    project_root: Path,
    *,
    canonical_commands: list[str],
    spec_kitty_version: str = "unknown",
) -> ManifestRepairResult:
    """Compare the manifest entry count against *canonical_commands*.

    If the manifest is stale (missing entries or has orphaned entries), add
    the missing entries and remove the orphaned ones.  Returns a
    :class:`ManifestRepairResult` describing what was added/removed.

    Drifted files (on-disk content differs from manifest hash) are reported
    in ``result.drifted`` but are **not** auto-repaired here — they must be
    routed through ``run_surface_repair()`` by the caller (Rule 3 / prompt
    policy from WP01).

    This function is always auto-applied (Rule 2 — auto-repair); it never
    prompts the user.  It is idempotent: re-running on an already-correct
    manifest is a no-op.

    Parameters
    ----------
    project_root:
        Repository root containing ``.kittify/`` and ``.agents/``.
    canonical_commands:
        The authoritative list of command names that should be in the
        manifest (e.g. from ``CANONICAL_COMMANDS`` in ``command_installer``).
    spec_kitty_version:
        Version string written into synthesized placeholder entries.
    """
    manifest = load(project_root)
    result = ManifestRepairResult()

    canonical_paths = {_SKILL_PATH_TEMPLATE.format(command=cmd): cmd for cmd in canonical_commands}

    existing_paths = {e.path for e in manifest.entries}

    # --- 1. Add missing canonical entries -----------------------------------
    for rel_path in sorted(canonical_paths):
        if rel_path in existing_paths:
            continue
        abs_path = project_root / rel_path
        # File absent or is a symlink — synthesize a placeholder hash so
        # the manifest count is correct; the surface repair service will
        # detect and address the underlying file issue.
        content_hash = fingerprint_file(abs_path) if abs_path.exists() and not abs_path.is_symlink() else fingerprint(b"")
        new_entry = ManifestEntry(
            path=rel_path,
            content_hash=content_hash,
            # Schema requires agents to be non-empty; use placeholder until the
            # real installer overwrites this entry with the actual agent set.
            agents=(_REPAIR_PLACEHOLDER_AGENT,),
            installed_at=now_utc_iso(),
            spec_kitty_version=spec_kitty_version,
        )
        manifest.upsert(new_entry)
        result.added.append(rel_path)
        logger.debug("repair_stale_manifest: added missing entry %s", rel_path)

    # --- 2. Remove orphaned entries -----------------------------------------
    for entry in list(manifest.entries):
        if entry.path not in canonical_paths:
            manifest.remove_path(entry.path)
            result.removed.append(entry.path)
            logger.debug("repair_stale_manifest: removed orphaned entry %s", entry.path)

    # --- 3. Detect drifted files (report only — no auto-repair) -------------
    for entry in manifest.entries:
        abs_path = project_root / entry.path
        if abs_path.exists() and not abs_path.is_symlink():
            actual_hash = fingerprint_file(abs_path)
            if actual_hash != entry.content_hash and entry.path not in result.added:
                result.drifted.append(entry.path)
                logger.debug(
                    "repair_stale_manifest: drifted file detected %s (manifest=%s, disk=%s)",
                    entry.path,
                    entry.content_hash[:8],
                    actual_hash[:8],
                )

    if result.changed:
        save(project_root, manifest)

    return result


def remove_unsafe_symlinks(project_root: Path) -> ManifestRepairResult:
    """Detect and remove unsafe symlink artifacts under ``.agents/skills/``.

    A past migration bug created symlink directories such as
    ``.agents/skills/spec-kitty`` pointing outside the project tree.
    This function walks ``.agents/skills/`` and removes any entry whose name
    is a Spec Kitty skill package name and is a symbolic link (rather than a
    real directory containing ``SKILL.md``).

    Only symlinks are removed — real directories are left untouched.

    Returns a :class:`ManifestRepairResult` whose ``symlinks_removed`` field
    lists the absolute paths of every symlink that was deleted.
    """
    result = ManifestRepairResult()
    skills_dir = project_root / _SKILL_DIR_PREFIX.rstrip("/")
    if not skills_dir.is_dir():
        return result

    for child in sorted(skills_dir.iterdir()):
        if child.name != "spec-kitty" and not child.name.startswith(_SPEC_KITTY_SKILL_PREFIX):
            continue
        if child.is_symlink():
            try:
                child.unlink()
                result.symlinks_removed.append(str(child))
                logger.info("remove_unsafe_symlinks: removed symlink artifact %s", child)
            except OSError as exc:
                logger.warning(
                    "remove_unsafe_symlinks: could not remove symlink %s: %s",
                    child,
                    exc,
                )

    return result
