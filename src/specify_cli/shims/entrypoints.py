"""Shim dispatch entrypoints.

``shim_dispatch()`` is the single function called by every
``spec-kitty agent shim <command>`` subcommand.  It:

1. Parses *raw_args* to extract ``WP##`` codes, ``--mission`` / ``--mission-run`` values, etc.
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
from specify_cli.shims.registry import PROMPT_DRIVEN_COMMANDS


# ---------------------------------------------------------------------------
# Argument parsing helpers
# ---------------------------------------------------------------------------

_WP_CODE_PATTERN = re.compile(r"\bWP\d{2,}\b", re.IGNORECASE)
_FEATURE_FLAG_PATTERN = re.compile(r"--(?:feature|mission-run)\s+(\S+)")


def _parse_raw_args(raw_args: str) -> dict[str, str | None]:
    """Extract structured values from a raw agent argument string.

    Looks for:
    - A ``WP##`` code (first match wins).
    - A ``--mission <slug>`` or ``--mission-run <slug>`` value (``--feature`` is accepted as a legacy alias).

    All other content is silently ignored so that new flags added to
    agent slash commands don't break existing dispatch logic.

    Args:
        raw_args: Raw argument string passed from the agent runtime.

    Returns:
        Dictionary with keys ``"wp_code"`` and ``"mission_slug"``
        (each may be ``None`` if not found).
    """
    wp_match = _WP_CODE_PATTERN.search(raw_args)
    wp_code = wp_match.group(0).upper() if wp_match else None

    feature_match = _FEATURE_FLAG_PATTERN.search(raw_args)
    mission_slug = feature_match.group(1) if feature_match else None

    return {"wp_code": wp_code, "mission_slug": mission_slug}


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
        "charter",
    }
)


def shim_dispatch(
    command: str,
    agent: str,
    raw_args: str,
    context_token: str | None,
    repo_root: Path,
) -> MissionContext | None:
    """Resolve context and dispatch to the workflow handler for *command*.

    For prompt-driven commands (``PROMPT_DRIVEN_COMMANDS``), returns
    ``None`` immediately — their full prompt template handles the workflow
    and there is nothing for the CLI shim path to dispatch.

    For CLI-driven commands, resolves the mission context and returns it.

    Args:
        command:       Skill verb, e.g. ``"implement"``.
        agent:         Agent key, e.g. ``"claude"``.
        raw_args:      Raw argument string from the agent runtime.
        context_token: Pre-resolved context token, or ``None``.
        repo_root:     Absolute path to the repository root.

    Returns:
        The resolved :class:`~specify_cli.context.models.MissionContext`,
        or ``None`` if *command* is prompt-driven.

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

    # Prompt-driven commands are handled entirely by their full prompt
    # template file.  The CLI shim pathway is a no-op for them.
    if command in PROMPT_DRIVEN_COMMANDS:
        return None

    # Parse raw_args to extract wp_code and mission_slug
    parsed = _parse_raw_args(raw_args)
    wp_code: str | None = parsed["wp_code"]
    mission_slug: str | None = parsed["mission_slug"]

    # Resolve or load context
    context = resolve_or_load(
        token=context_token,
        wp_code=wp_code,
        mission_slug=mission_slug,
        agent=agent,
        repo_root=repo_root,
    )

    # Future: dispatch to command-specific workflow handlers here.
    # For now, context resolution IS the dispatch result — callers
    # use the returned MissionContext to drive their workflow.

    return context
