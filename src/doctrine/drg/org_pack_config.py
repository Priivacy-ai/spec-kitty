"""Shared org-pack config contract for ``.kittify/config.yaml``.

The operator-facing config shape belongs below both ``charter`` and
``specify_cli`` so every consumer sees the same configured packs. New writes
use the canonical ``doctrine.org.packs`` schema; the old top-level
``organisation_packs`` form is read as legacy compatibility through this same
parser so it cannot drift independently.
"""

from __future__ import annotations

import os
import re
import warnings
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator
from ruamel.yaml import YAML

__all__ = [
    "OrgPackConfig",
    "OrgPackEnvVarUnsetError",
    "OrgPackSubdirEscapeError",
    "PackRegistry",
    "load_pack_registry",
    "resolve_org_roots",
    "resolve_relative_path_within_root",
    "save_pack_registry",
]

SourceType = Literal["git", "https", "api"]

_CONFIG_REL_PATH = Path(".kittify") / "config.yaml"
_LEGACY_DEFAULT_PACK_NAME = "default"


class OrgPackSubdirEscapeError(ValueError):
    """Raised when ``subdir`` resolves to a path outside the pack's ``local_path``.

    This is a structured error distinct from generic ``ValueError`` so that
    call sites (and broad ``except Exception`` handlers such as
    ``pack_context.py``) can catch and re-raise it rather than swallowing it
    into a silent empty registry.
    """


class OrgPackEnvVarUnsetError(ValueError):
    """Raised when ``local_path`` references an env var that is unset/empty.

    ``os.path.expandvars`` silently leaves ``${UNSET}``/``$UNSET`` tokens
    verbatim in its output when the referenced variable is not set — this
    would otherwise resolve to a literal-token path (or, when joined onto
    ``repo_root``, an unrelated relative path) instead of failing loudly.
    This structured error names both the unresolved token and the pack so
    the operator can fix ``.kittify/config.yaml`` or their environment.
    """

    def __init__(self, pack_name: str, raw_local_path: str, unresolved_token: str) -> None:
        self.pack_name = pack_name
        self.raw_local_path = raw_local_path
        self.unresolved_token = unresolved_token
        super().__init__(
            f"Org pack {pack_name!r} local_path {raw_local_path!r} references "
            f"environment variable {unresolved_token!r} which is unset or empty "
            "(or is itself a nested ${VAR} token — expansion is not recursive). "
            "Set the variable directly, or update local_path in .kittify/config.yaml."
        )


_ENV_VAR_TOKEN_RE = re.compile(r"\$\{[^}]+\}|\$[A-Za-z_][A-Za-z0-9_]*")


def _expand_path_template(raw: str) -> str:
    """Expand ``${VAR}``/``$VAR`` env-var tokens, then ``~`` home-dir tokens.

    Pure string transform — no filesystem access, no exceptions raised here
    for the happy path. Callers are responsible for detecting any
    unresolved ``$``-tokens left behind by an unset variable (see
    :class:`OrgPackEnvVarUnsetError`).
    """
    return os.path.expanduser(os.path.expandvars(raw))


def _unresolved_env_token(expanded: str) -> str | None:
    """Return the first unresolved ``${VAR}``/``$VAR`` token, if any survives."""
    match = _ENV_VAR_TOKEN_RE.search(expanded)
    return match.group(0) if match else None


def _empty_expanded_env_token(raw: str) -> str | None:
    """Return the first env-var token expanded to empty string (var set but blank)."""
    for match in _ENV_VAR_TOKEN_RE.finditer(raw):
        token = match.group(0)
        var_name = token[2:-1] if token.startswith("${") else token[1:]
        if os.environ.get(var_name) == "":
            return token
    return None


