"""Agent config parsing and validation tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.core.agent_config import (
    AgentConfig,
    AgentConfigError,
    get_auto_commit_default,
    load_agent_config,
    save_agent_config,
)


def _write_config(tmp_path: Path, content: str) -> Path:
    kittify = tmp_path / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    config_file = kittify / "config.yaml"
    config_file.write_text(content, encoding="utf-8")
    return config_file


class TestCorruptYaml:
    def test_corrupt_yaml_clear_error(self, tmp_path: Path) -> None:
        """Corrupt YAML should produce parse error, not silent fallback."""
        _write_config(tmp_path, "invalid: yaml: content: [")

        with pytest.raises(AgentConfigError) as exc_info:
            load_agent_config(tmp_path)

        assert "Invalid YAML" in str(exc_info.value)
        assert "config.yaml" in str(exc_info.value)


class TestUnknownAgentKey:
    def test_unknown_agent_reported(self, tmp_path: Path) -> None:
        """Unknown agent key should be explicitly reported."""
        _write_config(tmp_path, "agents:\n  available:\n    - unknown_agent_xyz\n")

        with pytest.raises(AgentConfigError) as exc_info:
            load_agent_config(tmp_path)

        message = str(exc_info.value)
        assert "unknown_agent_xyz" in message
        assert "Valid agents" in message


class TestSaveAgentConfig:
    def test_save_agent_config_no_selection_block(self, tmp_path: Path) -> None:
        """Persisted agent config must not include a selection block."""
        config = AgentConfig(
            available=["claude", "codex"],
        )

        save_agent_config(tmp_path, config)
        content = (tmp_path / ".kittify" / "config.yaml").read_text(encoding="utf-8")

        assert "selection:" not in content
        assert "preferred_implementer" not in content
        assert "preferred_reviewer" not in content


class TestAutoCommitLoading:
    def test_loads_top_level_auto_commit_without_agents_section(self, tmp_path: Path) -> None:
        """Top-level auto_commit should still work when agents config is absent."""
        _write_config(tmp_path, "auto_commit: false\n")

        config = load_agent_config(tmp_path)

        assert config.auto_commit is False
        assert config.available == []
        assert get_auto_commit_default(tmp_path) is False

    def test_agents_auto_commit_overrides_top_level(self, tmp_path: Path) -> None:
        """agents.auto_commit should take precedence over the legacy top-level key."""
        _write_config(
            tmp_path,
            "auto_commit: false\nagents:\n  available: []\n  auto_commit: true\n",
        )

        config = load_agent_config(tmp_path)

        assert config.auto_commit is True


class TestToolsKeyFallback:
    def test_load_agent_config_tools_key(self, tmp_path: Path) -> None:
        """load_agent_config() reads from 'tools' key (post-m_2_0_1 migration)."""
        config_dir = tmp_path / ".kittify"
        config_dir.mkdir()
        (config_dir / "config.yaml").write_text(
            "tools:\n  available:\n    - opencode\n  auto_commit: false\n"
        )
        config = load_agent_config(tmp_path)
        assert config.available == ["opencode"]
        assert config.auto_commit is False

    def test_load_agent_config_agents_key_takes_precedence(self, tmp_path: Path) -> None:
        """'agents' key takes precedence over 'tools' key when both present."""
        _write_config(
            tmp_path,
            "agents:\n  available:\n    - claude\n  auto_commit: true\ntools:\n  available:\n    - opencode\n  auto_commit: false\n",
        )
        config = load_agent_config(tmp_path)
        assert config.available == ["claude"]
        assert config.auto_commit is True

    def test_load_agent_config_neither_key_returns_defaults(self, tmp_path: Path) -> None:
        """Config with neither 'agents' nor 'tools' key returns defaults."""
        _write_config(tmp_path, "vcs:\n  base_branch: main\n")
        config = load_agent_config(tmp_path)
        assert config.available == []
        assert config.auto_commit is True
