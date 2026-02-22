"""Tests for migration m_2_0_0_retire_git_hooks."""

from __future__ import annotations

from pathlib import Path

from specify_cli.upgrade.migrations.m_2_0_0_retire_git_hooks import (
    RetireGitHooksMigration,
)


MANAGED_SHIM = """#!/usr/bin/env bash
# SPEC_KITTY_MANAGED_HOOK_SHIM=1
# Spec Kitty managed git hook shim (pre-commit)
"""

MANAGED_PRE_COMMIT = """#!/usr/bin/env bash
# Main pre-commit hook that orchestrates all pre-commit checks
if [ -x "$HOOKS_DIR/pre-commit-encoding-check" ]; then
    "$HOOKS_DIR/pre-commit-encoding-check" || exit 1
fi
if [ -x "$HOOKS_DIR/pre-commit-agent-check" ]; then
    "$HOOKS_DIR/pre-commit-agent-check" || exit 1
fi
"""

MANAGED_COMMIT_MSG = """#!/usr/bin/env bash
# commit-msg hook to enforce conventional commit messages via commitlint.
echo "Example: feat(doctrine): add markdown and commit quality gates"
"""

MANAGED_AGENT_CHECK = """#!/usr/bin/env bash
# Pre-commit hook to prevent committing agent directories
AGENT_DIRS=(".claude" ".codex" ".github/copilot")
"""

MANAGED_ENCODING_CHECK = """#!/usr/bin/env bash
# Pre-commit hook to validate UTF-8 encoding in markdown files
echo "spec-kitty validate-encoding --all --fix"
"""

MANAGED_MARKDOWN_CHECK = """#!/usr/bin/env bash
# Pre-commit hook to validate markdown style on staged files.
echo "markdownlint-cli2"
echo "SPEC_KITTY_TEST_MODE"
"""


def _hooks_dir(tmp_path: Path) -> Path:
    hooks_dir = tmp_path / ".git" / "hooks"
    hooks_dir.mkdir(parents=True)
    return hooks_dir


class TestRetireGitHooksMigration:
    def test_detect_true_when_managed_hook_exists(self, tmp_path: Path) -> None:
        hooks_dir = _hooks_dir(tmp_path)
        (hooks_dir / "pre-commit").write_text(MANAGED_SHIM, encoding="utf-8")

        migration = RetireGitHooksMigration()
        assert migration.detect(tmp_path) is True

    def test_detect_false_when_only_custom_hooks_exist(self, tmp_path: Path) -> None:
        hooks_dir = _hooks_dir(tmp_path)
        (hooks_dir / "pre-commit").write_text("#!/usr/bin/env bash\necho custom\n", encoding="utf-8")

        migration = RetireGitHooksMigration()
        assert migration.detect(tmp_path) is False

    def test_apply_removes_only_managed_hooks(self, tmp_path: Path) -> None:
        hooks_dir = _hooks_dir(tmp_path)
        (hooks_dir / "pre-commit").write_text(MANAGED_PRE_COMMIT, encoding="utf-8")
        (hooks_dir / "commit-msg").write_text(MANAGED_COMMIT_MSG, encoding="utf-8")
        (hooks_dir / "pre-commit-agent-check").write_text(MANAGED_AGENT_CHECK, encoding="utf-8")
        (hooks_dir / "pre-commit-encoding-check").write_text(MANAGED_ENCODING_CHECK, encoding="utf-8")
        (hooks_dir / "pre-commit-markdown-check").write_text(MANAGED_MARKDOWN_CHECK, encoding="utf-8")
        (hooks_dir / "prepare-commit-msg").write_text("#!/usr/bin/env bash\necho custom\n", encoding="utf-8")

        migration = RetireGitHooksMigration()
        result = migration.apply(tmp_path)

        assert result.success is True
        assert not result.errors
        assert (hooks_dir / "prepare-commit-msg").exists()
        assert not (hooks_dir / "pre-commit").exists()
        assert not (hooks_dir / "commit-msg").exists()
        assert not (hooks_dir / "pre-commit-agent-check").exists()
        assert not (hooks_dir / "pre-commit-encoding-check").exists()
        assert not (hooks_dir / "pre-commit-markdown-check").exists()

    def test_apply_dry_run_does_not_modify_hooks(self, tmp_path: Path) -> None:
        hooks_dir = _hooks_dir(tmp_path)
        pre_commit = hooks_dir / "pre-commit"
        pre_commit.write_text(MANAGED_PRE_COMMIT, encoding="utf-8")

        migration = RetireGitHooksMigration()
        result = migration.apply(tmp_path, dry_run=True)

        assert result.success is True
        assert pre_commit.exists()
        assert any("Would remove managed hook: pre-commit" in change for change in result.changes_made)

    def test_apply_skips_custom_hook_with_warning(self, tmp_path: Path) -> None:
        hooks_dir = _hooks_dir(tmp_path)
        pre_commit = hooks_dir / "pre-commit"
        pre_commit.write_text("#!/usr/bin/env bash\necho custom-hook\n", encoding="utf-8")

        migration = RetireGitHooksMigration()
        result = migration.apply(tmp_path)

        assert result.success is True
        assert pre_commit.exists()
        assert "Skipped custom hook: pre-commit" in result.warnings

    def test_apply_succeeds_when_hooks_dir_missing(self, tmp_path: Path) -> None:
        migration = RetireGitHooksMigration()
        result = migration.apply(tmp_path)

        assert result.success is True
        assert "No .git/hooks directory found" in result.changes_made

