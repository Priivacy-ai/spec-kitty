"""Unit tests for requirement_mapping module."""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.requirement_mapping import (
    compute_coverage,
    normalize_requirement_refs_value,
    parse_requirement_ids_from_spec_md,
    read_all_wp_requirement_refs,
    validate_ref_format,
    validate_refs,
)


class TestValidateRefs:
    """Test ref validation against spec IDs."""

    def test_all_valid(self):
        valid, unknown = validate_refs(
            ["FR-001", "NFR-002"], {"FR-001", "NFR-002", "FR-003"}
        )
        assert valid == ["FR-001", "NFR-002"]
        assert unknown == []

    def test_some_unknown(self):
        valid, unknown = validate_refs(
            ["FR-001", "FR-999"], {"FR-001", "FR-002"}
        )
        assert valid == ["FR-001"]
        assert unknown == ["FR-999"]

    def test_case_insensitive(self):
        valid, unknown = validate_refs(["fr-001"], {"FR-001"})
        assert valid == ["FR-001"]
        assert unknown == []


class TestValidateRefFormat:
    """Test ref format validation."""

    def test_valid_formats(self):
        well_formed, malformed = validate_ref_format(
            ["FR-001", "NFR-002", "C-003"]
        )
        assert well_formed == ["FR-001", "NFR-002", "C-003"]
        assert malformed == []

    def test_malformed_formats(self):
        well_formed, malformed = validate_ref_format(
            ["FR-001", "INVALID", "REQ-001"]
        )
        assert well_formed == ["FR-001"]
        assert malformed == ["INVALID", "REQ-001"]


class TestComputeCoverage:
    """Test coverage summary computation."""

    def test_full_coverage(self):
        mappings = {"WP01": ["FR-001", "FR-002"], "WP02": ["FR-003"]}
        coverage = compute_coverage(mappings, {"FR-001", "FR-002", "FR-003"})
        assert coverage["total_functional"] == 3
        assert coverage["mapped_functional"] == 3
        assert coverage["unmapped_functional"] == []

    def test_partial_coverage(self):
        mappings = {"WP01": ["FR-001"]}
        coverage = compute_coverage(
            mappings, {"FR-001", "FR-002", "FR-003"}
        )
        assert coverage["total_functional"] == 3
        assert coverage["mapped_functional"] == 1
        assert sorted(coverage["unmapped_functional"]) == ["FR-002", "FR-003"]

    def test_empty_mappings(self):
        coverage = compute_coverage({}, {"FR-001", "FR-002"})
        assert coverage["total_functional"] == 2
        assert coverage["mapped_functional"] == 0
        assert len(coverage["unmapped_functional"]) == 2


class TestParseRequirementIdsFromSpecMd:
    """Test spec.md ID extraction."""

    def test_extracts_fr_nfr_c(self):
        content = """
| FR-001 | First req |
| FR-002 | Second req |
| NFR-001 | Non-functional |
| C-001 | Constraint |
"""
        result = parse_requirement_ids_from_spec_md(content)
        assert "FR-001" in result["all"]
        assert "NFR-001" in result["all"]
        assert "C-001" in result["all"]
        assert result["functional"] == ["FR-001", "FR-002"]

    def test_case_insensitive(self):
        content = "fr-001 and nfr-002"
        result = parse_requirement_ids_from_spec_md(content)
        assert "FR-001" in result["all"]
        assert "NFR-002" in result["all"]


class TestNormalizeRequirementRefsValue:
    """Test normalize_requirement_refs_value()."""

    def test_string_input(self):
        assert normalize_requirement_refs_value("FR-001, FR-002") == [
            "FR-001",
            "FR-002",
        ]

    def test_list_of_strings(self):
        assert normalize_requirement_refs_value(["FR-001", "NFR-002"]) == [
            "FR-001",
            "NFR-002",
        ]

    def test_mixed_list(self):
        # Non-string items are skipped
        assert normalize_requirement_refs_value(["FR-001", 42, "NFR-002"]) == [
            "FR-001",
            "NFR-002",
        ]

    def test_empty_list(self):
        assert normalize_requirement_refs_value([]) == []

    def test_none(self):
        assert normalize_requirement_refs_value(None) == []

    def test_deduplicates(self):
        assert normalize_requirement_refs_value(["FR-001", "FR-001"]) == [
            "FR-001",
        ]

    def test_uppercases(self):
        assert normalize_requirement_refs_value(["fr-001"]) == ["FR-001"]


class TestReadAllWpRequirementRefs:
    """Test read_all_wp_requirement_refs()."""

    def test_reads_from_wp_frontmatter(self, tmp_path: Path):
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        (tasks_dir / "WP01-test.md").write_text(
            '---\nwork_package_id: "WP01"\ntitle: "WP01"\n'
            "requirement_refs:\n  - FR-001\n  - FR-002\n---\n\n# WP01\n",
            encoding="utf-8",
        )
        (tasks_dir / "WP02-test.md").write_text(
            '---\nwork_package_id: "WP02"\ntitle: "WP02"\n---\n\n# WP02\n',
            encoding="utf-8",
        )

        result = read_all_wp_requirement_refs(tasks_dir)
        assert result["WP01"] == ["FR-001", "FR-002"]
        assert result["WP02"] == []

    def test_returns_empty_for_missing_dir(self, tmp_path: Path):
        assert read_all_wp_requirement_refs(tmp_path / "nonexistent") == {}
