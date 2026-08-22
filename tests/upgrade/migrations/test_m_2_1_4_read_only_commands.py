"""Regression tests for rewriting generated command files in migration 2.1.4."""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.shims import registry as shims_registry
from specify_cli.upgrade.migrations import m_2_1_4_enforce_command_file_state as migration

pytestmark = pytest.mark.fast


def test_apply_rewrites_and_reprotects_existing_command_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Generated prompt and shim files remain replaceable after write protection."""
    templates_dir = tmp_path / "templates"
    (templates_dir / "plan").mkdir(parents=True)
    (templates_dir / "plan" / "prompt.md").write_text("template\n", encoding="utf-8")

    command_dir = tmp_path / ".claude" / "commands"
    command_dir.mkdir(parents=True)
    prompt_path = command_dir / "spec-kitty.plan.md"
    shim_path = command_dir / "spec-kitty.implement.md"
    for path in (prompt_path, shim_path):
        path.write_text("stale\n", encoding="utf-8")
        path.chmod(0o444)

    monkeypatch.setattr(
        migration, "get_agent_dirs_for_project", lambda _project: [(".claude", "commands")]
    )
    monkeypatch.setattr(migration, "_get_runtime_command_templates_dir", lambda: templates_dir)
    monkeypatch.setattr(
        migration, "_render_full_prompt", lambda *_args, **_kwargs: "current prompt\n"
    )
    monkeypatch.setattr(migration, "_render_shim", lambda *_args: "current shim\n")
    monkeypatch.setattr(shims_registry, "PROMPT_DRIVEN_COMMANDS", {"plan"})
    monkeypatch.setattr(shims_registry, "CLI_DRIVEN_COMMANDS", {"implement"})

    result = migration.EnforceCommandFileStateMigration().apply(tmp_path)

    assert result.success is True
    assert result.errors == []
    assert prompt_path.read_text(encoding="utf-8") == "current prompt\n"
    assert shim_path.read_text(encoding="utf-8") == "current shim\n"
    assert prompt_path.stat().st_mode & 0o222 == 0
    assert shim_path.stat().st_mode & 0o222 == 0
