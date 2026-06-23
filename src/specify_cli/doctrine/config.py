"""Compatibility facade for the shared org-pack config contract.

The parser and value objects live in ``doctrine.drg.org_pack_config`` so
``charter`` and ``specify_cli`` consume one contract. This module preserves the
existing ``specify_cli.doctrine.config`` import surface for CLI code.
"""

from __future__ import annotations

from pathlib import Path

from doctrine.drg.org_pack_config import (
    OrgPackConfig,
    PackRegistry,
    load_pack_registry,
    resolve_org_roots,
    save_pack_registry,
)

__all__ = [
    "OrgPackConfig",
    "PackRegistry",
    "assert_pack_local_paths_exist",
    "load_pack_registry",
    "resolve_org_roots",
    "save_pack_registry",
]


def assert_pack_local_paths_exist(repo_root: Path) -> None:
    """Hard-fail when any configured org pack's ``local_path`` is missing."""

    from specify_cli.doctrine.org_charter import MissingDoctrinePackError

    registry = load_pack_registry(repo_root)
    for pack in registry.packs:
        effective = pack.effective_root(repo_root)
        if not effective.exists():
            raise MissingDoctrinePackError(pack.name, effective)
