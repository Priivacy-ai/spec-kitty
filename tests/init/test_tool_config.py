"""Tests for specify_cli.core.tool_config (renamed from agent_config).

Covers:
- New import paths work correctly
- Old import paths (agent_config shim) work with DeprecationWarning
- AgentConfig is ToolConfig (same class via alias)
- Functionality is unchanged
"""

from __future__ import annotations

import warnings
from pathlib import Path

import pytest

from specify_cli.core.tool_config import (
    ToolConfig,
    ToolConfigError,
    ToolSelectionConfig,
    get_configured_tools,
    load_tool_config,
    save_tool_config,
)
pytestmark = pytest.mark.fast



# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_config(tmp_path: Path, content: str) -> Path:
    kittify = tmp_path / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    config_file = kittify / "config.yaml"
    config_file.write_text(content, encoding="utf-8")
    return config_file


# ---------------------------------------------------------------------------
# New import path tests
# ---------------------------------------------------------------------------


class TestNewImportPaths:
    """Verify that the new tool_config module exports all expected symbols."""

    def test_tool_config_importable(self) -> None:
        assert ToolConfig is not None

    def test_tool_selection_config_importable(self) -> None:
        assert ToolSelectionConfig is not None

    def test_tool_config_error_importable(self) -> None:
        assert ToolConfigError is not None

    def test_load_tool_config_importable(self) -> None:
        assert callable(load_tool_config)

    def test_save_tool_config_importable(self) -> None:
        assert callable(save_tool_config)

    def test_get_configured_tools_importable(self) -> None:
        assert callable(get_configured_tools)


# ---------------------------------------------------------------------------
# Deprecation shim tests
# ---------------------------------------------------------------------------


class TestDeprecationShim:
    """Verify that the old agent_config module re-exports everything with a warning."""

    def test_old_import_emits_deprecation_warning(self) -> None:
        """Importing agent_config should emit a DeprecationWarning."""
        # Force a reimport to trigger the module-level warning.
        import sys

        # Remove from sys.modules to force re-execution of the module body.
        sys.modules.pop("specify_cli.core.agent_config", None)

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            import specify_cli.core.agent_config  # noqa: F401

        deprecation_warnings = [
            w for w in caught if issubclass(w.category, DeprecationWarning)
        ]
        assert deprecation_warnings, "Expected at least one DeprecationWarning"
        assert any(
            "specify_cli.core.agent_config" in str(w.message) for w in deprecation_warnings
        )

    def test_agent_config_is_tool_config(self) -> None:
        """AgentConfig from the shim must be the same class as ToolConfig."""
        import sys

        sys.modules.pop("specify_cli.core.agent_config", None)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from specify_cli.core.agent_config import AgentConfig

        assert AgentConfig is ToolConfig

    def test_agent_selection_config_is_tool_selection_config(self) -> None:
        """AgentSelectionConfig from the shim must equal ToolSelectionConfig."""
        import sys

        sys.modules.pop("specify_cli.core.agent_config", None)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from specify_cli.core.agent_config import AgentSelectionConfig

        assert AgentSelectionConfig is ToolSelectionConfig

    def test_agent_config_error_is_tool_config_error(self) -> None:
        """AgentConfigError from the shim must equal ToolConfigError."""
        import sys

        sys.modules.pop("specify_cli.core.agent_config", None)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from specify_cli.core.agent_config import AgentConfigError

        assert AgentConfigError is ToolConfigError

    def test_load_agent_config_is_load_tool_config(self) -> None:
        """load_agent_config from the shim must be the same callable as load_tool_config."""
        import sys

        sys.modules.pop("specify_cli.core.agent_config", None)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from specify_cli.core.agent_config import load_agent_config

        assert load_agent_config is load_tool_config

    def test_save_agent_config_is_save_tool_config(self) -> None:
        """save_agent_config from the shim must be the same callable as save_tool_config."""
        import sys

        sys.modules.pop("specify_cli.core.agent_config", None)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from specify_cli.core.agent_config import save_agent_config

        assert save_agent_config is save_tool_config

    def test_get_configured_agents_is_get_configured_tools(self) -> None:
        """get_configured_agents from the shim must be the same callable as get_configured_tools."""
        import sys

        sys.modules.pop("specify_cli.core.agent_config", None)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from specify_cli.core.agent_config import get_configured_agents


        assert get_configured_agents is get_configured_tools


# ---------------------------------------------------------------------------
# Functional tests (via new names)
# ---------------------------------------------------------------------------


class TestToolConfigDefaults:
    def test_default_instance_has_empty_available(self) -> None:
        config = ToolConfig()
        assert config.available == []

    def test_default_selection_has_no_preferences(self) -> None:
        config = ToolConfig()
        assert config.selection.preferred_implementer is None
        assert config.selection.preferred_reviewer is None


