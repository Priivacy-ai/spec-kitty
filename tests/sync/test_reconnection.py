"""Tests for WebSocket client reconnection with exponential backoff"""
import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from specify_cli.sync.client import WebSocketClient, ConnectionStatus


class TestReconnectionConfiguration:
    """Test reconnection configuration constants"""

    def test_max_reconnect_attempts_is_10(self):
        """Test max reconnect attempts is set to 10"""
        assert WebSocketClient.MAX_RECONNECT_ATTEMPTS == 10

    def test_base_delay_is_500ms(self):
        """Test base delay is 500ms (0.5 seconds)"""
        assert WebSocketClient.BASE_DELAY_SECONDS == 0.5

    def test_max_delay_is_30_seconds(self):
        """Test max delay cap is 30 seconds"""
        assert WebSocketClient.MAX_DELAY_SECONDS == 30.0

    def test_jitter_range_is_1_second(self):
        """Test jitter range is +/- 1 second"""
        assert WebSocketClient.JITTER_RANGE == 1.0


class TestExponentialBackoffFormula:
    """Test the exponential backoff delay calculation"""

    def test_delay_attempt_0(self):
        """Test delay for attempt 0: 500ms * 2^0 = 500ms"""
        client = WebSocketClient("ws://localhost", "token")
        delay = client.get_reconnect_delay(0)
        assert delay == 0.5

    def test_delay_attempt_1(self):
        """Test delay for attempt 1: 500ms * 2^1 = 1s"""
        client = WebSocketClient("ws://localhost", "token")
        delay = client.get_reconnect_delay(1)
        assert delay == 1.0

    def test_delay_attempt_2(self):
        """Test delay for attempt 2: 500ms * 2^2 = 2s"""
        client = WebSocketClient("ws://localhost", "token")
        delay = client.get_reconnect_delay(2)
        assert delay == 2.0

    def test_delay_attempt_5(self):
        """Test delay for attempt 5: 500ms * 2^5 = 16s"""
        client = WebSocketClient("ws://localhost", "token")
        delay = client.get_reconnect_delay(5)
        assert delay == 16.0

    def test_delay_capped_at_30_seconds(self):
        """Test delay is capped at 30 seconds for high attempt numbers"""
        client = WebSocketClient("ws://localhost", "token")
        # 500ms * 2^7 = 64s, should be capped at 30s
        delay = client.get_reconnect_delay(7)
        assert delay == 30.0

    def test_delay_still_capped_at_higher_attempts(self):
        """Test delay remains capped for very high attempt numbers"""
        client = WebSocketClient("ws://localhost", "token")
        delay = client.get_reconnect_delay(10)
        assert delay == 30.0


class TestReconnectionAttemptCounter:
    """Test reconnection attempt tracking"""

    def test_initial_attempt_count_is_zero(self):
        """Test client starts with zero reconnect attempts"""
        client = WebSocketClient("ws://localhost", "token")
        assert client.reconnect_attempts == 0

    def test_reset_reconnect_attempts(self):
        """Test resetting reconnect attempt counter"""
        client = WebSocketClient("ws://localhost", "token")
        client.reconnect_attempts = 5
        client.reset_reconnect_attempts()
        assert client.reconnect_attempts == 0


class TestReconnectionStatus:
    """Test status changes during reconnection"""

    def test_initial_status_is_offline(self):
        """Test client starts in offline status"""
        client = WebSocketClient("ws://localhost", "token")
        assert client.status == ConnectionStatus.OFFLINE

    def test_is_in_batch_mode_false_initially(self):
        """Test is_in_batch_mode returns False initially"""
        client = WebSocketClient("ws://localhost", "token")
        assert client.is_in_batch_mode() is False

    def test_is_in_batch_mode_true_when_batch_mode(self):
        """Test is_in_batch_mode returns True when in batch mode"""
        client = WebSocketClient("ws://localhost", "token")
        client.status = ConnectionStatus.BATCH_MODE
        assert client.is_in_batch_mode() is True


