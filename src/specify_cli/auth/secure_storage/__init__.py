"""Pluggable secure storage backends for the spec-kitty auth subsystem.

Public entry point: :class:`SecureStorage`. Use
``SecureStorage.from_environment()`` to obtain the best backend available on
the current platform.

On Windows, :class:`KeychainStorage` is **never** imported at runtime.
``keyring`` is not a Windows dependency (see ``pyproject.toml``).
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from .abstract import SecureStorage
from .file_fallback import EncryptedFileStorage
from .windows_storage import WindowsFileStorage

if TYPE_CHECKING:
    from .keychain import KeychainStorage  # noqa: F401 — mypy coverage on all platforms

if sys.platform != "win32":
    # Runtime import only on non-Windows platforms.
    from .keychain import KeychainStorage  # noqa: F401
    __all__ = ["SecureStorage", "EncryptedFileStorage", "WindowsFileStorage", "KeychainStorage"]
else:
    __all__ = ["SecureStorage", "EncryptedFileStorage", "WindowsFileStorage"]
