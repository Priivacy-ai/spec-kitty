"""Windows-native secure storage backend.

Uses the encrypted file-backed store (AES-256-GCM) rooted at
``%LOCALAPPDATA%\\spec-kitty\\auth\\`` (resolved via
``specify_cli.paths.get_runtime_root().auth_dir``).

Does NOT depend on ``keyring`` or Windows Credential Manager.
"""

from __future__ import annotations

from pathlib import Path

from .file_fallback import EncryptedFileStorage


class WindowsFileStorage(EncryptedFileStorage):
    """Windows-native secure storage.

    Uses the encrypted file-backed store at ``%LOCALAPPDATA%\\spec-kitty\\auth\\``.
    Does NOT depend on keyring or Windows Credential Manager.
    """

    def __init__(self, store_path: Path | None = None) -> None:
        if store_path is None:
            from specify_cli.paths import get_runtime_root  # noqa: PLC0415

            store_path = get_runtime_root().auth_dir
        super().__init__(store_path=store_path)
