"""Unit tests for derive_mode() from CLI entry command."""

from __future__ import annotations

import pytest

from specify_cli.invocation.modes import ModeOfWork, derive_mode


@pytest.mark.parametrize(
    ("entry_command", "expected"),
    [
        ("advise", ModeOfWork.ADVISORY),
        ("ask", ModeOfWork.TASK_EXECUTION),
        ("do", ModeOfWork.TASK_EXECUTION),
        ("next.specify", ModeOfWork.MISSION_STEP),
        ("next.plan", ModeOfWork.MISSION_STEP),
        ("next.tasks", ModeOfWork.MISSION_STEP),
        ("next.implement", ModeOfWork.MISSION_STEP),
        ("next.review", ModeOfWork.MISSION_STEP),
        ("next.merge", ModeOfWork.MISSION_STEP),
        ("next.accept", ModeOfWork.MISSION_STEP),
        ("profiles.list", ModeOfWork.QUERY),
        ("invocations.list", ModeOfWork.QUERY),
    ],
)
def test_derive_mode_table(entry_command: str, expected: ModeOfWork) -> None:
    assert derive_mode(entry_command) == expected


def test_derive_mode_unknown_raises() -> None:
    with pytest.raises(KeyError):
        derive_mode("not-a-real-command")


def test_mode_enum_str_round_trip() -> None:
    """ModeOfWork is a str-Enum so JSONL round-trip works."""
    assert ModeOfWork.ADVISORY.value == "advisory"
    assert str(ModeOfWork.ADVISORY) in {"ModeOfWork.ADVISORY", "advisory"}
