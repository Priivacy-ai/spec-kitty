"""Integration test: token-refresh log dedup (FR-029, NFR-007, T034).

Asserts that ``AuthenticatedClient`` emits at most one user-facing
token-refresh failure line per command invocation, even when many
authenticated requests trigger refresh failures in the same process.
"""

from __future__ import annotations

from typing import Any

import pytest

from specify_cli.auth.transport import (
    AuthRefreshFailed,
    _emit_user_facing_failure_once,
    _user_facing_failure_was_emitted,
    reset_user_facing_dedup,
)


@pytest.fixture(autouse=True)
def _reset_dedup() -> None:
    """Each test starts with a fresh dedup window."""
    reset_user_facing_dedup()
    yield
    reset_user_facing_dedup()


class TestTokenRefreshDedup:
    """FR-029 / NFR-007: ≤1 user-facing token-refresh failure line."""

    def test_first_failure_emits_once(self, capsys: pytest.CaptureFixture[str]) -> None:
        _emit_user_facing_failure_once("Authentication expired. Run `spec-kitty auth login`.")
        captured = capsys.readouterr()
        assert "Authentication expired" in captured.err
        assert _user_facing_failure_was_emitted() is True

    def test_subsequent_failures_dedup(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Five refresh failures produce exactly one user-facing line."""
        for _ in range(5):
            _emit_user_facing_failure_once("Authentication expired. Run `spec-kitty auth login`.")
        captured = capsys.readouterr()

        # Exactly one occurrence on stderr.
        occurrences = captured.err.count("Authentication expired")
        assert occurrences == 1, f"Expected 1 user-facing line, got {occurrences}"

    def test_reset_restores_emit(self, capsys: pytest.CaptureFixture[str]) -> None:
        _emit_user_facing_failure_once("first")
        _emit_user_facing_failure_once("second-suppressed")
        reset_user_facing_dedup()
        _emit_user_facing_failure_once("third-after-reset")
        captured = capsys.readouterr()

        assert "first" in captured.err
        assert "second-suppressed" not in captured.err
        assert "third-after-reset" in captured.err

    def test_authenticated_client_emits_once_across_many_requests(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Five authenticated requests with always-failing refresh → 1 line.

        Drives the full ``AuthenticatedClient`` code path with fakes:

        * ``_fetch_access_token_sync`` always returns a token, so we
          enter the request path;
        * the request transport returns a 401 response;
        * ``_force_refresh_sync`` always raises :class:`AuthRefreshFailed`.

        Each of the five calls raises :class:`AuthRefreshFailed`, but
        only the first prints the user-facing line.
        """
        from specify_cli.auth import transport as transport_mod

        monkeypatch.setattr(
            transport_mod,
            "_fetch_access_token_sync",
            lambda: "fake-token",
        )

        def _always_401(method: str, url: str, **kwargs: Any) -> Any:  # noqa: ARG001
            class _FakeResp:
                status_code = 401

                def close(self) -> None:
                    return None

            return _FakeResp()

        monkeypatch.setattr(
            transport_mod,
            "request_with_fallback_sync",
            _always_401,
        )

        def _refresh_always_fails() -> None:
            raise AuthRefreshFailed(
                "synthetic refresh failure",
                error_code="refresh_token_invalid",
            )

        monkeypatch.setattr(
            transport_mod,
            "_force_refresh_sync",
            _refresh_always_fails,
        )

        client = transport_mod.AuthenticatedClient()

        raised = 0
        for _ in range(5):
            try:
                client.request("GET", "https://example.test/whatever")
            except AuthRefreshFailed:
                raised += 1
        assert raised == 5, "All five attempts should have raised AuthRefreshFailed"

        captured = capsys.readouterr()
        occurrences = captured.err.count("Authentication expired")
        assert occurrences == 1, f"Expected exactly one user-facing token-refresh line, got {occurrences}\nstderr was:\n{captured.err}"
