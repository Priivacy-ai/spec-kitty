"""Project identity management for spec-kitty.

Canonical home for ProjectIdentity and all related helpers.
Moved here from specify_cli.sync.project_identity (GitHub issue #862)
so that specify_cli.dossier can import it without depending on
specify_cli.sync.

Provides:
- ProjectIdentity dataclass with persistence
- Generation of project UUID, slug, and node ID
- Atomic writes to config.yaml
- Graceful backfill for existing projects
- Read-only fallback with in-memory identity
"""

from __future__ import annotations

import getpass
import hashlib
import logging
import os
import socket
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from rich.console import Console
from ruamel.yaml import YAML

logger = logging.getLogger(__name__)

# Fixed namespace for deterministic build_id derivation (Decision C, FR-002).
# Derived once from NAMESPACE_URL so a *minted* build_id is stable across
# repeated read-only resolutions of the same (project_uuid, node_id) pair.
_BUILD_ID_NAMESPACE = uuid5(NAMESPACE_URL, "spec-kitty:identity:build_id")
# Separator between the two derivation inputs in the uuid5 name string.
_BUILD_ID_INPUT_SEPARATOR = ":"


@dataclass
class ProjectIdentity:
    """Unique identity for a spec-kitty project.

    Fields:
        project_uuid: UUID4 identifier, unique per project
        project_slug: Human-readable slug derived from repo name
        node_id: Stable machine identifier (12-char hex)
        repo_slug: Optional owner/repo override for git metadata
    """

    project_uuid: UUID | None = None
    project_slug: str | None = None
    node_id: str | None = None
    repo_slug: str | None = None
    build_id: str | None = None

    @property
    def is_complete(self) -> bool:
        """Check if all identity fields are populated.

        Note: repo_slug is optional and not required for completeness.
        build_id is required for completeness (FR-009).
        """
        return all([self.project_uuid, self.project_slug, self.node_id, self.build_id])

    def with_defaults(self, repo_root: Path) -> ProjectIdentity:
        """Return new instance with missing fields filled with generated values.

        Note: repo_slug is a user override, not auto-generated.

        Args:
            repo_root: Path to repository root for slug derivation

        Returns:
            New ProjectIdentity with all fields populated
        """
        # Resolve the identity inputs first so a *missing* build_id is derived from
        # their final values, not the possibly-None originals (Decision C / FR-002).
        resolved_project_uuid = self.project_uuid or generate_project_uuid()
        resolved_node_id = self.node_id or generate_node_id()
        return ProjectIdentity(
            project_uuid=resolved_project_uuid,
            project_slug=self.project_slug or derive_project_slug(repo_root),
            node_id=resolved_node_id,
            repo_slug=self.repo_slug,
            build_id=self.build_id or derive_build_id(resolved_project_uuid, resolved_node_id),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for YAML persistence.

        Returns:
            Dictionary with 'uuid', 'slug', 'node_id', and 'build_id' keys.
            Includes 'repo_slug' only if not None.
        """
        d: dict[str, Any] = {
            "uuid": str(self.project_uuid) if self.project_uuid else None,
            "slug": self.project_slug,
            "node_id": self.node_id,
            "build_id": self.build_id,
        }
        if self.repo_slug is not None:
            d["repo_slug"] = self.repo_slug
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProjectIdentity:
        """Deserialize from dictionary.

        Args:
            data: Dictionary with optional 'uuid', 'slug', 'node_id', 'repo_slug', 'build_id' keys

        Returns:
            ProjectIdentity instance
        """
        uuid_str = data.get("uuid")
        return cls(
            project_uuid=UUID(uuid_str) if uuid_str else None,
            project_slug=data.get("slug"),
            node_id=data.get("node_id"),
            repo_slug=data.get("repo_slug"),
            build_id=data.get("build_id"),
        )


def generate_project_uuid() -> UUID:
    """Generate a new UUID4 for project identification.

    Returns:
        Randomly generated UUID4
    """
    return uuid4()


def generate_build_id() -> str:
    """Generate a new UUID4 string for build identification (FR-009).

    Returns:
        UUID4 string for use as build_id in upstream contracts
    """
    return str(uuid4())


def derive_build_id(project_uuid: UUID, node_id: str) -> str:
    """Derive a deterministic build_id from project_uuid + node_id (Decision C, FR-002).

    Pure function: same ``(project_uuid, node_id)`` inputs always produce the same
    output, with no randomness or I/O. This lets the read-only resolver
    (:func:`resolve_identity`) mint a *stable* build_id for an incomplete-identity
    checkout without persisting it — the value no longer drifts between calls the way
    :func:`generate_build_id` (random uuid4) would.

    Args:
        project_uuid: Resolved project UUID (the stable per-project identifier)
        node_id: Resolved stable machine identifier

    Returns:
        Deterministic UUID5 string derived from the two inputs.
    """
    name = f"{project_uuid}{_BUILD_ID_INPUT_SEPARATOR}{node_id}"
    return str(uuid5(_BUILD_ID_NAMESPACE, name))


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
            encoding="utf-8",
            errors="replace",
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
    """Generate stable machine identifier from hostname + username.

    Returns first 12 characters of SHA-256 hash for anonymization.
    Same value across CLI restarts, different per user on shared machines.
    """
    hostname = socket.gethostname()
    username = getpass.getuser()
    raw = f"{hostname}:{username}"
    return hashlib.sha256(raw.encode()).hexdigest()[:12]  # noqa: TID251 - production raw SHA-256 owner


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


class ConfigNotUnderstoodError(RuntimeError):
    """``config.yaml`` exists but cannot be parsed, or its top level is not a mapping.

    Raised only by :func:`atomic_write_config`, and deliberately **not** by
    :func:`load_identity`: reading such a file yields no identity (the answer it
    already gave for a parse error), while *writing over* it is refused. One notion
    of "a config that cannot be understood", two directions.

    ``load_identity``'s seven production callers therefore learn nothing new — a new
    exception nobody catches is a crash moved, not fixed — and this error is handled
    inside :func:`ensure_identity`, so its own callers (``init``, ``tracker``,
    history-import) see the in-memory-identity degradation they already handle for an
    unwritable config rather than a new failure.

    Mirrors ``sync/consent.py``'s ``ConfigReadFault(kind="unparseable", detail="…top-level
    content is not a mapping")`` so the two modules do not grow separate notions of
    the same broken file (#3030 FR-022 follow-up).
    """


def _config_shape_fault(config: object, config_path: Path) -> str | None:
    """Return why *config* is not a usable config document, or ``None``.

    A YAML document is not necessarily a mapping: ``- a\\n- list`` loads as a
    sequence, ``hello`` as a string, ``42`` as an int. Every one of those reached
    ``config.get("project")`` and raised ``AttributeError`` out of functions whose
    contract is to answer. ``None``/empty is *absence*, not a fault — an empty file
    legitimately means "no identity recorded yet" and must keep minting.
    """
    if config is None:
        return None
    if not isinstance(config, dict):
        return (
            f"{config_path}: top-level content is not a mapping "
            f"(got {type(config).__name__})"
        )
    return None


def _load_mapping_for_merge(config_path: Path, yaml: YAML) -> dict[str, Any]:
    """Load *config_path* as a mapping to merge into, or refuse.

    The refusal is what stops an identity write from replacing a document it could
    not read. Both failure directions are converted to one typed error so callers do
    not have to know whether ruamel raised or returned the wrong shape.
    """
    try:
        with open(config_path, encoding="utf-8") as f:
            loaded = yaml.load(f)
    except OSError:
        raise
    except Exception as exc:  # noqa: BLE001 - re-raised as the typed refusal below
        raise ConfigNotUnderstoodError(
            f"{config_path}: could not be parsed ({exc}); refusing to overwrite it"
        ) from exc

    fault = _config_shape_fault(loaded, config_path)
    if fault is not None:
        raise ConfigNotUnderstoodError(f"{fault}; refusing to overwrite it")
    # Returned as loaded, NOT copied into a plain dict: ruamel's round-trip loader
    # returns a CommentedMap (itself a dict subclass) carrying the file's comments,
    # and rebuilding it as a dict would silently strip every comment the operator
    # wrote on the next identity write.
    return loaded if loaded else {}


def atomic_write_config(config_path: Path, identity: ProjectIdentity) -> None:
    """Atomically write identity to config.yaml (temp file + rename).

    Uses the POSIX-compliant os.replace() for atomic rename.
    Temp file is created in the same directory to ensure same filesystem.

    Existing content is **merged**, not overwritten: the file is re-loaded and only
    its ``project`` section is replaced, so unrelated sections (``sync.enabled``,
    comments) survive an identity write. That merge is only meaningful over a
    document that can be understood — hence the refusal below.

    Args:
        config_path: Path to config.yaml
        identity: ProjectIdentity to persist

    Raises:
        OSError: If write fails
        ConfigNotUnderstoodError: If the file exists but cannot be parsed, or its
            top level is not a mapping. Refusing is the point: the only way to
            "succeed" would be to discard a document we could not read, taking the
            operator's other sections with it. Nothing is written and no temp file
            is created.
    """
    yaml = YAML()
    yaml.preserve_quotes = True

    # Ensure parent directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing config to merge into, or start fresh when there is no file
    config = _load_mapping_for_merge(config_path, yaml) if config_path.exists() else {}

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

    # A YAML document need not be a mapping. ``- a\n- list`` loads as a sequence,
    # ``hello`` as a str, ``42`` as an int — and each one made the ``.get`` below
    # raise ``AttributeError`` out of a function documented to handle malformed
    # config gracefully. That crashed every caller, including the sync policy gate
    # (``sync/routing.py``), which is supposed to answer a boolean. Treated exactly
    # like the parse error above: no identity, warned, no exception.
    shape_fault = _config_shape_fault(config, config_path)
    if shape_fault is not None:
        logger.warning(f"Invalid config.yaml; regenerating identity: {shape_fault}")
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
        except ConfigNotUnderstoodError as e:
            # The file is writable but not understandable, so persisting would mean
            # replacing a document we could not read — taking the operator's other
            # sections with it. Degrade down the path this function already has for
            # an unwritable config: usable in-memory identity, file untouched,
            # operator warned. Handled HERE so that ``init`` / ``tracker`` /
            # history-import see no new exception (#3030 FR-022 follow-up).
            logger.warning(f"Refusing to persist identity: {e}")
            _warn_in_memory("Config exists but could not be understood")
        except OSError as e:
            logger.warning(f"Failed to persist identity: {e}")
            _warn_in_memory()
    else:
        _warn_in_memory()

    return identity


def resolve_identity(repo_root: Path) -> ProjectIdentity:
    """Resolve a complete project identity WITHOUT persisting it (#1916).

    Read-only counterpart of :func:`ensure_identity`. Loads the on-disk identity and
    fills deterministic missing fields *in memory only* — it never writes
    ``.kittify/config.yaml``. Use this on side-effect-free paths (e.g. accept
    readiness / the sync emitter init) where identity must be *available* but the
    minting must not dirty the working tree. Persisting a new project UUID is the
    job of :func:`ensure_identity` at a write-authorized boundary (``init``,
    commit-authorized accept).

    Determinism note (C-IR-4): the realistic stable case is a *legacy* checkout that
    already persisted ``project_uuid``/``project_slug``/``node_id`` but is missing
    ``build_id``. Because :func:`ProjectIdentity.with_defaults` now derives a missing
    ``build_id`` deterministically from the resolved ``project_uuid``/``node_id``
    (see :func:`derive_build_id`), repeated calls return an identical identity with no
    drift and no write. The truly-uninitialized case (no ``project_uuid`` on disk)
    returns a side-effect-free not-initialized identity; callers that require a
    project UUID must no-op or tell the operator to run ``init``.

    Args:
        repo_root: Path to repository root

    Returns:
        Complete ProjectIdentity (all fields populated, not persisted)
    """
    config_path = repo_root / ".kittify" / "config.yaml"

    identity = load_identity(config_path)
    if identity.is_complete:
        return identity

    if identity.project_uuid is None:
        return ProjectIdentity(
            project_uuid=None,
            project_slug=identity.project_slug or derive_project_slug(repo_root),
            node_id=identity.node_id or generate_node_id(),
            repo_slug=identity.repo_slug,
            build_id=identity.build_id,
        )

    return identity.with_defaults(repo_root)


def _warn_in_memory(reason: str = "Config not writable") -> None:
    """Warn that identity is in-memory only, naming the actual cause.

    *reason* defaults to the historical wording (an unwritable config). It is a
    parameter because there is now a second cause with a different remedy: a config
    that is writable but cannot be understood. Telling that operator "not writable"
    sends them to ``chmod`` when the fix is a YAML error — the misdirected-cause
    class this mission has been closing elsewhere (#3030).
    """
    console = Console(stderr=True)
    console.print(f"[yellow]Warning: {reason}; using in-memory identity[/yellow]")
