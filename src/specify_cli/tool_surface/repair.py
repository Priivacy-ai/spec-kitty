"""Repair service for the tool surface contract bounded context.

:class:`SurfaceRepairService` accepts provider-owned :class:`SurfaceStatus`
objects (never reconstructs :class:`SurfaceInstance` from a finding) and
delegates the actual mutation to the provider that owns each surface kind. This
preserves the manifest/source/hash/refcount context the providers carry.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from .enums import SurfaceKind
from .findings import SurfaceFinding
from .providers.protocol import ReportingSurfaceProvider
from .status import SurfaceStatus, _surface_id


@dataclass(frozen=True)
class RepairResult:
    """Outcome of :meth:`SurfaceRepairService.repair`."""

    repaired: tuple[str, ...] = ()
    skipped: tuple[str, ...] = ()
    failed: tuple[str, ...] = ()
    dry_run: bool = False
    findings_after: tuple[SurfaceFinding, ...] = ()

    def to_json(self) -> dict[str, object]:
        """Serialize to a JSON-friendly mapping."""
        return {
            "repaired": list(self.repaired),
            "skipped": list(self.skipped),
            "failed": list(self.failed),
            "dry_run": self.dry_run,
            "findings_after": [f.to_json() for f in self.findings_after],
        }


@dataclass
class _RepairTally:
    """Mutable accumulator while folding per-status repair outcomes."""

    repaired: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)


class SurfaceRepairService:
    """Execute repair for a sequence of provider-owned statuses."""

    def __init__(self, providers: Sequence[ReportingSurfaceProvider]) -> None:
        self._providers = list(providers)

    def _provider_for(
        self, status: SurfaceStatus
    ) -> ReportingSurfaceProvider | None:
        for provider in self._providers:
            if provider.can_handle(status.instance.definition):
                return provider
        return None

    def repair(
        self,
        project_root: Path,
        statuses: Sequence[SurfaceStatus],
        *,
        kinds: set[SurfaceKind] | None = None,
        dry_run: bool = False,
    ) -> RepairResult:
        """Repair the supplied statuses, grouped by owning provider."""
        selected = self._select(statuses, kinds)
        tally = _RepairTally()
        grouped = self._group_by_provider(selected, tally)
        for provider, provider_statuses in grouped:
            self._apply(provider, project_root, provider_statuses, dry_run, tally)
        return RepairResult(
            repaired=tuple(tally.repaired),
            skipped=tuple(tally.skipped),
            failed=tuple(tally.failed),
            dry_run=dry_run,
        )

    @staticmethod
    def _select(
        statuses: Sequence[SurfaceStatus],
        kinds: set[SurfaceKind] | None,
    ) -> list[SurfaceStatus]:
        if kinds is None:
            return list(statuses)
        return [s for s in statuses if s.instance.definition.kind in kinds]

    def _group_by_provider(
        self,
        statuses: Sequence[SurfaceStatus],
        tally: _RepairTally,
    ) -> list[tuple[ReportingSurfaceProvider, list[SurfaceStatus]]]:
        """Bucket statuses by provider; record orphans as failures."""
        buckets: list[tuple[ReportingSurfaceProvider, list[SurfaceStatus]]] = []
        index: dict[int, list[SurfaceStatus]] = {}
        for status in statuses:
            provider = self._provider_for(status)
            if provider is None:
                tally.failed.append(_surface_id(status.instance))
                continue
            key = id(provider)
            if key not in index:
                index[key] = []
                buckets.append((provider, index[key]))
            index[key].append(status)
        return buckets

    @staticmethod
    def _apply(
        provider: ReportingSurfaceProvider,
        project_root: Path,
        statuses: list[SurfaceStatus],
        dry_run: bool,
        tally: _RepairTally,
    ) -> None:
        result = provider.repair(project_root, statuses, dry_run=dry_run)
        tally.repaired.extend(result.repaired)
        tally.skipped.extend(result.skipped)
        tally.failed.extend(result.failed)
