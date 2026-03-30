"""Shared utility for resolving --mission / --feature flag backward compatibility."""
from __future__ import annotations

import warnings

import typer


def resolve_mission_or_feature(
    mission: str | None,
    feature: str | None,
) -> str | None:
    """Resolve --mission / --feature flag pair.

    Returns:
        The resolved slug, or None if neither was provided.

    Raises:
        typer.BadParameter: If both flags are provided with different values.
    """
    # Normalize: old-style typer annotations pass an OptionInfo object as the
    # default when the function is called directly (not via CLI runner). Treat
    # any non-string value as "not provided".
    if not isinstance(mission, str):
        mission = None
    if not isinstance(feature, str):
        feature = None

    if mission and feature:
        if mission != feature:
            raise typer.BadParameter(
                f"Conflicting flags: --mission={mission!r} and --feature={feature!r}. "
                "Use --mission only (--feature is deprecated).",
                param_hint="'--mission' / '--feature'",
            )
        # Same value — accept silently, prefer mission
        return mission
    if feature is not None:
        warnings.warn(
            "--feature is deprecated; use --mission instead.",
            DeprecationWarning,
            stacklevel=3,
        )
        return feature
    return mission  # may be None
