"""Tests for shims/models.py — ShimTemplate and AgentShimConfig."""

from __future__ import annotations

import pytest

from specify_cli.shims.models import AgentShimConfig, ShimTemplate


class TestShimTemplate:
    def test_creation(self) -> None:
        t = ShimTemplate(
            command_name="spec-kitty.implement",
            cli_command="spec-kitty agent shim implement",
            agent_name="claude",
            filename="spec-kitty.implement.md",
        )
        assert t.command_name == "spec-kitty.implement"
        assert t.cli_command == "spec-kitty agent shim implement"
        assert t.agent_name == "claude"
        assert t.filename == "spec-kitty.implement.md"

    def test_frozen(self) -> None:
        t = ShimTemplate(
            command_name="spec-kitty.plan",
            cli_command="spec-kitty agent shim plan",
            agent_name="codex",
            filename="spec-kitty.plan.md",
        )
        with pytest.raises((AttributeError, TypeError)):
            t.command_name = "changed"  # type: ignore[misc]

    def test_equality(self) -> None:
        a = ShimTemplate("x", "y", "z", "f.md")
        b = ShimTemplate("x", "y", "z", "f.md")
        assert a == b

    def test_hashable(self) -> None:
        t = ShimTemplate("a", "b", "c", "d.md")
        s: set[ShimTemplate] = {t}
        assert t in s


class TestAgentShimConfig:
    def _make_templates(self) -> tuple[ShimTemplate, ...]:
        return (
            ShimTemplate(
                "spec-kitty.implement",
                "spec-kitty agent shim implement",
                "claude",
                "spec-kitty.implement.md",
            ),
            ShimTemplate(
                "spec-kitty.review",
                "spec-kitty agent shim review",
                "claude",
                "spec-kitty.review.md",
            ),
        )

    def test_creation(self) -> None:
        templates = self._make_templates()
        cfg = AgentShimConfig(
            agent_key="claude",
            agent_dir=".claude",
            command_subdir="commands",
            templates=templates,
        )
        assert cfg.agent_key == "claude"
        assert cfg.agent_dir == ".claude"
        assert cfg.command_subdir == "commands"
        assert len(cfg.templates) == 2

    def test_frozen(self) -> None:
        cfg = AgentShimConfig("claude", ".claude", "commands", ())
        with pytest.raises((AttributeError, TypeError)):
            cfg.agent_key = "other"  # type: ignore[misc]

    def test_empty_templates(self) -> None:
        cfg = AgentShimConfig("opencode", ".opencode", "command", ())
        assert cfg.templates == ()

    def test_different_agents(self) -> None:
        for agent_key, agent_dir, subdir in [
            ("claude", ".claude", "commands"),
            ("codex", ".codex", "prompts"),
            ("opencode", ".opencode", "command"),
            ("windsurf", ".windsurf", "workflows"),
            ("q", ".amazonq", "prompts"),
        ]:
            cfg = AgentShimConfig(agent_key, agent_dir, subdir, ())
            assert cfg.agent_key == agent_key
            assert cfg.agent_dir == agent_dir
            assert cfg.command_subdir == subdir
