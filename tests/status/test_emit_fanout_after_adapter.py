"""Regression test: emit_status_transition fan-out works end-to-end.

After P1.3 the status package no longer imports from sync; SaaS fan-out
is routed through registered adapters. This test guards against the
failure mode where the registry pattern silently drops fan-out.

Cases covered:
1. A registered SaaS handler receives the fan-out from emit_status_transition.
2. An empty registry degrades to a logged no-op (handlers=0 breadcrumb).
3. A failing handler does not block canonical persistence.

(The former "importing specify_cli.sync registers the handlers" bootstrap
case died with the sync transport, issue #5; production registrants return
with epic E3.)
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from specify_cli.status import adapters
from specify_cli.status.emit import emit_status_transition
from specify_cli.status.models import Lane, StatusEvent, TransitionRequest
from tests.status.conftest import seed_wp_to_planned as _seed_planned

pytestmark = pytest.mark.fast


@pytest.fixture
def feature_dir(tmp_path: Path) -> Path:
    fd = tmp_path / "kitty-specs" / "test-feature"
    fd.mkdir(parents=True)
    return fd


class TestFanOutPreservation:
    """emit_status_transition must invoke registered fan-out handlers."""

    def test_saas_fanout_fires_when_handler_registered(self, feature_dir: Path) -> None:
        """Registering a SaaS handler causes emit_status_transition to call it."""
        adapters.reset_handlers()
        captured: list[dict] = []

        def fake_saas(**kwargs: object) -> None:
            captured.append(dict(kwargs))

        adapters.register_saas_fanout_handler(fake_saas)

        try:
            _seed_planned(feature_dir, "WP01")
            event = emit_status_transition(
                TransitionRequest(
                    feature_dir=feature_dir,
                    mission_slug="test-feature",
                    wp_id="WP01",
                    to_lane="claimed",
                    actor="test-actor",
                )
            )
            assert isinstance(event, StatusEvent)
            assert event.to_lane == Lane.CLAIMED

            assert len(captured) == 1, "SaaS fan-out handler must be invoked exactly once"
            call = captured[0]
            assert call["wp_id"] == "WP01"
            assert call["to_lane"] == "claimed"
            assert call["actor"] == "test-actor"
            assert call["mission_slug"] == "test-feature"
        finally:
            adapters.reset_handlers()

    def test_no_handlers_registered_logs_zero_handler_breadcrumb(
        self,
        feature_dir: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Empty registry -> emit succeeds and logs handlers=0 for diagnosis."""
        adapters.reset_handlers()

        try:
            _seed_planned(feature_dir, "WP01")
            caplog.set_level(logging.INFO, logger="specify_cli.status.adapters")
            event = emit_status_transition(
                TransitionRequest(
                    feature_dir=feature_dir,
                    mission_slug="test-feature",
                    wp_id="WP01",
                    to_lane="claimed",
                    actor="test-actor",
                )
            )
            assert event is not None
            assert event.to_lane == Lane.CLAIMED
            # ``force`` now travels inside the ``metadata=WPStatusChangeMetadata``
            # object (S107 cleanup) rather than as a top-level fire_saas_fanout()
            # kwarg. The #1141 breadcrumb still surfaces it: adapters._fanout_force
            # duck-types ``metadata.force`` when no top-level ``force`` is present,
            # so the diagnostic keeps reporting the real flag.
            assert ("fire_saas_fanout: wp_id=WP01 from=planned to=claimed force=False handlers=0") in caplog.text
        finally:
            adapters.reset_handlers()

    def test_handler_exception_does_not_block_persistence(self, feature_dir: Path) -> None:
        """A failing handler must not propagate or block canonical persistence."""
        adapters.reset_handlers()

        def boom(**kwargs: object) -> None:
            raise RuntimeError("handler exploded")

        adapters.register_saas_fanout_handler(boom)

        try:
            _seed_planned(feature_dir, "WP01")
            event = emit_status_transition(
                TransitionRequest(
                    feature_dir=feature_dir,
                    mission_slug="test-feature",
                    wp_id="WP01",
                    to_lane="claimed",
                    actor="test-actor",
                )
            )
            assert event is not None
        finally:
            adapters.reset_handlers()
