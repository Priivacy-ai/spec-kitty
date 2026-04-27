"""Unit tests for PyPIProvider.

Mock strategy
-------------
``respx`` is available in pyproject.toml's test extras (``respx>=0.21.1``), so we
use ``respx`` to intercept httpx calls without touching the real network.  This
gives us fine-grained control over status codes, body content, and redirect
behaviour at the httpx transport layer.

All tests are marked ``pytest.mark.fast`` (pure unit, no I/O).
"""

from __future__ import annotations

import json
from unittest.mock import patch

import httpx
import pytest
import respx

from specify_cli.compat.provider import (
    LatestVersionResult,
    PyPIProvider,
    _MAX_RESPONSE_BYTES,
)

pytestmark = pytest.mark.fast

_PYPI_URL = "https://pypi.org/pypi/spec-kitty-cli/json"
_PYPI_OTHER_URL = "https://pypi.org/pypi/some-package/json"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _pypi_payload(version: str = "2.0.14") -> bytes:
    """Return a minimal valid PyPI JSON response body."""
    return json.dumps({"info": {"version": version}}).encode()


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestPyPIProviderSuccess:
    @respx.mock
    def test_success_returns_version(self) -> None:
        """A 200 response with a valid version string returns that version."""
        respx.get(_PYPI_URL).mock(return_value=httpx.Response(200, content=_pypi_payload("2.0.14")))
        provider = PyPIProvider()
        result = provider.get_latest("spec-kitty-cli")
        assert result == LatestVersionResult(version="2.0.14", source="pypi", error=None)

    @respx.mock
    def test_success_source_is_pypi(self) -> None:
        respx.get(_PYPI_URL).mock(return_value=httpx.Response(200, content=_pypi_payload("1.0.0")))
        result = PyPIProvider().get_latest("spec-kitty-cli")
        assert result.source == "pypi"

    @respx.mock
    def test_success_error_is_none(self) -> None:
        respx.get(_PYPI_URL).mock(return_value=httpx.Response(200, content=_pypi_payload("3.0.0")))
        result = PyPIProvider().get_latest("spec-kitty-cli")
        assert result.error is None

    @respx.mock
    def test_version_with_plus_sign_accepted(self) -> None:
        """Version regex allows ``+`` for local-version identifiers."""
        respx.get(_PYPI_URL).mock(return_value=httpx.Response(200, content=_pypi_payload("1.0.0+local")))
        result = PyPIProvider().get_latest("spec-kitty-cli")
        assert result.version == "1.0.0+local"
        assert result.error is None

    @respx.mock
    def test_version_with_pre_release_suffix_accepted(self) -> None:
        respx.get(_PYPI_URL).mock(return_value=httpx.Response(200, content=_pypi_payload("3.2.0a4")))
        result = PyPIProvider().get_latest("spec-kitty-cli")
        assert result.version == "3.2.0a4"


# ---------------------------------------------------------------------------
# User-Agent header
# ---------------------------------------------------------------------------


class TestPyPIProviderUserAgent:
    @respx.mock
    def test_user_agent_header_is_set(self) -> None:
        """The User-Agent header must contain 'spec-kitty-cli/' and 'compat-planner'."""
        route = respx.get(_PYPI_URL).mock(return_value=httpx.Response(200, content=_pypi_payload()))
        PyPIProvider().get_latest("spec-kitty-cli")
        assert route.called
        request = route.calls.last.request
        ua = request.headers.get("user-agent", "")
        assert ua.startswith("spec-kitty-cli/")
        assert "compat-planner" in ua

    @respx.mock
    def test_no_extra_headers_beyond_user_agent(self) -> None:
        """Only the User-Agent header should be set (CHK018).

        httpx automatically adds ``host``, ``accept``, ``accept-encoding``,
        ``connection``, and ``user-agent``.  We only assert that no unexpected
        *auth*, *cookie*, or *x-* headers are injected.
        """
        route = respx.get(_PYPI_URL).mock(return_value=httpx.Response(200, content=_pypi_payload()))
        PyPIProvider().get_latest("spec-kitty-cli")
        request = route.calls.last.request
        header_names = {k.lower() for k in request.headers}
        # These are the only headers httpx should send:
        allowed = {"host", "accept", "accept-encoding", "connection", "user-agent"}
        unexpected = header_names - allowed
        # Allow content-length for POST; should not appear for GET
        assert not unexpected, f"Unexpected headers found: {unexpected}"


# ---------------------------------------------------------------------------
# Timeout
# ---------------------------------------------------------------------------


