"""Tests for charter extraction pipeline."""

from datetime import datetime, UTC
from unittest.mock import patch

import pytest

from charter.extractor import (
    ExtractionResult,
    Extractor,
    extract_with_ai,
    write_extraction_result,
)
from charter.parser import CharterParser, CharterSection
from charter.schemas import (
    DirectivesConfig,
    GovernanceConfig,
)

pytestmark = pytest.mark.fast


class TestExtractor:
    @pytest.fixture
    def extractor(self) -> Extractor:
        return Extractor()

    def test_extractor_initialization(self) -> None:
        extractor = Extractor()
        assert extractor.parser is not None
        assert isinstance(extractor.parser, CharterParser)

    def test_extractor_with_custom_parser(self) -> None:
        parser = CharterParser()
        extractor = Extractor(parser=parser)
        assert extractor.parser is parser

    def test_extract_empty_content(self, extractor: Extractor) -> None:
        result = extractor.extract("")
        assert isinstance(result, ExtractionResult)
        assert isinstance(result.governance, GovernanceConfig)
        assert isinstance(result.directives, DirectivesConfig)
        assert result.metadata.extraction_mode == "deterministic"

    def test_extract_returns_all_schemas(self, extractor: Extractor) -> None:
        content = "## Testing\nWe require 90% test coverage and TDD is required.\n"
        result = extractor.extract(content)
        assert result.governance is not None
        assert result.directives is not None
        assert result.metadata is not None


class TestSectionClassification:
    @pytest.fixture
    def extractor(self) -> Extractor:
        return Extractor()

    def test_classify_testing_section(self, extractor: Extractor) -> None:
        assert extractor._classify_section("Testing") == ("governance", "testing")

    def test_classify_quality_section(self, extractor: Extractor) -> None:
        assert extractor._classify_section("Quality Gates") == ("governance", "quality")

    def test_classify_commit_section(self, extractor: Extractor) -> None:
        assert extractor._classify_section("Commit Guidelines") == ("governance", "commits")

    def test_classify_directive_section(self, extractor: Extractor) -> None:
        assert extractor._classify_section("Project Directives") == ("directives", "directives")

    def test_classify_case_insensitive(self, extractor: Extractor) -> None:
        assert extractor._classify_section("TESTING") == ("governance", "testing")
        assert extractor._classify_section("quality") == ("governance", "quality")

    def test_classify_unmatched_section(self, extractor: Extractor) -> None:
        assert extractor._classify_section("Unrelated Section") is None


class TestGovernanceExtraction:
    @pytest.fixture
    def extractor(self) -> Extractor:
        return Extractor()

    def test_extract_testing_config(self, extractor: Extractor) -> None:
        content = """## Testing Requirements
We require 90% test coverage. TDD required.
We use pytest as our framework and mypy --strict for type checking.
"""
        result = extractor.extract(content)
        assert result.governance.testing.min_coverage == 90
        assert result.governance.testing.tdd_required is True
        assert result.governance.testing.framework == "pytest"
        assert result.governance.testing.type_checking == "mypy --strict"

    def test_extract_quality_config(self, extractor: Extractor) -> None:
        content = """## Code Quality
We use ruff for linting. PRs require 2 approvals.
Pre-commit hooks are required.
"""
        result = extractor.extract(content)
        assert result.governance.quality.linting == "ruff"
        assert result.governance.quality.pr_approvals == 2
        assert result.governance.quality.pre_commit_hooks is True

    def test_extract_doctrine_selection_from_yaml_block(self, extractor: Extractor) -> None:
        content = """## Governance Activation

```yaml
selected_paradigms: [test-first]
selected_directives: [TEST_FIRST]
available_tools: [git, pytest]
template_set: software-dev-default
```
"""
        result = extractor.extract(content)
        doctrine = result.governance.doctrine
        assert doctrine.selected_paradigms == ["test-first"]
        assert doctrine.selected_directives == ["TEST_FIRST"]
        assert doctrine.available_tools == ["git", "pytest"]
        assert doctrine.template_set == "software-dev-default"


