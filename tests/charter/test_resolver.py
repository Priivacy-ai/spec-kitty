"""Tests for charter-centric governance resolver."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

import charter.catalog as catalog_module
from charter.interview import default_interview
from charter.resolver import (
    GovernanceResolutionError,
    collect_governance_diagnostics,
    resolve_governance,
    resolve_governance_for_profile,
)

pytestmark = pytest.mark.fast


def _write_charter_files(
    root: Path,
    *,
    governance: str,
    directives: str = "directives: []\n",
) -> Path:
    charter_dir = root / ".kittify" / "charter"
    charter_dir.mkdir(parents=True)
    (charter_dir / "governance.yaml").write_text(governance, encoding="utf-8")
    (charter_dir / "directives.yaml").write_text(directives, encoding="utf-8")
    return charter_dir


def test_resolve_governance_reads_charter_selections_first(tmp_path: Path, monkeypatch) -> None:
    """Charter selections (paradigms, directives, tools, template_set) are used
    when explicitly declared and all values exist in the shipped catalog."""
    # Build a minimal doctrine root so shipped paradigm validation passes.
    doctrine_root = tmp_path / "doctrine_root"
    (doctrine_root / "paradigms" / "shipped").mkdir(parents=True)
    (doctrine_root / "paradigms" / "shipped" / "test-first.paradigm.yaml").write_text("id: test-first\n")
    (doctrine_root / "directives" / "shipped").mkdir(parents=True)
    (doctrine_root / "agent_profiles" / "shipped").mkdir(parents=True)
    (doctrine_root / "missions" / "software-dev").mkdir(parents=True)
    (doctrine_root / "missions" / "software-dev" / "mission.yaml").write_text("name: software-dev\n")
    monkeypatch.setattr(catalog_module, "resolve_doctrine_root", lambda: doctrine_root)

    repo_root = tmp_path / "repo"
    _write_charter_files(
        repo_root,
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

    result = resolve_governance(repo_root, tool_registry={"git", "python", "pytest"})

    assert result.paradigms == ["test-first"]
    assert result.directives == ["TEST_FIRST"]
    assert result.tools == ["git"]
    assert result.template_set == "software-dev-default"
    assert result.metadata["template_set_source"] == "charter"


def test_resolve_governance_missing_paradigm_hard_fails(tmp_path: Path) -> None:
    _write_charter_files(
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
    _write_charter_files(
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
    _write_charter_files(
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
    _write_charter_files(
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
    _write_charter_files(
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
    _write_charter_files(
        tmp_path,
        governance="doctrine: {}\n",
    )
    mission_file = tmp_path / "src" / "doctrine" / "missions" / "software-dev" / "mission.yaml"
    mission_file.parent.mkdir(parents=True)
    mission_file.write_text("::invalid-yaml::\n\tbad")

    result = resolve_governance(tmp_path, tool_registry={"git"})
    assert result.tools == ["git"]


def test_collect_governance_diagnostics_reports_failures(tmp_path: Path) -> None:
    _write_charter_files(
        tmp_path,
        governance="""
doctrine:
  selected_directives: [NOT_A_DIRECTIVE]
""",
    )

    diagnostics = collect_governance_diagnostics(tmp_path)
    assert diagnostics
    assert any("NOT_A_DIRECTIVE" in line for line in diagnostics)


def test_resolve_governance_uses_registry_local_directives_and_template_fallback(
    tmp_path: Path,
) -> None:
    _write_charter_files(
        tmp_path,
        governance="doctrine: {}\n",
        directives="""
directives:
  - id: LOCAL_ONLY
    title: Local rule
