"""Unit tests for ``tool_surface.repair.SurfaceRepairService``."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from specify_cli.tool_surface.enums import (
    ActivationMode,
    InstallScope,
    RequiredPolicy,
    SourceKind,
    ToolSurfaceKind,
)
from specify_cli.tool_surface.model import SurfaceDefinition, SurfaceInstance
from specify_cli.tool_surface.repair import RepairResult, SurfaceRepairService
from specify_cli.tool_surface.status import STATE_MISSING, SurfaceStatus, _surface_id

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def _definition(kind: ToolSurfaceKind) -> SurfaceDefinition:
    return SurfaceDefinition(
        kind=kind,
        source_kind=SourceKind.GENERATED,
        install_scope=InstallScope.PROJECT,
        path_pattern="x/{command}",
        required_policy=RequiredPolicy.REPAIRABLE_REQUIRED,
        activation_mode=ActivationMode.ALWAYS,
        provider_key="p",
        repair_hint="fix",
    )


def _status(kind: ToolSurfaceKind, name: str) -> SurfaceStatus:
    inst = SurfaceInstance(
        definition=_definition(kind),
        path=Path("/proj") / name,
        exists=False,
        file_hash=None,
        owner="codex",
    )
    return SurfaceStatus(instance=inst, state=STATE_MISSING)


class _RecordingProvider:
    provider_key = "p"

    def __init__(self, kind: ToolSurfaceKind) -> None:
        self._kind = kind
        self.received: list[SurfaceStatus] = []

    def can_handle(self, definition: SurfaceDefinition) -> bool:
        return bool(definition.kind == self._kind)

    def expand(
        self, definition: SurfaceDefinition, tool_key: str, project_root: Path
    ) -> list[SurfaceInstance]:
        return []

    def probe(self, instance: SurfaceInstance) -> SurfaceStatus:
        return SurfaceStatus(instance=instance, state=STATE_MISSING)

    def repair(
        self,
        project_root: Path,
        statuses: Sequence[SurfaceStatus],
        *,
        dry_run: bool = False,
    ) -> RepairResult:
        self.received.extend(statuses)
        return RepairResult(
            repaired=tuple(_surface_id(s.instance) for s in statuses),
            dry_run=dry_run,
        )

    def remove(self, instance: SurfaceInstance) -> bool:
        return True


def test_no_provider_records_failure_not_raise() -> None:
    service = SurfaceRepairService([])
    result = service.repair(Path("/proj"), [_status(ToolSurfaceKind.COMMAND_SKILL, "a")])
    assert isinstance(result, RepairResult)
    assert len(result.failed) == 1
    assert result.repaired == ()


def test_delegates_to_provider() -> None:
    provider = _RecordingProvider(ToolSurfaceKind.COMMAND_SKILL)
    service = SurfaceRepairService([provider])
    status = _status(ToolSurfaceKind.COMMAND_SKILL, "a")
    result = service.repair(Path("/proj"), [status])
    assert provider.received == [status]
    assert len(result.repaired) == 1


def test_takes_status_objects_and_preserves_instance() -> None:
    provider = _RecordingProvider(ToolSurfaceKind.COMMAND_SKILL)
    service = SurfaceRepairService([provider])
    status = _status(ToolSurfaceKind.COMMAND_SKILL, "a")
    service.repair(Path("/proj"), [status])
    # The provider received the original SurfaceStatus, carrying its instance.
    assert provider.received[0].instance is status.instance


def test_kind_filter_selects_subset() -> None:
    provider = _RecordingProvider(ToolSurfaceKind.COMMAND_SKILL)
    service = SurfaceRepairService([provider])
    skill = _status(ToolSurfaceKind.COMMAND_SKILL, "a")
    other = _status(ToolSurfaceKind.COMMAND_FILE, "b")
    service.repair(Path("/proj"), [skill, other], kinds={ToolSurfaceKind.COMMAND_SKILL})
    assert provider.received == [skill]


def test_dry_run_passed_through() -> None:
    provider = _RecordingProvider(ToolSurfaceKind.COMMAND_SKILL)
    service = SurfaceRepairService([provider])
    result = service.repair(
        Path("/proj"), [_status(ToolSurfaceKind.COMMAND_SKILL, "a")], dry_run=True
    )
    assert result.dry_run is True
