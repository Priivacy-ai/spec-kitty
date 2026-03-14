#!/usr/bin/env python3
"""Legacy research mission integration coverage."""

from __future__ import annotations

from pathlib import Path



def test_research_mission_loads_correctly(research_project_root: Path) -> None:
    """Research mission should load with correct configuration."""
    import sys

    sys.path.insert(0, str(Path.cwd() / "src"))

    from specify_cli.mission import get_active_mission

    mission = get_active_mission(research_project_root)

    assert mission.name == "Deep Research Kitty"
    assert mission.domain == "research"
    assert len(mission.config.workflow.phases) == 6
    assert "all_sources_documented" in mission.config.validation.checks


def test_research_templates_exist(research_project_root: Path) -> None:
    """Research templates should exist and be accessible."""
    import sys

    sys.path.insert(0, str(Path.cwd() / "src"))

    from specify_cli.mission import get_active_mission

    mission = get_active_mission(research_project_root)

    spec_template = mission.get_template("spec-template.md")
    assert spec_template.exists()
    content = spec_template.read_text()
    assert "Research Specification" in content or "RESEARCH QUESTION" in content

    plan_template = mission.get_template("plan-template.md")
    assert plan_template.exists()
    content = plan_template.read_text()
    assert "Research Plan" in content or "Methodology" in content


def test_path_validation_for_research_mission(research_project_root: Path) -> None:
    """Path validation should check research-specific paths."""
    import sys

    sys.path.insert(0, str(Path.cwd() / "src"))

    from specify_cli.mission import get_active_mission
    from specify_cli.validators.paths import validate_mission_paths

    mission = get_active_mission(research_project_root)

    result = validate_mission_paths(mission, research_project_root, strict=False)
    assert not result.is_valid
    assert len(result.warnings) > 0

    (research_project_root / "research").mkdir()
    result2 = validate_mission_paths(mission, research_project_root, strict=False)
    assert len(result2.missing_paths) < len(result.missing_paths)
