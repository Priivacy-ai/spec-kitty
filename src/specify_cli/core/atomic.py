"""Atomic file write utility — compatibility shim.

The canonical implementation lives in ``kernel.atomic``.
This module re-exports it for backward compatibility with existing
``specify_cli`` imports.
"""

from kernel.atomic import atomic_write

__all__ = ["atomic_write"]
