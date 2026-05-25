"""Tests for build_charter_context -- DRG-based charter context (T021 + T022)."""

from __future__ import annotations

import ast
import inspect
import textwrap
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from charter.context import (
    CharterContextResult,
    _build_doctrine_service,
    _bundle_root_for_json,
    _project_charter_json_block,
    _project_directive_entries,
    _relative_json_path,
    _render_action_scoped,
    _render_bootstrap,
    build_charter_context,
    build_charter_context_json,
)

pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_MINIMAL_GRAPH_YAML = textwrap.dedent("""\
    schema_version: "1.0"
    generated_at: "2026-04-13T10:00:00+00:00"
    generated_by: "test"
    nodes:
      - urn: "action:software-dev/implement"
        kind: action
        label: implement
      - urn: "directive:DIRECTIVE_001"
        kind: directive
        label: Architectural Integrity Standard
      - urn: "tactic:tdd-red-green-refactor"
        kind: tactic
        label: TDD Red-Green-Refactor
      - urn: "styleguide:kitty-glossary-writing"
        kind: styleguide
        label: Kitty Glossary Writing
      - urn: "toolguide:efficient-local-tooling"
        kind: toolguide
        label: Efficient Local Tooling
    edges:
      - source: "action:software-dev/implement"
        target: "directive:DIRECTIVE_001"
        relation: scope
      - source: "action:software-dev/implement"
        target: "tactic:tdd-red-green-refactor"
        relation: scope
      - source: "directive:DIRECTIVE_001"
        target: "styleguide:kitty-glossary-writing"
        relation: suggests
      - source: "styleguide:kitty-glossary-writing"
        target: "toolguide:efficient-local-tooling"
        relation: suggests
""")

_CHARTER_MD = textwrap.dedent("""\
    # Project Charter

    ## Policy Summary

    - Intent: deterministic delivery
    - Testing: pytest + coverage
    - Quality: ruff linting
""")

_GOVERNANCE_YAML = textwrap.dedent("""\
    doctrine:
      template_set: software-dev-default
      selected_paradigms: []
      selected_directives: []
      available_tools: []
""")

_REFERENCES_YAML = textwrap.dedent("""\
    schema_version: "1.0.0"
    references:
      - id: "USER:PROJECT_PROFILE"
        kind: user_profile
        title: User Project Profile
        local_path: _LIBRARY/user-project-profile.md
""")


def _setup_fixture_repo(tmp_path: Path) -> None:
    """Create a minimal repo layout for build_charter_context testing."""
    charter_dir = tmp_path / ".kittify" / "charter"
    charter_dir.mkdir(parents=True, exist_ok=True)
    (charter_dir / "charter.md").write_text(_CHARTER_MD, encoding="utf-8")
    (charter_dir / "governance.yaml").write_text(_GOVERNANCE_YAML, encoding="utf-8")
    (charter_dir / "references.yaml").write_text(_REFERENCES_YAML, encoding="utf-8")


def _write_graph_fixture(tmp_path: Path) -> None:
    from io import StringIO

    from doctrine.drg.models import DRGGraph
    from ruamel.yaml import YAML

    yaml = YAML(typ="safe")
    graph_data = yaml.load(StringIO(_MINIMAL_GRAPH_YAML))
    mock_graph = DRGGraph.model_validate(graph_data)

    def patched_load_graph(path: Path) -> DRGGraph:
        return mock_graph

    return patched_load_graph


# ---------------------------------------------------------------------------
# T021: build_charter_context functional tests
# ---------------------------------------------------------------------------


