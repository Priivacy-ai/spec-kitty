"""Unit tests for ``tool_surface.providers._registry``.

Tests cover :class:`SurfaceRegistration`, :class:`SurfaceProviderRegistry`,
and :mod:`_discovery` (provider import tuple).  Each test that mutates
:data:`SurfaceProviderRegistry._registrations` uses ``monkeypatch`` to restore
the original state, preventing cross-test state leakage.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from specify_cli.tool_surface.enums import (
    ActivationMode,
    InstallScope,
    RequiredPolicy,
    SourceKind,
    ToolSurfaceKind,
)
from specify_cli.tool_surface.model import SurfaceDefinition, SurfaceInstance
from specify_cli.tool_surface.providers._registry import (
    SurfaceProviderRegistry,
    SurfaceRegistration,
)

if TYPE_CHECKING:
    from specify_cli.tool_surface.repair import RepairResult
    from specify_cli.tool_surface.status import SurfaceStatus

pytestmark = [pytest.mark.unit, pytest.mark.fast]


# ---------------------------------------------------------------------------
# Minimal stub provider implementations for tests
# ---------------------------------------------------------------------------


class _StubProvider:
    """Minimal provider that satisfies the ReportingSurfaceProvider protocol."""

    provider_key = "stub"

    def can_handle(self, definition: SurfaceDefinition) -> bool:
        return True

    def expand(
        self,
        definition: SurfaceDefinition,
        tool_key: str,
        project_root: Path,
    ) -> list[SurfaceInstance]:
        return []

    def probe(self, instance: SurfaceInstance) -> SurfaceStatus:  # type: ignore[return]
        ...

    def repair(
        self,
        project_root: Path,
        statuses: Sequence[SurfaceStatus],
        *,
        dry_run: bool = False,
    ) -> RepairResult:  # type: ignore[return]
        ...


class _AnotherStubProvider:
    """Second stub provider for multi-registration tests."""

    provider_key = "stub_two"

    def can_handle(self, definition: SurfaceDefinition) -> bool:
        return False

    def expand(
        self,
        definition: SurfaceDefinition,
        tool_key: str,
        project_root: Path,
    ) -> list[SurfaceInstance]:
        return []

    def probe(self, instance: SurfaceInstance) -> SurfaceStatus:  # type: ignore[return]
        ...

    def repair(
        self,
        project_root: Path,
        statuses: Sequence[SurfaceStatus],
        *,
        dry_run: bool = False,
    ) -> RepairResult:  # type: ignore[return]
        ...


def _make_definition(kind: ToolSurfaceKind = ToolSurfaceKind.COMMAND_SKILL) -> SurfaceDefinition:
    return SurfaceDefinition(
        kind=kind,
        source_kind=SourceKind.CHECKED_IN,
        install_scope=InstallScope.PROJECT,
        path_pattern=".kittify/{tool_key}.json",
        required_policy=RequiredPolicy.REQUIRED,
        activation_mode=ActivationMode.ALWAYS,
        provider_key="stub",
        repair_hint="run spec-kitty doctor tool-surfaces --fix",
    )


# ---------------------------------------------------------------------------
# SurfaceRegistration dataclass
# ---------------------------------------------------------------------------


def test_surface_registration_is_frozen() -> None:
    reg = SurfaceRegistration(
        provider_class=_StubProvider,
        definitions=(_make_definition(),),
        kind_tokens={"command-skill": ToolSurfaceKind.COMMAND_SKILL},
        order=0,
    )
    with pytest.raises(AttributeError):  # frozen dataclass raises FrozenInstanceError
        reg.order = 99  # type: ignore[misc]


def test_surface_registration_defaults() -> None:
    reg = SurfaceRegistration(
        provider_class=_StubProvider,
        definitions=(_make_definition(),),
        kind_tokens={},
    )
    assert reg.synthetic_key is None
    assert reg.order == 0


def test_surface_registration_with_synthetic_key() -> None:
    reg = SurfaceRegistration(
        provider_class=_StubProvider,
        definitions=(_make_definition(),),
        kind_tokens={"plugin-manifest": ToolSurfaceKind.PLUGIN_MANIFEST},
        synthetic_key="plugin_bundle",
        order=10,
    )
    assert reg.synthetic_key == "plugin_bundle"
    assert reg.order == 10


# ---------------------------------------------------------------------------
# SurfaceProviderRegistry — isolated (empty) state tests
# ---------------------------------------------------------------------------


def test_registry_empty_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(SurfaceProviderRegistry, "_registrations", [])
    assert SurfaceProviderRegistry.build_providers() == []
    assert SurfaceProviderRegistry.build_kind_tokens() == {}


def test_registry_register_single(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(SurfaceProviderRegistry, "_registrations", [])
    reg = SurfaceRegistration(
        provider_class=_StubProvider,
        definitions=(_make_definition(),),
        kind_tokens={"command-skill": ToolSurfaceKind.COMMAND_SKILL},
        order=0,
    )
    SurfaceProviderRegistry.register(reg)
    providers = SurfaceProviderRegistry.build_providers()
    assert len(providers) == 1
    assert isinstance(providers[0], _StubProvider)


def test_registry_duplicate_order_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(SurfaceProviderRegistry, "_registrations", [])
    reg1 = SurfaceRegistration(
        provider_class=_StubProvider,
        definitions=(),
        kind_tokens={},
        order=5,
    )
    reg2 = SurfaceRegistration(
        provider_class=_AnotherStubProvider,
        definitions=(),
        kind_tokens={},
        order=5,  # same order — should raise
    )
    SurfaceProviderRegistry.register(reg1)
    with pytest.raises(ValueError, match="Duplicate SurfaceRegistration order"):
        SurfaceProviderRegistry.register(reg2)


def test_registry_sorted_by_order(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(SurfaceProviderRegistry, "_registrations", [])
    reg_high = SurfaceRegistration(
        provider_class=_AnotherStubProvider,
        definitions=(),
        kind_tokens={},
        order=20,
    )
    reg_low = SurfaceRegistration(
        provider_class=_StubProvider,
        definitions=(),
        kind_tokens={},
        order=10,
    )
    SurfaceProviderRegistry.register(reg_high)
    SurfaceProviderRegistry.register(reg_low)
    providers = SurfaceProviderRegistry.build_providers()
    # Lower order comes first
    assert isinstance(providers[0], _StubProvider)
    assert isinstance(providers[1], _AnotherStubProvider)


def test_build_kind_tokens_merges_in_order(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(SurfaceProviderRegistry, "_registrations", [])
    reg1 = SurfaceRegistration(
        provider_class=_StubProvider,
        definitions=(),
        kind_tokens={"token-a": ToolSurfaceKind.COMMAND_SKILL, "token-b": ToolSurfaceKind.HOOK},
        order=1,
    )
    reg2 = SurfaceRegistration(
        provider_class=_AnotherStubProvider,
        definitions=(),
        kind_tokens={"token-b": ToolSurfaceKind.RULE, "token-c": ToolSurfaceKind.NATIVE_CONFIG},
        order=2,
    )
    SurfaceProviderRegistry.register(reg1)
    SurfaceProviderRegistry.register(reg2)
    tokens = SurfaceProviderRegistry.build_kind_tokens()
    assert tokens["token-a"] is ToolSurfaceKind.COMMAND_SKILL
    assert tokens["token-b"] is ToolSurfaceKind.RULE  # reg2 wins (higher order)
    assert tokens["token-c"] is ToolSurfaceKind.NATIVE_CONFIG


# ---------------------------------------------------------------------------
# build_registry — non-synthetic-key path (fan-out per tool_key)
# ---------------------------------------------------------------------------


def test_build_registry_fans_out_per_tool_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(SurfaceProviderRegistry, "_registrations", [])
    defn = _make_definition(ToolSurfaceKind.COMMAND_SKILL)
    reg = SurfaceRegistration(
        provider_class=_StubProvider,
        definitions=(defn,),
        kind_tokens={"command-skill": ToolSurfaceKind.COMMAND_SKILL},
        order=0,
    )
    SurfaceProviderRegistry.register(reg)
    registry = SurfaceProviderRegistry.build_registry(["codex", "claude"])
    assert defn in registry.get_definitions("codex")
    assert defn in registry.get_definitions("claude")


def test_build_registry_empty_tool_keys_skips_non_synthetic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(SurfaceProviderRegistry, "_registrations", [])
    defn = _make_definition()
    reg = SurfaceRegistration(
        provider_class=_StubProvider,
        definitions=(defn,),
        kind_tokens={},
        order=0,
    )
    SurfaceProviderRegistry.register(reg)
    # No tool_keys → nothing registered for standard providers
    registry = SurfaceProviderRegistry.build_registry([])
    assert registry.all_tool_keys() == []


# ---------------------------------------------------------------------------
# build_registry — synthetic-key path (unconditional, not gated on tool_keys)
# ---------------------------------------------------------------------------


def test_build_registry_synthetic_key_unconditional(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Providers with synthetic_key are registered regardless of tool_keys."""
    monkeypatch.setattr(SurfaceProviderRegistry, "_registrations", [])
    defn = _make_definition(ToolSurfaceKind.PLUGIN_MANIFEST)
    reg = SurfaceRegistration(
        provider_class=_StubProvider,
        definitions=(defn,),
        kind_tokens={},
        synthetic_key="plugin_bundle",
        order=0,
    )
    SurfaceProviderRegistry.register(reg)
    # Even with an empty tool_keys list the synthetic definition must appear.
    registry = SurfaceProviderRegistry.build_registry([])
    assert defn in registry.get_definitions("plugin_bundle")


