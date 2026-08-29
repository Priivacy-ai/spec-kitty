"""A daemon tick that could not authenticate is not a successful tick (#3030 H7).

#598 pinned "an auth failure escalates backoff" with three tests
(``test_sync_once_401_escalates_backoff``,
``test_sync_once_401_does_not_drain_body_queue``,
``test_full_sync_401_escalates_backoff``). WP02 removed the queue-backed event
drain those tests posted through, and the tests were deleted **without a
replacement written against the surviving body drain** — so the property lost its
witness even though it still matters.

Two things must hold on every tick:

* A tick that could not get a token must escalate backoff and must not stamp
  ``last_sync``. Otherwise ``sync status`` reports a healthy last sync while
  nothing moves — the #3004 false-green class this mission folded.
* A tick that genuinely drained resets backoff and stamps ``last_sync``.

The second seam is the subtle one: ``_drain_body_queue`` fetches its **own**
token and used to ``return`` silently when it was ``None``, after which the tick
fell through to "success". An expired token therefore produced a green tick that
delivered nothing.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

from specify_cli.sync.background import BackgroundSyncService
from specify_cli.sync.queue import OfflineQueue
from specify_cli.sync.project_store import ProjectSyncStore

PROJECT_UUID = "aaaaaaaa-0000-0000-0000-000000000001"


@pytest.fixture(autouse=True)
def _saas_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """These are daemon-tick tests; the rollout flag is not what they measure."""
    monkeypatch.setattr(
        "specify_cli.sync.background.is_saas_sync_enabled", lambda: True
    )


@pytest.fixture
def service(tmp_path, monkeypatch) -> BackgroundSyncService:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    store = ProjectSyncStore(PROJECT_UUID)
    authority = store.layout_generation()
    authority.begin_cutover("background-auth-test")
    authority.publish_project_only("background-auth-test", verify_exact=lambda: True)
    with store.unit_of_work() as unit:
        background = BackgroundSyncService(
            queue=OfflineQueue(unit, authority),
            config=MagicMock(),
            sync_interval_seconds=0.1,
        )
        monkeypatch.setattr(background, "_has_discovered_project_candidates", lambda: False)
        yield background


def _no_token() -> None:
    return None


class TestTokenAbsentTickIsAFailure:
    """``_fetch_access_token_sync() is None`` at the top of a tick."""

    def test_sync_once_without_a_token_escalates_backoff(
        self, service: BackgroundSyncService
    ) -> None:
        with patch(
            "specify_cli.sync.background._fetch_access_token_sync", _no_token
        ):
            service._sync_once()

            assert service._consecutive_failures == 1, (
                "an unauthenticated tick is a failed tick; it must count"
            )
            assert service._backoff_seconds == 1.0, (
                "backoff must escalate so the daemon retries on the failure "
                "schedule rather than the steady-state interval"
            )
            service._sync_once()
            assert service._consecutive_failures == 2
            assert service._backoff_seconds == 2.0

    def test_sync_once_without_a_token_does_not_stamp_last_sync(
        self, service: BackgroundSyncService
    ) -> None:
        with patch(
            "specify_cli.sync.background._fetch_access_token_sync", _no_token
        ):
            service._sync_once()

        assert service.last_sync is None, (
            "stamping last_sync on a tick that delivered nothing makes "
            "`sync status` report a healthy sync while nothing moves (#3004)"
        )

    def test_full_sync_without_a_token_escalates_backoff(
        self, service: BackgroundSyncService
    ) -> None:
        with patch(
            "specify_cli.sync.background._fetch_access_token_sync", _no_token
        ):
            service._perform_full_sync()

        assert service._consecutive_failures == 1
        assert service._backoff_seconds == 1.0
        assert service.last_sync is None


class TestBodyDrainAuthFailureIsNotSuccess:
    """The inner token fetch inside ``_drain_body_queue`` is a second auth seam."""

    def test_tick_whose_body_drain_could_not_authenticate_is_not_a_success(
        self, service: BackgroundSyncService
    ) -> None:
        """A silent body-drain auth bail must not read as a delivered tick.

        The outer fetch succeeds and the inner one fails (token expiry between
        the two, or a revoked refresh). Before the fix the tick reset
        ``consecutive_failures`` and stamped ``last_sync``.
        """
        service._body_queue = MagicMock()
        service._body_queue.remove_stale.return_value = 0
        service._consecutive_failures = 3
        service._backoff_seconds = 4.0

        tokens = iter(["outer-token", None])
        with patch(
            "specify_cli.sync.background._fetch_access_token_sync",
            lambda: next(tokens),
        ):
            result = service._sync_once()

        assert service.last_sync is None, (
            "the body drain never authenticated, so nothing was delivered"
        )
        assert service._consecutive_failures == 4
        assert service._backoff_seconds == 8.0
        # Reported, not swallowed. Via error_messages rather than error_count: a
        # fabricated count makes _should_retry_final_sync_result retry the
        # exit-time final sync (3 attempts, 1s sleeps) for a tick with nothing to
        # send — added latency on the #598 hang path.
        assert any(
            "Not authenticated" in message for message in result.error_messages
        ), "the failure must be reported, not swallowed"
        assert result.error_count == 0, (
            "no fabricated error count: it would re-trigger the final-sync retry "
            "loop for an unauthenticated tick over an empty queue (#598)"
        )


class TestGenuineSuccessStillResetsAndStamps:
    """The other half of the contract: real progress must look like progress."""

    def test_successful_body_drain_resets_backoff_and_stamps_last_sync(
        self, service: BackgroundSyncService
    ) -> None:
        service._body_queue = MagicMock()
        service._body_queue.remove_stale.return_value = 0
        service._body_queue.drain.return_value = []
        service._consecutive_failures = 3
        service._backoff_seconds = 8.0

        with patch(
            "specify_cli.sync.background._fetch_access_token_sync",
            lambda: "token",
        ):
            service._sync_once()

        assert service._consecutive_failures == 0
        assert service._backoff_seconds == 0.5
        assert service.last_sync is not None

    # NOTE: the post-upload-loop ``return True`` inside ``_drain_body_queue`` is
    # deliberately NOT pinned here. As of T025 that path runs through the
    # consent-windowed task collection, so a test for it has to speak that seam's
    # API; pinning it belongs with T025's own suite rather than coupling this
    # auth-backoff file to it. The empty-queue exit above covers the True side of
    # the contract that this file owns.

    def test_failing_body_drain_still_escalates_backoff(
        self, service: BackgroundSyncService
    ) -> None:
        service._body_queue = MagicMock()
        with (
            patch(
                "specify_cli.sync.background._fetch_access_token_sync",
                lambda: "token",
            ),
            patch.object(
                service, "_drain_body_queue", side_effect=Exception("boom")
            ),
        ):
            service._sync_once()

        assert service._consecutive_failures == 1
        assert service._backoff_seconds == 1.0
        assert service.last_sync is None
