"""Provider protocol for the tool surface contract bounded context.

A provider wraps an existing installer to expand, probe, repair, and remove one
surface kind for a given tool. This module defines the protocol all providers
must satisfy; concrete providers are added in later work packages.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from ..model import SurfaceDefinition, SurfaceInstance


@runtime_checkable
class AbstractSurfaceProvider(Protocol):
    """Protocol for surface providers.

    A provider wraps an existing installer to expand, probe, repair, and remove
    one surface kind for a given tool.
    """

    provider_key: str

    def can_handle(self, definition: SurfaceDefinition) -> bool:
        """Return whether this provider handles the given definition."""
        ...

    def expand(
        self,
        definition: SurfaceDefinition,
        tool_key: str,
        project_root: Path,
    ) -> list[SurfaceInstance]:
        """Expand a definition into concrete instances with real paths."""
        ...

    def probe(self, instance: SurfaceInstance) -> SurfaceInstance:
        """Re-check ``exists`` and ``file_hash`` for a known instance."""
        ...

    def repair(self, instance: SurfaceInstance) -> bool:
        """Run the underlying installer to create or restore the file."""
        ...

    def remove(self, instance: SurfaceInstance) -> bool:
        """Remove the materialized surface file."""
        ...
