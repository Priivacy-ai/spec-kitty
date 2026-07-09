"""``EventSyncConfig`` — the operator dial over **retention × delivery** (WP09, IC-06).

This module is *policy*, not target selection. It decides two orthogonal things
(**FR-006**, spec US2):

* **Retention** (``ON``/``OFF``) — does the journal persist event payloads?
* **Delivery** (``NONE`` / ``TEAMSPACE`` / ``EXTERNAL_RECEIVER``) — which WP06
  receiver, if any, drains the journal?

The four operator-facing presets (``TEAMSPACE``, ``EXTERNAL_RECEIVER``,
``LOCAL_RETENTION``, ``OPT_OUT``/``TRASH``) are *points* on those two axes; the
axes stay independent in the type system so ``LOCAL_RETENTION`` (retention ON ×
delivery NONE) is genuinely distinct from ``OPT_OUT`` (retention OFF × delivery
NONE).

**Boundary — policy, never target authority (FR-016, C-007, contract §1).**
``EventSyncConfig`` MUST NOT resolve or store the Teamspace network server URL.
When the ``TEAMSPACE`` mode needs a URL it reads it from the WP01-resolved target
passed into :meth:`EventSyncConfig.resolve` (the :class:`ResolvedTarget`), never
from this config. The config only carries *operator* parameters that are not
target authority — the ``EXTERNAL_RECEIVER`` endpoint/auth, which are inputs to a
WP06 :class:`~specify_cli.delivery.receivers.ExternalReceiver`.

**Opt-out safety — never silently drop (C-008, contract §2 rule 4).**
``OPT_OUT``/``TRASH`` discards a family **only** when a durability classification
proves it is local-only or explicitly discardable. A Teamspace-bound discard is
*refused* (with an audit-visible reason) or *audit-recorded* through a durable
source — never a silent no-op. An unknown/unclassified family fails **closed**
(treated as potentially Teamspace-bound).

Per **C-001** this module imports only the WP06 receivers; it never imports
``sync/queue.py`` or :mod:`specify_cli.events`. The WP01 resolved target is
consumed structurally (:class:`ResolvedTarget`), not by importing its concrete
class, so the policy layer never re-derives the network target.
"""
from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Protocol, runtime_checkable

from specify_cli.core.time_utils import now_utc_iso
from specify_cli.delivery.receivers import (
    DeliveryReceiver,
    ExternalReceiver,
    HttpPoster,
    TeamspaceReceiver,
    _requests_post,
)

# -- Audit-visible reason strings (S1192: referenced across helpers/tests) ------
_REASON_LOCAL_ONLY = "family classified local-only/explicitly-discardable; safe to discard"
_REASON_REFUSED = (
    "refusing to discard a Teamspace-bound family without durable audit evidence "
    "(C-008 fail-closed): no silent drop"
)
_REASON_AUDITED = "Teamspace-bound discard recorded to a durable audit source: {ref}"
_ERR_NO_ENDPOINT = "EXTERNAL_RECEIVER mode requires an operator endpoint URL"
_ERR_NO_TARGET = (
    "TEAMSPACE delivery requires a WP01-resolved target; none was supplied "
    "(delivery is blocked — capture still happens, SC-009)"
)


# --------------------------------------------------------------------------- #
# T051 — the two orthogonal axes
# --------------------------------------------------------------------------- #


class Retention(StrEnum):
    """Whether the journal persists event payloads (axis 1)."""

    ON = "on"
    OFF = "off"


class Delivery(StrEnum):
    """Which receiver, if any, drains the journal (axis 2)."""

    NONE = "none"
    TEAMSPACE = "teamspace"
    EXTERNAL_RECEIVER = "external_receiver"


# --------------------------------------------------------------------------- #
# T052 — the four presets as named modes over the axes
# --------------------------------------------------------------------------- #


class Mode(StrEnum):
    """The operator-facing named modes (FR-006). ``TRASH`` is an alias of ``OPT_OUT``."""

    TEAMSPACE = "teamspace"
    EXTERNAL_RECEIVER = "external_receiver"
    LOCAL_RETENTION = "local_retention"
    OPT_OUT = "opt_out"

    @classmethod
    def from_token(cls, token: str) -> Mode:
        """Normalize an operator token to a canonical :class:`Mode`.

        Case-insensitive; ``-`` folds to ``_`` so ``opt-out`` resolves. ``TRASH``
        is the documented alias of ``OPT_OUT`` and normalizes to it (only the
        canonical value is ever stored). Honors the Terminology Canon — there are
        no ``feature*`` aliases; any unknown token raises :class:`UnknownModeError`.
        """
        normalized = token.strip().lower().replace("-", "_")
        alias = _MODE_ALIASES.get(normalized)
        if alias is not None:
            return alias
        try:
            return cls(normalized)
        except ValueError as exc:
            raise UnknownModeError(token) from exc


