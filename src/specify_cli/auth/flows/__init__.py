"""Orchestration flows for the spec-kitty auth subsystem (feature 080).

This package contains the high-level flow orchestrators that coordinate the
primitives in sibling packages (``loopback``, ``device_flow``,
``secure_storage``, ``token_manager``) to produce a :class:`StoredSession`:

- :class:`AuthorizationCodeFlow` — browser-based OAuth Authorization Code +
  PKCE flow, wired by ``cli.commands.auth login`` (WP04).
- :class:`TokenRefreshFlow` — refresh-grant flow, used by ``TokenManager``
  to renew an expired access token (WP04).
- :class:`DeviceCodeFlow` — RFC 8628 device authorization flow for
  headless environments. Lazy-imported by ``cli.commands._auth_login``
  when ``--headless`` is passed (WP05).

Downstream callers import from ``specify_cli.auth.flows`` only; the
individual modules are not considered public API.
"""

from __future__ import annotations

from .authorization_code import AuthorizationCodeFlow
from .device_code import DeviceCodeFlow
from .refresh import TokenRefreshFlow

__all__ = ["AuthorizationCodeFlow", "DeviceCodeFlow", "TokenRefreshFlow"]
