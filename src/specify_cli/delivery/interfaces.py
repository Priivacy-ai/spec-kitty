"""Delivery-domain seams: the four ``typing.Protocol`` contracts + value objects.

This module is the IC-01 anti-spaghetti seam (**C-001**). It declares the
structural contracts that the rest of Phase 3/4 implements so the concrete WPs
bind to an *abstraction*, never to each other's concretions:

* :class:`DeliveryTargetRegistry` — implemented here in WP04 (``targets.py``).
* :class:`DeliveryLedger`        — implemented in WP05 (contract §3, FR-002).
* :class:`DeliveryReceiver`      — implemented in WP06 (contract §4).
* :class:`Dispatcher`           — implemented in WP07 (contract §3/§4).

It owns the small value objects exchanged across these seams (:class:`TargetIdentity`,
:class:`DeliveryTarget`, :class:`ResetSignal`). It contains **no implementation**:
protocol methods are ``...``-bodied. Value objects owned by *other* WPs (the
ledger row, the receiver result enum) are referenced as ``object`` with an
``# implemented in WPxx`` note rather than redefined here.

To avoid the import cycle the plan warns about, this module **must not import
``targets.py``**: the abstraction never depends on its concretion.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

# A deployment-metadata mapping as the registry/health surface exchanges it.
# Values are nullable because the URL-only MVP (C-004) may omit every field.
DeploymentMetadata = Mapping[str, str | None]


@dataclass(frozen=True)
class TargetIdentity:
    """The C-002 identity key for a delivery target.

    Identity is exactly ``(url_hash, team_slug, user_email)`` — a one-way hash of
    the canonical endpoint URL plus user/team scope. Deployment metadata is
    **never** part of this key. ``team_slug``/``user_email`` are normalized to
    ``""`` (not ``None``) when identity is unknown (pre-auth) so the same
    anonymous endpoint never forks into two identities.
    """

    url_hash: str
    team_slug: str
    user_email: str


@dataclass(frozen=True)
class DeliveryTarget:
    """A registered delivery-target row (spec Key Entities → *Delivery Target*).

    Carries the C-002 :class:`TargetIdentity` plus the recorded deployment
    metadata (provenance only) and first/last-seen timestamps. The deployment
    fields are nullable: they are absent in the URL-only MVP (C-004) and are
    never used to key identity.
    """

    target_id: str
    canonical_url: str
    identity: TargetIdentity
    server_instance_id: str | None
    deployment_id: str | None
    environment_name: str | None
    git_sha: str | None
    first_seen_at: str
    last_seen_at: str

    @property
    def url_hash(self) -> str:
        return self.identity.url_hash

    @property
    def team_slug(self) -> str:
        return self.identity.team_slug

    @property
    def user_email(self) -> str:
        return self.identity.user_email


@dataclass(frozen=True)
class ResetSignal:
    """Advisory environment-reset notice for a stable URL (**FR-012**).

    Emitted when a *stable* deployment field changes under an unchanged URL+scope
    identity (e.g. a preview env was wiped but kept its URL). It is purely
    advisory: it recommends a re-drain but does NOT fork identity, mutate ledger
    state, or call any SaaS ``/health`` endpoint (IC-09, out of scope — C-004).
    A ``deployment_id``-only change never produces a signal (Upsun re-stamps it
    on every push).
    """

    target_id: str
    changed_fields: tuple[str, ...]
    previous: DeploymentMetadata
    current: DeploymentMetadata
    recommendation: str


@runtime_checkable
class DeliveryTargetRegistry(Protocol):
    """Registry of delivery-target identities (**WP04**, contract §1/§3, FR-002).

    Identity is canonical-URL ``url_hash`` + user/team scope (C-002). ``register``
    is an idempotent upsert on that identity; deployment metadata is recorded as
    provenance only. ``@runtime_checkable`` so the seam can be asserted with
    ``isinstance`` in a smoke test.
    """

    def register(
        self,
        *,
        url: str,
        team_slug: str | None,
        user_email: str | None,
        deployment_metadata: DeploymentMetadata | None = None,
    ) -> DeliveryTarget: ...

    def get(
        self, url_hash: str, team_slug: str | None, user_email: str | None
    ) -> DeliveryTarget | None: ...

    def detect_reset(
        self,
        *,
        url: str,
        team_slug: str | None,
        user_email: str | None,
        new_deployment_metadata: DeploymentMetadata | None,
    ) -> ResetSignal | None: ...


class DeliveryLedger(Protocol):
    """Per-event/per-target delivery state (**WP05**, contract §3, FR-002).

    Declares method *signatures only*; the SQLite-backed implementation and the
    ledger-row value object are owned by WP05. ``delivered_anywhere`` is the
    immutability gate referenced by the journal/coalescing rules (contract §3).
    """

    def record_result(self, *, event_id: str, target_id: str, result: object) -> None:
        # ``result`` is the DeliveryResult enum — implemented in WP06.
        ...

    def select_pending(self, *, target_id: str, limit: int) -> Sequence[str]: ...

    def delivered_anywhere(self, event_id: str) -> bool: ...


class DeliveryReceiver(Protocol):
    """One dispatch contract per delivery-target type (**WP06**, contract §4).

    Mirrors the contract §4 column semantics (endpoint, auth, gates, per-event
    result mapping, retry). Teamspace, external-receiver, and stub all implement
    this single contract so the dispatcher carries no target-specific branches.
    """

    @property
    def endpoint_url(self) -> str: ...

    def auth_headers(self) -> Mapping[str, str]: ...

    def gates_satisfied(self) -> bool: ...

    def deliver(self, *, payloads: Sequence[bytes]) -> Sequence[object]:
        # Returns per-event DeliveryResult values — enum implemented in WP06.
        ...


class Dispatcher(Protocol):
    """Select → post → record across a registered target (**WP07**, contract §3/§4).

    Drives one :class:`DeliveryReceiver` against one :class:`DeliveryTarget`,
    recording outcomes through the :class:`DeliveryLedger`. The dispatch-summary
    return type is owned by WP07.
    """

    def dispatch(
        self, *, target: DeliveryTarget, receiver: DeliveryReceiver, ledger: DeliveryLedger
    ) -> object:
        # Returns a dispatch summary — implemented in WP07.
        ...
