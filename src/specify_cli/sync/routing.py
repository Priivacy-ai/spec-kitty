"""Checkout-level sync routing and opt-in/opt-out controls."""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from ruamel.yaml import YAML

from specify_cli.core.paths import locate_project_root

from .body_queue import OfflineBodyUploadQueue
from .config import SyncConfig
from .git_metadata import GitMetadataResolver
from .project_identity import ensure_identity
from .queue import OfflineQueue


@dataclass(frozen=True)
class CheckoutSyncRouting:
    """Resolved sync routing state for the active checkout."""

    repo_root: Path
    project_uuid: str | None
    project_slug: str | None
    build_id: str | None
    repo_slug: str | None
    local_sync_enabled: bool | None
    repo_default_sync_enabled: bool | None
    effective_sync_enabled: bool


@dataclass(frozen=True)
class SyncOptOutResult:
    """Result of disabling SaaS sync for one checkout."""

    routing: CheckoutSyncRouting
    removed_events: int
    removed_body_uploads: int
    remembered_for_repo: bool


def resolve_checkout_sync_routing(start: Path | None = None) -> CheckoutSyncRouting | None:
    """Resolve the active checkout's effective sync policy."""
    repo_root = locate_project_root((start or Path.cwd()).resolve())
    if repo_root is None:
        return None

    identity = ensure_identity(repo_root)
    git_metadata = GitMetadataResolver(
        repo_root=repo_root,
        repo_slug_override=identity.repo_slug,
    ).resolve()
    repo_slug = git_metadata.repo_slug or identity.repo_slug

    local_sync_enabled = read_local_sync_enabled(repo_root)
    repo_default_sync_enabled = (
        SyncConfig().get_repository_sync_enabled(repo_slug)
        if repo_slug
        else None
    )

    if local_sync_enabled is not None:
        effective_sync_enabled = local_sync_enabled
    elif repo_default_sync_enabled is not None:
        effective_sync_enabled = repo_default_sync_enabled
    else:
        effective_sync_enabled = True

    return CheckoutSyncRouting(
        repo_root=repo_root,
        project_uuid=str(identity.project_uuid) if identity.project_uuid else None,
        project_slug=identity.project_slug,
        build_id=identity.build_id,
        repo_slug=repo_slug,
        local_sync_enabled=local_sync_enabled,
        repo_default_sync_enabled=repo_default_sync_enabled,
        effective_sync_enabled=effective_sync_enabled,
    )


def is_sync_enabled_for_checkout(start: Path | None = None) -> bool:
    """Return whether the active checkout may emit/upload SaaS sync data."""
    routing = resolve_checkout_sync_routing(start=start)
    if routing is None:
        return True
    return routing.effective_sync_enabled


def read_local_sync_enabled(repo_root: Path) -> bool | None:
    """Read the checkout-local ``sync.auto_start`` override, if present."""
    config_path = repo_root / ".kittify" / "config.yaml"
    if not config_path.exists():
        return None

    yaml = YAML()
    try:
        with open(config_path, encoding="utf-8") as fh:
            config = yaml.load(fh) or {}
    except Exception:
        return None

    sync_config = config.get("sync")
    if not isinstance(sync_config, dict):
        return None

    auto_start = sync_config.get("auto_start")
    if isinstance(auto_start, bool):
        return auto_start
    return None


def write_local_sync_enabled(repo_root: Path, enabled: bool) -> None:
    """Persist the checkout-local ``sync.auto_start`` override."""
    config_path = repo_root / ".kittify" / "config.yaml"
    yaml = YAML()
    yaml.preserve_quotes = True

    if config_path.exists():
        with open(config_path, encoding="utf-8") as fh:
            config = yaml.load(fh) or {}
    else:
        config = {}

    sync_config = config.get("sync")
    if not isinstance(sync_config, dict):
        sync_config = {}
        config["sync"] = sync_config
    sync_config["auto_start"] = bool(enabled)

    config_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=config_path.parent,
        prefix=".config.yaml.",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            yaml.dump(config, fh)
        os.replace(tmp_path, config_path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def enable_checkout_sync(
    repo_root: Path,
    *,
    remember_repo_default: bool = True,
) -> CheckoutSyncRouting:
    """Enable SaaS sync for this checkout and optionally future repo checkouts."""
    routing = resolve_checkout_sync_routing(repo_root)
    if routing is None:
        raise ValueError("Could not resolve the active checkout.")

    write_local_sync_enabled(repo_root, True)
    if remember_repo_default and routing.repo_slug:
        SyncConfig().set_repository_sync_enabled(routing.repo_slug, True)
    refreshed = resolve_checkout_sync_routing(repo_root)
    assert refreshed is not None
    return refreshed


def disable_checkout_sync(
    repo_root: Path,
    *,
    remember_repo_default: bool = True,
) -> SyncOptOutResult:
    """Disable SaaS sync for this checkout and purge its pending uploads."""
    routing = resolve_checkout_sync_routing(repo_root)
    if routing is None:
        raise ValueError("Could not resolve the active checkout.")

    write_local_sync_enabled(repo_root, False)
    if remember_repo_default and routing.repo_slug:
        SyncConfig().set_repository_sync_enabled(routing.repo_slug, False)

    queue = OfflineQueue()
    removed_events = (
        queue.remove_project_events(routing.project_uuid)
        if routing.project_uuid
        else 0
    )
    body_queue = OfflineBodyUploadQueue(db_path=queue.db_path)
    removed_body_uploads = (
        body_queue.remove_project_tasks(routing.project_uuid)
        if routing.project_uuid
        else 0
    )

    refreshed = resolve_checkout_sync_routing(repo_root)
    assert refreshed is not None
    return SyncOptOutResult(
        routing=refreshed,
        removed_events=removed_events,
        removed_body_uploads=removed_body_uploads,
        remembered_for_repo=bool(remember_repo_default and routing.repo_slug),
    )