""",
    )

    result = resolve_governance(
        tmp_path,
        tool_registry={"python", "git"},
        fallback_template_set="fallback-pack",
    )

    assert result.tools == ["git", "python"]
    assert result.directives == ["LOCAL_ONLY"]
    assert result.template_set == "fallback-pack"
    assert result.metadata == {
        "tools_source": "registry_fallback",
        "directives_source": "catalog_fallback",
        "template_set_source": "fallback",
    }
    assert any("runtime tool registry fallback" in line for line in result.diagnostics)
    assert any("fallback-pack" in line for line in result.diagnostics)


def test_resolve_governance_uses_catalog_directives_when_no_local_declarations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_charter_files(tmp_path, governance="doctrine: {}\n")
    monkeypatch.setattr(
        "charter.resolver.load_doctrine_catalog",
        lambda: SimpleNamespace(
            paradigms=frozenset(),
            directives=frozenset({"DIRECTIVE_010", "DIRECTIVE_003"}),
            template_sets=frozenset({"software-dev-default"}),
            domains_present=frozenset(),
        ),
    )

    result = resolve_governance(tmp_path, tool_registry={"git"})

    assert result.directives == ["DIRECTIVE_003", "DIRECTIVE_010"]
    assert result.metadata["directives_source"] == "catalog_fallback"


def test_resolve_governance_for_profile_merges_profile_directives_first() -> None:
    interview = default_interview(mission="software-dev", profile="minimal")
    interview = default_interview(mission="software-dev", profile="minimal")
    object.__setattr__(interview, "selected_directives", ["INTERVIEW_DIRECTIVE", "PROFILE_DIRECTIVE"])

    profile = SimpleNamespace(
        profile_id="reviewer",
        directive_references=[
            SimpleNamespace(code="PROFILE_DIRECTIVE"),
            SimpleNamespace(code="PROFILE_SECOND"),
        ],
    )
    doctrine_service = MagicMock()
    doctrine_service.agent_profiles.resolve_profile.return_value = profile
    doctrine_service.directives.get.side_effect = lambda artifact_id: SimpleNamespace(
        id=artifact_id,
        title=artifact_id,
        intent=f"Intent for {artifact_id}",
        tactic_refs=[],
    )
    doctrine_service.tactics.get.return_value = None
    doctrine_service.styleguides.get.return_value = None
    doctrine_service.toolguides.get.return_value = None
    doctrine_service.procedures.get.return_value = None

    resolution = resolve_governance_for_profile("reviewer", "reviewer", doctrine_service, interview)

    assert resolution.profile_id == "reviewer"
    assert resolution.role == "reviewer"
    assert resolution.directives == ["PROFILE_DIRECTIVE", "PROFILE_SECOND", "INTERVIEW_DIRECTIVE"]
    assert resolution.metadata["directives_source"] == "profile+interview"


def test_resolve_governance_for_profile_populates_graph_artifacts_and_normalizes_role() -> None:
    interview = default_interview(mission="software-dev", profile="minimal")
    object.__setattr__(interview, "selected_directives", ["INTERVIEW_DIRECTIVE", "PROFILE_DIRECTIVE"])

    profile = SimpleNamespace(
        profile_id="reviewer",
        directive_references=[
            SimpleNamespace(code=" PROFILE_DIRECTIVE "),
            SimpleNamespace(code=""),
            SimpleNamespace(code="PROFILE_SECOND"),
        ],
    )
    doctrine_service = MagicMock()
    doctrine_service.agent_profiles.resolve_profile.return_value = profile

    # Post-WP03: monkeypatch charter.resolver.resolve_transitive_refs; its
    # result is a :class:`doctrine.drg.query.ResolveTransitiveRefsResult`
    # look-alike (SimpleNamespace is structurally compatible here).
    monkeypatch_graph = SimpleNamespace(
        tactics=["TACTIC_001"],
        styleguides=["STYLE_001"],
        toolguides=["TOOL_001"],
        procedures=["PROC_001"],
        unresolved=[("directive:MISSING_DIRECTIVE", "directive:MISSING_DIRECTIVE")],
    )

    # Provide a stand-in graph so the resolver invokes resolve_transitive_refs.
    stub_graph = SimpleNamespace()

    with patch(
        "charter.resolver.resolve_references_transitively",
        return_value=monkeypatch_graph,
    ):
        resolution = resolve_governance_for_profile(
            " reviewer ",
            "   ",
            doctrine_service,
            interview,
            graph=stub_graph,
        )

    assert resolution.directives == ["PROFILE_DIRECTIVE", "PROFILE_SECOND", "INTERVIEW_DIRECTIVE"]
    assert resolution.tactics == ["TACTIC_001"]
    assert resolution.styleguides == ["STYLE_001"]
    assert resolution.toolguides == ["TOOL_001"]
    assert resolution.procedures == ["PROC_001"]
    assert resolution.role is None
    assert resolution.metadata["profile_directives_count"] == "2"
    assert any("MISSING_DIRECTIVE" in line for line in resolution.diagnostics)


def test_resolve_governance_for_profile_missing_profile_raises_value_error() -> None:
    interview = default_interview(mission="software-dev", profile="minimal")
    doctrine_service = MagicMock()
    doctrine_service.agent_profiles.resolve_profile.side_effect = KeyError("missing")

    with pytest.raises(ValueError) as exc:
        resolve_governance_for_profile("missing", None, doctrine_service, interview)

    assert "missing" in str(exc.value)


def test_resolve_governance_for_profile_rejects_blank_profile_id() -> None:
    interview = default_interview(mission="software-dev", profile="minimal")
    doctrine_service = MagicMock()

    with pytest.raises(ValueError, match="Profile ID is required"):
        resolve_governance_for_profile("   ", None, doctrine_service, interview)


def test_resolve_governance_for_profile_records_unresolved_references_in_diagnostics() -> None:
    """Post-WP03, unresolved references surface via the DRG walker.

    The ``unresolved`` entries in the :class:`ResolveTransitiveRefsResult`
    are formatted into ``diagnostics`` by ``resolve_governance_for_profile``.
    """
    interview = default_interview(mission="software-dev", profile="minimal")
    object.__setattr__(interview, "selected_directives", [])

    profile = SimpleNamespace(
        profile_id="reviewer",
        directive_references=[SimpleNamespace(code="MISSING_DIRECTIVE")],
    )
    doctrine_service = MagicMock()
    doctrine_service.agent_profiles.resolve_profile.return_value = profile

    monkeypatch_graph = SimpleNamespace(
        tactics=[],
        styleguides=[],
        toolguides=[],
        procedures=[],
        unresolved=[
            (
                "directive:MISSING_DIRECTIVE",
                "directive:MISSING_DIRECTIVE",
            )
        ],
    )
    stub_graph = SimpleNamespace()

    with patch(
        "charter.resolver.resolve_references_transitively",
        return_value=monkeypatch_graph,
    ):
        resolution = resolve_governance_for_profile(
            "reviewer",
            None,
            doctrine_service,
            interview,
            graph=stub_graph,
        )

    assert resolution.directives == ["MISSING_DIRECTIVE"]
    assert any("MISSING_DIRECTIVE" in line for line in resolution.diagnostics)


def test_collect_governance_diagnostics_returns_success_diagnostics(
    tmp_path: Path,
) -> None:
    _write_charter_files(tmp_path, governance="doctrine: {}\n")

    diagnostics = collect_governance_diagnostics(
        tmp_path,
        tool_registry={"git"},
        fallback_template_set="fallback-pack",
    )

    assert any("runtime tool registry fallback" in line for line in diagnostics)
    assert any("fallback-pack" in line for line in diagnostics)


# ---------------------------------------------------------------------------
# T017: Regression tests — named-ID failures, shipped-only, no agents.yaml
# ---------------------------------------------------------------------------


def _make_doctrine_root(tmp_path: Path, *, with_paradigm: str | None = None) -> Path:
    """Create a minimal doctrine root for resolver tests."""
    doctrine_root = tmp_path / "doctrine_root"
    paradigms_shipped = doctrine_root / "paradigms" / "shipped"
    paradigms_shipped.mkdir(parents=True)
    if with_paradigm:
        (paradigms_shipped / f"{with_paradigm}.paradigm.yaml").write_text(f"id: {with_paradigm}\n")
    (doctrine_root / "directives" / "shipped").mkdir(parents=True)
    (doctrine_root / "agent_profiles" / "shipped").mkdir(parents=True)
    (doctrine_root / "missions" / "software-dev").mkdir(parents=True)
    (doctrine_root / "missions" / "software-dev" / "mission.yaml").write_text("name: software-dev\n")
    return doctrine_root


def test_paradigm_failure_names_exact_offending_id(tmp_path: Path, monkeypatch) -> None:
    """Error message names the exact paradigm ID that was not in the shipped catalog."""
    doctrine_root = _make_doctrine_root(tmp_path)
    monkeypatch.setattr(catalog_module, "resolve_doctrine_root", lambda: doctrine_root)

    repo_root = tmp_path / "repo"
    _write_charter_files(
        repo_root,
        governance="doctrine:\n  selected_paradigms: [my-bad-paradigm]\n",
    )

    with pytest.raises(GovernanceResolutionError) as exc:
        resolve_governance(repo_root)

    error_text = str(exc.value)
    assert "my-bad-paradigm" in error_text


def test_paradigm_failure_skipped_when_shipped_dir_absent(tmp_path: Path, monkeypatch) -> None:
    """When the paradigms shipped directory does not exist, validation is skipped gracefully."""
    doctrine_root = tmp_path / "doctrine_root"
    # Do NOT create paradigms directory at all
    (doctrine_root / "directives" / "shipped").mkdir(parents=True)
    (doctrine_root / "agent_profiles" / "shipped").mkdir(parents=True)
    (doctrine_root / "missions" / "software-dev").mkdir(parents=True)
    (doctrine_root / "missions" / "software-dev" / "mission.yaml").write_text("name: software-dev\n")
    monkeypatch.setattr(catalog_module, "resolve_doctrine_root", lambda: doctrine_root)

    repo_root = tmp_path / "repo"
    _write_charter_files(
        repo_root,
        governance="doctrine:\n  selected_paradigms: [any-value]\n",
    )

    # Should not raise — domain is absent so skip validation
    result = resolve_governance(repo_root, tool_registry={"git"})
    assert result.paradigms == ["any-value"]


def test_directive_failure_names_exact_offending_id(tmp_path: Path, monkeypatch) -> None:
    """Error message names the exact directive ID that was not found."""
    doctrine_root = _make_doctrine_root(tmp_path)
    monkeypatch.setattr(catalog_module, "resolve_doctrine_root", lambda: doctrine_root)

    repo_root = tmp_path / "repo"
    _write_charter_files(
        repo_root,
        governance="doctrine:\n  selected_directives: [GHOST_DIRECTIVE]\n",
    )

    with pytest.raises(GovernanceResolutionError) as exc:
        resolve_governance(repo_root)

    assert "GHOST_DIRECTIVE" in str(exc.value)


def test_template_set_failure_names_exact_offending_value(tmp_path: Path, monkeypatch) -> None:
    """Error message names the exact template_set value that was not in shipped catalog."""
    doctrine_root = _make_doctrine_root(tmp_path)
    monkeypatch.setattr(catalog_module, "resolve_doctrine_root", lambda: doctrine_root)

    repo_root = tmp_path / "repo"
    _write_charter_files(
        repo_root,
        governance="doctrine:\n  template_set: ghost-template-set\n",
    )

    with pytest.raises(GovernanceResolutionError) as exc:
        resolve_governance(repo_root)

    assert "ghost-template-set" in str(exc.value)


def test_tool_failure_names_exact_offending_value(tmp_path: Path, monkeypatch) -> None:
    """Error message names the exact tool name that was not in the registry."""
    doctrine_root = _make_doctrine_root(tmp_path)
    monkeypatch.setattr(catalog_module, "resolve_doctrine_root", lambda: doctrine_root)

    repo_root = tmp_path / "repo"
    _write_charter_files(
        repo_root,
        governance="doctrine:\n  available_tools: [ghost-tool]\n",
    )

    with pytest.raises(GovernanceResolutionError) as exc:
        resolve_governance(repo_root, tool_registry={"git"})

    assert "ghost-tool" in str(exc.value)


def test_local_support_declaration_bypasses_catalog_validation(tmp_path: Path, monkeypatch) -> None:
    """Directives declared in directives.yaml are valid without being in the shipped catalog."""
    doctrine_root = _make_doctrine_root(tmp_path)
    monkeypatch.setattr(catalog_module, "resolve_doctrine_root", lambda: doctrine_root)

    repo_root = tmp_path / "repo"
    _write_charter_files(
        repo_root,
        governance="doctrine:\n  selected_directives: [LOCAL_ONLY]\n",
        directives="directives:\n  - id: LOCAL_ONLY\n    title: Local rule\n",
    )

    # Should NOT raise — LOCAL_ONLY is declared in directives.yaml
    result = resolve_governance(repo_root, tool_registry={"git"})
    assert "LOCAL_ONLY" in result.directives


def test_sync_output_does_not_include_agents_yaml(tmp_path: Path) -> None:
    """Charter sync writes exactly governance/directives/metadata — no agents.yaml."""
    from charter.sync import sync

    charter_file = tmp_path / "charter.md"
    charter_file.write_text("# Project\n\n## Directives\n1. Write tests\n")

    result = sync(charter_file, tmp_path)

    assert result.synced is True
    assert set(result.files_written) == {"governance.yaml", "directives.yaml", "metadata.yaml"}
    assert not (tmp_path / "agents.yaml").exists()
