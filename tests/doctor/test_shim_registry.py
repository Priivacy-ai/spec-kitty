"""FR-009: Integration tests for spec-kitty doctor shim-registry."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

import specify_cli.cli.commands.doctor as doctor_mod
from specify_cli.cli.commands.doctor import app

runner = CliRunner()


def _write_project(tmp_path: Path, registry_content: str, version: str = "3.2.0") -> None:
    (tmp_path / "pyproject.toml").write_text(
        f'[project]\nname = "spec-kitty-cli"\nversion = "{version}"\n'
    )
    arch = tmp_path / "architecture" / "2.x"
    arch.mkdir(parents=True)
    (arch / "shim-registry.yaml").write_text(registry_content)


def _shim_entry(
    legacy_path: str = "specify_cli.example",
    canonical: str = "example",
    introduced: str = "3.2.0",
    removal: str = "3.3.0",
    issue: str = "#615",
    grandfathered: bool = False,
) -> str:
    gf = "true" if grandfathered else "false"
    return (
        f"  - legacy_path: {legacy_path}\n"
        f'    canonical_import: "{canonical}"\n'
        f'    introduced_in_release: "{introduced}"\n'
        f'    removal_target_release: "{removal}"\n'
        f'    tracker_issue: "{issue}"\n'
        f"    grandfathered: {gf}\n"
    )


def _create_shim_file(tmp_path: Path, legacy_path: str) -> Path:
    parts = legacy_path.split(".")
    base = tmp_path / "src" / Path(*parts)
    base.parent.mkdir(parents=True, exist_ok=True)
    shim = base.with_suffix(".py")
    shim.write_text("__deprecated__ = True\n__canonical_import__ = 'example'\n")
    return shim


class TestEmptyRegistry:
    def test_empty_registry_exits_0(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_project(tmp_path, "shims: []\n")
        monkeypatch.setattr(doctor_mod, "locate_project_root", lambda: tmp_path)
        result = runner.invoke(app, ["shim-registry"])
        assert result.exit_code == 0
        assert "empty" in result.output.lower()

    def test_empty_registry_json_exits_0(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_project(tmp_path, "shims: []\n")
        monkeypatch.setattr(doctor_mod, "locate_project_root", lambda: tmp_path)
        result = runner.invoke(app, ["shim-registry", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["entries"] == []
        assert data["has_overdue"] is False
        assert data["exit_code"] == 0

    def test_json_output_has_expected_keys(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_project(tmp_path, "shims: []\n")
        monkeypatch.setattr(doctor_mod, "locate_project_root", lambda: tmp_path)
        result = runner.invoke(app, ["shim-registry", "--json"])
        data = json.loads(result.output)
        assert set(data.keys()) >= {
            "project_version",
            "registry_path",
            "entries",
            "has_overdue",
            "exit_code",
        }


class TestPendingEntry:
    def test_pending_entry_exits_0(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _create_shim_file(tmp_path, "specify_cli.example")
        entry = _shim_entry(removal="3.3.0")
        _write_project(tmp_path, f"shims:\n{entry}", version="3.2.0")
        monkeypatch.setattr(doctor_mod, "locate_project_root", lambda: tmp_path)
        result = runner.invoke(app, ["shim-registry"])
        assert result.exit_code == 0
        assert "pending" in result.output

    def test_pending_json_shows_status(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _create_shim_file(tmp_path, "specify_cli.example")
        entry = _shim_entry(removal="3.3.0")
        _write_project(tmp_path, f"shims:\n{entry}", version="3.2.0")
        monkeypatch.setattr(doctor_mod, "locate_project_root", lambda: tmp_path)
        result = runner.invoke(app, ["shim-registry", "--json"])
        data = json.loads(result.output)
        assert data["entries"][0]["status"] == "pending"


class TestOverdueEntry:
    def test_overdue_entry_exits_1(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _create_shim_file(tmp_path, "specify_cli.example")
        entry = _shim_entry(removal="3.2.0")
        _write_project(tmp_path, f"shims:\n{entry}", version="3.2.0")
        monkeypatch.setattr(doctor_mod, "locate_project_root", lambda: tmp_path)
        result = runner.invoke(app, ["shim-registry"])
        assert result.exit_code == 1
        assert "OVERDUE" in result.output or "overdue" in result.output.lower()

    def test_overdue_shows_remediation_block(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _create_shim_file(tmp_path, "specify_cli.example")
        entry = _shim_entry(removal="3.2.0")
        _write_project(tmp_path, f"shims:\n{entry}", version="3.2.0")
        monkeypatch.setattr(doctor_mod, "locate_project_root", lambda: tmp_path)
        result = runner.invoke(app, ["shim-registry"])
        assert "Option A" in result.output or "Delete" in result.output

    def test_overdue_json_has_overdue_true(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _create_shim_file(tmp_path, "specify_cli.example")
        entry = _shim_entry(removal="3.2.0")
        _write_project(tmp_path, f"shims:\n{entry}", version="3.2.0")
        monkeypatch.setattr(doctor_mod, "locate_project_root", lambda: tmp_path)
        result = runner.invoke(app, ["shim-registry", "--json"])
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["has_overdue"] is True
        assert data["exit_code"] == 1
        assert data["entries"][0]["status"] == "overdue"


class TestGrandfatheredEntry:
    def test_grandfathered_exits_0_even_past_removal(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _create_shim_file(tmp_path, "specify_cli.example")
        # Use valid semver ordering (removal >= introduced); grandfathered=True prevents OVERDUE
        entry = _shim_entry(introduced="3.0.0", removal="3.1.0", grandfathered=True)
        _write_project(tmp_path, f"shims:\n{entry}", version="3.2.0")
        monkeypatch.setattr(doctor_mod, "locate_project_root", lambda: tmp_path)
        result = runner.invoke(app, ["shim-registry"])
        assert result.exit_code == 0
        assert "grandfathered" in result.output

    def test_grandfathered_json_status(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        entry = _shim_entry(introduced="3.0.0", removal="3.1.0", grandfathered=True)
        _write_project(tmp_path, f"shims:\n{entry}", version="3.2.0")
        monkeypatch.setattr(doctor_mod, "locate_project_root", lambda: tmp_path)
        result = runner.invoke(app, ["shim-registry", "--json"])
        data = json.loads(result.output)
        assert data["entries"][0]["status"] == "grandfathered"
        assert data["has_overdue"] is False


class TestRemovedEntry:
    def test_removed_entry_exits_0(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        entry = _shim_entry(removal="3.2.0")
        _write_project(tmp_path, f"shims:\n{entry}", version="3.2.0")
        monkeypatch.setattr(doctor_mod, "locate_project_root", lambda: tmp_path)
        result = runner.invoke(app, ["shim-registry"])
        assert result.exit_code == 0

    def test_removed_json_status(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        entry = _shim_entry(removal="3.2.0")
        _write_project(tmp_path, f"shims:\n{entry}", version="3.2.0")
        monkeypatch.setattr(doctor_mod, "locate_project_root", lambda: tmp_path)
        result = runner.invoke(app, ["shim-registry", "--json"])
        data = json.loads(result.output)
        assert data["entries"][0]["status"] == "removed"


class TestConfigErrors:
    def test_missing_pyproject_exits_2(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        arch = tmp_path / "architecture" / "2.x"
        arch.mkdir(parents=True)
        (arch / "shim-registry.yaml").write_text("shims: []\n")
        monkeypatch.setattr(doctor_mod, "locate_project_root", lambda: tmp_path)
        result = runner.invoke(app, ["shim-registry"])
        assert result.exit_code == 2
        assert "configuration error" in result.output.lower() or "error" in result.output.lower()

    def test_missing_registry_exits_2(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (tmp_path / "pyproject.toml").write_text('[project]\nname="x"\nversion="3.2.0"\n')
        monkeypatch.setattr(doctor_mod, "locate_project_root", lambda: tmp_path)
        result = runner.invoke(app, ["shim-registry"])
        assert result.exit_code == 2

    def test_malformed_registry_exits_2(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_project(tmp_path, "not_valid: registry: content\n  broken:\n")
        monkeypatch.setattr(doctor_mod, "locate_project_root", lambda: tmp_path)
        result = runner.invoke(app, ["shim-registry"])
        assert result.exit_code == 2

    def test_not_in_project_exits_2(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(doctor_mod, "locate_project_root", lambda: None)
        result = runner.invoke(app, ["shim-registry"])
        assert result.exit_code == 2
