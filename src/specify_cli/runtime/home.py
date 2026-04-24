"""DEPRECATED — specify_cli.runtime.home is a compatibility shim.

Import from runtime.discovery.home instead:
    from runtime.discovery.home import get_kittify_home, get_package_asset_root
"""
from __future__ import annotations

__deprecated__ = True
__canonical_import__ = "runtime.discovery.home"
__removal_release__ = "3.4.0"
__deprecation_message__ = (
    "specify_cli.runtime.home is deprecated; "
    "use 'from runtime.discovery.home import ...' instead. "
    "Scheduled for removal in 3.4.0."
)

import warnings

warnings.warn(__deprecation_message__, DeprecationWarning, stacklevel=2)

from runtime.discovery.home import *  # noqa: F401, F403
