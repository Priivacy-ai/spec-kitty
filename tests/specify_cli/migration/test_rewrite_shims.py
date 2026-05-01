"""Tests for migration/rewrite_shims.py — Subtask T063.

Covers:
- T063-1: All 16 command files generated (7 CLI shims + 9 prompt templates)
- T063-2: Old template content is gone after rewrite
- T063-3: Stale spec-kitty.*.md files not in generated set are deleted
- T063-4: RewriteResult reports correct counts
- T063-5: Works when agent directories already have correct shims (idempotent)
"""

from __future__ import annotations

from pathlib import Path


from specify_cli.migration.rewrite_shims import RewriteResult, rewrite_agent_shims


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _setup_project(tmp_path: Path, agents: list[str] | None = None) -> None:
    """Create a minimal project with .kittify/config.yaml and agent directories."""
    if agents is None:
        agents = ["claude", "codex"]

    kittify = tmp_path / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)

    # Write config.yaml with specified agents
    config_lines = ["agents:\n", "  available:\n"]
    for agent in agents:
        config_lines.append(f"  - {agent}\n")
    (kittify / "config.yaml").write_text("".join(config_lines))


def _get_claude_cmd_dir(tmp_path: Path) -> Path:
    return tmp_path / ".claude" / "commands"


def _get_codex_cmd_dir(tmp_path: Path) -> Path:
    return tmp_path / ".codex" / "prompts"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRewriteAgentShims:
    def test_all_commands_written(self, tmp_path: Path) -> None:
        """T063-1: All 16 command files are created for each configured agent."""
        from specify_cli.shims.registry import CONSUMER_SKILLS

        _setup_project(tmp_path, agents=["claude"])
        result = rewrite_agent_shims(tmp_path)
        assert isinstance(result, RewriteResult)

        claude_dir = _get_claude_cmd_dir(tmp_path)
        command_files = list(claude_dir.glob("spec-kitty.*.md"))
        assert len(command_files) == len(CONSUMER_SKILLS), f"Expected {len(CONSUMER_SKILLS)} command files, got {len(command_files)}"

    def test_cli_shim_content_is_thin(self, tmp_path: Path) -> None:
        """T063-1: CLI-driven shim files have the canonical 3-line format."""
        from specify_cli.shims.registry import CLI_DRIVEN_COMMANDS

        _setup_project(tmp_path, agents=["claude"])
        rewrite_agent_shims(tmp_path)

        claude_dir = _get_claude_cmd_dir(tmp_path)
        for command in CLI_DRIVEN_COMMANDS:
            shim_file = claude_dir / f"spec-kitty.{command}.md"
            assert shim_file.exists(), f"CLI shim missing: {command}"
            content = shim_file.read_text()
            assert "spec-kitty" in content
            assert "agent shim" not in content

    def test_prompt_templates_are_full(self, tmp_path: Path) -> None:
        """T063-1: Prompt-driven command files are full templates, not thin shims."""
        from specify_cli.shims.registry import PROMPT_DRIVEN_COMMANDS

        _setup_project(tmp_path, agents=["claude"])
        rewrite_agent_shims(tmp_path)

        claude_dir = _get_claude_cmd_dir(tmp_path)
        for command in PROMPT_DRIVEN_COMMANDS:
            template_file = claude_dir / f"spec-kitty.{command}.md"
            assert template_file.exists(), f"Prompt template missing: {command}"
            content = template_file.read_text()
            # Prompt templates should NOT contain the shim marker
            assert "spec-kitty agent shim" not in content
            # They should be substantial (not thin)
            lines = [l for l in content.splitlines() if l.strip()]
            assert len(lines) > 10, f"Prompt template {command} too short ({len(lines)} lines)"

    def test_stale_files_deleted(self, tmp_path: Path) -> None:
        """T063-3: Legacy workflow files not in generated set are removed."""
        _setup_project(tmp_path, agents=["claude"])

        claude_dir = _get_claude_cmd_dir(tmp_path)
        claude_dir.mkdir(parents=True, exist_ok=True)

        # Write a stale workflow file
        stale = claude_dir / "spec-kitty.old-workflow.md"
        stale.write_text("# Old lengthy workflow\n\nThis is old content.\n")

        result = rewrite_agent_shims(tmp_path)
        assert not stale.exists(), "Stale file should have been deleted"
        assert stale in result.files_deleted

    def test_result_counts(self, tmp_path: Path) -> None:
        """T063-4: RewriteResult fields are populated.

        Post-mission-083 codex uses the Agent Skills pipeline, not the slash-command
        shim pipeline, so it's NOT processed by ``rewrite_agent_shims``. To verify
        the counter with multiple agents we use two slash-command agents (claude,
        opencode) instead.
        """
        _setup_project(tmp_path, agents=["claude", "opencode"])
        result = rewrite_agent_shims(tmp_path)
        assert result.agents_processed >= 2
        assert len(result.files_written) > 0

    def test_idempotent(self, tmp_path: Path) -> None:
        """T063-5: Running rewrite twice yields same result; nothing deleted second time."""
        _setup_project(tmp_path, agents=["claude"])
        result1 = rewrite_agent_shims(tmp_path)
        result2 = rewrite_agent_shims(tmp_path)
        assert len(result2.files_deleted) == 0
        assert len(result2.files_written) == len(result1.files_written)

    def test_no_config_handled(self, tmp_path: Path) -> None:
        """Runs without error when no .kittify/config.yaml exists (falls back to empty)."""
        # No config.yaml — should not raise; just process nothing or all
        result = rewrite_agent_shims(tmp_path)
        assert isinstance(result, RewriteResult)

    def test_old_template_content_gone(self, tmp_path: Path) -> None:
        """T063-2: Old workflow template content is replaced by thin shim."""
        _setup_project(tmp_path, agents=["claude"])
        claude_dir = _get_claude_cmd_dir(tmp_path)
        claude_dir.mkdir(parents=True, exist_ok=True)

        # Place a legacy template file that matches a known consumer skill
        from specify_cli.shims.registry import CONSUMER_SKILLS

        a_skill = sorted(CONSUMER_SKILLS)[0]
        legacy_file = claude_dir / f"spec-kitty.{a_skill}.md"
        legacy_file.write_text("# Old Workflow\n\n## Steps\n\n1. Do this\n2. Do that\n3. Do everything\n")

        rewrite_agent_shims(tmp_path)

        # File should now contain a direct canonical command
        new_content = legacy_file.read_text()
        assert "spec-kitty" in new_content
        assert "agent shim" not in new_content
        # Old content should be gone
        assert "Do this" not in new_content
