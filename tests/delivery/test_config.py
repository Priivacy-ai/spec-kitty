"""US2 Independent Test for ``EventSyncConfig`` (WP09, FR-006/FR-007, C-008).

Each mode is proven by its **observable** on-disk + network footprint (NFR-001),
never by call order:

* ``TEAMSPACE``          — ``retain`` True; the receiver's endpoint is the
  WP01-resolved target URL, never anything stored in the config (FR-016/C-007).
* ``LOCAL_RETENTION``    — ``retain`` True, ``receiver`` None: a produce cycle
  *journals* rows on disk but *never posts*; the retained events become drainable
  once a delivery mode is selected later (US2 acceptance scenario 2).
* ``EXTERNAL_RECEIVER``  — same resolution branch as the localhost stub; a delivery
  records ledger state with **no** Teamspace credentials present (SC-005, US3).
* ``OPT_OUT``/``TRASH``  — local-only families neither journal nor post; a
  Teamspace-bound discard is **refused or audit-recorded** through a durable
  source, never silently dropped (C-008); unknown families fail closed.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import pytest

from specify_cli.delivery.config import (
    DefaultReceiverFactory,
    Delivery,
    DiscardAuditRecord,
    DiscardDecisionKind,
    EventSyncConfig,
    FamilyClassification,
    JsonlAuditSink,
    MissingExternalEndpointError,
    Mode,
    PolicyResolutionError,
    ResolvedPolicy,
    Retention,
    UnknownModeError,
    discard_decision,
)
from specify_cli.delivery.ledger import SqliteDeliveryLedger, init_ledger
from specify_cli.delivery.receivers import (
    DeliveryReceiver,
    ExternalReceiver,
    OutboundEvent,
    StubReceiver,
    TeamspaceReceiver,
)

pytestmark = pytest.mark.fast

_TARGET_ID = "target-1"
_BATCH_PATH = "/api/v1/events/batch/"


@dataclass(frozen=True)
class _FakeResolvedTarget:
    """Minimal stand-in for WP01 ``ResolvedSyncTarget`` (only the URL is read)."""

    resolved_server_url: str


@dataclass
class _StubFactory:
    """A factory whose EXTERNAL branch returns a WP06 ``StubReceiver``.

    Proves the stub is not a special mode — it falls out of the *same*
    EXTERNAL_RECEIVER resolution branch (contract §4 rule 2).
    """

    stub: StubReceiver

    def build_teamspace(self, *, resolved_server_url: str) -> DeliveryReceiver:
        return TeamspaceReceiver(resolved_server_url=resolved_server_url, auth_token="unused")

    def build_external(
        self, *, endpoint_url: str, auth_headers: Mapping[str, str] | None
    ) -> DeliveryReceiver:
        return self.stub


def _open_journal(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path))
    conn.execute("CREATE TABLE IF NOT EXISTS journal (event_id TEXT PRIMARY KEY)")
    conn.commit()
    return conn


def _journal_ids(conn: sqlite3.Connection) -> list[str]:
    return [str(row[0]) for row in conn.execute("SELECT event_id FROM journal ORDER BY event_id")]


def _simulate_cycle(
    policy: ResolvedPolicy,
    event_ids: Sequence[str],
    *,
    journal: sqlite3.Connection,
    ledger: SqliteDeliveryLedger,
) -> None:
    """A faithful mini drain: journal when ``retain``; post when a receiver exists."""
    if policy.retain:
        journal.executemany(
            "INSERT OR IGNORE INTO journal (event_id) VALUES (?)", [(eid,) for eid in event_ids]
        )
        journal.commit()
    if policy.receiver is not None:
        batch = [OutboundEvent(event_id=eid, payload={"event_id": eid}) for eid in event_ids]
        for result in policy.receiver.deliver(batch):
            ledger.record_result(
                event_id=result.event_id, target_id=_TARGET_ID, result=result.outcome
            )


def _make_ledger() -> SqliteDeliveryLedger:
    ledger = SqliteDeliveryLedger()
    init_ledger(ledger.connection)
    return ledger


# --------------------------------------------------------------------------- #
# Axes & presets (T051/T052)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("token", "retention", "delivery", "mode"),
    [
        ("TEAMSPACE", Retention.ON, Delivery.TEAMSPACE, Mode.TEAMSPACE),
        ("EXTERNAL_RECEIVER", Retention.ON, Delivery.EXTERNAL_RECEIVER, Mode.EXTERNAL_RECEIVER),
        ("LOCAL_RETENTION", Retention.ON, Delivery.NONE, Mode.LOCAL_RETENTION),
        ("OPT_OUT", Retention.OFF, Delivery.NONE, Mode.OPT_OUT),
    ],
)
def test_presets_map_to_exact_axis_points(
    token: str, retention: Retention, delivery: Delivery, mode: Mode
) -> None:
    endpoint = "http://localhost:9000/sink/" if token == "EXTERNAL_RECEIVER" else None
    config = EventSyncConfig.from_mode(token, external_endpoint=endpoint)
    assert config.retention is retention
    assert config.delivery is delivery
    assert config.mode is mode


def test_axes_are_independent_local_retention_vs_opt_out() -> None:
    local_retention = EventSyncConfig.from_mode("LOCAL_RETENTION")
    opt_out = EventSyncConfig.from_mode("OPT_OUT")
    # Same delivery axis (NONE) ...
    assert local_retention.delivery is Delivery.NONE
    assert opt_out.delivery is Delivery.NONE
    # ... but the retention axis keeps them distinct (not conflated into one enum).
    assert local_retention.retention is Retention.ON
    assert opt_out.retention is Retention.OFF
    assert local_retention != opt_out
    assert local_retention.mode is Mode.LOCAL_RETENTION
    assert opt_out.mode is Mode.OPT_OUT


def test_config_carries_no_teamspace_target_url() -> None:
    # The config models policy, not target authority (FR-016/C-007): it has no
    # Teamspace server-URL field at all.
    field_names = set(EventSyncConfig.__dataclass_fields__)
    assert "resolved_server_url" not in field_names
    assert "server_url" not in field_names
    assert "teamspace_url" not in field_names


# --------------------------------------------------------------------------- #
# Mode token parsing + TRASH alias + Terminology Canon (T052)
# --------------------------------------------------------------------------- #


def test_trash_alias_normalizes_to_opt_out() -> None:
    config = EventSyncConfig.from_mode("TRASH")
    assert config.mode is Mode.OPT_OUT
    assert config.retention is Retention.OFF
    assert config.delivery is Delivery.NONE
    assert Mode.from_token("trash") is Mode.OPT_OUT
    assert Mode.from_token("OPT_OUT") is Mode.OPT_OUT
    assert Mode.from_token("opt-out") is Mode.OPT_OUT


def test_unknown_mode_token_is_rejected() -> None:
    with pytest.raises(UnknownModeError):
        Mode.from_token("nonsense")
    # Terminology Canon: a ``feature*`` token is NOT a valid mode.
    with pytest.raises(UnknownModeError):
        Mode.from_token("feature_sync")


def test_external_receiver_requires_endpoint() -> None:
    with pytest.raises(MissingExternalEndpointError):
        EventSyncConfig.from_mode("EXTERNAL_RECEIVER")


# --------------------------------------------------------------------------- #
# US2 acceptance scenario 1 — TEAMSPACE (T053/T055)
# --------------------------------------------------------------------------- #


def test_teamspace_resolves_against_resolved_target_url() -> None:
    config = EventSyncConfig.from_mode("TEAMSPACE")
    target = _FakeResolvedTarget(resolved_server_url="https://teamspace.example.com")
    factory = DefaultReceiverFactory(teamspace_auth_token="secret-token")

    policy = config.resolve(resolved_target=target, receiver_factory=factory)

    assert policy.retain is True
    assert isinstance(policy.receiver, TeamspaceReceiver)
    # The endpoint comes from the WP01-resolved target, never from the config.
    assert policy.receiver.endpoint_url == "https://teamspace.example.com" + _BATCH_PATH


def test_teamspace_without_resolved_target_is_refused_not_crash() -> None:
    config = EventSyncConfig.from_mode("TEAMSPACE")
    with pytest.raises(PolicyResolutionError):
        config.resolve(resolved_target=None)


# --------------------------------------------------------------------------- #
# US2 acceptance scenario 2 — LOCAL_RETENTION journals but never posts (T055)
# --------------------------------------------------------------------------- #


def test_local_retention_journals_but_never_posts(tmp_path: Path) -> None:
    config = EventSyncConfig.from_mode("LOCAL_RETENTION")
    policy = config.resolve()  # no target needed; delivery is NONE
    assert policy.retain is True
    assert policy.receiver is None

    journal = _open_journal(tmp_path / "journal.sqlite3")
    ledger = _make_ledger()
    try:
        _simulate_cycle(policy, ["evt-a", "evt-b"], journal=journal, ledger=ledger)
        # Journaled on disk ...
        assert _journal_ids(journal) == ["evt-a", "evt-b"]
        # ... but never posted: no delivery-ledger rows exist.
        assert ledger.get("evt-a", _TARGET_ID) is None
        assert ledger.delivered_anywhere("evt-a") is False

        # Drain later: select EXTERNAL delivery and the retained events flow out.
        stub = StubReceiver()
        later = EventSyncConfig.from_mode(
            "EXTERNAL_RECEIVER", external_endpoint="http://localhost:9000/sink/"
        )
        later_policy = later.resolve(receiver_factory=_StubFactory(stub))
        _simulate_cycle(later_policy, _journal_ids(journal), journal=journal, ledger=ledger)
        assert sorted(stub.received_event_ids()) == ["evt-a", "evt-b"]
        assert ledger.get("evt-a", _TARGET_ID) is not None
    finally:
        journal.close()
        ledger.close()


# --------------------------------------------------------------------------- #
# US2 acceptance scenario 3 — EXTERNAL_RECEIVER / stub share one branch (T053/T055)
# --------------------------------------------------------------------------- #


def test_external_receiver_records_ledger_without_teamspace_credentials() -> None:
    stub = StubReceiver()
    config = EventSyncConfig.from_mode(
        "EXTERNAL_RECEIVER", external_endpoint="http://localhost:9000/__sink__/"
    )
    policy = config.resolve(receiver_factory=_StubFactory(stub))

    assert policy.retain is True
    assert policy.receiver is stub
    # No Teamspace credentials leak into the external/stub path (SC-005 hygiene).
    assert policy.receiver.auth_headers() == {}

    ledger = _make_ledger()
    journal = sqlite3.connect(":memory:")
    journal.execute("CREATE TABLE journal (event_id TEXT PRIMARY KEY)")
    try:
        _simulate_cycle(policy, ["evt-1"], journal=journal, ledger=ledger)
        row = ledger.get("evt-1", _TARGET_ID)
        assert row is not None
        assert row.status == "success"
        assert stub.received_event_ids() == ("evt-1",)
    finally:
        journal.close()
        ledger.close()


def test_external_receiver_default_branch_yields_credential_free_receiver() -> None:
    # The *same* branch with the default factory builds a real ExternalReceiver
    # pointed at the operator endpoint — no separate stub path.
    config = EventSyncConfig.from_mode(
        "EXTERNAL_RECEIVER", external_endpoint="http://localhost:9000/sink/"
    )
    policy = config.resolve(receiver_factory=DefaultReceiverFactory())
    assert isinstance(policy.receiver, ExternalReceiver)
    assert policy.receiver.endpoint_url == "http://localhost:9000/sink/"
    assert "Authorization" not in policy.receiver.auth_headers()


def test_resolve_uses_default_factory_when_none_supplied() -> None:
    config = EventSyncConfig.from_mode(
        "EXTERNAL_RECEIVER", external_endpoint="http://localhost:9000/sink/"
    )
    policy = config.resolve()
    assert isinstance(policy.receiver, ExternalReceiver)


# --------------------------------------------------------------------------- #
# US2 acceptance scenario 4 — OPT_OUT (local-only) neither journals nor posts
# --------------------------------------------------------------------------- #


def test_opt_out_local_only_neither_journals_nor_posts(tmp_path: Path) -> None:
    config = EventSyncConfig.from_mode("OPT_OUT")
    policy = config.resolve()
    assert policy.retain is False
    assert policy.receiver is None

    journal = _open_journal(tmp_path / "journal.sqlite3")
    ledger = _make_ledger()
    try:
        _simulate_cycle(policy, ["local-1"], journal=journal, ledger=ledger)
        assert _journal_ids(journal) == []  # not journaled
        assert ledger.get("local-1", _TARGET_ID) is None  # not posted
    finally:
        journal.close()
        ledger.close()

    decision = discard_decision("local.metric", classification=FamilyClassification.LOCAL_ONLY)
    assert decision.kind is DiscardDecisionKind.DISCARD_ALLOWED
    assert decision.dropped is True
    assert decision.refused is False


def test_opt_out_explicitly_discardable_family_is_allowed() -> None:
    decision = discard_decision(
        "ephemeral.cache", classification=FamilyClassification.EXPLICITLY_DISCARDABLE
    )
    assert decision.kind is DiscardDecisionKind.DISCARD_ALLOWED
    assert decision.dropped is True


# --------------------------------------------------------------------------- #
# US2 acceptance scenario 5 — Teamspace-bound discard is never silent (C-008)
# --------------------------------------------------------------------------- #


def test_teamspace_bound_discard_is_refused_without_durable_sink() -> None:
    decision = discard_decision(
        "mission.event", classification=FamilyClassification.TEAMSPACE_BOUND
    )
    assert decision.kind is DiscardDecisionKind.REFUSED
    assert decision.refused is True
    assert decision.dropped is False  # NOT silently dropped
    assert "teamspace" in decision.reason.lower()
    assert decision.reason.strip()  # human-readable, audit-visible reason


def test_teamspace_bound_discard_is_audit_recorded_to_durable_source(tmp_path: Path) -> None:
    audit_path = tmp_path / "discard-audit.jsonl"
    sink = JsonlAuditSink(audit_path)
    decision = discard_decision(
        "mission.event",
        classification=FamilyClassification.TEAMSPACE_BOUND,
        audit_sink=sink,
    )
    assert decision.kind is DiscardDecisionKind.AUDIT_RECORDED
    assert decision.dropped is True  # discardable, because preserved durably
    # Durable, observable on-disk evidence — the fact is not lost.
    assert audit_path.exists()
    records = sink.records()
    assert len(records) == 1
    assert records[0].event_family == "mission.event"
    assert records[0].classification is FamilyClassification.TEAMSPACE_BOUND


def test_unknown_family_fails_closed_non_discardable() -> None:
    # Fail-closed: an unclassified family is treated as potentially Teamspace-bound.
    decision = discard_decision("mystery", classification=FamilyClassification.UNKNOWN)
    assert decision.kind is DiscardDecisionKind.REFUSED
    assert decision.dropped is False


def test_unknown_family_with_durable_sink_is_audit_recorded(tmp_path: Path) -> None:
    sink = JsonlAuditSink(tmp_path / "audit.jsonl")
    decision = discard_decision(
        "mystery", classification=FamilyClassification.UNKNOWN, audit_sink=sink
    )
    assert decision.kind is DiscardDecisionKind.AUDIT_RECORDED
    assert len(sink.records()) == 1


# --------------------------------------------------------------------------- #
# Defensive-branch coverage
# --------------------------------------------------------------------------- #


def test_resolve_external_without_endpoint_is_defensively_rejected() -> None:
    # Bypassing ``from_mode`` (which guards the endpoint) still cannot deliver
    # externally with no endpoint — the resolve build step fails closed.
    config = EventSyncConfig(retention=Retention.ON, delivery=Delivery.EXTERNAL_RECEIVER)
    with pytest.raises(MissingExternalEndpointError):
        config.resolve()


def test_audit_sink_records_empty_when_file_absent(tmp_path: Path) -> None:
    sink = JsonlAuditSink(tmp_path / "missing.jsonl")
    assert sink.records() == []


def test_audit_sink_skips_blank_lines(tmp_path: Path) -> None:
    audit_path = tmp_path / "audit.jsonl"
    sink = JsonlAuditSink(audit_path)
    sink.record(
        DiscardAuditRecord(
            event_family="mission.event",
            classification=FamilyClassification.TEAMSPACE_BOUND,
            reason="durable",
            at="2026-06-29T00:00:00+00:00",
        )
    )
    # Inject a stray blank line; it must be skipped, not parsed.
    with audit_path.open("a", encoding="utf-8") as handle:
        handle.write("\n")
    records = sink.records()
    assert len(records) == 1
    assert records[0].event_family == "mission.event"
