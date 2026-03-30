"""Backwards-compatible re-exports for path resolution utilities.

The canonical implementations live in ``kernel.paths``.  This module
preserves all existing import paths inside ``specify_cli`` so that no
call sites need to change.
"""

from __future__ import annotations

from kernel.paths import _is_windows, get_kittify_home, get_package_asset_root

__all__ = ["_is_windows", "get_kittify_home", "get_package_asset_root"]
