"""Unit tests for the RFC 8628 device authorization flow poller (WP03)."""

from __future__ import annotations

import asyncio
import unittest.mock

import pytest

from specify_cli.auth.device_flow import (
    DeviceFlowPoller,
    DeviceFlowState,
    format_user_code,
)
from specify_cli.auth.errors import DeviceFlowDenied, DeviceFlowExpired


# ---------------------------------------------------------------------------
# format_user_code
# ---------------------------------------------------------------------------


class TestFormatUserCode:
    """Tests for the :func:`format_user_code` helper."""

    def test_short_code(self) -> None:
        """Codes of 4 or fewer characters pass through unchanged."""
        assert format_user_code("ABCD") == "ABCD"

    def test_8char_code(self) -> None:
        """An 8-character code is hyphenated at the 4-char boundary."""
        assert format_user_code("ABCD1234") == "ABCD-1234"

    def test_already_formatted(self) -> None:
        """A code that is already hyphenated is stable under the helper."""
        assert format_user_code("ABCD-1234") == "ABCD-1234"

    def test_12char_code(self) -> None:
        """A 12-character code is split into three 4-char chunks."""
        assert format_user_code("ABCD12345678") == "ABCD-1234-5678"

    def test_strips_spaces(self) -> None:
        """Whitespace in the incoming code is removed before chunking."""
        assert format_user_code("ABCD 1234") == "ABCD-1234"


# ---------------------------------------------------------------------------
# DeviceFlowPoller
# ---------------------------------------------------------------------------


def make_state(expires_in: int = 900, interval: int = 1) -> DeviceFlowState:
    """Build a :class:`DeviceFlowState` suitable for poller tests."""
    return DeviceFlowState.from_oauth_response(
        {
            "device_code": "dc_xyz",
            "user_code": "ABCD-1234",
            "verification_uri": "https://saas.test/device",
            "expires_in": expires_in,
            "interval": interval,
        }
    )


