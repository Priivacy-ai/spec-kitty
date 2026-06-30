"""Checkout-level sync routing and opt-in/opt-out controls."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from specify_cli.core.paths import locate_project_root

from .body_queue import OfflineBodyUploadQueue
from .config import SyncConfig
from .git_metadata import GitMetadataResolver
from specify_cli.identity.project import ProjectIdentity, load_identity, resolve_identity
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
    """Resolve the active checkout's effective sync policy.

    Identity is resolved WITHOUT persisting (#2263, FR-002/FR-003): routing is a
    read of the checkout's effective sync policy and must never dirty
    ``.kittify/config.yaml``. The read-only twin
    ``resolve_checkout_sync_routing_readonly`` (which uses ``load_identity``) remains
    available for callers that must not even mint an in-memory identity.
    """
    repo_root = locate_project_root((start or Path.cwd()).resolve())
    if repo_root is None:
        return None

    identity = resolve_identity(repo_root)
    return _build_checkout_sync_routing(repo_root, identity)


def resolve_checkout_sync_routing_readonly(start: Path | None = None) -> CheckoutSyncRouting | None:
    """Resolve checkout sync policy without creating or updating project identity."""
    repo_root = locate_project_root((start or Path.cwd()).resolve())
    if repo_root is None:
        return None

    identity = load_identity(repo_root / ".kittify" / "config.yaml")
    return _build_checkout_sync_routing(repo_root, identity)


def _build_checkout_sync_routing(repo_root: Path, identity: ProjectIdentity) -> CheckoutSyncRouting:
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
    """Return whether the active checkout may emit/upload SaaS sync data.

    This is a pure *policy read* — it answers "is sync enabled?" and never needs
    to mint or persist project identity. It is reached from the accept-readiness
    path (``sync.emitter`` emit-time gate, batch/body-upload gates), so it MUST be
    side-effect-free: route through the read-only twin
    (``resolve_checkout_sync_routing_readonly``), which uses ``load_identity`` and
    never mints an identity at all. (As of #2263, ``resolve_checkout_sync_routing``
    is also side-effect-free — it resolves identity in-memory via
    ``resolve_identity`` — but the read-only twin remains the canonical choice for
    pure policy reads.) This is the third readiness writer closed for #1916 (WP08).
    """
    routing = resolve_checkout_sync_routing_readonly(start=start)
    if routing is None:
        return True
    return routing.effective_sync_enabled


def read_local_sync_enabled(repo_root: Path) -> bool | None:
    """Read the checkout-local sync override from global machine config."""
    return SyncConfig().get_checkout_sync_enabled(repo_root)


def write_local_sync_enabled(repo_root: Path, enabled: bool) -> None:
    """Persist the checkout-local sync override in global machine config."""
    SyncConfig().set_checkout_sync_enabled(repo_root, enabled)


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
