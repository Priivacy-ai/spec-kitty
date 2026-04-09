"""Sync configuration management"""
from pathlib import Path
from typing import Any

import toml

from specify_cli.core.atomic import atomic_write

from .queue import DEFAULT_MAX_QUEUE_SIZE


class SyncConfig:
    """Manage sync configuration"""

    def __init__(self) -> None:
        self.config_dir = Path.home() / '.spec-kitty'
        self.config_file = self.config_dir / 'config.toml'

    def _load(self) -> dict[str, Any]:
        """Load config.toml, returning empty dict when missing or invalid."""
        if not self.config_file.exists():
            return {}
        try:
            return toml.load(self.config_file)
        except (toml.TomlDecodeError, OSError):
            return {}

    def _save(self, config: dict[str, Any]) -> None:
        """Write config dict back to config.toml atomically."""
        content = toml.dumps(config)
        atomic_write(self.config_file, content, mkdir=True)

    def get_server_url(self) -> str:
        """Get server URL from config"""
        config = self._load()
        url = config.get('sync', {}).get('server_url', 'https://spec-kitty-dev.fly.dev')
        return str(url)

    def set_server_url(self, url: str) -> None:
        """Set server URL in config"""
        config = self._load()
        if 'sync' not in config:
            config['sync'] = {}
        config['sync']['server_url'] = url
        self._save(config)

    def get_max_queue_size(self) -> int:
        """Get maximum offline queue size from config.

        Config key: [sync] max_queue_size = <int>
        Default: 100,000
        """
        config = self._load()
        try:
            value = config.get("sync", {}).get("max_queue_size")
            if value is not None:
                return int(value)
        except (TypeError, ValueError):
            pass
        return DEFAULT_MAX_QUEUE_SIZE

    def set_max_queue_size(self, size: int) -> None:
        """Set maximum offline queue size in config."""
        config = self._load()
        if "sync" not in config:
            config["sync"] = {}
        config["sync"]["max_queue_size"] = size
        self._save(config)
        print(f"Max queue size set to: {size:,}")
