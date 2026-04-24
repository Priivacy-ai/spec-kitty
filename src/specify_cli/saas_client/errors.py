"""Error hierarchy for the SaaS client.

All SaaS HTTP failures are surfaced as ``SaasClientError`` or one of its
subclasses.  Callers should catch the base class when they want to suppress
all SaaS failures (C-007 local-first), or a specific subclass when they need
to discriminate between auth, timeout, and not-found scenarios.
"""

from __future__ import annotations


class SaasClientError(Exception):
    """Base error for all SaaS client failures."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class SaasTimeoutError(SaasClientError):
    """Raised when an HTTP request to SaaS exceeds the configured timeout."""


class SaasAuthError(SaasClientError):
    """Raised on HTTP 401/403 or missing credentials."""


class SaasNotFoundError(SaasClientError):
    """Raised on HTTP 404 (decision or mission not found)."""
