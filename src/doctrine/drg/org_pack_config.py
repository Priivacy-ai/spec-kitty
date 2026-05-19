"""Shared org-pack config contract for ``.kittify/config.yaml``.

The operator-facing config shape belongs below both ``charter`` and
``specify_cli`` so every consumer sees the same configured packs. New writes
use the canonical ``doctrine.org.packs`` schema; the old top-level
``organisation_packs`` form is read as legacy compatibility through this same
parser so it cannot drift independently.
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator
from ruamel.yaml import YAML

__all__ = [
    "OrgPackConfig",
    "PackRegistry",
    "SourceType",
    "load_pack_registry",
    "resolve_org_roots",
    "save_pack_registry",
]

SourceType = Literal["git", "https", "api"]

_CONFIG_REL_PATH = Path(".kittify") / "config.yaml"
_LEGACY_DEFAULT_PACK_NAME = "default"


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
    """Return configured org doctrine local roots in declaration order."""

    return [pack.local_path for pack in load_pack_registry(repo_root).packs]


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
    if pack.source_type is not None:
        payload["source_type"] = pack.source_type
    if pack.url is not None:
        payload["url"] = pack.url
    if pack.ref is not None:
        payload["ref"] = pack.ref
    return payload
