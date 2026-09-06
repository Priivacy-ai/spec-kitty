"""Unit tests for the Claude Code plugin bundle projector."""

from __future__ import annotations

import json
from pathlib import Path

from specify_cli.tool_surface.enums import ToolSurfaceKind
from specify_cli.tool_surface.bundles.claude import ClaudeCodeBundleProjector

from ._support import full_plans, skills_only_plans

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def test_repeat_projection_preserves_every_node_mtime(tmp_path: Path) -> None:
    import os
    from tests.upgrade.preview_support.snapshot import assert_unchanged, snapshot

    project, out = tmp_path / "project", tmp_path / "dist"
    plans = full_plans(project)
    projector = ClaudeCodeBundleProjector()
    projector.project(plans, project, out)
    for path in (out, *out.rglob("*")):
        os.utime(path, ns=(1_000_000_000, 1_000_000_000), follow_symlinks=False)
    before = snapshot({"stage": out})
    projector.project(plans, project, out)
    assert_unchanged(before, snapshot({"stage": out}))


def test_missing_required_source_refuses_before_staging(tmp_path: Path) -> None:
    project, out = tmp_path / "project", tmp_path / "dist"
    plans = full_plans(project)
    plans[0].instances[0].path.unlink()
    try:
        ClaudeCodeBundleProjector().project(plans, project, out)
    except (OSError, ValueError):
        pass
    assert not out.exists(), "Missing source produced a successful empty placeholder"


def test_projection_preserves_unknown_destination_link(tmp_path: Path) -> None:
    project, out = tmp_path / "project", tmp_path / "dist"
    plans = full_plans(project)
    sentinel = tmp_path / "sentinel"
    sentinel.write_bytes(b"custom outside staged tree")
    destination = out / "skills/spec-kitty.plan/SKILL.md"
    destination.parent.mkdir(parents=True)
    destination.symlink_to(sentinel)
    try:
        ClaudeCodeBundleProjector().project(plans, project, out)
    except (OSError, ValueError):
        pass
    assert destination.is_symlink()
    assert sentinel.read_bytes() == b"custom outside staged tree"


def test_claude_code_bundle_layout_is_correct(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    out = tmp_path / "dist"
    bundle = ClaudeCodeBundleProjector().project(
        full_plans(project), project, out
    )
    # Manifest under .claude-plugin/, skills under skills/, agents under agents/.
    assert (out / ".claude-plugin" / "plugin.json").is_file()
    assert (out / "skills" / "spec-kitty.plan" / "SKILL.md").is_file()
    assert (out / "skills" / "spec-kitty.charter" / "SKILL.md").is_file()
    assert (out / "agents" / "architect-alphonso.md").is_file()
    # Hooks land at hooks/hooks.json, MCP config at root .mcp.json -- NOT
    # settings.json.
    assert (out / "hooks" / "hooks.json").is_file()
    assert (out / ".mcp.json").is_file()
    assert not (out / "settings.json").exists()
    assert bundle.manifest_path == out / ".claude-plugin" / "plugin.json"


def test_claude_code_bundle_plugin_json_exists(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    out = tmp_path / "dist"
    ClaudeCodeBundleProjector().project(full_plans(project), project, out)
    payload = json.loads(
        (out / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
    assert payload["name"] == "spec-kitty"
    assert payload["distribution_target"] == "claude_code_plugin"
    assert "version" in payload


def test_claude_code_bundle_validate_passes_when_complete(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    out = tmp_path / "dist"
    projector = ClaudeCodeBundleProjector()
    bundle = projector.project(full_plans(project), project, out)
    result = projector.validate(bundle)
    assert result.passed is True
    assert result.missing_surfaces == ()


def test_claude_code_bundle_validate_fails_when_skills_missing(
    tmp_path: Path,
) -> None:
    project = tmp_path / "proj"
    out = tmp_path / "dist"
    projector = ClaudeCodeBundleProjector()
    bundle = projector.project(skills_only_plans(project), project, out)
    result = projector.validate(bundle)
    assert result.passed is False
    codes = {f.code for f in result.missing_surfaces}
    assert codes == {"bundle-component-missing"}
    missing_kinds = {
        f.message.rsplit(": ", 1)[-1] for f in result.missing_surfaces
    }
    assert str(ToolSurfaceKind.AGENT_PROFILE) in missing_kinds
    assert str(ToolSurfaceKind.DOCTRINE_SKILL) in missing_kinds


def test_claude_code_bundle_excludes_session_presence(tmp_path: Path) -> None:
    """CONTEXT_FILE / RULE surfaces must never enter a plugin bundle."""
    from specify_cli.tool_surface.model import (
        SurfaceInstance,
        SurfacePlan,
    )

    from ._support import _definition

    project = tmp_path / "proj"
    out = tmp_path / "dist"
    claude_md = project / "CLAUDE.md"
    claude_md.parent.mkdir(parents=True, exist_ok=True)
    claude_md.write_text("# context\n", encoding="utf-8")
    plan = SurfacePlan(
        tool_key="all",
        instances=(
            SurfaceInstance(
                definition=_definition(ToolSurfaceKind.CONTEXT_FILE),
                path=claude_md,
                exists=True,
                file_hash=None,
                owner="claude",
            ),
        ),
        computed_at="t",
    )
    bundle = ClaudeCodeBundleProjector().project([plan], project, out)
    assert bundle.entries == ()
    assert not (out / "CLAUDE.md").exists()


def test_claude_code_bundle_excludes_out_of_tree_sources(tmp_path: Path) -> None:
    """A surface whose source escapes project_root is not bundled."""
    from specify_cli.tool_surface.model import (
        SurfaceInstance,
        SurfacePlan,
    )

    from ._support import _definition

    project = tmp_path / "proj"
    project.mkdir(parents=True, exist_ok=True)
    out = tmp_path / "dist"
    outside = tmp_path / "elsewhere" / "spec-kitty.plan" / "SKILL.md"
    outside.parent.mkdir(parents=True, exist_ok=True)
    outside.write_text("# outside\n", encoding="utf-8")
    plan = SurfacePlan(
        tool_key="all",
        instances=(
            SurfaceInstance(
                definition=_definition(ToolSurfaceKind.COMMAND_SKILL),
                path=outside,
                exists=True,
                file_hash=None,
                owner="codex",
            ),
        ),
        computed_at="t",
    )
    bundle = ClaudeCodeBundleProjector().project([plan], project, out)
    assert bundle.entries == ()