class TestBuildContextV2:
    """Functional tests for the DRG-based context builder."""

    def _call(
        self,
        tmp_path: Path,
        action: str = "implement",
        depth: int = 2,
        profile: str | None = None,
        mark_loaded: bool = True,
    ) -> CharterContextResult:
        """Call build_charter_context with a patched graph loader."""
        _setup_fixture_repo(tmp_path)

        from io import StringIO

        from doctrine.drg.models import DRGGraph
        from ruamel.yaml import YAML

        yaml = YAML(typ="safe")
        graph_data = yaml.load(StringIO(_MINIMAL_GRAPH_YAML))
        mock_graph = DRGGraph.model_validate(graph_data)

        def patched_load_graph(path: Path) -> DRGGraph:
            # Return our minimal test graph regardless of path
            return mock_graph

        with (
            patch("doctrine.drg.loader.load_graph", side_effect=patched_load_graph),
            patch("charter.catalog.resolve_doctrine_root", return_value=tmp_path),
            patch("doctrine.drg.validator.assert_valid"),  # fixture may not pass full validation
        ):
            return build_charter_context(
                tmp_path,
                profile=profile,
                action=action,
                depth=depth,
                mark_loaded=mark_loaded,
            )

    def test_returns_charter_context_result(self, tmp_path: Path) -> None:
        """Returns the correct type."""
        result = self._call(tmp_path)
        assert isinstance(result, CharterContextResult)

    def test_action_normalized(self, tmp_path: Path) -> None:
        """Action is normalized to lowercase."""
        result = self._call(tmp_path, action="  IMPLEMENT  ")
        assert result.action == "implement"

    def test_mode_is_bootstrap_on_first_load(self, tmp_path: Path) -> None:
        """Mode is 'bootstrap' on first load at depth >= 2."""
        result = self._call(tmp_path)
        assert result.mode == "bootstrap"
        assert result.first_load is True

    def test_mode_is_compact_on_second_load(self, tmp_path: Path) -> None:
        """Mode is 'compact' on second load when depth is state-driven."""
        # First load with depth=None (state decides: first_load -> depth 2)
        _setup_fixture_repo(tmp_path)

        patched_load_graph = _write_graph_fixture(tmp_path)

        with (
            patch("doctrine.drg.loader.load_graph", side_effect=patched_load_graph),
            patch("charter.catalog.resolve_doctrine_root", return_value=tmp_path),
            patch("doctrine.drg.validator.assert_valid"),
        ):
            # First load: depth=None -> state decides -> 2 (bootstrap)
            first = build_charter_context(tmp_path, action="implement", depth=None, mark_loaded=True)
            assert first.mode == "bootstrap"
            assert first.first_load is True
            # Second load: depth=None -> state decides -> 1 (compact)
            second = build_charter_context(tmp_path, action="implement", depth=None, mark_loaded=True)
            assert second.mode == "compact"
            assert second.first_load is False

    def test_non_bootstrap_action_returns_compact(self, tmp_path: Path) -> None:
        """Non-bootstrap actions always return compact mode."""
        result = self._call(tmp_path, action="custom-action")
        assert result.mode == "compact"
        assert result.first_load is False

    def test_text_contains_charter_context_header(self, tmp_path: Path) -> None:
        """Output text starts with Charter Context header."""
        result = self._call(tmp_path)
        assert "Charter Context (Bootstrap):" in result.text

    def test_text_contains_policy_summary(self, tmp_path: Path) -> None:
        """Output text includes policy summary from charter.md."""
        result = self._call(tmp_path)
        assert "Policy Summary:" in result.text
        assert "deterministic delivery" in result.text

    def test_text_contains_directives_section(self, tmp_path: Path) -> None:
        """Output text includes resolved directives."""
        result = self._call(tmp_path)
        assert "Directives:" in result.text
        assert "DIRECTIVE_001" in result.text

    def test_text_contains_tactics_section(self, tmp_path: Path) -> None:
        """Output text includes resolved tactics."""
        result = self._call(tmp_path)
        assert "Tactics:" in result.text
        assert "tdd-red-green-refactor" in result.text

    def test_selected_directive_closure_contributes_action_context(self, tmp_path: Path) -> None:
        """Selected directives contribute their DRG closure even without action-scope edges."""
        _setup_fixture_repo(tmp_path)
        (tmp_path / ".kittify" / "charter" / "governance.yaml").write_text(
            textwrap.dedent("""\
                doctrine:
                  template_set: software-dev-default
                  selected_paradigms: []
                  selected_directives: [DIRECTIVE_039]
                  available_tools: []
            """),
            encoding="utf-8",
        )

        graph_yaml = textwrap.dedent("""\
            schema_version: "1.0"
            generated_at: "2026-04-13T10:00:00+00:00"
            generated_by: "test"
            nodes:
              - urn: "action:software-dev/implement"
                kind: action
                label: implement
              - urn: "directive:DIRECTIVE_039"
                kind: directive
                label: Lynn Cole Engineering Culture
              - urn: "tactic:boring-code-review"
                kind: tactic
                label: Boring Code Review
            edges:
              - source: "directive:DIRECTIVE_039"
                target: "tactic:boring-code-review"
                relation: requires
        """)

        from io import StringIO

        from doctrine.drg.models import DRGGraph
        from ruamel.yaml import YAML

        yaml = YAML(typ="safe")
        mock_graph = DRGGraph.model_validate(yaml.load(StringIO(graph_yaml)))

        with (
            patch("doctrine.drg.loader.load_graph", return_value=mock_graph),
            patch("charter.catalog.resolve_doctrine_root", return_value=tmp_path),
            patch("doctrine.drg.validator.assert_valid"),
            patch("charter.sync.ensure_charter_bundle_fresh", return_value=None),
        ):
            result = build_charter_context(tmp_path, action="implement", depth=2, mark_loaded=False)

        assert "DIRECTIVE_039" in result.text
        assert "boring-code-review" in result.text

    def test_text_contains_reference_docs(self, tmp_path: Path) -> None:
        """Output text includes Reference Docs section."""
        result = self._call(tmp_path)
        assert "Reference Docs:" in result.text

    def test_profile_none_does_not_crash(self, tmp_path: Path) -> None:
        """profile=None is accepted without error."""
        result = self._call(tmp_path, profile=None)
        assert result.text  # non-empty

    def test_profile_value_ignored(self, tmp_path: Path) -> None:
        """profile value is accepted but does not change output (Phase 0)."""
        result_none = self._call(tmp_path, profile=None)
        result_named = self._call(tmp_path, profile="implementer")
        assert result_none.text == result_named.text

    def test_depth_1_returns_compact(self, tmp_path: Path) -> None:
        """depth=1 returns compact governance (matching legacy behavior)."""
        result = self._call(tmp_path, depth=1)
        assert result.mode == "compact"
        assert result.depth == 1

    def test_depth_3_includes_extended_sections(self, tmp_path: Path) -> None:
        """depth >= 3 renders styleguide and toolguide extended sections."""
        result = self._call(tmp_path, depth=3)
        assert "Styleguides:" in result.text
        assert "Toolguides:" in result.text

    def test_depth_2_omits_extended_sections(self, tmp_path: Path) -> None:
        """depth=2 does NOT render extended sections."""
        result = self._call(tmp_path, depth=2)
        assert "Styleguides:" not in result.text
        assert "Toolguides:" not in result.text

    def test_missing_charter_file(self, tmp_path: Path) -> None:
        """When charter.md is missing, returns mode='missing'."""
        _setup_fixture_repo(tmp_path)
        (tmp_path / ".kittify" / "charter" / "charter.md").unlink()

        from io import StringIO

        from doctrine.drg.models import DRGGraph
        from ruamel.yaml import YAML

        yaml = YAML(typ="safe")
        graph_data = yaml.load(StringIO(_MINIMAL_GRAPH_YAML))
        mock_graph = DRGGraph.model_validate(graph_data)

        def patched_load_graph(path: Path) -> DRGGraph:
            return mock_graph

        with (
            patch("doctrine.drg.loader.load_graph", side_effect=patched_load_graph),
            patch("charter.catalog.resolve_doctrine_root", return_value=tmp_path),
            patch("doctrine.drg.validator.assert_valid"),
        ):
            result = build_charter_context(tmp_path, action="implement", depth=2)

        assert result.mode == "missing"
        assert "Charter file not found" in result.text

    def test_references_count(self, tmp_path: Path) -> None:
        """references_count reflects filtered references."""
        result = self._call(tmp_path)
        assert result.references_count >= 0

    def test_build_context_uses_fallback_summary_when_policy_section_missing(
        self, tmp_path: Path
    ) -> None:
        _setup_fixture_repo(tmp_path)
        charter_path = tmp_path / ".kittify" / "charter" / "charter.md"
        charter_path.write_text("# Project Charter\n", encoding="utf-8")

        patched_load_graph = _write_graph_fixture(tmp_path)

        with (
            patch("doctrine.drg.loader.load_graph", side_effect=patched_load_graph),
            patch("charter.catalog.resolve_doctrine_root", return_value=tmp_path),
            patch("doctrine.drg.validator.assert_valid"),
        ):
            result = build_charter_context(tmp_path, action="implement", depth=2)

        assert "No explicit policy summary section found in charter.md." in result.text

    def test_depth_field_matches_input(self, tmp_path: Path) -> None:
        """The depth field in the result matches the input depth."""
        for d in [1, 2, 3]:
            result = self._call(tmp_path, depth=d)
            assert result.depth == d

    def test_json_compact_mode_reports_project_charter_and_all_directives(
        self, tmp_path: Path
    ) -> None:
        """Compact JSON still exposes project-local charter facts."""
        _setup_fixture_repo(tmp_path)
        charter_dir = tmp_path / ".kittify" / "charter"
        (charter_dir / "directives.yaml").write_text(
            textwrap.dedent("""\
                directives:
                  - id: DIR-001
                    title: First directive
                    description: First rule
                  - id: DIR-002
                    title: Second directive
                    description: Second rule
            """),
            encoding="utf-8",
        )
        (charter_dir / "metadata.yaml").write_text(
            textwrap.dedent("""\
                schema_version: 1.0.0
                charter_hash: sha256:testhash
                source_path: .kittify/charter/charter.md
                bundle_schema_version: 2
            """),
            encoding="utf-8",
        )

        from charter.sync import SyncResult

        sync_result = SyncResult(
            synced=False,
            stale_before=False,
            files_written=[],
            extraction_mode="",
            canonical_root=tmp_path,
        )
        with patch("charter.sync.ensure_charter_bundle_fresh", return_value=sync_result):
            payload = build_charter_context_json(tmp_path, action="plan", depth=1)

        assert payload["directives"] == []
        assert [entry["id"] for entry in payload["all_directives"]] == ["DIR-001", "DIR-002"]
        assert payload["project_charter"] == {
            "present": True,
            "path": ".kittify/charter/charter.md",
            "bytes": (charter_dir / "charter.md").stat().st_size,
            "hash": "sha256:testhash",
            "source_path": ".kittify/charter/charter.md",
            "bundle_schema_version": 2,
            "schema_version": "1.0.0",
        }

    def test_json_project_charter_metadata_fallbacks(self, tmp_path: Path) -> None:
        """Project-charter JSON metadata degrades to explicit presence facts."""
        assert _relative_json_path(Path("/outside/charter.md"), tmp_path) == "/outside/charter.md"

        with patch("charter.sync.ensure_charter_bundle_fresh", side_effect=RuntimeError("boom")):
            assert _bundle_root_for_json(tmp_path) == tmp_path

        with patch("charter.sync.ensure_charter_bundle_fresh", return_value=None):
            assert _bundle_root_for_json(tmp_path) == tmp_path

        missing = _project_charter_json_block(tmp_path)
        assert missing == {
            "present": False,
            "path": ".kittify/charter/charter.md",
        }

        charter_dir = tmp_path / ".kittify" / "charter"
        charter_dir.mkdir(parents=True)
        (charter_dir / "charter.md").write_text("# Charter\n", encoding="utf-8")
        from charter.sync import SyncResult

        sync_result = SyncResult(
            synced=False,
            stale_before=False,
            files_written=[],
            extraction_mode="",
            canonical_root=tmp_path,
        )

        with patch("charter.sync.ensure_charter_bundle_fresh", return_value=sync_result):
            no_metadata = _project_charter_json_block(tmp_path)
        assert no_metadata["present"] is True
        assert no_metadata["bytes"] == 10
        assert "hash" not in no_metadata

        metadata = charter_dir / "metadata.yaml"
        metadata.write_text("[not-a-mapping]\n", encoding="utf-8")
        with patch("charter.sync.ensure_charter_bundle_fresh", return_value=sync_result):
            non_mapping = _project_charter_json_block(tmp_path)
        assert "hash" not in non_mapping

        with (
            patch("charter.sync.ensure_charter_bundle_fresh", return_value=sync_result),
            patch("charter.context.YAML") as yaml_cls,
        ):
            yaml_cls.side_effect = ValueError("bad yaml")
            unreadable = _project_charter_json_block(tmp_path)
        assert "hash" not in unreadable

    def test_project_directive_entries_fallbacks(self, tmp_path: Path) -> None:
        """Directive JSON keeps IDs when optional loaders are unavailable."""
        with (
            patch("charter.sync.load_directives_config", side_effect=RuntimeError("no config")),
            patch(
                "charter.resolver.resolve_project_governance",
                return_value=SimpleNamespace(directives=["DIRECTIVE_001"]),
            ),
            patch("charter.context._build_doctrine_service", side_effect=RuntimeError("no service")),
        ):
            assert _project_directive_entries(tmp_path) == [
                {"id": "DIRECTIVE_001", "source": "builtin"}
            ]

        directive = SimpleNamespace(id="DIR-LOCAL", title="Local", description="")
        with (
            patch(
                "charter.sync.load_directives_config",
                return_value=SimpleNamespace(directives=[directive]),
            ),
            patch("charter.resolver.resolve_project_governance", side_effect=RuntimeError("no resolver")),
            patch("charter.context._build_doctrine_service", side_effect=RuntimeError("no service")),
        ):
            assert _project_directive_entries(tmp_path) == [
                {"id": "DIR-LOCAL", "source": "project", "title": "Local"}
            ]

        repo = SimpleNamespace(
            get=lambda artifact_id: SimpleNamespace(
                id=artifact_id,
                title="Catalog directive",
                intent="Catalog intent",
            ),
            get_provenance=lambda _artifact_id: "builtin",
        )
        with (
            patch(
                "charter.sync.load_directives_config",
                return_value=SimpleNamespace(directives=[]),
            ),
            patch(
                "charter.resolver.resolve_project_governance",
                return_value=SimpleNamespace(directives=["DIRECTIVE_002"]),
            ),
            patch(
                "charter.context._build_doctrine_service",
                return_value=SimpleNamespace(directives=repo),
            ),
        ):
            assert _project_directive_entries(tmp_path) == [
                {
                    "id": "DIRECTIVE_002",
                    "source": "builtin",
                    "title": "Catalog directive",
                    "summary": "Catalog intent",
                }
            ]


