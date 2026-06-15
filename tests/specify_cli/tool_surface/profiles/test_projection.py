"""Unit tests for ``tool_surface.profiles.projection``."""

from __future__ import annotations

from pathlib import Path

from doctrine.agent_profiles.repository import AgentProfileRepository
from specify_cli.tool_surface.profiles.projection import (
    ProfileProjector,
    default_profile_repository,
)

from .test_renderers import make_test_profile

import pytest

pytestmark = [pytest.mark.unit]


def _builtin_repo() -> AgentProfileRepository:
    return AgentProfileRepository()


def test_project_claude_returns_builtin_profiles() -> None:
    projector = ProfileProjector(_builtin_repo())
    projected = projector.project("claude", Path("/project"))
    assert projected, "expected at least the built-in profiles"
    urns = {p.profile_urn for p in projected}
    assert "agent_profile:architect-alphonso" in urns
    sample = projected[0]
    assert sample.tool_key == "claude"
    assert sample.format == "claude-agent"
    assert sample.source_layer == "builtin"
    assert sample.file_hash is None  # computed only after write


def test_project_unsupported_tool_returns_empty() -> None:
    # "codex" now has a renderer (WP02), so use a truly unsupported tool key.
    projector = ProfileProjector(_builtin_repo())
    assert projector.project("unknown_tool_xyz", Path("/project")) == []
    assert projector.project("windsurf", Path("/project")) == []


def test_project_excludes_sentinel_profiles() -> None:
    repo = _builtin_repo()
    projector = ProfileProjector(repo)
    projected_ids = {
        p.profile_urn.split(":", 1)[1]
        for p in projector.project("claude", Path("/project"))
    }
    sentinel_ids = {
        prof.profile_id for prof in repo.list_all() if prof.sentinel
    }
    assert sentinel_ids  # there is at least one sentinel built-in
    assert projected_ids.isdisjoint(sentinel_ids)


def test_project_source_layer_filter() -> None:
    projector = ProfileProjector(_builtin_repo())
    builtin_only = projector.project(
        "claude", Path("/project"), source_layers=["builtin"]
    )
    org_only = projector.project(
        "claude", Path("/project"), source_layers=["org"]
    )
    assert builtin_only  # all built-ins survive the builtin filter
    assert org_only == []  # no org overlay in a default setup


def test_project_does_not_mutate_repository() -> None:
    repo = _builtin_repo()
    before = {p.profile_id for p in repo.list_all()}
    ProfileProjector(repo).project("claude", Path("/project"))
    after = {p.profile_id for p in repo.list_all()}
    assert before == after


def test_render_returns_body_for_known_profile() -> None:
    projector = ProfileProjector(_builtin_repo())
    body = projector.render("claude", "agent_profile:architect-alphonso")
    assert body is not None
    assert body.startswith("---\n")
    assert "name: architect-alphonso" in body


def test_render_returns_none_for_unsupported_tool() -> None:
    # "codex" now has a renderer (WP02); use a tool with no native primitive.
    projector = ProfileProjector(_builtin_repo())
    assert projector.render("unknown_tool_xyz", "agent_profile:architect-alphonso") is None
    assert projector.render("windsurf", "agent_profile:architect-alphonso") is None


def test_render_returns_none_for_unknown_profile() -> None:
    projector = ProfileProjector(_builtin_repo())
    assert projector.render("claude", "agent_profile:does-not-exist") is None


def test_default_profile_repository_loads_builtins(tmp_path: Path) -> None:
    repo = default_profile_repository(tmp_path)
    ids = {p.profile_id for p in repo.list_all()}
    assert "architect-alphonso" in ids


def test_project_uses_injected_repo_provenance() -> None:
    """A project-layer profile is tagged with its provenance layer."""
    repo = _builtin_repo()
    profile = make_test_profile(slug="custom-carol")
    repo._profiles[profile.profile_id] = profile  # noqa: SLF001 - test seam
    repo._provenance[profile.profile_id] = "project"  # noqa: SLF001 - test seam
    projector = ProfileProjector(repo)
    projected = {
        p.profile_urn: p for p in projector.project("claude", Path("/project"))
    }
    assert projected["agent_profile:custom-carol"].source_layer == "project"
