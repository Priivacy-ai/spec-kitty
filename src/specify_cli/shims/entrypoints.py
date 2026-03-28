"""Shim dispatch entrypoints.

``shim_dispatch()`` is the single function called by every
``spec-kitty agent shim <command>`` subcommand.  It:

1. Parses *raw_args* to extract ``WP##`` codes, ``--feature`` values, etc.
2. Loads an existing context if *context_token* is supplied.
3. Otherwise, resolves a new context from the parsed arguments.
4. Dispatches to the appropriate workflow handler.

All workflow logic lives here and in the CLI layer — **not** in shim files.
"""

from __future__ import annotations

import re
from pathlib import Path

from specify_cli.context.models import MissionContext
from specify_cli.context.resolver import resolve_or_load


# ---------------------------------------------------------------------------
# Argument parsing helpers
# ---------------------------------------------------------------------------

_WP_CODE_PATTERN = re.compile(r"\bWP\d{2,}\b", re.IGNORECASE)
_FEATURE_FLAG_PATTERN = re.compile(r"--feature\s+(\S+)")


def _parse_raw_args(raw_args: str) -> dict[str, str | None]:
    """Extract structured values from a raw agent argument string.

    Looks for:
    - A ``WP##`` code (first match wins).
    - A ``--feature <slug>`` value.

    All other content is silently ignored so that new flags added to
    agent slash commands don't break existing dispatch logic.

    Args:
        raw_args: Raw argument string passed from the agent runtime.

    Returns:
        Dictionary with keys ``"wp_code"`` and ``"feature_slug"``
        (each may be ``None`` if not found).
    """
    wp_match = _WP_CODE_PATTERN.search(raw_args)
    wp_code = wp_match.group(0).upper() if wp_match else None

    feature_match = _FEATURE_FLAG_PATTERN.search(raw_args)
    feature_slug = feature_match.group(1) if feature_match else None

    return {"wp_code": wp_code, "feature_slug": feature_slug}


# ---------------------------------------------------------------------------
# Public dispatch entrypoint
# ---------------------------------------------------------------------------

# Mapping from command verb to a description used in error messages.
# Expand this as new workflow handlers are wired in.
_KNOWN_COMMANDS: frozenset[str] = frozenset(
    {
        "specify",
        "plan",
        "tasks",
        "tasks-outline",
        "tasks-packages",
        "tasks-finalize",
        "implement",
        "review",
        "accept",
        "merge",
        "status",
        "dashboard",
        "checklist",
        "analyze",
        "research",
        "constitution",
    }
)


def shim_dispatch(
    command: str,
    agent: str,
    raw_args: str,
    context_token: str | None,
    repo_root: Path,
) -> MissionContext:
    """Resolve context and dispatch to the workflow handler for *command*.

    Args:
        command:       Skill verb, e.g. ``"implement"``.
        agent:         Agent key, e.g. ``"claude"``.
        raw_args:      Raw argument string from the agent runtime.
        context_token: Pre-resolved context token, or ``None``.
        repo_root:     Absolute path to the repository root.

    Returns:
        The resolved :class:`~specify_cli.context.models.MissionContext`.

    Raises:
        ValueError: If *command* is not a known consumer skill.
        MissingArgumentError: If neither token nor sufficient raw args
            are provided.
        ContextResolutionError: If context resolution fails.
    """
    if command not in _KNOWN_COMMANDS:
        known = ", ".join(sorted(_KNOWN_COMMANDS))
        msg = (
            f"Unknown shim command '{command}'. "
            f"Expected one of: {known}."
        )
        raise ValueError(msg)

    # Parse raw_args to extract wp_code and feature_slug
    parsed = _parse_raw_args(raw_args)
    wp_code: str | None = parsed["wp_code"]
    feature_slug: str | None = parsed["feature_slug"]

    # Resolve or load context
    context = resolve_or_load(
        token=context_token,
        wp_code=wp_code,
        feature_slug=feature_slug,
        agent=agent,
        repo_root=repo_root,
    )

    # Future: dispatch to command-specific workflow handlers here.
    # For now, context resolution IS the dispatch result — callers
    # use the returned MissionContext to drive their workflow.

    return context
