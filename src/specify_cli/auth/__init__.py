"""Spec-kitty auth subsystem (feature 080: browser-mediated OAuth CLI auth).

Public API:

- :func:`get_token_manager` — process-wide :class:`TokenManager` factory with
  double-checked-locking lazy init. Every WP that needs a bearer token calls
  ``await get_token_manager().get_access_token()``.
- :func:`reset_token_manager` — test-only helper to drop the shared instance
  between test cases (used by ``tests/auth/conftest.py``).
- :class:`TokenManager` — re-exported for type hints and direct construction
  in unit tests.
- :class:`SecureStorage` — re-exported so callers can construct custom
  backends or use ``SecureStorage.from_environment()`` directly.
- The auth error hierarchy — re-exported so downstream code imports errors
  from ``specify_cli.auth`` instead of flow-internal modules.

This module deliberately uses a module-level ``_tm`` + ``threading.Lock``
rather than a class attribute or singleton pattern — decision from the WP01
review of the previous run, where a class-level singleton caused lifecycle
ambiguity and made testing difficult.
"""

from __future__ import annotations

import threading

from .errors import (
    AuthenticationError,
    BrowserLaunchError,
    CallbackError,
    CallbackTimeoutError,
    CallbackValidationError,
    ConfigurationError,
    DeviceFlowDenied,
    DeviceFlowError,
    DeviceFlowExpired,
    NetworkError,
    NotAuthenticatedError,
    RefreshTokenExpiredError,
    SecureStorageError,
    SessionInvalidError,
    StateExpiredError,
    StorageBackendUnavailableError,
    StorageDecryptionError,
    TokenRefreshError,
)
from .secure_storage import SecureStorage
from .token_manager import TokenManager

__all__ = [
    # Factory + test helper
    "get_token_manager",
    "reset_token_manager",
    # Core classes
    "TokenManager",
    "SecureStorage",
    # Error hierarchy
    "AuthenticationError",
    "NotAuthenticatedError",
    "ConfigurationError",
    "TokenRefreshError",
    "RefreshTokenExpiredError",
    "SessionInvalidError",
    "NetworkError",
    "CallbackError",
    "CallbackTimeoutError",
    "CallbackValidationError",
    "StateExpiredError",
    "BrowserLaunchError",
    "DeviceFlowError",
    "DeviceFlowDenied",
    "DeviceFlowExpired",
    "SecureStorageError",
    "StorageBackendUnavailableError",
    "StorageDecryptionError",
]

_tm: TokenManager | None = None
_tm_lock = threading.Lock()


def get_token_manager() -> TokenManager:
    """Return the process-wide :class:`TokenManager` instance.

    Lazy-initializes from secure storage on first call; subsequent calls
    return the same instance. Thread-safe via double-checked locking.
    """
    global _tm
    if _tm is None:
        with _tm_lock:
            if _tm is None:
                storage = SecureStorage.from_environment()
                tm = TokenManager(storage)
                tm.load_from_storage_sync()
                _tm = tm
    return _tm


def reset_token_manager() -> None:
    """Reset the global :class:`TokenManager`. For tests only.

    Used by ``tests/auth/conftest.py`` to guarantee state isolation between
    test cases.
    """
    global _tm
    with _tm_lock:
        _tm = None