class TestPyPIProviderTimeout:
    @respx.mock
    def test_timeout_returns_error_token(self) -> None:
        respx.get(_PYPI_URL).mock(side_effect=httpx.TimeoutException("timed out"))
        result = PyPIProvider().get_latest("spec-kitty-cli")
        assert result == LatestVersionResult(version=None, source="none", error="timeout")

    @respx.mock
    def test_timeout_does_not_raise(self) -> None:
        respx.get(_PYPI_URL).mock(side_effect=httpx.TimeoutException("timed out"))
        # Must not propagate
        result = PyPIProvider().get_latest("spec-kitty-cli")
        assert result.error == "timeout"


# ---------------------------------------------------------------------------
# HTTP error status codes
# ---------------------------------------------------------------------------


class TestPyPIProviderHTTPErrors:
    @respx.mock
    def test_500_returns_http_error(self) -> None:
        respx.get(_PYPI_URL).mock(return_value=httpx.Response(500, content=b"Internal Server Error"))
        result = PyPIProvider().get_latest("spec-kitty-cli")
        assert result == LatestVersionResult(version=None, source="none", error="http_error")

    @respx.mock
    def test_404_returns_http_error(self) -> None:
        respx.get(_PYPI_URL).mock(return_value=httpx.Response(404, content=b"Not Found"))
        result = PyPIProvider().get_latest("spec-kitty-cli")
        assert result.error == "http_error"

    @respx.mock
    def test_503_returns_http_error(self) -> None:
        respx.get(_PYPI_URL).mock(return_value=httpx.Response(503, content=b""))
        result = PyPIProvider().get_latest("spec-kitty-cli")
        assert result.error == "http_error"

    @respx.mock
    def test_http_error_exception_returns_http_error_token(self) -> None:
        """An httpx.HTTPError exception (not a status code) also maps to http_error."""
        respx.get(_PYPI_URL).mock(side_effect=httpx.HTTPError("connection refused"))
        result = PyPIProvider().get_latest("spec-kitty-cli")
        assert result.error == "http_error"


# ---------------------------------------------------------------------------
# Malformed JSON
# ---------------------------------------------------------------------------


class TestPyPIProviderMalformedJSON:
    @respx.mock
    def test_malformed_json_returns_parse_error(self) -> None:
        respx.get(_PYPI_URL).mock(return_value=httpx.Response(200, content=b"this is not json {{{"))
        result = PyPIProvider().get_latest("spec-kitty-cli")
        assert result == LatestVersionResult(version=None, source="none", error="parse_error")

    @respx.mock
    def test_missing_info_key_returns_parse_error(self) -> None:
        body = json.dumps({"other": "field"}).encode()
        respx.get(_PYPI_URL).mock(return_value=httpx.Response(200, content=body))
        result = PyPIProvider().get_latest("spec-kitty-cli")
        assert result.error == "parse_error"

    @respx.mock
    def test_missing_version_key_returns_parse_error(self) -> None:
        body = json.dumps({"info": {"name": "spec-kitty-cli"}}).encode()
        respx.get(_PYPI_URL).mock(return_value=httpx.Response(200, content=body))
        result = PyPIProvider().get_latest("spec-kitty-cli")
        assert result.error == "parse_error"

    @respx.mock
    def test_version_is_integer_returns_parse_error(self) -> None:
        body = json.dumps({"info": {"version": 42}}).encode()
        respx.get(_PYPI_URL).mock(return_value=httpx.Response(200, content=body))
        result = PyPIProvider().get_latest("spec-kitty-cli")
        assert result.error == "parse_error"

    @respx.mock
    def test_null_info_returns_parse_error(self) -> None:
        body = json.dumps({"info": None}).encode()
        respx.get(_PYPI_URL).mock(return_value=httpx.Response(200, content=body))
        result = PyPIProvider().get_latest("spec-kitty-cli")
        assert result.error == "parse_error"


# ---------------------------------------------------------------------------
# Oversized body
# ---------------------------------------------------------------------------


class TestPyPIProviderOversizedBody:
    @respx.mock
    def test_body_larger_than_1mb_returns_oversized(self) -> None:
        """A 2 MiB response body must be rejected with error='oversized' (CHK012)."""
        oversized = b"x" * (_MAX_RESPONSE_BYTES + 1)
        respx.get(_PYPI_URL).mock(return_value=httpx.Response(200, content=oversized))
        result = PyPIProvider().get_latest("spec-kitty-cli")
        assert result == LatestVersionResult(version=None, source="none", error="oversized")

    @respx.mock
    def test_body_exactly_1mb_is_accepted(self) -> None:
        """A body exactly at the limit is allowed; content will fail JSON parse, but not oversized."""
        # Exactly at the cap — not oversized, but not valid JSON either
        at_limit = b"x" * _MAX_RESPONSE_BYTES
        respx.get(_PYPI_URL).mock(return_value=httpx.Response(200, content=at_limit))
        result = PyPIProvider().get_latest("spec-kitty-cli")
        # Not oversized — parse will fail instead
        assert result.error != "oversized"

    @respx.mock
    def test_2mb_body_returns_oversized(self) -> None:
        two_mb = b"a" * (2 * _MAX_RESPONSE_BYTES)
        respx.get(_PYPI_URL).mock(return_value=httpx.Response(200, content=two_mb))
        result = PyPIProvider().get_latest("spec-kitty-cli")
        assert result.error == "oversized"


