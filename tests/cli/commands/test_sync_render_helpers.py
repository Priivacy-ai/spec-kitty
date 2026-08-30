"""Focused unit tests for the ``sync`` render helpers extracted in WP03 T009.

Each helper collapsed a Sonar ``S3358`` nested ternary. The behaviour must be
byte-identical to the inline form it replaced, so these tests pin every band /
branch the ternaries encoded.
"""

from __future__ import annotations

import pytest

from specify_cli.cli.commands.sync import (
    _depth_color,
    _override_label,
    _selector_kind,
)

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]


@pytest.mark.parametrize(
    ("pct", "expected"),
    [
        (0, "green"),
        (79.9, "green"),
        (80, "yellow"),
        (99.9, "yellow"),
        (100, "red"),
        (150, "red"),
    ],
)
def test_depth_color_bands(pct: float, expected: str) -> None:
    assert _depth_color(pct) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, "[dim]Not set[/dim]"),
        (True, "enabled"),
        (False, "disabled"),
    ],
)
def test_override_label_tri_state(value: bool | None, expected: str) -> None:
    assert _override_label(value) == expected


@pytest.mark.parametrize(
    ("project", "identity_less", "expected"),
    [
        ("proj-uuid", False, "project"),
        ("proj-uuid", True, "project"),
        (None, True, "identity-less"),
        (None, False, "all"),
    ],
)
def test_selector_kind_classification(project: str | None, identity_less: bool, expected: str) -> None:
    assert _selector_kind(project, identity_less) == expected
