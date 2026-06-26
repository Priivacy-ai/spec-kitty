"""Windows alias for the canonical encrypted session-file backend."""

from __future__ import annotations

from pathlib import Path

from specify_cli.paths import get_runtime_root

from .file_fallback import EncryptedFileStorage


class WindowsFileStorage(EncryptedFileStorage):
    """Windows wrapper for the canonical encrypted ``auth`` session store.

    The default store directory resolves through
    :func:`specify_cli.paths.get_runtime_root` (decision
    DM-01KW1KDHVGWZ0QERDMV1CRJ15S): the platformdirs LocalAppData base on
    Windows, or ``$SPEC_KITTY_HOME/auth`` when that environment variable is set.
    This replaces the previous hardcoded ``~/.spec-kitty/auth`` so Windows
    consumers resolve under the unified runtime root and honor
    ``SPEC_KITTY_HOME``.
    """

    def __init__(self, store_path: Path | None = None) -> None:
        if store_path is None:
            store_path = get_runtime_root().auth_dir
        super().__init__(store_path=store_path)
