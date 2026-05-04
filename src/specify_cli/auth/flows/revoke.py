"""RevokeFlow — RFC 7009 token revocation for spec-kitty auth logout."""
from __future__ import annotations

import logging
from enum import StrEnum

import httpx

from ..config import get_saas_base_url
from ..session import StoredSession

log = logging.getLogger(__name__)

_HTTP_TIMEOUT_SECONDS = 10.0


class RevokeOutcome(StrEnum):
    REVOKED = "revoked"
    """Server confirmed revocation: 200 + {"revoked": true}."""

    SERVER_FAILURE = "server_failure"
    """Server returned 4xx/5xx or unexpected body. NOT revoked."""

    NETWORK_ERROR = "network_error"
    """Transport-level failure (DNS, connect, timeout)."""

    NO_REFRESH_TOKEN = "no_refresh_token"
    """Session has no refresh token; revocation not attempted."""


class RevokeFlow:
    """RFC 7009-compliant token revocation."""

    async def revoke(self, session: StoredSession) -> RevokeOutcome:
        """POST /oauth/revoke with the session's refresh token.

        Never raises. Returns RevokeOutcome so the caller can produce
        accurate output without re-implementing status logic.
        """
        if not session.refresh_token:
            return RevokeOutcome.NO_REFRESH_TOKEN

        saas_url = get_saas_base_url()
        url = f"{saas_url}/oauth/revoke"
        data = {
            "token": session.refresh_token,
            "token_type_hint": "refresh_token",
        }

        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT_SECONDS) as client:
                response = await client.post(url, data=data)
        except httpx.RequestError as exc:
            log.warning("Revoke network error: %s", type(exc).__name__)
            return RevokeOutcome.NETWORK_ERROR
        except Exception as exc:  # noqa: BLE001 - revoke must never block local logout cleanup
            log.warning("Revoke unexpected error: %s", type(exc).__name__)
            return RevokeOutcome.SERVER_FAILURE

        if response.status_code == 200:
            try:
                body = response.json()
                if body.get("revoked") is True:
                    return RevokeOutcome.REVOKED
            except ValueError:
                pass
            # 200 but unexpected body
            log.warning("Revoke 200 but unexpected body shape")
            return RevokeOutcome.SERVER_FAILURE

        log.warning("Revoke HTTP %d", response.status_code)
        return RevokeOutcome.SERVER_FAILURE


__all__ = ["RevokeFlow", "RevokeOutcome"]
