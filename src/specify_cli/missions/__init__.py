"""Backward-compatibility shim for specify_cli.missions.

The canonical implementation is in doctrine.missions.
This package re-exports the public surface so that existing
callers continue to work without modification (C-006).
"""

from doctrine.missions import PrimitiveExecutionContext, execute_with_glossary

__all__ = [
    "PrimitiveExecutionContext",
    "execute_with_glossary",
]
