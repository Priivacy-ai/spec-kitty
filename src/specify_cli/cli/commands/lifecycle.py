"""Top-level lifecycle command shims.

These commands provide CLI-visible entry points that delegate to the
agent lifecycle implementations.
"""

from __future__ import annotations

import re
from typing import Optional

import typer

from specify_cli.cli.commands.agent import feature as agent_feature


def _slugify_feature_input(value: str) -> str:
    """Normalize a free-form feature name to kebab-case slug text."""
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    if not slug:
        raise typer.BadParameter("Feature name cannot be empty.")
    return slug


def specify(
    feature: str = typer.Argument(..., help="Feature name or slug (e.g., user-authentication)"),
    mission: Optional[str] = typer.Option(None, "--mission", help="Mission type (e.g., software-dev, research)"),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON result"),
) -> None:
    """Create a feature scaffold in kitty-specs/."""
    slug = _slugify_feature_input(feature)
    agent_feature.create_feature(feature_slug=slug, mission=mission, json_output=json_output)


def plan(
    feature: Optional[str] = typer.Option(None, "--feature", help="Feature slug (e.g., 001-user-authentication)"),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON result"),
) -> None:
    """Scaffold plan.md for a feature."""
    agent_feature.setup_plan(feature=feature, json_output=json_output)


def tasks(
    json_output: bool = typer.Option(False, "--json", help="Emit JSON result"),
) -> None:
    """Finalize tasks metadata after task generation."""
    agent_feature.finalize_tasks(json_output=json_output)


__all__ = ["specify", "plan", "tasks"]
