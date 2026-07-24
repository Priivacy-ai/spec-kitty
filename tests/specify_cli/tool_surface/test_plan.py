"""Unit tests for ``tool_surface.plan.SurfacePlanBuilder``."""

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
from specify_cli.tool_surface.plan import SurfacePlanBuilder
from specify_cli.tool_surface.registry import ToolSurfaceRegistry
from specify_cli.tool_surface.repair import RepairResult
from specify_cli.tool_surface.status import SurfaceStatus

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def _definition(kind: ToolSurfaceKind, provider_key: str) -> SurfaceDefinition:
    return SurfaceDefinition(
        kind=kind,
        source_kind=SourceKind.GENERATED,
        install_scope=InstallScope.PROJECT,
        path_pattern="x/{command}",
        required_policy=RequiredPolicy.REPAIRABLE_REQUIRED,
        activation_mode=ActivationMode.ALWAYS,
        provider_key=provider_key,
        repair_hint="fix it",
    )


class _FakeProvider:
    """Minimal reporting provider that emits one instance per expand call."""

    provider_key = "fake"

    def __init__(self, kind: ToolSurfaceKind) -> None:
        self._kind = kind

    def can_handle(self, definition: SurfaceDefinition) -> bool:
        return bool(definition.kind == self._kind)

    def expand(
        self,
        definition: SurfaceDefinition,
        tool_key: str,
        project_root: Path,
    ) -> list[SurfaceInstance]:
        return [
            SurfaceInstance(
                definition=definition,
                path=project_root / f"{tool_key}.txt",
                exists=False,
                file_hash=None,
                owner=tool_key,
            )
        ]

    def probe(self, instance: SurfaceInstance) -> SurfaceStatus:
        return SurfaceStatus(instance=instance, state="missing")

    def repair(
        self,
        project_root: Path,
        statuses: Sequence[SurfaceStatus],
        *,
        dry_run: bool = False,
    ) -> RepairResult:
        return RepairResult(dry_run=dry_run)

    def remove(self, instance: SurfaceInstance) -> bool:
        return True


def test_empty_plan_for_tool_with_no_definitions(tmp_path: Path) -> None:
    builder = SurfacePlanBuilder(ToolSurfaceRegistry(), [_FakeProvider(ToolSurfaceKind.COMMAND_SKILL)])
    plans = builder.build(["codex"], tmp_path)
    assert len(plans) == 1
    assert plans[0].tool_key == "codex"
    assert plans[0].instances == ()


def test_build_expands_definitions(tmp_path: Path) -> None:
    registry = ToolSurfaceRegistry()
    registry.register_definition("codex", _definition(ToolSurfaceKind.COMMAND_SKILL, "fake"))
    builder = SurfacePlanBuilder(registry, [_FakeProvider(ToolSurfaceKind.COMMAND_SKILL)])
    plans = builder.build(["codex"], tmp_path)
    assert len(plans[0].instances) == 1
    assert plans[0].instances[0].owner == "codex"


def test_kind_filter_excludes_other_kinds(tmp_path: Path) -> None:
    registry = ToolSurfaceRegistry()
    registry.register_definition("codex", _definition(ToolSurfaceKind.COMMAND_SKILL, "fake"))
    registry.register_definition("codex", _definition(ToolSurfaceKind.COMMAND_FILE, "other"))
    builder = SurfacePlanBuilder(registry, [_FakeProvider(ToolSurfaceKind.COMMAND_SKILL)])
    plans = builder.build(["codex"], tmp_path, ToolSurfaceKind.COMMAND_FILE)
    # Filter keeps only COMMAND_FILE definitions, but no provider handles them.
    assert plans[0].instances == ()


def test_no_provider_yields_no_instances(tmp_path: Path) -> None:
    registry = ToolSurfaceRegistry()
    registry.register_definition("codex", _definition(ToolSurfaceKind.AGENT_PROFILE, "none"))
    builder = SurfacePlanBuilder(registry, [_FakeProvider(ToolSurfaceKind.COMMAND_SKILL)])
    plans = builder.build(["codex"], tmp_path)
    assert plans[0].instances == ()
