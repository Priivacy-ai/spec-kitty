"""Compatibility shim for mission primitives.

This module keeps legacy imports working after primitives moved under
``doctrine.missions``.
"""

from doctrine.missions.primitives import PrimitiveExecutionContext

__all__ = ["PrimitiveExecutionContext"]
