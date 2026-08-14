"""Checkout-level sync routing and opt-in/opt-out controls."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from specify_cli.core.paths import locate_project_root

from .config import ConfigReadFault, SyncConfig
from .consent import (
    LegacyConsentMigrationRequiredError,
    ProjectConsentRecord,
    project_local_consent_fault,
    record_project_opt_in,
    record_project_opt_out,
    resolve_project_consent,
)
from .git_metadata import GitMetadataResolver
from specify_cli.identity.project import ProjectIdentity, load_identity, resolve_identity

logger = logging.getLogger(__name__)


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
    #: Why the project-local ``.kittify/config.yaml`` could not be understood, when it
    #: exists but is unreadable, unparseable, or (#3030 FR-027) records a *field* value
    #: that cannot be used — an unusable ``sync.enabled`` or an unusable
    #: ``project.uuid``. ``None`` for the ordinary cases — a readable file, or no file
    #: at all. Present so a denial on this ground is distinguishable from the far more
    #: common "no record" denial: an operator told only "sync is disabled" goes looking
    #: for a missing opt-in instead of the broken file that actually caused it.
    project_local_fault: ConfigReadFault | None = None


@dataclass(frozen=True)
class SyncOptOutResult:
    """Result of disabling SaaS sync for one checkout."""

    routing: CheckoutSyncRouting
    removed_events: int
    removed_body_uploads: int
    remembered_for_repo: bool
    decision: ProjectConsentRecord | None = None


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

    unreadable = _routing_for_unreadable_project_config(repo_root)
    if unreadable is not None:
        return unreadable

    identity = resolve_identity(repo_root)
    return _build_checkout_sync_routing(repo_root, identity)


def resolve_checkout_sync_routing_readonly(start: Path | None = None) -> CheckoutSyncRouting | None:
    """Resolve checkout sync policy without creating or updating project identity."""
    repo_root = locate_project_root((start or Path.cwd()).resolve())
    if repo_root is None:
        return None

    unreadable = _routing_for_unreadable_project_config(repo_root)
    if unreadable is not None:
        return unreadable

    identity = load_identity(repo_root / ".kittify" / "config.yaml")
    return _build_checkout_sync_routing(repo_root, identity)


def _routing_for_unreadable_project_config(
    repo_root: Path,
) -> CheckoutSyncRouting | None:
    """Deny, without reading identity, when the project's own config is unreadable.

    ``None`` when there is no fault — the ordinary path, including the very common
    "no project config at all", which is absence and must keep falling through to the
    machine-level records (denying on absence would deny every delivery on the
    machine; ``ConfigReadFault`` draws that line, and this function inherits it).

    **The leak this closes (#3030 FR-022).** ``read_project_local_consent`` returns
    ``None`` for an unreadable or unparseable file exactly as it does for an absent
    one, and the chain below then falls through to ``local_sync_enabled`` — a
    *checkout-level grant*. So a committed ``sync.enabled: false`` that a later edit
    turned into a YAML syntax error was silently replaced by whatever the machine
    happened to hold. Measured before this fix, with a checkout grant present:
    ``chmod 000`` and unparseable YAML both resolved to **enabled**. FR-013's
    refusal-outranks-grant rule, voidable by a syntax error — and the record that
    wins is the one that survives a clone or a rename, so what stands in for the
    refusal is precisely a *stale grant*.

    ``consent.py`` split :func:`~specify_cli.sync.consent.project_local_consent_fault`
    out for this wiring rather than change ``read_project_local_consent``'s shape
    under its callers; this is that function's first production consumer.

    Deliberately placed **before** the identity read, not merely before the consent
    fall-through. A list-shaped ``config.yaml`` makes ``load_identity`` raise
    ``AttributeError: 'CommentedSeq' object has no attribute 'get'``
    (``identity/project.py:322``), so a policy read that is supposed to answer a
    boolean crashed the caller instead. Answering "deny" from here means an
    unreadable project file cannot take out any command that consults the gate.
    (The ``load_identity`` fault itself is still latent for its other callers and is
    reported separately — it is not this module's to fix.)

    **#3030 FR-027 widened what this fence catches, with no change here.** It consumes
    ``project_local_consent_fault`` rather than re-deciding readability, so extending
    that one notion from the *file* to a *field* — an unusable ``sync.enabled``, an
    unusable ``project.uuid`` — reached this path for free. That is the whole point of
    the C-003 shape: the two field-level leaks it now closes are
    ``sync.enabled: no`` overridden by a checkout-level grant (nineteen such shapes,
    all measured granting), and FR-024's residual, where a corrupt ``project.uuid``
    resolved to ``effective_sync_enabled=True`` with ``project_uuid=None`` — events
    captured with no identity at all, which is the population FR-011/FR-017 then have
    to clean up. Had this function re-implemented its own readability test, FR-027
    would have had to be fixed twice.
    """
    fault = project_local_consent_fault(repo_root)
    if fault is None:
        return None
    return _deny_routing_for_project_local_fault(repo_root, fault)


def _deny_routing_for_project_local_fault(repo_root: Path, fault: ConfigReadFault) -> CheckoutSyncRouting:
    """Build the fail-closed routing for an unreadable/unusable project-local file.

    Shared by the pre-identity fence (:func:`_routing_for_unreadable_project_config`)
    and by :func:`_build_checkout_sync_routing` itself (#3112), so "an unreadable
    project-local consent file fails closed" is guaranteed by the function that
    builds routing rather than only by callers running the fence first. The fence
    calls remain in place (defence-in-depth) — this is the local backstop for a
    caller that reaches ``_build_checkout_sync_routing`` directly.
    """
    logger.warning(
        "Denying hosted sync for %s: its project config could not be read (%s). %s",
        repo_root,
        fault.kind,
        fault.detail,
    )
    return CheckoutSyncRouting(
        repo_root=repo_root,
        project_uuid=None,
        project_slug=None,
        build_id=None,
        repo_slug=None,
        # Reported truthfully so the operator can see the grant that was NOT
        # honoured; the repo default is left unread because no value it could take
        # can change a fail-closed answer.
        local_sync_enabled=read_local_sync_enabled(repo_root),
        repo_default_sync_enabled=None,
        effective_sync_enabled=False,
        project_local_fault=fault,
    )


def _build_checkout_sync_routing(repo_root: Path, identity: ProjectIdentity) -> CheckoutSyncRouting:
    # #3112: fold the fault check in locally so the fail-closed invariant does not
    # depend on the caller having run ``_routing_for_unreadable_project_config``
    # first. Both current production callers already fence before reaching here, so
    # this branch is presently unreachable from them (defence-in-depth); it exists
    # for a future caller that invokes this function directly.
    fault = project_local_consent_fault(repo_root)
    if fault is not None:
        return _deny_routing_for_project_local_fault(repo_root, fault)

    git_metadata = GitMetadataResolver(
        repo_root=repo_root,
        repo_slug_override=identity.repo_slug,
    ).resolve()
    repo_slug = git_metadata.repo_slug or identity.repo_slug

    local_sync_enabled = read_local_sync_enabled(repo_root)
    repo_default_sync_enabled = SyncConfig().get_repository_sync_enabled(repo_slug) if repo_slug else None

    # Checkout and repository settings remain visible as legacy diagnostics, but
    # only the UUID-owned store decision may grant. The global environment value is
    # applied later as a deny-only egress switch, never in this authority read.
    decision = resolve_project_consent(str(identity.project_uuid) if identity.project_uuid else None)
    effective_sync_enabled = decision.granted

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
    """Reject the retired checkout grant writer with migration guidance."""
    del repo_root, enabled
    raise LegacyConsentMigrationRequiredError("checkout sync overrides are non-authoritative; use explicit project opt-in")


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
    actor: str = "local-operator",
) -> CheckoutSyncRouting:
    """Explicitly grant this UUID while leaving admission/network state separate."""
    del remember_repo_default
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

    record_project_opt_in(str(routing.project_uuid), actor=actor)
    refreshed = resolve_checkout_sync_routing(repo_root)
    assert refreshed is not None
    return refreshed


def disable_checkout_sync(
    repo_root: Path,
    *,
    remember_repo_default: bool = True,
    actor: str = "local-operator",
) -> SyncOptOutResult:
    """Explicitly refuse egress and seal the epoch without deleting local rows."""
    del remember_repo_default
    routing = resolve_checkout_sync_routing(repo_root)
    if routing is None:
        raise ValueError("Could not resolve the active checkout.")

    if not routing.project_uuid:
        raise ConsentIdentityUnresolvedError(repo_root)
    decision = record_project_opt_out(str(routing.project_uuid), actor=actor)

    refreshed = resolve_checkout_sync_routing(repo_root)
    assert refreshed is not None
    return SyncOptOutResult(
        routing=refreshed,
        removed_events=0,
        removed_body_uploads=0,
        remembered_for_repo=False,
        decision=decision,
    )
