"""Unit tests for DashboardFileReader."""
from __future__ import annotations

import urllib.parse
from pathlib import Path
from unittest.mock import patch

import pytest

from dashboard.file_reader import DashboardFileReader, FileReadResult

pytestmark = pytest.mark.fast


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def feature_dir(project_dir: Path) -> Path:
    feature = project_dir / "kitty-specs" / "001-test"
    feature.mkdir(parents=True)
    return feature


@pytest.fixture
def reader(project_dir: Path) -> DashboardFileReader:
    return DashboardFileReader(project_dir)


# ---------------------------------------------------------------------------
# _safe_read
# ---------------------------------------------------------------------------


class TestSafeRead:
    def test_returns_not_found_for_missing_file(self, reader, tmp_path):
        result = reader._safe_read(tmp_path / "nonexistent.md")
        assert result.found is False
        assert result.content is None

    def test_returns_not_found_for_directory(self, reader, tmp_path):
        result = reader._safe_read(tmp_path)
        assert result.found is False

    def test_reads_utf8_file(self, reader, tmp_path):
        f = tmp_path / "hello.md"
        f.write_text("hello world", encoding="utf-8")
        result = reader._safe_read(f)
        assert result.found is True
        assert result.content == "hello world"
        assert result.encoding_error is False

    def test_recovers_from_non_utf8_content(self, reader, tmp_path):
        f = tmp_path / "bad.md"
        f.write_bytes(b"\xff\xfe bad bytes")
        result = reader._safe_read(f)
        assert result.found is True
        assert result.encoding_error is True
        assert "Encoding Error" in result.content


# ---------------------------------------------------------------------------
# _check_traversal
# ---------------------------------------------------------------------------


class TestCheckTraversal:
    def test_allows_file_within_feature_dir(self, reader, feature_dir):
        candidate = (feature_dir / "spec.md").resolve()
        assert reader._check_traversal(feature_dir, candidate) is True

    def test_blocks_file_outside_feature_dir(self, reader, feature_dir, tmp_path):
        outside = (tmp_path / "other" / "secret.md").resolve()
        assert reader._check_traversal(feature_dir, outside) is False

    def test_allows_nested_file(self, reader, feature_dir):
        nested = (feature_dir / "contracts" / "api.yaml").resolve()
        assert reader._check_traversal(feature_dir, nested) is True


# ---------------------------------------------------------------------------
# read_research
# ---------------------------------------------------------------------------


class TestReadResearch:
    def test_returns_empty_for_unknown_feature(self, reader):
        with patch("dashboard.file_reader.resolve_feature_dir", return_value=None):
            response = reader.read_research("unknown-feature")
        assert response["main_file"] is None
        assert response["artifacts"] == []

    def test_returns_research_md_content(self, reader, feature_dir):
        (feature_dir / "research.md").write_text("# Research", encoding="utf-8")
        with patch("dashboard.file_reader.resolve_feature_dir", return_value=feature_dir):
            response = reader.read_research("001-test")
        assert response["main_file"] == "# Research"

    def test_lists_research_subdir_artifacts(self, reader, feature_dir):
        research_dir = feature_dir / "research"
        research_dir.mkdir()
        (research_dir / "notes.md").write_text("notes", encoding="utf-8")
        (research_dir / "data.csv").write_text("col1,col2", encoding="utf-8")
        (research_dir / "report.json").write_text("{}", encoding="utf-8")

        with patch("dashboard.file_reader.resolve_feature_dir", return_value=feature_dir):
            response = reader.read_research("001-test")

        names = [a["name"] for a in response["artifacts"]]
        assert "notes.md" in names
        assert "data.csv" in names
        assert "report.json" in names
        icons = {a["name"]: a["icon"] for a in response["artifacts"]}
        assert icons["notes.md"] == "📝"
        assert icons["data.csv"] == "📊"
        assert icons["report.json"] == "📋"

    def test_no_research_dir_returns_empty_artifacts(self, reader, feature_dir):
        (feature_dir / "research.md").write_text("content", encoding="utf-8")
        with patch("dashboard.file_reader.resolve_feature_dir", return_value=feature_dir):
            response = reader.read_research("001-test")
        assert response["artifacts"] == []


# ---------------------------------------------------------------------------
# read_artifact_file
# ---------------------------------------------------------------------------