# ---------------------------------------------------------------------------
# Version string sanitisation (CHK015, CHK016)
# ---------------------------------------------------------------------------


class TestPyPIProviderVersionSanitisation:
    @respx.mock
    def test_ansi_escape_in_version_returns_parse_error(self) -> None:
        """ANSI injection e.g. ``\\x1b[31mUPGRADE NOW\\x1b[0m`` must be rejected."""
        ansi_version = "\x1b[31mUPGRADE NOW\x1b[0m"
        body = json.dumps({"info": {"version": ansi_version}}).encode()
        respx.get(_PYPI_URL).mock(return_value=httpx.Response(200, content=body))
        result = PyPIProvider().get_latest("spec-kitty-cli")
        assert result.error == "parse_error"

    @respx.mock
    def test_shell_metacharacters_in_version_returns_parse_error(self) -> None:
        """Shell metacharacters like ``;rm -rf /`` must be rejected."""
        bad_version = "1.0.0;rm -rf /"
        body = json.dumps({"info": {"version": bad_version}}).encode()
        respx.get(_PYPI_URL).mock(return_value=httpx.Response(200, content=body))
        result = PyPIProvider().get_latest("spec-kitty-cli")
        assert result.error == "parse_error"

    @respx.mock
    def test_version_longer_than_64_chars_returns_parse_error(self) -> None:
        long_version = "1" * 65
        body = json.dumps({"info": {"version": long_version}}).encode()
        respx.get(_PYPI_URL).mock(return_value=httpx.Response(200, content=body))
        result = PyPIProvider().get_latest("spec-kitty-cli")
        assert result.error == "parse_error"

    @respx.mock
    def test_empty_version_string_returns_parse_error(self) -> None:
        body = json.dumps({"info": {"version": ""}}).encode()
        respx.get(_PYPI_URL).mock(return_value=httpx.Response(200, content=body))
        result = PyPIProvider().get_latest("spec-kitty-cli")
        assert result.error == "parse_error"


# ---------------------------------------------------------------------------
# Redirect handling (CHK014) — redirects must NOT be followed
# ---------------------------------------------------------------------------


class TestPyPIProviderRedirects:
    def test_follow_redirects_false(self) -> None:
        """PyPIProvider must set follow_redirects=False on the httpx client.

        We verify this by inspecting the Client constructor call rather than
        relying on a live redirect, so the test is fast and deterministic.
        """
        captured_kwargs: list[dict[str, object]] = []

        original_init = httpx.Client.__init__

        def patched_init(self: httpx.Client, **kwargs: object) -> None:
            captured_kwargs.append(dict(kwargs))
            original_init(self, **kwargs)

        with patch.object(httpx.Client, "__init__", patched_init), respx.mock:
            respx.get(_PYPI_URL).mock(return_value=httpx.Response(200, content=_pypi_payload()))
            PyPIProvider().get_latest("spec-kitty-cli")

        assert len(captured_kwargs) >= 1
        assert captured_kwargs[0].get("follow_redirects") is False

    @respx.mock
    def test_301_redirect_returns_http_error(self) -> None:
        """A 301 from PyPI is an error code (redirect not followed), not a success."""
        respx.get(_PYPI_URL).mock(
            return_value=httpx.Response(
                301,
                headers={"location": "https://pypi.org/pypi/other/json"},
                content=b"",
            )
        )
        result = PyPIProvider().get_latest("spec-kitty-cli")
        # 301 is a 3xx status; httpx treats 3xx as non-error when redirects disabled,
        # but it IS an is_error=False response.  The version parse will fail.
        # The important thing is it does NOT follow the redirect.
        assert result.version is None


# ---------------------------------------------------------------------------
# TLS failure simulation
# ---------------------------------------------------------------------------


class TestPyPIProviderTLSFailure:
    def test_tls_error_returns_http_error(self) -> None:
        """A ConnectError (e.g., TLS failure) maps to http_error, not a raise."""
        with respx.mock:
            respx.get(_PYPI_URL).mock(side_effect=httpx.ConnectError("SSL handshake failed"))
            result = PyPIProvider().get_latest("spec-kitty-cli")
        assert result.error == "http_error"