def resolve_relative_path_within_root(root: Path, relative_path: str) -> Path:
    """Resolve *relative_path* under *root*, enforcing containment.

    Shared containment primitive: :meth:`OrgPackConfig.effective_root` uses
    this for ``subdir`` containment, and
    ``specify_cli.doctrine.pack_validator._check_asset_path_containment``
    reuses it for ASSET sidecar manifest ``path`` containment (FR-009 /
    NFR-005) — a single canonical escape-detection implementation rather than
    a hand-rolled resolve-then-``relative_to`` at each call site.

    Rejects (raising :class:`OrgPackSubdirEscapeError`):

    * an absolute *relative_path* (POSIX, Windows drive-letter, or UNC form);
    * a path with a string-level ``..`` component;
    * a path that resolves (``Path.resolve(strict=False)``) outside *root*
      (e.g. a symlink escape).

    Does not otherwise touch the filesystem — a not-yet-materialised *root*
    or *relative_path* is not an error by itself (``strict=False``).
    """
    if PurePosixPath(relative_path).is_absolute() or PureWindowsPath(
        relative_path
    ).is_absolute():
        raise OrgPackSubdirEscapeError(
            f"path {relative_path!r} must be a relative path, got an absolute path"
        )
    posix_parts = PurePosixPath(relative_path).parts
    win_parts = PureWindowsPath(relative_path).parts
    if ".." in posix_parts or ".." in win_parts:
        raise OrgPackSubdirEscapeError(
            f"path {relative_path!r} must not contain '..' components"
        )

    resolved_root = root.resolve(strict=False)
    resolved_candidate = (root / relative_path).resolve(strict=False)
    try:
        resolved_candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise OrgPackSubdirEscapeError(
            f"path {relative_path!r} resolves outside root {resolved_root}: "
            f"{resolved_candidate}"
        ) from exc
    return resolved_candidate


def _yaml() -> YAML:
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)
    return yaml


class OrgPackConfig(BaseModel):
    """Single named org doctrine pack entry."""

    model_config = ConfigDict(extra="forbid", frozen=False)

    name: str
    local_path: Path
    subdir: str | None = None
    source_type: SourceType | None = None
    url: str | None = None
    ref: str | None = None
    legacy_source: str | None = Field(default=None, exclude=True)

    @field_validator("local_path", mode="before")
    @classmethod
    def _coerce_local_path(cls, value: str | Path) -> Path:
        """Coerce to ``Path`` WITHOUT expanding ``~``/env-vars.

        The stored value must remain exactly what the operator wrote —
        including any ``${VAR}``/``$VAR``/``~`` tokens, unexpanded — so
        that :func:`save_pack_registry` round-trips it verbatim. Expansion
        happens only at resolution time, in :meth:`effective_root`.
        """
        return Path(str(value))

    @field_validator("name")
    @classmethod
    def _name_non_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("pack name must be a non-empty string")
        return value

    @field_validator("subdir", mode="before")
    @classmethod
    def _validate_subdir(cls, value: str | None) -> str | None:
        """Validate ``subdir`` at model-construction time (string-level only).

        Rejects absolute paths (POSIX, Windows drive, UNC) and any ``..``
        component.  Normalises ``.`` and empty string to ``None``.  Does NOT
        touch the filesystem — the pack directory may not exist yet.
        """
        if value is None:
            return None
        if not isinstance(value, str):
            value = str(value)
        # Normalize to None for "empty" values
        stripped = value.strip()
        if stripped in ("", "."):
            return None
        # Reject POSIX absolute paths
        if PurePosixPath(stripped).is_absolute():
            raise ValueError(
                f"subdir must be a relative path, got absolute POSIX path: {stripped!r}"
            )
        # Reject Windows drive-letter absolute paths (C:\...) and UNC (\\...)
        if PureWindowsPath(stripped).is_absolute():
            raise ValueError(
                f"subdir must be a relative path, got absolute Windows path: {stripped!r}"
            )
        # Reject any path containing .. components
        parts = PurePosixPath(stripped).parts
        if ".." in parts:
            raise ValueError(
                f"subdir must not contain '..' components, got: {stripped!r}"
            )
        # Also check Windows-style separators for ..
        win_parts = PureWindowsPath(stripped).parts
        if ".." in win_parts:
            raise ValueError(
                f"subdir must not contain '..' components, got: {stripped!r}"
            )
        return stripped

    def local_path_root(self, repo_root: Path) -> Path:
        """Return ``local_path`` after env-var/tilde expansion, normalised against ``repo_root``.

        This is Steps 0-1 of :meth:`effective_root`, exposed separately so
        fetch/write call sites — which target the pack's own directory,
        before any ``subdir`` slicing — resolve through the SAME expansion
        seam as read-side ``effective_root()`` instead of using the raw,
        unexpanded ``self.local_path``. Using the raw value as a fetch/clone
        target would write into a literal ``${VAR}``-named directory while
        every subsequent read resolves the expanded path, silently diverging
        on the very first fetch.

        Raises
        ------
        OrgPackEnvVarUnsetError
            When ``local_path`` references an environment variable that is
            unset or empty (fail-closed — never silently produces a
            literal-token path).
        """
        raw_local_path = str(self.local_path)
        expanded_local_path = _expand_path_template(raw_local_path)
        unresolved_token = _unresolved_env_token(expanded_local_path)
        if unresolved_token is not None:
            raise OrgPackEnvVarUnsetError(self.name, raw_local_path, unresolved_token)
        empty_token = _empty_expanded_env_token(raw_local_path)
        if empty_token is not None:
            raise OrgPackEnvVarUnsetError(self.name, raw_local_path, empty_token)
        expanded_path = Path(expanded_local_path)
        return expanded_path if expanded_path.is_absolute() else repo_root / expanded_path

    def effective_root(self, repo_root: Path) -> Path:
        """Return the resolved pack root, joining ``subdir`` when set.

        Resolution strategy
        -------------------
        0-1. Expand ``local_path`` and normalise it against ``repo_root``
             via :meth:`local_path_root` (read-side only — ``self.local_path``
             itself is never mutated, so the stored config value round-trips
             unexpanded).
        2. Join ``subdir`` when present.
        3. Apply a **resolution-time** containment check using
           ``resolve(strict=False)`` so that a not-yet-fetched pack directory
           does NOT raise ``FileNotFoundError``.

        Raises
        ------
        OrgPackEnvVarUnsetError
            When ``local_path`` references an environment variable that is
            unset or empty (fail-closed — never silently produces a
            literal-token path).
        OrgPackSubdirEscapeError
            When the resolved effective path escapes outside ``local_path``
            (symlink-escape detected at resolution time).
        """
        pack_root = self.local_path_root(repo_root)

        if self.subdir is None:
            return pack_root.resolve(strict=False)

        # Steps 2-3 — join subdir + resolution-time containment check, via
        # the shared primitive (also reused for ASSET manifest path
        # containment in pack_validator.py).
        return resolve_relative_path_within_root(pack_root, self.subdir)


