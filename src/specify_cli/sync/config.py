"""Sync configuration management"""
from pathlib import Path
from typing import Any

import toml  # type: ignore[import-untyped]

DEFAULT_SERVER_URL = "https://spec-kitty-dev.fly.dev"


class SyncConfig:
    """Manage sync configuration"""

    def __init__(self) -> None:
        self.config_dir = Path.home() / ".spec-kitty"
        self.config_file = self.config_dir / "config.toml"

    def get_server_url(self) -> str:
        """Get server URL from config"""
        if not self.config_file.exists():
            return DEFAULT_SERVER_URL

        config: dict[str, Any] = toml.load(self.config_file)
        sync_section = config.get("sync")
        if isinstance(sync_section, dict):
            server_url = sync_section.get("server_url")
            if isinstance(server_url, str):
                return server_url
        return DEFAULT_SERVER_URL

    def set_server_url(self, url: str) -> None:
        """Set server URL in config"""
        self.config_dir.mkdir(exist_ok=True)

        config: dict[str, Any] = {}
        if self.config_file.exists():
            config = toml.load(self.config_file)

        sync_section = config.get("sync")
        if not isinstance(sync_section, dict):
            sync_section = {}
            config["sync"] = sync_section

        sync_section["server_url"] = url

        with open(self.config_file, "w", encoding="utf-8") as f:
            toml.dump(config, f)

        print(f"✅ Server URL set to: {url}")
