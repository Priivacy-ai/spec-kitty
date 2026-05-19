"""Pydantic models and loader for the ``doctrine.org`` config block.

This module reads and writes the ``doctrine.org`` block of
``.kittify/config.yaml`` and exposes a typed registry of org doctrine packs
for the rest of ``specify_cli``.

Schema (see ``contracts/config-schema.yaml``):

* **Form A — multi-pack** (preferred)::

    doctrine:
      org:
        packs:
          - name: security
            local_path: ~/.kittify/org/security/
            source_type: git
            url: git@example.com:security/doctrine.git
            ref: v2.1.0

* **Form B — legacy single pack** (backward compatibility)::

    doctrine:
      org:
        local_path: ~/.kittify/org/acme/
        source_type: git
        url: git@example.com:acme/doctrine.git

When the config file or ``doctrine.org`` block is missing, an *empty*
:class:`PackRegistry` is returned (never ``None``).  This keeps callers
branch-free for the common no-config case.

Architectural note: the actual config-aware resolver for org doctrine lives
here (in ``specify_cli``).  The lower ``charter`` layer keeps
``_resolve_org_root()`` as an inert stub and accepts an explicit ``org_root``
argument so the dependency direction
``kernel <- doctrine <- charter <- specify_cli`` is preserved.
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator
from ruamel.yaml import YAML

__all__ = [
    "OrgPackConfig",
    "PackRegistry",
    "load_pack_registry",
    "save_pack_registry",
    "resolve_org_roots",
]

SourceType = Literal["git", "https", "api"]

_CONFIG_REL_PATH = Path(".kittify") / "config.yaml"
_LEGACY_DEFAULT_PACK_NAME = "default"


def _yaml() -> YAML:
    y = YAML()
    y.preserve_quotes = True
    y.indent(mapping=2, sequence=4, offset=2)
    return y


class OrgPackConfig(BaseModel):
    """Single named org doctrine pack entry."""

    model_config = ConfigDict(extra="forbid", frozen=False)

    name: str
    local_path: Path
    source_type: SourceType | None = None
    url: str | None = None
    ref: str | None = None

    @field_validator("local_path", mode="before")
    @classmethod
    def _expand_tilde(cls, v: str | Path) -> Path:
        return Path(str(v)).expanduser()

    @field_validator("name")
    @classmethod
    def _name_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("pack name must be a non-empty string")
        return v


class PackRegistry(BaseModel):
    """Ordered list of configured org doctrine packs.

    Declaration order is significant — the last entry has the highest
    intra-org-layer precedence (see contracts/config-schema.yaml).
    """

    model_config = ConfigDict(extra="forbid")

    packs: list[OrgPackConfig] = []

    @model_validator(mode="after")
    def _validate_unique_names(self) -> PackRegistry:
        names = [p.name for p in self.packs]
        dupes = sorted({n for n in names if names.count(n) > 1})
        if dupes:
            raise ValueError(
                f"Duplicate pack names in doctrine.org.packs: {dupes}"
            )
        return self

    # Convenience -----------------------------------------------------
    def get(self, name: str) -> OrgPackConfig | None:
        for pack in self.packs:
            if pack.name == name:
                return pack
        return None

    def names(self) -> list[str]:
        return [p.name for p in self.packs]


def _config_path(repo_root: Path) -> Path:
    return repo_root / _CONFIG_REL_PATH


def _load_yaml_data(config_path: Path) -> dict[str, Any]:
    """Return the parsed config mapping, or an empty dict on absence / type-mismatch."""
    if not config_path.exists():
        return {}
    text = config_path.read_text(encoding="utf-8")
    if not text.strip():
        return {}
    data = _yaml().load(text)
    if not isinstance(data, dict):
        return {}
    return data


def _build_legacy_pack(org_block: dict[str, Any]) -> OrgPackConfig:
    """Construct a single anonymous pack from a legacy ``local_path`` block."""
    return OrgPackConfig(
        name=_LEGACY_DEFAULT_PACK_NAME,
        local_path=org_block["local_path"],
        source_type=org_block.get("source_type"),
        url=org_block.get("url"),
        ref=org_block.get("ref"),
    )


def load_pack_registry(repo_root: Path) -> PackRegistry:
    """Read ``doctrine.org`` from ``.kittify/config.yaml``.

    Handles both forms:

    * Multi-pack: ``doctrine.org.packs`` → :class:`PackRegistry`.
    * Legacy single: ``doctrine.org.local_path`` → :class:`PackRegistry` with
      one anonymous pack named ``default``.

    Returns an empty :class:`PackRegistry` (never ``None``) when the file or
    block is missing.  On :class:`ValidationError` (including duplicate
    names), emits ``warnings.warn`` and returns an empty registry so the
    caller can degrade gracefully.
    """
    try:
        data = _load_yaml_data(_config_path(repo_root))
    except Exception as exc:  # pragma: no cover - defensive: unreadable YAML
        warnings.warn(
            f"Failed to read .kittify/config.yaml; org doctrine disabled: {exc}",
            stacklevel=2,
        )
        return PackRegistry()

    org_block = data.get("doctrine", {}).get("org") if isinstance(data, dict) else None
    if not isinstance(org_block, dict):
        return PackRegistry()

    try:
        if "packs" in org_block:
            return PackRegistry.model_validate({"packs": org_block["packs"]})
        if "local_path" in org_block:
            return PackRegistry(packs=[_build_legacy_pack(org_block)])
    except ValidationError as exc:
        warnings.warn(
            f"Invalid doctrine.org config; ignoring org layer: {exc}",
            stacklevel=2,
        )
        return PackRegistry()
    except ValueError as exc:
        # Pydantic surfaces our own ValueError through ValidationError, but
        # legacy-pack construction can raise it directly.
        warnings.warn(
            f"Invalid doctrine.org config; ignoring org layer: {exc}",
            stacklevel=2,
        )
        return PackRegistry()

    return PackRegistry()


def save_pack_registry(repo_root: Path, registry: PackRegistry) -> None:
    """Write ``doctrine.org.packs`` to ``.kittify/config.yaml`` (merge-safe).

    Existing top-level keys and other ``doctrine.*`` sub-keys are preserved.
    Creates the file and parent directory when absent.
    """
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
        "packs": [
            _pack_to_yaml_dict(pack) for pack in registry.packs
        ]
    }

    with config_path.open("w", encoding="utf-8") as fh:
        yaml.dump(data, fh)


def _pack_to_yaml_dict(pack: OrgPackConfig) -> dict[str, Any]:
    """Serialise a pack for YAML; drop ``None`` fields for cleanliness."""
    payload: dict[str, Any] = {
        "name": pack.name,
        "local_path": str(pack.local_path),
    }
    if pack.source_type is not None:
        payload["source_type"] = pack.source_type
    if pack.url is not None:
        payload["url"] = pack.url
    if pack.ref is not None:
        payload["ref"] = pack.ref
    return payload


def resolve_org_roots(repo_root: Path) -> list[Path]:
    """Return the ordered list of configured org doctrine pack roots.

    Convenience for ``DoctrineService`` factory sites: callers that only
    need the merge-order list of local paths (and not the typed pack
    metadata) can use this directly.
    """
    registry = load_pack_registry(repo_root)
    return [pack.local_path for pack in registry.packs]
