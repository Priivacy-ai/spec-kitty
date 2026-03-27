"""Tests for migration/rewrite_shims.py — Subtask T063.

Covers:
- T063-1: Agent command files replaced with 3-line thin shims
- T063-2: Old template content is gone after rewrite
- T063-3: Stale spec-kitty.*.md files not in generated set are deleted
- T063-4: RewriteResult reports correct counts
- T063-5: Works when agent directories already have correct shims (idempotent)
"""

from __future__ import annotations

from pathlib import Path

import pytest

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
    def test_shims_written(self, tmp_path: Path) -> None:
        """T063-1: Shim files are created for each configured agent."""
        _setup_project(tmp_path, agents=["claude"])
        result = rewrite_agent_shims(tmp_path)
        assert isinstance(result, RewriteResult)
        assert len(result.files_written) > 0

        # At least one spec-kitty.*.md written for claude
        claude_dir = _get_claude_cmd_dir(tmp_path)
        shims = list(claude_dir.glob("spec-kitty.*.md"))
        assert len(shims) > 0

    def test_shim_content_is_thin(self, tmp_path: Path) -> None:
        """T063-1: Shim content has the canonical 3-line format."""
        _setup_project(tmp_path, agents=["claude"])
        rewrite_agent_shims(tmp_path)

        claude_dir = _get_claude_cmd_dir(tmp_path)
        shim_files = list(claude_dir.glob("spec-kitty.*.md"))
        assert len(shim_files) > 0

        for shim_file in shim_files:
            content = shim_file.read_text()
            # Must contain the CLI invocation line
            assert "spec-kitty agent shim" in content
            # Must not contain lengthy workflow/step logic
            assert "## Steps" not in content
            assert "## Objectives" not in content

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
        """T063-4: RewriteResult fields are populated."""
        _setup_project(tmp_path, agents=["claude", "codex"])
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
        legacy_file.write_text(
            "# Old Workflow\n\n"
            "## Steps\n\n"
            "1. Do this\n2. Do that\n3. Do everything\n"
        )

        rewrite_agent_shims(tmp_path)

        # File should now be a thin shim
        new_content = legacy_file.read_text()
        assert "spec-kitty agent shim" in new_content
        # Old content should be gone
        assert "Do this" not in new_content