class TestDirectivesExtraction:
    @pytest.fixture
    def extractor(self) -> Extractor:
        return Extractor()

    def test_extract_directives_from_numbered_list(self, extractor: Extractor) -> None:
        content = """## Project Directives

1. All code must pass type checking
2. All PRs must have tests
3. No commits directly to main
"""
        result = extractor.extract(content)
        assert len(result.directives.directives) == 3
        assert result.directives.directives[0].id == "DIR-001"
        assert result.directives.directives[1].id == "DIR-002"
        assert result.directives.directives[2].id == "DIR-003"


class TestMetadataGeneration:
    @pytest.fixture
    def extractor(self) -> Extractor:
        return Extractor()

    @patch("charter.extractor.datetime")
    def test_metadata_has_timestamp(self, mock_datetime, extractor: Extractor) -> None:
        fixed_time = datetime(2026, 2, 15, 12, 0, 0, tzinfo=UTC)
        mock_datetime.now.return_value = fixed_time
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        result = extractor.extract("## Testing\n90% coverage required.")
        assert result.metadata.extracted_at == "2026-02-15T12:00:00+00:00"

    def test_metadata_has_hash(self, extractor: Extractor) -> None:
        result = extractor.extract("## Testing\n90% coverage required.")
        assert result.metadata.charter_hash.startswith("sha256:")


class TestIdempotency:
    @pytest.fixture
    def extractor(self) -> Extractor:
        return Extractor()

    @patch("charter.extractor.datetime")
    def test_extract_twice_identical_results(self, mock_datetime, extractor: Extractor) -> None:
        fixed_time = datetime(2026, 2, 15, 12, 0, 0, tzinfo=UTC)
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

        assert result1.governance.model_dump() == result2.governance.model_dump()
        assert result1.directives.model_dump() == result2.directives.model_dump()
        assert result1.metadata.model_dump() == result2.metadata.model_dump()


class TestAIFallback:
    def test_extract_with_ai_returns_empty_dict(self) -> None:
        sections = [
            CharterSection(
                heading="Philosophy",
                level=2,
                content="Just prose text",
                structured_data={},
                requires_ai=True,
            )
        ]
        assert extract_with_ai(sections, {"philosophy": "str"}) == {}

    def test_extract_with_ai_logs_info(self, caplog) -> None:
        sections = [
            CharterSection(
                heading="Philosophy",
                level=2,
                content="Just prose text",
                structured_data={},
                requires_ai=True,
            )
        ]
        with caplog.at_level("INFO"):
            extract_with_ai(sections, {})
        assert "AI extraction not yet implemented" in caplog.text


class TestYAMLWriter:
    def test_write_extraction_result_creates_directory(self, tmp_path) -> None:
        extractor = Extractor()
        result = extractor.extract("## Testing\n90% coverage required.")

        charter_dir = tmp_path / "charter"
        write_extraction_result(result, charter_dir)

        assert charter_dir.exists()
        assert charter_dir.is_dir()

    def test_write_extraction_result_creates_all_files(self, tmp_path) -> None:
        extractor = Extractor()
        result = extractor.extract("## Testing\n90% coverage required.")

        charter_dir = tmp_path / "charter"
        write_extraction_result(result, charter_dir)

        assert (charter_dir / "governance.yaml").exists()
        assert (charter_dir / "directives.yaml").exists()
        assert (charter_dir / "metadata.yaml").exists()

    def test_write_extraction_result_yaml_has_header(self, tmp_path) -> None:
        extractor = Extractor()
        result = extractor.extract("## Testing\n90% coverage required.")

        charter_dir = tmp_path / "charter"
        write_extraction_result(result, charter_dir)

        governance_content = (charter_dir / "governance.yaml").read_text()
        assert "# Auto-generated from charter.md" in governance_content
        assert "# Run 'spec-kitty charter sync' to regenerate" in governance_content


# ---------------------------------------------------------------------------
# T013: Characterisation tests for _extract_governance field dispatch
# ---------------------------------------------------------------------------


