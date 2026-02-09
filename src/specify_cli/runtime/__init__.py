"""Global runtime management for spec-kitty.

This subpackage manages the user-global ~/.kittify/ directory,
including path resolution, asset discovery, and runtime bootstrapping.
"""

from specify_cli.runtime.bootstrap import ensure_runtime
from specify_cli.runtime.home import get_kittify_home, get_package_asset_root

__all__ = ["ensure_runtime", "get_kittify_home", "get_package_asset_root"]
