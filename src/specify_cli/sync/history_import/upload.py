"""PROVENANCE + PREFLIGHT + UPLOAD for ``sync import-history`` (WP-Y5, #2262).

Takes the synthesized envelope stream and materializes it into the SaaS
projection, reusing the WP06 delivery receiver as the transport seam rather
than hand-rolling HTTP:

* **PROVENANCE (stage 6):** a per-envelope ``envelope_sha256`` manifest, hashed
  with the same canonical-JSON shape the migration dry-run uses.
* **PREFLIGHT (stage 7):** POST each chunk's exact proof-bearing
  ``HistoryPreflightRequest`` to ``/api/v1/events/preflight/`` and require a
  correlated result for every event. The server validates shape/ingress without
  mutating state. Every chunk is preflighted *before* any chunk uploads, so a
  *preflight* rejection anywhere leaves the projection untouched (fail-closed,
  INV-6).
* **UPLOAD (stage 8):** chunk the stream mission-atomically (no mission ever
  straddles a chunk boundary — see :func:`_chunked`) and hand each chunk to a
  :class:`DeliveryReceiver` (canonical batch encoding, POST, response mapping,
  and poison-batch bisection all live there). Delivery stops at the first chunk that reports any
  failure outcome, so a mid-upload delivery failure leaves at most a partial —
  and because chunks are Lamport-ordered and mission-atomic, any delivered
  prefix is a valid ordered prefix of whole missions (never an orphan). The
  report flags that state (``UploadReport.partial``). A re-run preserves the
  same durable attempt/native identity; it never mints a fresh identity merely
  to reach server-side deduplication.

The transport is injectable: production passes an authed ``TeamspaceReceiver``
and the default ``requests`` poster; tests pass a ``StubReceiver`` and a fake
poster, so the whole stage runs with no network.

**CONSENT (#3030 FR-028).** Until 2026-07-30 this whole stage was ungated: a
grep for consent across ``sync/history_import/`` returned zero hits, and the only
gate was ``_resolve_gated_receiver``'s ``GateKind`` set — the exact set the
mission's root-cause §1 names as having no consent field — plus a
``Mode.TEAMSPACE`` check. The path is single-project by construction
(``build_import_plan`` yields one ``plan.identity.project_uuid``), so it held the
uuid and never asked it. It is now gated by construction rather than by another
check: :func:`_consented_batches` mints one
:class:`~specify_cli.delivery.consent_gate.ConsentedBatch` per chunk, which is
the only thing ``receiver.deliver`` accepts, and it runs **before the preflight**
— because ``run_server_preflight`` is a second sink carrying the same envelopes,
and a gate placed at the delivery call alone would have leaked every one of them.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import requests

from specify_cli.core.contract_gate import validate_outbound_payload
from specify_cli.delivery.consent_gate import (
    ConsentAnswer,
    ConsentedBatch,
    ProjectTransportDisclosure,
    ProjectTransportRefusal,
    UnconsentedDelivery,
    consented_batch,
    default_transport_deadline,
    execute_project_transport_batch,
    resolve_consent_answer,
    resolve_envelope_project,
    stable_transport_id,
)
from specify_cli.delivery.interfaces import DeliveryTarget
from specify_cli.delivery.receivers import (
    BATCH_TIMEOUT_SECONDS,
    DeliveryEffectCertainty,
    DeliveryOutcome,
    DeliveryReceiver,
    DeliveryResult,
    HttpPoster,
    OutboundEvent,
    default_http_poster,
    disclosed_event_payload_bytes,
)
from specify_cli.delivery.targets import canonicalize_url, compute_target_id
from specify_cli.migration.envelope_seam import envelope_sha256
from specify_cli.status import MISSION_CREATED
from specify_cli.sync.history_disclosure import (
    HistoryDisclosureCapability,
    HistoryDisclosureError,
    revalidate_history_disclosure,
)
from specify_cli.sync.project_context import (
    AdmissionState,
    ProjectSyncContext,
    validate_project_sync_context_authority,
)
from specify_cli.sync.project_identity import CanonicalProjectUUID
from specify_cli.sync.project_store import ProjectStoreError, ProjectSyncStore
from specify_cli.sync.transport_attempts import (
    DeliveryAttemptSpec,
    DeliveryOutcome as TransportDeliveryOutcome,
    DeliveryTerminalResultProjection,
    DeliveryTerminalResultStatus,
    get_delivery_terminal_result_projection,
)
from specify_cli.sync.transport_lease import acquire_project_transport_lease

_PREFLIGHT_ENDPOINT_PATH = "/api/v1/events/preflight/"
_SYNC_PROTOCOL_VERSION = "2.0"
# One delivery timeout policy for the whole SaaS transport: reuse the receiver's
# canonical batch timeout rather than re-declaring the same 60s value (#2884).
_PREFLIGHT_TIMEOUT_SECONDS = BATCH_TIMEOUT_SECONDS
# Conservative per-request size: well under the server's 1000-event cap and its
# 512 KiB decompressed byte ceiling. The receiver still auto-bisects on a 413.
_IMPORT_CHUNK_SIZE = 500
# The server's hard per-batch envelope cap. A single mission larger than
# _IMPORT_CHUNK_SIZE is deliberately NOT split (mission-atomic chunking, see
# _chunked) and becomes one oversized chunk — safe up to this many events per
# batch. A mission that exceeds even this cap is caught fail-closed before any
# network round-trip by _assert_batches_within_cap.
_SERVER_MAX_BATCH_SIZE = 1000
_MAX_REJECTED_SAMPLES = 5

# The outbound-envelope contract context every producer validates against
# (sync.emitter/batch/client all pass this to validate_outbound_payload). The
# import producer runs the same offline gate so its hand-assembled prefix
# envelopes fail fast locally, consistent with the rest of the fleet (#2884).
_ENVELOPE_CONTRACT_CONTEXT = "envelope"

Envelope = Mapping[str, Any]


# ── provenance (stage 6) ──────────────────────────────────────────────────────
#
# The canonical-JSON SHA-256 recipe is shared with the migration dry-run's
# row mapping — one owner (mission_state.envelope_sha256, re-exported through
# the envelope_seam), so the two checksums cannot drift (#2884).


@dataclass(frozen=True)
class ImportProvenanceEntry:
    """One provenance record for the import audit manifest."""

    event_id: str
    event_type: str
    envelope_sha256: str
    # Import envelopes are synthesized / replayed, not lifted verbatim from a
    # single on-disk JSONL row, so there is no row_sha256 to anchor.
    row_sha256: str | None = None


def build_provenance_manifest(envelopes: Sequence[Envelope]) -> list[ImportProvenanceEntry]:
    return [
        ImportProvenanceEntry(
            event_id=str(env["event_id"]),
            event_type=str(env["event_type"]),
            envelope_sha256=envelope_sha256(env),
        )
        for env in envelopes
    ]


# ── preflight (stage 7) ───────────────────────────────────────────────────────


class PreflightRejected(RuntimeError):
    """Raised when the server preflight refuses a chunk (fail-closed)."""

    def __init__(self, payload: Mapping[str, Any]) -> None:
        self.payload = dict(payload)
        super().__init__(f"server preflight rejected the batch: {_preflight_rejection_message(self.payload)}")


_PREFLIGHT_TOP_LEVEL_DIAGNOSTIC_FIELDS = ("category", "code")
_PREFLIGHT_DETAIL_FIELDS = ("event_id", "path", "detail")


def _first_preflight_detail(payload: Mapping[str, Any]) -> Mapping[str, Any] | None:
    """Return the first per-event entry of a deployed 400 ``details[]`` array.

    ``apps/sync/serializers.py::serialize_live_ingress_failure`` (deployed SaaS)
    shapes a rejection as one ``detail`` per offending event
    (``category``/``code``/``detail``/``event_id``/``index``/``path``/``value``);
    the first entry is the same one the server's own ``error`` summary is
    derived from.
    """
    raw = payload.get("details")
    if isinstance(raw, list) and raw and isinstance(raw[0], Mapping):
        return raw[0]
    return None


def _preflight_structured_diagnostic(payload: Mapping[str, Any]) -> dict[str, Any] | None:
    """Extract the deployed server's structured rejection diagnostic, if sent.

    ``None`` when the payload carries no top-level ``error`` summary --
    callers fall back to whatever legacy shape they have (#3582 backward
    compatibility). The deployed rejection shape carries the summary as
    top-level ``error``/``category``/``code`` plus a ``details[]`` array (one
    entry per offending event); older/test shapes may only carry a per-event
    ``error_category`` alias, which :func:`_canonical_preflight_error_category`
    already resolves.
    """
    error_message = payload.get("error")
    if not (isinstance(error_message, str) and error_message.strip()):
        return None
    diagnostic: dict[str, Any] = {"error": error_message.strip()}
    for field_name in _PREFLIGHT_TOP_LEVEL_DIAGNOSTIC_FIELDS:
        value = payload.get(field_name)
        if isinstance(value, str) and value.strip():
            diagnostic[field_name] = value.strip()
    first_detail = _first_preflight_detail(payload)
    if first_detail is not None:
        for field_name in _PREFLIGHT_DETAIL_FIELDS:
            value = first_detail.get(field_name)
            if value:
                diagnostic.setdefault(field_name, value)
        if "category" not in diagnostic:
            category = _canonical_preflight_error_category(first_detail)
            if category:
                diagnostic["category"] = category
    return diagnostic


def _preflight_rejection_message(payload: Mapping[str, Any]) -> str:
    """Prefer the server's structured diagnostic over reconciliation counters.

    Preflight never mutates state (``/api/v1/events/preflight/`` runs no
    ingestion), so its ``reconciliation`` counters are structurally always
    null/zero -- surfacing them for a genuine rejection hides the real cause
    (#3582). Prefer the top-level ``error``/``category``/``code`` plus the
    first ``details[]`` entry whenever the server actually sent one; keep the
    reconciliation counters as secondary context rather than discarding them.
    Payloads that only carry ``error`` (e.g. a local transport failure) or
    neither fall back to the pre-existing rendering.
    """
    diagnostic = _preflight_structured_diagnostic(payload)
    if diagnostic is not None:
        reconciliation = payload.get("reconciliation")
        if isinstance(reconciliation, Mapping) and reconciliation:
            diagnostic = {**diagnostic, "reconciliation": dict(reconciliation)}
        return str(diagnostic)
    return str(payload.get("reconciliation") or payload.get("error") or payload)


class HistoryTransportAuthorityError(RuntimeError):
    """The exact confirmed history cohort cannot use this project target."""


@dataclass(frozen=True, slots=True)
class _PreflightResponse:
    status_code: int
    payload: Mapping[str, Any] | None
    error: str | None = None
    expected_event_ids: tuple[str, ...] = ()

    @property
    def accepted(self) -> bool:
        if self.status_code != 200 or self.payload is None:
            return False
        results = _correlated_preflight_results(self.payload)
        if results is not None:
            if set(results) != set(self.expected_event_ids):
                return False
            return all(str(result.get("status") or "").strip().lower() in {"success", "duplicate"} for result in results.values())
        # Deployed contract (#3581): a 200 response with NO ``results`` key at
        # all (preflight never mutates state, so it has nothing to correlate)
        # is accepted only when the server's own top-level verdict says so. A
        # ``results`` that IS present but does not correlate is a malformed or
        # partial verdict -- fail closed, never waive (F1).
        if "results" in self.payload:
            return False
        return self.payload.get("accepted") is True


def _admission_bound_event(
    envelope: Envelope,
    *,
    project_context: ProjectSyncContext,
) -> dict[str, Any]:
    """Return the pinned SaaS ``EventWrite`` for one exact local envelope."""
    validate_project_sync_context_authority(project_context)
    project_uuid = project_context.project_uuid.storage_token
    raw_admission_generation = project_context.admission_generation
    binding_audience = project_context.binding_audience
    if raw_admission_generation is None or binding_audience is None:
        raise HistoryTransportAuthorityError("history event write requires current admission generation and binding audience")
    try:
        admission_generation = int(raw_admission_generation)
    except (TypeError, ValueError) as exc:
        raise HistoryTransportAuthorityError("history admission generation is not a positive integer") from exc
    if admission_generation < 1:
        raise HistoryTransportAuthorityError("history admission generation is not a positive integer")
    supplied = {
        "project_uuid": project_uuid,
        "admission_generation": admission_generation,
        "binding_audience": binding_audience,
    }
    for key, expected in supplied.items():
        current = envelope.get(key)
        if current is not None and str(current) != str(expected):
            raise HistoryTransportAuthorityError(f"history event carries a conflicting {key}")
    return {**dict(envelope), **supplied}


def _canonical_request_bytes(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _correlated_preflight_results(
    payload: Mapping[str, Any],
) -> dict[str, Mapping[str, Any]] | None:
    raw = payload.get("results")
    if not isinstance(raw, list):
        return None
    correlated: dict[str, Mapping[str, Any]] = {}
    for item in raw:
        if not isinstance(item, Mapping):
            return None
        event_id = item.get("event_id")
        if not isinstance(event_id, str) or not event_id.strip() or event_id in correlated:
            return None
        correlated[event_id] = item
    return correlated


def _preflight_request(
    envelopes: Sequence[Envelope],
    *,
    server_url: str,
    auth_token: str,
    project_context: ProjectSyncContext,
    history_capability: HistoryDisclosureCapability,
) -> tuple[str, bytes, dict[str, str]]:
    url = server_url.rstrip("/") + _PREFLIGHT_ENDPOINT_PATH
    body = _canonical_request_bytes(
        {
            "history_action_id": history_capability.action_id,
            "preview_hash": history_capability.preview_hash,
            "events": [
                _admission_bound_event(
                    envelope,
                    project_context=project_context,
                )
                for envelope in envelopes
            ],
        }
    )
    return (
        url,
        body,
        {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json",
            "X-Spec-Kitty-Sync-Protocol": _SYNC_PROTOCOL_VERSION,
        },
    )


def _post_server_preflight(
    envelopes: Sequence[Envelope],
    *,
    server_url: str,
    auth_token: str,
    poster: HttpPoster,
    project_context: ProjectSyncContext,
    history_capability: HistoryDisclosureCapability,
) -> _PreflightResponse:
    """Perform only the HTTP call; reachable solely inside the WP06 gate."""
    url, body, headers = _preflight_request(
        envelopes,
        server_url=server_url,
        auth_token=auth_token,
        project_context=project_context,
        history_capability=history_capability,
    )
    try:
        response = poster(
            url,
            data=body,
            headers=headers,
            timeout=_PREFLIGHT_TIMEOUT_SECONDS,
        )
    except requests.RequestException:
        # The canonical gate owns uncertainty for an exception after the
        # attempt becomes in-flight.  Do not translate it before that fence.
        raise
    try:
        payload = response.json()
    except Exception:
        return _PreflightResponse(
            status_code=response.status_code,
            payload=None,
            error=f"preflight response was not JSON (HTTP {response.status_code})",
            expected_event_ids=tuple(str(envelope["event_id"]) for envelope in envelopes),
        )
    if not isinstance(payload, Mapping):
        return _PreflightResponse(
            status_code=response.status_code,
            payload=None,
            error=f"preflight response was not an object (HTTP {response.status_code})",
            expected_event_ids=tuple(str(envelope["event_id"]) for envelope in envelopes),
        )
    return _PreflightResponse(
        response.status_code,
        dict(payload),
        expected_event_ids=tuple(str(envelope["event_id"]) for envelope in envelopes),
    )


def run_server_preflight(
    envelopes: Sequence[Envelope],
    *,
    server_url: str,
    auth_token: str,
    poster: HttpPoster = default_http_poster,
    project_context: ProjectSyncContext | None = None,
    target: DeliveryTarget | None = None,
    history_capability: HistoryDisclosureCapability | None = None,
) -> dict[str, Any]:
    """Preflight one exact confirmed cohort through a durable WP06 attempt."""
    if project_context is None or target is None or history_capability is None:
        raise PreflightRejected({"error": "history preflight requires exact project context, target, and confirmed capability"})
    try:
        response = _run_gated_preflight_chunk(
            envelopes,
            all_envelopes=envelopes,
            server_url=server_url,
            auth_token=auth_token,
            poster=poster,
            project_context=project_context,
            target=target,
            history_capability=history_capability,
        )
    except requests.RequestException as exc:
        raise PreflightRejected({"error": f"preflight transport failed: {exc}"}) from exc
    if not response.accepted:
        raise PreflightRejected(response.payload or {"error": response.error or "preflight rejected"})
    assert response.payload is not None
    return dict(response.payload)


def validate_import_envelopes(envelopes: Sequence[Envelope]) -> None:
    """Run the offline outbound-envelope contract gate over every envelope.

    Every other envelope producer (``sync.emitter``/``batch``/``client``)
    validates at emit/enqueue time; the import producer runs the same gate so
    its hand-assembled ``MissionCreated``/``WPCreated`` prefix envelopes fail
    fast locally instead of only at the server-preflight round-trip — closing
    the defense-in-depth gap the #2884 review flagged. Raises
    :class:`~specify_cli.core.contract_gate.ContractViolationError` on the first
    offending envelope, before any network call.
    """
    for env in envelopes:
        validate_outbound_payload(dict(env), _ENVELOPE_CONTRACT_CONTEXT)


def _assert_batches_within_cap(chunks: Sequence[Sequence[Envelope]]) -> None:
    """Fail closed if any mission-atomic chunk exceeds the server's batch cap.

    Mission-atomic chunking (:func:`_chunked`) never splits a mission, so a
    single mission larger than ``_SERVER_MAX_BATCH_SIZE`` becomes one oversized
    chunk that the server would reject at preflight. Catch it here, before the
    network round-trip, with an actionable message rather than an opaque
    server-side rejection (#2884).
    """
    for chunk in chunks:
        if len(chunk) > _SERVER_MAX_BATCH_SIZE:
            raise PreflightRejected(
                {
                    "error": (
                        f"a single mission is {len(chunk)} events, over the server's "
                        f"{_SERVER_MAX_BATCH_SIZE}-event batch cap; mission-atomic chunking "
                        "cannot split it. Import this mission on its own or trim its history."
                    )
                }
            )


# ── upload (stage 8) ──────────────────────────────────────────────────────────


@dataclass
class UploadReport:
    """Tally of per-event delivery outcomes for one import run.

    ``partial`` marks the distinct third state between success and total
    failure: a chunk failed mid-run, delivery stopped there, and
    ``undelivered_event_count`` events in later chunks were never attempted.
    ``delivered_through_chunk`` counts the chunks that were delivered cleanly
    before the stop.
    """

    success: int = 0
    duplicate: int = 0
    pending: int = 0
    rejected: int = 0
    rejected_samples: list[str] = field(default_factory=list)
    partial: bool = False
    delivered_through_chunk: int = 0
    undelivered_event_count: int = 0
    #: The run was refused locally before any network call because the project did
    #: not consent (FR-028). Distinct from ``rejected``, which is a server verdict:
    #: here nothing was transmitted, so there is nothing for the server to have
    #: judged. It counts into ``rejected`` as well, so ``ok`` is False and the
    #: caller's exit code is non-zero without needing to know about this field.
    refused: bool = False

    @property
    def total(self) -> int:
        return self.success + self.duplicate + self.pending + self.rejected

    @property
    def ok(self) -> bool:
        return self.pending == 0 and self.rejected == 0 and not self.partial


ConsentPredicate = Callable[[Sequence[str | None]], frozenset[str]]


def _refusal_report(envelopes: Sequence[Envelope], exc: Exception) -> UploadReport:
    """Turn a local consent refusal into a non-zero, self-explaining report.

    Not an exception escaping to the CLI, deliberately: ``_run_import_apply``
    catches five specific exception types, and a sixth would surface as a
    traceback. Routing the refusal through the report the command already renders
    gives the operator the reason, the project, and exit 1 — the US1a AS-1
    contract ("refuses, names the projects, exits non-zero without POSTing")
    without a second rendering path.
    """
    return UploadReport(
        rejected=len(envelopes),
        rejected_samples=[str(exc)],
        refused=True,
    )


def _missing_authority_error(
    envelopes: Sequence[Envelope],
    *,
    surface: str,
) -> HistoryTransportAuthorityError:
    projects = sorted({str(project) for project in (resolve_envelope_project(envelope) for envelope in envelopes) if project})
    named = ", ".join(projects) if projects else "<unresolvable project>"
    return HistoryTransportAuthorityError(f"{surface} refused for {named}: exact project context, target, and confirmed history capability are required")


def _consent_answer(
    envelopes: Sequence[Envelope],
    *,
    checkout_root: Path | None,
    consent_predicate: ConsentPredicate | None,
) -> ConsentAnswer:
    """Ask the one resolver about every project present in the stream.

    **The question is keyed on the data, not on a root.** Candidates are the
    ``project_uuid`` of each envelope about to be sent, resolved through the same
    three-site chain the refusal uses — not ``plan.identity.project_uuid`` and not
    ``checkout_root``. That matters because "consent answered by where the code is
    standing rather than by whose data is moving" is this mission's recurring
    defect (cwd, ``repo_root``, machine-global arming, daemon scope, a
    checkout-level grant — five substitutions, five leaks). Asking about what is
    actually on the wire also keeps a future ``synthesize`` bug that mixed two
    projects into one stream from being authorised by an identity nobody
    re-checked: it would be refused here.

    ``checkout_root`` is therefore a **lookup aid, never an authorization key**.
    It is offered to the resolver only as a level-1 root so the project's own
    committed ``.kittify/config.yaml`` can be read at all; ``consent.py``'s
    ``_project_local_votes`` discards any root whose declared uuid differs from
    the one being asked about. So a wrong root cannot widen the answer — it can
    only be ignored (falling through to the machine index, then to deny) or, if
    it is unreadable, contribute a fault, which denies. Both directions are
    fail-closed, which is what makes this safe without a locality precondition.

    What would falsify that, and should be re-checked if either changes: (a) if
    ``_project_local_votes`` ever stopped filtering on the declared uuid, an
    offered root would begin speaking for a project that is not its own; (b) if a
    caller ever passed several roots harvested from elsewhere on the machine
    rather than the one checkout being imported.
    """
    projects = [resolve_envelope_project(env) for env in envelopes]
    roots = [checkout_root] if checkout_root is not None else None
    return resolve_consent_answer(projects, consent_predicate=consent_predicate, checkout_roots=roots)


def _consented_batches(
    chunks: Sequence[Sequence[Envelope]],
    answer: ConsentAnswer,
) -> list[ConsentedBatch]:
    """Mint one batch per chunk, or raise :class:`UnconsentedDelivery`.

    This is the gate. It is not an ``if``: the batches it returns are the only
    values ``receiver.deliver`` accepts, so a future caller that skips this step
    has nothing to hand the receiver.
    """
    return [
        consented_batch(
            [OutboundEvent(event_id=str(env["event_id"]), payload=env) for env in chunk],
            answer=answer,
        )
        for chunk in chunks
    ]


def _canonical_event_json(envelope: Envelope) -> str:
    return json.dumps(dict(envelope), sort_keys=True, separators=(",", ":"))


def _assert_target_matches_context(
    context: ProjectSyncContext,
    target: DeliveryTarget,
) -> None:
    validate_project_sync_context_authority(context)
    audience = context.target_audience
    if audience is None or context.admission_state is not AdmissionState.ADMITTED or context.admission_generation is None or context.binding_audience is None:
        raise HistoryTransportAuthorityError("history disclosure requires a currently admitted project target")
    expected_target_id = compute_target_id(
        target_identity=target.target_identity,
        account_identity=target.account_identity,
        private_teamspace_id=target.private_teamspace_id,
        project_uuid=target.project_uuid,
        configuration_generation=target.configuration_generation,
    )
    expected = (
        context.project_uuid.storage_token,
        audience.target_identity,
        audience.account_identity,
        audience.private_teamspace_id,
        CanonicalProjectUUID.parse(audience.project_uuid).storage_token,
        audience.configuration_generation,
        str(context.admission_generation),
        context.binding_audience,
    )
    actual = (
        target.project_uuid.storage_token,
        target.target_identity,
        target.account_identity,
        target.private_teamspace_id,
        target.project_uuid.storage_token,
        target.configuration_generation,
        str(target.admission_generation),
        target.binding_audience,
    )
    if target.target_id != expected_target_id or target.admission_state is not AdmissionState.ADMITTED:
        raise HistoryTransportAuthorityError("history target is not the canonical admitted audience")
    if actual != expected:
        raise HistoryTransportAuthorityError("history target does not match the immutable project context")


def _origin(value: str) -> tuple[str, str, int | None]:
    parsed = urlsplit(canonicalize_url(value))
    return parsed.scheme.lower(), (parsed.hostname or "").lower(), parsed.port


def _assert_receiver_matches_target(
    receiver: DeliveryReceiver,
    target: DeliveryTarget,
) -> None:
    endpoint = getattr(receiver, "endpoint_url", None)
    try:
        matches = isinstance(endpoint, str) and _origin(endpoint) == _origin(target.target_identity)
    except ValueError:
        matches = False
    if not matches:
        raise HistoryTransportAuthorityError("history receiver endpoint does not match the admitted target")


def _assert_history_authority(
    envelopes: Sequence[Envelope],
    *,
    project_context: ProjectSyncContext,
    target: DeliveryTarget,
    history_capability: HistoryDisclosureCapability,
    server_url: str | None = None,
) -> None:
    """Revalidate the exact sealed cohort and target without retaining a UoW."""
    _assert_target_matches_context(project_context, target)
    project_uuid = project_context.project_uuid.storage_token
    if history_capability.project_uuid != project_uuid:
        raise HistoryTransportAuthorityError("history capability belongs to another project")
    if server_url is not None and canonicalize_url(server_url) != canonicalize_url(target.target_identity):
        raise HistoryTransportAuthorityError("history server URL does not match the admitted target")
    event_ids = tuple(str(envelope.get("event_id") or "") for envelope in envelopes)
    if event_ids != history_capability.row_ids:
        raise HistoryTransportAuthorityError("history envelopes do not equal the capability's exact ordered cohort")
    if any(resolve_envelope_project(envelope) != project_uuid for envelope in envelopes):
        raise HistoryTransportAuthorityError("history cohort contains an envelope from another project")

    store = ProjectSyncStore(project_uuid)
    with store.unit_of_work() as unit:
        try:
            revalidate_history_disclosure(unit, history_capability)
        except HistoryDisclosureError as exc:
            raise HistoryTransportAuthorityError(str(exc)) from exc
        placeholders = ", ".join("?" for _ in event_ids)
        query = (
            f"SELECT entry_id, payload_json FROM journal_entries WHERE project_uuid = ? AND entry_id IN ({placeholders}) "  # noqa: S608 - capability-count placeholders only
            "ORDER BY capture_sequence, entry_id"
        )
        rows = unit.execute(
            query,
            (project_uuid, *event_ids),
        ).fetchall()
    persisted = tuple((str(row[0]), str(row[1])) for row in rows)
    disclosed = tuple((str(envelope["event_id"]), _canonical_event_json(envelope)) for envelope in envelopes)
    if persisted != disclosed:
        raise HistoryTransportAuthorityError("history envelopes differ from the exact confirmed local rows")


def _event_payload_bytes(envelope: Envelope, *, sink: str) -> bytes:
    if sink == "history_upload":
        event = OutboundEvent(
            event_id=str(envelope["event_id"]),
            payload=envelope,
        )
        return disclosed_event_payload_bytes(event)
    return _canonical_request_bytes(dict(envelope))


def _history_disclosures(
    envelopes: Sequence[Envelope],
    *,
    sink: str,
    project_context: ProjectSyncContext,
    target: DeliveryTarget,
    history_capability: HistoryDisclosureCapability,
) -> list[ProjectTransportDisclosure]:
    epoch_id = project_context.epoch_id
    consent_generation = project_context.consent_generation
    if not isinstance(epoch_id, int) or not isinstance(consent_generation, int):
        raise HistoryTransportAuthorityError("history transport requires a current consenting project epoch")
    disclosures: list[ProjectTransportDisclosure] = []
    for envelope in envelopes:
        native_identity = str(envelope["event_id"])
        wire_event = _admission_bound_event(
            envelope,
            project_context=project_context,
        )
        disclosed_item: Mapping[str, Any]
        if sink == "history_preflight":
            disclosed_item = {
                "history_action_id": history_capability.action_id,
                "preview_hash": history_capability.preview_hash,
                "event": wire_event,
            }
        else:
            disclosed_item = wire_event
        disclosed_bytes = _event_payload_bytes(disclosed_item, sink=sink)
        payload_hash = (
            "sha256:"
            + hashlib.sha256(  # noqa: TID251 - exact wire disclosure digest
                disclosed_bytes
            ).hexdigest()
        )
        disclosures.append(
            ProjectTransportDisclosure(
                project_uuid=project_context.project_uuid.storage_token,
                epoch_id=epoch_id,
                consent_generation=consent_generation,
                target_identity=target.target_identity,
                account_identity=target.account_identity,
                private_teamspace_id=target.private_teamspace_id,
                target_project_uuid=target.project_uuid.storage_token,
                target_generation=target.configuration_generation,
                admission_generation=str(target.admission_generation),
                binding_audience=str(target.binding_audience),
                write_kind=sink,
                native_identity=native_identity,
                payload_hash=payload_hash,
                payload_reference=json.dumps(
                    {
                        "history_action_id": history_capability.action_id,
                        "preview_hash": history_capability.preview_hash,
                        "native_identity": native_identity,
                        "disclosed_sha256": payload_hash,
                        "sink": sink,
                        "target_id": target.target_id,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                attempt_id=f"{sink}:"
                + stable_transport_id(
                    history_capability.action_id,
                    target.target_id,
                    native_identity,
                    payload_hash,
                ),
                deadline_at=default_transport_deadline(),
                reconciliation_policy="native_identity_retry",
            )
        )
    return disclosures


def _preflight_classification(
    response: _PreflightResponse,
    disclosures: Sequence[ProjectTransportDisclosure],
) -> Mapping[str, tuple[str, str | None]]:
    if response.status_code == 200 and response.payload is not None:
        results = _correlated_preflight_results(response.payload)
        if results is None:
            # #3581/#3582: the deployed contract sends no results[] on a 200
            # accepted verdict. Record every preflighted event as DELIVERED so
            # the attempt ledger reaches a genuine terminal state -- leaving
            # it UNKNOWN would make a re-run crash trying to recover a
            # perpetually nonterminal attempt instead of replaying the
            # accepted verdict (_prior_preflight_response /
            # _exact_terminal_history require TERMINAL or ABSENT, never
            # NONTERMINAL). A non-accepted 200 with no results[] carries no
            # per-event information at all, so it stays UNKNOWN -- gracefully
            # inert, never a crash or a silently-dropped event.
            # #3722: PREFLIGHT_ACCEPTED, not DELIVERED. Terminal, so the
            # re-run recovery path above is unaffected, but it does not claim
            # the server is holding the event -- preflight is non-mutating and
            # the upload phase has not run yet. Recording it as DELIVERED made
            # a half-finished preflight read as a completed import.
            no_results_outcome = (
                TransportDeliveryOutcome.PREFLIGHT_ACCEPTED.value
                if response.accepted
                else TransportDeliveryOutcome.UNKNOWN.value
            )
            return {disclosure.attempt_id: (no_results_outcome, None) for disclosure in disclosures}
        mapped: dict[str, tuple[str, str | None]] = {}
        for disclosure in disclosures:
            result = results.get(disclosure.native_identity)
            if result is None:
                mapped[disclosure.attempt_id] = (
                    TransportDeliveryOutcome.UNKNOWN.value,
                    None,
                )
                continue
            status = str(result.get("status") or "").strip().lower()
            category = _canonical_preflight_error_category(result)
            outcome: tuple[str, str | None]
            if status == "success":
                # Still a preflight verdict, not a delivery (#3722).
                outcome = (TransportDeliveryOutcome.PREFLIGHT_ACCEPTED.value, None)
            elif status == "duplicate":
                outcome = (TransportDeliveryOutcome.DUPLICATE.value, None)
            elif status == "pending":
                outcome = (TransportDeliveryOutcome.PENDING.value, None)
            elif status == "rejected":
                outcome = (
                    TransportDeliveryOutcome.REFUSED.value,
                    category or "preflight_rejected",
                )
            else:
                outcome = (TransportDeliveryOutcome.UNKNOWN.value, None)
            mapped[disclosure.attempt_id] = outcome
        return mapped
    if response.status_code == 400:
        details = _preflight_error_details(response.payload)
        return {
            disclosure.attempt_id: (
                (TransportDeliveryOutcome.REFUSED.value if disclosure.native_identity in details else TransportDeliveryOutcome.RETRYABLE_NO_EFFECT.value),
                (
                    _canonical_preflight_error_category(details.get(disclosure.native_identity)) or "preflight_rejected"
                    if disclosure.native_identity in details
                    else None
                ),
            )
            for disclosure in disclosures
        }
    outcome = (TransportDeliveryOutcome.UNKNOWN.value, None)
    if response.status_code == 413:
        # The receiver authoritatively rejected this request without applying
        # any event. Keep the stable per-event attempts recoverable so WP10 can
        # retry a smaller chunk under the same native identities; terminalizing
        # here would make size recovery impossible.
        outcome = (TransportDeliveryOutcome.RETRYABLE_NO_EFFECT.value, None)
    return {disclosure.attempt_id: outcome for disclosure in disclosures}


def _canonical_preflight_error_category(
    payload: Mapping[str, Any] | None,
) -> str | None:
    if payload is None:
        return None
    for category_field in ("error_category", "category", "code"):
        category = payload.get(category_field)
        if isinstance(category, str) and category.strip():
            return category.strip().lower()
    return None


def _preflight_error_details(
    payload: Mapping[str, Any] | None,
) -> dict[str, Mapping[str, Any]]:
    if payload is None:
        return {}
    raw: object = payload.get("results", payload.get("details"))
    if isinstance(raw, str) and raw.strip():
        try:
            raw = json.loads(raw)
        except (TypeError, ValueError, json.JSONDecodeError):
            return {}
    if not isinstance(raw, list):
        return {}
    return {
        str(detail["event_id"]): detail
        for detail in raw
        if isinstance(detail, Mapping) and isinstance(detail.get("event_id"), str) and str(detail["event_id"]).strip()
    }


def _attempt_spec(
    disclosure: ProjectTransportDisclosure,
) -> DeliveryAttemptSpec:
    return DeliveryAttemptSpec(
        attempt_id=disclosure.attempt_id,
        write_kind=disclosure.write_kind,
        native_identity=disclosure.native_identity,
        payload_hash=disclosure.payload_hash,
        payload_reference=disclosure.payload_reference,
        deadline_at=disclosure.deadline_at,
        reconciliation_policy=disclosure.reconciliation_policy,
    )


def _exact_terminal_history(
    disclosures: Sequence[ProjectTransportDisclosure],
    *,
    target: DeliveryTarget,
) -> tuple[DeliveryTerminalResultProjection, ...] | None:
    """Project exact prior terminal truth, or ``None`` when every row is absent."""
    store = ProjectSyncStore(disclosures[0].project_uuid)
    try:
        with (
            acquire_project_transport_lease(store) as lease,
            lease.unit_of_work() as (unit, context),
        ):
            _assert_target_matches_context(context, target)
            projections = tuple(
                get_delivery_terminal_result_projection(
                    unit,
                    context,
                    _attempt_spec(disclosure),
                )
                for disclosure in disclosures
            )
    except (ProjectStoreError, TypeError, ValueError) as exc:
        raise HistoryTransportAuthorityError(f"history terminal result projection refused: {exc}") from exc
    statuses = {projection.status for projection in projections}
    if statuses == {DeliveryTerminalResultStatus.ABSENT}:
        return None
    if statuses != {DeliveryTerminalResultStatus.TERMINAL}:
        raise HistoryTransportAuthorityError("history terminal result cohort is mixed or nonterminal; recover the original attempts")
    return projections


def _prior_preflight_response(
    disclosures: Sequence[ProjectTransportDisclosure],
    *,
    target: DeliveryTarget,
) -> _PreflightResponse | None:
    projections = _exact_terminal_history(disclosures, target=target)
    if projections is None:
        return None
    results: list[dict[str, object]] = []
    for disclosure, projection in zip(disclosures, projections, strict=True):
        if projection.outcome in (
            TransportDeliveryOutcome.PREFLIGHT_ACCEPTED,
            # DELIVERED remains readable so ledgers written before #3722 still
            # replay rather than raising "nonterminal truth" on the first
            # re-run after upgrade.
            TransportDeliveryOutcome.DELIVERED,
        ):
            results.append({"event_id": disclosure.native_identity, "status": "success"})
        elif projection.outcome is TransportDeliveryOutcome.DUPLICATE:
            results.append({"event_id": disclosure.native_identity, "status": "duplicate"})
        elif projection.outcome is TransportDeliveryOutcome.REFUSED:
            results.append(
                {
                    "event_id": disclosure.native_identity,
                    "status": "rejected",
                    "error_category": projection.terminal_refusal_category or "preflight_rejected",
                    "retryable": False,
                }
            )
        else:
            raise HistoryTransportAuthorityError("history preflight terminal projection contains nonterminal truth")
    return _PreflightResponse(
        status_code=200,
        payload={"results": results, "terminal_history_replay": True},
        expected_event_ids=tuple(disclosure.native_identity for disclosure in disclosures),
    )


def _run_gated_preflight_chunk(
    chunk: Sequence[Envelope],
    *,
    all_envelopes: Sequence[Envelope],
    server_url: str,
    auth_token: str,
    poster: HttpPoster,
    project_context: ProjectSyncContext,
    target: DeliveryTarget,
    history_capability: HistoryDisclosureCapability,
    restart_attempts: bool = False,
) -> _PreflightResponse:
    disclosures = _history_disclosures(
        chunk,
        sink="history_preflight",
        project_context=project_context,
        target=target,
        history_capability=history_capability,
    )
    if not restart_attempts:
        prior = _prior_preflight_response(disclosures, target=target)
        if prior is not None:
            return prior

    def send() -> _PreflightResponse:
        # Revalidate the full confirmed cohort while the WP06 transport lease is
        # held, then close the UoW before bytes cross the network.
        _assert_history_authority(
            all_envelopes,
            project_context=project_context,
            target=target,
            history_capability=history_capability,
            server_url=server_url,
        )
        return _post_server_preflight(
            chunk,
            server_url=server_url,
            auth_token=auth_token,
            poster=poster,
            project_context=project_context,
            history_capability=history_capability,
        )

    result = execute_project_transport_batch(
        disclosures,
        send=send,
        classify=lambda value: _preflight_classification(
            value
            if isinstance(value, _PreflightResponse)
            else _PreflightResponse(
                0,
                None,
                "uncorrelated response",
                tuple(disclosure.native_identity for disclosure in disclosures),
            ),
            disclosures,
        ),
        restart_attempt_ids=(frozenset(disclosure.attempt_id for disclosure in disclosures) if restart_attempts else frozenset()),
    )
    if isinstance(result, ProjectTransportRefusal):
        raise HistoryTransportAuthorityError(f"{result.category}: {result.diagnostic}")
    if not isinstance(result, _PreflightResponse):
        raise HistoryTransportAuthorityError("history preflight returned an uncorrelated result")
    if result.status_code == 413 and len(chunk) > 1:
        midpoint = len(chunk) // 2
        for smaller_chunk in (chunk[:midpoint], chunk[midpoint:]):
            split_result = _run_gated_preflight_chunk(
                smaller_chunk,
                all_envelopes=all_envelopes,
                server_url=server_url,
                auth_token=auth_token,
                poster=poster,
                project_context=project_context,
                target=target,
                history_capability=history_capability,
                restart_attempts=True,
            )
            if not split_result.accepted:
                return split_result
        return _PreflightResponse(
            status_code=200,
            payload={
                "results": [{"event_id": str(envelope["event_id"]), "status": "success"} for envelope in chunk],
                "split_preflight": True,
            },
            expected_event_ids=tuple(str(envelope["event_id"]) for envelope in chunk),
        )
    return result


def _delivery_classification(
    value: object,
    disclosures: Sequence[ProjectTransportDisclosure],
) -> Mapping[str, tuple[str, str | None]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise TypeError("history receiver returned a non-sequence result")
    results = list(value)
    if any(not isinstance(result, DeliveryResult) for result in results):
        raise TypeError("history receiver returned a non-DeliveryResult value")
    expected = [disclosure.native_identity for disclosure in disclosures]
    actual = [result.event_id for result in results]
    if len(actual) != len(set(actual)) or set(actual) != set(expected):
        raise ValueError("history receiver result identities are not an exact bijection")
    by_id = {result.event_id: result for result in results}
    mapped: dict[str, tuple[str, str | None]] = {}
    for disclosure in disclosures:
        result = by_id[disclosure.native_identity]
        outcome: tuple[str, str | None]
        if result.outcome is DeliveryOutcome.SUCCESS:
            outcome = (TransportDeliveryOutcome.DELIVERED.value, None)
        elif result.outcome is DeliveryOutcome.DUPLICATE:
            outcome = (TransportDeliveryOutcome.DUPLICATE.value, None)
        elif result.outcome is DeliveryOutcome.TERMINAL_FAILED:
            category = None
            if isinstance(result.raw, Mapping):
                category = _canonical_preflight_error_category(result.raw)
            outcome = (
                TransportDeliveryOutcome.REFUSED.value,
                category or "history_upload_terminal_refusal",
            )
        elif result.outcome in {DeliveryOutcome.PENDING, DeliveryOutcome.REJECTED}:
            if result.effect_certainty is DeliveryEffectCertainty.KNOWN_NO_EFFECT:
                outcome = (TransportDeliveryOutcome.RETRYABLE_NO_EFFECT.value, None)
            elif result.effect_certainty is DeliveryEffectCertainty.ACCEPTED_PENDING:
                outcome = (TransportDeliveryOutcome.PENDING.value, None)
            else:
                outcome = (TransportDeliveryOutcome.UNKNOWN.value, None)
        else:
            outcome = (TransportDeliveryOutcome.UNKNOWN.value, None)
        mapped[disclosure.attempt_id] = outcome
    return mapped


def _prior_upload_results(
    disclosures: Sequence[ProjectTransportDisclosure],
    *,
    target: DeliveryTarget,
) -> list[DeliveryResult] | None:
    projections = _exact_terminal_history(disclosures, target=target)
    if projections is None:
        return None
    outcomes = {projection.outcome for projection in projections}
    if not outcomes <= {
        TransportDeliveryOutcome.DELIVERED,
        TransportDeliveryOutcome.DUPLICATE,
    }:
        categories = sorted(
            {
                projection.terminal_refusal_category or (projection.outcome.value if projection.outcome is not None else "missing_outcome")
                for projection in projections
            }
        )
        raise HistoryTransportAuthorityError("history upload terminal result is not replayable: " + ", ".join(categories))
    return [
        DeliveryResult(
            event_id=disclosure.native_identity,
            outcome=(DeliveryOutcome.SUCCESS if projection.outcome is TransportDeliveryOutcome.DELIVERED else DeliveryOutcome.DUPLICATE),
            effect_certainty=DeliveryEffectCertainty.TERMINAL,
            raw={"terminal_history_replay": True},
        )
        for disclosure, projection in zip(disclosures, projections, strict=True)
    ]


def upload_envelopes(
    envelopes: Sequence[Envelope],
    *,
    receiver: DeliveryReceiver,
    chunk_size: int = _IMPORT_CHUNK_SIZE,
    checkout_root: Path | None = None,
    consent_predicate: ConsentPredicate | None = None,
    project_context: ProjectSyncContext | None = None,
    target: DeliveryTarget | None = None,
    history_capability: HistoryDisclosureCapability | None = None,
) -> UploadReport:
    """Chunk the stream (mission-atomically) and deliver, stopping on failure.

    Same delivery semantics as :func:`run_import_upload` minus the preflight:
    the first chunk with a failure outcome halts the run and the report records
    the partial state. Consent is resolved and the batches minted before the
    first chunk is handed to the receiver (FR-028).
    """
    if not envelopes:
        return UploadReport()
    if project_context is None or target is None or history_capability is None:
        return _refusal_report(
            envelopes,
            _missing_authority_error(envelopes, surface="history upload"),
        )
    try:
        _assert_receiver_matches_target(receiver, target)
        _assert_history_authority(
            envelopes,
            project_context=project_context,
            target=target,
            history_capability=history_capability,
        )
    except HistoryTransportAuthorityError as exc:
        return _refusal_report(envelopes, exc)
    chunks = list(_chunked(envelopes, chunk_size))
    _assert_batches_within_cap(chunks)
    answer = _consent_answer(envelopes, checkout_root=checkout_root, consent_predicate=consent_predicate)
    try:
        batches = _consented_batches(chunks, answer)
    except UnconsentedDelivery as exc:
        return _refusal_report(envelopes, exc)
    report = UploadReport()
    _deliver_chunks(
        batches,
        receiver,
        report,
        all_envelopes=envelopes,
        project_context=project_context,
        target=target,
        history_capability=history_capability,
    )
    return report


def run_import_upload(
    envelopes: Sequence[Envelope],
    *,
    receiver: DeliveryReceiver,
    server_url: str,
    auth_token: str,
    poster: HttpPoster = default_http_poster,
    chunk_size: int = _IMPORT_CHUNK_SIZE,
    checkout_root: Path | None = None,
    consent_predicate: ConsentPredicate | None = None,
    project_context: ProjectSyncContext | None = None,
    target: DeliveryTarget | None = None,
    history_capability: HistoryDisclosureCapability | None = None,
) -> UploadReport:
    """Preflight every chunk, then (only if all pass) upload chunks in order.

    Preflighting the whole stream before delivering anything is the fail-closed
    ordering: a **preflight** rejection in any chunk raises
    :class:`PreflightRejected` and nothing is uploaded (INV-6).

    A mid-upload *delivery* failure (after preflight passes) stops the run at
    the failed chunk — later chunks are never attempted, and the report records
    the partial state (``partial`` / ``delivered_through_chunk`` /
    ``undelivered_event_count``). The partial is safe: chunks are
    mission-atomic and carry monotonic per-mission Lamport clocks, so any
    delivered prefix is a valid ordered prefix of whole missions (a
    WPStatusChanged never lands before its WPCreated), never an orphan — and a
    retry uses the same durable attempt/native identity. If that attempt already
    has a terminal result, the canonical recovery API must project it; this
    adapter never creates a fresh attempt to force another request.
    """
    if not envelopes:
        return UploadReport()
    if project_context is None or target is None or history_capability is None:
        return _refusal_report(
            envelopes,
            _missing_authority_error(envelopes, surface="history import"),
        )
    try:
        _assert_receiver_matches_target(receiver, target)
        _assert_history_authority(
            envelopes,
            project_context=project_context,
            target=target,
            history_capability=history_capability,
            server_url=server_url,
        )
    except HistoryTransportAuthorityError as exc:
        return _refusal_report(envelopes, exc)
    chunks = list(_chunked(envelopes, chunk_size))
    _assert_batches_within_cap(chunks)
    # The consent gate runs BEFORE the preflight. ``run_server_preflight`` POSTs
    # the full envelope stream — mission slugs, project slug, payloads — so it is
    # a sink in its own right, and gating only the ``receiver.deliver`` call would
    # have left the leak intact while looking closed (E1's entry in the egress
    # inventory names the delivery line; the preflight line is the same breach).
    answer = _consent_answer(envelopes, checkout_root=checkout_root, consent_predicate=consent_predicate)
    try:
        batches = _consented_batches(chunks, answer)
    except UnconsentedDelivery as exc:
        return _refusal_report(envelopes, exc)
    for chunk in chunks:
        try:
            response = _run_gated_preflight_chunk(
                chunk,
                all_envelopes=envelopes,
                server_url=server_url,
                auth_token=auth_token,
                poster=poster,
                project_context=project_context,
                target=target,
                history_capability=history_capability,
            )
        except HistoryTransportAuthorityError as exc:
            return _refusal_report(envelopes, exc)
        except requests.RequestException as exc:
            raise PreflightRejected({"error": f"preflight transport failed: {exc}"}) from exc
        if not response.accepted:
            raise PreflightRejected(response.payload or {"error": response.error or "preflight rejected"})
    report = UploadReport()
    _deliver_chunks(
        batches,
        receiver,
        report,
        all_envelopes=envelopes,
        project_context=project_context,
        target=target,
        history_capability=history_capability,
    )
    return report


# ── internals ─────────────────────────────────────────────────────────────────


def _deliver_chunks(
    batches: Sequence[ConsentedBatch],
    receiver: DeliveryReceiver,
    report: UploadReport,
    *,
    all_envelopes: Sequence[Envelope],
    project_context: ProjectSyncContext,
    target: DeliveryTarget,
    history_capability: HistoryDisclosureCapability,
) -> None:
    """Deliver chunks in order, stopping at the first chunk with a failure.

    A chunk whose delivery reports any outcome outside {success, duplicate,
    pending} — i.e. REJECTED / TERMINAL_FAILED / TRANSIENT — halts the run:
    subsequent chunks are never attempted and the report records the partial
    state. Everything delivered before the stop is a valid ordered prefix of
    whole missions (mission-atomic chunks, monotonic Lamport clocks), and a
    re-run resumes idempotently (the server dedups on ``event_id``).
    """
    for index, batch in enumerate(batches):
        events = list(batch)
        wire_events = [
            OutboundEvent(
                event_id=event.event_id,
                payload=_admission_bound_event(
                    event.payload,
                    project_context=project_context,
                ),
            )
            for event in events
        ]
        wire_batch = consented_batch(
            wire_events,
            answer=batch.answer,
            event_projects=batch.event_projects,
        )
        disclosures = _history_disclosures(
            [event.payload for event in events],
            sink="history_upload",
            project_context=project_context,
            target=target,
            history_capability=history_capability,
        )

        def send(
            current_batch: ConsentedBatch = batch,
            current_wire_batch: ConsentedBatch = wire_batch,
        ) -> Sequence[DeliveryResult]:
            _assert_history_authority(
                all_envelopes,
                project_context=project_context,
                target=target,
                history_capability=history_capability,
            )
            del current_batch
            return receiver.deliver(current_wire_batch)

        def classify(
            value: object,
            current_disclosures: tuple[ProjectTransportDisclosure, ...] = tuple(disclosures),
        ) -> Mapping[str, tuple[str, str | None]]:
            return _delivery_classification(value, current_disclosures)

        failures_before = report.rejected
        try:
            prior_results = _prior_upload_results(disclosures, target=target)
        except HistoryTransportAuthorityError as exc:
            report.rejected += len(events)
            report.refused = True
            report.rejected_samples.append(str(exc))
            report.delivered_through_chunk = index
            report.undelivered_event_count = sum(len(later) for later in batches[index + 1 :])
            report.partial = report.undelivered_event_count > 0
            return
        result_value: object = (
            prior_results
            if prior_results is not None
            else execute_project_transport_batch(
                disclosures,
                send=send,
                classify=classify,
            )
        )
        if isinstance(result_value, ProjectTransportRefusal):
            refused = HistoryTransportAuthorityError(f"{result_value.category}: {result_value.diagnostic}")
            report.rejected += len(events)
            report.refused = True
            report.rejected_samples.append(str(refused))
            report.delivered_through_chunk = index
            report.undelivered_event_count = sum(len(later) for later in batches[index + 1 :])
            report.partial = report.undelivered_event_count > 0
            return
        if not isinstance(result_value, Sequence) or isinstance(result_value, (str, bytes)):
            raise TypeError("history receiver returned an uncorrelated result")
        for result in result_value:
            if not isinstance(result, DeliveryResult):
                raise TypeError("history receiver returned a non-DeliveryResult value")
            _tally(report, result)
        if report.rejected > failures_before:
            report.delivered_through_chunk = index
            report.undelivered_event_count = sum(len(later) for later in batches[index + 1 :])
            report.partial = report.undelivered_event_count > 0
            return
        report.delivered_through_chunk = index + 1


def _tally(report: UploadReport, result: DeliveryResult) -> None:
    if result.outcome is DeliveryOutcome.SUCCESS:
        report.success += 1
    elif result.outcome is DeliveryOutcome.DUPLICATE:
        report.duplicate += 1
    elif result.outcome is DeliveryOutcome.PENDING:
        report.pending += 1
    else:  # REJECTED / TERMINAL_FAILED / TRANSIENT
        report.rejected += 1
        if len(report.rejected_samples) < _MAX_REJECTED_SAMPLES:
            report.rejected_samples.append(f"{result.event_id}: {result.error or result.outcome.value}")


def _chunked(items: Sequence[Envelope], size: int) -> Iterator[Sequence[Envelope]]:
    """Mission-atomic chunking: pack whole missions into chunks of ≤ *size* envelopes.

    The ordered stream is grouped into contiguous mission units — each unit
    starts at a ``MissionCreated`` and carries that mission's ``WPCreated[]`` +
    ``WPStatusChanged[]``; envelopes arriving before the first
    ``MissionCreated`` (synthetic/legacy streams) are singleton units. Units
    are packed greedily up to the *size* budget and a unit is NEVER split: a
    single mission larger than *size* becomes its own oversized chunk, which
    the server still accepts (``_SERVER_MAX_BATCH_SIZE`` = 1000 events/batch
    vs our conservative 500 budget).

    Recorded assumption, verified server-side: SaaS ``/events/preflight/``
    (apps/sync/views.py::preflight_sync_events →
    apps/sync/cutover_contract.py::_validate_event_batch) validates each
    envelope in isolation — schema/shape only, no cross-event
    referential-completeness check — so chunk boundaries are not
    correctness-bearing for preflight; mission-atomic chunking is
    defense-in-depth for delivery-prefix semantics.
    """
    chunk: list[Envelope] = []
    for unit in _mission_units(items):
        if chunk and len(chunk) + len(unit) > size:
            yield chunk
            chunk = []
        chunk.extend(unit)
    if chunk:
        yield chunk


def _mission_units(items: Sequence[Envelope]) -> Iterator[list[Envelope]]:
    """Group the ordered stream into contiguous per-mission units.

    A unit opens at each ``MissionCreated`` and absorbs every envelope up to
    the next one. Envelopes before the first ``MissionCreated`` have no mission
    prefix to stay atomic with, so each is its own singleton unit (this also
    preserves plain size-based packing for prefix-less synthetic streams).
    """
    unit: list[Envelope] = []
    for env in items:
        if env.get("event_type") == MISSION_CREATED:
            if unit:
                yield unit
            unit = [env]
        elif unit:
            unit.append(env)
        else:
            yield [env]
    if unit:
        yield unit
