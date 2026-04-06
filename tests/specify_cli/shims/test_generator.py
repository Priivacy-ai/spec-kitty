"""Tests for shims/generator.py -- direct canonical command generation."""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.shims.generator import (
    AGENT_ARG_PLACEHOLDERS,
    _canonical_command,
    generate_shim_content,
    generate_all_shims,
)
from specify_cli.shims.registry import CLI_DRIVEN_COMMANDS, CONSUMER_SKILLS, PROMPT_DRIVEN_COMMANDS


# ---------------------------------------------------------------------------
# _canonical_command
# ---------------------------------------------------------------------------

class TestCanonicalCommand:
    def test_implement(self) -> None:
        cmd = _canonical_command("implement", "claude", "$ARGUMENTS")
        assert cmd == "spec-kitty agent action implement $ARGUMENTS --agent claude"

    def test_review(self) -> None:
        cmd = _canonical_command("review", "codex", "$PROMPT")
        assert cmd == "spec-kitty agent action review $PROMPT --agent codex"

    def test_accept(self) -> None:
        cmd = _canonical_command("accept", "claude", "$ARGUMENTS")
        assert cmd == "spec-kitty agent mission accept $ARGUMENTS"

    def test_status(self) -> None:
        cmd = _canonical_command("status", "claude", "$ARGUMENTS")
        assert cmd == "spec-kitty agent tasks status $ARGUMENTS"

    def test_merge(self) -> None:
        cmd = _canonical_command("merge", "claude", "$ARGUMENTS")
        assert cmd == "spec-kitty merge $ARGUMENTS"

    def test_dashboard(self) -> None:
        cmd = _canonical_command("dashboard", "claude", "$ARGUMENTS")
        assert cmd == "spec-kitty dashboard $ARGUMENTS"

    def test_tasks_finalize(self) -> None:
        cmd = _canonical_command("tasks-finalize", "claude", "$ARGUMENTS")
        assert cmd == "spec-kitty agent mission finalize-tasks $ARGUMENTS"

    def test_unknown_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Unknown CLI-driven command"):
            _canonical_command("nonexistent", "claude", "$ARGUMENTS")

    def test_all_cli_driven_commands_mapped(self) -> None:
        """Every command in CLI_DRIVEN_COMMANDS must have a canonical mapping."""
        for cmd in CLI_DRIVEN_COMMANDS:
            result = _canonical_command(cmd, "claude", "$ARGUMENTS")
            assert "spec-kitty" in result


# ---------------------------------------------------------------------------
# generate_shim_content
# ---------------------------------------------------------------------------

class TestGenerateShimContent:
    def test_three_non_empty_components(self) -> None:
        content = generate_shim_content("implement", "claude", "$ARGUMENTS")
        lines = content.rstrip("\n").splitlines()
        # version marker, invariant line, prohibition line, mission hint, blank, CLI call
        assert len(lines) == 6

    def test_first_line_invariant(self) -> None:
        content = generate_shim_content("implement", "claude", "$ARGUMENTS")
        # Line 0 is the version marker; invariant is on line 1
        first = content.splitlines()[1]
        assert first == "Run this exact command and treat its output as authoritative."

    def test_second_line_prohibition(self) -> None:
        content = generate_shim_content("implement", "claude", "$ARGUMENTS")
        # Line 0 is the version marker; prohibition is on line 2
        second = content.splitlines()[2]
        assert second == "Do not rediscover context from branches, files, or prompt contents."

    def test_direct_implement_command(self) -> None:
        content = generate_shim_content("implement", "claude", "$ARGUMENTS")
        assert "spec-kitty agent action implement $ARGUMENTS --agent claude" in content

    def test_direct_review_command(self) -> None:
        content = generate_shim_content("review", "codex", "$PROMPT")
        assert "spec-kitty agent action review $PROMPT --agent codex" in content

    def test_direct_accept_command(self) -> None:
        content = generate_shim_content("accept", "claude", "$ARGUMENTS")
        assert "spec-kitty agent mission accept $ARGUMENTS" in content

    def test_no_shim_dispatch(self) -> None:
        """Generated content must NOT reference the old shim dispatch path."""
        for cmd in CLI_DRIVEN_COMMANDS:
            content = generate_shim_content(cmd, "claude", "$ARGUMENTS")
            assert "agent shim" not in content

    def test_arg_placeholder_substituted(self) -> None:
        content = generate_shim_content("review", "codex", "$PROMPT")
        assert "$PROMPT" in content
        assert "$ARGUMENTS" not in content

    def test_agent_name_in_implement_review(self) -> None:
        for agent in ["claude", "codex", "opencode", "gemini"]:
            content = generate_shim_content("implement", agent, "$ARGUMENTS")
            assert f"--agent {agent}" in content

    def test_no_workflow_logic(self) -> None:
        """Command files must not contain workflow keywords."""
        content = generate_shim_content("implement", "claude", "$ARGUMENTS")
        forbidden = ["worktree", "git checkout", "if [", "mkdir"]
        for token in forbidden:
            assert token not in content, f"Workflow logic leaked: {token!r}"

    def test_shim_content_mentions_mission(self) -> None:
        content = generate_shim_content("status", "claude", "$ARGUMENTS")
        assert "--mission" in content

    def test_shim_content_mission_hint_line(self) -> None:
        content = generate_shim_content("implement", "claude", "$ARGUMENTS")
        lines = content.splitlines()
        assert lines[3] == "In repos with multiple missions, pass --mission <slug> in your arguments."

    def test_shim_content_version_marker_still_first(self) -> None:
        content = generate_shim_content("implement", "claude", "$ARGUMENTS")
        assert content.splitlines()[0].startswith("<!-- spec-kitty-command-version:")


