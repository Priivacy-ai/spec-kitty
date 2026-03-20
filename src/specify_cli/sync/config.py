"""Sync configuration management"""
from pathlib import Path
import toml

from specify_cli.core.atomic import atomic_write


class SyncConfig:
    """Manage sync configuration"""

    def __init__(self):
        self.config_dir = Path.home() / '.spec-kitty'
        self.config_file = self.config_dir / 'config.toml'

    def get_server_url(self) -> str:
        """Get server URL from config"""
        if not self.config_file.exists():
            return "https://spec-kitty-dev.fly.dev"  # Default

        config = toml.load(self.config_file)
        return config.get('sync', {}).get('server_url', 'https://spec-kitty-dev.fly.dev')

    def set_server_url(self, url: str):
        """Set server URL in config"""
        config = {}
        if self.config_file.exists():
            config = toml.load(self.config_file)

        if 'sync' not in config:
            config['sync'] = {}

        config['sync']['server_url'] = url

        content = toml.dumps(config)
        atomic_write(self.config_file, content, mkdir=True)

        print(f"✅ Server URL set to: {url}")