def test_render_bootstrap_uses_fallback_labels_without_summary_or_references() -> None:
    text = _render_bootstrap(Path("/tmp/charter.md"), [], [])

    assert "Policy Summary:" in text
    assert "No explicit policy summary section found in charter.md." in text
    assert "Reference Docs:" in text
    assert "No references manifest found." in text


def test_render_action_scoped_uses_fallback_labels_without_summary_or_references(tmp_path: Path) -> None:
    with patch("charter.context._append_action_doctrine_lines") as append_action_doctrine_lines:
        append_action_doctrine_lines.return_value = None
        text = _render_action_scoped(
            tmp_path,
            "implement",
            tmp_path / "charter.md",
            [],
            [],
        )

    assert "Policy Summary:" in text
    assert "No explicit policy summary section found in charter.md." in text
    assert "Reference Docs:" in text
    assert "No references manifest found." in text


# ---------------------------------------------------------------------------
# T022: Structural test -- no per-action filtering logic (FR-009)
# ---------------------------------------------------------------------------


class TestNoPerActionFiltering:
    """Structural audit verifying FR-009 compliance.

    build_charter_context must not contain if-statements that branch on
    action names to conditionally filter artifacts. Context size is
    determined entirely by graph topology.
    """

    def test_no_action_name_string_literals_in_function_body(self) -> None:
        """No action-name string literals in build_charter_context body.

        Checks that none of the canonical action names appear as string
        literals in the function's source code (excluding the docstring).
        """
        source = inspect.getsource(build_charter_context)
        tree = ast.parse(textwrap.dedent(source))

        # Find the function definition
        func_def = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "build_charter_context":
                func_def = node
                break

        assert func_def is not None, "Could not find build_charter_context function"

        # Collect all string literals in the function body (skip docstring)
        body_nodes = func_def.body
        # Skip the first statement if it's the docstring
        if (
            body_nodes
            and isinstance(body_nodes[0], ast.Expr)
            and isinstance(body_nodes[0].value, ast.Constant)
            and isinstance(body_nodes[0].value.value, str)
        ):
            body_nodes = body_nodes[1:]

        action_names = {"specify", "plan", "implement", "review", "tasks"}
        found_literals: list[str] = []

        for node in ast.walk(ast.Module(body=body_nodes, type_ignores=[])):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if node.value.lower() in action_names:
                    found_literals.append(node.value)

        assert not found_literals, (
            f"build_charter_context contains action-name string literals: "
            f"{found_literals}. FR-009 prohibits per-action filtering. "
            f"Context size is determined by graph topology, not if-statements."
        )

    def test_no_conditional_on_action_parameter(self) -> None:
        """No if-statements that compare the 'action' parameter to string literals."""
        source = inspect.getsource(build_charter_context)
        tree = ast.parse(textwrap.dedent(source))

        func_def = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "build_charter_context":
                func_def = node
                break

        assert func_def is not None

        # Look for if-statements that test 'action' or 'normalized' against
        # string constants
        for node in ast.walk(func_def):
            if isinstance(node, ast.If):
                test = node.test
                # Check for comparisons like `action == "specify"` or
                # `normalized in {"specify", "plan"}`
                if isinstance(test, ast.Compare):
                    for comparator in [test.left, *test.comparators]:
                        if isinstance(comparator, ast.Name) and comparator.id in (
                            "action",
                            "normalized",
                        ):
                            # Check if other side has string constants matching actions
                            for other in [test.left, *test.comparators]:
                                if isinstance(other, ast.Constant) and isinstance(
                                    other.value, str
                                ):
                                    action_names = {
                                        "specify",
                                        "plan",
                                        "implement",
                                        "review",
                                        "tasks",
                                    }
                                    assert other.value.lower() not in action_names, (
                                        f"Found conditional on action parameter: "
                                        f"comparison with '{other.value}'. "
                                        f"FR-009 prohibits per-action filtering."
                                    )


def test_build_doctrine_service_prefers_repo_src_overlay(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: dict[str, object] = {}

    class StubDoctrineService:
        def __init__(self, *, built_in_root: Path, project_root: Path | None, active_languages: list[str]) -> None:
            calls["built_in_root"] = built_in_root
            calls["project_root"] = project_root
            calls["active_languages"] = active_languages

    built_in_root = tmp_path / "shipped-doctrine"
    built_in_root.mkdir()
    project_root = tmp_path / "src" / "doctrine"
    project_root.mkdir(parents=True)

    monkeypatch.setattr("charter.catalog.resolve_doctrine_root", lambda: built_in_root)
    monkeypatch.setattr("charter.context.infer_repo_languages", lambda repo_root: ["python", "typescript"])
    monkeypatch.setattr("doctrine.service.DoctrineService", StubDoctrineService)

    service = _build_doctrine_service(tmp_path)

    assert isinstance(service, StubDoctrineService)
    assert calls == {
        "built_in_root": built_in_root,
        "project_root": project_root,
        "active_languages": ["python", "typescript"],
    }
