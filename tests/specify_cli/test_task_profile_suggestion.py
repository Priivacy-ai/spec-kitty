"""ATDD acceptance tests for task template role hints and profile suggestion (WP09).

Scenarios:
1. Mission template YAML has agent_role in task_type definitions.
2. Profile is suggested and written to WP frontmatter based on task_type.
3. finalize-tasks confirmation step outputs profile review section.
"""

from __future__ import annotations

from pathlib import Path

import yaml


# ---------------------------------------------------------------------------
# Scenario 1 — mission template has agent_role
# ---------------------------------------------------------------------------


def test_role_hint_in_mission_template() -> None:
    """software-dev mission.yaml must have at least one task_type with agent_role."""
    from doctrine.missions.repository import MissionRepository

    mission_yaml = MissionRepository.default_missions_root() / "software-dev" / "mission.yaml"
    assert mission_yaml.exists(), f"Mission YAML not found: {mission_yaml}"
    config = yaml.safe_load(mission_yaml.read_text(encoding="utf-8"))
    task_types = config.get("task_types", {})
    assert task_types, "No task_types section found in mission YAML"
    roles = [t.get("agent_role") for t in task_types.values() if isinstance(t, dict)]
    assert any(roles), "No agent_role defined in any task_type"


# ---------------------------------------------------------------------------
# Scenario 2 — profile suggestion written to WP frontmatter
# ---------------------------------------------------------------------------


def test_profile_suggested_in_generated_wp(tmp_path: Path) -> None:
    """apply_profile_suggestions writes agent_profile into WP frontmatter."""
    from specify_cli.task_profile import apply_profile_suggestions

    # WP file with task_type set (as an LLM would generate it)
    wp_file = tmp_path / "WP01-some-implementation.md"
    wp_file.write_text(
        "---\n"
        "work_package_id: WP01\n"
        "title: Implement something\n"
        "task_type: implement\n"
        "lane: planned\n"
        "---\n\n# WP01\n",
        encoding="utf-8",
    )

    mission_config = {
        "task_types": {
            "implement": {"agent_role": "implementer"},
            "review": {"agent_role": "reviewer"},
        }
    }

    suggestions = apply_profile_suggestions([wp_file], mission_config)

    # The function should return suggestions
    assert suggestions, "No profile suggestions returned"
    assert suggestions[0][1] == "implementer", f"Expected 'implementer', got {suggestions[0][1]}"

    # WP file should now contain agent_profile
    content = wp_file.read_text(encoding="utf-8")
    assert "agent_profile: implementer" in content


# ---------------------------------------------------------------------------
# Scenario 3 — finalize-tasks output includes profile review section
# ---------------------------------------------------------------------------


def test_finalize_tasks_shows_profile_confirmation(capsys) -> None:
    """display_profile_suggestions outputs a profile review section."""
    from io import StringIO

    from rich.console import Console

    from specify_cli.task_profile import display_profile_suggestions

    buf = StringIO()
    console = Console(file=buf, highlight=False)

    suggestions = [("WP01", "implementer"), ("WP02", "reviewer")]
    display_profile_suggestions(suggestions, console)

    output = buf.getvalue()
    assert "Agent Profile Suggestions" in output or "profile" in output.lower()
    assert "implementer" in output
    assert "reviewer" in output
