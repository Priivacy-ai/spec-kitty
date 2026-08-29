"""M1 successor: capture answers to the *event's* project store, never to cwd.

The defect this file pinned — ``EventEmitter._capture_gate_state`` resolving
consent against ``Path.cwd()`` while the row was stamped with the emitter's cached
identity — is closed structurally by the per-project store migration: capture now
selects the physical store from the event's own ``project_uuid``
(``_queue_event_locally``), so cwd can neither authorize, deny, nor *misplace* a
row. Two premises of the original tests changed with it, deliberately:

* **Capture is no longer consent-gated.** Local capture is the unconditional
  durable outbox (FR-006 / issue #1072): a non-consenting project's event is
  written into that project's *own* store, where it is not a leak — consent gates
  egress, and C-002 forbids destroying local history on refusal. The old
  "capture refuses without consent" direction is therefore migrated to "capture
  lands in the event's own store and the project stays egress-ineligible".
* **Checkout files and the machine index are diagnostic only.** Grants and
  refusals live exclusively in the UUID-owned project store
  (``record_project_opt_in`` / ``record_project_opt_out``); the retired writer
  ``set_project_consent`` raises ``LegacyConsentMigrationRequiredError``.

What survives unchanged is the cwd-vs-identity core: one long-lived emitter,
``os.chdir`` moving underneath it, and every row landing in — and only in — the
store of the project stamped on it. Assertions are made against the per-project
journal, the durable artefact that decides deliverability.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from specify_cli.event_journal import DRAIN_BLOCKED_SAAS_DISABLED
from specify_cli.event_journal.journal import EventJournal
from specify_cli.sync.project_store import ProjectSyncStore

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.unit, pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

UUID_A = "aaaaaaaa-0000-0000-0000-00000000000a"
UUID_B = "bbbbbbbb-0000-0000-0000-00000000000b"

_ACTOR = "capture-gate-identity-test"


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Per-test project stores and home; the arming env var deleted.

    ``SPEC_KITTY_ENABLE_SAAS_SYNC`` is machine-global arming and never a grant, so
    a developer's own export must not decide anything here. ``is_saas_sync_enabled``
    is patched True instead, because a machine with SaaS sync off would classify
    every drain question ``saas_disabled`` and the per-project question would never
    be reached.

    The machine layout authority (one record shared by all projects under this
    isolated home) is published ``project_only``: live payload writes require the
    project-only layout, and these tests exercise the live capture path.
    """
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "home"))
    (tmp_path / "home").mkdir(parents=True, exist_ok=True)
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)
    monkeypatch.setattr("specify_cli.sync.emitter.is_saas_sync_enabled", lambda: True)
    authority = ProjectSyncStore(UUID_A).layout_generation()
    authority.begin_cutover(_ACTOR)
    authority.publish_project_only(_ACTOR, verify_exact=lambda: True)


