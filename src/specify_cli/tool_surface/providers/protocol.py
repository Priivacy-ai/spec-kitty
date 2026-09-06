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

from ..model import SurfaceDefinition, SurfaceInstance, SurfaceSelection

if TYPE_CHECKING:
    from collections.abc import Sequence
    from contextlib import AbstractContextManager

    from ..repair import RepairResult
    from ..status import SurfaceStatus
    from ..operations import ApplyConsent, AssessmentInputs, Diagnostic, OwnerApplyResult, OwnerAssessment


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


@runtime_checkable
class AssessingSurfaceProvider(Protocol):
    """Separate upgrade-capable contract; legacy reporting providers need not implement it.

    ``recheck`` acquires the owner's existing lock and compares the WHOLE batch's
    source/input/destination/parent observations before yielding diagnostics.
    The context remains held through ``apply``. Errors prohibit that batch's
    writer. ``apply`` consumes exact prepared bytes and reports actual IDs; it
    must never rerender/resample clocks or retry changed preconditions.
    """

    provider_key: str

    def assess(self, inputs: AssessmentInputs, statuses: Sequence[SurfaceStatus], *, selections: tuple[SurfaceSelection, ...]) -> OwnerAssessment:
        """Prepare effects using original statuses and canonical selected policies.

        Selections retain tool keys and definitions even for zero expansion.
        They come from the registry plans, never duplicated in opaque inputs.
        """
        ...

    def recheck(self, assessment: OwnerAssessment) -> AbstractContextManager[tuple[Diagnostic, ...]]:
        """Hold the owner lock while rechecking the complete batch and applying."""
        ...

    def apply(self, assessment: OwnerAssessment, explicit_consent: ApplyConsent) -> OwnerApplyResult:
        """Apply a rechecked, consent-permitted preparation using existing writers."""
        ...
