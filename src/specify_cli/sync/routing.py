"""Checkout-level sync routing and opt-in/opt-out controls."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from specify_cli.core.paths import locate_project_root

from .body_queue import OfflineBodyUploadQueue
from .config import SyncConfig
from .consent import read_project_local_consent, set_project_consent
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

    # Level 1 of the consent chain (``sync/consent.py``): the project's OWN
    # ``.kittify/config.yaml`` ``sync.enabled`` key. Consulted first because it is the
    # most specific and the only reviewable input — it lives in the repo it governs
    # and shows up in a diff, where every record below it is machine-global state
    # invisible to the project.
    #
    # This read is why the acceptance pins in
    # ``tests/sync/test_sync_consent_default_deny.py`` mean anything. Until it landed,
    # nothing in the tree read that key: the pins wrote ``sync.enabled`` and passed
    # purely on the default-deny fall-through below, so flipping the fixture to an
    # explicit ``sync.enabled: true`` grant left them green — they were not testing
    # refusal-beats-grant at all.
    project_local_sync_enabled = read_project_local_consent(repo_root)

    if project_local_sync_enabled is not None:
        effective_sync_enabled = project_local_sync_enabled
    elif local_sync_enabled is not None:
        effective_sync_enabled = local_sync_enabled
    elif repo_default_sync_enabled is not None:
        effective_sync_enabled = repo_default_sync_enabled
    else:
        # FR-002 (spec-kitty#3030, absorbing #3031): absence of a consent record
        # is NOT consent — for capture *or* delivery.
        #
        # This fall-through used to yield ``True``, which is how the 2026-07-27
        # breach happened: five client projects had never been opted in, so
        # neither a checkout override nor a repo default existed, and every one
        # resolved to "sync enabled". Inverting only the ``routing is None``
        # branch of ``is_sync_enabled_for_checkout`` does not close it — those
        # projects resolve fine, they simply have no record.
        #
        # Pinned red on main by
        # ``tests/sync/test_sync_consent_default_deny.py::
        # test_unconfigured_checkout_does_not_consent_to_sync``.
        #
        # Deny here also gates the emit-time path (``sync/emitter.py:1890,1921``)
        # and the body-upload path (``sync/body_upload.py:150``). That is now
        # intended: NFR-005 was amended so capture-first durability applies only
        # to *consenting* projects — a non-consenting project's events must never
        # reach the journal (#3031 Defect 3).
        effective_sync_enabled = False

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
        # FR-003 (spec-kitty#3030): fail CLOSED. This returned ``True``, so any
        # invocation where the checkout could not be resolved was treated as
        # consent. For a gate standing in front of a confidentiality boundary
        # the default is inverted: inability to determine consent is not consent.
        return False
    return routing.effective_sync_enabled


def read_local_sync_enabled(repo_root: Path) -> bool | None:
    """Read the checkout-local sync override from global machine config."""
    return SyncConfig().get_checkout_sync_enabled(repo_root)


def write_local_sync_enabled(repo_root: Path, enabled: bool) -> None:
    """Persist the checkout-local sync override in global machine config."""
    SyncConfig().set_checkout_sync_enabled(repo_root, enabled)


class ConsentIdentityUnresolvedError(RuntimeError):
    """No ``project_uuid`` resolved while recording consent (#3030 T016).

    Raised instead of writing a path-keyed record with no uuid counterpart. Under
    FR-002 an absent uuid record denies, so a half-written grant would silently
    never deliver.
    """

    def __init__(self, repo_root: Path) -> None:
        super().__init__(
            f"Cannot record hosted-sync consent for {repo_root}: no project_uuid "
            "resolved. Run `spec-kitty init` in this checkout so it has a project "
            "identity, then retry."
        )


def enable_checkout_sync(
    repo_root: Path,
    *,
    remember_repo_default: bool = True,
) -> CheckoutSyncRouting:
    """Enable SaaS sync for this checkout and optionally future repo checkouts."""
    routing = resolve_checkout_sync_routing(repo_root)
    if routing is None:
        raise ValueError("Could not resolve the active checkout.")

    # #3030 T016: fail loudly rather than half-succeed. Under FR-002 absence of a
    # uuid-keyed record denies, so writing only the path-keyed record here would
    # leave the index empty and silently never deliver the project the operator
    # just explicitly opted in — the exact failure the inversion was supposed to
    # avoid. resolve_checkout_sync_routing already mints identity, so a missing
    # uuid at this point is a real fault, not a state to paper over.
    if not routing.project_uuid:
        raise ConsentIdentityUnresolvedError(repo_root)

    write_local_sync_enabled(repo_root, True)
    if remember_repo_default and routing.repo_slug:
        SyncConfig().set_repository_sync_enabled(routing.repo_slug, True)
    set_project_consent(str(routing.project_uuid), True)
    refreshed = resolve_checkout_sync_routing(repo_root)
    assert refreshed is not None
    return refreshed


def disable_checkout_sync(
    repo_root: Path,
    *,
    remember_repo_default: bool = True,
) -> SyncOptOutResult:
    """Disable SaaS sync for this checkout and purge its pending uploads.

    "Pending uploads" spans two live stores: the event journal's rows for this
    project that have not been delivered anywhere, and the project's queued document
    bodies. Already-delivered journal rows are **kept** — see the C-004 note in the
    body — and removing everything is the operator's explicit ``sync purge``
    (FR-016), which is dry-run by default.
    """
    from specify_cli.delivery.retention import purge_project_events_from_live_stores

    routing = resolve_checkout_sync_routing(repo_root)
    if routing is None:
        raise ValueError("Could not resolve the active checkout.")

    write_local_sync_enabled(repo_root, False)
    if remember_repo_default and routing.repo_slug:
        SyncConfig().set_repository_sync_enabled(routing.repo_slug, False)

    if routing.project_uuid:
        # #3030 FR-013: record the refusal uuid-keyed as well, so the drain
        # honours it from any checkout and after this one moves or is deleted.
        set_project_consent(str(routing.project_uuid), False)

    # C-004 (#3030 WP08): the legacy-queue purge is retired. It targeted the store
    # WP02 removed the drain from — nothing ships out of it — and full-decoded every
    # row to find the project. The store that *does* ship is the event journal, which
    # only gained a ``project_uuid`` column in WP04; that is why C-004 had to wait
    # for this WP.
    #
    # Scope is deliberately "queued" (no terminal-success delivery anywhere), not
    # everything: C-002 reserves wholesale deletion for the operator's explicit
    # ``sync purge`` (FR-016/FR-017, dry-run by default), and ``removed_events`` is
    # printed as "Removed N queued event(s)". Destroying the record of what already
    # left the machine on a routing toggle would be both a surprise and the loss of
    # the incident's own evidence.
    removed_events = 0
    if routing.project_uuid:
        purge = purge_project_events_from_live_stores(
            str(routing.project_uuid), dry_run=False, undelivered_only=True
        )
        # ``None`` means there is no journal on disk yet — nothing to purge, and no
        # store is created just to report zero.
        removed_events = 0 if purge is None else purge.purged_count

    # Body uploads stay: they are a *separate* store the daemon still drains (WP11
    # gated it per task, it did not remove it), so this purge is live, not
    # superseded. Removing this call would reopen the path WP11 just closed.
    body_queue = OfflineBodyUploadQueue(db_path=OfflineQueue().db_path)
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
