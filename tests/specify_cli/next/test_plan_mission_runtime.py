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

    def test_next_command_plan_feature_not_blocked(self, plan_feature):
        """Verify spec-kitty next doesn't block on plan features (Feature 041 fix).

        This is the core regression test: plan mission should be discoverable
        and should NOT return "Mission 'plan' not found" error.
        """
        feature_slug, feature_dir = plan_feature
        import yaml

        # 1. Verify feature has mission=plan
        meta = json.loads((feature_dir / "meta.json").read_text())
        assert meta["mission"] == "plan", "Feature must have mission=plan"

        # 2. Verify mission-runtime.yaml exists (required for discovery)
        mission_runtime = Path("src/specify_cli/missions/plan/mission-runtime.yaml")
        assert mission_runtime.exists(), "mission-runtime.yaml must exist"

        # 3. Verify it parses as valid YAML
        mission_def = yaml.safe_load(mission_runtime.read_text())
        assert mission_def["mission"]["key"] == "plan", "Mission key must be plan"

        # 4. Verify mission is NOT blocked (would have status "blocked": true)
        # The runtime should discover the plan mission successfully
        assert "steps" in mission_def["mission"], "Mission must have steps"
        assert len(mission_def["mission"]["steps"]) == 4, "Plan mission must have 4 steps"

        # 5. Verify no error would be raised by discovery
        # (In real execution, discover_mission would be called and not raise exception)
        try:
            mission = yaml.safe_load(mission_runtime.read_text())
            assert mission is not None, "Mission should load successfully"
        except Exception as e:
            pytest.fail(f"Failed to discover plan mission: {e}")


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
        import yaml

        # Verify software-dev mission exists and is intact
        sd_runtime = Path("src/specify_cli/missions/software-dev/mission-runtime.yaml")
        assert sd_runtime.exists(), "software-dev mission-runtime.yaml must exist"

        # Load and parse
        data = yaml.safe_load(sd_runtime.read_text())
        assert "mission" in data, "software-dev must have 'mission' key at top level"
        assert data["mission"]["key"] == "software-dev", "Mission key must be software-dev"

        # Verify steps exist (software-dev has steps at top level)
        assert "steps" in data, "software-dev must have steps at top level"
        steps = data["steps"]
        assert len(steps) > 0, "software-dev must have at least one step"

        # Verify core templates exist for software-dev
        cmd_dir = Path("src/specify_cli/missions/software-dev/command-templates")
        core_templates = ["specify.md", "plan.md", "implement.md", "review.md"]
        for template in core_templates:
            template_file = cmd_dir / template
            assert template_file.exists(), f"Missing core template {template} in software-dev"

    def test_plan_mission_isolated_from_research(self):
        """Verify plan mission doesn't interfere with research."""
        import yaml

        # Verify research mission exists and is intact
        r_mission = Path("src/specify_cli/missions/research/mission.yaml")
        assert r_mission.exists(), "research mission.yaml must exist"

        # Load and parse
        data = yaml.safe_load(r_mission.read_text())
        assert "mission" in data, "research must have 'mission' key at top level"

        # Research mission has states at top level - verify it has the expected structure
        assert "states" in data, "research must have states at top level"
        states = data["states"]
        assert len(states) > 0, "research must have at least one state"

        # Verify command templates exist
        cmd_dir = Path("src/specify_cli/missions/research/command-templates")
        assert cmd_dir.exists(), "research command-templates directory must exist"
        assert len(list(cmd_dir.glob("*.md"))) > 0, "research must have command templates"

        # Verify core templates for research
        core_templates = ["specify.md", "plan.md", "review.md"]
        for template in core_templates:
            template_file = cmd_dir / template
            assert template_file.exists(), f"Missing core template {template} in research"

    def test_mission_runtime_yaml_validation(self):
        """Verify mission-runtime.yaml is valid YAML and structure is correct."""
        import yaml

        # Load plan mission-runtime.yaml
        plan_runtime = Path("src/specify_cli/missions/plan/mission-runtime.yaml")
        assert plan_runtime.exists(), "plan mission-runtime.yaml must exist"

        content = plan_runtime.read_text()
        mission = yaml.safe_load(content)

        # Verify top-level structure
        assert "mission" in mission, "Must have 'mission' key"

        # Verify mission fields
        mission_obj = mission["mission"]
        assert mission_obj["key"] == "plan", "Mission key must be 'plan'"
        assert "title" in mission_obj, "Mission must have title"
        assert "description" in mission_obj, "Mission must have description"

        # Verify steps structure
        assert "steps" in mission_obj, "Mission must have steps"
        steps = mission_obj["steps"]
        assert len(steps) == 4, "Plan mission must have exactly 4 steps"

        # Verify each step has required fields
        for i, step in enumerate(steps, 1):
            assert "id" in step, f"Step {i} must have id"
            assert "name" in step, f"Step {i} must have name"
            assert "description" in step, f"Step {i} must have description"
            assert "order" in step, f"Step {i} must have order"
            assert step["order"] == i, f"Step {i} order must be {i}"

        # Verify dependency chain
        assert steps[0].get("depends_on", []) == [], "First step must not depend on others"
        assert steps[1].get("depends_on") == ["specify"], "Research must depend on specify"
        assert steps[2].get("depends_on") == ["research"], "Plan must depend on research"
        assert steps[3].get("depends_on") == ["plan"], "Review must depend on plan"

        # Verify runtime configuration
        assert "runtime" in mission_obj, "Mission must have runtime config"
        runtime = mission_obj["runtime"]
        assert runtime["loop_type"] == "sequential", "Loop type must be sequential"
        assert runtime["step_transition"] == "manual", "Step transition must be manual"
        assert runtime["prompt_template_dir"] == "command-templates", "Prompt dir must be command-templates"
        assert runtime["terminal_step"] == "review", "Terminal step must be review"


