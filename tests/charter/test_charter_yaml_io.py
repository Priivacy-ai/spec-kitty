"""Tests for the shared charter.yaml write helper (WP01 / T003 / INV-9).

Three independent writers (activation_engine.commit_plan, pack_manager.
merge_defaults, compiler.write_compiled_charter) must route through this ONE
``load -> mutate-owned-section -> round-trip-save`` helper so section
preservation is structural, not conventional (Landmine 3 / alphonso
MAJOR-3). These tests prove the byte-preservation guarantee: mutating one
named section leaves every other section's formatting (including comments)
untouched.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from charter.charter_yaml_io import (
    OWNED_SECTIONS,
    UnknownCharterYamlSectionError,
    load_charter_yaml,
    save_charter_yaml,
    update_charter_yaml_section,
)


pytestmark = [pytest.mark.unit]


_FIXTURE = """\
schema_version: "2.0.0"
governance:
  testing:
    min_coverage: 80  # GOV-COMMENT-MARKER preserved
  quality: {}
  commits: {}
  performance: {}
  branch_strategy: {}
  doctrine: {}
  activations: []
  enforcement: {}
directives:
  directives: []
catalog:
  mission: software-dev
  template_set: software-dev-default  # CATALOG-COMMENT-MARKER preserved
  languages:
  - python
  references: []
activated_kinds:
- directives
mission_type_activations:
- software-dev
activated_directives: []
activated_tactics:
activated_styleguides:
activated_toolguides:
activated_paradigms:
activated_procedures:
activated_agent_profiles:
activated_mission_step_contracts:
overrides: {}
metadata:
  generated_at: '2026-07-18T00:00:00Z'
  bundle_schema_version: 2
"""


def _write_fixture(path: Path) -> None:
    path.write_text(_FIXTURE, encoding="utf-8")


class TestOwnedSections:
    def test_owned_sections_cover_the_six_named_sections(self) -> None:
        expected = {
            "governance",
            "directives",
            "catalog",
            "activation",
            "metadata",
            "overrides",
        }
        assert expected == OWNED_SECTIONS

    def test_unknown_section_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "charter.yaml"
        _write_fixture(path)
        with pytest.raises(UnknownCharterYamlSectionError):
            update_charter_yaml_section(path, "not-a-real-section", {"x": 1})


class TestLoadSaveRoundTrip:
    def test_load_then_save_is_byte_identical_when_unmutated(self, tmp_path: Path) -> None:
        path = tmp_path / "charter.yaml"
        _write_fixture(path)

        document = load_charter_yaml(path)
        save_charter_yaml(path, document)

        assert path.read_text(encoding="utf-8") == _FIXTURE


class TestMutateActivationPreservesGovernanceAndCatalog:
    def test_mutating_activation_preserves_governance_comment_marker(self, tmp_path: Path) -> None:
        path = tmp_path / "charter.yaml"
        _write_fixture(path)

        update_charter_yaml_section(
            path,
            "activation",
            {"activated_directives": ["001-architectural-integrity-standard"]},
        )

        text = path.read_text(encoding="utf-8")
        assert "# GOV-COMMENT-MARKER preserved" in text
        assert "min_coverage: 80" in text

    def test_mutating_activation_preserves_catalog_comment_marker(self, tmp_path: Path) -> None:
        path = tmp_path / "charter.yaml"
        _write_fixture(path)

        update_charter_yaml_section(
            path,
            "activation",
            {"activated_directives": ["001-architectural-integrity-standard"]},
        )

        text = path.read_text(encoding="utf-8")
        assert "# CATALOG-COMMENT-MARKER preserved" in text
        assert "template_set: software-dev-default" in text

    def test_mutating_activation_actually_updates_the_target_key(self, tmp_path: Path) -> None:
        path = tmp_path / "charter.yaml"
        _write_fixture(path)

        update_charter_yaml_section(
            path,
            "activation",
            {"activated_directives": ["001-architectural-integrity-standard"]},
        )

        document = load_charter_yaml(path)
        assert document["activated_directives"] == ["001-architectural-integrity-standard"]

    def test_mutating_activation_leaves_other_activation_keys_untouched(self, tmp_path: Path) -> None:
        path = tmp_path / "charter.yaml"
        _write_fixture(path)

        update_charter_yaml_section(
            path,
            "activation",
            {"activated_directives": ["001-architectural-integrity-standard"]},
        )

        document = load_charter_yaml(path)
        assert document["activated_kinds"] == ["directives"]
        assert document["mission_type_activations"] == ["software-dev"]

    def test_mutating_activation_rejects_unknown_activation_key(self, tmp_path: Path) -> None:
        path = tmp_path / "charter.yaml"
        _write_fixture(path)

        with pytest.raises(ValueError, match="Unknown activation key"):
            update_charter_yaml_section(path, "activation", {"not_a_real_activation_key": []})


class TestMutateCatalogPreservesGovernanceAndActivation:
    def test_mutating_catalog_preserves_governance_comment_marker(self, tmp_path: Path) -> None:
        path = tmp_path / "charter.yaml"
        _write_fixture(path)

        update_charter_yaml_section(
            path,
            "catalog",
            {
                "mission": "software-dev",
                "template_set": "software-dev-default",
                "languages": ["python", "rust"],
                "references": [],
            },
        )

        text = path.read_text(encoding="utf-8")
        assert "# GOV-COMMENT-MARKER preserved" in text

    def test_mutating_catalog_preserves_activation_flat_keys(self, tmp_path: Path) -> None:
        path = tmp_path / "charter.yaml"
        _write_fixture(path)

        update_charter_yaml_section(
            path,
            "catalog",
            {
                "mission": "software-dev",
                "template_set": "software-dev-default",
                "languages": ["python", "rust"],
                "references": [],
            },
        )

        document = load_charter_yaml(path)
        assert document["activated_kinds"] == ["directives"]
        assert document["activated_directives"] == []

    def test_mutating_catalog_updates_the_target_section(self, tmp_path: Path) -> None:
        path = tmp_path / "charter.yaml"
        _write_fixture(path)

        update_charter_yaml_section(
            path,
            "catalog",
            {
                "mission": "software-dev",
                "template_set": "software-dev-default",
                "languages": ["python", "rust"],
                "references": [],
            },
        )

        document = load_charter_yaml(path)
        assert document["catalog"]["languages"] == ["python", "rust"]


class TestMutateGovernancePreservesCatalogAndMetadata:
    def test_mutating_governance_preserves_catalog_comment_marker(self, tmp_path: Path) -> None:
        path = tmp_path / "charter.yaml"
        _write_fixture(path)

        update_charter_yaml_section(
            path,
            "governance",
            {
                "testing": {"min_coverage": 90},
                "quality": {},
                "commits": {},
                "performance": {},
                "branch_strategy": {},
                "doctrine": {},
                "activations": [],
                "enforcement": {},
            },
        )

        text = path.read_text(encoding="utf-8")
        assert "# CATALOG-COMMENT-MARKER preserved" in text

    def test_mutating_governance_preserves_metadata(self, tmp_path: Path) -> None:
        path = tmp_path / "charter.yaml"
        _write_fixture(path)

        update_charter_yaml_section(
            path,
            "governance",
            {
                "testing": {"min_coverage": 90},
                "quality": {},
                "commits": {},
                "performance": {},
                "branch_strategy": {},
                "doctrine": {},
                "activations": [],
                "enforcement": {},
            },
        )

        document = load_charter_yaml(path)
        assert document["metadata"]["bundle_schema_version"] == 2
