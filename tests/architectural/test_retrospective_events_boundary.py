"""Boundary test: enforced once spec_kitty_events upstream release ships.

This test will be unskipped in the cutover PR. Until then, retrospective
event Pydantic models live locally in specify_cli.retrospective.events.
See docs/migration/retrospective-events-upstream.md for the cutover runbook.
"""

import pytest


@pytest.mark.skip(reason="pending spec_kitty_events upstream release: <TODO: WP12 issue link>")
def test_retrospective_events_single_home_post_cutover() -> None:
    """When upstream ships, no Retrospective*Payload Pydantic models live outside spec_kitty_events.

    Unskipped in the cutover PR (see docs/migration/retrospective-events-upstream.md).
    """
    raise AssertionError("intentionally not implemented until cutover")
