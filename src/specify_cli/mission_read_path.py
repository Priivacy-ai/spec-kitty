"""Backward-compat shim — canonical home is specify_cli.missions._read_path_resolver.

This module is retained for older lightweight ``spec-kitty next`` imports, but
must not grow resolver logic of its own. (Its last production importer was
``runtime/next/runtime_bridge.py``, which mission 01KVJPEQ re-pointed to the
canonical ``resolve_handle_to_read_path`` seam; the shim stays for external/
back-compat consumers.)
"""

from __future__ import annotations

from typing import Any

# WP01 privatized the canonical worker (``resolve_mission_read_path`` →
# ``_resolve_mission_read_path``) and dropped it from the resolver's ``__all__``.
# This shim deliberately re-exports it under the ORIGINAL public name so the
# back-compat contract (and the architectural allowlists / importer test that
# depend on ``specify_cli.mission_read_path.resolve_mission_read_path``) keep
# resolving. (Deleting the shim entirely is tracked separately as #2048.)
from specify_cli.missions._read_path_resolver import (
    _resolve_mission_read_path as resolve_mission_read_path,
)

__all__ = [
    "resolve_mission_read_path",
]

_COMPAT_ATTRS = frozenset(
    {
        "STATUS_READ_PATH_NOT_FOUND_CODE",
        "StatusReadPathNotFound",
    }
)


def __getattr__(name: str) -> Any:
    """Resolve historical error-contract names without advertising them."""
    if name not in _COMPAT_ATTRS:
        raise AttributeError(name)
    from specify_cli.missions import _read_path_resolver

    return getattr(_read_path_resolver, name)
