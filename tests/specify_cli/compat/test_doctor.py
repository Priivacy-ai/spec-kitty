"""Unit tests for specify_cli.compat.doctor — classification, shim-existence, and report."""
from __future__ import annotations

from pathlib import Path

import pytest
from packaging.version import Version
from ruamel.yaml import YAML

from specify_cli.compat.doctor import (
    ShimRegistryReport,
    ShimStatus,
    ShimStatusEntry,
    _classify,
    _shim_exists,
    check_shim_registry,
)
from specify_cli.compat.registry import ShimEntry

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BASE_ENTRY = ShimEntry(
    legacy_path="specify_cli.old_module",
    canonical_import="specify_cli.new_module",
    introduced_in_release="3.2.0",
    removal_target_release="3.3.0",
    tracker_issue="#615",
    grandfathered=False,
)


def _make_entry(**overrides: object) -> ShimEntry:
    fields = {
        "legacy_path": "specify_cli.old_module",
        "canonical_import": "specify_cli.new_module",
        "introduced_in_release": "3.2.0",
        "removal_target_release": "3.3.0",
        "tracker_issue": "#615",
        "grandfathered": False,
    }
    fields.update(overrides)
    return ShimEntry(**fields)  # type: ignore[arg-type]


def _setup_repo(tmp_path: Path, version: str = "3.2.0", shims: list[dict] | None = None) -> Path:
    """Create a minimal repo layout with pyproject.toml and shim registry."""
    # pyproject.toml
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(f'[project]\nname = "spec-kitty-cli"\nversion = "{version}"\n')

    # shim registry
    registry_dir = tmp_path / "architecture" / "2.x"
    registry_dir.mkdir(parents=True)
    yaml = YAML()
    with (registry_dir / "shim-registry.yaml").open("w") as fp:
        yaml.dump({"shims": shims or []}, fp)

    return tmp_path


def _create_shim_module(repo_root: Path, dotted_path: str) -> None:
    """Create a .py file at src/<dotted_path converted to path>."""
    parts = dotted_path.split(".")
    shim_path = repo_root / "src" / Path(*parts[:-1]) / f"{parts[-1]}.py"
    shim_path.parent.mkdir(parents=True, exist_ok=True)
    shim_path.write_text("# shim\n")


def _create_shim_package(repo_root: Path, dotted_path: str) -> None:
    """Create a package at src/<dotted_path converted to path>/__init__.py."""
    parts = dotted_path.split(".")
    pkg_path = repo_root / "src" / Path(*parts) / "__init__.py"
    pkg_path.parent.mkdir(parents=True, exist_ok=True)
    pkg_path.write_text("# shim package\n")


# ---------------------------------------------------------------------------
# _shim_exists()
# ---------------------------------------------------------------------------


class TestShimExists:
    def test_returns_false_when_no_file(self, tmp_path: Path) -> None:
        assert _shim_exists(tmp_path, "specify_cli.old") is False

    def test_detects_py_module(self, tmp_path: Path) -> None:
        _create_shim_module(tmp_path, "specify_cli.old")
        assert _shim_exists(tmp_path, "specify_cli.old") is True

    def test_detects_package_init(self, tmp_path: Path) -> None:
        _create_shim_package(tmp_path, "specify_cli.old_pkg")
        assert _shim_exists(tmp_path, "specify_cli.old_pkg") is True

    def test_does_not_detect_non_py_file(self, tmp_path: Path) -> None:
        parts = ["specify_cli", "old"]
        target = tmp_path / "src" / Path(*parts[:-1]) / f"{parts[-1]}.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("not a module")
        assert _shim_exists(tmp_path, "specify_cli.old") is False

    def test_single_segment_path(self, tmp_path: Path) -> None:
        module = tmp_path / "src" / "toplevel.py"
        module.parent.mkdir(parents=True, exist_ok=True)
        module.write_text("")
        assert _shim_exists(tmp_path, "toplevel") is True

    def test_deeply_nested_path(self, tmp_path: Path) -> None:
        _create_shim_module(tmp_path, "a.b.c.d.e.shim")
        assert _shim_exists(tmp_path, "a.b.c.d.e.shim") is True


# ---------------------------------------------------------------------------
# _classify()
# ---------------------------------------------------------------------------