# ``TRASH`` is the only alias; kept as a table so additions stay declarative.
_MODE_ALIASES: dict[str, Mode] = {"trash": Mode.OPT_OUT}

# The preset table — each named mode is one point on the (retention, delivery)
# plane. Hoisted to a module constant (S1192) so resolution is a pure lookup.
_MODE_PRESETS: dict[Mode, tuple[Retention, Delivery]] = {
    Mode.TEAMSPACE: (Retention.ON, Delivery.TEAMSPACE),
    Mode.EXTERNAL_RECEIVER: (Retention.ON, Delivery.EXTERNAL_RECEIVER),
    Mode.LOCAL_RETENTION: (Retention.ON, Delivery.NONE),
    Mode.OPT_OUT: (Retention.OFF, Delivery.NONE),
}


class EventSyncConfigError(ValueError):
    """Base class for policy-configuration errors."""


class UnknownModeError(EventSyncConfigError):
    """An operator mode token does not name a known preset."""

    def __init__(self, token: str) -> None:
        super().__init__(f"unknown sync mode {token!r}; expected one of {_mode_tokens()}")
        self.token = token


class MissingExternalEndpointError(EventSyncConfigError):
    """``EXTERNAL_RECEIVER`` was selected with no operator endpoint configured."""

    def __init__(self) -> None:
        super().__init__(_ERR_NO_ENDPOINT)


class PolicyResolutionError(EventSyncConfigError):
    """A mode could not be resolved to a runtime ``(retain, receiver)`` pair."""


def _mode_tokens() -> str:
    """A stable, operator-facing list of the canonical mode tokens (upper-cased)."""
    return ", ".join(sorted(mode.name for mode in Mode))


# --------------------------------------------------------------------------- #
# Structural seam for the WP01-resolved target (consumed, never imported)
# --------------------------------------------------------------------------- #


@runtime_checkable
class ResolvedTarget(Protocol):
    """The single attribute the policy reads off the WP01-resolved target.

    Structural on purpose (C-001 / FR-016): the policy never imports WP01's
    concrete ``ResolvedSyncTarget`` and never re-derives the URL — it only reads
    the already-resolved ``resolved_server_url``.
    """

    @property
    def resolved_server_url(self) -> str: ...


# --------------------------------------------------------------------------- #
# T053 — receiver factory + the resolved (retain, receiver) pair
# --------------------------------------------------------------------------- #


class ReceiverFactory(Protocol):
    """Builds the WP06 receivers a mode resolves to.

    Injected so tests can substitute a localhost :class:`StubReceiver` for the
    EXTERNAL branch — the resolution logic is identical, the stub is just an
    external receiver at a localhost URL (contract §4 rule 2).
    """

    def build_teamspace(self, *, resolved_server_url: str) -> DeliveryReceiver: ...

    def build_external(
        self, *, endpoint_url: str, auth_headers: Mapping[str, str] | None
    ) -> DeliveryReceiver: ...


@dataclass(frozen=True)
class DefaultReceiverFactory:
    """Builds the production WP06 receivers.

    ``teamspace_auth_token`` is supplied by the caller (WP12) — the Bearer token
    is **not** stored in :class:`EventSyncConfig` (policy ≠ credentials/target
    authority). The external receiver is credential-free unless the operator
    supplied headers via the config.
    """

    teamspace_auth_token: str = ""
    poster: HttpPoster = _requests_post

    def build_teamspace(self, *, resolved_server_url: str) -> DeliveryReceiver:
        return TeamspaceReceiver(
            resolved_server_url=resolved_server_url,
            auth_token=self.teamspace_auth_token,
            poster=self.poster,
        )

    def build_external(
        self, *, endpoint_url: str, auth_headers: Mapping[str, str] | None
    ) -> DeliveryReceiver:
        return ExternalReceiver(
            endpoint_url=endpoint_url, auth_headers=auth_headers, poster=self.poster
        )


@dataclass(frozen=True)
class ResolvedPolicy:
    """The runtime pair a mode resolves to: retain the journal? which receiver?"""

    retain: bool
    receiver: DeliveryReceiver | None


