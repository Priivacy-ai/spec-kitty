"""Documentation parity for logged-out local Mission commands."""

from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.fast]

_POLICY_DOC = Path("docs/operations/logged-out-teamspace.md")
_EXPECTED_POLICY = {
    "spec-kitty agent mission create": (
        "Completes eligible local artifact work",
        "Never starts one",
        "Local mission-creation result and exit code",
    ),
    "spec-kitty agent mission setup-plan": (
        "Completes eligible local verification",
        "Never starts one",
        "Local verification payload and exit code",
    ),
}


def _policy_rows(text: str) -> dict[str, tuple[str, str, str]]:
    """Parse the command-keyed policy table without relying on nearby prose."""
    rows: dict[str, tuple[str, str, str]] = {}
    for line in text.splitlines():
        if not line.startswith("| `spec-kitty agent mission "):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != 4:
            continue
        rows[cells[0].strip("`")] = (cells[1], cells[2], cells[3])
    return rows


def test_create_and_setup_plan_share_logged_out_local_command_policy() -> None:
    """Each sibling command has its own complete, noninteractive policy row."""
    text = _POLICY_DOC.read_text(encoding="utf-8")
    assert _policy_rows(text) == _EXPECTED_POLICY


def test_policy_parser_keeps_command_rows_independent() -> None:
    """A contradictory setup-plan row cannot borrow create's policy cells."""
    contradictory = """
| `spec-kitty agent mission create` | Completes eligible local artifact work | Never starts one | Local mission-creation result and exit code |
| `spec-kitty agent mission setup-plan` | Refuses local verification | Starts login | Hosted result |
"""

    rows = _policy_rows(contradictory)
    assert rows["spec-kitty agent mission create"] == _EXPECTED_POLICY["spec-kitty agent mission create"]
    assert rows["spec-kitty agent mission setup-plan"] != _EXPECTED_POLICY["spec-kitty agent mission setup-plan"]
