"""The unforgeable delivery input: a batch that carries its own consent answer.

**Why this module exists.** Two independent universes feed the same HTTP sink.
``delivery/dispatcher.py`` reaches it with consent pushed into SQL by
:func:`~specify_cli.delivery.selection.select_consented`;
``sync/history_import/upload.py`` reaches it having never asked (FR-028). The
shared object is :class:`~specify_cli.delivery.receivers.DeliveryReceiver`, and
that is exactly where a consent answer could have been made unbypassable —
instead consent lived one layer *above* it, in a selection function only one of
the two callers used. FR-001's retirement inherited the same scope error: it was
retired because ``_cross_project_refusal`` sits at the position a gate would
occupy, which is true for the dispatcher and false for ``import-history``, which
shares the ``GateContext`` and not the dispatcher.

So the fix is not another gate. ``deliver()`` stops accepting a bare
``Sequence[OutboundEvent]`` and accepts a :class:`ConsentedBatch` — a frozen type
whose only constructor requires a resolved :class:`ConsentAnswer`. A new sender
then cannot *write* a delivery call without first obtaining an answer; the guard
(``tests/architectural/test_egress_consent_boundary.py``) makes a new sender a
red build, and this makes it a type error at the point of writing.

**This is not a second consent chain (C-003).** Nothing here decides consent.
:func:`resolve_consent_answer` delegates to the one resolver —
``sync/consent.consented_project_uuids``, reached through
``delivery/selection``'s drain predicate — and merely wraps the value that
function already computes in a type that cannot be fabricated. The dispatcher
does not re-ask: :func:`~specify_cli.delivery.selection.select_consented` mints
the answer once, during the same resolution that builds the SQL predicate, and
carries it forward.

**What "unforgeable" means here, precisely.** Python has no private
constructors, so the claim is bounded and worth stating exactly:

* :class:`ConsentAnswer` and :class:`ConsentedBatch` both hold a module-private
  mint witness. ``__post_init__`` refuses any construction that does not present
  it, and then **clears** it, so ``dataclasses.replace`` on a genuine instance
  refuses too (that is the hole a plain sentinel field would leave: swapping the
  events of a legitimately-minted batch).
* Both are ``@final`` and refuse subclassing at runtime via
  ``__init_subclass__``, so the ``isinstance`` check the receivers perform
  cannot be satisfied by a class that overrode ``__post_init__``.
* What is *not* claimed: immunity to ``object.__new__`` plus
  ``object.__setattr__``, or to a caller that passes a fabricated
  ``consent_predicate``. Both are deliberate, visible acts — the predicate seam
  is the same injection point ``select_consented`` already exposes and
  tests already use. The bar is that a sender cannot reach the wire *by
  accident*, or by writing ordinary code, without an answer.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
import hashlib
from dataclasses import dataclass, field
from kernel.clock import datetime, now_utc, timedelta
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, final

if TYPE_CHECKING:  # pragma: no cover - typing only
    from collections.abc import Iterator
    from pathlib import Path

    from specify_cli.delivery.receivers import OutboundEvent

# The mint witness. Module-private and identity-compared: presenting it is only
# possible from inside this module, which is what confines minting to the two
# factories below.
_MINT: Any = object()

_NO_MINT = (
    "{name} cannot be constructed directly; it is minted by {factory}, which requires a "
    "resolved consent answer. A delivery input that could be built from a bare list would "
    "be documentation, not a control (#3030 FR-028)."
)


class ConsentNotResolved(TypeError):
    """Raised when a consent-bearing value is constructed outside its factory.

    A :class:`TypeError` on purpose: to a caller this is the same class of
    mistake as passing the wrong type to ``deliver``, and the receivers raise it
    for exactly that case too.
    """


class UnconsentedDelivery(RuntimeError):
    """Raised when a batch is minted for a project that did not consent.

    Carries the offending project uuids so the refusal can name them (US1a
    AS-1: refuse, *name the projects*, make no request).
    """

    def __init__(self, project_uuids: Sequence[str | None]) -> None:
        self.project_uuids: tuple[str | None, ...] = tuple(project_uuids)
        named = ", ".join(str(uuid) if uuid else "<unresolvable identity>" for uuid in self.project_uuids)
        super().__init__(f"refused before send: no consent answer grants {named}; absence of a consent record is not consent (#3030 FR-002/FR-028)")


@dataclass(frozen=True, slots=True)
class ProjectTransportDisclosure:
    """Immutable per-write identity consumed by the WP06 transport final gate."""

    project_uuid: str
    epoch_id: int
    consent_generation: int
    target_identity: str
    account_identity: str
    private_teamspace_id: str
    target_project_uuid: str
    target_generation: int
    admission_generation: str
    binding_audience: str
    write_kind: str
    native_identity: str
    payload_hash: str
    payload_reference: str
    attempt_id: str
    deadline_at: str
    reconciliation_policy: str = "native_identity_query"


@dataclass(frozen=True, slots=True)
class ProjectTransportRefusal:
    """A correlated, no-I/O refusal from the per-project final gate."""

    project_uuid: str
    attempt_id: str
    category: str
    diagnostic: str


class ProjectTransportResultError(RuntimeError):
    """Raised after I/O when the durable result fence cannot be recorded."""


class _ProjectTransportPhaseRefusal(RuntimeError):
    """Rollback sentinel for an atomic no-I/O transport phase."""

    def __init__(self, refusal: ProjectTransportRefusal) -> None:
        super().__init__(refusal.diagnostic)
        self.refusal = refusal


def default_transport_deadline(*, now: datetime | None = None) -> str:
    """Return the bounded disclosure deadline used by interactive senders."""
    base = now or now_utc()
    return (base + timedelta(minutes=5)).isoformat()


def stable_transport_id(*parts: object) -> str:
    """Build a stable, adapter-neutral identifier without leaking payload bytes."""
    text = "\x1f".join(str(part) for part in parts)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()  # noqa: TID251 - native idempotency key, not charter content


def execute_project_transport_disclosure(
    disclosure: ProjectTransportDisclosure,
    *,
    send: Callable[[], object],
    classify: Callable[[object], tuple[str, str | None]],
) -> object | ProjectTransportRefusal:
    """Run one interactive hosted write through WP06's attempt/lease/result gate.

    The caller supplies the immutable project/write identity and the I/O closure.
    This helper opens the project store, persists the durable attempt before I/O,
    proves a live per-project transport lease immediately before calling *send*,
    then records the genuine result under that same lease. If the project lacks
    current consent/admission/kill-switch eligibility, *send* is never invoked and
    the refusal is scoped to this exact project/attempt.
    """

    def _batch_send() -> object:
        return send()

    def _batch_classify(value: object) -> Mapping[str, tuple[str, str | None]]:
        return {disclosure.attempt_id: classify(value)}

    result = execute_project_transport_batch(
        [disclosure],
        send=_batch_send,
        classify=_batch_classify,
    )
    return result


def execute_project_transport_batch(  # noqa: C901 - four explicit transport phases share one lease
    disclosures: Sequence[ProjectTransportDisclosure],
    *,
    send: Callable[[], object],
    classify: Callable[[object], Mapping[str, tuple[str, str | None]]],
    restart_attempt_ids: frozenset[str] = frozenset(),
) -> object | ProjectTransportRefusal:
    """Run a same-project batch through per-item WP06 durable attempts.

    Every item is prepared and started in its own durable row before the single
    receiver call. Result correlation is supplied by *classify* and persisted per
    original attempt; if the send or result classification becomes uncertain, the
    original attempts are marked ``unknown`` rather than replaced or recorded as a
    fake terminal outcome.
    """
    if not disclosures:
        return send()
    refusal = _same_project_batch_refusal(disclosures)
    if refusal is not None:
        return refusal
    from specify_cli.sync.project_store import ProjectStoreError, ProjectSyncStore
    from specify_cli.sync.transport_attempts import (
        DeliveryOutcome,
        mark_transport_started,
        record_delivery_result,
        restart_delivery_attempt,
    )
    from specify_cli.sync.transport_lease import acquire_project_transport_lease

    store = ProjectSyncStore(disclosures[0].project_uuid)
    specs = {disclosure.attempt_id: _attempt_spec(disclosure) for disclosure in disclosures}
    start_required: set[str] = set()
    restart_required: set[str] = set()
    with acquire_project_transport_lease(store) as lease:
        with lease.unit_of_work() as (unit, context):
            for disclosure in disclosures:
                try:
                    _assert_expected_transport_authority(disclosure, context)
                except ProjectStoreError as exc:
                    return ProjectTransportRefusal(
                        project_uuid=disclosure.project_uuid,
                        attempt_id=disclosure.attempt_id,
                        category="project_not_admitted",
                        diagnostic=str(exc),
                    )
                try:
                    action, refusal = _prepare_or_recover_disclosure(
                        unit=unit,
                        context=context,
                        disclosure=disclosure,
                        spec=specs[disclosure.attempt_id],
                        restart_attempt_ids=restart_attempt_ids,
                    )
                    if refusal is not None:
                        return refusal
                    if action == "start":
                        start_required.add(disclosure.attempt_id)
                    elif action == "restart":
                        restart_required.add(disclosure.attempt_id)
                except ProjectStoreError as exc:
                    return ProjectTransportRefusal(
                        project_uuid=disclosure.project_uuid,
                        attempt_id=disclosure.attempt_id,
                        category="delivery_attempt_recovery_required",
                        diagnostic=str(exc),
                    )

        try:
            with lease.unit_of_work() as (unit, context):
                for disclosure in disclosures:
                    try:
                        _assert_expected_transport_authority(disclosure, context)
                    except ProjectStoreError as exc:
                        raise _ProjectTransportPhaseRefusal(
                            ProjectTransportRefusal(
                                project_uuid=disclosure.project_uuid,
                                attempt_id=disclosure.attempt_id,
                                category="project_not_admitted",
                                diagnostic=str(exc),
                            )
                        ) from exc
                    try:
                        if disclosure.attempt_id in start_required:
                            mark_transport_started(unit, context, disclosure.attempt_id)
                        elif disclosure.attempt_id in restart_required:
                            restart_delivery_attempt(unit, context, disclosure.attempt_id)
                    except ProjectStoreError as exc:
                        raise _ProjectTransportPhaseRefusal(
                            ProjectTransportRefusal(
                                project_uuid=disclosure.project_uuid,
                                attempt_id=disclosure.attempt_id,
                                category="delivery_attempt_recovery_required",
                                diagnostic=str(exc),
                            )
                        ) from exc
        except _ProjectTransportPhaseRefusal as exc:
            return exc.refusal

        try:
            value = send()
        except Exception:
            _mark_unknown(disclosures, lease=lease, reason="send raised before result correlation")
            raise

        try:
            outcomes = classify(value)
        except (ProjectStoreError, ValueError, TypeError) as exc:
            _mark_unknown(disclosures, lease=lease, reason=f"result classification failed: {exc}")
            raise ProjectTransportResultError(
                f"delivery disclosed bytes but result correlation failed; recover original attempts: {', '.join(d.attempt_id for d in disclosures)}"
            ) from exc

        # One unit for the whole batch's result fence (NFR-003: recording N
        # results must not open N connections). The fence is all-or-nothing:
        # a failure rolls back every result in the batch, and every original
        # attempt is marked unknown for recovery — never a partial fence that
        # claims some results while losing the one that failed.
        failed_attempt_id: str | None = None
        try:
            with lease.unit_of_work() as (unit, context):
                for disclosure in disclosures:
                    failed_attempt_id = disclosure.attempt_id
                    outcome_value, category = outcomes[disclosure.attempt_id]
                    _assert_expected_transport_authority(disclosure, context)
                    record_delivery_result(
                        unit,
                        context,
                        result_id=_transport_result_id(disclosure.attempt_id, "result"),
                        attempt_id=disclosure.attempt_id,
                        outcome=DeliveryOutcome(outcome_value),
                        terminal_refusal_category=category,
                    )
        except (KeyError, ProjectStoreError, ValueError) as exc:
            _mark_unknown(disclosures, lease=lease, reason=f"result persistence failed: {exc}")
            raise ProjectTransportResultError(
                f"delivery disclosed bytes but the durable result fence could not be recorded; recover original attempt {failed_attempt_id}: {exc}"
            ) from exc
        return value


def _same_project_batch_refusal(
    disclosures: Sequence[ProjectTransportDisclosure],
) -> ProjectTransportRefusal | None:
    project_uuids = {disclosure.project_uuid for disclosure in disclosures}
    if len(project_uuids) == 1:
        return None
    first = disclosures[0]
    return ProjectTransportRefusal(
        project_uuid=first.project_uuid,
        attempt_id=first.attempt_id,
        category="project_not_admitted",
        diagnostic="transport batch spans more than one project",
    )


def _prepare_or_recover_disclosure(
    *,
    unit: Any,
    context: Any,
    disclosure: ProjectTransportDisclosure,
    spec: Any,
    restart_attempt_ids: frozenset[str],
) -> tuple[str, ProjectTransportRefusal | None]:
    from specify_cli.sync.transport_attempts import (
        DeliveryAttemptState,
        RecoveryAction,
        get_delivery_attempt_record,
        plan_delivery_attempt_recovery,
        prepare_delivery_attempt,
    )

    existing = get_delivery_attempt_record(unit, attempt_id=disclosure.attempt_id)
    if existing is None:
        prepare_delivery_attempt(unit, context, spec)
        return "start", None
    if (
        existing.state not in {DeliveryAttemptState.PREPARED, DeliveryAttemptState.RETRYABLE_NO_EFFECT}
        or existing.native_identity != disclosure.native_identity
        or existing.payload_hash != disclosure.payload_hash
    ):
        return "", ProjectTransportRefusal(
            project_uuid=disclosure.project_uuid,
            attempt_id=disclosure.attempt_id,
            category="delivery_attempt_recovery_required",
            diagnostic="existing delivery attempt is not a prepared retry of the same native identity",
        )
    if existing.state in {DeliveryAttemptState.PREPARED, DeliveryAttemptState.RETRYABLE_NO_EFFECT}:
        decision = plan_delivery_attempt_recovery(unit, attempt_id=disclosure.attempt_id)
        if (
            (existing.state is DeliveryAttemptState.RETRYABLE_NO_EFFECT and disclosure.attempt_id not in restart_attempt_ids)
            or decision.action is not RecoveryAction.RETRY_NATIVE_IDENTITY
            or not decision.may_resend
        ):
            return "", ProjectTransportRefusal(
                project_uuid=disclosure.project_uuid,
                attempt_id=disclosure.attempt_id,
                category="delivery_attempt_recovery_required",
                diagnostic=decision.diagnostic,
            )
        return "restart" if existing.state is DeliveryAttemptState.RETRYABLE_NO_EFFECT else "start", None
    return "start", None


def _attempt_spec(disclosure: ProjectTransportDisclosure) -> Any:
    from specify_cli.sync.transport_attempts import DeliveryAttemptSpec

    return DeliveryAttemptSpec(
        attempt_id=disclosure.attempt_id,
        write_kind=disclosure.write_kind,
        native_identity=disclosure.native_identity,
        payload_hash=disclosure.payload_hash,
        payload_reference=disclosure.payload_reference,
        deadline_at=disclosure.deadline_at,
        reconciliation_policy=disclosure.reconciliation_policy,
    )


def _mark_unknown(disclosures: Sequence[ProjectTransportDisclosure], *, lease: Any, reason: str) -> None:
    from specify_cli.sync.project_store import ProjectStoreError
    from specify_cli.sync.transport_attempts import mark_delivery_result_unknown

    for disclosure in disclosures:
        try:
            with lease.unit_of_work() as (unit, context):
                mark_delivery_result_unknown(
                    unit,
                    context,
                    attempt_id=disclosure.attempt_id,
                    reason=reason,
                )
        except ProjectStoreError:
            pass


def _transport_result_id(attempt_id: str, kind: str) -> str:
    return f"{attempt_id}:{kind}"


def _assert_expected_transport_authority(
    disclosure: ProjectTransportDisclosure,
    context: Any,
) -> None:
    """Reject a leased context that does not match the exact target being called."""
    from specify_cli.sync.project_store import ProjectStoreError

    target = context.target_audience
    if target is None:
        raise ProjectStoreError("delivery attempt requires an admitted target audience")
    expected = {
        "project_uuid": disclosure.project_uuid,
        "target_identity": disclosure.target_identity,
        "account_identity": disclosure.account_identity,
        "private_teamspace_id": disclosure.private_teamspace_id,
        "target_project_uuid": disclosure.target_project_uuid,
        "target_generation": str(disclosure.target_generation),
        "admission_generation": disclosure.admission_generation,
        "binding_audience": disclosure.binding_audience,
        "epoch_id": str(disclosure.epoch_id),
        "consent_generation": str(disclosure.consent_generation),
    }
    actual = {
        "project_uuid": str(context.project_uuid.storage_token),
        "target_identity": target.target_identity,
        "account_identity": target.account_identity,
        "private_teamspace_id": target.private_teamspace_id,
        "target_project_uuid": target.project_uuid.storage_token,
        "target_generation": str(target.configuration_generation),
        "admission_generation": str(context.admission_generation),
        "binding_audience": str(context.binding_audience),
        "epoch_id": str(context.epoch_id),
        "consent_generation": str(context.consent_generation),
    }
    for key, expected_value in expected.items():
        if actual[key] != expected_value:
            raise ProjectStoreError(f"delivery target audience mismatch for {key}")


def _forbid_subclassing(cls: type) -> None:
    raise TypeError(f"{cls.__name__} is final: subclassing it would let __post_init__ be overridden, which is the receivers' isinstance check defeated in one line")


# ── the resolved answer ───────────────────────────────────────────────────────


@final
@dataclass(frozen=True, slots=True)
class ConsentAnswer:
    """A consent decision that was actually taken, for a known candidate set.

    ``granted`` is the subset of ``asked`` that consents. Both are recorded
    because "not in ``granted``" is ambiguous on its own: a uuid that was never
    *asked* is a different fault from one that was asked and refused, and the
    mint reports them differently.
    """

    granted: frozenset[str]
    asked: tuple[str, ...]
    _mint: Any = field(default=None, repr=False, compare=False)

    def __init_subclass__(cls, **kwargs: object) -> None:  # pragma: no cover - guard
        _forbid_subclassing(cls)

    def __post_init__(self) -> None:
        if self._mint is not _MINT:
            raise ConsentNotResolved(_NO_MINT.format(name="ConsentAnswer", factory="resolve_consent_answer()"))
        # Burn the witness so ``dataclasses.replace`` on a real answer cannot
        # widen ``granted`` — replace copies field values, and a live witness
        # would be one of them.
        object.__setattr__(self, "_mint", None)

    def grants(self, project_uuid: str | None) -> bool:
        return bool(project_uuid) and project_uuid in self.granted


def _drain_consent_predicate(checkout_roots: Sequence[Path] | None) -> Callable[[Sequence[str | None]], frozenset[str]]:
    """The one resolver, bound to the checkouts the caller can offer.

    Imported lazily: ``delivery`` must not acquire an import-time dependency on
    ``sync`` (C-001), and ``selection`` owns the drain's rooting rules. A root
    declaring a different ``project_uuid`` is ignored by the resolver, so
    offering one can never widen the answer.
    """
    if checkout_roots is None:
        from specify_cli.delivery.selection import _default_consent_predicate

        drain_predicate: Callable[[Sequence[str | None]], frozenset[str]] = _default_consent_predicate
        return drain_predicate

    from specify_cli.sync.consent import consented_project_uuids

    roots = list(checkout_roots)

    def _resolve(candidates: Sequence[str | None]) -> frozenset[str]:
        # Re-wrapped rather than returned directly: under the project's
        # ``follow_imports = "skip"`` mypy config a cross-module call is seen as
        # ``Any``, and this seam's return type is load-bearing.
        return frozenset(consented_project_uuids(list(candidates), checkout_roots=roots))

    return _resolve


def resolve_consent_answer(
    candidates: Sequence[str | None],
    *,
    consent_predicate: Callable[[Sequence[str | None]], frozenset[str]] | None = None,
    checkout_roots: Sequence[Path] | None = None,
) -> ConsentAnswer:
    """Ask the one resolver about *candidates* and mint the answer.

    This is the **only** way to obtain a :class:`ConsentAnswer`, and therefore
    the only way to reach :func:`consented_batch`. It decides nothing itself —
    ``consent_predicate`` defaults to the drain's resolver, so the precedence
    chain stays encoded once, in ``sync/consent.py``.
    """
    predicate = consent_predicate or _drain_consent_predicate(checkout_roots)
    asked = tuple(str(c) for c in candidates if c)
    granted = frozenset(predicate(list(candidates))) if candidates else frozenset()
    return ConsentAnswer(granted=granted, asked=asked, _mint=_MINT)


# ── envelope identity (one definition, shared with the refusal) ───────────────


def resolve_envelope_project(payload: Mapping[str, Any]) -> str | None:
    """Resolve an envelope's project identity, or ``None``.

    The three sites identity is written to (``namespace.project_uuid``,
    top-level, ``subject.project_uuid``), in one place, so the batch mint and
    ``receivers._cross_project_refusal`` cannot come to disagree about which
    project an envelope belongs to (C-003).

    ``None`` means *unresolvable from the envelope*. The refusal treats that as
    "not a project" — counting it as one would refuse ordinary batches holding a
    legacy identity-less row. The **mint** treats it as a denial, because
    NFR-001's second half is ``None ∉ delivered_project_uuids``; a caller whose
    identity authority is elsewhere (the dispatcher's stored ``project_uuid``
    column) supplies it explicitly instead.
    """
    namespace = payload.get("namespace")
    if isinstance(namespace, Mapping) and namespace.get("project_uuid"):
        return str(namespace["project_uuid"])
    if payload.get("project_uuid"):
        return str(payload["project_uuid"])
    subject = payload.get("subject")
    if isinstance(subject, Mapping) and subject.get("project_uuid"):
        return str(subject["project_uuid"])
    return None


# ── the batch ─────────────────────────────────────────────────────────────────


@final
@dataclass(frozen=True, slots=True)
class ConsentedBatch:
    """Events cleared for delivery, plus the answer that cleared them.

    ``event_projects`` maps ``event_id`` -> the ``project_uuid`` the event was
    attributed to when the batch was minted. It is kept rather than re-derived
    so a receiver, the ledger and any diagnostic all read the same attribution
    the consent check used.
    """

    events: tuple[OutboundEvent, ...]
    event_projects: Mapping[str, str]
    answer: ConsentAnswer
    _mint: Any = field(default=None, repr=False, compare=False)

    def __init_subclass__(cls, **kwargs: object) -> None:  # pragma: no cover - guard
        _forbid_subclassing(cls)

    def __post_init__(self) -> None:
        if self._mint is not _MINT:
            raise ConsentNotResolved(_NO_MINT.format(name="ConsentedBatch", factory="consented_batch()"))
        object.__setattr__(self, "_mint", None)

    def __len__(self) -> int:
        return len(self.events)

    def __iter__(self) -> Iterator[OutboundEvent]:
        return iter(self.events)

    @property
    def project_uuids(self) -> frozenset[str]:
        """The distinct projects this batch is attributed to."""
        return frozenset(self.event_projects.values())


def consented_batch(
    events: Sequence[OutboundEvent],
    *,
    answer: ConsentAnswer,
    event_projects: Mapping[str, str | None] | None = None,
) -> ConsentedBatch:
    """Mint a batch, or refuse — the single decision point for delivery consent.

    Every event must be attributable to a project *and* that project must be
    granted by *answer*. Both halves fail closed:

    * **unattributable** — the identity chain (or the caller's explicit map)
      yields ``None``. NFR-001 is a subset invariant whose second half is
      ``None ∉ delivered``; an event whose project cannot be identified can
      never be shown to belong to a consenting one.
    * **not granted** — including a project the answer was never *asked* about,
      which is the FR-028 shape exactly: holding the uuid and never asking it.

    *event_projects* lets a caller whose identity authority is not the envelope
    supply it. The dispatcher passes the stored ``project_uuid`` column, which
    C-003 makes the sole selection authority; ``import-history`` passes nothing
    and is attributed from the envelopes it is about to send, which is strictly
    what crosses the wire.
    """
    materialised = tuple(events)
    attribution: dict[str, str] = {}
    refused: list[str | None] = []
    for event in materialised:
        uuid = event_projects.get(event.event_id) if event_projects is not None else resolve_envelope_project(event.payload)
        if not answer.grants(uuid):
            if uuid not in refused:
                refused.append(uuid)
            continue
        assert uuid is not None  # narrowed by ``answer.grants``
        attribution[event.event_id] = uuid
    if refused:
        raise UnconsentedDelivery(refused)
    return ConsentedBatch(
        events=materialised,
        event_projects=MappingProxyType(attribution),
        answer=answer,
        _mint=_MINT,
    )


__all__ = [
    "ConsentAnswer",
    "ConsentNotResolved",
    "ConsentedBatch",
    "ProjectTransportDisclosure",
    "ProjectTransportRefusal",
    "ProjectTransportResultError",
    "UnconsentedDelivery",
    "consented_batch",
    "default_transport_deadline",
    "execute_project_transport_disclosure",
    "resolve_consent_answer",
    "resolve_envelope_project",
    "stable_transport_id",
]
