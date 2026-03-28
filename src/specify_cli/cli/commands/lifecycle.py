"""Top-level lifecycle command shims.

These commands provide CLI-visible entry points that delegate to the
agent lifecycle implementations.
"""

from __future__ import annotations

import re

import typer

from specify_cli.cli.commands._flag_utils import resolve_mission_or_feature, resolve_mission_type
from specify_cli.cli.commands.agent import mission as agent_mission


def _slugify_mission_input(value: str) -> str:
    """Normalize a free-form mission name to kebab-case slug text."""
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    if not slug:
        raise typer.BadParameter("Mission name cannot be empty.")
    return slug


def specify(
    mission_name: str = typer.Argument(..., help="Mission name or slug (e.g., user-authentication)"),
    mission_type: str | None = typer.Option(None, "--mission-type", help="Mission type (e.g., software-dev, research)"),
    mission_legacy: str | None = typer.Option(None, "--mission", hidden=True, help="[Removed] Use --mission-type"),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON result"),
) -> None:
    """Create a mission scaffold in kitty-specs/."""
    slug = _slugify_mission_input(mission_name)
    resolved_type = resolve_mission_type(mission_type, mission_legacy)
    agent_mission.create_mission(mission_name=slug, mission_type=resolved_type, json_output=json_output)


def plan(
    mission: str | None = typer.Option(None, "--mission", help="Mission slug (e.g., 001-user-authentication)"),
    feature: str | None = typer.Option(None, "--feature", hidden=True, help="[Deprecated] Use --mission"),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON result"),
) -> None:
    """Scaffold plan.md for a mission."""
    mission_flag = resolve_mission_or_feature(mission, feature)
    agent_mission.setup_plan(mission=mission_flag, json_output=json_output)


def tasks(
    json_output: bool = typer.Option(False, "--json", help="Emit JSON result"),
) -> None:
    """Finalize tasks metadata after task generation."""
    agent_mission.finalize_tasks(json_output=json_output)


__all__ = ["specify", "plan", "tasks"]
