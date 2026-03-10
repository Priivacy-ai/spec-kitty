"""Sync configuration management"""

from pathlib import Path
from typing import Any

import toml  # type: ignore[import-untyped]


class SyncConfig:
    """Manage sync configuration"""

    def __init__(self) -> None:
        self.config_dir = Path.home() / ".spec-kitty"
        self.config_file = self.config_dir / "config.toml"

    def get_server_url(self) -> str:
        """Get server URL from config"""
        if not self.config_file.exists():
            return "https://spec-kitty-dev.fly.dev"  # Default

        config: dict[str, Any] = toml.load(self.config_file)
        url = config.get("sync", {}).get("server_url", "https://spec-kitty-dev.fly.dev")
        return str(url)

    def set_server_url(self, url: str) -> None:
        """Set server URL in config"""
        self.config_dir.mkdir(exist_ok=True)

        config: dict[str, Any] = {}
        if self.config_file.exists():
            config = toml.load(self.config_file)

        if "sync" not in config:
            config["sync"] = {}

        config["sync"]["server_url"] = url

        with open(self.config_file, "w") as f:
            toml.dump(config, f)

        print(f"✅ Server URL set to: {url}")
