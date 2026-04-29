"""Process-wide TokenManager singleton.

Extracted from auth/__init__.py to avoid global mutable state at package import.
"""

from __future__ import annotations

import threading

from specify_cli.auth.secure_storage import SecureStorage
from specify_cli.auth.token_manager import TokenManager

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
