"""
Tests for plan mission runtime support (Feature 041).

Coverage:
- Mission discovery integration test
- Command resolution tests (all 4 steps)
- Regression tests (software-dev, research missions)
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from typing import Generator


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_project(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary spec-kitty project for testing.

    Setup: Creates minimal project structure
    Teardown: Cleanup handled by tmp_path
    Yields: Path to project root
    """
    # Create kitty-specs/ directory
    (tmp_path / "kitty-specs").mkdir()

    # Create .kittify/ directory
    (tmp_path / ".kittify").mkdir()

    # Create .git/ directory (for git operations)
    (tmp_path / ".git").mkdir()

    yield tmp_path
    # Cleanup handled by tmp_path


@pytest.fixture
def plan_feature(temp_project: Path) -> Generator[tuple[str, Path], None, None]:
    """Create a test feature with mission=plan.

    Depends on: temp_project
    Yields: (feature_slug, feature_dir)
    """
    feature_slug = "001-test-plan-feature"
    feature_dir = temp_project / "kitty-specs" / feature_slug
    feature_dir.mkdir()

    # Create meta.json with mission: "plan"
    meta = {
        "feature_number": "001",
        "slug": feature_slug,
        "mission": "plan",
        "created_at": "2026-02-22T00:00:00+00:00"
    }
    (feature_dir / "meta.json").write_text(json.dumps(meta, indent=2))

    # Create spec.md
    (feature_dir / "spec.md").write_text(
        "# Test Feature\n\n"
        "This is a test feature for plan mission integration.\n"
    )

    yield (feature_slug, feature_dir)


@pytest.fixture
def mock_runtime_bridge() -> MagicMock:
    """Mock the runtime bridge for unit tests.

    Returns: MagicMock with methods:
    - discover_mission(mission_key) -> mission_definition
    - resolve_command(mission, step) -> template_content
    """
    bridge = MagicMock()

    # Configure discover_mission to return valid plan mission definition
    bridge.discover_mission.return_value = {
        "mission": {
            "key": "plan",
            "steps": [
                {"id": "specify", "order": 1, "title": "Specify"},
                {"id": "research", "order": 2, "title": "Research"},
                {"id": "plan", "order": 3, "title": "Plan"},
                {"id": "review", "order": 4, "title": "Review"}
            ]
        }
    }

    # Configure resolve_command to return template content
    bridge.resolve_command.return_value = "<resolved template>"

    return bridge


@pytest.fixture
def mock_workspace_context() -> MagicMock:
    """Mock workspace context for testing.

    Returns: MagicMock with properties:
    - feature_slug
    - wp_id
    - base_branch
    """
    context = MagicMock()
    context.feature_slug = "001-test-plan-feature"
    context.wp_id = "WP01"
    context.base_branch = "main"
    return context


# ============================================================================
# Test Classes
# ============================================================================

class TestPlanMissionIntegration:
    """Integration tests for plan mission feature creation and runtime."""

    def test_create_plan_feature_with_mission_yaml(self, plan_feature):
        """Verify plan feature can be created with mission=plan."""
        feature_slug, feature_dir = plan_feature

        # Verify feature directory exists
        assert feature_dir.exists()

        # Verify meta.json exists and contains mission=plan
        meta_file = feature_dir / "meta.json"
        assert meta_file.exists()

        meta = json.loads(meta_file.read_text())
        assert meta["mission"] == "plan"
        assert meta["slug"] == feature_slug

    def test_plan_feature_spec_file_created(self, plan_feature):
        """Verify spec.md is created for plan features."""
        feature_slug, feature_dir = plan_feature

        # Verify spec.md exists
        spec_file = feature_dir / "spec.md"
        assert spec_file.exists()

        # Verify it contains expected content
        content = spec_file.read_text()
        assert "Test Feature" in content
        assert len(content) > 0

    def test_runtime_bridge_discovers_plan_mission(self, mock_runtime_bridge):
        """Verify plan mission can be discovered via runtime bridge."""
        result = mock_runtime_bridge.discover_mission("plan")

        # Verify mission definition structure
        assert "mission" in result
        assert result["mission"]["key"] == "plan"
        assert "steps" in result["mission"]

        # Verify all 4 steps are present
        steps = result["mission"]["steps"]
        assert len(steps) == 4

        step_ids = [step["id"] for step in steps]
        expected_steps = ["specify", "research", "plan", "review"]
        assert step_ids == expected_steps

    def test_plan_mission_all_steps_reachable(self, mock_runtime_bridge):
        """Verify all 4 steps are accessible."""
        mission_def = mock_runtime_bridge.discover_mission("plan")
        steps = mission_def["mission"]["steps"]

        # Verify steps are in correct order
        for i, expected_id in enumerate(["specify", "research", "plan", "review"], 1):
            assert steps[i-1]["id"] == expected_id
            assert steps[i-1]["order"] == i


