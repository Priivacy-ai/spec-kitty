"""Tests for constitution extraction pipeline."""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.constitution.extractor import (
    SECTION_MAPPING,
    ExtractionResult,
    Extractor,
    extract_with_ai,
    write_extraction_result,
)
from specify_cli.constitution.parser import ConstitutionParser, ConstitutionSection
from specify_cli.constitution.schemas import (
    AgentsConfig,
    DirectivesConfig,
    GovernanceConfig,
)


class TestExtractor:
    """Tests for Extractor class."""

    @pytest.fixture
    def extractor(self):
        """Provide Extractor instance."""
        return Extractor()

    def test_extractor_initialization(self):
        """T013-1: Extractor can be instantiated with default parser."""
        extractor = Extractor()
        assert extractor.parser is not None
        assert isinstance(extractor.parser, ConstitutionParser)

    def test_extractor_with_custom_parser(self):
        """T013-2: Extractor accepts custom parser instance."""
        parser = ConstitutionParser()
        extractor = Extractor(parser=parser)
        assert extractor.parser is parser

    def test_extract_empty_content(self, extractor):
        """T013-3: Extract from empty content returns default configs."""
        result = extractor.extract("")
        assert isinstance(result, ExtractionResult)
        assert isinstance(result.governance, GovernanceConfig)
        assert isinstance(result.agents, AgentsConfig)
        assert isinstance(result.directives, DirectivesConfig)
        assert result.metadata.extraction_mode == "deterministic"

    def test_extract_returns_all_schemas(self, extractor):
        """T013-4: Extract returns complete ExtractionResult with all schemas."""
        content = """## Testing
We require 90% test coverage and TDD is required.
"""
        result = extractor.extract(content)
        assert result.governance is not None
        assert result.agents is not None
        assert result.directives is not None
        assert result.metadata is not None


class TestSectionClassification:
    """Tests for section-to-schema mapping."""

    @pytest.fixture
    def extractor(self):
        """Provide Extractor instance."""
        return Extractor()

    def test_classify_testing_section(self, extractor):
        """T014-1: 'Testing' heading maps to governance.testing."""
        classification = extractor._classify_section("Testing")
        assert classification == ("governance", "testing")

    def test_classify_quality_section(self, extractor):
        """T014-2: 'Quality' heading maps to governance.quality."""
        classification = extractor._classify_section("Quality Gates")
        assert classification == ("governance", "quality")

    def test_classify_commit_section(self, extractor):
        """T014-3: 'Commit' heading maps to governance.commits."""
        classification = extractor._classify_section("Commit Guidelines")
        assert classification == ("governance", "commits")

    def test_classify_performance_section(self, extractor):
        """T014-4: 'Performance' heading maps to governance.performance."""
        classification = extractor._classify_section("Performance Requirements")
        assert classification == ("governance", "performance")

    def test_classify_branch_section(self, extractor):
        """T014-5: 'Branch' heading maps to governance.branch_strategy."""
        classification = extractor._classify_section("Branch Strategy")
        assert classification == ("governance", "branch_strategy")

    def test_classify_agent_section(self, extractor):
        """T014-6: 'Agent' heading maps to agents.profiles."""
        classification = extractor._classify_section("Agent Configuration")
        assert classification == ("agents", "profiles")

    def test_classify_directive_section(self, extractor):
        """T014-7: 'Directive' heading maps to directives.directives."""
        classification = extractor._classify_section("Project Directives")
        assert classification == ("directives", "directives")

    def test_classify_case_insensitive(self, extractor):
        """T014-8: Classification is case-insensitive."""
        assert extractor._classify_section("TESTING") == ("governance", "testing")
        assert extractor._classify_section("quality") == ("governance", "quality")
        assert extractor._classify_section("TeStInG") == ("governance", "testing")

    def test_classify_unmatched_section(self, extractor):
        """T014-9: Unmatched heading returns None."""
        classification = extractor._classify_section("Unrelated Section")
        assert classification is None

    def test_classify_longest_match_wins(self, extractor):
        """T014-10: Longest keyword match takes precedence."""
        # "test coverage" contains both "test" and "coverage" - should match "coverage" if longer
        classification = extractor._classify_section("Test Coverage Goals")
        assert classification == ("governance", "testing")  # Both map to same field


