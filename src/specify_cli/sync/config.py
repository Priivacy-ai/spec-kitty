"""Sync configuration management.

Target authority (WP02, contract §1): ``get_server_url`` / ``set_server_url``
are the **config-file accessors** the canonical resolver consumes — they read
and write ``[sync].server_url`` only and never apply env precedence. Callers
that need the *live runtime target* must obtain a
:class:`~specify_cli.sync.target_authority.ResolvedSyncTarget` via
:meth:`SyncConfig.resolve_runtime_target` (which folds in ``SPEC_KITTY_SAAS_URL``
precedence and derives the queue scope) rather than treating the raw
``get_server_url`` value as the target.
"""
import sys
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any

import toml

from specify_cli.core.atomic import atomic_write
from specify_cli.paths import get_runtime_root

from .queue import DEFAULT_MAX_QUEUE_SIZE

if TYPE_CHECKING:
    from .target_authority import ResolvedSyncTarget


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
        # Resolve lazily per instance (not at import) so ``SPEC_KITTY_HOME``
        # and test ``HOME`` monkeypatching are honoured. On POSIX with the env
        # var unset this is ``~/.spec-kitty`` — byte-identical to the legacy
        # path (WP01 / NFR-001). ``get_runtime_root`` is seen as ``Any`` here
        # (mypy follow_imports=skip for ``specify_cli.*``); coerce at the typed
        # boundary.
        self.config_dir: Path = get_runtime_root().base
        self.config_file = self.config_dir / 'config.toml'

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

    def resolve_runtime_target(
        self,
        *,
        user_id: str | None = None,
        team_slug: str | None = None,
    ) -> "ResolvedSyncTarget":
        """Resolve the single canonical runtime sync target (contract §1, FR-016).

        This is the resolver-backed entry point every runtime surface should use
        to learn "what target are we actually hitting?" — as opposed to
        :meth:`get_server_url`, which is the low-level ``config.toml`` accessor
        the resolver itself consumes. The resolver folds in the
        ``SPEC_KITTY_SAAS_URL`` env precedence, fails-closed on an ambiguous
        split-brain before any network call, and *derives* the queue scope from
        the resolved URL (never an independent selector).

        Imported lazily because
        :mod:`specify_cli.sync.target_authority` imports :class:`SyncConfig`;
        a module-level import would create a cycle.
        """
        from .target_authority import resolve_sync_target

        return resolve_sync_target(user_id=user_id, team_slug=team_slug)

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
            raise ValueError(
                "[sync].background_daemon must be 'auto' or 'manual', not an empty string"
            )

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
