"""Unit tests for requirement_mapping module."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.requirement_mapping import (
    MAPPING_FILENAME,
    compute_coverage,
    load_requirement_mapping,
    parse_requirement_ids_from_spec_md,
    save_requirement_mapping,
    validate_ref_format,
    validate_refs,
)


class TestLoadSaveRoundTrip:
    """Test JSON persistence round-trip."""

    def test_load_returns_empty_when_missing(self, tmp_path: Path):
        assert load_requirement_mapping(tmp_path) == {}

    def test_save_and_load_round_trip(self, tmp_path: Path):
        mappings = {"WP01": ["FR-001", "FR-002"], "WP02": ["NFR-001"]}
        save_requirement_mapping(tmp_path, mappings)
        loaded = load_requirement_mapping(tmp_path)
        assert loaded == {"WP01": ["FR-001", "FR-002"], "WP02": ["NFR-001"]}

    def test_save_uppercases_refs(self, tmp_path: Path):
        save_requirement_mapping(tmp_path, {"WP01": ["fr-001", "nfr-002"]})
        loaded = load_requirement_mapping(tmp_path)
        assert loaded == {"WP01": ["FR-001", "NFR-002"]}

    def test_save_deduplicates_refs(self, tmp_path: Path):
        save_requirement_mapping(tmp_path, {"WP01": ["FR-001", "FR-001", "FR-002"]})
        loaded = load_requirement_mapping(tmp_path)
        assert loaded["WP01"] == ["FR-001", "FR-002"]

    def test_load_returns_empty_on_malformed_json(self, tmp_path: Path):
        (tmp_path / MAPPING_FILENAME).write_text("not json", encoding="utf-8")
        assert load_requirement_mapping(tmp_path) == {}

    def test_load_returns_empty_on_missing_mappings_key(self, tmp_path: Path):
        (tmp_path / MAPPING_FILENAME).write_text('{"version": 1}', encoding="utf-8")
        assert load_requirement_mapping(tmp_path) == {}

    def test_save_includes_version_and_timestamp(self, tmp_path: Path):
        save_requirement_mapping(tmp_path, {"WP01": ["FR-001"]})
        data = json.loads((tmp_path / MAPPING_FILENAME).read_text(encoding="utf-8"))
        assert data["version"] == 1
        assert "updated_at" in data
        assert "mappings" in data


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
