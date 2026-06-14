"""Reporting-layer provider protocol for the tool surface contract.

This protocol describes the surface a provider exposes to
:class:`SurfaceStatusService` and :class:`SurfaceRepairService`: ``expand``
turns a :class:`SurfaceDefinition` into concrete :class:`SurfaceInstance`
objects, ``probe`` returns a :class:`SurfaceStatus`, and ``repair`` operates on
a sequence of provider-owned statuses and returns a :class:`RepairResult`.

Return types are imported only under ``TYPE_CHECKING`` to keep the status and
repair modules free of import cycles.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from ..model import SurfaceDefinition, SurfaceInstance

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ..repair import RepairResult
    from ..status import SurfaceStatus


@runtime_checkable
class ReportingSurfaceProvider(Protocol):
    """Provider contract consumed by the status and repair services."""

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

    def probe(self, instance: SurfaceInstance) -> SurfaceStatus:
        """Probe on-disk state and return a :class:`SurfaceStatus`."""
        ...

    def repair(
        self,
        project_root: Path,
        statuses: Sequence[SurfaceStatus],
        *,
        dry_run: bool = False,
    ) -> RepairResult:
        """Repair the supplied statuses and return a :class:`RepairResult`."""
        ...
