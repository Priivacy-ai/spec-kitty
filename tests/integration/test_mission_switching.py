#!/usr/bin/env python3
"""Comprehensive integration tests for mission switching workflows."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def clean_project(tmp_path: Path) -> Path:
    """Create clean spec-kitty project for mission switching tests."""
    project_dir = tmp_path / "test-project"
    project_dir.mkdir()

    # Initialize git
    subprocess.run(["git", "init"], cwd=project_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=project_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=project_dir, check=True, capture_output=True)

    # Create .kittify with both missions
    kittify = project_dir / ".kittify"
    kittify.mkdir()

    import shutil
    src_missions = Path.cwd() / ".kittify" / "missions"
    if src_missions.exists():
        shutil.copytree(src_missions, kittify / "missions")

    # Set software-dev as active
    active = kittify / "active-mission"
    try:
        active.symlink_to(Path("missions") / "software-dev")
    except (OSError, NotImplementedError):
        active.write_text("software-dev\n")

    subprocess.run(["git", "add", "."], cwd=project_dir, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Init"], cwd=project_dir, check=True, capture_output=True)

    return project_dir


def test_switch_changes_active_mission_link(clean_project: Path) -> None:
    """Switching missions should update active-mission symlink."""
    import sys
    sys.path.insert(0, str(Path.cwd() / "src"))

    from specify_cli.mission import set_active_mission, get_active_mission

    # Start with software-dev
    mission = get_active_mission(clean_project)
    assert mission.path.name == "software-dev"

    # Switch to research
    kittify_dir = clean_project / ".kittify"
    set_active_mission("research", kittify_dir)

    # Verify switch
    mission = get_active_mission(clean_project)
    assert mission.path.name == "research"
    assert mission.name == "Deep Research Kitty"


def test_switch_back_to_original_mission(clean_project: Path) -> None:
    """Should be able to switch back to original mission."""
    import sys
    sys.path.insert(0, str(Path.cwd() / "src"))

    from specify_cli.mission import set_active_mission, get_active_mission

    kittify_dir = clean_project / ".kittify"

    # software-dev → research → software-dev
    set_active_mission("research", kittify_dir)
    mission = get_active_mission(clean_project)
    assert mission.domain == "research"

    set_active_mission("software-dev", kittify_dir)
    mission = get_active_mission(clean_project)
    assert mission.domain == "software"


def test_templates_change_after_switch(clean_project: Path) -> None:
    """Templates should come from new mission after switch."""
    import sys
    sys.path.insert(0, str(Path.cwd() / "src"))

    from specify_cli.mission import set_active_mission, get_active_mission

    kittify_dir = clean_project / ".kittify"

    # Get software-dev template
    mission1 = get_active_mission(clean_project)
    spec1 = mission1.get_template("spec-template.md").read_text()

    # Switch to research
    set_active_mission("research", kittify_dir)
    mission2 = get_active_mission(clean_project)
    spec2 = mission2.get_template("spec-template.md").read_text()

    # Templates should be different
    assert spec1 != spec2
    assert "Research" in spec2 or "research" in spec2.lower()


def test_path_warnings_at_mission_switch(clean_project: Path) -> None:
    """Mission switch should warn about missing paths (non-blocking)."""
    import sys
    sys.path.insert(0, str(Path.cwd() / "src"))

    from specify_cli.mission import set_active_mission, get_active_mission
    from specify_cli.validators.paths import validate_mission_paths

    kittify_dir = clean_project / ".kittify"

    # Switch to research (has different paths: research/, data/)
    set_active_mission("research", kittify_dir)
    mission = get_active_mission(clean_project)

    # Validate paths (non-strict)
    result = validate_mission_paths(mission, clean_project, strict=False)

    # Should warn but not fail
    assert not result.is_valid
    assert len(result.warnings) > 0
    assert "research/" in str(result.missing_paths) or "data/" in str(result.missing_paths)


def test_validation_checks_differ_by_mission(clean_project: Path) -> None:
    """Different missions should have different validation checks."""
    import sys
    sys.path.insert(0, str(Path.cwd() / "src"))

    from specify_cli.mission import set_active_mission, get_active_mission

    kittify_dir = clean_project / ".kittify"

    # Software-dev checks
    mission1 = get_active_mission(clean_project)
    checks1 = mission1.config.validation.checks
    assert "git_clean" in checks1 or "all_tests_pass" in checks1

    # Research checks
    set_active_mission("research", kittify_dir)
    mission2 = get_active_mission(clean_project)
    checks2 = mission2.config.validation.checks
    assert "all_sources_documented" in checks2 or "methodology_clear" in checks2

    # Checks should be different
    assert set(checks1) != set(checks2)


def test_workflow_phases_differ_by_mission(clean_project: Path) -> None:
    """Different missions should have different workflow phases."""
    import sys
    sys.path.insert(0, str(Path.cwd() / "src"))

    from specify_cli.mission import set_active_mission, get_active_mission

    kittify_dir = clean_project / ".kittify"

    # Software-dev phases (research → design → implement → test → review)
    mission1 = get_active_mission(clean_project)
    phases1 = [p.name for p in mission1.config.workflow.phases]
    assert "implement" in phases1 or "design" in phases1

    # Research phases (question → methodology → gather → analyze → synthesize → publish)
    set_active_mission("research", kittify_dir)
    mission2 = get_active_mission(clean_project)
    phases2 = [p.name for p in mission2.config.workflow.phases]
    assert "methodology" in phases2 or "synthesize" in phases2

    # Phases should be different
    assert phases1 != phases2
