"""PKCE (RFC 7636) code_verifier and code_challenge generation.

This module implements the S256 PKCE method for the Authorization Code +
PKCE OAuth flow (feature 080, WP02). The verifier/challenge pair binds the
authorization request in the browser to the token exchange in the CLI, so
an attacker who intercepts the redirect URL alone cannot exchange the code.

Functions here are pure and stateless; the lifecycle wrapper lives in
``state_manager.py``.
"""

from __future__ import annotations

import base64
import hashlib
import secrets


def generate_code_verifier() -> str:
    """Return a 43-character cryptographically secure code_verifier.

    Per RFC 7636 section 4.1, the verifier must be in the
    ``[A-Z] / [a-z] / [0-9] / "-" / "." / "_" / "~"`` alphabet and between
    43 and 128 characters. ``secrets.token_urlsafe(32)`` produces 43 base64url
    characters (from 32 random bytes, ``ceil(32 * 4/3) = 43``, no padding).

    Returns:
        A 43-character URL-safe random string.
    """
    return secrets.token_urlsafe(32)


def generate_code_challenge(verifier: str) -> str:
    """Return ``base64url(SHA256(verifier))`` without padding.

    Implements the S256 code challenge method per RFC 7636 section 4.2.
    Padding is stripped because RFC 7636 requires the unpadded base64url
    form.

    Args:
        verifier: The code verifier produced by :func:`generate_code_verifier`.

    Returns:
        A base64url-encoded SHA256 digest with no trailing ``=`` characters.
    """
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def generate_pkce_pair() -> tuple[str, str]:
    """Return a ``(code_verifier, code_challenge)`` tuple.

    Convenience helper that calls :func:`generate_code_verifier` and
    :func:`generate_code_challenge` in sequence. Callers that need both
    values should use this to avoid accidental reuse of verifiers across
    login attempts.
    """
    verifier = generate_code_verifier()
    challenge = generate_code_challenge(verifier)
    return verifier, challenge
