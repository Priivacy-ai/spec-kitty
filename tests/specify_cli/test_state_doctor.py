"""Tests for the state-roots doctor diagnostic."""

from __future__ import annotations

import json

from specify_cli.state.doctor import check_state_roots


def test_roots_resolved(tmp_path):
    """check_state_roots resolves three roots with correct names."""
    (tmp_path / ".kittify").mkdir()
    report = check_state_roots(tmp_path)
    root_names = [r.name for r in report.roots]
    assert "project" in root_names
    assert "global_runtime" in root_names
    assert "global_sync" in root_names


def test_project_root_exists(tmp_path):
    """Project root detected as existing when .kittify/ directory is present."""
    (tmp_path / ".kittify").mkdir()
    report = check_state_roots(tmp_path)
    project = next(r for r in report.roots if r.name == "project")
    assert project.exists is True


def test_project_root_absent(tmp_path):
    """Project root detected as absent when .kittify/ directory is missing."""
    report = check_state_roots(tmp_path)
    project = next(r for r in report.roots if r.name == "project")
    assert project.exists is False


def test_surface_present(tmp_path):
    """Present surfaces are detected when the file exists on disk."""
    (tmp_path / ".kittify").mkdir()
    (tmp_path / ".kittify" / "config.yaml").write_text("agents: {}")
    report = check_state_roots(tmp_path)
    config_check = next(
        (s for s in report.surfaces if s.surface.name == "project_config"),
        None,
    )
    assert config_check is not None
    assert config_check.present is True


def test_surface_absent(tmp_path):
    """Absent surfaces are detected when the file does not exist."""
    report = check_state_roots(tmp_path)
    config_check = next(
        (s for s in report.surfaces if s.surface.name == "project_config"),
        None,
    )
    assert config_check is not None
    assert config_check.present is False


def test_absent_runtime_no_warning(tmp_path):
    """Absent runtime surfaces are not warnings (lazily created)."""
    (tmp_path / ".kittify").mkdir()
    report = check_state_roots(tmp_path)
    runtime_checks = [
        s for s in report.surfaces if s.surface.name == "runtime_feature_index"
    ]
    for check in runtime_checks:
        assert check.warning is None  # Absent = no warning


def test_report_to_dict_serializable(tmp_path):
    """Report to_dict() output is JSON-serializable."""
    report = check_state_roots(tmp_path)
    d = report.to_dict()
    json.dumps(d)  # Must not raise
    assert "healthy" in d
    assert "roots" in d
    assert "surfaces" in d
    assert "warnings" in d


def test_healthy_when_no_warnings(tmp_path):
    """Report is healthy when there are no warnings."""
    report = check_state_roots(tmp_path)
    # With no runtime surfaces on disk, no warnings expected
    assert report.healthy is True


def test_warning_for_unignored_runtime(tmp_path, monkeypatch):
    """Present runtime surface not covered by gitignore produces warning."""
    (tmp_path / ".kittify").mkdir()
    (tmp_path / ".kittify" / "merge-state.json").write_text("{}")

    # Mock _is_gitignore_covered to return False
    from specify_cli.state import doctor as doctor_mod

    monkeypatch.setattr(doctor_mod, "_is_gitignore_covered", lambda *a: False)

    report = check_state_roots(tmp_path)
    merge_check = next(
        (s for s in report.surfaces if s.surface.name == "merge_resume_state"),
        None,
    )
    assert merge_check is not None
    assert merge_check.warning is not None
    assert "merge-state.json" in merge_check.warning
    assert not report.healthy


def test_no_warning_for_tracked_surface(tmp_path, monkeypatch):
    """Tracked surfaces never produce gitignore warnings."""
    (tmp_path / ".kittify").mkdir()
    (tmp_path / ".kittify" / "config.yaml").write_text("agents: {}")

    # Even if gitignore says "not covered", tracked surfaces are fine
    from specify_cli.state import doctor as doctor_mod

    monkeypatch.setattr(doctor_mod, "_is_gitignore_covered", lambda *a: False)

    report = check_state_roots(tmp_path)
    config_check = next(
        (s for s in report.surfaces if s.surface.name == "project_config"),
        None,
    )
    assert config_check is not None
    assert config_check.warning is None


def test_surfaces_cover_all_state_surfaces(tmp_path):
    """Report surfaces list covers every entry in STATE_SURFACES."""
    from specify_cli.state_contract import STATE_SURFACES

    report = check_state_roots(tmp_path)
    assert len(report.surfaces) == len(STATE_SURFACES)
    report_names = {s.surface.name for s in report.surfaces}
    registry_names = {s.name for s in STATE_SURFACES}
    assert report_names == registry_names