def _checkout(tmp_path: Path, name: str, *, uuid: str, consents: bool | None) -> Path:
    """A checkout whose ``.kittify/config.yaml`` declares identity and legacy consent.

    Under UUID-owned consent authority these files are read-only diagnostic
    evidence — they can neither grant nor refuse. Keeping them in the scenarios is
    the point: a committed ``sync.enabled`` in cwd's checkout decides nothing.
    """
    root = tmp_path / name
    (root / ".kittify").mkdir(parents=True, exist_ok=True)
    lines = ["project:", f"  uuid: {uuid}", f"  slug: {name}", "  node_id: 0123456789ab"]
    if consents is not None:
        lines += ["sync:", f"  enabled: {str(consents).lower()}"]
    (root / ".kittify" / "config.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return root


def _envelope(event_id: str, project_uuid: str | None) -> dict[str, Any]:
    """A wire envelope shaped like the one ``EventEmitter._emit`` assembles."""
    # canonical-event-exempt(exception-flow): mirrors EventEmitter._emit's legacy wire dict; no Payload model for this shape
    return {
        "event_id": event_id,
        "event_type": "WPStatusChanged",
        "aggregate_id": "wp-01",
        "aggregate_type": "WorkPackage",
        "schema_version": "3.0.0",
        "payload": {"status": "done"},
        "timestamp": "2026-07-30T07:00:00+00:00",
        "team_slug": None,
        "project_uuid": project_uuid,
        "project_slug": "some-slug",
    }


def _capture(envelope: dict[str, Any]) -> None:
    """Drive the real capture path for *envelope* from the current cwd."""
    from specify_cli.sync.emitter import EventEmitter

    EventEmitter()._capture_to_journal(
        event_id=str(envelope["event_id"]),
        event_type=str(envelope["event_type"]),
        event=envelope,
        occurred_at=str(envelope["timestamp"]),
        team_slug=None,
    )


def _captured_rows(project_uuid: str) -> dict[str, Any]:
    """The rows durably captured in *project_uuid*'s own store."""
    store = ProjectSyncStore(project_uuid)
    with store.unit_of_work() as unit:
        journal = EventJournal(unit, store.layout_generation())
        return {event.event_id: event for event in journal.read_all()}


# --------------------------------------------------------------------------- #
# The M1 scenario: cwd "consents", the event belongs to another project         #
# --------------------------------------------------------------------------- #


def test_capture_lands_in_the_events_own_store_never_in_cwds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Standing in a consenting project must not decide another's capture.

    Premise migrated: capture is no longer consent-gated, so the refusal the
    original test demanded is gone *by design* — but the confidentiality boundary
    it protected still holds. Project B holds a real explicit grant; project A has
    no record anywhere. A's event, emitted from inside B, lands in A's own store
    (unconditional local durability, FR-006), never in B's — and A remains
    egress-ineligible, so nothing about B's grant can ship it.
    """
    from specify_cli.sync.consent import record_project_opt_in, resolve_project_consent

    record_project_opt_in(UUID_B, actor=_ACTOR)
    consenting_b = _checkout(tmp_path, "project-b", uuid=UUID_B, consents=True)
    monkeypatch.chdir(consenting_b)

    envelope = _envelope("evt-a-in-b", UUID_A)
    _capture(envelope)

    assert "evt-a-in-b" in _captured_rows(UUID_A), (
        "the capture path must select project A's own store from the event's "
        "project_uuid; dropping the row would be silent capture loss"
    )
    assert "evt-a-in-b" not in _captured_rows(UUID_B), (
        "cwd's project (B) must not receive a row for project A's event — the "
        "working directory can neither select nor widen the destination store"
    )
    assert resolve_project_consent(UUID_A).granted is False, (
        "project A has no consent record anywhere; B's grant must not make A's "
        "event eligible to leave the machine"
    )


def test_the_stamped_reason_comes_from_the_events_project_not_cwds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The audit column must not be poisoned by cwd.

    A consenting project A, classified from within a *refusing* project B. If the
    gate were cwd-derived the reason would be ``saas_disabled``, which
    ``delivery/selection.py`` classifies **terminal** — the row retained on disk
    and permanently unselectable. The classification is driven through the
    emitter's real seam and stamped onto the captured row.
    """
    from specify_cli.sync.consent import record_project_opt_in
    from specify_cli.sync.emitter import EventEmitter

    record_project_opt_in(UUID_A, actor=_ACTOR)
    refusing_b = _checkout(tmp_path, "project-b", uuid=UUID_B, consents=False)
    monkeypatch.chdir(refusing_b)

    reason = EventEmitter()._classify_drain_blocked_reason(
        "some-team", project_uuid=UUID_A
    )
    assert reason != DRAIN_BLOCKED_SAAS_DISABLED, (
        "the drain classification answered cwd's question (project B refuses) for "
        "project A's event. saas_disabled is terminal in delivery/selection.py, so "
        "this row would be retained and never deliverable — silent capture loss"
    )

    envelope = _envelope("evt-a-from-refusing-b", UUID_A)
    envelope["drain_blocked_reason"] = reason
    _capture(envelope)

    rows = _captured_rows(UUID_A)
    assert "evt-a-from-refusing-b" in rows, (
        "project A consents, so its event must be captured no matter which "
        "directory the emitter is standing in"
    )
    assert rows["evt-a-from-refusing-b"].drain_blocked_reason != DRAIN_BLOCKED_SAAS_DISABLED
    assert rows["evt-a-from-refusing-b"].project_uuid == UUID_A


# --------------------------------------------------------------------------- #
# The converse: a blanket-deny implementation must not pass either              #
# --------------------------------------------------------------------------- #


def test_capture_accepts_an_event_whose_own_project_opted_in_from_outside_any_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The daemon's usual case: no readable checkout for the project at all.

    Consent lives in the UUID-owned project store (the retired machine index can
    no longer grant), which exists precisely because a drain sees only a
    ``project_uuid``. A capture path that reached for the checkout and gave up
    would strand every honest daemon capture.
    """
    from specify_cli.sync.consent import record_project_opt_in

    record_project_opt_in(UUID_A, actor=_ACTOR)
    outside = tmp_path / "not-a-project"
    outside.mkdir()
    monkeypatch.chdir(outside)
    monkeypatch.delenv("SPECIFY_REPO_ROOT", raising=False)

    _capture(_envelope("evt-a-outside", UUID_A))

    assert "evt-a-outside" in _captured_rows(UUID_A), (
        "a project that consents in its own UUID-owned store must be capturable "
        "with no checkout available; a blanket deny would pass the isolation tests "
        "above while breaking every honest daemon capture"
    )


def test_an_explicit_opt_out_outranks_an_earlier_opt_in_without_destroying_capture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Premise migrated from FR-013: refusal beats grant, on the one live chain.

    The committed checkout refusal the original test exercised is diagnostic-only
    now; the authoritative refusal is an explicit opt-out in the project's own
    store, and it must supersede the earlier opt-in. What the refusal seals is
    *egress eligibility* — per C-002 it must not delete or refuse the local row.
    """
    from specify_cli.sync.consent import (
        record_project_opt_in,
        record_project_opt_out,
        resolve_project_consent,
    )

    record_project_opt_in(UUID_A, actor=_ACTOR)
    record_project_opt_out(UUID_A, actor=_ACTOR)
    refusing_a = _checkout(tmp_path, "project-a", uuid=UUID_A, consents=False)
    monkeypatch.chdir(refusing_a)

    decision = resolve_project_consent(UUID_A)
    assert decision.granted is False, (
        "project A explicitly opted out; the refusal outranks the earlier grant, "
        "so nothing may be delivered"
    )

    _capture(_envelope("evt-a-refused-locally", UUID_A))

    assert "evt-a-refused-locally" in _captured_rows(UUID_A), (
        "refusal governs what leaves the machine, not local retention (C-002); "
        "capture into the project's own store must survive an opt-out"
    )


def test_an_event_with_no_resolvable_project_is_never_captured(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """NFR-001: not identifiable is not consentable, so it must not be stored.

    An event with no ``project_uuid`` has no project-owned store to select;
    refusing the write keeps an unconsentable payload out of every store rather
    than stranding it as an unmatched row.
    """
    consenting_b = _checkout(tmp_path, "project-b", uuid=UUID_B, consents=True)
    monkeypatch.chdir(consenting_b)

    _capture(_envelope("evt-no-identity", None))

    assert "evt-no-identity" not in _captured_rows(UUID_A)
    assert "evt-no-identity" not in _captured_rows(UUID_B), (
        "an event carrying no resolvable project_uuid cannot be shown to belong to "
        "any project — not even cwd's — so it must not be written anywhere"
    )


# --------------------------------------------------------------------------- #
# The scenario the defect actually needs: one long-lived emitter, two projects  #
# --------------------------------------------------------------------------- #


def test_one_long_lived_emitter_captures_each_event_into_its_own_projects_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The ``SyncRuntime`` singleton's shape: one emitter, cwd moved underneath it.

    Four captures, two projects, two working directories. Every row must land in —
    and only in — the store of the project stamped on it, from either directory.
    This is the cwd-vs-identity core of #3030 M1, restated for per-project stores.
    """
    from specify_cli.sync.consent import record_project_opt_in
    from specify_cli.sync.emitter import EventEmitter

    record_project_opt_in(UUID_A, actor=_ACTOR)  # A consents; B does not
    consenting_a = _checkout(tmp_path, "project-a", uuid=UUID_A, consents=True)
    refusing_b = _checkout(tmp_path, "project-b", uuid=UUID_B, consents=False)

    emitter = EventEmitter()
    original = Path(os.getcwd())
    try:
        for cwd in (consenting_a, refusing_b):
            os.chdir(cwd)
            for uuid, tag in ((UUID_A, "a"), (UUID_B, "b")):
                envelope = _envelope(f"evt-{tag}-from-{cwd.name}", uuid)
                emitter._capture_to_journal(
                    event_id=str(envelope["event_id"]),
                    event_type=str(envelope["event_type"]),
                    event=envelope,
                    occurred_at=str(envelope["timestamp"]),
                    team_slug=None,
                )
    finally:
        os.chdir(original)

    captured_a = set(_captured_rows(UUID_A))
    captured_b = set(_captured_rows(UUID_B))
    assert captured_a == {"evt-a-from-project-a", "evt-a-from-project-b"}, (
        "exactly the two project-A events belong in A's store, from either working "
        f"directory: {sorted(captured_a)}"
    )
    assert captured_b == {"evt-b-from-project-a", "evt-b-from-project-b"}, (
        "exactly the two project-B events belong in B's store, from either working "
        f"directory: {sorted(captured_b)}"
    )


def test_a_consent_read_failure_fails_closed_for_egress_but_not_for_capture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FR-003's rule: inability to determine consent is not consent.

    Premise migrated: capture is no longer the consent boundary, so an unreadable
    consent record must not destroy local durability — but the emitter's one
    consent predicate (``_project_consents_to_capture``, shared by the drain
    classification and the delivery path) must fail **closed**, never converting an
    unanswerable question into egress eligibility.
    """
    from specify_cli.sync.emitter import EventEmitter

    consenting_b = _checkout(tmp_path, "project-b", uuid=UUID_B, consents=True)
    monkeypatch.chdir(consenting_b)

    def _explode(*_args: object, **_kwargs: object) -> frozenset[str]:
        raise RuntimeError("consent index unreadable")

    monkeypatch.setattr(
        "specify_cli.sync.consent.consented_project_uuids", _explode
    )

    assert EventEmitter()._project_consents_to_capture(UUID_A) is False, (
        "a consent read that raises must deny egress eligibility, not fall back "
        "to cwd or to a grant"
    )

    _capture(_envelope("evt-unanswerable", UUID_A))

    assert "evt-unanswerable" in _captured_rows(UUID_A), (
        "the unanswerable consent question governs shipping; refusing the local "
        "write would turn a read fault into data loss (C-002)"
    )


def test_capture_writes_the_envelope_json_verbatim_for_a_consenting_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Guard the positive path's substance, not only the row's existence.

    The dispatcher decodes this BLOB verbatim and the receiver POSTs it, so a
    capture change that quietly altered what is stored would be a delivery bug the
    isolation tests above cannot see.
    """
    from specify_cli.sync.consent import record_project_opt_in

    record_project_opt_in(UUID_A, actor=_ACTOR)
    consenting_a = _checkout(tmp_path, "project-a", uuid=UUID_A, consents=True)
    monkeypatch.chdir(consenting_a)

    envelope = _envelope("evt-verbatim", UUID_A)
    _capture(envelope)

    row = _captured_rows(UUID_A)["evt-verbatim"]
    assert json.loads(row.payload.decode()) == envelope
    assert row.project_uuid == UUID_A