class TestLoadToolConfig:
    def test_returns_empty_config_when_no_config_file(self, tmp_path: Path) -> None:
        config = load_tool_config(tmp_path)
        assert isinstance(config, ToolConfig)
        assert config.available == []

    def test_loads_available_tools(self, tmp_path: Path) -> None:
        _write_config(tmp_path, "tools:\n  available:\n    - claude\n    - codex\n")
        config = load_tool_config(tmp_path)
        assert config.available == ["claude", "codex"]

    def test_loads_selection_preferences_from_tools_key(self, tmp_path: Path) -> None:
        _write_config(
            tmp_path,
            "tools:\n  available:\n    - claude\n    - codex\n"
            "  selection:\n    preferred_implementer: claude\n    preferred_reviewer: codex\n",
        )
        config = load_tool_config(tmp_path)
        assert config.selection.preferred_implementer == "claude"
        assert config.selection.preferred_reviewer == "codex"

    def test_loads_legacy_agents_key_with_deprecation_warning(self, tmp_path: Path) -> None:
        _write_config(tmp_path, "agents:\n  available:\n    - claude\n")
        with pytest.deprecated_call(match="deprecated"):
            config = load_tool_config(tmp_path)
        assert config.available == ["claude"]

    def test_raises_tool_config_error_on_corrupt_yaml(self, tmp_path: Path) -> None:
        _write_config(tmp_path, "invalid: yaml: [unterminated")
        with pytest.raises(ToolConfigError) as exc_info:
            load_tool_config(tmp_path)
        assert "Invalid YAML" in str(exc_info.value)

    def test_raises_tool_config_error_on_unknown_agent(self, tmp_path: Path) -> None:
        _write_config(tmp_path, "tools:\n  available:\n    - nonexistent_agent_xyz\n")
        with pytest.raises(ToolConfigError) as exc_info:
            load_tool_config(tmp_path)
        assert "nonexistent_agent_xyz" in str(exc_info.value)
        assert "Valid agents" in str(exc_info.value)


class TestSaveToolConfig:
    def test_saves_and_reloads(self, tmp_path: Path) -> None:
        config = ToolConfig(
            available=["claude", "codex"],
            selection=ToolSelectionConfig(
                preferred_implementer="claude",
                preferred_reviewer="codex",
            ),
        )
        save_tool_config(tmp_path, config)
        reloaded = load_tool_config(tmp_path)
        assert reloaded.available == ["claude", "codex"]
        assert reloaded.selection.preferred_implementer == "claude"
        assert reloaded.selection.preferred_reviewer == "codex"

    def test_does_not_persist_strategy_field(self, tmp_path: Path) -> None:
        config = ToolConfig(
            available=["claude"],
            selection=ToolSelectionConfig(preferred_implementer="claude"),
        )
        save_tool_config(tmp_path, config)
        content = (tmp_path / ".kittify" / "config.yaml").read_text(encoding="utf-8")
        assert "strategy:" not in content

    def test_preserves_other_config_sections(self, tmp_path: Path) -> None:
        """save_tool_config should not clobber unrelated config sections."""
        _write_config(tmp_path, "vcs:\n  type: git\n")
        config = ToolConfig(available=["claude"])
        save_tool_config(tmp_path, config)
        content = (tmp_path / ".kittify" / "config.yaml").read_text(encoding="utf-8")
        assert "vcs:" in content
        assert "git" in content

    def test_uses_tools_yaml_key(self, tmp_path: Path) -> None:
        """YAML key should be canonicalized to 'tools'."""
        config = ToolConfig(available=["claude"])
        save_tool_config(tmp_path, config)
        content = (tmp_path / ".kittify" / "config.yaml").read_text(encoding="utf-8")
        assert "tools:" in content
        assert "agents:" not in content

    def test_save_removes_legacy_agents_key(self, tmp_path: Path) -> None:
        _write_config(tmp_path, "agents:\n  available:\n    - codex\nvcs:\n  type: git\n")
        save_tool_config(tmp_path, ToolConfig(available=["claude"]))
        content = (tmp_path / ".kittify" / "config.yaml").read_text(encoding="utf-8")
        assert "tools:" in content
        assert "agents:" not in content
        assert "vcs:" in content


class TestGetConfiguredTools:
    def test_returns_empty_list_when_no_config(self, tmp_path: Path) -> None:
        tools = get_configured_tools(tmp_path)
        assert tools == []

    def test_returns_configured_tools(self, tmp_path: Path) -> None:
        _write_config(tmp_path, "tools:\n  available:\n    - claude\n    - gemini\n")
        tools = get_configured_tools(tmp_path)
        assert tools == ["claude", "gemini"]


class TestToolConfigSelectMethods:
    def test_select_implementer_returns_preferred(self) -> None:
        config = ToolConfig(
            available=["claude", "codex"],
            selection=ToolSelectionConfig(preferred_implementer="codex"),
        )
        assert config.select_implementer() == "codex"

    def test_select_implementer_falls_back_to_first(self) -> None:
        config = ToolConfig(available=["claude", "codex"])
        assert config.select_implementer() == "claude"

    def test_select_implementer_excludes_specified(self) -> None:
        config = ToolConfig(available=["claude", "codex"])
        result = config.select_implementer(exclude="claude")
        assert result == "codex"

    def test_select_implementer_returns_none_when_empty(self) -> None:
        config = ToolConfig(available=[])
        assert config.select_implementer() is None

    def test_select_reviewer_prefers_different_from_implementer(self) -> None:
        config = ToolConfig(available=["claude", "codex"])
        result = config.select_reviewer(implementer="claude")
        assert result == "codex"

    def test_select_reviewer_falls_back_to_same_when_only_one(self) -> None:
        config = ToolConfig(available=["claude"])
        result = config.select_reviewer(implementer="claude")
        assert result == "claude"

    def test_select_reviewer_returns_none_when_empty(self) -> None:
        config = ToolConfig(available=[])
        assert config.select_reviewer() is None