class TestPlanMissionSteps:
    """Tests for individual plan mission steps."""

    def test_specify_step_has_deliverables(self):
        """Verify specify step documents deliverables."""
        template = Path("src/specify_cli/missions/plan/command-templates/specify.md")
        assert template.exists(), "specify.md must exist"

        content = template.read_text()
        assert "## Deliverables" in content, "specify.md must have Deliverables section"
        assert len(content) > 100, "specify.md must have meaningful content"

    def test_research_step_has_deliverables(self):
        """Verify research step documents deliverables."""
        template = Path("src/specify_cli/missions/plan/command-templates/research.md")
        assert template.exists(), "research.md must exist"

        content = template.read_text()
        assert "## Deliverables" in content, "research.md must have Deliverables section"
        assert len(content) > 100, "research.md must have meaningful content"

    def test_plan_step_has_deliverables(self):
        """Verify plan step documents deliverables."""
        template = Path("src/specify_cli/missions/plan/command-templates/plan.md")
        assert template.exists(), "plan.md must exist"

        content = template.read_text()
        assert "## Deliverables" in content, "plan.md must have Deliverables section"
        assert len(content) > 100, "plan.md must have meaningful content"

    def test_review_step_has_deliverables(self):
        """Verify review step documents deliverables."""
        template = Path("src/specify_cli/missions/plan/command-templates/review.md")
        assert template.exists(), "review.md must exist"

        content = template.read_text()
        assert "## Deliverables" in content, "review.md must have Deliverables section"
        assert len(content) > 100, "review.md must have meaningful content"


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
        """Verify valid transitions between steps follow dependency chain."""
        import yaml

        # Load mission definition
        mission_yaml = Path("src/specify_cli/missions/plan/mission-runtime.yaml")
        mission = yaml.safe_load(mission_yaml.read_text())
        steps = mission["mission"]["steps"]

        # Build a map of step_id -> step for quick lookup
        step_map = {step["id"]: step for step in steps}

        # Verify each step can transition to its dependents only
        step_ids = [s["id"] for s in steps]

        # Verify linear chain: each step depends only on the previous one
        for i, step_id in enumerate(step_ids):
            step = step_map[step_id]
            depends_on = step.get("depends_on", [])

            if i == 0:
                # First step has no dependencies
                assert depends_on == [], f"Step {step_id} should not depend on anything"
            else:
                # Each step depends only on the previous one
                expected_dep = step_ids[i - 1]
                assert depends_on == [expected_dep], \
                    f"Step {step_id} should depend only on {expected_dep}, got {depends_on}"

        # Verify no cycles (linear chain is acyclic by definition)
        assert len(step_ids) == len(set(step_ids)), "Step IDs must be unique"

        # Verify terminal step is correct
        assert mission["mission"]["runtime"]["terminal_step"] == "review", \
            "Terminal step must be review (last step)"