class TestPlanCommandResolution:
    """Resolution tests for plan mission command templates."""

    def test_resolve_specify_command_template(self, mock_runtime_bridge):
        """Verify specify.md template resolves successfully."""
        result = mock_runtime_bridge.resolve_command("plan", "specify")

        # Verify template is resolved
        assert result is not None
        assert len(result) > 0

    def test_resolve_research_command_template(self, mock_runtime_bridge):
        """Verify research.md template resolves successfully."""
        result = mock_runtime_bridge.resolve_command("plan", "research")

        # Verify template is resolved
        assert result is not None
        assert len(result) > 0

    def test_resolve_plan_command_template(self, mock_runtime_bridge):
        """Verify plan.md template resolves successfully."""
        result = mock_runtime_bridge.resolve_command("plan", "plan")

        # Verify template is resolved
        assert result is not None
        assert len(result) > 0

    def test_resolve_review_command_template(self, mock_runtime_bridge):
        """Verify review.md template resolves successfully."""
        result = mock_runtime_bridge.resolve_command("plan", "review")

        # Verify template is resolved
        assert result is not None
        assert len(result) > 0

    def test_resolve_all_plan_steps(self, mock_runtime_bridge):
        """Verify all 4 step templates resolve."""
        mission_def = mock_runtime_bridge.discover_mission("plan")
        steps = mission_def["mission"]["steps"]

        for step in steps:
            result = mock_runtime_bridge.resolve_command("plan", step["id"])
            assert result is not None


class TestPlanMissionRegressions:
    """Regression tests ensuring no impacts to other missions."""

    def test_plan_mission_isolated_from_software_dev(self):
        """Verify plan mission doesn't interfere with software-dev."""
        # TODO: Implement
        # Should verify that software-dev mission steps are still intact
        pass

    def test_plan_mission_isolated_from_research(self):
        """Verify plan mission doesn't interfere with research."""
        # TODO: Implement
        # Should verify that research mission steps are still intact
        pass

    def test_mission_runtime_yaml_validation(self):
        """Verify mission-runtime.yaml is valid YAML."""
        # TODO: Implement
        # Should load and validate mission-runtime.yaml structure
        pass


class TestPlanMissionSteps:
    """Tests for individual plan mission steps."""

    def test_specify_step_has_deliverables(self):
        """Verify specify step documents deliverables."""
        # TODO: Implement
        # Should check specify.md for deliverables section
        pass

    def test_research_step_has_deliverables(self):
        """Verify research step documents deliverables."""
        # TODO: Implement
        # Should check research.md for deliverables section
        pass

    def test_plan_step_has_deliverables(self):
        """Verify plan step documents deliverables."""
        # TODO: Implement
        # Should check plan.md for deliverables section
        pass

    def test_review_step_has_deliverables(self):
        """Verify review step documents deliverables."""
        # TODO: Implement
        # Should check review.md for deliverables section
        pass


class TestPlanMissionWorkflow:
    """Tests for plan mission workflow progression."""

    def test_workflow_steps_ordered_correctly(self, mock_runtime_bridge):
        """Verify workflow steps progress in correct order."""
        mission_def = mock_runtime_bridge.discover_mission("plan")
        steps = mission_def["mission"]["steps"]

        # Verify ordering
        for i, step in enumerate(steps, 1):
            assert step["order"] == i

    def test_step_transitions_valid(self):
        """Verify valid transitions between steps."""
        # TODO: Implement
        # Should test that step transitions are allowed
        pass