class TestClassify:
    def test_grandfathered_entry_returns_grandfathered(self, tmp_path: Path) -> None:
        entry = _make_entry(grandfathered=True)
        result = _classify(entry, Version("3.2.0"), tmp_path)
        assert result == ShimStatus.GRANDFATHERED

    def test_grandfathered_skips_existence_check(self, tmp_path: Path) -> None:
        # Shim does not exist, but grandfathered overrides
        entry = _make_entry(grandfathered=True)
        result = _classify(entry, Version("99.0.0"), tmp_path)
        assert result == ShimStatus.GRANDFATHERED

    def test_non_existing_shim_is_removed(self, tmp_path: Path) -> None:
        entry = _make_entry(legacy_path="specify_cli.gone")
        result = _classify(entry, Version("3.2.0"), tmp_path)
        assert result == ShimStatus.REMOVED

    def test_existing_shim_before_deadline_is_pending(self, tmp_path: Path) -> None:
        _create_shim_module(tmp_path, "specify_cli.old_module")
        entry = _make_entry(removal_target_release="3.3.0")
        result = _classify(entry, Version("3.2.0"), tmp_path)
        assert result == ShimStatus.PENDING

    def test_existing_shim_at_deadline_is_overdue(self, tmp_path: Path) -> None:
        _create_shim_module(tmp_path, "specify_cli.old_module")
        entry = _make_entry(removal_target_release="3.3.0")
        result = _classify(entry, Version("3.3.0"), tmp_path)
        assert result == ShimStatus.OVERDUE

    def test_existing_shim_past_deadline_is_overdue(self, tmp_path: Path) -> None:
        _create_shim_module(tmp_path, "specify_cli.old_module")
        entry = _make_entry(removal_target_release="3.3.0")
        result = _classify(entry, Version("4.0.0"), tmp_path)
        assert result == ShimStatus.OVERDUE

    def test_package_shim_pending(self, tmp_path: Path) -> None:
        _create_shim_package(tmp_path, "specify_cli.old_pkg")
        entry = _make_entry(legacy_path="specify_cli.old_pkg", removal_target_release="3.3.0")
        result = _classify(entry, Version("3.2.0"), tmp_path)
        assert result == ShimStatus.PENDING


# ---------------------------------------------------------------------------
# ShimRegistryReport properties
# ---------------------------------------------------------------------------


class TestShimRegistryReport:
    def _make_status_entry(self, status: ShimStatus) -> ShimStatusEntry:
        return ShimStatusEntry(entry=_BASE_ENTRY, status=status, shim_exists=True)

    def test_has_overdue_false_when_no_overdue(self) -> None:
        report = ShimRegistryReport(
            entries=[self._make_status_entry(ShimStatus.PENDING)],
            project_version="3.2.0",
            registry_path=Path("architecture/2.x/shim-registry.yaml"),
        )
        assert report.has_overdue is False

    def test_has_overdue_true_when_any_overdue(self) -> None:
        report = ShimRegistryReport(
            entries=[
                self._make_status_entry(ShimStatus.PENDING),
                self._make_status_entry(ShimStatus.OVERDUE),
            ],
            project_version="3.2.0",
            registry_path=Path("architecture/2.x/shim-registry.yaml"),
        )
        assert report.has_overdue is True

    def test_recommended_exit_code_zero_when_clean(self) -> None:
        report = ShimRegistryReport(
            entries=[self._make_status_entry(ShimStatus.PENDING)],
            project_version="3.2.0",
            registry_path=Path("architecture/2.x/shim-registry.yaml"),
        )
        assert report.recommended_exit_code == 0

    def test_recommended_exit_code_one_when_overdue(self) -> None:
        report = ShimRegistryReport(
            entries=[self._make_status_entry(ShimStatus.OVERDUE)],
            project_version="3.2.0",
            registry_path=Path("architecture/2.x/shim-registry.yaml"),
        )
        assert report.recommended_exit_code == 1

    def test_empty_entries_no_overdue(self) -> None:
        report = ShimRegistryReport(
            entries=[],
            project_version="3.2.0",
            registry_path=Path("architecture/2.x/shim-registry.yaml"),
        )
        assert report.has_overdue is False
        assert report.recommended_exit_code == 0


# ---------------------------------------------------------------------------
# check_shim_registry() integration
# ---------------------------------------------------------------------------


