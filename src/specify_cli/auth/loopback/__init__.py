"""Loopback OAuth callback package (feature 080, WP02).

Implements the pieces the Authorization Code + PKCE flow needs on the CLI
side of the browser redirect:

- :mod:`pkce` — RFC 7636 code_verifier / code_challenge generation
- :mod:`state` — :class:`PKCEState` dataclass with 5-minute TTL
- :mod:`state_manager` — :class:`StateManager` lifecycle wrapper
- :mod:`callback_server` — localhost HTTP server (:class:`CallbackServer`)
- :mod:`callback_handler` — CSRF state validation (:class:`CallbackHandler`)
- :mod:`browser_launcher` — stdlib-``webbrowser`` :class:`BrowserLauncher`

The orchestration layer that ties these together (feature 080, WP04) imports
from this package only; individual modules are not considered public API.
"""

from __future__ import annotations

from .browser_launcher import BrowserLauncher
from .callback_handler import CallbackHandler, validate_callback_params
from .callback_server import CallbackServer
from .pkce import generate_code_challenge, generate_code_verifier, generate_pkce_pair
from .state import PKCEState
from .state_manager import StateManager

__all__ = [
    "PKCEState",
    "generate_code_verifier",
    "generate_code_challenge",
    "generate_pkce_pair",
    "CallbackServer",
    "CallbackHandler",
    "validate_callback_params",
    "StateManager",
    "BrowserLauncher",
]
