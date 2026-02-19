"""Tests for doctrine structure and curation traceability."""

from __future__ import annotations

from pathlib import Path

from ruamel.yaml import YAML

from specify_cli.validators.doctrine_curation import validate_import_candidate
from tests.utils import REPO_ROOT


def test_doctrine_structure_paths_exist() -> None:
    expected_dirs = [
        REPO_ROOT / "src" / "doctrine" / "paradigms",
        REPO_ROOT / "src" / "doctrine" / "directives",
        REPO_ROOT / "src" / "doctrine" / "tactics",
        REPO_ROOT / "src" / "doctrine" / "agent-profiles",
        REPO_ROOT / "src" / "doctrine" / "schemas",
        REPO_ROOT / "src" / "doctrine" / "curation",
        REPO_ROOT / "src" / "doctrine" / "templates" / "sets",
    ]
    for directory in expected_dirs:
        assert directory.is_dir(), f"Missing expected doctrine directory: {directory}"


def test_curation_readme_documents_pull_based_flow() -> None:
    readme = (REPO_ROOT / "src" / "doctrine" / "curation" / "README.md").read_text(
        encoding="utf-8"
    )
    assert "pull-based" in readme.lower()
    assert "ZOMBIES TDD" in readme


def test_import_candidate_schema_contains_adoption_gate() -> None:
    schema_path = REPO_ROOT / "src" / "doctrine" / "schemas" / "import-candidate.schema.yaml"
    yaml = YAML(typ="safe")
    schema = yaml.load(schema_path.read_text(encoding="utf-8"))

    required = schema.get("required", [])
    assert "id" in required
    assert "source" in required
    assert "status" in required

    all_of = schema.get("allOf", [])
    assert all_of, "Schema must define adoption gate rules"
    rendered = str(all_of)
    assert "adopted" in rendered
    assert "resulting_artifacts" in rendered


def test_import_candidate_sample_validates() -> None:
    candidate_path = (
        REPO_ROOT
        / "src"
        / "doctrine"
        / "curation"
        / "imports"
        / "example-zombies"
        / "candidates"
        / "zombies-tdd.import.yaml"
    )
    result = validate_import_candidate(candidate_path)
    assert result.valid, f"Candidate should be valid, got: {result.errors}"


def test_adopted_candidate_requires_resulting_artifact_links(tmp_path: Path) -> None:
    candidate = tmp_path / "candidate.import.yaml"
    candidate.write_text(
        """
id: "imp-001"
source:
  title: "Example"
  type: "article"
  url: "https://example.org"
  accessed_on: "2026-02-17"
classification:
  target_concepts: ["tactic"]
adaptation:
  summary: "Example adaptation."
status: "adopted"
""",
        encoding="utf-8",
    )

    result = validate_import_candidate(candidate)
    assert not result.valid
    assert any("resulting_artifacts" in error for error in result.errors)
