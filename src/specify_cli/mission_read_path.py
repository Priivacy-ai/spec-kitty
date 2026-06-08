"""Compatibility shim for canonical mission read-path resolution.

The implementation lives in :mod:`specify_cli.missions._read_path_resolver`.
This module is retained for older lightweight ``spec-kitty next`` imports, but
must not grow resolver logic of its own.
"""

from __future__ import annotations

from typing import Any

from specify_cli.missions._read_path_resolver import resolve_mission_read_path

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
