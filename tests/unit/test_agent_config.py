"""Agent config parsing and validation tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.core.agent_config import (
    AgentConfig,
    AgentConfigError,
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


class TestRolePreferenceRemoval:
    def test_save_agent_config_only_persists_available_agents(self, tmp_path: Path) -> None:
        """Persisted agent config should only include agents.available."""
        config = AgentConfig(available=["claude", "codex"])

        save_agent_config(tmp_path, config)
        content = (tmp_path / ".kittify" / "config.yaml").read_text(encoding="utf-8")

        assert "strategy:" not in content
        assert "selection:" not in content
        assert "available:" in content