class TestReadArtifactFile:
    def test_returns_not_found_for_unknown_feature(self, reader):
        with patch("dashboard.file_reader.resolve_feature_dir", return_value=None):
            result = reader.read_artifact_file("unknown", "spec.md")
        assert result.found is False

    def test_reads_file_within_feature_dir(self, reader, feature_dir):
        (feature_dir / "spec.md").write_text("the spec", encoding="utf-8")
        with patch("dashboard.file_reader.resolve_feature_dir", return_value=feature_dir):
            result = reader.read_artifact_file("001-test", "spec.md")
        assert result.found is True
        assert result.content == "the spec"

    def test_blocks_path_traversal(self, reader, feature_dir, tmp_path):
        (tmp_path / "secret.md").write_text("secret", encoding="utf-8")
        with patch("dashboard.file_reader.resolve_feature_dir", return_value=feature_dir):
            result = reader.read_artifact_file("001-test", "../secret.md")
        assert result.found is False

    def test_decodes_url_encoded_path(self, reader, feature_dir):
        subdir = feature_dir / "contracts"
        subdir.mkdir()
        (subdir / "api.yaml").write_text("openapi: 3.0.0", encoding="utf-8")
        encoded = urllib.parse.quote("contracts/api.yaml")
        with patch("dashboard.file_reader.resolve_feature_dir", return_value=feature_dir):
            result = reader.read_artifact_file("001-test", encoded)
        assert result.found is True
        assert "openapi" in result.content


# ---------------------------------------------------------------------------
# read_artifact_directory
# ---------------------------------------------------------------------------


class TestReadArtifactDirectory:
    def test_returns_empty_for_unknown_feature(self, reader):
        with patch("dashboard.file_reader.resolve_feature_dir", return_value=None):
            response = reader.read_artifact_directory("unknown", "contracts")
        assert response["files"] == []

    def test_returns_empty_when_directory_absent(self, reader, feature_dir):
        with patch("dashboard.file_reader.resolve_feature_dir", return_value=feature_dir):
            response = reader.read_artifact_directory("001-test", "contracts")
        assert response["files"] == []

    def test_lists_directory_files(self, reader, feature_dir):
        contracts = feature_dir / "contracts"
        contracts.mkdir()
        (contracts / "api.md").write_text("contract", encoding="utf-8")
        (contracts / "schema.json").write_text("{}", encoding="utf-8")

        with patch("dashboard.file_reader.resolve_feature_dir", return_value=feature_dir):
            response = reader.read_artifact_directory("001-test", "contracts", md_icon="📝")

        names = [f["name"] for f in response["files"]]
        assert "api.md" in names
        assert "schema.json" in names
        icons = {f["name"]: f["icon"] for f in response["files"]}
        assert icons["api.md"] == "📝"
        assert icons["schema.json"] == "📋"

    def test_non_md_non_json_gets_default_icon(self, reader, feature_dir):
        contracts = feature_dir / "contracts"
        contracts.mkdir()
        (contracts / "diagram.png").write_bytes(b"\x89PNG")

        with patch("dashboard.file_reader.resolve_feature_dir", return_value=feature_dir):
            response = reader.read_artifact_directory("001-test", "contracts")

        assert response["files"][0]["icon"] == "📄"


# ---------------------------------------------------------------------------
# read_named_artifact
# ---------------------------------------------------------------------------


class TestReadNamedArtifact:
    def test_returns_not_found_for_unknown_feature(self, reader):
        with patch("dashboard.file_reader.resolve_feature_dir", return_value=None):
            result = reader.read_named_artifact("unknown", "spec")
        assert result.found is False

    def test_returns_not_found_for_unknown_artifact_name(self, reader, feature_dir):
        with patch("dashboard.file_reader.resolve_feature_dir", return_value=feature_dir):
            result = reader.read_named_artifact("001-test", "nonexistent-artifact")
        assert result.found is False

    def test_reads_spec_md(self, reader, feature_dir):
        (feature_dir / "spec.md").write_text("# Spec", encoding="utf-8")
        with patch("dashboard.file_reader.resolve_feature_dir", return_value=feature_dir):
            result = reader.read_named_artifact("001-test", "spec")
        assert result.found is True
        assert result.content == "# Spec"

    def test_reads_plan_md(self, reader, feature_dir):
        (feature_dir / "plan.md").write_text("# Plan", encoding="utf-8")
        with patch("dashboard.file_reader.resolve_feature_dir", return_value=feature_dir):
            result = reader.read_named_artifact("001-test", "plan")
        assert result.found is True

    def test_returns_not_found_when_file_missing(self, reader, feature_dir):
        with patch("dashboard.file_reader.resolve_feature_dir", return_value=feature_dir):
            result = reader.read_named_artifact("001-test", "spec")
        assert result.found is False
