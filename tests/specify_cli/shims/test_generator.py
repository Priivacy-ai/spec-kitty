"""Tests for shims/generator.py — shim content and file generation."""

from __future__ import annotations

from pathlib import Path

from specify_cli.shims.generator import (
    AGENT_ARG_PLACEHOLDERS,
    generate_shim_content,
    generate_all_shims,
)
from specify_cli.shims.registry import CLI_DRIVEN_COMMANDS, CONSUMER_SKILLS, PROMPT_DRIVEN_COMMANDS


# ---------------------------------------------------------------------------
# generate_shim_content
# ---------------------------------------------------------------------------

class TestGenerateShimContent:
    def test_three_non_empty_components(self) -> None:
        content = generate_shim_content("implement", "claude", "$ARGUMENTS")
        lines = content.rstrip("\n").splitlines()
        # invariant line, prohibition line, blank, CLI call
        assert len(lines) == 4

    def test_first_line_invariant(self) -> None:
        content = generate_shim_content("implement", "claude", "$ARGUMENTS")
        first = content.splitlines()[0]
        assert first == "Run this exact command and treat its output as authoritative."

    def test_second_line_prohibition(self) -> None:
        content = generate_shim_content("implement", "claude", "$ARGUMENTS")
        second = content.splitlines()[1]
        assert second == "Do not rediscover context from branches, files, or prompt contents."

    def test_fourth_line_is_cli_call(self) -> None:
        content = generate_shim_content("implement", "claude", "$ARGUMENTS")
        fourth = content.splitlines()[3]
        assert "spec-kitty agent shim implement" in fourth
        assert "--agent claude" in fourth
        assert "--raw-args" in fourth
        assert "$ARGUMENTS" in fourth

    def test_arg_placeholder_substituted(self) -> None:
        content = generate_shim_content("review", "codex", "$PROMPT")
        assert "$PROMPT" in content
        assert "$ARGUMENTS" not in content

    def test_command_verb_in_cli_call(self) -> None:
        for skill in ["specify", "plan", "tasks", "implement", "review", "merge"]:
            content = generate_shim_content(skill, "claude", "$ARGUMENTS")
            assert f"spec-kitty agent shim {skill}" in content

    def test_agent_name_in_cli_call(self) -> None:
        for agent in ["claude", "codex", "opencode", "gemini"]:
            content = generate_shim_content("implement", agent, "$ARGUMENTS")
            assert f"--agent {agent}" in content

    def test_no_workflow_logic(self) -> None:
        """Shim must not contain workflow keywords like 'if', 'git', 'worktree'."""
        content = generate_shim_content("implement", "claude", "$ARGUMENTS")
        forbidden = ["worktree", "git checkout", "if [", "mkdir"]
        for token in forbidden:
            assert token not in content, f"Workflow logic leaked: {token!r}"


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

        # Only CLI-driven skills should get shim files — not prompt-driven ones
        written_names = {p.name for p in written}
        for skill in CLI_DRIVEN_COMMANDS:
            assert f"spec-kitty.{skill}.md" in written_names

    def test_prompt_driven_skills_not_written(self, tmp_path: Path) -> None:
        """Prompt-driven commands must NOT receive shim files."""
        _setup_kittify_config(tmp_path, ["claude"])
        (tmp_path / ".claude" / "commands").mkdir(parents=True)
        generate_all_shims(tmp_path)

        cmd_dir = tmp_path / ".claude" / "commands"
        for skill in PROMPT_DRIVEN_COMMANDS:
            assert not (cmd_dir / f"spec-kitty.{skill}.md").exists(), (
                f"Prompt-driven skill '{skill}' should not get a shim file"
            )

    def test_generates_exactly_seven_files_per_agent(self, tmp_path: Path) -> None:
        """generate_all_shims produces exactly 7 shim files per configured agent."""
        _setup_kittify_config(tmp_path, ["claude"])
        (tmp_path / ".claude" / "commands").mkdir(parents=True)
        written = generate_all_shims(tmp_path)
        assert len(written) == len(CLI_DRIVEN_COMMANDS)
        assert len(CLI_DRIVEN_COMMANDS) == 7

    def test_files_have_correct_content(self, tmp_path: Path) -> None:
        _setup_kittify_config(tmp_path, ["claude"])
        (tmp_path / ".claude" / "commands").mkdir(parents=True)
        generate_all_shims(tmp_path)

        impl_file = tmp_path / ".claude" / "commands" / "spec-kitty.implement.md"
        assert impl_file.exists()
        content = impl_file.read_text(encoding="utf-8")
        assert "Run this exact command and treat its output as authoritative." in content
        assert "Do not rediscover context" in content
        assert "spec-kitty agent shim implement" in content

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
        """Agents not in config.yaml should not get shim files."""
        _setup_kittify_config(tmp_path, ["claude"])
        # Pre-create a codex directory (orphaned)
        (tmp_path / ".codex" / "prompts").mkdir(parents=True)
        (tmp_path / ".claude" / "commands").mkdir(parents=True)

        generate_all_shims(tmp_path)

        # codex dir was pre-existing but NOT configured — no spec-kitty shims
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