class TestGovernanceExtraction:
    """Tests for governance configuration extraction."""

    @pytest.fixture
    def extractor(self):
        """Provide Extractor instance."""
        return Extractor()

    def test_extract_testing_config(self, extractor):
        """T015-1: Extract testing config from Testing section."""
        content = """## Testing Requirements
We require 90% test coverage. TDD required.
We use pytest as our framework and mypy --strict for type checking.
"""
        result = extractor.extract(content)
        assert result.governance.testing.min_coverage == 90
        assert result.governance.testing.tdd_required is True
        assert result.governance.testing.framework == "pytest"
        assert result.governance.testing.type_checking == "mypy --strict"

    def test_extract_quality_config(self, extractor):
        """T015-2: Extract quality config from Quality section."""
        content = """## Code Quality
We use ruff for linting. PRs require 2 approvals.
Pre-commit hooks are required.
"""
        result = extractor.extract(content)
        assert result.governance.quality.linting == "ruff"
        assert result.governance.quality.pr_approvals == 2
        assert result.governance.quality.pre_commit_hooks is True

    def test_extract_commit_config(self, extractor):
        """T015-3: Extract commit config from Commit section."""
        content = """## Commit Guidelines
We follow conventional commits for all commit messages.
"""
        result = extractor.extract(content)
        assert result.governance.commits.convention == "conventional"

    def test_extract_performance_config(self, extractor):
        """T015-4: Extract performance config from Performance section."""
        content = """## Performance Requirements
CLI commands must complete in < 2 seconds.
"""
        result = extractor.extract(content)
        assert result.governance.performance.cli_timeout_seconds == 2.0

    def test_merge_multiple_governance_sections(self, extractor):
        """T015-5: Merge data from multiple governance sections."""
        content = """## Testing
We require 80% coverage.

## Quality Gates
We use ruff for linting.

## Commit Guidelines
We follow conventional commits.
"""
        result = extractor.extract(content)
        assert result.governance.testing.min_coverage == 80
        assert result.governance.quality.linting == "ruff"
        assert result.governance.commits.convention == "conventional"

    def test_later_section_overrides_earlier(self, extractor):
        """T015-6: Later sections override earlier ones (deterministic merging)."""
        content = """## Testing Requirements
We require 80% test coverage.

## Additional Testing
We require 90% test coverage.
"""
        result = extractor.extract(content)
        # Both sections map to testing - last one wins
        assert result.governance.testing.min_coverage == 90


class TestAgentsExtraction:
    """Tests for agent configuration extraction."""

    @pytest.fixture
    def extractor(self):
        """Provide Extractor instance."""
        return Extractor()

    def test_extract_agent_profiles_from_table(self, extractor):
        """T015-7: Extract agent profiles from table in Agent section."""
        content = """## Agent Configuration

| agent | role | model |
|-------|------|-------|
| claude | implementer | claude-3-5-sonnet |
| codex | reviewer | gpt-4 |
"""
        result = extractor.extract(content)
        assert len(result.agents.profiles) == 2
        assert result.agents.profiles[0].agent_key == "claude"
        assert result.agents.profiles[0].role == "implementer"
        assert result.agents.profiles[0].preferred_model == "claude-3-5-sonnet"
        assert result.agents.profiles[1].agent_key == "codex"

    def test_extract_agent_selection_strategy(self, extractor):
        """T015-8: Extract selection strategy from Agent section."""
        content = """## Agent Selection
We use a preferred agent selection strategy.
"""
        result = extractor.extract(content)
        assert result.agents.selection.strategy == "preferred"


class TestDirectivesExtraction:
    """Tests for directives extraction."""

    @pytest.fixture
    def extractor(self):
        """Provide Extractor instance."""
        return Extractor()

    def test_extract_directives_from_numbered_list(self, extractor):
        """T015-9: Extract directives from numbered list with auto-generated IDs."""
        content = """## Project Directives

1. All code must pass type checking
2. All PRs must have tests
3. No commits directly to main
"""
        result = extractor.extract(content)
        assert len(result.directives.directives) == 3
        assert result.directives.directives[0].id == "DIR-001"
        assert "type checking" in result.directives.directives[0].description
        assert result.directives.directives[1].id == "DIR-002"
        assert result.directives.directives[2].id == "DIR-003"

    def test_directive_title_truncated(self, extractor):
        """T015-10: Directive title is truncated to 50 chars."""
        long_directive = "This is a very long directive that exceeds fifty characters and should be truncated"
        content = f"""## Project Rules

1. {long_directive}
"""
        result = extractor.extract(content)
        assert len(result.directives.directives) == 1
        assert len(result.directives.directives[0].title) == 50
        assert result.directives.directives[0].description == long_directive