class PackRegistry(BaseModel):
    """Ordered list of configured org doctrine packs."""

    model_config = ConfigDict(extra="forbid")

    packs: list[OrgPackConfig] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_unique_names(self) -> PackRegistry:
        names = [pack.name for pack in self.packs]
        dupes = sorted({name for name in names if names.count(name) > 1})
        if dupes:
            raise ValueError(
                f"Duplicate pack names in doctrine.org.packs: {dupes}"
            )
        return self

    def get(self, name: str) -> OrgPackConfig | None:
        for pack in self.packs:
            if pack.name == name:
                return pack
        return None

    def names(self) -> list[str]:
        return [pack.name for pack in self.packs]


def load_pack_registry(repo_root: Path) -> PackRegistry:
    """Read configured org packs from ``repo_root/.kittify/config.yaml``.

    Canonical shape:

    ``doctrine.org.packs[]`` with ``name`` and ``local_path``.

    Legacy read-only shape:

    top-level ``organisation_packs[]`` with ``name`` and ``path``. This is
    accepted only here so old fixtures/operators degrade consistently across
    all consumers.
    """

    try:
        data = _load_yaml_data(_config_path(repo_root))
    except Exception as exc:  # pragma: no cover - defensive unreadable YAML
        warnings.warn(
            f"Failed to read .kittify/config.yaml; org doctrine disabled: {exc}",
            stacklevel=2,
        )
        return PackRegistry()

    try:
        registry = _registry_from_doctrine_org(data)
        if registry is not None:
            return registry
        legacy_registry = _registry_from_legacy_organisation_packs(data)
        if legacy_registry is not None:
            warnings.warn(
                "Top-level organisation_packs is deprecated; use "
                "doctrine.org.packs[].local_path instead.",
                DeprecationWarning,
                stacklevel=2,
            )
            return legacy_registry
    except ValidationError as exc:
        warnings.warn(
            f"Invalid doctrine.org config; ignoring org layer: {exc}",
            stacklevel=2,
        )
        return PackRegistry()
    except ValueError as exc:
        warnings.warn(
            f"Invalid doctrine.org config; ignoring org layer: {exc}",
            stacklevel=2,
        )
        return PackRegistry()

    return PackRegistry()


