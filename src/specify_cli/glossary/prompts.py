"""Typer prompts for interactive clarification (WP06/T026, T027).

This module implements user prompts for conflict resolution and
non-interactive mode detection for CI environments.
"""

import logging
import os
import sys
from enum import StrEnum
from typing import List, Tuple

import typer

from .models import SemanticConflict

logger = logging.getLogger(__name__)


class PromptChoice(StrEnum):
    """User choice during clarification."""

    SELECT_CANDIDATE = "select"
    CUSTOM_SENSE = "custom"
    DEFER = "defer"


# --------------------------------------------------------------------------- #
# Non-interactive detection (T027)
# --------------------------------------------------------------------------- #

_CI_ENV_VARS = [
    "CI",
    "GITHUB_ACTIONS",
    "JENKINS_HOME",
    "GITLAB_CI",
    "CIRCLECI",
    "TRAVIS",
    "BUILDKITE",
]


def is_interactive() -> bool:
    """Detect if running in an interactive terminal.

    Checks:
    1. sys.stdin.isatty() -- True if connected to a terminal
    2. CI environment variables (CI, GITHUB_ACTIONS, JENKINS_HOME, etc.)

    Returns:
        True if interactive, False if non-interactive (CI, piped input, etc.)
    """
    # Check if stdin is a TTY
    if not sys.stdin.isatty():
        return False

    # Check common CI environment variables
    for var in _CI_ENV_VARS:
        if os.getenv(var):
            return False

    return True


def log_non_interactive_context() -> None:
    """Log details about non-interactive detection for debugging."""
    if not is_interactive():
        logger.info("Non-interactive mode detected")
        logger.info("  stdin.isatty(): %s", sys.stdin.isatty())
        detected_ci = [k for k in _CI_ENV_VARS if os.getenv(k)]
        if detected_ci:
            logger.info("  CI env vars: %s", detected_ci)


def auto_defer_conflicts(
    conflicts: List[SemanticConflict],
) -> List[Tuple[SemanticConflict, PromptChoice, None]]:
    """Auto-defer all conflicts in non-interactive mode.

    Args:
        conflicts: List of semantic conflicts

    Returns:
        List of (conflict, DEFER, None) tuples for each conflict
    """
    return [(conflict, PromptChoice.DEFER, None) for conflict in conflicts]


# --------------------------------------------------------------------------- #
# Interactive prompts (T026)
# --------------------------------------------------------------------------- #


def prompt_conflict_resolution(
    conflict: SemanticConflict,
) -> Tuple[PromptChoice, int | str | None]:
    """Prompt user to resolve a semantic conflict.

    Displays options:
    - 1-N: Select candidate sense (by number)
    - C: Provide custom sense definition
    - D: Defer to async resolution

    Args:
        conflict: The semantic conflict to resolve

    Returns:
        Tuple of (choice type, value):
        - (SELECT_CANDIDATE, candidate_index) if user selects 1-N (0-indexed)
        - (CUSTOM_SENSE, custom_definition) if user enters C
        - (DEFER, None) if user enters D

    Raises:
        typer.Abort: If user cancels with Ctrl+C
    """
    num_candidates = len(conflict.candidate_senses)

    # Build prompt message
    options: List[str] = []
    if num_candidates > 0:
        options.append(f"  1-{num_candidates}: Choose candidate sense")
    options.append("  C: Provide custom definition")
    options.append("  D: Defer to async resolution")
    options_text = "\n".join(options)

    prompt_msg = f"\nSelect resolution:\n{options_text}\n\nYour choice"

    while True:
        try:
            response = typer.prompt(prompt_msg).strip().upper()

            # Handle defer
            if response == "D":
                return (PromptChoice.DEFER, None)

            # Handle custom sense
            if response == "C":
                custom_def = typer.prompt(
                    "\nEnter custom definition",
                    type=str,
                ).strip()

                if not custom_def:
                    typer.echo("Error: Definition cannot be empty. Try again.")
                    continue

                return (PromptChoice.CUSTOM_SENSE, custom_def)

            # Handle candidate selection
            if response.isdigit():
                choice_num = int(response)
                if 1 <= choice_num <= num_candidates:
                    # Return 0-indexed candidate index
                    return (PromptChoice.SELECT_CANDIDATE, choice_num - 1)
                else:
                    if num_candidates > 0:
                        typer.echo(
                            f"Error: Please enter a number between 1 and {num_candidates}, C for custom, or D to defer."
                        )
                    else:
                        typer.echo("Error: No candidates available. Enter C for custom or D to defer.")
                    continue

            # Invalid input
            if num_candidates > 0:
                typer.echo(f"Error: Invalid choice '{response}'. Enter 1-{num_candidates}, C, or D.")
            else:
                typer.echo(f"Error: Invalid choice '{response}'. Enter C or D.")

        except typer.Abort:
            typer.echo("\nAborted by user.")
            raise


def prompt_conflict_resolution_safe(
    conflict: SemanticConflict,
) -> Tuple[PromptChoice, int | str | None]:
    """Safe prompt that auto-defers in non-interactive mode.

    Args:
        conflict: The semantic conflict to resolve

    Returns:
        (DEFER, None) if non-interactive, otherwise delegates to interactive prompt
    """
    if not is_interactive():
        typer.echo(f"Non-interactive mode detected: Auto-deferring conflict for '{conflict.term.surface_text}'")
        return (PromptChoice.DEFER, None)

    return prompt_conflict_resolution(conflict)


def prompt_context_change_confirmation(
    old_hash: str,
    new_hash: str,
) -> bool:
    """Prompt user to confirm resumption if context has changed.

    Args:
        old_hash: Original input hash from checkpoint
        new_hash: Current input hash

    Returns:
        True if user confirms, False otherwise
    """
    typer.echo(
        f"\nWarning: Step inputs have changed since checkpoint.\n"
        f"  Original hash: {old_hash[:16]}...\n"
        f"  Current hash:  {new_hash[:16]}...\n"
    )

    return typer.confirm(
        "Context may have changed. Proceed with resolution?",
        default=False,
    )
