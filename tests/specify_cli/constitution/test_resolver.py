"""Tests for constitution-centric governance resolver."""

from pathlib import Path

import pytest

from specify_cli.constitution.resolver import (
    GovernanceResolutionError,
    collect_governance_diagnostics,
    resolve_governance,
)


def _write_constitution_files(
    root: Path,
    *,
    governance: str,
    agents: str = "profiles: []\nselection: {}\n",
    directives: str = "directives: []\n",
) -> Path:
    constitution_dir = root / ".kittify" / "constitution"
    constitution_dir.mkdir(parents=True)
    (constitution_dir / "governance.yaml").write_text(governance, encoding="utf-8")
    (constitution_dir / "agents.yaml").write_text(agents, encoding="utf-8")
    (constitution_dir / "directives.yaml").write_text(directives, encoding="utf-8")
    return constitution_dir


def test_resolve_governance_reads_constitution_selections_first(tmp_path: Path) -> None:
    _write_constitution_files(
        tmp_path,
        governance="""
doctrine:
  selected_paradigms: [test-first]
  selected_directives: [DIR-001]
  selected_agent_profiles: [codex]
  available_tools: [git]
  template_set: strict-doctrine
""",
        agents="""
profiles:
  - agent_key: codex
    role: implementer
  - agent_key: claude
    role: reviewer
selection: {}
""",
        directives="""
directives:
  - id: DIR-001
    title: Keep tests strict
""",
    )

    result = resolve_governance(
        tmp_path, tool_registry={"git", "python", "pytest"}
    )

    assert result.paradigms == ["test-first"]
    assert result.directives == ["DIR-001"]
    assert [profile.agent_key for profile in result.agent_profiles] == ["codex"]
    assert result.tools == ["git"]
    assert result.template_set == "strict-doctrine"
    assert result.metadata["template_set_source"] == "constitution"


def test_resolve_governance_missing_profile_hard_fails(tmp_path: Path) -> None:
    _write_constitution_files(
        tmp_path,
        governance="""
doctrine:
  selected_agent_profiles: [missing-profile]
""",
        agents="""
profiles:
  - agent_key: codex
    role: implementer
selection: {}
""",
    )

    with pytest.raises(GovernanceResolutionError) as exc:
        resolve_governance(tmp_path)

    assert "missing-profile" in str(exc.value)


def test_resolve_governance_missing_tool_hard_fails(tmp_path: Path) -> None:
    _write_constitution_files(
        tmp_path,
        governance="""
doctrine:
  available_tools: [imaginary-tool]
""",
    )

    with pytest.raises(GovernanceResolutionError) as exc:
        resolve_governance(tmp_path, tool_registry={"git", "python"})

    assert "imaginary-tool" in str(exc.value)


def test_resolve_governance_template_set_fallback_visible(tmp_path: Path) -> None:
    _write_constitution_files(
        tmp_path,
        governance="""
doctrine:
  selected_agent_profiles: []
  available_tools: []
""",
    )

    result = resolve_governance(
        tmp_path,
        tool_registry={"git"},
        fallback_template_set="fallback-pack",
    )

    assert result.template_set == "fallback-pack"
    assert result.metadata["template_set_source"] == "fallback"
    assert any("fallback-pack" in line for line in result.diagnostics)


def test_resolver_does_not_read_mission_files(tmp_path: Path) -> None:
    _write_constitution_files(
        tmp_path,
        governance="doctrine: {}\n",
    )
    mission_file = tmp_path / "src" / "doctrine" / "missions" / "software-dev" / "mission.yaml"
    mission_file.parent.mkdir(parents=True)
    mission_file.write_text("::invalid-yaml::\n\tbad")

    result = resolve_governance(tmp_path, tool_registry={"git"})
    assert result.tools == ["git"]


def test_collect_governance_diagnostics_reports_failures(tmp_path: Path) -> None:
    _write_constitution_files(
        tmp_path,
        governance="""
doctrine:
  selected_agent_profiles: [missing-profile]
""",
        agents="profiles: []\nselection: {}\n",
    )

    diagnostics = collect_governance_diagnostics(tmp_path)
    assert diagnostics
    assert any("missing-profile" in line for line in diagnostics)
