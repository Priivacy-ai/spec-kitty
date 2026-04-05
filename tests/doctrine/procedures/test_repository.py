"""Tests for ProcedureRepository."""

from pathlib import Path

import pytest
from ruamel.yaml import YAML

from doctrine.procedures.repository import ProcedureRepository
pytestmark = [pytest.mark.fast, pytest.mark.doctrine]



class TestProcedureRepository:
    """Repository CRUD and loading tests."""

    def test_default_repository_includes_migration_procedure(self) -> None:
        repo = ProcedureRepository()
        procedure = repo.get("migrate-project-guidance-to-spec-kitty-charter")
        assert procedure is not None
        assert procedure.name == "Migrate Project Guidance to Spec Kitty Charter"

    def test_list_all_from_shipped(self, tmp_procedure_dir: Path) -> None:
        repo = ProcedureRepository(shipped_dir=tmp_procedure_dir)
        procedures = repo.list_all()
        assert len(procedures) == 1
        assert procedures[0].id == "curation-interview"

    def test_get_by_id(self, tmp_procedure_dir: Path) -> None:
        repo = ProcedureRepository(shipped_dir=tmp_procedure_dir)
        p = repo.get("curation-interview")
        assert p is not None
        assert p.name == "Doctrine Curation Interview"

    def test_get_missing_returns_none(self, tmp_procedure_dir: Path) -> None:
        repo = ProcedureRepository(shipped_dir=tmp_procedure_dir)
        assert repo.get("nonexistent") is None

    def test_project_override_merges(
        self, tmp_path: Path, sample_procedure_data: dict
    ) -> None:
        yaml = YAML()
        yaml.default_flow_style = False

        shipped = tmp_path / "shipped"
        shipped.mkdir()
        with (shipped / "curation-interview.procedure.yaml").open("w") as f:
            yaml.dump(sample_procedure_data, f)

        project = tmp_path / "project"
        project.mkdir()
        override = {**sample_procedure_data, "name": "Overridden Name"}
        with (project / "curation-interview.procedure.yaml").open("w") as f:
            yaml.dump(override, f)

        repo = ProcedureRepository(shipped_dir=shipped, project_dir=project)
        p = repo.get("curation-interview")
        assert p is not None
        assert p.name == "Overridden Name"

    def test_save_raises_without_project_dir(
        self, tmp_procedure_dir: Path, sample_procedure_data: dict
    ) -> None:
        from doctrine.procedures.models import Procedure

        repo = ProcedureRepository(shipped_dir=tmp_procedure_dir)
        procedure = Procedure.model_validate(sample_procedure_data)
        with pytest.raises(ValueError, match="project_dir not configured"):
            repo.save(procedure)

    def test_save_writes_to_project_dir(
        self, tmp_path: Path, sample_procedure_data: dict
    ) -> None:
        from doctrine.procedures.models import Procedure


        shipped = tmp_path / "shipped"
        shipped.mkdir()
        project = tmp_path / "project"

        repo = ProcedureRepository(shipped_dir=shipped, project_dir=project)
        procedure = Procedure.model_validate(sample_procedure_data)
        path = repo.save(procedure)

        assert path.exists()
        assert "curation-interview.procedure.yaml" in path.name
        assert repo.get("curation-interview") is not None

    def test_invalid_yaml_skipped_with_warning(self, tmp_path: Path) -> None:
        shipped = tmp_path / "shipped"
        shipped.mkdir()
        (shipped / "bad.procedure.yaml").write_text("not: valid: yaml: [")

        with pytest.warns(UserWarning, match="Skipping invalid shipped procedure"):
            repo = ProcedureRepository(shipped_dir=shipped)
        assert repo.list_all() == []

    def test_empty_shipped_dir(self, tmp_path: Path) -> None:
        shipped = tmp_path / "empty"
        shipped.mkdir()
        repo = ProcedureRepository(shipped_dir=shipped)
        assert repo.list_all() == []
