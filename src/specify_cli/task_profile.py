"""Task type → agent profile suggestion utilities.

Provides a deterministic lookup from a WP's task_type (or title-inferred type)
to a suggested agent_profile, using agent_role hints stored in mission YAML files.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rich.console import Console

# Maps mission template agent_role → concrete profile name
ROLE_TO_PROFILE: dict[str, str] = {
    "implementer": "implementer",
    "reviewer": "reviewer",
    "planner": "planner",
    "researcher": "researcher",
    "writer": "designer",
    "curator": "curator",
}

# Keywords used to infer task_type from WP title when task_type is absent
_TITLE_KEYWORDS: list[tuple[str, list[str]]] = [
    ("review", ["review", "audit", "check", "validate", "verify", "assess"]),
    ("specify", ["spec", "specification", "requirement", "scenario", "user story"]),
    ("plan", ["plan", "design", "architect", "outline", "structure"]),
    ("research", ["research", "investigate", "explore", "survey", "study"]),
    ("implement", [
        "implement", "implementation", "migration", "migrate", "integration",
        "integrate", "add ", "create", "build", "write", "update", "fix", "refactor",
    ]),
]


def _infer_task_type_from_title(title: str) -> str | None:
    """Heuristic: map a WP title to a task_type via keyword scan."""
    lower = title.lower()
    for task_type, keywords in _TITLE_KEYWORDS:
        if any(kw in lower for kw in keywords):
            return task_type
    return None


def suggest_profile_for_wp(
    task_type: str | None,
    mission_config: dict[str, object],
) -> str | None:
    """Return the suggested agent_profile for *task_type* using mission config.

    Args:
        task_type: Task type string (e.g. "implement", "review"). May be None.
        mission_config: Parsed mission YAML dict with optional ``task_types`` section.

    Returns:
        Profile name string, or None if no mapping exists.
    """
    if not task_type:
        return None
    task_types = mission_config.get("task_types") or {}
    if not isinstance(task_types, dict):
        return None
    type_def = task_types.get(task_type)
    if not isinstance(type_def, dict):
        return None
    role = type_def.get("agent_role")
    if not isinstance(role, str):
        return None
    return ROLE_TO_PROFILE.get(role)


def apply_profile_suggestions(
    wp_files: list[Path],
    mission_config: dict[str, object],
) -> list[tuple[str, str]]:
    """Suggest and write agent_profile into WP frontmatter files.

    Only writes if agent_profile is absent in the current frontmatter.

    Args:
        wp_files: List of WP .md file paths to process.
        mission_config: Parsed mission YAML dict.

    Returns:
        List of (wp_id, profile) pairs for WPs that received a suggestion.
    """
    from specify_cli.frontmatter import read_frontmatter, write_frontmatter

    suggestions: list[tuple[str, str]] = []

    for wp_file in wp_files:
        try:
            frontmatter, body = read_frontmatter(wp_file)
        except Exception:  # noqa: BLE001, S112
            continue

        # Skip if profile already set
        if frontmatter.get("agent_profile"):
            continue

        # Determine task_type: explicit > title inference
        task_type = frontmatter.get("task_type") or None
        if not task_type:
            title = str(frontmatter.get("title") or wp_file.stem)
            task_type = _infer_task_type_from_title(title)

        profile = suggest_profile_for_wp(task_type, mission_config)
        if not profile:
            continue

        wp_id_match = re.match(r"(WP\d{2,})", wp_file.name)
        wp_id = wp_id_match.group(1) if wp_id_match else wp_file.stem

        frontmatter["agent_profile"] = profile
        write_frontmatter(wp_file, frontmatter, body)
        suggestions.append((wp_id, profile))

    return suggestions


def display_profile_suggestions(
    suggestions: list[tuple[str, str]],
    console: Console,
) -> None:
    """Print the agent profile suggestion summary to the console.

    Args:
        suggestions: List of (wp_id, profile) pairs.
        console: Rich Console for output.
    """
    if not suggestions:
        return
    console.print("\n[bold]Agent Profile Suggestions[/bold]")
    console.print(
        "The following profiles were suggested based on task types in the mission template.\n"
    )
    for wp_id, profile in suggestions:
        console.print(f"  [cyan]{wp_id}[/cyan]: [green]{profile}[/green]")
    console.print(
        "\n[dim]To override a profile, edit the agent_profile field in the WP frontmatter.[/dim]"
    )
