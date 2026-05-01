"""Unit tests for DirectiveRepository."""

from pathlib import Path

import pytest
from ruamel.yaml import YAML

from doctrine.directives.repository import DirectiveRepository

pytestmark = [pytest.mark.fast, pytest.mark.doctrine]


class TestDirectiveRepository:
    def test_list_all_from_shipped(self, tmp_directive_dir: Path) -> None:
        """list_all returns all directives from the given directory."""
        repo = DirectiveRepository(shipped_dir=tmp_directive_dir)
        directives = repo.list_all()
        assert len(directives) == 1
        assert directives[0].id == "DIRECTIVE_999"

    def test_get_by_full_id(self, tmp_directive_dir: Path) -> None:
        """get() with full ID returns the directive."""
        repo = DirectiveRepository(shipped_dir=tmp_directive_dir)
        directive = repo.get("DIRECTIVE_999")
        assert directive is not None
        assert directive.title == "Test Directive"

    def test_get_by_numeric_shorthand(self, tmp_directive_dir: Path) -> None:
        """get() with numeric shorthand normalizes and returns."""
        repo = DirectiveRepository(shipped_dir=tmp_directive_dir)
        directive = repo.get("999")
        assert directive is not None
        assert directive.id == "DIRECTIVE_999"

    def test_get_returns_none_for_unknown(self, tmp_directive_dir: Path) -> None:
        repo = DirectiveRepository(shipped_dir=tmp_directive_dir)
        assert repo.get("888") is None

    def test_get_numeric_and_full_return_same(self, tmp_directive_dir: Path) -> None:
        repo = DirectiveRepository(shipped_dir=tmp_directive_dir)
        by_num = repo.get("999")
        by_full = repo.get("DIRECTIVE_999")
        assert by_num is not None
        assert by_full is not None
        assert by_num.id == by_full.id

    def test_load_from_custom_shipped_dir(self, tmp_directive_dir: Path) -> None:
        repo = DirectiveRepository(shipped_dir=tmp_directive_dir)
        directives = repo.list_all()
        assert len(directives) == 1
        assert directives[0].id == "DIRECTIVE_999"

    def test_malformed_yaml_skipped_with_warning(self, tmp_path: Path) -> None:
        """Malformed YAML files are skipped, not crash."""
        shipped = tmp_path / "shipped"
        shipped.mkdir()
        bad_file = shipped / "bad.directive.yaml"
        bad_file.write_text("not: valid: yaml: [")

        with pytest.warns(UserWarning, match="Skipping invalid"):
            repo = DirectiveRepository(shipped_dir=shipped)

        assert repo.list_all() == []

    def test_save_writes_valid_yaml(self, tmp_path: Path, sample_directive_data: dict) -> None:
        from doctrine.directives.models import Directive

        project_dir = tmp_path / "project"
        repo = DirectiveRepository(shipped_dir=tmp_path / "empty", project_dir=project_dir)

        directive = Directive.model_validate(sample_directive_data)
        path = repo.save(directive)

        assert path.exists()
        assert path.suffix == ".yaml"

        # Verify the saved file is loadable
        yaml = YAML(typ="safe")
        data = yaml.load(path)
        assert data["id"] == "DIRECTIVE_999"

    def test_save_raises_without_project_dir(self, tmp_path: Path, sample_directive_data: dict) -> None:
        from doctrine.directives.models import Directive

        repo = DirectiveRepository(shipped_dir=tmp_path / "empty")
        directive = Directive.model_validate(sample_directive_data)
        with pytest.raises(ValueError, match="project_dir not configured"):
            repo.save(directive)

    def test_field_level_merge_with_project_override(self, tmp_path: Path) -> None:
        """Project directive overrides shipped fields at field level."""
        shipped = tmp_path / "shipped"
        shipped.mkdir()
        project = tmp_path / "project"
        project.mkdir()

        yaml = YAML()
        yaml.default_flow_style = False

        base = {
            "schema_version": "1.0",
            "id": "DIRECTIVE_100",
            "title": "Base Title",
            "intent": "Base intent.",
            "enforcement": "required",
        }
        override = {
            "schema_version": "1.0",
            "id": "DIRECTIVE_100",
            "title": "Overridden Title",
            "intent": "Overridden intent.",
            "enforcement": "advisory",
        }

        with (shipped / "100-base.directive.yaml").open("w") as f:
            yaml.dump(base, f)
        with (project / "100-base.directive.yaml").open("w") as f:
            yaml.dump(override, f)

        repo = DirectiveRepository(shipped_dir=shipped, project_dir=project)
        directive = repo.get("DIRECTIVE_100")
        assert directive is not None
        assert directive.title == "Overridden Title"
        assert directive.enforcement.value == "advisory"
