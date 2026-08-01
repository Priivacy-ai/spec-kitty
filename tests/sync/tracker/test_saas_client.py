"""Comprehensive tests for SaaSTrackerClient.

Covers auth injection, synchronous endpoints, async endpoints (push/run with
202 polling), polling timeout, 401 refresh, 429 rate-limit, error envelope
parsing, and network errors.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest

from specify_cli.tracker.saas_client import (
    SaaSTrackerClient,
    SaaSTrackerClientError,
    _parse_error_envelope,
)

pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _advancing_clock(step: float = 1.0) -> Iterator[float]:
    """An unbounded, monotonically increasing clock for ``time.monotonic`` mocks.

    The polling tests used to hand ``mock_monotonic.side_effect`` an exact list
    sized to the number of clock reads ``_poll_operation`` made — ``[0.0, 1.0,
    3.0]`` and friends. That coupled each test to the *total* number of
    ``time.monotonic()`` calls anywhere in the process, because
    ``@patch("...saas_client.time.monotonic")`` patches the attribute on the
    shared :mod:`time` module rather than a module-local alias.

    #3030 FR-029 made that coupling bite: ``_request`` now resolves per-project
    consent, and the consent chain reads the clock too
    (``sync/git_metadata.py``). The lists ran out, the resolver raised
    ``StopIteration``, and the gate did exactly what it should — refused, because
    consent could not be determined. The tests were red for a fixture reason
    dressed up as a confidentiality verdict.

    None of these tests assert on clock *values* or on how often the clock is
    read; they assert on poll results and on ``sleep`` delays, which are driven by
    the backoff schedule and ``secrets.randbelow``. So an unbounded advancing
    clock preserves every assertion while removing a brittleness that would have
    caught the next person to add any clock read on this path.

    ``test_timeout_after_5_minutes`` deliberately keeps its exact ``[0.0,
    301.0]``: there the second value *is* the assertion, and it never reaches
    ``_request``.
    """
    current = 0.0
    while True:
        yield current
        current += step


def _make_response(
    status_code: int = 200,
    json_body: dict[str, Any] | None = None,
    *,
    text: str = "",
) -> httpx.Response:
    """Build a fake httpx.Response with the given status and JSON body."""
    resp = httpx.Response(
        status_code=status_code,
        request=httpx.Request("GET", "https://example.com"),
    )
    if json_body is not None:
        import json as _json

        resp._content = _json.dumps(json_body).encode()
        resp.headers["content-type"] = "application/json"
    elif text:
        resp._content = text.encode()
    else:
        resp._content = b""
    return resp


@pytest.fixture()
def mock_credential_store() -> MagicMock:
    store = MagicMock()
    store.get_access_token.return_value = "test-access-token"
    store.get_team_slug.return_value = "team-acme"
    store.get_refresh_token.return_value = "test-refresh-token"
    return store


@pytest.fixture()
def mock_sync_config() -> MagicMock:
    config = MagicMock()
    config.get_server_url.return_value = "https://saas.example.com"
    # The client now resolves its base URL via the canonical target authority
    # (#2146), not the raw get_server_url accessor.
    config.resolve_runtime_target.return_value.resolved_server_url = (
        "https://saas.example.com"
    )
    return config


@pytest.fixture()
def client(mock_credential_store: MagicMock, mock_sync_config: MagicMock) -> SaaSTrackerClient:
    return SaaSTrackerClient(
        credential_store=mock_credential_store,
        sync_config=mock_sync_config,
        timeout=5.0,
    )


# ---------------------------------------------------------------------------
# Error envelope parsing
# ---------------------------------------------------------------------------


class TestParseErrorEnvelope:
    def test_parses_full_envelope(self) -> None:
        resp = _make_response(
            422,
            {
                "error_code": "missing_installation",
                "category": "identity_resolution",
                "message": "No installation found",
                "retryable": False,
                "user_action_required": True,
                "source": "jira",
                "retry_after_seconds": None,
            },
        )
        envelope = _parse_error_envelope(resp)
        assert envelope["error_code"] == "missing_installation"
        assert envelope["category"] == "identity_resolution"
        assert envelope["message"] == "No installation found"
        assert envelope["retryable"] is False
        assert envelope["user_action_required"] is True
        assert envelope["source"] == "jira"

    def test_handles_malformed_json(self) -> None:
        resp = _make_response(500, text="Internal Server Error")
        envelope = _parse_error_envelope(resp)
        assert envelope["error_code"] is None
        assert envelope["category"] is None
        assert envelope["message"] == "HTTP 500"

    def test_handles_partial_envelope(self) -> None:
        resp = _make_response(400, {"message": "Bad request"})
        envelope = _parse_error_envelope(resp)
        assert envelope["message"] == "Bad request"
        assert envelope["error_code"] is None
        assert envelope["category"] is None
        assert envelope["retryable"] is False


# ---------------------------------------------------------------------------
# Auth injection
# ---------------------------------------------------------------------------


class TestAuthInjection:
    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_bearer_token_on_every_request(
        self, mock_httpx_client_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        mock_http = MagicMock()
        mock_httpx_client_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_httpx_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.request.return_value = _make_response(200, {"ok": True})

        client._request("GET", "/api/v1/tracker/status")

        _, kwargs = mock_http.request.call_args
        assert kwargs["headers"]["Authorization"] == "Bearer test-access-token"

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_team_slug_header_on_every_request(
        self, mock_httpx_client_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        mock_http = MagicMock()
        mock_httpx_client_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_httpx_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.request.return_value = _make_response(200, {"ok": True})

        client._request("GET", "/api/v1/tracker/status")

        _, kwargs = mock_http.request.call_args
        assert kwargs["headers"]["X-Team-Slug"] == "team-acme"

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_token_fetched_at_request_time(
        self, mock_httpx_client_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        """Token is read on each call, not cached at construction."""
        mock_http = MagicMock()
        mock_httpx_client_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_httpx_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.request.return_value = _make_response(200, {"ok": True})

        # First request uses the original token
        client._request("GET", "/api/v1/tracker/status")

        # Change token
        client._credential_store.get_access_token.return_value = "new-token"  # type: ignore[attr-defined]
        client._request("GET", "/api/v1/tracker/status")

        calls = mock_http.request.call_args_list
        assert calls[0][1]["headers"]["Authorization"] == "Bearer test-access-token"
        assert calls[1][1]["headers"]["Authorization"] == "Bearer new-token"

    def test_no_token_raises(self, client: SaaSTrackerClient) -> None:
        client._credential_store.get_access_token.return_value = None  # type: ignore[attr-defined]
        with pytest.raises(SaaSTrackerClientError, match="spec-kitty auth login") as exc_info:
            client._request("GET", "/api/v1/tracker/status")
        assert exc_info.value.error_code == "unauthenticated"
        assert exc_info.value.status_code == 401
        assert exc_info.value.details["category"] == "unauthenticated"
        assert exc_info.value.user_action_required is True

    def test_missing_team_slug_raises_error(self, client: SaaSTrackerClient) -> None:
        """FR-015: Missing X-Team-Slug must raise, not silently omit the header."""
        client._credential_store.get_team_slug.return_value = None  # type: ignore[attr-defined]
        with pytest.raises(SaaSTrackerClientError, match="spec-kitty auth login") as exc_info:
            client._request("GET", "/api/v1/tracker/status")
        assert exc_info.value.error_code == "unauthenticated"
        assert exc_info.value.details["category"] == "unauthenticated"

    def test_empty_team_slug_raises_error(self, client: SaaSTrackerClient) -> None:
        """FR-015: Empty string team slug must also raise."""
        client._credential_store.get_team_slug.return_value = ""  # type: ignore[attr-defined]
        with pytest.raises(SaaSTrackerClientError, match="spec-kitty auth login") as exc_info:
            client._request("GET", "/api/v1/tracker/status")
        assert exc_info.value.error_code == "unauthenticated"
        assert exc_info.value.details["category"] == "unauthenticated"


# ---------------------------------------------------------------------------
# Synchronous endpoints
# ---------------------------------------------------------------------------


class TestPull:
    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_pull_200(self, mock_cls: MagicMock, client: SaaSTrackerClient) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.request.return_value = _make_response(
            200, {"items": [{"id": "1"}], "cursor": "abc"}
        )

        result = client.pull("jira", "proj-1")

        assert result == {"items": [{"id": "1"}], "cursor": "abc"}
        _, kwargs = mock_http.request.call_args
        assert kwargs["json"]["provider"] == "jira"
        assert kwargs["json"]["project_slug"] == "proj-1"
        assert kwargs["json"]["limit"] == 100

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_pull_with_cursor_and_filters(
        self, mock_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.request.return_value = _make_response(200, {"items": []})

        client.pull(
            "jira", "proj-1", limit=50, cursor="xyz", filters={"status": ["open"]}
        )

        _, kwargs = mock_http.request.call_args
        assert kwargs["json"]["cursor"] == "xyz"
        assert kwargs["json"]["filters"] == {"status": ["open"]}
        assert kwargs["json"]["limit"] == 50

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_pull_uses_post_method(
        self, mock_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.request.return_value = _make_response(200, {"items": []})

        client.pull("jira", "proj-1")

        args, kwargs = mock_http.request.call_args
        assert args[0] == "POST"
        assert args[1].endswith("/api/v1/tracker/pull/")


class TestStatus:
    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_status_200(self, mock_cls: MagicMock, client: SaaSTrackerClient) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.request.return_value = _make_response(
            200, {"connected": True, "last_sync": "2026-01-01"}
        )

        result = client.status("jira", "proj-1")

        assert result["connected"] is True
        args, kwargs = mock_http.request.call_args
        assert args[0] == "GET"
        assert args[1].endswith("/api/v1/tracker/status/")
        assert kwargs["params"]["provider"] == "jira"
        assert kwargs["params"]["project_slug"] == "proj-1"


class TestMappings:
    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_mappings_200(self, mock_cls: MagicMock, client: SaaSTrackerClient) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.request.return_value = _make_response(
            200, {"fields": [{"src": "title", "dst": "summary"}]}
        )

        result = client.mappings("jira", "proj-1")

        assert result["fields"][0]["src"] == "title"
        args, kwargs = mock_http.request.call_args
        assert args[0] == "GET"
        assert args[1].endswith("/api/v1/tracker/mappings/")


# ---------------------------------------------------------------------------
# Async-capable endpoints (push, run)
# ---------------------------------------------------------------------------


class TestPush:
    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_push_200_sync(self, mock_cls: MagicMock, client: SaaSTrackerClient) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.request.return_value = _make_response(
            200, {"pushed": 3, "errors": []}
        )

        result = client.push("jira", "proj-1", [{"title": "Bug"}])
        assert result == {"pushed": 3, "errors": []}

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_push_has_idempotency_key(
        self, mock_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.request.return_value = _make_response(200, {"pushed": 1})

        client.push("jira", "proj-1", [])

        _, kwargs = mock_http.request.call_args
        idem_key = kwargs["headers"]["Idempotency-Key"]
        # Must be a valid UUID
        uuid.UUID(idem_key)

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_push_custom_idempotency_key(
        self, mock_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.request.return_value = _make_response(200, {"pushed": 1})

        client.push("jira", "proj-1", [], idempotency_key="my-key-123")

        _, kwargs = mock_http.request.call_args
        assert kwargs["headers"]["Idempotency-Key"] == "my-key-123"

    @patch("specify_cli.tracker.saas_client.time.sleep")
    @patch("specify_cli.tracker.saas_client.time.monotonic")
    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_push_202_polls_until_completed(
        self,
        mock_cls: MagicMock,
        mock_monotonic: MagicMock,
        mock_sleep: MagicMock,
        client: SaaSTrackerClient,
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        # First call: POST push -> 202
        # Second call: GET operation -> pending
        # Third call: GET operation -> completed
        mock_http.request.side_effect = [
            _make_response(202, {"operation_id": "op-1"}),
            _make_response(200, {"status": "pending"}),
            _make_response(200, {"status": "completed", "result": {"pushed": 2}}),
        ]
        mock_monotonic.side_effect = _advancing_clock()

        result = client.push("jira", "proj-1", [{"title": "X"}])
        assert result == {"pushed": 2}

    @patch("specify_cli.tracker.saas_client.time.sleep")
    @patch("specify_cli.tracker.saas_client.time.monotonic")
    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_push_202_polls_failed_raises(
        self,
        mock_cls: MagicMock,
        mock_monotonic: MagicMock,
        mock_sleep: MagicMock,
        client: SaaSTrackerClient,
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_http.request.side_effect = [
            _make_response(202, {"operation_id": "op-2"}),
            _make_response(200, {"status": "failed", "error": "Provider rejected"}),
        ]
        mock_monotonic.side_effect = _advancing_clock()

        with pytest.raises(SaaSTrackerClientError, match="Provider rejected"):
            client.push("jira", "proj-1", [{"title": "Y"}])


class TestRun:
    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_run_200_sync(self, mock_cls: MagicMock, client: SaaSTrackerClient) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.request.return_value = _make_response(
            200, {"pulled": 5, "pushed": 3}
        )

        result = client.run("jira", "proj-1")
        assert result == {"pulled": 5, "pushed": 3}
        _, kwargs = mock_http.request.call_args
        assert kwargs["json"]["pull_first"] is True
        assert kwargs["json"]["limit"] == 100

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_run_has_idempotency_key(
        self, mock_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.request.return_value = _make_response(200, {"ok": True})

        client.run("jira", "proj-1")

        _, kwargs = mock_http.request.call_args
        idem_key = kwargs["headers"]["Idempotency-Key"]
        uuid.UUID(idem_key)  # validates UUID format

    @patch("specify_cli.tracker.saas_client.time.sleep")
    @patch("specify_cli.tracker.saas_client.time.monotonic")
    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_run_202_polls_until_completed(
        self,
        mock_cls: MagicMock,
        mock_monotonic: MagicMock,
        mock_sleep: MagicMock,
        client: SaaSTrackerClient,
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_http.request.side_effect = [
            _make_response(202, {"operation_id": "op-run"}),
            _make_response(200, {"status": "running"}),
            _make_response(200, {"status": "completed", "result": {"synced": 10}}),
        ]
        mock_monotonic.side_effect = _advancing_clock()

        result = client.run("jira", "proj-1")
        assert result == {"synced": 10}


# ---------------------------------------------------------------------------
# Polling
# ---------------------------------------------------------------------------


class TestPolling:
    @patch(
        "specify_cli.tracker.saas_client.secrets.randbelow",
        side_effect=[1000, 2000, 3000],  # basis points → jitter factors 0.9, 1.0, 1.1
    )
    @patch("specify_cli.tracker.saas_client.time.sleep")
    @patch("specify_cli.tracker.saas_client.time.monotonic")
    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_exponential_backoff_intervals(
        self,
        mock_cls: MagicMock,
        mock_monotonic: MagicMock,
        mock_sleep: MagicMock,
        mock_randbelow: MagicMock,
        client: SaaSTrackerClient,
    ) -> None:
        """#3115 (WP06, FR-005, round 2): the real site, on the real evidence.

        Round 1 pinned this attribution to
        ``TestRetryBehaviors::test_429_respects_retry_after`` on the strength
        of the issue body's own wording. That test has never been observed
        red. **This** is one of the two tests CI actually failed on --
        verified against the live log (`fast-tests-sync`, job `91126025663`,
        run `30621215287`, base `bb2020fea9`, `-n auto --dist loadfile`,
        Python 3.12.3, `pytest-xdist==3.8.0`), fetched directly with
        ``gh api repos/Priivacy-ai/spec-kitty/actions/jobs/91126025663/logs``
        because the copy a prior review session had wasn't recoverable in this
        one -- refetching by job id reproduced it line-for-line (the
        `AssertionError` at the log's line 451 and its short-summary repeat
        at line 1083 both landed at those exact line numbers again).

        **The real failure text, quoted verbatim** --
        ``[gw5] linux -- Python 3.12.3 /home/runner/_work/spec-kitty/spec-kitty/.venv/bin/python3``::

            tests/sync/tracker/test_saas_client.py:534: in test_exponential_backoff_intervals
                assert len(sleep_calls) == 3
            E   assert 71 == 3
            E    +  where 71 = len([call(0.9),
             call(2.0),
             call(4.4),
             call(0.001),
             call(0.002),
             call(0.004),
             call(0.008),
             call(0.016),
             call(0.032)...),
             call(0.05), ... (62 total)])

        **The second real victim, outside this WP's write scope** (flagged in
        the WP06 report, not edited here) --
        ``tests/sync/tracker/test_saas_client_origin.py:261:
        TestSearchIssues.test_429_retries_then_raises``, ``[gw2]``::

            mock_sleep.assert_called_once_with(2.0)
            /usr/lib/python3.12/unittest/mock.py:955: in assert_called_once_with
                raise AssertionError(msg)
            E   AssertionError: Expected 'sleep' to be called once. Called 556 times.

        Session tally: ``5 failed, 2103 passed, 11 skipped, 1 warning in
        98.34s (0:01:38)``.

        **The mechanism (FR-005, established, not re-derived)**:
        ``@patch("specify_cli.tracker.saas_client.time.sleep")`` patches the
        **stdlib** ``time`` module's ``sleep`` attribute -- `saas_client.py:19`
        is a bare ``import time`` -- so the mock's call recorder is
        process-wide for the patch's lifetime: it counts a ``time.sleep`` call
        from *any* live thread in the worker **process** (not worker in the
        xdist sense -- ``gw2``/``gw5`` are separate OS processes and cannot
        share a mock's state, so the two victims above were independently
        polluted, each by something alive in *its own* process). Same hazard
        :func:`_advancing_clock`'s docstring (`:32-50`) documents for
        ``time.monotonic``. Confirmed reproducible on demand (round 1): a
        deliberately-injected live thread left running past its own test moves
        this exact assertion from a clean pass to
        ``AssertionError: Expected 'sleep' to be called once. Called 400 times.``,
        399 of 400 calls attributed to the injected thread by name
        (`scripts/mutants/attribute_sleep_count_3115.py`).

        **Correction (round 2): the magnitude exclusion was unsound.** Round 1
        reasoned "no single-shot sleep or short loop can explain a 71x/556x
        tally, so it's excluded." That counts *intended* sleep duration under
        a live clock -- but the victim's patch makes ``time.sleep`` a **no-op**
        that returns instantly, so every wall-clock-**bounded** loop
        (``while time.monotonic() < deadline: ...; time.sleep(x)``) keeps
        re-checking a deadline that (mostly) isn't advancing and spins through
        its full iteration budget in the patch window, not over its intended
        wall-clock span. Measured on the mechanism proof itself: the injected
        probe intended ``400 * 0.005s = 2.0s`` of sleeping and recorded
        ``378`` calls inside a **sub-second** window. So *"the loop is too
        short to explain N calls"* is **not** a valid exclusion for any
        **iteration-bounded** loop in the sync cone -- only for genuinely
        single-shot sleeps (`daemon.py:584`, one `time.sleep(0.01)`;
        `daemon.py:757`, one `time.sleep(_RUNTIME_BACKGROUND_START_DELAY_SECONDS)`).

        **Completed `daemon.py` census (round 2).** Round 1's daemon.py
        candidate list (threads `:587`, `:767`, `:828`; sleep loops `:584`,
        `:1382`) missed two **iteration-bounded** loops, both un-excludable by
        magnitude per the correction above:
        ``_acquire_daemon_lock`` (`:1077-1090`) -- ``for _ in range(100): ...
        time.sleep(0.1)``, up to 100 calls; and
        ``_ensure_sync_daemon_running_locked`` (`:1207-1251`, loop at
        `:1240-1251`) -- iterates
        ``[0.1] * 10 + [0.25] * 40 + [0.5] * 20`` (the same shape as
        `dashboard/lifecycle.py`'s health-poll, "matching dashboard pattern"
        per its own comment), up to 70 calls. **One contended**
        ``ensure_sync_daemon_running(REMOTE_REQUIRED)`` **call can therefore
        cost up to 170 sleep calls**, and under the neutralising patch all 170
        complete instantly rather than over their intended ~20s.

        **The `0.05` / doubling fingerprint -- corrected (round 3): the
        producer is named.** Round 2 read the 556-call victim as **two**
        producers -- a doubling run and a separate flat-`0.05` tail -- and
        reported the doubling leg as an unattributed negative after a grep
        scoped to `src/` and `tests/`. **That decomposition was wrong.** A
        geometric ramp that flattens at a ceiling is **one** loop whose delay
        saturated, not two loops end-to-end, and the correct search key was
        never "a doubling backoff" but "a doubling backoff capped at
        `0.05`" -- which exists in exactly one place in any CPython process:
        **`subprocess.Popen._wait`** (`Lib/subprocess.py`, POSIX branch),
        confirmed by reading the installed interpreter's own source
        (`inspect.getsource`, this venv, Python 3.11.15; the same shape is in
        3.12's stdlib, CI's interpreter)::

            delay = 0.0005  # 500 us -> initial delay of 1 ms
            while True:
                ...
                delay = min(delay * 2, remaining, .05)
                time.sleep(delay)

        **Reproduced independently, not copied from the rejection.** A
        standalone probe with **no repo code** --
        `subprocess.Popen(["sleep", "30"])`, `.wait(timeout=0.2)` on a
        background thread, `time.sleep` patched at module scope -- gave
        `first 10: [0.001, 0.002, 0.004, 0.008, 0.016, 0.032, 0.05, 0.05,
        0.05, 0.05]` and `30169` total calls in one 0.2s window on this
        machine (a different run of the same probe recorded `220326`+ at the
        `0.05` plateau in the coordinator's environment -- the exact count is
        a function of how fast the busy loop's own bookkeeping runs against
        real wall-clock time, which is why it varies by machine and is not
        itself part of the fingerprint). CI's `556` is one such call caught
        in flight, mid-plateau: `call(2.0)` (the test's own retry-after
        sleep) + one complete six-term ramp + `549` plateau calls before the
        patch window closed.

        **Consequence: `restart.py:147` and `daemon.py:1382` are falsified as
        this fingerprint's producer.** Both emit a *flat* `0.05` with no
        preceding ramp (`_OWNER_RECORD_POLL_SECONDS` / the health-poll loop
        each call `time.sleep(0.05)` unconditionally, never
        `min(delay * 2, ..., .05)`), so neither can generate the observed
        `0.001→0.032` prefix. They remain real, iteration-bounded,
        magnitude-uncapped loops for the census purpose two paragraphs above
        (a leaked thread stuck in either would still read as N extra flat
        calls) -- they are retired specifically as candidates for *this*
        compound ramp-then-plateau shape.

        **A second, structural falsification found while chasing this one:**
        `daemon.py:1000-1032 _kill_and_cleanup`'s `wait_fn(timeout=...)`
        (reached from `stop_sync_daemon`, `:1385-1389`, and
        `_ensure_sync_daemon_running_locked`, `:1254-1255`) and
        `dashboard/lifecycle.py:600`'s `proc.wait(timeout=3.0)`
        (`_terminate_by_pid`) both call **`psutil.Process.wait`**, not
        `subprocess.Popen.wait` -- and `psutil.Process.wait` is **structurally
        invisible to `@patch("time.sleep")`**. Read from the installed
        `psutil==7.2.2`: `psutil._psposix.wait_pid_posix` declares
        ``_sleep=time.sleep`` as a **function-default parameter**, bound once
        to the real `sleep` object when `psutil` is first imported (typically
        at test-collection time, long before any test's `@patch` runs) --
        the same value-capture hazard the standing rules document for
        `from X import f` (rot mode 5), except here it is an unnamed default
        argument rather than an import statement, so a `grep` for `import
        time` finds nothing to flag. Confirmed empirically, not just read:
        `psutil.Process(real_child_pid).wait(timeout=0.2)` under
        `patch("time.sleep")` recorded **0** calls on the mock, versus
        `subprocess.Popen.wait(timeout=0.2)` on the same child recording
        thousands under the identical patch. Both `daemon.py`'s and
        `dashboard/lifecycle.py`'s daemon-teardown waits are therefore
        excluded as producers of *any* observed mock inflation, not merely
        of this one fingerprint.

        **The real, patchable `subprocess.Popen.wait(timeout=...)` sites in
        this tree** (repo-wide grep, `psutil.*wait(timeout=` extended
        alongside plain `.wait(timeout=`): none in `src/specify_cli/sync/`
        or `src/specify_cli/dashboard/` (both route through the
        psutil-shielded path above); one genuine site in `src/`,
        `review/pre_review_gate.py:390`, but `tests/sync/` does not reach it
        (`tests/sync/conftest.py:141`'s
        `_isolate_pre_review_gate_sync_toggles` only unsets two env vars by
        name -- it never imports or calls the gate module); and the
        test-owned `tests/sync/_daemon_harness.py`'s `_terminate_proc`
        (`:136-149`, real `subprocess.Popen[bytes].wait(timeout=3.0)`,
        synchronous inside `DaemonHarness.shutdown()`, not threaded), used by
        `test_daemon_cleanup_boundary.py`, `test_daemon_orphan_classification.py`,
        `test_issue_1071_singleton_reconfirmation.py`, `test_orphan_sweep.py`,
        plus direct `proc.wait(timeout=...)` calls in
        `test_owner_record_unreadable_3030.py:151`,
        `test_daemon_owner_record.py:478,788`,
        `test_sync_boundary_preflight.py:153`,
        `test_daemon_singleton_reaper_consolidation.py:635`, and
        `test_orphan_sweep.py:94,106,112`.

        **The instrument was proven before it was trusted.** `attribute_sleep_count_3115.py`
        now captures `traceback.extract_stack()` on the first 5 calls per
        `(site, thread)` and reports the modal signature (round 3 addition --
        see its module docstring). Positive control: a standalone
        `Popen.wait(timeout=0.2)` on a background thread, run through the
        mutant, was attributed **`subprocess.py:2047 in _wait`** as the modal
        stack for the polluted thread -- the instrument names a known
        producer correctly.

        **Two clean serial runs, on the proven instrument.** (1) A targeted
        291-test selection -- this file, `test_saas_client_origin.py`, and
        every `tests/sync/` file listed above as a genuine
        `subprocess.Popen.wait` call site -- ran serially under the mutant:
        `280 passed, 11 skipped in 80.93s`, `total recorded calls: 12`, all
        `MainThread`, matching only the tests' own expected sleeps (this
        test's own 3 among them). (2) The **full** `tests/sync/` cone, serial
        (no `-n`, the mutant's documented requirement): `2370 passed, 18
        skipped in 112.30s`. Neither run put any extra call on
        `specify_cli.tracker.saas_client.time.sleep` (still 12, still all
        `MainThread`) -- **but** the full-cone run *did* catch, live, two
        leaked threads (`Thread-69 (_guarded_final_sync)`,
        `Thread-70 (_guarded_final_sync)`) each calling
        `sync/batch.py:674 _sleep_before_final_sync_retry` (via
        `background.py:467 _guarded_final_sync` /
        `batch.py:648 run_final_sync_with_retries`) and landing 2 calls each
        on a **different** test's `specify_cli.sync.batch.time.sleep` patch.
        This is a live, stack-confirmed instance of WP04's inventory E24/E25
        (`background.py::BackgroundSyncService.stop`'s final-sync thread,
        `no reset seam`, `sync_thread.join(timeout=...)` then only a
        diagnostic) and issue #3130's confirmed leaks 1-2 -- proof the
        instrument catches real leaks in this exact session, on this exact
        box, when one is present, and that this particular leak class is
        real and active. It simply did not land on either FR-005 victim's
        own patch window in either run.

        **The named `adapters.py`/`events.py` lead was checked structurally**
        (budget; unchanged from round 2). `status/adapters.py:106-112`'s
        orphaned-worker chain (`events.py:282` → `:307` →
        `events.py:67`'s `ensure_sync_daemon_running(REMOTE_REQUIRED)`, the
        170-call surface from the census above) is gated behind
        `get_token_manager().is_authenticated` at `events.py:58`, and neither
        this file, `test_saas_client_origin.py`, nor `tracker/conftest.py`
        import or exercise `specify_cli.status.adapters` or
        `specify_cli.sync.events` anywhere -- not reachable from these
        tests' own call graph, and per the coordinator's round-3 direction a
        CPU-contention reproduction was **not attempted** (it would name
        *why* a thread outlives its join, not *which* construct is sleeping,
        and the construct is now named).

        **Verdict**: the producer **construct** is named and independently
        reproduced -- `subprocess.Popen._wait`'s POSIX busy-wait,
        `delay = min(delay * 2, remaining, .05)`, base `0.0005`. The two
        flat-`0.05` sites this WP previously named (`restart.py:147`,
        `daemon.py:1382`) are retired as candidates for this fingerprint; two
        further candidates (`daemon.py`'s and `dashboard/lifecycle.py`'s
        daemon-teardown waits) are excluded **structurally** (psutil shields
        them from this patch entirely, confirmed empirically). Every
        genuine `subprocess.Popen.wait` site reachable from `tests/sync/` is
        enumerated above and was run twice, serially, under an instrument
        proven correct by positive control (and which caught a different
        real leak live in the same session) -- and recorded zero pollution
        on either FR-005 victim. That is the legitimate FR-005 negative: not
        "no construct could be found" (round 2's error), but "the construct
        is named, the instrument that could see it is proven, and it still
        did not see it here." Left open for WP14 on that basis.
        """
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        # pending, pending, pending, completed
        mock_http.request.side_effect = [
            _make_response(200, {"status": "pending"}),
            _make_response(200, {"status": "pending"}),
            _make_response(200, {"status": "pending"}),
            _make_response(200, {"status": "completed", "result": {"done": True}}),
        ]
        # Provide enough time values: start, check1, check2, check3, check4
        mock_monotonic.side_effect = _advancing_clock()

        result = client._poll_operation("op-backoff")
        assert result == {"done": True}

        # Verify sleep was called with increasing delays (with jitter)
        # jitter_factor = 0.8 + (basis_points / 10000)
        # 1000 bp → 0.9, 2000 bp → 1.0, 3000 bp → 1.1
        sleep_calls = mock_sleep.call_args_list
        assert len(sleep_calls) == 3
        delays = [c.args[0] for c in sleep_calls]
        assert delays == [0.9, 2.0, 4.4]
        assert mock_randbelow.call_count == 3

    @patch("specify_cli.tracker.saas_client.time.sleep")
    @patch("specify_cli.tracker.saas_client.time.monotonic")
    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_timeout_after_5_minutes(
        self,
        mock_cls: MagicMock,
        mock_monotonic: MagicMock,
        mock_sleep: MagicMock,
        client: SaaSTrackerClient,
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        # monotonic returns 301 on first check, exceeding 300 timeout
        mock_monotonic.side_effect = [0.0, 301.0]

        with pytest.raises(SaaSTrackerClientError, match="timed out after 5 minutes"):
            client._poll_operation("op-timeout")

    @patch("specify_cli.tracker.saas_client.time.sleep")
    @patch("specify_cli.tracker.saas_client.time.monotonic")
    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_pending_then_running_then_completed(
        self,
        mock_cls: MagicMock,
        mock_monotonic: MagicMock,
        mock_sleep: MagicMock,
        client: SaaSTrackerClient,
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_http.request.side_effect = [
            _make_response(200, {"status": "pending"}),
            _make_response(200, {"status": "running"}),
            _make_response(200, {"status": "completed", "result": {"items": 5}}),
        ]
        mock_monotonic.side_effect = _advancing_clock()

        result = client._poll_operation("op-progress")
        assert result == {"items": 5}


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestRetryBehaviors:
    @patch("specify_cli.tracker.saas_client._force_refresh_sync")
    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_401_refresh_retry_success(
        self,
        mock_cls: MagicMock,
        mock_force_refresh: MagicMock,
        client: SaaSTrackerClient,
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        # First: 401, after refresh: 200
        mock_http.request.side_effect = [
            _make_response(401, {"message": "Unauthorized"}),
            _make_response(200, {"ok": True}),
        ]
        result = client._request_with_retry("GET", "/api/v1/tracker/status")
        assert result.status_code == 200
        mock_force_refresh.assert_called_once()

    @patch("specify_cli.tracker.saas_client._force_refresh_sync")
    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_401_double_failure_halts(
        self,
        mock_cls: MagicMock,
        mock_force_refresh: MagicMock,
        client: SaaSTrackerClient,
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        # 401 both times
        mock_http.request.side_effect = [
            _make_response(401, {"message": "Unauthorized"}),
            _make_response(401, {"message": "Unauthorized"}),
        ]
        with pytest.raises(SaaSTrackerClientError, match="Session expired"):
            client._request_with_retry("GET", "/api/v1/tracker/status")

    @patch("specify_cli.tracker.saas_client._force_refresh_sync")
    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_401_refresh_itself_fails(
        self,
        mock_cls: MagicMock,
        mock_force_refresh: MagicMock,
        client: SaaSTrackerClient,
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_http.request.return_value = _make_response(401, {"message": "Unauthorized"})
        mock_force_refresh.side_effect = RuntimeError("refresh failed")

        with pytest.raises(SaaSTrackerClientError, match="Session expired"):
            client._request_with_retry("GET", "/api/v1/tracker/status")

    @patch("specify_cli.tracker.saas_client.time.sleep")
    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_429_respects_retry_after(
        self,
        mock_cls: MagicMock,
        mock_sleep: MagicMock,
        client: SaaSTrackerClient,
    ) -> None:
        """#3115 (WP06, FR-005) -- corrected pointer (round 2).

        This node was the round-1 attribution site, on the strength of the
        issue body's own wording. It is **not** one of the tests CI actually
        failed on: the live CI log (`fast-tests-sync`, job 91126025663, run
        30621215287, base `bb2020fea9`) shows two different real victims --
        ``TestPolling.test_exponential_backoff_intervals`` in *this* file
        (see its docstring below, `:497` class / the test a few lines above
        this one in file order) and
        ``TestSearchIssues.test_429_retries_then_raises`` in
        `tests/sync/tracker/test_saas_client_origin.py:261` (outside this
        WP's write scope -- flagged in the WP06 report, not edited here).
        This test has never been observed red, locally or on CI. The
        stdlib-``time``-module mechanism this docstring used to describe here
        is still correct and is not re-derived -- see the real victim's
        docstring for the full attribution, the quoted failure text, and the
        round-2 corrections (magnitude exclusion, completed `daemon.py`
        census, the `0.05`/doubling fingerprint measurement).
        """
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_http.request.side_effect = [
            _make_response(429, {"message": "Rate limited", "retry_after_seconds": 3}),
            _make_response(200, {"ok": True}),
        ]

        result = client._request_with_retry("GET", "/api/v1/tracker/status")
        assert result.status_code == 200
        mock_sleep.assert_called_once_with(3.0)

    @patch("specify_cli.tracker.saas_client.time.sleep")
    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_429_defaults_to_5s_when_missing(
        self,
        mock_cls: MagicMock,
        mock_sleep: MagicMock,
        client: SaaSTrackerClient,
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_http.request.side_effect = [
            _make_response(429, {"message": "Rate limited"}),
            _make_response(200, {"ok": True}),
        ]

        client._request_with_retry("GET", "/api/v1/tracker/status")
        mock_sleep.assert_called_once_with(5.0)

    @patch("specify_cli.tracker.saas_client.time.sleep")
    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_429_double_failure_raises(
        self,
        mock_cls: MagicMock,
        mock_sleep: MagicMock,
        client: SaaSTrackerClient,
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_http.request.side_effect = [
            _make_response(429, {"message": "Rate limited", "retry_after_seconds": 1}),
            _make_response(429, {"message": "Still rate limited"}),
        ]

        with pytest.raises(SaaSTrackerClientError, match="Still rate limited"):
            client._request_with_retry("GET", "/api/v1/tracker/status")

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_4xx_error_envelope_parsed(
        self, mock_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_http.request.return_value = _make_response(
            422,
            {
                "error_code": "missing_installation",
                "category": "identity_resolution",
                "message": "Jira app not installed",
                "user_action_required": True,
            },
        )

        with pytest.raises(
            SaaSTrackerClientError, match="Jira app not installed"
        ) as exc_info:
            client._request_with_retry("GET", "/api/v1/tracker/status")
        assert "action required" in str(exc_info.value)

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_5xx_error_envelope_parsed(
        self, mock_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_http.request.return_value = _make_response(
            500, {"error_code": "internal_error", "message": "Something broke"}
        )

        with pytest.raises(SaaSTrackerClientError, match="Something broke"):
            client._request_with_retry("GET", "/api/v1/tracker/status")

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_malformed_error_response(
        self, mock_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_http.request.return_value = _make_response(500, text="Internal Server Error")

        with pytest.raises(SaaSTrackerClientError, match="HTTP 500"):
            client._request_with_retry("GET", "/api/v1/tracker/status")


class TestNetworkErrors:
    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_connect_error(
        self, mock_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_http.request.side_effect = httpx.ConnectError("Connection refused")

        with pytest.raises(SaaSTrackerClientError, match="Cannot connect"):
            client._request("GET", "/api/v1/tracker/status")

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_timeout_error(
        self, mock_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_http.request.side_effect = httpx.ReadTimeout("Read timed out")

        with pytest.raises(SaaSTrackerClientError, match="Cannot connect"):
            client._request("GET", "/api/v1/tracker/status")


# ---------------------------------------------------------------------------
# Constructor defaults
# ---------------------------------------------------------------------------


class TestConstructorDefaults:
    def test_custom_instances_used(
        self, mock_credential_store: MagicMock, mock_sync_config: MagicMock
    ) -> None:
        c = SaaSTrackerClient(
            credential_store=mock_credential_store,
            sync_config=mock_sync_config,
        )
        assert c._credential_store is mock_credential_store
        assert c._sync_config is mock_sync_config
        assert c._base_url == "https://saas.example.com"


# ---------------------------------------------------------------------------
# Regression tests for Codex review cycle 1 fixes
# ---------------------------------------------------------------------------


class TestAsyncErrorEnvelopeParsing:
    """Fix 1 (FR-017/NFR-002): Failed async operations must parse the error
    envelope dict, not dump it as a raw string."""

    @patch("specify_cli.tracker.saas_client.time.sleep")
    @patch("specify_cli.tracker.saas_client.time.monotonic")
    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_failed_operation_parses_error_envelope_dict(
        self,
        mock_cls: MagicMock,
        mock_monotonic: MagicMock,
        mock_sleep: MagicMock,
        client: SaaSTrackerClient,
    ) -> None:
        """When the 'error' field is an ErrorEnvelope dict, the raised exception
        must contain the human-readable 'message' and 'user_action_required',
        not a repr of the dict."""
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        error_envelope = {
            "error_code": "provider_auth_expired",
            "category": "auth",
            "message": "Jira OAuth token has expired",
            "user_action_required": True,
        }
        mock_http.request.side_effect = [
            _make_response(202, {"operation_id": "op-err-envelope"}),
            _make_response(200, {"status": "failed", "error": error_envelope}),
        ]
        mock_monotonic.side_effect = _advancing_clock()

        with pytest.raises(SaaSTrackerClientError) as exc_info:
            client.push("jira", "proj-1", [{"title": "Bug"}])

        error_text = str(exc_info.value)
        # Must contain the readable message
        assert "Jira OAuth token has expired" in error_text
        # user_action_required is boolean True → generic guidance appended
        assert "action required" in error_text
        # Must NOT contain raw dict syntax
        assert "{'error_code'" not in error_text
        assert "provider_auth_expired" not in error_text

    @patch("specify_cli.tracker.saas_client.time.sleep")
    @patch("specify_cli.tracker.saas_client.time.monotonic")
    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_failed_operation_with_string_error_still_works(
        self,
        mock_cls: MagicMock,
        mock_monotonic: MagicMock,
        mock_sleep: MagicMock,
        client: SaaSTrackerClient,
    ) -> None:
        """When the 'error' field is a plain string, it should still work."""
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_http.request.side_effect = [
            _make_response(202, {"operation_id": "op-str-err"}),
            _make_response(200, {"status": "failed", "error": "Something went wrong"}),
        ]
        mock_monotonic.side_effect = _advancing_clock()

        with pytest.raises(SaaSTrackerClientError, match="Something went wrong"):
            client.push("jira", "proj-1", [{"title": "Bug"}])

    @patch("specify_cli.tracker.saas_client.time.sleep")
    @patch("specify_cli.tracker.saas_client.time.monotonic")
    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_failed_operation_with_no_error_field(
        self,
        mock_cls: MagicMock,
        mock_monotonic: MagicMock,
        mock_sleep: MagicMock,
        client: SaaSTrackerClient,
    ) -> None:
        """When the 'error' field is missing, a fallback message is used."""
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_http.request.side_effect = [
            _make_response(202, {"operation_id": "op-no-err"}),
            _make_response(200, {"status": "failed"}),
        ]
        mock_monotonic.side_effect = _advancing_clock()

        with pytest.raises(SaaSTrackerClientError, match="Operation failed"):
            client.push("jira", "proj-1", [{"title": "Bug"}])


# ---------------------------------------------------------------------------
# WP03: Enriched error attributes (T013 + T014)
# ---------------------------------------------------------------------------


class TestErrorEnrichmentAttributes:
    """T013: Verify enriched SaaSTrackerClientError attributes from PRI-12 envelope."""

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_error_enrichment_preserves_error_code(
        self, mock_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        """error_code is extracted from the envelope 'error_code' field."""
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_http.request.return_value = _make_response(
            400,
            {
                "error_code": "binding_not_found",
                "message": "No binding exists for this mission",
            },
        )

        with pytest.raises(SaaSTrackerClientError) as exc_info:
            client._request_with_retry("GET", "/api/v1/tracker/status")

        assert exc_info.value.error_code == "binding_not_found"

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_error_enrichment_preserves_status_code(
        self, mock_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        """status_code is the HTTP status from the response."""
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_http.request.return_value = _make_response(
            400,
            {"error_code": "binding_not_found", "message": "Not found"},
        )

        with pytest.raises(SaaSTrackerClientError) as exc_info:
            client._request_with_retry("GET", "/api/v1/tracker/status")

        assert exc_info.value.status_code == 400

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_error_enrichment_preserves_details(
        self, mock_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        """details dict is the full parsed envelope."""
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_http.request.return_value = _make_response(
            422,
            {
                "error_code": "mapping_disabled",
                "category": "configuration",
                "message": "Mapping is disabled",
                "retryable": False,
                "user_action_required": False,
                "source": "jira",
                "retry_after_seconds": None,
            },
        )

        with pytest.raises(SaaSTrackerClientError) as exc_info:
            client._request_with_retry("GET", "/api/v1/tracker/status")

        details = exc_info.value.details
        assert isinstance(details, dict)
        assert details["error_code"] == "mapping_disabled"
        assert details["category"] == "configuration"
        assert details["source"] == "jira"

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_error_enrichment_user_action_required(
        self, mock_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        """user_action_required is True when envelope says so."""
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_http.request.return_value = _make_response(
            422,
            {
                "error_code": "missing_installation",
                "message": "App not installed",
                "user_action_required": True,
            },
        )

        with pytest.raises(SaaSTrackerClientError) as exc_info:
            client._request_with_retry("GET", "/api/v1/tracker/status")

        assert exc_info.value.user_action_required is True

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_error_enrichment_backward_compat_str(
        self, mock_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        """str(e) still returns the human-readable message."""
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_http.request.return_value = _make_response(
            400,
            {"error_code": "binding_not_found", "message": "No binding found"},
        )

        with pytest.raises(SaaSTrackerClientError) as exc_info:
            client._request_with_retry("GET", "/api/v1/tracker/status")

        assert str(exc_info.value) == "No binding found"

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_error_enrichment_missing_envelope(
        self, mock_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        """Empty/malformed body: error_code=None, status_code preserved."""
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_http.request.return_value = _make_response(
            400, text="Bad Request"
        )

        with pytest.raises(SaaSTrackerClientError) as exc_info:
            client._request_with_retry("GET", "/api/v1/tracker/status")

        assert exc_info.value.error_code is None
        assert exc_info.value.status_code == 400
        assert str(exc_info.value) == "HTTP 400"

    @patch("specify_cli.tracker.saas_client.time.sleep")
    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_429_enrichment_has_error_code_and_status(
        self,
        mock_cls: MagicMock,
        mock_sleep: MagicMock,
        client: SaaSTrackerClient,
    ) -> None:
        """Double 429 raises with error_code='rate_limited' and status_code=429."""
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_http.request.side_effect = [
            _make_response(429, {"message": "Rate limited", "retry_after_seconds": 1}),
            _make_response(429, {"message": "Still rate limited"}),
        ]

        with pytest.raises(SaaSTrackerClientError) as exc_info:
            client._request_with_retry("GET", "/api/v1/tracker/status")

        assert exc_info.value.error_code == "rate_limited"
        assert exc_info.value.status_code == 429

    @patch("specify_cli.tracker.saas_client._force_refresh_sync")
    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_401_enrichment_has_error_code_and_status(
        self,
        mock_cls: MagicMock,
        mock_force_refresh: MagicMock,
        client: SaaSTrackerClient,
    ) -> None:
        """Double 401 raises with error_code='session_expired' and status_code=401."""
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_http.request.side_effect = [
            _make_response(401, {"message": "Unauthorized"}),
            _make_response(401, {"message": "Unauthorized"}),
        ]
        with pytest.raises(SaaSTrackerClientError) as exc_info:
            client._request_with_retry("GET", "/api/v1/tracker/status")

        assert exc_info.value.error_code == "session_expired"
        assert exc_info.value.status_code == 401
        assert exc_info.value.user_action_required is True


class TestErrorEnrichmentRegression:
    """T014: Regression — existing callers constructing SaaSTrackerClientError('msg') still work."""

    def test_existing_str_pattern(self) -> None:
        """Plain string construction with no kwargs must still work."""
        err = SaaSTrackerClientError("Something failed")
        assert str(err) == "Something failed"
        assert err.error_code is None
        assert err.status_code is None
        assert err.details == {}
        assert err.user_action_required is False

    def test_isinstance_runtime_error(self) -> None:
        """SaaSTrackerClientError is still a RuntimeError subclass."""
        err = SaaSTrackerClientError("boom")
        assert isinstance(err, RuntimeError)

    def test_enriched_construction(self) -> None:
        """Full kwarg construction exposes all attributes."""
        err = SaaSTrackerClientError(
            "Binding not found",
            error_code="binding_not_found",
            status_code=404,
            details={"error_code": "binding_not_found", "source": "jira"},
            user_action_required=True,
        )
        assert str(err) == "Binding not found"
        assert err.error_code == "binding_not_found"
        assert err.status_code == 404
        assert err.details == {"error_code": "binding_not_found", "source": "jira"}
        assert err.user_action_required is True

    def test_catch_as_exception(self) -> None:
        """Can be caught as generic Exception (callers that do except Exception)."""
        with pytest.raises(Exception):
            raise SaaSTrackerClientError("test")

    def test_catch_as_runtime_error(self) -> None:
        """Can be caught as RuntimeError (existing callers)."""
        with pytest.raises(RuntimeError):
            raise SaaSTrackerClientError("test")