# ---------------------------------------------------------------------------
# Agent-specific placeholder mapping
# ---------------------------------------------------------------------------

class TestAgentArgPlaceholders:
    def test_claude_uses_arguments(self) -> None:
        assert AGENT_ARG_PLACEHOLDERS["claude"] == "$ARGUMENTS"

    def test_codex_uses_prompt(self) -> None:
        assert AGENT_ARG_PLACEHOLDERS["codex"] == "$PROMPT"

    def test_claude_content_has_arguments(self) -> None:
        content = generate_shim_content("implement", "claude", AGENT_ARG_PLACEHOLDERS["claude"])
        assert "$ARGUMENTS" in content

    def test_codex_content_has_prompt(self) -> None:
        content = generate_shim_content("implement", "codex", AGENT_ARG_PLACEHOLDERS["codex"])
        assert "$PROMPT" in content


# ---------------------------------------------------------------------------
# generate_all_shims (filesystem)
# ---------------------------------------------------------------------------

def _setup_kittify_config(tmp_path: Path, agents: list[str]) -> None:
    """Write a minimal .kittify/config.yaml selecting specific agents."""
    kittify = tmp_path / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    available_lines = "\n".join(f"    - {a}" for a in agents)
    (kittify / "config.yaml").write_text(
        f"project:\n  uuid: test-uuid-1234\nagents:\n  available:\n{available_lines}\n",
        encoding="utf-8",
    )


