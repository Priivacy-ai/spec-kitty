"""Backward-compatibility shim for specify_cli.missions.

The canonical implementation is in doctrine.missions. This package
re-exports the public surface so that existing callers continue to work
without modification (C-006). Access is mediated through the
``charter.primitives`` facade per the runtime → charter → doctrine
boundary (mission ``charter-mediated-doctrine-selection-01KRTZCA``).
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "PrimitiveExecutionContext",
    "execute_with_glossary",
]


def __getattr__(name: str) -> Any:
    """Lazily expose the historical primitive helpers.

    Importing submodules such as ``specify_cli.missions._read_path_resolver``
    should not eagerly load the full charter/doctrine primitive stack. That
    startup path is latency-sensitive for ``spec-kitty next`` query mode.
    """
    if name not in __all__:
        raise AttributeError(name)

    from charter.primitives import PrimitiveExecutionContext, execute_with_glossary  # noqa: PLC0415

    exports = {
        "PrimitiveExecutionContext": PrimitiveExecutionContext,
        "execute_with_glossary": execute_with_glossary,
    }
    return exports[name]
