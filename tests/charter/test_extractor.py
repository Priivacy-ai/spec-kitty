"""Tests for the charter extraction pipeline (IC-04 / WP04 retirement).

The heading-classification dispatch (``SECTION_MAPPING`` / ``_classify_section``)
that used to drive ``governance.testing``/``.quality``/``.commits``/
``.performance``/``.branch_strategy`` and ``directives.directives`` extraction
from ``charter.md`` prose is RETIRED -- those fields are hand-authored
directly in ``charter.yaml`` now (see ``tests/charter/test_integration.py``).
The scraper tests that pinned that dispatch table (``TestSectionClassification``,
``TestExtractGovernanceDispatch``, the prose-driven halves of
``TestGovernanceExtraction`` / ``TestDirectivesExtraction``, ``TestAIFallback``,
``TestYAMLWriter``) are retired below in favor of retirement-contract tests
that pin the NEW behavior: ``extract()`` still runs end-to-end, but the
retired fields stay at schema defaults.

Still live and still tested here: doctrine-selection extraction and
``Extractor``'s metadata/idempotency contract -- both scan every section
unconditionally, unaffected by the classification-table retirement.
"""

from datetime import datetime, UTC
from unittest.mock import patch

import pytest

from charter.extractor import (
    ExtractionResult,
    Extractor,
)
from charter.parser import CharterParser
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


class TestGovernanceExtraction:
    @pytest.fixture
    def extractor(self) -> Extractor:
        return Extractor()

    def test_extract_doctrine_selection_from_yaml_block(self, extractor: Extractor) -> None:
        """Doctrine-selection extraction is still live -- it scans every
        section unconditionally (never gated by heading classification)."""
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


# ---------------------------------------------------------------------------
# IC-04 / WP04: retirement-contract tests (replace the T013 SECTION_MAPPING
# dispatch characterisation + the prose-driven governance/directives tests
# retired above). These pin the NEW behavior: extract() still runs
# end-to-end, but the retired prose->triad fields stay at schema defaults.
# ---------------------------------------------------------------------------


class TestProseScrapeRetired:
    @pytest.fixture
    def extractor(self) -> Extractor:
        return Extractor()

    def test_governance_testing_quality_commits_stay_at_defaults(self, extractor: Extractor) -> None:
        """Prose that would have populated testing/quality/commits under
        the retired SECTION_MAPPING dispatch no longer does."""
        content = (
            "## Testing\n90% coverage. TDD required. pytest framework.\n\n"
            "## Code Quality\nruff for linting. 2 approvals required.\n\n"
            "## Commit Guidelines\nWe follow conventional commits.\n"
        )
        result = extractor.extract(content)
        assert result.governance.testing.min_coverage == 0
        assert result.governance.testing.tdd_required is False
        assert result.governance.quality.linting == ""
        assert result.governance.commits.convention is None

    def test_governance_performance_branch_strategy_stay_at_defaults(self, extractor: Extractor) -> None:
        content = (
            "## Performance Benchmarks\nCLI operations must complete < 30 seconds.\n\n"
            "## Branch Strategy\n\n"
            "| branch | policy |\n"
            "|--------|--------|\n"
            "| develop | dev |\n"
        )
        result = extractor.extract(content)
        assert result.governance.performance.cli_timeout_seconds == 2.0
        assert result.governance.branch_strategy.dev_branch is None

    def test_directives_are_always_empty(self, extractor: Extractor) -> None:
        """Numbered-list directive scraping (and its DIR-NNN id minting) is
        retired -- directives.directives is unconditionally empty."""
        content = "## Project Directives\n\n1. All code must pass type checking\n2. All PRs must have tests\n"
        result = extractor.extract(content)
        assert result.directives.directives == []

    def test_classify_section_and_section_mapping_are_removed(self) -> None:
        """Guard-rail: SECTION_MAPPING / _classify_section must not be
        reintroduced -- their retirement is INV-3's structural half."""
        import charter.extractor as extractor_module

        assert not hasattr(extractor_module, "SECTION_MAPPING")
        assert not hasattr(extractor_module.Extractor, "_classify_section")

    def test_extract_with_ai_and_write_extraction_result_are_removed(self) -> None:
        import charter.extractor as extractor_module

        assert not hasattr(extractor_module, "extract_with_ai")
        assert not hasattr(extractor_module, "write_extraction_result")
