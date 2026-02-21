"""Tests for constitution schemas module."""

import tempfile
from pathlib import Path


from specify_cli.constitution.schemas import (
    AgentProfile,
    AgentsConfig,
    AgentSelectionConfig,
    BranchStrategyConfig,
    CommitConfig,
    Directive,
    DirectivesConfig,
    ExtractionMetadata,
    GovernanceConfig,
    PerformanceConfig,
    QualityConfig,
    SectionsParsed,
    ConstitutionTestingConfig,
    emit_yaml,
)


class TestConstitutionTestingConfig:
    """Tests for ConstitutionTestingConfig schema."""

    def test_default_values(self):
        """T027: ConstitutionTestingConfig has correct defaults."""
        config = ConstitutionTestingConfig()
        assert config.min_coverage == 0
        assert config.tdd_required is False
        assert config.framework == ""
        assert config.type_checking == ""

    def test_custom_values(self):
        """T028: ConstitutionTestingConfig accepts custom values."""
        config = ConstitutionTestingConfig(
            min_coverage=90,
            tdd_required=True,
            framework="pytest",
            type_checking="mypy --strict",
        )
        assert config.min_coverage == 90
        assert config.tdd_required is True


class TestQualityConfig:
    """Tests for QualityConfig schema."""

    def test_default_values(self):
        """T029: QualityConfig has correct defaults."""
        config = QualityConfig()
        assert config.linting == ""
        assert config.pr_approvals == 1
        assert config.pre_commit_hooks is False

    def test_custom_values(self):
        """T030: QualityConfig accepts custom values."""
        config = QualityConfig(linting="ruff", pr_approvals=2, pre_commit_hooks=True)
        assert config.linting == "ruff"
        assert config.pr_approvals == 2


class TestPerformanceConfig:
    """Tests for PerformanceConfig schema."""

    def test_default_values(self):
        """T031: PerformanceConfig has correct defaults."""
        config = PerformanceConfig()
        assert config.cli_timeout_seconds == 2.0
        assert config.dashboard_max_wps == 100

    def test_custom_values(self):
        """T032: PerformanceConfig accepts custom values."""
        config = PerformanceConfig(cli_timeout_seconds=5.0, dashboard_max_wps=200)
        assert config.cli_timeout_seconds == 5.0
        assert config.dashboard_max_wps == 200


class TestBranchStrategyConfig:
    """Tests for BranchStrategyConfig schema."""

    def test_default_values(self):
        """T033: BranchStrategyConfig has correct defaults."""
        config = BranchStrategyConfig()
        assert config.main_branch == "main"
        assert config.dev_branch is None
        assert config.rules == []

    def test_custom_values(self):
        """T034: BranchStrategyConfig accepts custom values."""
        config = BranchStrategyConfig(
            main_branch="master",
            dev_branch="develop",
            rules=["No direct commits to main"],
        )
        assert config.main_branch == "master"
        assert config.dev_branch == "develop"
        assert len(config.rules) == 1


class TestGovernanceConfig:
    """Tests for GovernanceConfig schema."""

    def test_default_values(self):
        """T035: GovernanceConfig has correct nested defaults."""
        config = GovernanceConfig()
        assert isinstance(config.testing, ConstitutionTestingConfig)
        assert isinstance(config.quality, QualityConfig)
        assert isinstance(config.performance, PerformanceConfig)
        assert config.enforcement == {}

    def test_custom_nested_values(self):
        """T036: GovernanceConfig accepts custom nested configs."""
        config = GovernanceConfig(
            testing=ConstitutionTestingConfig(min_coverage=90, tdd_required=True),
            quality=QualityConfig(linting="ruff"),
        )
        assert config.testing.min_coverage == 90
        assert config.quality.linting == "ruff"

    def test_full_config(self):
        """T037: GovernanceConfig can be fully populated."""
        config = GovernanceConfig(
            testing=ConstitutionTestingConfig(min_coverage=90, framework="pytest"),
            quality=QualityConfig(pr_approvals=2),
            commits=CommitConfig(convention="conventional"),
            performance=PerformanceConfig(cli_timeout_seconds=3.0),
            branch_strategy=BranchStrategyConfig(main_branch="main"),
            enforcement={"testing": "strict"},
        )
        assert config.testing.min_coverage == 90
        assert config.enforcement["testing"] == "strict"


class TestAgentProfile:
    """Tests for AgentProfile schema."""

    def test_required_field(self):
        """T038: AgentProfile requires agent_key."""
        profile = AgentProfile(agent_key="claude")
        assert profile.agent_key == "claude"
        assert profile.role == "implementer"

    def test_custom_values(self):
        """T039: AgentProfile accepts custom values."""
        profile = AgentProfile(
            agent_key="claude",
            role="reviewer",
            preferred_model="claude-3.5",
            capabilities=["python", "typescript"],
        )
        assert profile.role == "reviewer"
        assert len(profile.capabilities) == 2


