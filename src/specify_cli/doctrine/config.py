"""Org-pack config bindings for the ``specify_cli.doctrine`` management package.

Conduit closure (mission ``doctrine-public-api-surface-01KZPDSR``, WP05 / C-005,
FR-004): the doctrine-origin org-pack-config symbols are NO LONGER part of this
module's ``__all__``. Previously they were re-exported through ``__all__``, which
laundered doctrine-origin objects behind a first-party public surface;
non-exempt runtime that reached them via ``specify_cli.doctrine.config`` now
consumes them through the ``charter.drg`` door (object-identity re-export).

The module-level bindings survive as explicit ``import X as X`` re-exports because
the exempt management package's own public surface (``specify_cli.doctrine``'s
``__init__`` and its unit tests) still exposes the shared contract. They are
deliberately kept out of ``__all__`` — the source-side laundering guard enforces
``__all__``, so their absence there is what closes the conduit.
``assert_pack_local_paths_exist`` is the sole genuine first-party public symbol.
"""

from __future__ import annotations

from pathlib import Path

from doctrine.drg.org_pack_config import (
    OrgPackConfig as OrgPackConfig,
    PackRegistry as PackRegistry,
    load_pack_registry as load_pack_registry,
    resolve_org_roots as resolve_org_roots,
    save_pack_registry as save_pack_registry,
)

__all__ = [
    "assert_pack_local_paths_exist",
]


def assert_pack_local_paths_exist(repo_root: Path) -> None:
    """Hard-fail when any configured org pack's ``local_path`` is missing."""

    from specify_cli.doctrine.org_charter import MissingDoctrinePackError

    registry = load_pack_registry(repo_root)
    for pack in registry.packs:
        effective = pack.effective_root(repo_root)
        if not effective.exists():
            raise MissingDoctrinePackError(pack.name, effective)
