"""Top-level lifecycle command shims.

These commands provide CLI-visible entry points that delegate to the
agent lifecycle implementations.
"""

from __future__ import annotations

import re
from typing import Optional

import typer

from specify_cli.cli.selector_resolution import resolve_selector
from specify_cli.cli.commands.agent import mission as agent_feature


def _slugify_feature_input(value: str) -> str:
    """Normalize a free-form feature name to kebab-case slug text."""
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    if not slug:
        raise typer.BadParameter("Feature name cannot be empty.")
    return slug


def specify(
    feature: str = typer.Argument(..., help="Feature name or slug (e.g., user-authentication)"),
    mission_type: str | None = typer.Option(None, "--mission-type", help="Mission type (e.g., software-dev, research)"),
    mission: str | None = typer.Option(None, "--mission", hidden=True, help="(deprecated) Use --mission-type"),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON result"),
) -> None:
    """Create a feature scaffold in kitty-specs/."""
    slug = _slugify_feature_input(feature)
    resolved_mission_type = mission_type
    if mission_type is not None or mission is not None:
        resolved = resolve_selector(
            canonical_value=mission_type,
            canonical_flag="--mission-type",
            alias_value=mission,
            alias_flag="--mission",
            suppress_env_var="SPEC_KITTY_SUPPRESS_MISSION_TYPE_DEPRECATION",
            command_hint="--mission-type <name>",
        )
        resolved_mission_type = resolved.canonical_value
    agent_feature.create_mission(mission_slug=slug, mission_type=resolved_mission_type, json_output=json_output)


def plan(
    mission: str | None = typer.Option(None, "--mission", help="Mission slug (e.g., 001-user-authentication)"),
    feature: str | None = typer.Option(None, "--feature", hidden=True, help="(deprecated) Use --mission"),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON result"),
) -> None:
    """Scaffold plan.md for a feature."""
    resolved_mission = None
    if mission is not None or feature is not None:
        resolved = resolve_selector(
            canonical_value=mission,
            canonical_flag="--mission",
            alias_value=feature,
            alias_flag="--feature",
            suppress_env_var="SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION",
            command_hint="--mission <slug>",
        )
        resolved_mission = resolved.canonical_value
    agent_feature.setup_plan(feature=resolved_mission, json_output=json_output)


def tasks(
    json_output: bool = typer.Option(False, "--json", help="Emit JSON result"),
) -> None:
    """Finalize tasks metadata after task generation."""
    agent_feature.finalize_tasks(json_output=json_output)


__all__ = ["specify", "plan", "tasks"]