class TestAgentsConfig:
    """Tests for AgentsConfig schema."""

    def test_default_values(self):
        """T040: AgentsConfig has correct defaults."""
        config = AgentsConfig()
        assert config.profiles == []
        assert isinstance(config.selection, AgentSelectionConfig)

    def test_with_profiles(self):
        """T041: AgentsConfig can contain multiple profiles."""
        config = AgentsConfig(
            profiles=[
                AgentProfile(agent_key="claude", role="implementer"),
                AgentProfile(agent_key="codex", role="reviewer"),
            ]
        )
        assert len(config.profiles) == 2


class TestDirective:
    """Tests for Directive schema."""

    def test_required_fields(self):
        """T042: Directive requires id and title."""
        directive = Directive(id="D001", title="Test Coverage")
        assert directive.id == "D001"
        assert directive.title == "Test Coverage"
        assert directive.severity == "warn"

    def test_custom_values(self):
        """T043: Directive accepts custom values."""
        directive = Directive(
            id="D001",
            title="TDD Required",
            description="All code must be test-driven",
            severity="error",
            applies_to=["python", "typescript"],
        )
        assert directive.severity == "error"
        assert len(directive.applies_to) == 2


class TestDirectivesConfig:
    """Tests for DirectivesConfig schema."""

    def test_default_values(self):
        """T044: DirectivesConfig has correct defaults."""
        config = DirectivesConfig()
        assert config.directives == []

    def test_with_directives(self):
        """T045: DirectivesConfig can contain multiple directives."""
        config = DirectivesConfig(
            directives=[
                Directive(id="D001", title="Coverage"),
                Directive(id="D002", title="TDD"),
            ]
        )
        assert len(config.directives) == 2


class TestExtractionMetadata:
    """Tests for ExtractionMetadata schema."""

    def test_default_values(self):
        """T046: ExtractionMetadata has correct defaults."""
        meta = ExtractionMetadata()
        assert meta.schema_version == "1.0.0"
        assert meta.extraction_mode == "deterministic"
        assert meta.source_path == ".kittify/constitution/constitution.md"
        assert isinstance(meta.sections_parsed, SectionsParsed)

    def test_custom_values(self):
        """T047: ExtractionMetadata accepts custom values."""
        meta = ExtractionMetadata(
            extracted_at="2026-01-27T10:00:00Z",
            constitution_hash="sha256:abc123",
            extraction_mode="hybrid",
            sections_parsed=SectionsParsed(structured=10, ai_assisted=5),
        )
        assert meta.extraction_mode == "hybrid"
        assert meta.sections_parsed.structured == 10


class TestEmitYAML:
    """Tests for emit_yaml function."""

    def test_emit_yaml_creates_file(self):
        """T048: emit_yaml creates YAML file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.yaml"
            config = ConstitutionTestingConfig(min_coverage=90, tdd_required=True)

            emit_yaml(config, output_path)

            assert output_path.exists()

    def test_emit_yaml_includes_header(self):
        """T049: emit_yaml includes auto-generated header comment."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.yaml"
            config = ConstitutionTestingConfig(min_coverage=90)

            emit_yaml(config, output_path)

            content = output_path.read_text()
            assert "Auto-generated from constitution.md" in content
            assert "do not edit directly" in content

    def test_emit_yaml_valid_structure(self):
        """T050: emit_yaml produces valid YAML with correct values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.yaml"
            config = ConstitutionTestingConfig(
                min_coverage=90,
                tdd_required=True,
                framework="pytest",
            )

            emit_yaml(config, output_path)

            content = output_path.read_text()
            assert "min_coverage: 90" in content
            assert "tdd_required: true" in content
            assert "framework: pytest" in content

    def test_emit_yaml_nested_config(self):
        """T051: emit_yaml handles nested configs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "governance.yaml"
            config = GovernanceConfig(
                testing=ConstitutionTestingConfig(min_coverage=90),
                quality=QualityConfig(linting="ruff"),
            )

            emit_yaml(config, output_path)

            content = output_path.read_text()
            assert "testing:" in content
            assert "quality:" in content
            assert "min_coverage: 90" in content

    def test_emit_yaml_list_fields(self):
        """T052: emit_yaml handles list fields correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "directives.yaml"
            config = DirectivesConfig(
                directives=[
                    Directive(id="D001", title="Coverage"),
                    Directive(id="D002", title="TDD"),
                ]
            )

            emit_yaml(config, output_path)

            content = output_path.read_text()
            assert "directives:" in content
            assert "D001" in content
            assert "D002" in content

    def test_emit_yaml_empty_lists(self):
        """T053: emit_yaml handles empty lists correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "agents.yaml"
            config = AgentsConfig(profiles=[])

            emit_yaml(config, output_path)

            content = output_path.read_text()
            assert "profiles: []" in content or "profiles:\n" in content