@dataclass(frozen=True)
class EventSyncConfig:
    """Retention × delivery policy. Constructed from a named mode (FR-006).

    Holds the two axes plus the EXTERNAL_RECEIVER operator parameters
    (``external_endpoint`` / ``external_auth``). It carries **no** Teamspace
    server URL — that is target authority (WP01), not policy (FR-016/C-007).
    """

    retention: Retention
    delivery: Delivery
    external_endpoint: str | None = None
    external_auth: Mapping[str, str] | None = field(default=None, compare=False)

    @classmethod
    def from_mode(
        cls,
        mode: Mode | str,
        *,
        external_endpoint: str | None = None,
        external_auth: Mapping[str, str] | None = None,
    ) -> EventSyncConfig:
        """Build a config from a named mode (the CLI/A7 ``sync mode`` entry point).

        ``EXTERNAL_RECEIVER`` requires ``external_endpoint`` (you cannot deliver
        externally with no endpoint). ``TEAMSPACE`` requires no endpoint here — it
        reads the resolved target at delivery time.
        """
        resolved_mode = mode if isinstance(mode, Mode) else Mode.from_token(mode)
        retention, delivery = _MODE_PRESETS[resolved_mode]
        if delivery is Delivery.EXTERNAL_RECEIVER and not external_endpoint:
            raise MissingExternalEndpointError
        return cls(
            retention=retention,
            delivery=delivery,
            external_endpoint=external_endpoint,
            external_auth=external_auth,
        )

    @property
    def mode(self) -> Mode:
        """The canonical named mode this (retention, delivery) point represents.

        Lets ``sync mode`` (with no argument) print the current mode and proves the
        ``TRASH`` → ``OPT_OUT`` normalization (only the canonical value is stored).
        """
        if self.delivery is Delivery.TEAMSPACE:
            return Mode.TEAMSPACE
        if self.delivery is Delivery.EXTERNAL_RECEIVER:
            return Mode.EXTERNAL_RECEIVER
        return Mode.LOCAL_RETENTION if self.retention is Retention.ON else Mode.OPT_OUT

    def resolve(
        self,
        *,
        resolved_target: ResolvedTarget | None = None,
        receiver_factory: ReceiverFactory | None = None,
    ) -> ResolvedPolicy:
        """Resolve this policy to a runtime ``(retain, receiver)`` pair.

        Retention maps directly to ``retain``; delivery maps to a WP06 receiver (or
        ``None``). ``TEAMSPACE`` reads the URL from *resolved_target* (FR-016);
        ``EXTERNAL_RECEIVER`` uses this config's endpoint/auth. The factory is a
        small build step — gate evaluation is receiver-owned (WP06), not here.
        """
        factory = receiver_factory if receiver_factory is not None else DefaultReceiverFactory()
        receiver = self._build_receiver(resolved_target, factory)
        return ResolvedPolicy(retain=self.retention is Retention.ON, receiver=receiver)

    def _build_receiver(
        self, resolved_target: ResolvedTarget | None, factory: ReceiverFactory
    ) -> DeliveryReceiver | None:
        if self.delivery is Delivery.NONE:
            return None
        if self.delivery is Delivery.TEAMSPACE:
            if resolved_target is None:
                raise PolicyResolutionError(_ERR_NO_TARGET)
            return factory.build_teamspace(resolved_server_url=resolved_target.resolved_server_url)
        if not self.external_endpoint:  # defensive — from_mode already guards this
            raise MissingExternalEndpointError
        return factory.build_external(
            endpoint_url=self.external_endpoint, auth_headers=self.external_auth
        )


# --------------------------------------------------------------------------- #
# T054 — OPT_OUT / TRASH discard safety (C-008)
# --------------------------------------------------------------------------- #


class FamilyClassification(StrEnum):
    """How a durability registry classifies an event family for discard safety.

    ``UNKNOWN`` is the fail-closed default: an unclassified family is treated as
    potentially Teamspace-bound and is never silently dropped.
    """

    LOCAL_ONLY = "local_only"
    EXPLICITLY_DISCARDABLE = "explicitly_discardable"
    TEAMSPACE_BOUND = "teamspace_bound"
    UNKNOWN = "unknown"


_DISCARDABLE_CLASSIFICATIONS = frozenset(
    {FamilyClassification.LOCAL_ONLY, FamilyClassification.EXPLICITLY_DISCARDABLE}
)


