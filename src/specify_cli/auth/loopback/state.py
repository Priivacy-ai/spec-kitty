"""PKCEState dataclass: transient state for one in-flight login attempt.

Each Authorization Code + PKCE flow instance carries:

- a CSRF nonce (``state``) echoed back by the SaaS in the callback URL
- a PKCE ``code_verifier`` held only in CLI memory
- the derived ``code_challenge`` sent in the authorization request
- creation/expiry timestamps (5-minute TTL)

This object is intentionally in-memory only: it lives inside a single
``spec-kitty auth login`` invocation and is never persisted. The 5-minute
TTL matches the loopback server's ``wait_for_callback`` timeout so stale
state never becomes valid again after a missed callback.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, UTC

_STATE_TTL = timedelta(minutes=5)


@dataclass
class PKCEState:
    """In-flight Authorization Code + PKCE state for one login attempt."""

    state: str
    """CSRF nonce echoed back by the SaaS in the redirect URL."""

    code_verifier: str
    """Random 43-char secret held only in CLI memory."""

    code_challenge: str
    """SHA256(verifier) base64url encoded without padding (S256)."""

    code_challenge_method: str
    """Always ``"S256"`` for this implementation (RFC 7636 §4.3)."""

    created_at: datetime
    """UTC timestamp when the state was created."""

    expires_at: datetime
    """UTC timestamp when the state becomes invalid (created_at + 5 min)."""

    @classmethod
    def create(cls, verifier: str, challenge: str) -> PKCEState:
        """Build a fresh :class:`PKCEState` with a new CSRF nonce and TTL.

        Args:
            verifier: PKCE code_verifier from :func:`pkce.generate_code_verifier`.
            challenge: PKCE code_challenge derived from ``verifier``.

        Returns:
            A new :class:`PKCEState` with ``expires_at = created_at + 5 minutes``.
        """
        now = datetime.now(UTC)
        return cls(
            state=secrets.token_urlsafe(32),
            code_verifier=verifier,
            code_challenge=challenge,
            code_challenge_method="S256",
            created_at=now,
            expires_at=now + _STATE_TTL,
        )

    def is_expired(self) -> bool:
        """Return ``True`` iff the current UTC time is at or past ``expires_at``."""
        return datetime.now(UTC) >= self.expires_at