def save_pack_registry(repo_root: Path, registry: PackRegistry) -> None:
    """Write the canonical ``doctrine.org.packs`` block merge-safely."""

    config_path = _config_path(repo_root)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    yaml = _yaml()
    if config_path.exists() and config_path.read_text(encoding="utf-8").strip():
        data = yaml.load(config_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            data = {}
    else:
        data = {}

    doctrine_section = data.get("doctrine")
    if not isinstance(doctrine_section, dict):
        doctrine_section = {}
        data["doctrine"] = doctrine_section

    doctrine_section["org"] = {
        "packs": [_pack_to_yaml_dict(pack) for pack in registry.packs]
    }

    with config_path.open("w", encoding="utf-8") as file:
        yaml.dump(data, file)


def resolve_org_roots(repo_root: Path) -> list[Path]:
    """Return configured org doctrine local roots in declaration order.

    Each entry is the pack's ``effective_root`` — i.e. the ``local_path``
    normalised relative to ``repo_root`` and joined with ``subdir`` (when
    present).  The ~9 ``DoctrineService`` consumers that call this function
    therefore inherit the ``subdir`` seam for free.
    """
    return [pack.effective_root(repo_root) for pack in load_pack_registry(repo_root).packs]


def _config_path(repo_root: Path) -> Path:
    return repo_root / _CONFIG_REL_PATH


def _load_yaml_data(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        return {}
    text = config_path.read_text(encoding="utf-8")
    if not text.strip():
        return {}
    data = _yaml().load(text)
    if not isinstance(data, dict):
        return {}
    return data


def _registry_from_doctrine_org(data: dict[str, Any]) -> PackRegistry | None:
    doctrine = data.get("doctrine")
    org_block = doctrine.get("org") if isinstance(doctrine, dict) else None
    if not isinstance(org_block, dict):
        return None
    if "packs" in org_block:
        return PackRegistry.model_validate({"packs": org_block["packs"]})
    if "local_path" in org_block:
        return PackRegistry(packs=[_build_legacy_single_pack(org_block)])
    return PackRegistry()


def _build_legacy_single_pack(org_block: dict[str, Any]) -> OrgPackConfig:
    return OrgPackConfig(
        name=_LEGACY_DEFAULT_PACK_NAME,
        local_path=org_block["local_path"],
        subdir=org_block.get("subdir"),
        source_type=org_block.get("source_type"),
        url=org_block.get("url"),
        ref=org_block.get("ref"),
    )


def _registry_from_legacy_organisation_packs(
    data: dict[str, Any],
) -> PackRegistry | None:
    raw_packs = data.get("organisation_packs")
    if raw_packs is None:
        return None
    if not isinstance(raw_packs, list):
        return PackRegistry()

    packs: list[OrgPackConfig] = []
    for raw in raw_packs:
        if not isinstance(raw, dict):
            continue
        source = str(raw.get("source", "local_path"))
        if source != "local_path":
            raise NotImplementedError(
                f"Org pack source {source!r} not yet implemented. "
                "Use doctrine.org.packs[].local_path for fetched local packs."
            )
        packs.append(
            OrgPackConfig(
                name=raw["name"],
                local_path=raw["path"],
                legacy_source=source,
            )
        )
    return PackRegistry(packs=packs)


def _pack_to_yaml_dict(pack: OrgPackConfig) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": pack.name,
        "local_path": str(pack.local_path),
    }
    if pack.subdir is not None:
        payload["subdir"] = pack.subdir
    if pack.source_type is not None:
        payload["source_type"] = pack.source_type
    if pack.url is not None:
        payload["url"] = pack.url
    if pack.ref is not None:
        payload["ref"] = pack.ref
    return payload