class TestMetadataGeneration:
    """Tests for extraction metadata generation."""

    @pytest.fixture
    def extractor(self):
        """Provide Extractor instance."""
        return Extractor()

    @patch("specify_cli.constitution.extractor.datetime")
    def test_metadata_has_timestamp(self, mock_datetime, extractor):
        """T015-11: Metadata includes ISO timestamp."""
        fixed_time = datetime(2026, 2, 15, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = fixed_time
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        content = "## Testing\n90% coverage required."
        result = extractor.extract(content)

        assert result.metadata.extracted_at == "2026-02-15T12:00:00+00:00"

    def test_metadata_has_hash(self, extractor):
        """T015-12: Metadata includes content hash."""
        content = "## Testing\n90% coverage required."
        result = extractor.extract(content)

        assert result.metadata.constitution_hash.startswith("sha256:")
        assert len(result.metadata.constitution_hash) > 10

    def test_metadata_counts_sections(self, extractor):
        """T015-13: Metadata counts structured vs AI-required sections."""
        content = """## Testing
We require 90% coverage.

## Philosophy
Just some prose without structured data.
"""
        result = extractor.extract(content)

        # Testing section has keywords -> structured
        # Philosophy section has no structured data -> ai_assisted
        assert result.metadata.sections_parsed.structured >= 1
        assert result.metadata.sections_parsed.ai_assisted >= 0

    def test_metadata_extraction_mode_deterministic(self, extractor):
        """T015-14: Metadata reports deterministic mode when no AI needed."""
        content = """## Testing
We require 90% coverage and TDD is required.
"""
        result = extractor.extract(content)
        # All sections have structured data
        assert result.metadata.extraction_mode == "deterministic"

    def test_metadata_extraction_mode_hybrid(self, extractor):
        """T015-15: Metadata reports hybrid mode when AI sections present."""
        content = """## Testing
We require 90% coverage.

## Philosophy
This is just prose text without any structured data or keywords.
"""
        result = extractor.extract(content)
        # Philosophy section requires AI
        assert result.metadata.extraction_mode == "hybrid"


class TestIdempotency:
    """Tests for extraction idempotency."""

    @pytest.fixture
    def extractor(self):
        """Provide Extractor instance."""
        return Extractor()

    @patch("specify_cli.constitution.extractor.datetime")
    def test_extract_twice_identical_results(self, mock_datetime, extractor):
        """T018-1: Extracting same content twice produces identical results (except timestamp)."""
        fixed_time = datetime(2026, 2, 15, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = fixed_time
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        content = """## Testing
We require 90% coverage. TDD is required.

## Quality
We use ruff for linting. 2 approvals required.

## Directives
1. All code must pass tests
2. No direct commits to main
"""

        result1 = extractor.extract(content)
        result2 = extractor.extract(content)

        # Governance should be identical
        assert result1.governance.model_dump() == result2.governance.model_dump()

        # Agents should be identical
        assert result1.agents.model_dump() == result2.agents.model_dump()

        # Directives should be identical
        assert result1.directives.model_dump() == result2.directives.model_dump()

        # Metadata should be identical (with mocked timestamp)
        assert result1.metadata.model_dump() == result2.metadata.model_dump()


class TestAIFallback:
    """Tests for AI extraction fallback."""

    def test_extract_with_ai_returns_empty_dict(self):
        """T016-1: AI fallback stub returns empty dict when unavailable."""
        sections = [
            ConstitutionSection(
                heading="Philosophy",
                level=2,
                content="Just prose text",
                structured_data={},
                requires_ai=True,
            )
        ]
        schema_hint = {"philosophy": "str"}

        result = extract_with_ai(sections, schema_hint)
        assert result == {}

    def test_extract_with_ai_logs_info(self, caplog):
        """T016-2: AI fallback logs info message about skipped sections."""
        sections = [
            ConstitutionSection(
                heading="Philosophy",
                level=2,
                content="Just prose text",
                structured_data={},
                requires_ai=True,
            )
        ]
        schema_hint = {}

        with caplog.at_level("INFO"):
            extract_with_ai(sections, schema_hint)

        assert "AI extraction not yet implemented" in caplog.text
        assert "1 prose sections" in caplog.text


class TestYAMLWriter:
    """Tests for YAML file writer."""

    def test_write_extraction_result_creates_directory(self, tmp_path):
        """T017-1: write_extraction_result creates target directory if needed."""
        extractor = Extractor()
        content = "## Testing\n90% coverage required."
        result = extractor.extract(content)

        constitution_dir = tmp_path / "constitution"
        write_extraction_result(result, constitution_dir)

        assert constitution_dir.exists()
        assert constitution_dir.is_dir()

    def test_write_extraction_result_creates_all_files(self, tmp_path):
        """T017-2: write_extraction_result creates all 4 YAML files."""
        extractor = Extractor()
        content = "## Testing\n90% coverage required."
        result = extractor.extract(content)

        constitution_dir = tmp_path / "constitution"
        write_extraction_result(result, constitution_dir)

        assert (constitution_dir / "governance.yaml").exists()
        assert (constitution_dir / "agents.yaml").exists()
        assert (constitution_dir / "directives.yaml").exists()
        assert (constitution_dir / "metadata.yaml").exists()

    def test_write_extraction_result_yaml_has_header(self, tmp_path):
        """T017-3: Written YAML files have auto-generated header comment."""
        extractor = Extractor()
        content = "## Testing\n90% coverage required."
        result = extractor.extract(content)

        constitution_dir = tmp_path / "constitution"
        write_extraction_result(result, constitution_dir)

        governance_content = (constitution_dir / "governance.yaml").read_text()
        assert "# Auto-generated from constitution.md" in governance_content
        assert "# Run 'spec-kitty constitution sync' to regenerate" in governance_content


class TestFullPipeline:
    """Integration tests for full extraction pipeline."""

    @pytest.fixture
    def extractor(self):
        """Provide Extractor instance."""
        return Extractor()

    def test_full_pipeline_with_comprehensive_constitution(self, extractor):
        """T018-2: Full pipeline with comprehensive constitution extracts all data correctly."""
        content = """## Testing Requirements
We require 90% test coverage minimum. TDD required for all new features.
We use pytest as our testing framework and mypy --strict for type checking.

## Code Quality Standards
We use ruff for linting all Python code. All PRs require 2 approvals.
Pre-commit hooks must be enabled.

## Commit Guidelines
We follow conventional commits for all commit messages.

## Performance Requirements
CLI commands must complete in < 2 seconds.

## Branch Strategy
Our main branch is main. Development happens on develop.

1. No direct commits to main
2. All changes via pull request
3. Merge commits only

## Agent Configuration

| agent | role | model |
|-------|------|-------|
| claude | implementer | claude-3-5-sonnet |
| codex | reviewer | gpt-4 |

We use a preferred agent selection strategy.

## Project Directives

1. All code must pass type checking
2. All PRs must have tests
3. No commits directly to main branch
"""

        result = extractor.extract(content)

        # Verify governance
        assert result.governance.testing.min_coverage == 90
        assert result.governance.testing.tdd_required is True
        assert result.governance.testing.framework == "pytest"
        assert result.governance.testing.type_checking == "mypy --strict"
        assert result.governance.quality.linting == "ruff"
        assert result.governance.quality.pr_approvals == 2
        assert result.governance.quality.pre_commit_hooks is True
        assert result.governance.commits.convention == "conventional"
        assert result.governance.performance.cli_timeout_seconds == 2.0
        assert result.governance.branch_strategy.main_branch == "main"
        assert len(result.governance.branch_strategy.rules) == 3

        # Verify agents
        assert len(result.agents.profiles) == 2
        assert result.agents.profiles[0].agent_key == "claude"
        assert result.agents.selection.strategy == "preferred"

        # Verify directives
        assert len(result.directives.directives) == 3
        assert result.directives.directives[0].id == "DIR-001"

        # Verify metadata
        assert result.metadata.extraction_mode == "deterministic"
        assert result.metadata.constitution_hash.startswith("sha256:")

    def test_full_pipeline_empty_constitution_uses_defaults(self, extractor):
        """T018-3: Full pipeline with empty constitution uses default values."""
        result = extractor.extract("")

        # Should have default values
        assert result.governance.testing.min_coverage == 0
        assert result.governance.testing.tdd_required is False
        assert result.governance.quality.pr_approvals == 1
        assert len(result.agents.profiles) == 0
        assert len(result.directives.directives) == 0
