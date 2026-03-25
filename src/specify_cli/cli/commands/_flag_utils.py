"""Shared utility for resolving --mission / --feature flag backward compatibility."""
from __future__ import annotations

import warnings

import typer


def resolve_mission_type(
    mission_type: str | None,
    mission: str | None,
) -> str | None:
    """Resolve --mission-type (canonical) vs --mission (deprecated alias for type selection).

    Returns mission_type if set; returns mission with deprecation warning if only mission set;
    returns None if neither set.
    """
    if mission_type is not None:
        return mission_type
    if mission is not None:
        typer.echo("Warning: --mission is deprecated for type selection; use --mission-type instead", err=True)
        return mission
    return None


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
