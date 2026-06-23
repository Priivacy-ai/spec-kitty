"""Shared org-pack config contract for ``.kittify/config.yaml``.

The operator-facing config shape belongs below both ``charter`` and
``specify_cli`` so every consumer sees the same configured packs. New writes
use the canonical ``doctrine.org.packs`` schema; the old top-level
``organisation_packs`` form is read as legacy compatibility through this same
parser so it cannot drift independently.
"""

from __future__ import annotations

import warnings
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator
from ruamel.yaml import YAML

__all__ = [
    "OrgPackConfig",
    "OrgPackSubdirEscapeError",
    "PackRegistry",
    "load_pack_registry",
    "resolve_org_roots",
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
    def _expand_tilde(cls, value: str | Path) -> Path:
        return Path(str(value)).expanduser()

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

    def effective_root(self, repo_root: Path) -> Path:
        """Return the resolved pack root, joining ``subdir`` when set.

        Resolution strategy
        -------------------
        1. Normalise ``local_path`` relative to ``repo_root`` when it is
           relative (so relative config values work from any CWD).
        2. Join ``subdir`` when present.
        3. Apply a **resolution-time** containment check using
           ``resolve(strict=False)`` so that a not-yet-fetched pack directory
           does NOT raise ``FileNotFoundError``.

        Raises
        ------
        OrgPackSubdirEscapeError
            When the resolved effective path escapes outside ``local_path``
            (symlink-escape detected at resolution time).
        """
        # Step 1 — normalise local_path vs repo_root
        pack_root = self.local_path if self.local_path.is_absolute() else repo_root / self.local_path

        if self.subdir is None:
            return pack_root.resolve(strict=False)

        # Step 2 — join subdir
        candidate = pack_root / self.subdir

        # Step 3 — containment check (strict=False so missing dirs don't crash)
        resolved_pack_root = pack_root.resolve(strict=False)
        resolved_candidate = candidate.resolve(strict=False)
        try:
            resolved_candidate.relative_to(resolved_pack_root)
        except ValueError as exc:
            raise OrgPackSubdirEscapeError(
                f"subdir {self.subdir!r} resolves outside pack root "
                f"{resolved_pack_root}: {resolved_candidate}"
            ) from exc

        return resolved_candidate


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
