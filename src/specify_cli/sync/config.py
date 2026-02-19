"""Sync configuration management"""
from pathlib import Path
import toml


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
        self.config_dir.mkdir(exist_ok=True)

        config = {}
        if self.config_file.exists():
            config = toml.load(self.config_file)

        if 'sync' not in config:
            config['sync'] = {}

        config['sync']['server_url'] = url

        with open(self.config_file, 'w') as f:
            toml.dump(config, f)

        print(f"✅ Server URL set to: {url}")