def test_build_registry_synthetic_key_not_duplicated_per_tool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Synthetic-key providers are NOT fanned out per tool_key."""
    monkeypatch.setattr(SurfaceProviderRegistry, "_registrations", [])
    defn = _make_definition(ToolSurfaceKind.PLUGIN_MANIFEST)
    reg = SurfaceRegistration(
        provider_class=_StubProvider,
        definitions=(defn,),
        kind_tokens={},
        synthetic_key="plugin_bundle",
        order=0,
    )
    SurfaceProviderRegistry.register(reg)
    registry = SurfaceProviderRegistry.build_registry(["codex", "claude"])
    # The definition is under the synthetic key, not under each tool key.
    assert defn in registry.get_definitions("plugin_bundle")
    assert defn not in registry.get_definitions("codex")
    assert defn not in registry.get_definitions("claude")


def test_build_registry_mixed_providers(monkeypatch: pytest.MonkeyPatch) -> None:
    """Standard and synthetic providers coexist correctly."""
    monkeypatch.setattr(SurfaceProviderRegistry, "_registrations", [])
    std_defn = _make_definition(ToolSurfaceKind.COMMAND_SKILL)
    syn_defn = _make_definition(ToolSurfaceKind.PLUGIN_MANIFEST)
    std_reg = SurfaceRegistration(
        provider_class=_StubProvider,
        definitions=(std_defn,),
        kind_tokens={},
        order=0,
    )
    syn_reg = SurfaceRegistration(
        provider_class=_AnotherStubProvider,
        definitions=(syn_defn,),
        kind_tokens={},
        synthetic_key="plugin_bundle",
        order=1,
    )
    SurfaceProviderRegistry.register(std_reg)
    SurfaceProviderRegistry.register(syn_reg)
    registry = SurfaceProviderRegistry.build_registry(["codex"])
    assert std_defn in registry.get_definitions("codex")
    assert syn_defn in registry.get_definitions("plugin_bundle")
    assert syn_defn not in registry.get_definitions("codex")


# ---------------------------------------------------------------------------
# _discovery module
# ---------------------------------------------------------------------------


def test_discovery_providers_tuple_has_seven_entries() -> None:
    from specify_cli.tool_surface.providers._discovery import _PROVIDERS

    assert len(_PROVIDERS) == 7


def test_discovery_providers_are_distinct_modules() -> None:
    from specify_cli.tool_surface.providers._discovery import _PROVIDERS

    module_names = [p.__name__ for p in _PROVIDERS]
    assert len(module_names) == len(set(module_names)), "duplicate modules in _PROVIDERS"


def test_discovery_contains_expected_provider_modules() -> None:
    from specify_cli.tool_surface.providers import (
        agent_profiles,
        command_skills,
        managed_skills,
        native_config,
        plugin_bundle,
        session_presence,
        slash_commands,
    )
    from specify_cli.tool_surface.providers._discovery import _PROVIDERS

    expected = {
        agent_profiles,
        command_skills,
        managed_skills,
        native_config,
        plugin_bundle,
        session_presence,
        slash_commands,
    }
    assert set(_PROVIDERS) == expected