class DiscardDecisionKind(StrEnum):
    """The three C-008 outcomes for an ``OPT_OUT`` discard request."""

    DISCARD_ALLOWED = "discard_allowed"
    REFUSED = "refused"
    AUDIT_RECORDED = "audit_recorded"


@dataclass(frozen=True)
class DiscardAuditRecord:
    """A durable record of a Teamspace-bound discard, so the fact is never lost."""

    event_family: str
    classification: FamilyClassification
    reason: str
    at: str

    def to_json(self) -> str:
        return json.dumps(
            {
                "event_family": self.event_family,
                "classification": self.classification.value,
                "reason": self.reason,
                "at": self.at,
            },
            sort_keys=True,
        )


@dataclass(frozen=True)
class DiscardDecision:
    """The audit-visible result of an ``OPT_OUT`` discard request (C-008)."""

    kind: DiscardDecisionKind
    event_family: str
    classification: FamilyClassification
    reason: str

    @property
    def dropped(self) -> bool:
        """Whether the local copy may be discarded (allowed, or durably preserved)."""
        return self.kind in (DiscardDecisionKind.DISCARD_ALLOWED, DiscardDecisionKind.AUDIT_RECORDED)

    @property
    def refused(self) -> bool:
        return self.kind is DiscardDecisionKind.REFUSED


class AuditSink(Protocol):
    """A durable sink for Teamspace-bound discard evidence (SQLite/JSONL/git audit)."""

    def record(self, record: DiscardAuditRecord) -> str: ...


@dataclass
class JsonlAuditSink:
    """A durable, on-disk JSONL audit sink (the default durable source).

    Appends one JSON line per discard so the evidence survives the process; the
    returned reference is a stable ``<path>#<line-number>`` cursor.
    """

    path: Path

    def record(self, record: DiscardAuditRecord) -> str:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(record.to_json() + "\n")
        return f"{self.path}#{len(self.records())}"

    def records(self) -> list[DiscardAuditRecord]:
        if not self.path.exists():
            return []
        out: list[DiscardAuditRecord] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            data = json.loads(line)
            out.append(
                DiscardAuditRecord(
                    event_family=str(data["event_family"]),
                    classification=FamilyClassification(data["classification"]),
                    reason=str(data["reason"]),
                    at=str(data["at"]),
                )
            )
        return out


def discard_decision(
    event_family: str,
    *,
    classification: FamilyClassification,
    audit_sink: AuditSink | None = None,
) -> DiscardDecision:
    """Decide whether ``OPT_OUT`` may discard *event_family* (C-008, contract §2 rule 4).

    * local-only / explicitly-discardable → ``discard_allowed``.
    * Teamspace-bound or unknown (fail-closed) with a durable *audit_sink* →
      ``audit_recorded`` (durable evidence written; the fact is not lost).
    * Teamspace-bound or unknown with no durable sink → ``refused`` with an
      audit-visible reason — **never** a silent drop.
    """
    if classification in _DISCARDABLE_CLASSIFICATIONS:
        return DiscardDecision(
            kind=DiscardDecisionKind.DISCARD_ALLOWED,
            event_family=event_family,
            classification=classification,
            reason=_REASON_LOCAL_ONLY,
        )
    if audit_sink is None:
        return DiscardDecision(
            kind=DiscardDecisionKind.REFUSED,
            event_family=event_family,
            classification=classification,
            reason=_REASON_REFUSED,
        )
    record = DiscardAuditRecord(
        event_family=event_family,
        classification=classification,
        reason="Teamspace-bound family discarded under OPT_OUT; preserved durably",
        at=now_utc_iso(),
    )
    ref = audit_sink.record(record)
    return DiscardDecision(
        kind=DiscardDecisionKind.AUDIT_RECORDED,
        event_family=event_family,
        classification=classification,
        reason=_REASON_AUDITED.format(ref=ref),
    )


__all__ = [
    "Retention",
    "Delivery",
    "Mode",
    "EventSyncConfig",
    "EventSyncConfigError",
    "UnknownModeError",
    "MissingExternalEndpointError",
    "PolicyResolutionError",
    "ResolvedTarget",
    "ReceiverFactory",
    "DefaultReceiverFactory",
    "ResolvedPolicy",
    "FamilyClassification",
    "DiscardDecisionKind",
    "DiscardDecision",
    "DiscardAuditRecord",
    "AuditSink",
    "JsonlAuditSink",
    "discard_decision",
]
