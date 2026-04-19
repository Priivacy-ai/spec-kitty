"""Windows alias for the canonical encrypted session-file backend."""

from __future__ import annotations

from pathlib import Path

from .file_fallback import EncryptedFileStorage


class WindowsFileStorage(EncryptedFileStorage):
    """Windows wrapper for the shared ``~/.spec-kitty/auth`` session store."""

    def __init__(self, store_path: Path | None = None) -> None:
        if store_path is None:
            store_path = Path.home() / ".spec-kitty" / "auth"
        super().__init__(store_path=store_path)