class TestExtractGovernanceDispatch:
    """T013: Lock observable behaviour of the 6-handler dispatch table.

    Each test exercises exactly one field_name bucket through the full
    extract pipeline. These tests must pass on unmodified code and must
    continue to pass after the T014 noqa removal and any T015 refactors.
    """

    @pytest.fixture
    def extractor(self) -> Extractor:
        return Extractor()

    def test_dispatch_testing_handler(self, extractor: Extractor) -> None:
        """testing field_name → _apply_testing_keywords fires."""
        content = "## Testing Standards\n90% coverage. TDD required. pytest framework."
        result = extractor.extract(content)
        assert result.governance.testing.min_coverage == 90
        assert result.governance.testing.tdd_required is True
        assert result.governance.testing.framework == "pytest"

    def test_dispatch_quality_handler(self, extractor: Extractor) -> None:
        """quality field_name → _apply_quality_keywords fires."""
        content = "## Code Quality\nruff for linting. 3 approvals required. pre-commit hooks required."
        result = extractor.extract(content)
        assert result.governance.quality.linting == "ruff"
        assert result.governance.quality.pr_approvals == 3
        assert result.governance.quality.pre_commit_hooks is True

    def test_dispatch_commits_handler(self, extractor: Extractor) -> None:
        """commits field_name → _apply_commits_keywords fires."""
        content = "## Commit Guidelines\nWe follow conventional commits for all changes."
        result = extractor.extract(content)
        assert result.governance.commits.convention == "conventional"

    def test_dispatch_performance_handler(self, extractor: Extractor) -> None:
        """performance field_name → _apply_performance_section fires."""
        content = "## Performance Benchmarks\nCLI operations must complete < 30 seconds."
        result = extractor.extract(content)
        assert result.governance.performance.cli_timeout_seconds == 30.0

    def test_dispatch_branch_strategy_handler(self, extractor: Extractor) -> None:
        """branch_strategy field_name → _apply_branch_strategy_section fires."""
        # Note: the handler reads the "branch" key (lowercase); headers must match.
        content = "## Branch Strategy\n\n| branch | policy |\n|--------|--------|\n| main | protected |\n| develop | dev |\n"
        result = extractor.extract(content)
        assert result.governance.branch_strategy.main_branch == "main"
        assert result.governance.branch_strategy.dev_branch == "develop"

    def test_dispatch_doctrine_handler(self, extractor: Extractor) -> None:
        """doctrine field_name → _merge_doctrine_selection fires."""
        content = "## Paradigm Selection\n\n```yaml\nselected_paradigms: [test-first]\navailable_tools: [git, pytest]\n```\n"
        result = extractor.extract(content)
        assert "test-first" in result.governance.doctrine.selected_paradigms
        assert "git" in result.governance.doctrine.available_tools

    def test_dispatch_unknown_section_is_ignored(self, extractor: Extractor) -> None:
        """Unclassified section heading → no handler fires, schema defaults preserved."""
        content = "## Unclassified Prose\nSome free-form text with no structured data.\n"
        result = extractor.extract(content)
        # Defaults: min_coverage=0, pr_approvals=1, convention=None (see schemas.py)
        assert result.governance.testing.min_coverage == 0
        assert result.governance.quality.pr_approvals == 1
        assert result.governance.commits.convention is None

    def test_dispatch_multiple_handlers_all_fire(self, extractor: Extractor) -> None:
        """Multiple sections → all relevant handlers fire independently."""
        content = "## Testing\n90% coverage. TDD required.\n\n## Code Quality\nruff linting. 2 approvals required.\n\n## Commit Guidelines\nConventional commits.\n"
        result = extractor.extract(content)
        assert result.governance.testing.min_coverage == 90
        assert result.governance.quality.linting == "ruff"
        assert result.governance.commits.convention == "conventional"

    def test_dispatch_non_governance_section_skipped(self, extractor: Extractor) -> None:
        """Directive sections are schema_name='directives', not 'governance' — skip."""
        content = "## Project Directives\n1. All code must pass tests.\n2. No direct commits to main.\n"
        result = extractor.extract(content)
        # Directive sections must NOT populate governance testing config (stays at default 0)
        assert result.governance.testing.min_coverage == 0
        # But they DO populate directives config
        assert len(result.directives.directives) == 2
