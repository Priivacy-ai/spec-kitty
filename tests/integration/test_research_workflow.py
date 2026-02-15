#!/usr/bin/env python3
"""Integration tests for research mission workflows."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def research_project_root(tmp_path: Path) -> Path:
    """Create a test research mission project."""
    project_dir = tmp_path / "test-research"
    project_dir.mkdir()

    # Initialize git
    subprocess.run(["git", "init"], cwd=project_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=project_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=project_dir, check=True, capture_output=True)

    # Create .kittify structure with research mission
    kittify = project_dir / ".kittify"
    kittify.mkdir()

    # Copy missions from current repo (new location in src/)
    import shutil
    src_missions = Path.cwd() / "src" / "specify_cli" / "missions"
    if src_missions.exists():
        shutil.copytree(src_missions, kittify / "missions")

    # Set research as active mission
    active_link = kittify / "active-mission"
    try:
        active_link.symlink_to(Path("missions") / "research")
    except (OSError, NotImplementedError):
        # Fallback for systems without symlink support
        active_link.write_text("research\n")

    # Initial commit
    subprocess.run(["git", "add", "."], cwd=project_dir, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Init research project"], cwd=project_dir, check=True, capture_output=True)

    return project_dir


def test_research_mission_loads_correctly(research_project_root: Path) -> None:
    """Research mission should load with correct configuration."""
    import sys
    sys.path.insert(0, str(Path.cwd() / "src"))

    from specify_cli.mission_system import get_active_mission

    mission = get_active_mission(research_project_root)

    assert mission.name == "Deep Research Kitty"
    assert mission.domain == "research"
    assert len(mission.config.workflow.phases) == 6
    assert "all_sources_documented" in mission.config.validation.checks


def test_research_templates_exist(research_project_root: Path) -> None:
    """Research templates should exist and be accessible."""
    import sys
    sys.path.insert(0, str(Path.cwd() / "src"))

    from specify_cli.mission_system import get_active_mission

    mission = get_active_mission(research_project_root)

    spec_template = mission.get_template("spec-template.md")
    assert spec_template.exists()
    content = spec_template.read_text()
    assert "Research Specification" in content or "RESEARCH QUESTION" in content

    plan_template = mission.get_template("plan-template.md")
    assert plan_template.exists()
    content = plan_template.read_text()
    assert "Research Plan" in content or "Methodology" in content


def test_citation_validation_with_valid_data(tmp_path: Path) -> None:
    """Citation validation should pass with valid citations."""
    import sys
    sys.path.insert(0, str(Path.cwd() / "src"))

    from specify_cli.validators.research import validate_citations

    evidence_log = tmp_path / "evidence-log.csv"
    evidence_log.write_text(
        "timestamp,source_type,citation,key_finding,confidence,notes\n"
        "2025-01-15T10:00:00,journal,\"Smith (2024). Title. Journal.\",Finding,high,Notes\n"
    )

    result = validate_citations(evidence_log)
    assert not result.has_errors


def test_citation_validation_catches_errors(tmp_path: Path) -> None:
    """Citation validation should catch completeness errors."""
    import sys
    sys.path.insert(0, str(Path.cwd() / "src"))

    from specify_cli.validators.research import validate_citations

    invalid_log = tmp_path / "invalid.csv"
    invalid_log.write_text(
        "timestamp,source_type,citation,key_finding,confidence,notes\n"
        "2025-01-15T10:00:00,invalid_type,,Empty,wrong,\n"
    )

    result = validate_citations(invalid_log)
    assert result.has_errors
    assert result.error_count >= 2


def test_source_register_validation(tmp_path: Path) -> None:
    """Source register validation should work in research context."""
    import sys
    sys.path.insert(0, str(Path.cwd() / "src"))

    from specify_cli.validators.research import validate_source_register

    valid = tmp_path / "sources.csv"
    valid.write_text(
        "source_id,citation,url,accessed_date,relevance,status\n"
        "smith2024,\"Citation\",https://example.com,2025-01-15,high,reviewed\n"
    )

    result = validate_source_register(valid)
    assert not result.has_errors


def test_path_validation_for_research_mission(research_project_root: Path) -> None:
    """Path validation should check research-specific paths."""
    import sys
    sys.path.insert(0, str(Path.cwd() / "src"))

    from specify_cli.mission_system import get_active_mission
    from specify_cli.validators.paths import validate_mission_paths

    mission = get_active_mission(research_project_root)

    # No paths exist yet
    result = validate_mission_paths(mission, research_project_root, strict=False)
    assert not result.is_valid
    assert len(result.warnings) > 0

    # Create one path
    (research_project_root / "research").mkdir()
    result2 = validate_mission_paths(mission, research_project_root, strict=False)
    assert len(result2.missing_paths) < len(result.missing_paths)


@pytest.mark.xfail(reason="Requires interactive TTY for agent strategy selection")
def test_full_research_workflow_via_cli(tmp_path: Path, run_cli) -> None:
    """Full research workflow using CLI commands end-to-end."""
    import subprocess

    # Initialize research project via CLI
    result = run_cli(tmp_path, "init", "research-test", "--mission", "research", "--ai", "claude", "--no-git")

    project_dir = tmp_path / "research-test"
    assert result.returncode == 0, f"CLI init failed: {result.stderr}"
    assert project_dir.exists(), "spec-kitty init did not create project directory"

    # Init git for testing
    subprocess.run(["git", "init"], cwd=project_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=project_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=project_dir, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=project_dir, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Init"], cwd=project_dir, check=True, capture_output=True)

    # Verify research mission active
    result = run_cli(project_dir, "mission", "current")
    assert result.returncode == 0
    assert "research" in result.stdout.lower()

    # Create CSV artifacts
    research_dir = project_dir / "research"
    research_dir.mkdir()

    (research_dir / "evidence-log.csv").write_text(
        "timestamp,source_type,citation,key_finding,confidence,notes\n"
        "2025-01-15T10:00:00,journal,\"Smith (2024). Title.\",Finding,high,Notes\n"
    )

    (research_dir / "source-register.csv").write_text(
        "source_id,citation,url,accessed_date,relevance,status\n"
        "smith2024,\"Smith (2024). Title.\",https://example.com,2025-01-15,high,reviewed\n"
    )

    # Validate artifacts
    import sys
    sys.path.insert(0, str(Path.cwd() / "src"))
    from specify_cli.validators.research import validate_citations, validate_source_register

    result_cit = validate_citations(research_dir / "evidence-log.csv")
    assert not result_cit.has_errors

    result_src = validate_source_register(research_dir / "source-register.csv")
    assert not result_src.has_errors


def test_deliverables_path_in_meta_json(tmp_path: Path) -> None:
    """meta.json should correctly store and retrieve deliverables_path."""
    import sys
    import json
    sys.path.insert(0, str(Path.cwd() / "src"))

    from specify_cli.mission_system import get_deliverables_path

    # Create feature structure
    feature_dir = tmp_path / "kitty-specs" / "001-market-research"
    feature_dir.mkdir(parents=True)

    # Write meta.json with deliverables_path
    meta_file = feature_dir / "meta.json"
    meta_file.write_text(json.dumps({
        "mission": "research",
        "slug": "001-market-research",
        "deliverables_path": "docs/research/market-study/"
    }))

    # Verify retrieval
    result = get_deliverables_path(feature_dir)
    assert result == "docs/research/market-study/"


def test_deliverables_path_not_in_kitty_specs(tmp_path: Path) -> None:
    """deliverables_path must NOT be inside kitty-specs/."""
    import sys
    sys.path.insert(0, str(Path.cwd() / "src"))

    from specify_cli.mission_system import validate_deliverables_path

    # Should reject kitty-specs paths
    is_valid, error = validate_deliverables_path("kitty-specs/001-test/research/")
    assert not is_valid
    assert "kitty-specs" in error.lower()

    # Should accept proper paths
    is_valid, error = validate_deliverables_path("docs/research/001-test/")
    assert is_valid


def test_research_deliverables_separate_from_planning(tmp_path: Path) -> None:
    """Research deliverables should be separate from planning artifacts."""
    import sys
    import json
    sys.path.insert(0, str(Path.cwd() / "src"))

    from specify_cli.mission_system import get_deliverables_path, get_feature_mission_key

    # Create feature structure
    feature_dir = tmp_path / "kitty-specs" / "001-research"
    feature_dir.mkdir(parents=True)

    # Create research planning artifacts (in kitty-specs)
    research_planning = feature_dir / "research"
    research_planning.mkdir()
    (research_planning / "evidence-log.csv").write_text("timestamp,source_type,citation\n")
    (research_planning / "source-register.csv").write_text("source_id,citation,url\n")

    # Create meta.json with deliverables path
    meta_file = feature_dir / "meta.json"
    meta_file.write_text(json.dumps({
        "mission": "research",
        "deliverables_path": "docs/research/001-research/"
    }))

    # Verify separation
    assert get_feature_mission_key(feature_dir) == "research"
    deliverables = get_deliverables_path(feature_dir)
    assert deliverables == "docs/research/001-research/"

    # Planning artifacts exist in kitty-specs
    assert (research_planning / "evidence-log.csv").exists()
    assert (research_planning / "source-register.csv").exists()

    # Deliverables path is NOT in kitty-specs
    assert not deliverables.startswith("kitty-specs")


def test_default_deliverables_path_generation(tmp_path: Path) -> None:
    """Should generate default deliverables path when not specified."""
    import sys
    import json
    sys.path.insert(0, str(Path.cwd() / "src"))

    from specify_cli.mission_system import get_deliverables_path

    # Create feature with research mission but NO deliverables_path
    feature_dir = tmp_path / "kitty-specs" / "002-literature-review"
    feature_dir.mkdir(parents=True)

    meta_file = feature_dir / "meta.json"
    meta_file.write_text(json.dumps({
        "mission": "research",
        "slug": "002-literature-review"
        # Note: no deliverables_path
    }))

    # Should return default path
    result = get_deliverables_path(feature_dir)
    assert result == "docs/research/002-literature-review/"
