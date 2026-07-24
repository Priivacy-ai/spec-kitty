"""Unit tests for the tool surface registry and provider protocol."""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.tool_surface.enums import (
    ActivationMode,
    InstallScope,
    RequiredPolicy,
    SourceKind,
    ToolSurfaceKind,
)
from specify_cli.tool_surface.model import SurfaceDefinition, SurfaceInstance
from specify_cli.tool_surface.providers.protocol import ReportingSurfaceProvider
from specify_cli.tool_surface.registry import ToolSurfaceRegistry

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def _definition(provider_key: str = "command-skill") -> SurfaceDefinition:
    return SurfaceDefinition(
        kind=ToolSurfaceKind.COMMAND_SKILL,
        source_kind=SourceKind.GENERATED,
        install_scope=InstallScope.PROJECT,
        path_pattern=".agents/skills/spec-kitty.{command}/SKILL.md",
        required_policy=RequiredPolicy.REQUIRED,
        activation_mode=ActivationMode.USER_INVOKED,
        provider_key=provider_key,
        repair_hint="run spec-kitty upgrade",
    )


def test_registry_starts_empty() -> None:
    registry = ToolSurfaceRegistry()
    assert registry.all_tool_keys() == []
    assert registry.get_definitions("claude") == []


def test_register_and_get_roundtrip() -> None:
    registry = ToolSurfaceRegistry()
    definition = _definition()
    registry.register_definition("claude", definition)
    assert registry.get_definitions("claude") == [definition]
    assert registry.all_tool_keys() == ["claude"]


def test_get_definitions_unknown_key_returns_empty_list() -> None:
    registry = ToolSurfaceRegistry()
    registry.register_definition("claude", _definition())
    assert registry.get_definitions("unknown") == []


def test_get_definitions_returns_copy() -> None:
    registry = ToolSurfaceRegistry()
    registry.register_definition("claude", _definition())
    returned = registry.get_definitions("claude")
    returned.clear()
    # Mutating the returned list must not affect registry state.
    assert registry.get_definitions("claude") == [_definition()]


def test_multiple_definitions_for_same_tool() -> None:
    registry = ToolSurfaceRegistry()
    first = _definition("command-skill")
    second = _definition("doctrine-skill")
    registry.register_definition("claude", first)
    registry.register_definition("claude", second)
    assert registry.get_definitions("claude") == [first, second]


class _StubProvider:
    """Minimal structural implementation of the provider protocol."""

    provider_key = "stub"

    def can_handle(self, definition: SurfaceDefinition) -> bool:
        return definition.provider_key == self.provider_key

    def expand(
        self,
        definition: SurfaceDefinition,
        tool_key: str,
        project_root: Path,
    ) -> list[SurfaceInstance]:
        return []

    def probe(self, instance: SurfaceInstance) -> object:
        return instance

    def repair(self, *args: object, **kwargs: object) -> object:
        return None


def test_provider_protocol_is_runtime_checkable() -> None:
    assert isinstance(_StubProvider(), ReportingSurfaceProvider)


def test_non_provider_fails_protocol_check() -> None:
    assert not isinstance(object(), ReportingSurfaceProvider)
