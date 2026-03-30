"""Smoke tests for specify_cli.runtime.home re-export shim.

The canonical behavioural tests for get_kittify_home() and
get_package_asset_root() live in tests/kernel/test_paths.py.

This file only verifies that the shim correctly re-exports the same
objects from kernel.paths, so that existing callers inside specify_cli
(and any downstream code that imports from specify_cli.runtime.home)
continue to work without modification.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.fast


class TestHomeShimReExports:
    """specify_cli.runtime.home re-exports the kernel.paths symbols."""

    def test_get_kittify_home_is_same_object(self) -> None:
        """get_kittify_home from shim is identical to kernel.paths version."""
        from kernel.paths import get_kittify_home as kernel_fn
        from specify_cli.runtime.home import get_kittify_home as shim_fn

        assert shim_fn is kernel_fn

    def test_get_package_asset_root_is_same_object(self) -> None:
        """get_package_asset_root from shim is identical to kernel.paths version."""
        from kernel.paths import get_package_asset_root as kernel_fn
        from specify_cli.runtime.home import get_package_asset_root as shim_fn

        assert shim_fn is kernel_fn

    def test_is_windows_is_same_object(self) -> None:
        """_is_windows from shim is identical to kernel.paths version."""
        from kernel.paths import _is_windows as kernel_fn
        from specify_cli.runtime.home import _is_windows as shim_fn

        assert shim_fn is kernel_fn