class TestCheckShimRegistry:
    def test_empty_registry_returns_empty_report(self, tmp_path: Path) -> None:
        root = _setup_repo(tmp_path)
        report = check_shim_registry(root)
        assert report.entries == []
        assert report.has_overdue is False

    def test_missing_pyproject_raises_file_not_found(self, tmp_path: Path) -> None:
        registry_dir = tmp_path / "architecture" / "2.x"
        registry_dir.mkdir(parents=True)
        yaml = YAML()
        with (registry_dir / "shim-registry.yaml").open("w") as fp:
            yaml.dump({"shims": []}, fp)
        with pytest.raises(FileNotFoundError, match="pyproject.toml"):
            check_shim_registry(tmp_path)

    def test_missing_registry_raises_file_not_found(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text('[project]\nname="x"\nversion="3.2.0"\n')
        with pytest.raises(FileNotFoundError):
            check_shim_registry(tmp_path)

    def test_pending_shim_classified_correctly(self, tmp_path: Path) -> None:
        shim_dict = {
            "legacy_path": "specify_cli.old_module",
            "canonical_import": "specify_cli.new_module",
            "introduced_in_release": "3.2.0",
            "removal_target_release": "3.5.0",
            "tracker_issue": "#1",
            "grandfathered": False,
        }
        root = _setup_repo(tmp_path, version="3.2.0", shims=[shim_dict])
        _create_shim_module(root, "specify_cli.old_module")
        report = check_shim_registry(root)
        assert len(report.entries) == 1
        assert report.entries[0].status == ShimStatus.PENDING
        assert report.entries[0].shim_exists is True

    def test_overdue_shim_sets_has_overdue(self, tmp_path: Path) -> None:
        shim_dict = {
            "legacy_path": "specify_cli.old_module",
            "canonical_import": "specify_cli.new_module",
            "introduced_in_release": "3.2.0",
            "removal_target_release": "3.2.0",
            "tracker_issue": "#1",
            "grandfathered": False,
        }
        root = _setup_repo(tmp_path, version="3.2.0", shims=[shim_dict])
        _create_shim_module(root, "specify_cli.old_module")
        report = check_shim_registry(root)
        assert report.has_overdue is True
        assert report.recommended_exit_code == 1

    def test_removed_shim_shim_exists_false(self, tmp_path: Path) -> None:
        shim_dict = {
            "legacy_path": "specify_cli.already_gone",
            "canonical_import": "specify_cli.new_module",
            "introduced_in_release": "3.2.0",
            "removal_target_release": "3.3.0",
            "tracker_issue": "#1",
            "grandfathered": False,
        }
        root = _setup_repo(tmp_path, version="3.2.0", shims=[shim_dict])
        report = check_shim_registry(root)
        assert report.entries[0].status == ShimStatus.REMOVED
        assert report.entries[0].shim_exists is False

    def test_grandfathered_shim_classified_correctly(self, tmp_path: Path) -> None:
        shim_dict = {
            "legacy_path": "specify_cli.old_module",
            "canonical_import": "specify_cli.new_module",
            "introduced_in_release": "3.2.0",
            "removal_target_release": "3.3.0",
            "tracker_issue": "#1",
            "grandfathered": True,
        }
        root = _setup_repo(tmp_path, version="99.0.0", shims=[shim_dict])
        report = check_shim_registry(root)
        assert report.entries[0].status == ShimStatus.GRANDFATHERED
        assert report.has_overdue is False

    def test_project_version_reflected_in_report(self, tmp_path: Path) -> None:
        root = _setup_repo(tmp_path, version="4.1.2")
        report = check_shim_registry(root)
        assert report.project_version == "4.1.2"

    def test_registry_path_reflected_in_report(self, tmp_path: Path) -> None:
        root = _setup_repo(tmp_path)
        report = check_shim_registry(root)
        assert report.registry_path == root / "architecture" / "2.x" / "shim-registry.yaml"

    def test_mixed_statuses_all_classified(self, tmp_path: Path) -> None:
        shims = [
            {
                "legacy_path": "specify_cli.overdue_shim",
                "canonical_import": "specify_cli.new_a",
                "introduced_in_release": "3.0.0",
                "removal_target_release": "3.2.0",
                "tracker_issue": "#1",
                "grandfathered": False,
            },
            {
                "legacy_path": "specify_cli.pending_shim",
                "canonical_import": "specify_cli.new_b",
                "introduced_in_release": "3.2.0",
                "removal_target_release": "4.0.0",
                "tracker_issue": "#2",
                "grandfathered": False,
            },
            {
                "legacy_path": "specify_cli.gone_shim",
                "canonical_import": "specify_cli.new_c",
                "introduced_in_release": "3.0.0",
                "removal_target_release": "3.5.0",
                "tracker_issue": "#3",
                "grandfathered": False,
            },
        ]
        root = _setup_repo(tmp_path, version="3.2.0", shims=shims)
        _create_shim_module(root, "specify_cli.overdue_shim")
        _create_shim_module(root, "specify_cli.pending_shim")
        # gone_shim intentionally not created

        report = check_shim_registry(root)
        statuses = {e.entry.legacy_path: e.status for e in report.entries}
        assert statuses["specify_cli.overdue_shim"] == ShimStatus.OVERDUE
        assert statuses["specify_cli.pending_shim"] == ShimStatus.PENDING
        assert statuses["specify_cli.gone_shim"] == ShimStatus.REMOVED
        assert report.has_overdue is True
