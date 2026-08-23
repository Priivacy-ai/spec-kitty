"""Documentation parity for logged-out local Mission commands."""

from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.fast]

_POLICY_DOC = Path("docs/operations/logged-out-teamspace.md")
_LOCAL_COMMANDS = (
    "`spec-kitty agent mission create`",
    "`spec-kitty agent mission setup-plan`",
)


def test_create_and_setup_plan_share_logged_out_local_command_policy() -> None:
    """Both sibling commands stay explicitly governed by the local-work rule."""
    text = _POLICY_DOC.read_text(encoding="utf-8")
    section = text.split("Local Mission commands are different.", maxsplit=1)[1]
    section = section.split("The interactive recovery surface", maxsplit=1)[0]
    normalized = " ".join(section.split())

    for command in _LOCAL_COMMANDS:
        assert command in section
    assert "complete eligible local artifact work while logged out" in normalized
    assert "local verification payload and exit code remain authoritative" in normalized
    assert "must not start an interactive login" in normalized
