"""The Zeitgeist moment handler at the status fan-out seam (E3, EXPERIMENTAL-spec-kitty#8).

One fire-and-forget ``event.publish`` per status moment, replacing the sync
package's import-time registration as the default occupant of the
``status/adapters.py`` fan-out slots. The design page
(``ephemeral-team-status.html``, CLI column) pins the shape: build the volatile
event via ``spec_kitty_events``, resolve credentials for ``(team, repo)``, then
``ZeitgeistClient.offer("event.publish", ...)`` inside the client's own 750 ms
budget — no retry, no queue, no daemon. ``emit.py`` is untouched; the handlers
are registered into the existing slots by
:func:`specify_cli.status.adapters.ensure_zeitgeist_moment_handlers`.

Three slots, one broadcast core:

* ``fire_saas_fanout`` (WP lane transitions) → ``WPStatusChanged``;
* ``fire_lifecycle_saas_fanout`` (mission lifecycle log) → the volatile subset
  of that log's event types. Today that is exactly ``MissionCreated``: no
  local producer emits ``MissionClosed`` or ``PhaseEntered`` (their only
  producers live in the doomed sync package), and this bridge adds none — the
  same code path carries them the moment a producer exists.
* ``fire_resolved_binding_fanout`` → nothing yet: ``WPResolvedBindingChanged``
  is not part of the volatile vocabulary
  (:data:`spec_kitty_events.zeitgeist_attrs.VOLATILE_EVENT_TYPES`), and
  inventing attrs for it here would put vocabulary where the design says it
  cannot live ("The vocabulary … lives only in spec-kitty-events"). The slot
  is wired anyway, so the moment spec-kitty-events ships a codec for it the
  relay carries binding changes with no further seam work.

Who is on a mission-level moment: the relay attests the actor from the
capability credential (the frame's ``actor.user``), and the payload's own
optional ``actor`` rides alongside as an attr when the producer set one —
``emit_mission_created_local`` resolves git ``user.email`` → ``"cli"`` at
emit time (#75), so ``MissionCreated`` carries its WHO. This bridge never
fabricates an actor either way.

Every failure is environmental and every one of them resolves to a logged drop:
the moment is simply lost — by design (design page, "How long anything lives").
Nothing here ever raises into the fan-out, so canonical local persistence is
untouched regardless of relay, credential, or codec state.
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any
from collections.abc import Mapping

from kernel.clock import datetime, now_utc, parse_iso
from pydantic import BaseModel, ValidationError

from spec_kitty_events.models import Event
from spec_kitty_events.status import StatusTransitionPayload
from spec_kitty_events.zeitgeist_attrs import (
    PAYLOAD_MODEL_BY_EVENT_TYPE,
    VOLATILE_EVENT_TYPES,
    ZeitgeistAttrsError,
    to_zeitgeist_attrs,
    zeitgeist_ref_for,
)

from .migrate_lifecycle_envelope import _generate_node_id  # noqa: PLC2701 -- same-package reuse, not a public API

if TYPE_CHECKING:
    from specify_cli.zeitgeist_client.credentials import StoredCredential

logger = logging.getLogger(__name__)

#: What presents itself to the relay in ``ClientConfig.harness``.
_HARNESS_ID = "spec-kitty-cli"

#: The op this handler offers, and the only one it needs a grant for: the
#: capability mint rides the ``presence`` kind, which zeitgeist grants both
#: ``presence.publish`` and ``event.publish`` (zeitgeist ``managed_auth.py``).
_EVENT_PUBLISH_OP = "event.publish"

# Per-process session identity for offered moments. The relay derives an opaque
# ``session_ref`` from it (the raw id never reaches a rendered surface), and
# moments carry no liveness semantics, so a fresh id per process groups this
# process's moments without pretending to be a long-lived session.
_SESSION_ID = str(uuid.uuid4())


def saas_moment_handler(**kwargs: Any) -> None:
    """Broadcast one WP lane transition as a ``WPStatusChanged`` moment."""
    try:
        _broadcast_status_transition(kwargs)
    except Exception:
        logger.warning(
            "Zeitgeist moment handler failed; canonical status log unaffected",
            exc_info=True,
        )


def lifecycle_moment_handler(**kwargs: Any) -> None:
    """Broadcast one volatile mission-lifecycle moment from the local log envelope."""
    try:
        _broadcast_lifecycle_envelope(kwargs)
    except Exception:
        logger.warning(
            "Zeitgeist lifecycle moment handler failed; canonical lifecycle log unaffected",
            exc_info=True,
        )


def resolved_binding_moment_handler(**kwargs: Any) -> None:
    """Slot wiring for ``WPResolvedBindingChanged`` — no broadcast until a codec exists."""
    logger.debug(
        "Zeitgeist: WPResolvedBindingChanged (wp_id=%s) is not a volatile-family moment; nothing broadcast",
        kwargs.get("wp_id"),
    )


def _broadcast_status_transition(kwargs: Mapping[str, Any]) -> None:
    """Build the ``WPStatusChanged`` payload/envelope pair and offer it once.

    ``metadata`` is duck-typed (the CORE ``WPStatusChangeMetadata`` params
    object) rather than imported, so this module stays decoupled from the
    producer's params type.
    """
    metadata = kwargs.get("metadata")
    mission_slug = kwargs.get("mission_slug")
    evidence = _normalise_evidence(getattr(metadata, "evidence", None))

    # Validated through the model's own schema (like the lifecycle path below):
    # a transition whose fan-out kwargs cannot form a payload is a dropped
    # moment with a logged reason, never a raised error into the seam.
    try:
        payload = StatusTransitionPayload.model_validate(
            {
                "mission_slug": mission_slug,
                "wp_id": kwargs.get("wp_id"),
                "from_lane": kwargs.get("from_lane"),
                "to_lane": kwargs.get("to_lane"),
                "actor": kwargs.get("actor"),
                "force": bool(getattr(metadata, "force", False)),
                "reason": getattr(metadata, "reason", None),
                "execution_mode": getattr(metadata, "execution_mode", None),
                "review_ref": getattr(metadata, "review_ref", None),
                "evidence": evidence,
            }
        )
    except ValidationError as exc:
        logger.warning("Zeitgeist moment WPStatusChanged not broadcast: %s", exc)
        return

    event_id = str(getattr(metadata, "causation_id", None) or uuid.uuid4())
    envelope = Event(
        event_id=event_id,
        event_type="WPStatusChanged",
        aggregate_id=str(mission_slug or kwargs.get("wp_id") or "work-package"),
        payload=payload.model_dump(mode="json"),
        timestamp=_parse_stamp(getattr(metadata, "occurred_at", None)),
        **_envelope_bookkeeping(mission_key=mission_slug or kwargs.get("wp_id"), event_id=event_id),
    )
    # No checkout directory rides these kwargs (emit.py hands the fan-out its
    # event facts only), so credential resolution runs against the process
    # working directory — where every CLI invocation already sits.
    _broadcast_moment(payload, envelope, cwd=Path.cwd())


def _broadcast_lifecycle_envelope(kwargs: Mapping[str, Any]) -> None:
    """Build the volatile moment carried by one local lifecycle-log envelope.

    Non-volatile lifecycle types (``SpecifyStarted`` &c.) are logged and
    skipped: they are not part of the ephemeral vocabulary, and fabricating
    attrs for them is exactly what the design forbids.
    """
    envelope_dict = kwargs.get("envelope")
    if not isinstance(envelope_dict, Mapping):
        return
    event_type = envelope_dict.get("event_type")
    if event_type not in VOLATILE_EVENT_TYPES:
        logger.debug(
            "Zeitgeist: lifecycle event %r is not a volatile-family moment; nothing broadcast",
            event_type,
        )
        return

    model = PAYLOAD_MODEL_BY_EVENT_TYPE[event_type]
    try:
        payload = model.model_validate(dict(envelope_dict.get("payload") or {}))
    except ValidationError as exc:
        logger.warning("Zeitgeist moment %s not broadcast: %s", event_type, exc)
        return

    event_id = str(envelope_dict.get("event_id") or uuid.uuid4())
    aggregate_id = str(envelope_dict.get("aggregate_id") or getattr(payload, "mission_slug", None) or event_type)
    envelope = Event(
        event_id=event_id,
        event_type=event_type,
        aggregate_id=aggregate_id,
        payload=payload.model_dump(mode="json"),
        timestamp=_parse_stamp(envelope_dict.get("timestamp")),
        schema_version=str(envelope_dict.get("schema_version") or "3.0.0"),
        **_envelope_bookkeeping(
            mission_key=aggregate_id,
            event_id=event_id,
            project_uuid=envelope_dict.get("project_uuid"),
        ),
    )
    # The append site passes the log path: the mission dir names the checkout
    # the moment was produced in, which beats the process working directory.
    log_path = kwargs.get("log_path")
    _broadcast_moment(payload, envelope, cwd=log_path.parent if isinstance(log_path, Path) else Path.cwd())


def _normalise_evidence(evidence: Any) -> Any:
    """Make a local done-evidence bundle validate against the canonical model.

    The local journal treats ``repos`` as optional and omits empty
    (``DoneEvidence.to_dict``), while ``spec_kitty_events.DoneEvidence``
    requires at least one entry — and its transition validator requires
    evidence to be *present* for approved/done lanes, so a review-only done
    transition would otherwise die in payload validation and never reach the
    relay. When repos are missing, fill them with this checkout's identity the
    way ``sync/emitter.py``'s emitter always has (its own fallback is the
    literal "local"/"unknown" triple when git cannot answer). Nothing here
    reaches the wire: evidence is in ``UNBROADCAST_FIELDS``, so attrs never
    carry it; this exists purely so review-only done moments broadcast.
    """
    if not isinstance(evidence, Mapping) or not evidence:
        return evidence
    if evidence.get("repos"):
        return evidence
    return {
        **evidence,
        "repos": [{"repo": "local", "branch": "unknown", "commit": "unknown"}],
    }


def _broadcast_moment(payload: BaseModel, envelope: Event, *, cwd: Path) -> None:
    """Project one volatile payload onto bounded attrs and offer it exactly once.

    Order matters: the codec runs first and credential resolution second, so an
    over-bound payload or an unresolvable credential costs zero network
    attempts — the relay's request log stays empty unless a well-formed moment
    has somewhere to go.
    """
    event_type = envelope.event_type
    try:
        # The offer attrs are exactly what the codec returns: the wire
        # vocabulary has a single owner (spec_kitty_events.zeitgeist_attrs),
        # so what stays local — ``reason``/``evidence`` prose, unencodable
        # shapes — is decided there and only there.
        attrs = to_zeitgeist_attrs(payload, envelope)
        ref = zeitgeist_ref_for(event_type, payload)
    except ZeitgeistAttrsError as exc:
        logger.warning("Zeitgeist moment %s not broadcast: %s", event_type, exc)
        return

    credential = _resolve_credentials(cwd)
    if credential is None:
        # Not admitted anywhere / nothing configured / Team Kitty unreachable:
        # the MVP's "a repo no team admitted produces nothing anywhere".
        logger.debug("Zeitgeist moment %s not broadcast: no relay credentials", event_type)
        return

    # EventArgs requires session_id on every event frame (the relay derives the
    # actor's opaque session_ref from it); kind/attrs are required too, ref is
    # optional and omitted when the family declares no aggregate field.
    offer_args: dict[str, Any] = {"session_id": _SESSION_ID, "kind": event_type, "attrs": attrs}
    if ref:
        offer_args["ref"] = ref
    _offer_and_log(credential, event_type, offer_args)


def _offer_and_log(credential: StoredCredential, event_type: str, offer_args: Mapping[str, Any]) -> None:
    """One bounded offer through the typed client, with the outcome logged.

    Imported here, not at module level: the resolution/transport chains pull
    httpx and the urllib machinery, none of which the status package should
    pay for at import time (every CLI start imports this package).
    """
    from specify_cli.zeitgeist_client.transport import ClientConfig, OfferOutcome, ZeitgeistClient  # noqa: PLC0415

    client = ZeitgeistClient(
        ClientConfig(
            relay_url=credential.relay_url,
            token=credential.token,
            harness=_HARNESS_ID,
            session_id=_SESSION_ID,
            agent_id=None,
            # ``repo``/``branch`` feed only the presence/focus ops this handler
            # never sends; filling them would cost a git probe per transition
            # for values no event.publish arg reads.
            repo="",
            branch="",
            capability_credential=credential.capability_credential,
        )
    )
    result = client.offer(_EVENT_PUBLISH_OP, dict(offer_args))
    if result.outcome is OfferOutcome.SENT:
        logger.debug(
            "Zeitgeist moment %s offered (%s) in %.0f ms",
            event_type,
            result.request_id,
            result.elapsed_s * 1000,
        )
    elif result.outcome is OfferOutcome.THROTTLED:
        # Still 429 after the one honoured Retry-After (#180). The human-facing
        # signal — the one-line "relay throttled; moment dropped" stderr notice
        # — has already been emitted by the client itself; logging it again at
        # warning level would print the loss twice, so this stays a debug-level
        # structured record (which moment, which request id, how long).
        logger.debug(
            "Zeitgeist moment %s throttled after its retry (%s) in %.0f ms; dropped",
            event_type,
            result.request_id,
            result.elapsed_s * 1000,
        )
    else:
        # rejected / dropped_budget / dropped_unreachable / refused_local: one
        # attempt was made (or refused before any socket) and there is no
        # retry, no queue — the moment is lost by design, so say so once.
        logger.warning(
            "Zeitgeist moment %s dropped (%s) after %.0f ms; no retry by design",
            event_type,
            result.outcome.value,
            result.elapsed_s * 1000,
        )


def _resolve_credentials(cwd: Path) -> StoredCredential | None:
    """Credentials for this checkout's team relay, or ``None`` to stay silent.

    Delegates entirely to E3's resolver (#9): cached store answer, else one
    admission pre-flight + capability mint against Team Kitty, else a stored
    negative answer. Every way it can fail resolves to ``None`` plus its own
    debug log — none of them raise here.
    """
    from specify_cli.zeitgeist_client.resolution import resolve_credentials  # noqa: PLC0415

    return resolve_credentials(cwd)


def _parse_stamp(raw: Any) -> datetime:
    """Producer occurrence time as a datetime, falling back to now.

    A missing/unparseable stamp must not drop the moment: the envelope's
    ``timestamp`` becomes the ``occurred_at`` attr, and a stamp we cannot read
    is replaced by the emission clock rather than losing the broadcast (Rule
    R-T-01 preserves *real* producer stamps end-to-end; this only covers their
    absence).
    """
    if isinstance(raw, str) and raw.strip():
        try:
            return parse_iso(raw)
        except (ValueError, TypeError):
            logger.debug("Zeitgeist: unparseable occurrence stamp %r; using emission clock", raw)
    return now_utc()


def _envelope_bookkeeping(*, mission_key: Any, event_id: str, project_uuid: Any = None) -> dict[str, Any]:
    """Synthesize the strict envelope's causal keys that moments do not carry.

    The attrs codec reads exactly ``event_id``/``timestamp``/``event_type`` off
    the envelope; the strict ``Event`` model still requires the causal keys, so
    they are synthesized deterministically and never reach the wire:

    * ``node_id`` — the repo-standard machine identity (hostname:user hash);
    * ``lamport_clock`` — ``0``, the "no causal order recorded" sentinel the
      local lifecycle journal already uses;
    * ``project_uuid``/``build_id`` — the real project UUID when the lifecycle
      log recorded one, else a deterministic UUID5 of the mission key, with
      ``build_id`` derived from it exactly as
      :func:`specify_cli.identity.project.derive_build_id` does elsewhere;
    * ``correlation_id`` — the moment's own ``event_id`` (the repo's standard
      root-event convention); ``causation_id`` stays ``None``.
    """
    from specify_cli.identity.project import derive_build_id  # noqa: PLC0415

    node_id = _generate_node_id()
    resolved_uuid = _coerce_uuid(project_uuid) or uuid.uuid5(uuid.NAMESPACE_URL, f"urn:spec-kitty:mission:{mission_key}")
    return {
        "node_id": node_id,
        "lamport_clock": 0,
        "project_uuid": resolved_uuid,
        "build_id": derive_build_id(resolved_uuid, node_id),
        "correlation_id": event_id,
        "causation_id": None,
    }


def _coerce_uuid(raw: Any) -> uuid.UUID | None:
    if isinstance(raw, uuid.UUID):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            return uuid.UUID(raw)
        except ValueError:
            logger.debug("Zeitgeist: unparseable project_uuid %r; synthesizing", raw)
    return None


__all__ = [
    "lifecycle_moment_handler",
    "resolved_binding_moment_handler",
    "saas_moment_handler",
]