class TestGenerateAllShims:
    def test_returns_list_of_paths(self, tmp_path: Path) -> None:
        _setup_kittify_config(tmp_path, ["claude"])
        (tmp_path / ".claude" / "commands").mkdir(parents=True)
        result = generate_all_shims(tmp_path)
        assert isinstance(result, list)
        assert all(isinstance(p, Path) for p in result)

    def test_creates_files_for_configured_agents(self, tmp_path: Path) -> None:
        _setup_kittify_config(tmp_path, ["claude", "codex"])
        (tmp_path / ".claude" / "commands").mkdir(parents=True)
        (tmp_path / ".codex" / "prompts").mkdir(parents=True)

        written = generate_all_shims(tmp_path)

        # Only CLI-driven skills should get command files
        written_names = {p.name for p in written}
        for skill in CLI_DRIVEN_COMMANDS:
            assert f"spec-kitty.{skill}.md" in written_names

    def test_prompt_driven_skills_not_written(self, tmp_path: Path) -> None:
        """Prompt-driven commands must NOT receive command files."""
        _setup_kittify_config(tmp_path, ["claude"])
        (tmp_path / ".claude" / "commands").mkdir(parents=True)
        generate_all_shims(tmp_path)

        cmd_dir = tmp_path / ".claude" / "commands"
        for skill in PROMPT_DRIVEN_COMMANDS:
            assert not (cmd_dir / f"spec-kitty.{skill}.md").exists(), (
                f"Prompt-driven skill '{skill}' should not get a command file"
            )

    def test_generates_exactly_seven_files_per_agent(self, tmp_path: Path) -> None:
        _setup_kittify_config(tmp_path, ["claude"])
        (tmp_path / ".claude" / "commands").mkdir(parents=True)
        written = generate_all_shims(tmp_path)
        assert len(written) == len(CLI_DRIVEN_COMMANDS)
        assert len(CLI_DRIVEN_COMMANDS) == 7

    def test_files_have_direct_commands(self, tmp_path: Path) -> None:
        _setup_kittify_config(tmp_path, ["claude"])
        (tmp_path / ".claude" / "commands").mkdir(parents=True)
        generate_all_shims(tmp_path)

        impl_file = tmp_path / ".claude" / "commands" / "spec-kitty.implement.md"
        assert impl_file.exists()
        content = impl_file.read_text(encoding="utf-8")
        assert "Run this exact command and treat its output as authoritative." in content
        assert "Do not rediscover context" in content
        assert "spec-kitty agent action implement" in content
        assert "agent shim" not in content

    def test_correct_placeholder_per_agent(self, tmp_path: Path) -> None:
        _setup_kittify_config(tmp_path, ["claude", "codex"])
        (tmp_path / ".claude" / "commands").mkdir(parents=True)
        (tmp_path / ".codex" / "prompts").mkdir(parents=True)
        generate_all_shims(tmp_path)

        claude_file = tmp_path / ".claude" / "commands" / "spec-kitty.implement.md"
        codex_file = tmp_path / ".codex" / "prompts" / "spec-kitty.implement.md"

        assert "$ARGUMENTS" in claude_file.read_text()
        assert "$PROMPT" in codex_file.read_text()

    def test_result_is_sorted(self, tmp_path: Path) -> None:
        _setup_kittify_config(tmp_path, ["claude"])
        (tmp_path / ".claude" / "commands").mkdir(parents=True)
        result = generate_all_shims(tmp_path)
        assert result == sorted(result)

    def test_unconfigured_agent_not_written(self, tmp_path: Path) -> None:
        _setup_kittify_config(tmp_path, ["claude"])
        (tmp_path / ".codex" / "prompts").mkdir(parents=True)
        (tmp_path / ".claude" / "commands").mkdir(parents=True)

        generate_all_shims(tmp_path)

        codex_impl = tmp_path / ".codex" / "prompts" / "spec-kitty.implement.md"
        assert not codex_impl.exists()

    def test_existing_files_overwritten(self, tmp_path: Path) -> None:
        _setup_kittify_config(tmp_path, ["claude"])
        cmd_dir = tmp_path / ".claude" / "commands"
        cmd_dir.mkdir(parents=True)
        target = cmd_dir / "spec-kitty.implement.md"
        target.write_text("old content", encoding="utf-8")

        generate_all_shims(tmp_path)

        assert target.read_text(encoding="utf-8") != "old content"

    def test_opencode_uses_command_subdir(self, tmp_path: Path) -> None:
        _setup_kittify_config(tmp_path, ["opencode"])
        (tmp_path / ".opencode" / "command").mkdir(parents=True)
        generate_all_shims(tmp_path)

        impl_file = tmp_path / ".opencode" / "command" / "spec-kitty.implement.md"
        assert impl_file.exists()

    def test_windsurf_uses_workflows_subdir(self, tmp_path: Path) -> None:
        _setup_kittify_config(tmp_path, ["windsurf"])
        (tmp_path / ".windsurf" / "workflows").mkdir(parents=True)
        generate_all_shims(tmp_path)

        impl_file = tmp_path / ".windsurf" / "workflows" / "spec-kitty.implement.md"
        assert impl_file.exists()

    def test_internal_skills_not_written(self, tmp_path: Path) -> None:
        _setup_kittify_config(tmp_path, ["claude"])
        (tmp_path / ".claude" / "commands").mkdir(parents=True)
        generate_all_shims(tmp_path)

        cmd_dir = tmp_path / ".claude" / "commands"
        for internal_skill in ["doctor", "materialize", "debug"]:
            assert not (cmd_dir / f"spec-kitty.{internal_skill}.md").exists()
