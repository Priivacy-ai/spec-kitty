"""ModeOfWork enum and deterministic derivation from CLI entry command.

See ADR-002-mode-derivation.md for the rationale and acceptance mapping.
"""

from __future__ import annotations

from enum import StrEnum


class ModeOfWork(StrEnum):
    ADVISORY = "advisory"
    TASK_EXECUTION = "task_execution"
    MISSION_STEP = "mission_step"
    QUERY = "query"


_ENTRY_COMMAND_MODE: dict[str, ModeOfWork] = {
    # Invocation-openers
    "advise": ModeOfWork.ADVISORY,
    "ask": ModeOfWork.TASK_EXECUTION,
    "do": ModeOfWork.TASK_EXECUTION,
    # Mission-step drivers (invoked via `spec-kitty next --agent ...`)
    "next.specify": ModeOfWork.MISSION_STEP,
    "next.plan": ModeOfWork.MISSION_STEP,
    "next.tasks": ModeOfWork.MISSION_STEP,
    "next.implement": ModeOfWork.MISSION_STEP,
    "next.review": ModeOfWork.MISSION_STEP,
    "next.merge": ModeOfWork.MISSION_STEP,
    "next.accept": ModeOfWork.MISSION_STEP,
    # Query commands (no InvocationRecord opened today, but mode is recorded
    # for future use and for enforcement consistency)
    "profiles.list": ModeOfWork.QUERY,
    "invocations.list": ModeOfWork.QUERY,
}


def derive_mode(entry_command: str) -> ModeOfWork:
    """Derive ModeOfWork from a CLI entry command.

    Args:
        entry_command: One of the keys in the _ENTRY_COMMAND_MODE mapping.

    Returns:
        The corresponding ModeOfWork.

    Raises:
        KeyError: if entry_command is not registered. Callers MUST catch and
            surface a clear CLI error — a mistyped entry_command indicates a
            programming error at the CLI layer, not an operator error.
    """
    return _ENTRY_COMMAND_MODE[entry_command]
