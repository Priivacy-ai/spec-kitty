"""Sync configuration management"""

import os
import sys
from enum import StrEnum
from pathlib import Path
from typing import Any

import toml

from specify_cli.core.atomic import atomic_write

from .queue import DEFAULT_MAX_QUEUE_SIZE


class BackgroundDaemonPolicy(StrEnum):
    """Policy controlling how the background sync daemon is started."""

    AUTO = "auto"
    MANUAL = "manual"


_BACKGROUND_DAEMON_VALUES: dict[str, BackgroundDaemonPolicy] = {
    "auto": BackgroundDaemonPolicy.AUTO,
    "manual": BackgroundDaemonPolicy.MANUAL,
}


class SyncConfig:
    """Manage sync configuration"""

    def __init__(self) -> None:
        self.config_dir = Path.home() / ".spec-kitty"
        self.config_file = self.config_dir / "config.toml"

    def _load(self) -> dict[str, Any]:
        """Load config.toml, returning empty dict when missing or invalid."""
        if not self.config_file.exists():
            return {}
        try:
            data: dict[str, Any] = toml.load(self.config_file)
            return data
        except (toml.TomlDecodeError, OSError):
            return {}

    def _save(self, config: dict[str, Any]) -> None:
        """Write config dict back to config.toml atomically."""
        content = toml.dumps(config)
        atomic_write(self.config_file, content, mkdir=True)

    def get_server_url(self) -> str:
        """Resolve the sync server URL.

        Honors decision D-5 (no hardcoded SaaS domain — see
        ``specify_cli.auth.config``): ``SPEC_KITTY_SAAS_URL`` is the source of
        truth and takes precedence over config, so auth and sync can never
        resolve different targets (#2146). Falls back to the ``[sync]
        server_url`` config key, then to the D-5 env resolver — which raises a
        clear error when nothing is configured — rather than a hardcoded (and
        now unreachable) default domain that fails silently.
        """
        env_url = os.environ.get("SPEC_KITTY_SAAS_URL", "").strip()
        if env_url:
            return env_url.rstrip("/")
        config = self._load()
        url = config.get("sync", {}).get("server_url")
        if url:
            return str(url).rstrip("/")
        # D-5: no hardcoded SaaS domain. Defer to the auth resolver, which
        # raises ConfigurationError when SPEC_KITTY_SAAS_URL is unset.
        from specify_cli.auth.config import get_saas_base_url

        return str(get_saas_base_url())

    def set_server_url(self, url: str) -> None:
        """Set server URL in config"""
        config = self._load()
        if "sync" not in config:
            config["sync"] = {}
        config["sync"]["server_url"] = url
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

    def get_background_daemon(self) -> BackgroundDaemonPolicy:
        """Get background daemon policy from config.

        Config key: [sync] background_daemon = "auto" | "manual"
        Default: BackgroundDaemonPolicy.AUTO (when key or [sync] table is absent)
        """
        config = self._load()
        raw = config.get("sync", {}).get("background_daemon")

        if raw is None:
            return BackgroundDaemonPolicy.AUTO

        if not isinstance(raw, str):
            print(
                f"[sync].background_daemon has a non-string value {raw!r}; defaulting to 'auto'",
                file=sys.stderr,
            )
            return BackgroundDaemonPolicy.AUTO

        stripped = raw.strip()

        if stripped == "":
            raise ValueError("[sync].background_daemon must be 'auto' or 'manual', not an empty string")

        folded = stripped.casefold()
        policy = _BACKGROUND_DAEMON_VALUES.get(folded)
        if policy is None:
            print(
                f"[sync].background_daemon value {raw!r} is unknown; defaulting to 'auto'",
                file=sys.stderr,
            )
            return BackgroundDaemonPolicy.AUTO

        return policy

    def set_background_daemon(self, policy: BackgroundDaemonPolicy) -> None:
        """Set background daemon policy in config."""
        config = self._load()
        if "sync" not in config:
            config["sync"] = {}
        config["sync"]["background_daemon"] = policy.value
        self._save(config)

    def get_repository_sync_enabled(self, repo_slug: str) -> bool | None:
        """Return the remembered default sync preference for a repository.

        Preferences are stored under:

            [sync.repo_defaults."<repo-slug>"]
            enabled = true | false

        Returns ``None`` when no preference has been recorded.
        """
        config = self._load()
        repo_defaults = config.get("sync", {}).get("repo_defaults", {})
        if not isinstance(repo_defaults, dict):
            return None
        entry = repo_defaults.get(repo_slug)
        if not isinstance(entry, dict):
            return None
        enabled = entry.get("enabled")
        if isinstance(enabled, bool):
            return enabled
        return None

    def set_repository_sync_enabled(self, repo_slug: str, enabled: bool) -> None:
        """Persist the default sync preference for future checkouts of a repo."""
        config = self._load()
        if "sync" not in config:
            config["sync"] = {}
        repo_defaults = config["sync"].setdefault("repo_defaults", {})
        if not isinstance(repo_defaults, dict):
            repo_defaults = {}
            config["sync"]["repo_defaults"] = repo_defaults
        repo_defaults[repo_slug] = {"enabled": bool(enabled)}
        self._save(config)

    def get_checkout_sync_enabled(self, repo_root: Path) -> bool | None:
        """Return the remembered sync preference for one local checkout path."""
        config = self._load()
        checkout_overrides = config.get("sync", {}).get("checkout_overrides", {})
        if not isinstance(checkout_overrides, dict):
            return None
        entry = checkout_overrides.get(str(repo_root.resolve()))
        if not isinstance(entry, dict):
            return None
        enabled = entry.get("enabled")
        if isinstance(enabled, bool):
            return enabled
        return None

    def set_checkout_sync_enabled(self, repo_root: Path, enabled: bool) -> None:
        """Persist the sync preference for one local checkout path only."""
        config = self._load()
        if "sync" not in config:
            config["sync"] = {}
        checkout_overrides = config["sync"].setdefault("checkout_overrides", {})
        if not isinstance(checkout_overrides, dict):
            checkout_overrides = {}
            config["sync"]["checkout_overrides"] = checkout_overrides
        checkout_overrides[str(repo_root.resolve())] = {"enabled": bool(enabled)}
        self._save(config)
