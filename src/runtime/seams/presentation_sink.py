"""PresentationSink — runtime output abstraction (FR-013).

Runtime surfaces output through this Protocol; CLI adapters inject
a Rich-backed implementation. Runtime must never import rich.* directly.
"""
from __future__ import annotations
from typing import Protocol, runtime_checkable


@runtime_checkable
class PresentationSink(Protocol):
    """Abstract output surface injected into runtime services."""

    def write_line(self, text: str) -> None:
        """Emit a single line of text output."""
        ...

    def write_status(self, message: str) -> None:
        """Emit a transient status message (e.g. spinner label)."""
        ...

    def write_json(self, data: object) -> None:
        """Emit structured JSON output (for --json mode)."""
        ...
