"""Backward-compatibility shim for specify_cli.missions.

The canonical implementation is in doctrine.missions. This package
re-exports the public surface so that existing callers continue to work
without modification (C-006). Access is mediated through the
``charter.primitives`` facade per the runtime → charter → doctrine
boundary (mission ``charter-mediated-doctrine-selection-01KRTZCA``).
"""

from charter.primitives import PrimitiveExecutionContext, execute_with_glossary

__all__ = [
    "PrimitiveExecutionContext",
    "execute_with_glossary",
]
