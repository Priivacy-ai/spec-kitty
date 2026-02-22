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
    directives: str = "directives: []\n",
) -> Path:
    constitution_dir = root / ".kittify" / "constitution"
    constitution_dir.mkdir(parents=True)
    (constitution_dir / "governance.yaml").write_text(governance, encoding="utf-8")
    (constitution_dir / "directives.yaml").write_text(directives, encoding="utf-8")
    return constitution_dir


def test_resolve_governance_reads_constitution_selections_first(tmp_path: Path) -> None:
    _write_constitution_files(
        tmp_path,
        governance="""
doctrine:
  selected_paradigms: [test-first]
  selected_directives: [TEST_FIRST]
  available_tools: [git]
  template_set: software-dev-default
""",
        directives="""
directives:
  - id: TEST_FIRST
    title: Keep tests strict
""",
    )

    result = resolve_governance(tmp_path, tool_registry={"git", "python", "pytest"})

    assert result.paradigms == ["test-first"]
    assert result.directives == ["TEST_FIRST"]
    assert result.tools == ["git"]
    assert result.template_set == "software-dev-default"
    assert result.metadata["template_set_source"] == "constitution"


def test_resolve_governance_missing_paradigm_hard_fails(tmp_path: Path) -> None:
    _write_constitution_files(
        tmp_path,
        governance="""
doctrine:
  selected_paradigms: [missing-paradigm]
""",
    )

    with pytest.raises(GovernanceResolutionError) as exc:
        resolve_governance(tmp_path)

    assert "missing-paradigm" in str(exc.value)


def test_resolve_governance_missing_directive_hard_fails(tmp_path: Path) -> None:
    _write_constitution_files(
        tmp_path,
        governance="""
doctrine:
  selected_directives: [NOT_A_DIRECTIVE]
""",
    )

    with pytest.raises(GovernanceResolutionError) as exc:
        resolve_governance(tmp_path)

    assert "NOT_A_DIRECTIVE" in str(exc.value)


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


def test_resolve_governance_missing_template_set_hard_fails(tmp_path: Path) -> None:
    _write_constitution_files(
        tmp_path,
        governance="""
doctrine:
  template_set: missing-template-set
""",
    )

    with pytest.raises(GovernanceResolutionError) as exc:
        resolve_governance(tmp_path)

    assert "missing-template-set" in str(exc.value)


def test_resolve_governance_template_set_fallback_visible(tmp_path: Path) -> None:
    _write_constitution_files(
        tmp_path,
        governance="""
doctrine:
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
  selected_directives: [NOT_A_DIRECTIVE]
""",
    )

    diagnostics = collect_governance_diagnostics(tmp_path)
    assert diagnostics
    assert any("NOT_A_DIRECTIVE" in line for line in diagnostics)
