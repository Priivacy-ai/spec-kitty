"""Unit tests for StyleguideRepository."""

from pathlib import Path

import pytest
from ruamel.yaml import YAML

from doctrine.styleguides.repository import StyleguideRepository
pytestmark = [pytest.mark.fast, pytest.mark.doctrine]



class TestStyleguideRepository:
    def test_list_all_from_shipped(self, tmp_styleguide_dir: Path) -> None:
        """list_all returns all styleguides from the given directory."""
        repo = StyleguideRepository(shipped_dir=tmp_styleguide_dir)
        styleguides = repo.list_all()
        assert len(styleguides) == 1
        assert styleguides[0].id == "test-style"

    def test_get_by_id(self, tmp_styleguide_dir: Path) -> None:
        """get() returns styleguide by ID."""
        repo = StyleguideRepository(shipped_dir=tmp_styleguide_dir)
        sg = repo.get("test-style")
        assert sg is not None
        assert sg.scope.value == "code"
        assert sg.title == "Test Styleguide"

    def test_get_returns_none_for_unknown(self, tmp_styleguide_dir: Path) -> None:
        repo = StyleguideRepository(shipped_dir=tmp_styleguide_dir)
        assert repo.get("nonexistent-style") is None

    def test_recursive_scan_finds_subdirectory_files(self, tmp_path: Path) -> None:
        """Subdirectory styleguides are found via recursive glob."""
        from ruamel.yaml import YAML as RuamelYAML

        shipped = tmp_path / "styleguides"
        shipped.mkdir()
        subdir = shipped / "writing"
        subdir.mkdir()

        data = {
            "schema_version": "1.0",
            "id": "sub-style",
            "title": "Subdirectory Styleguide",
            "scope": "docs",
            "principles": ["Write clearly"],
        }
        y = RuamelYAML()
        y.default_flow_style = False
        with (subdir / "sub-style.styleguide.yaml").open("w") as f:
            y.dump(data, f)

        repo = StyleguideRepository(shipped_dir=shipped)
        ids = [sg.id for sg in repo.list_all()]
        assert "sub-style" in ids

    def test_load_from_custom_shipped_dir(
        self, tmp_styleguide_dir: Path
    ) -> None:
        repo = StyleguideRepository(shipped_dir=tmp_styleguide_dir)
        styleguides = repo.list_all()
        assert len(styleguides) == 1
        assert styleguides[0].id == "test-style"

    def test_malformed_yaml_skipped_with_warning(self, tmp_path: Path) -> None:
        shipped = tmp_path / "shipped"
        shipped.mkdir()
        bad_file = shipped / "bad.styleguide.yaml"
        bad_file.write_text("not: valid: yaml: [")

        with pytest.warns(UserWarning, match="Skipping invalid"):
            repo = StyleguideRepository(shipped_dir=shipped)

        assert repo.list_all() == []

    def test_save_writes_valid_yaml(
        self, tmp_path: Path, sample_styleguide_data: dict
    ) -> None:
        from doctrine.styleguides.models import Styleguide

        project_dir = tmp_path / "project"
        repo = StyleguideRepository(
            shipped_dir=tmp_path / "empty", project_dir=project_dir
        )

        sg = Styleguide.model_validate(sample_styleguide_data)
        path = repo.save(sg)

        assert path.exists()
        assert path.suffix == ".yaml"

        yaml = YAML(typ="safe")
        data = yaml.load(path)
        assert data["id"] == "test-style"

    def test_save_raises_without_project_dir(
        self, tmp_path: Path, sample_styleguide_data: dict
    ) -> None:
        from doctrine.styleguides.models import Styleguide


        repo = StyleguideRepository(shipped_dir=tmp_path / "empty")
        sg = Styleguide.model_validate(sample_styleguide_data)
        with pytest.raises(ValueError, match="project_dir not configured"):
            repo.save(sg)

    def test_field_level_merge_with_project_override(
        self, tmp_path: Path
    ) -> None:
        shipped = tmp_path / "shipped"
        shipped.mkdir()
        project = tmp_path / "project"
        project.mkdir()

        yaml = YAML()
        yaml.default_flow_style = False

        base = {
            "schema_version": "1.0",
            "id": "merge-test",
            "title": "Base Title",
            "scope": "code",
            "principles": ["Original principle"],
        }
        override = {
            "schema_version": "1.0",
            "id": "merge-test",
            "title": "Overridden Title",
            "scope": "testing",
            "principles": ["New principle"],
        }

        with (shipped / "merge-test.styleguide.yaml").open("w") as f:
            yaml.dump(base, f)
        with (project / "merge-test.styleguide.yaml").open("w") as f:
            yaml.dump(override, f)

        repo = StyleguideRepository(shipped_dir=shipped, project_dir=project)
        sg = repo.get("merge-test")
        assert sg is not None
        assert sg.title == "Overridden Title"
        assert sg.scope.value == "testing"
