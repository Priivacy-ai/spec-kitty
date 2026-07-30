"""Mint :class:`ConsentedBatch` values in tests, through the real factory (#3030 FR-028).

``DeliveryReceiver.deliver`` takes a ``ConsentedBatch``, never a bare sequence, so
every test that drives a receiver has to obtain a consent answer first. That is the
point of the type, and this module deliberately does **not** offer a back door
around it: there is no "make me a batch without an answer" helper here, because a
helper like that — importable, convenient, one line — is exactly how a type stops
being a control and becomes documentation.

What it offers instead is the same seam production uses: an explicit
``consent_predicate``. :func:`granting` runs the real
:func:`~specify_cli.delivery.consent_gate.resolve_consent_answer` with a predicate
that says yes, so a test that wants a delivery to happen has to *say so* in one
readable call rather than inherit it from a default.

Tests that care about the consent decision itself (``tests/sync/test_history_import_consent_3030.py``,
``tests/delivery/test_dispatch_project_consent_3030.py``) use the real chain and
must not use this module.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from specify_cli.delivery.consent_gate import (
    ConsentAnswer,
    ConsentedBatch,
    consented_batch,
    resolve_consent_answer,
    resolve_envelope_project,
)
from specify_cli.delivery.receivers import OutboundEvent

#: The project a test event belongs to when its envelope carries no identity.
#: A real uuid shape rather than a sentinel, because ``consented_project_uuids``
#: normalises and a nil/blank value is *unresolvable identity*, not a project.
FIXTURE_PROJECT_UUID = "00000000-0000-4000-8000-00000000f1c7"


def _grant_all(candidates: Sequence[str | None]) -> frozenset[str]:
    """A predicate that consents to every identifiable candidate."""
    return frozenset(str(candidate) for candidate in candidates if candidate)


def granting(*project_uuids: str) -> ConsentAnswer:
    """A real answer that grants *project_uuids* — the test's explicit "yes"."""
    return resolve_consent_answer(list(project_uuids), consent_predicate=_grant_all)


def deliverable(
    events: Sequence[OutboundEvent],
    *,
    project_uuid: str = FIXTURE_PROJECT_UUID,
    event_projects: Mapping[str, str | None] | None = None,
) -> ConsentedBatch:
    """Mint a batch for *events*, granting whatever projects they belong to.

    Attribution follows the envelope when it carries identity (so a test that
    builds a cross-project batch keeps its two distinct projects and still meets
    ``_cross_project_refusal``), and falls back to *project_uuid* for the many
    fixtures whose envelopes carry none.
    """
    if event_projects is None:
        event_projects = {
            event.event_id: resolve_envelope_project(event.payload) or project_uuid for event in events
        }
    answer = granting(*{uuid for uuid in event_projects.values() if uuid})
    return consented_batch(events, answer=answer, event_projects=event_projects)