@pytest.mark.asyncio
class TestDeviceFlowPoller:
    """Tests for the :class:`DeviceFlowPoller` polling loop."""

    async def test_success_after_two_pending(self) -> None:
        """Poller returns the token response after two pending attempts."""
        state = make_state(interval=0)
        poller = DeviceFlowPoller(state)
        responses = [
            {"error": "authorization_pending"},
            {"error": "authorization_pending"},
            {
                "access_token": "at_xyz",
                "refresh_token": "rt_xyz",
                "expires_in": 3600,
                "scope": "offline_access",
                "session_id": "sess_1",
            },
        ]
        call_count = 0

        async def mock_request(device_code: str) -> dict:
            nonlocal call_count
            assert device_code == "dc_xyz"
            r = responses[call_count]
            call_count += 1
            return r

        result = await poller.poll(mock_request)
        assert result["access_token"] == "at_xyz"
        assert state.poll_count == 3

    async def test_on_pending_callback_invoked(self) -> None:
        """Callback is invoked on each authorization_pending response."""
        state = make_state(interval=0)
        poller = DeviceFlowPoller(state)
        responses = [
            {"error": "authorization_pending"},
            {
                "access_token": "at",
                "refresh_token": "rt",
                "expires_in": 3600,
                "scope": "",
                "session_id": "s",
            },
        ]
        call_count = 0
        pending_calls: list[int] = []

        async def mock_request(device_code: str) -> dict:
            nonlocal call_count
            r = responses[call_count]
            call_count += 1
            return r

        def on_pending(_state: DeviceFlowState) -> None:
            pending_calls.append(_state.poll_count)

        await poller.poll(mock_request, on_pending=on_pending)
        assert pending_calls == [1]

    async def test_access_denied(self) -> None:
        """SaaS ``access_denied`` raises :class:`DeviceFlowDenied`."""
        state = make_state(interval=0)
        poller = DeviceFlowPoller(state)

        async def mock_request(device_code: str) -> dict:
            return {"error": "access_denied"}

        with pytest.raises(DeviceFlowDenied):
            await poller.poll(mock_request)

    async def test_expired_token(self) -> None:
        """SaaS ``expired_token`` raises :class:`DeviceFlowExpired`."""
        state = make_state(interval=0)
        poller = DeviceFlowPoller(state)

        async def mock_request(device_code: str) -> dict:
            return {"error": "expired_token"}

        with pytest.raises(DeviceFlowExpired):
            await poller.poll(mock_request)

    async def test_unknown_error_raises_denied(self) -> None:
        """An unknown error code is surfaced as :class:`DeviceFlowDenied`."""
        state = make_state(interval=0)
        poller = DeviceFlowPoller(state)

        async def mock_request(device_code: str) -> dict:
            return {"error": "wrench_in_the_works", "error_description": "boom"}

        with pytest.raises(DeviceFlowDenied, match="boom"):
            await poller.poll(mock_request)

    async def test_local_expiry(self) -> None:
        """Poller raises :class:`DeviceFlowExpired` before the first poll.

        When the :class:`DeviceFlowState` has already expired (expires_in=0)
        the loop must raise on the opening local expiry check rather than
        calling the token endpoint even once.
        """
        state = make_state(expires_in=0, interval=0)
        # Tiny pause to guarantee `now > expires_at`.
        await asyncio.sleep(0.01)
        poller = DeviceFlowPoller(state)

        async def mock_request(device_code: str) -> dict:
            raise AssertionError("token_request must not be called on expired state")

        with pytest.raises(DeviceFlowExpired):
            await poller.poll(mock_request)

    async def test_interval_capped_at_10(self) -> None:
        """SaaS-sent intervals above 10 seconds are clamped (FR-018).

        The poller MUST cap its polling interval at 10 seconds no matter what
        SaaS sends in the ``/oauth/device`` response. We monkeypatch
        :func:`asyncio.sleep` so the test runs instantly while still asserting
        on the requested sleep duration.
        """
        state = DeviceFlowState.from_oauth_response(
            {
                "device_code": "dc",
                "user_code": "ABCD",
                "verification_uri": "https://saas.test/device",
                "expires_in": 900,
                "interval": 30,  # SaaS asks for 30s, poller must cap to 10s.
            }
        )
        poller = DeviceFlowPoller(state)

        sleep_durations: list[float] = []
        orig_sleep = asyncio.sleep

        async def tracking_sleep(duration: float) -> None:
            sleep_durations.append(duration)
            await orig_sleep(0)

        call_count = 0

        async def mock_request(device_code: str) -> dict:
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                return {
                    "access_token": "at",
                    "refresh_token": "rt",
                    "expires_in": 3600,
                    "scope": "",
                    "session_id": "s",
                }
            return {"error": "authorization_pending"}

        with unittest.mock.patch(
            "specify_cli.auth.device_flow.poller.asyncio.sleep",
            side_effect=tracking_sleep,
        ):
            await poller.poll(mock_request)

        assert sleep_durations, "poller should have slept at least once"
        assert all(d <= 10 for d in sleep_durations), f"All sleeps must be <=10s, got {sleep_durations}"

    async def test_slow_down_bumps_interval_but_caps(self) -> None:
        """``slow_down`` bumps the interval 5s but still caps at 10."""
        state = DeviceFlowState.from_oauth_response(
            {
                "device_code": "dc",
                "user_code": "ABCD",
                "verification_uri": "https://saas.test/device",
                "expires_in": 900,
                "interval": 6,  # +5 would go to 11; must clamp to 10.
            }
        )
        poller = DeviceFlowPoller(state)

        sleep_durations: list[float] = []
        orig_sleep = asyncio.sleep

        async def tracking_sleep(duration: float) -> None:
            sleep_durations.append(duration)
            await orig_sleep(0)

        call_count = 0

        async def mock_request(device_code: str) -> dict:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {"error": "slow_down"}
            return {
                "access_token": "at",
                "refresh_token": "rt",
                "expires_in": 3600,
                "scope": "",
                "session_id": "s",
            }

        with unittest.mock.patch(
            "specify_cli.auth.device_flow.poller.asyncio.sleep",
            side_effect=tracking_sleep,
        ):
            await poller.poll(mock_request)

        # First sleep = initial interval (6), second sleep = bumped and
        # capped (10). Both must be <= 10.
        assert sleep_durations == [6, 10]

    async def test_network_error_retries(self) -> None:
        """A :class:`NetworkError` is caught and the loop continues."""
        from specify_cli.auth.errors import NetworkError

        state = make_state(interval=0)
        poller = DeviceFlowPoller(state)
        call_count = 0

        async def mock_request(device_code: str) -> dict:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise NetworkError("connection refused")
            return {
                "access_token": "at",
                "refresh_token": "rt",
                "expires_in": 3600,
                "scope": "",
                "session_id": "s",
            }

        result = await poller.poll(mock_request)
        assert result["access_token"] == "at"
        assert state.poll_count == 2