class TestReconnectMethod:
    """Test the reconnect() method behavior"""

    @pytest.mark.asyncio
    async def test_reconnect_max_attempts_switches_to_batch_mode(self):
        """Test reconnect switches to batch mode after max attempts"""
        client = WebSocketClient("ws://localhost", "token")

        # Mock connect to always fail
        with patch.object(client, 'connect', side_effect=Exception("Connection failed")):
            with patch('specify_cli.sync.client.asyncio.sleep', new_callable=AsyncMock):
                result = await client.reconnect()

        assert result is False
        assert client.status == ConnectionStatus.BATCH_MODE
        assert client.is_in_batch_mode() is True
        assert client.reconnect_attempts == WebSocketClient.MAX_RECONNECT_ATTEMPTS

    @pytest.mark.asyncio
    async def test_reconnect_success_resets_attempts(self):
        """Test successful reconnection resets attempt counter"""
        client = WebSocketClient("ws://localhost", "token")
        client.reconnect_attempts = 3

        # Mock connect to succeed
        with patch.object(client, 'connect', new_callable=AsyncMock):
            with patch('specify_cli.sync.client.asyncio.sleep', new_callable=AsyncMock):
                result = await client.reconnect()

        assert result is True
        assert client.reconnect_attempts == 0

    @pytest.mark.asyncio
    async def test_reconnect_returns_true_on_success(self):
        """Test reconnect returns True when connection succeeds"""
        client = WebSocketClient("ws://localhost", "token")

        with patch.object(client, 'connect', new_callable=AsyncMock):
            with patch('specify_cli.sync.client.asyncio.sleep', new_callable=AsyncMock):
                result = await client.reconnect()

        assert result is True

    @pytest.mark.asyncio
    async def test_reconnect_stops_after_success(self):
        """Test reconnect stops trying after successful connection"""
        client = WebSocketClient("ws://localhost", "token")
        connect_calls = 0

        async def mock_connect():
            nonlocal connect_calls
            connect_calls += 1

        with patch.object(client, 'connect', side_effect=mock_connect):
            with patch('specify_cli.sync.client.asyncio.sleep', new_callable=AsyncMock):
                await client.reconnect()

        assert connect_calls == 1

    @pytest.mark.asyncio
    async def test_reconnect_increments_attempts_on_failure(self):
        """Test each failed attempt increments the counter"""
        client = WebSocketClient("ws://localhost", "token")
        attempts_seen = []

        async def track_attempts():
            attempts_seen.append(client.reconnect_attempts)
            raise Exception("Connection failed")

        with patch.object(client, 'connect', side_effect=track_attempts):
            with patch('specify_cli.sync.client.asyncio.sleep', new_callable=AsyncMock):
                await client.reconnect()

        # Should have attempted 10 times (0-9)
        assert len(attempts_seen) == 10
        assert attempts_seen == list(range(10))

    @pytest.mark.asyncio
    async def test_reconnect_calls_sleep_with_exponential_delays(self):
        """Test reconnect sleeps between attempts with exponential backoff"""
        client = WebSocketClient("ws://localhost", "token")
        sleep_calls = []

        async def mock_sleep(delay):
            sleep_calls.append(delay)

        with patch.object(client, 'connect', side_effect=Exception("Connection failed")):
            with patch('specify_cli.sync.client.asyncio.sleep', side_effect=mock_sleep):
                with patch('specify_cli.sync.client.random.uniform', return_value=0):
                    await client.reconnect()

        # Should have 10 sleep calls
        assert len(sleep_calls) == 10
        # Verify exponential pattern (with max cap)
        expected = [0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 30.0, 30.0, 30.0, 30.0]
        assert sleep_calls == expected


class TestJitterBehavior:
    """Test jitter application in backoff delays"""

    @pytest.mark.asyncio
    async def test_jitter_applied_to_delay(self):
        """Test that jitter is applied to the calculated delay"""
        client = WebSocketClient("ws://localhost", "token")
        delays = []

        async def capture_delay(delay):
            delays.append(delay)

        # Succeed on first attempt after capturing delay
        connect_count = [0]
        async def succeed_on_second():
            connect_count[0] += 1
            if connect_count[0] == 1:
                raise Exception("fail first time")
            # Succeed on second attempt

        with patch.object(client, 'connect', side_effect=succeed_on_second):
            with patch('specify_cli.sync.client.asyncio.sleep', side_effect=capture_delay):
                with patch('specify_cli.sync.client.random.uniform', return_value=0.5):
                    await client.reconnect()

        # First delay should be 0.5 (base) + 0.5 (jitter) = 1.0
        assert len(delays) >= 1
        assert delays[0] == 1.0

    @pytest.mark.asyncio
    async def test_negative_delay_clamped_to_zero(self):
        """Test that delay is clamped to 0 if jitter makes it negative"""
        client = WebSocketClient("ws://localhost", "token")
        delays = []

        async def capture_delay(delay):
            delays.append(delay)

        # Succeed on first attempt after capturing delay
        connect_count = [0]
        async def succeed_on_second():
            connect_count[0] += 1
            if connect_count[0] == 1:
                raise Exception("fail first time")

        with patch.object(client, 'connect', side_effect=succeed_on_second):
            with patch('specify_cli.sync.client.asyncio.sleep', side_effect=capture_delay):
                # Large negative jitter that would make delay negative
                with patch('specify_cli.sync.client.random.uniform', return_value=-1.0):
                    await client.reconnect()

        # First delay: max(0, 0.5 - 1.0) = max(0, -0.5) = 0
        assert len(delays) >= 1
        assert delays[0] == 0


class _FakeWebSocket:
    """Minimal async websocket stub for lifecycle tests."""

    async def recv(self):
        return '{"type":"snapshot","work_packages":[]}'

    async def close(self):
        return None

    async def send(self, _msg):
        return None

    def __aiter__(self):
        return self

    async def __anext__(self):
        await asyncio.sleep(60)
        raise StopAsyncIteration


class TestClientLifecycle:
    """Tests for connect/disconnect task lifecycle hygiene."""

    @pytest.mark.asyncio
    async def test_disconnect_cancels_listener_task(self):
        """disconnect() should cancel the background listener task."""
        client = WebSocketClient("https://example.test", "token")

        async def fake_connect(*_args, **_kwargs):
            return _FakeWebSocket()

        with patch("specify_cli.sync.client.websockets.connect", side_effect=fake_connect):
            await client.connect()
            assert client._listen_task is not None
            assert not client._listen_task.done()

            await client.disconnect()
            await asyncio.sleep(0)

            assert client._listen_task is None
            leaked_listeners = [
                t for t in asyncio.all_tasks()
                if t is not asyncio.current_task()
                and not t.done()
                and getattr(t.get_coro(), "__qualname__", "") == "WebSocketClient._listen"
            ]
            assert leaked_listeners == []
