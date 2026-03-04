"""Unit tests for ToolguideRepository."""

from pathlib import Path

import pytest
from ruamel.yaml import YAML

from doctrine.toolguides.repository import ToolguideRepository
pytestmark = [pytest.mark.fast, pytest.mark.doctrine]



class TestToolguideRepository:
    def test_list_all_from_shipped(self, tmp_toolguide_dir: Path) -> None:
        """list_all returns all toolguides from the given directory."""
        repo = ToolguideRepository(shipped_dir=tmp_toolguide_dir)
        toolguides = repo.list_all()
        assert len(toolguides) == 1

    def test_get_by_id(self, tmp_toolguide_dir: Path) -> None:
        """get() returns toolguide by ID."""
        repo = ToolguideRepository(shipped_dir=tmp_toolguide_dir)
        toolguide = repo.get("test-toolguide")
        assert toolguide is not None
        assert toolguide.tool == "bash"

    def test_get_returns_none_for_unknown(self, tmp_toolguide_dir: Path) -> None:
        repo = ToolguideRepository(shipped_dir=tmp_toolguide_dir)
        assert repo.get("nonexistent-toolguide") is None

    def test_load_from_custom_shipped_dir(self, tmp_toolguide_dir: Path) -> None:
        repo = ToolguideRepository(shipped_dir=tmp_toolguide_dir)
        toolguides = repo.list_all()
        assert len(toolguides) == 1
        assert toolguides[0].id == "test-toolguide"

    def test_malformed_yaml_skipped_with_warning(self, tmp_path: Path) -> None:
        shipped = tmp_path / "shipped"
        shipped.mkdir()
        bad_file = shipped / "bad.toolguide.yaml"
        bad_file.write_text("not: valid: yaml: [")

        with pytest.warns(UserWarning, match="Skipping invalid"):
            repo = ToolguideRepository(shipped_dir=shipped)

        assert repo.list_all() == []

    def test_save_writes_valid_yaml(self, tmp_path: Path, sample_toolguide_data: dict) -> None:
        from doctrine.toolguides.models import Toolguide

        project_dir = tmp_path / "project"
        repo = ToolguideRepository(shipped_dir=tmp_path / "empty", project_dir=project_dir)

        toolguide = Toolguide.model_validate(sample_toolguide_data)
        path = repo.save(toolguide)

        assert path.exists()
        assert path.suffix == ".yaml"

        yaml = YAML(typ="safe")
        data = yaml.load(path)
        assert data["id"] == "test-toolguide"

    def test_save_raises_without_project_dir(self, tmp_path: Path, sample_toolguide_data: dict) -> None:
        from doctrine.toolguides.models import Toolguide


        repo = ToolguideRepository(shipped_dir=tmp_path / "empty")
        toolguide = Toolguide.model_validate(sample_toolguide_data)
        with pytest.raises(ValueError, match="project_dir not configured"):
            repo.save(toolguide)

    def test_field_level_merge_with_project_override(self, tmp_path: Path) -> None:
        shipped = tmp_path / "shipped"
        shipped.mkdir()
        project = tmp_path / "project"
        project.mkdir()

        yaml = YAML()
        yaml.default_flow_style = False

        base = {
            "schema_version": "1.0",
            "id": "merge-test",
            "tool": "bash",
            "title": "Base Title",
            "guide_path": "src/doctrine/toolguides/shipped/POWERSHELL_SYNTAX.md",
            "summary": "Base summary",
        }
        override = {
            "schema_version": "1.0",
            "id": "merge-test",
            "tool": "powershell",
            "title": "Overridden Title",
            "guide_path": "src/doctrine/toolguides/shipped/POWERSHELL_SYNTAX.md",
            "summary": "Overridden summary",
            "commands": ["spec-kitty"],
        }

        with (shipped / "merge-test.toolguide.yaml").open("w") as f:
            yaml.dump(base, f)
        with (project / "merge-test.toolguide.yaml").open("w") as f:
            yaml.dump(override, f)

        repo = ToolguideRepository(shipped_dir=shipped, project_dir=project)
        toolguide = repo.get("merge-test")
        assert toolguide is not None
        assert toolguide.tool == "powershell"
        assert toolguide.title == "Overridden Title"
        assert toolguide.commands == ["spec-kitty"]

