"""Shared base for structured exceptions carrying a stable ``error_code``.

Several exception families across the codebase expose a machine-readable
``error_code`` so consumers branch on the typed value rather than
substring-matching human-readable messages (NFR-007). Before this base
those families re-decided the idiom each time (class-attr constant,
``__init__`` parameter, or full contextual ``to_dict()``), producing the
divergence flagged in #1893.

:class:`StructuredError` is the minimal shared contract: a default
``error_code`` class attribute and a default :meth:`to_dict`. New error
families subclass it and override ``error_code``; families predating this
base adopt it on next touch (no big-bang migration).
"""

from __future__ import annotations

from typing import Any

__all__ = ["StructuredError"]


class StructuredError(RuntimeError):
    """Base for exceptions carrying a stable, machine-readable ``error_code``.

    Subclasses override ``error_code`` with a stable identifier so consumers
    branch on the typed value rather than substring-matching the message
    (NFR-007, #1893). :meth:`to_dict` returns a JSON-serializable envelope;
    subclasses that carry extra contextual fields override it and extend the
    base payload.
    """

    error_code: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation for tooling."""
        return {"error_code": self.error_code, "message": str(self)}
