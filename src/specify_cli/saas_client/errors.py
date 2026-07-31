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


class SaasConsentError(SaasClientError):
    """Raised when the project owning the data has not consented to hosted sync.

    #3030 FR-030. Deliberately a :class:`SaasClientError` subclass, because that
    is the type this package's callers already handle: the widen prereq probe
    suppresses it (so a non-consenting project simply never sees the ``[w]iden``
    option, which is the correct outcome), the interview helpers report it as a
    non-fatal warning, and ``spec-kitty decision widen`` — the one call an
    operator makes deliberately — surfaces the message and exits non-zero. A new
    unrelated exception type would instead escape those handlers and turn a
    confidentiality refusal into a crash in an interview.

    ``status_code`` stays ``None``: nothing was sent, so there is no HTTP status
    to report, and reporting one would invite the reader to debug the network.
    """

    def __init__(self, reason: str) -> None:
        super().__init__(
            f"Refusing to call Spec Kitty SaaS: {reason}",
            status_code=None,
        )
        self.reason = reason
