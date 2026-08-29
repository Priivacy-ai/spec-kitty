"""WP09 public opt-out and all-family revocation ordering matrix."""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import subprocess
import sys
import textwrap
import threading
import time
from dataclasses import replace
from pathlib import Path

import pytest

from specify_cli.sync.consent import record_project_opt_in
from specify_cli.sync.project_store import ProjectStoreError, ProjectSyncStore
from specify_cli.sync.routing import disable_checkout_sync
from specify_cli.sync.transport_attempts import (
    DeliveryAttemptSpec,
    DeliveryAttemptState,
    DeliveryOutcome,
    mark_delivery_result_unknown,
    mark_transport_started,
    prepare_delivery_attempt,
    record_delivery_result,
)
from specify_cli.sync.transport_lease import acquire_project_transport_lease
from tests.support.sync_transport_barriers import (
    PAIRED_SAAS_CONTRACT_DIGEST,
    PAIRED_SAAS_REPLAY_EVIDENCE,
    PAIRED_SAAS_REPLAY_SHA,
    PAIRED_SAAS_REPLAY_TREE,
    PAIRED_SAAS_SOURCE_BLOBS,
    PRODUCTION_ADAPTER_CONTRACTS,
    BarrierIdentity,
    BarrierPhase,
    HostedReferenceExpectation,
    PhysicalSinkPoison,
    ProcessTransportBarrier,
    ProductionAdapterContract,
    ProductionAdapterEvidence,
    PersistedAttemptEvidence,
    ResultExpectation,
    TRANSPORT_FAMILIES,
    assert_exact_transport_evidence,
    assert_transport_evidence_values,
    canonical_transport_payload,
    evidence_from_barrier,
    invoke_production_adapter,
    paired_saas_contract_digest,
)

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

PROJECT_A = "aaaaaaaa-0000-0000-0000-000000000001"
PROJECT_B = "bbbbbbbb-0000-0000-0000-000000000002"
MINTED_NATIVE_FAMILIES = (
    "event_relay",
    "body_drain",
    "reconnect_local_commit",
    "tracker_hosted",
    "generic_saas",
)
CALLER_NATIVE_FAMILIES = tuple(family for family in TRANSPORT_FAMILIES if family not in MINTED_NATIVE_FAMILIES)


def test_paired_saas_c3_contract_snapshot_is_immutable() -> None:
    assert PAIRED_SAAS_REPLAY_SHA == "c3f39217aedea94a20802f9e9f2dbdeeecec3077"
    assert PAIRED_SAAS_REPLAY_TREE == "e7f740319b8032a3b7991f590d289096eecdf5b9"
    assert dict(PAIRED_SAAS_SOURCE_BLOBS) == {
        "apps/connectors/runtime_push.py": "6473848a8137025e8bc66b0d6f62f5abe47f786b",
        "apps/connectors/tests/test_runtime_push.py": "15a0d9ee50c3405b11f1ca2e13dcb7be08664bce",
        "apps/collaboration/views.py": "b63eeee02999727fc1031d22d32ea2e127814eb3",
        "apps/collaboration/tests/test_widen_endpoint.py": "46c085b8c8eed5df3c5f1b5ca1b6fb2e98bd97be",
    }
    assert paired_saas_contract_digest() == PAIRED_SAAS_CONTRACT_DIGEST


@pytest.mark.parametrize("contract", PRODUCTION_ADAPTER_CONTRACTS, ids=lambda row: row.family)
def test_each_matrix_row_invokes_its_real_entry_and_poisoned_physical_sink(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    contract: ProductionAdapterContract,
) -> None:
    """T040 red: no family may pass by substituting a write-kind label."""
    family = contract.family
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / family / "runtime"))
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    repo_root = _repo(tmp_path / family, PROJECT_A)
    identity = BarrierIdentity(
        family=family,
        project_uuid=PROJECT_A,
        attempt_id=f"poison:{family}",
        native_identity=f"native:poison:{family}",
    )

    with pytest.raises(PhysicalSinkPoison):
        invoke_production_adapter(
            repo_root,
            identity,
            outcome="delivered",
            poison_sink=True,
        )


@pytest.mark.parametrize("family", MINTED_NATIVE_FAMILIES)
def test_minted_families_reject_the_callers_arbitrary_native_label(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    family: str,
) -> None:
    """T040 mutant: five producers own correlation; the harness does not."""
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / family / "runtime"))
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    seed = BarrierIdentity(
        family=family,
        project_uuid=PROJECT_A,
        attempt_id="arbitrary-caller-attempt",
        native_identity="arbitrary-caller-native",
    )
    evidence = invoke_production_adapter(
        _repo(tmp_path / family, PROJECT_A),
        seed,
        outcome="delivered",
    )
    payload, attempt = assert_exact_transport_evidence(evidence)

    assert evidence.actual_identity.attempt_id == attempt.attempt_id
    assert evidence.actual_identity.attempt_id != seed.attempt_id
    assert evidence.actual_identity.native_identity != seed.native_identity
    if family in {"event_relay", "reconnect_local_commit"}:
        assert payload["spec_kitty_delivery_identity"] == evidence.actual_identity.native_identity
    elif family == "tracker_hosted":
        assert payload["headers"]["Idempotency-Key"] == evidence.actual_identity.native_identity
    elif family == "generic_saas":
        assert payload["native_identity"] == evidence.actual_identity.native_identity


@pytest.mark.parametrize("family", CALLER_NATIVE_FAMILIES)
def test_caller_correlated_families_preserve_the_exact_native_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    family: str,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / family / "runtime"))
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    seed = BarrierIdentity(
        family=family,
        project_uuid=PROJECT_A,
        attempt_id=f"caller-attempt:{family}",
        native_identity=f"caller-native:{family}",
    )
    evidence = invoke_production_adapter(
        _repo(tmp_path / family, PROJECT_A),
        seed,
        outcome="delivered",
    )
    assert_exact_transport_evidence(evidence)
    assert evidence.actual_identity.native_identity == seed.native_identity


def test_partial_transport_bytes_and_local_only_relay_are_not_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T040 mutants: a subset of one frame or only the local POST cannot pass."""
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    websocket = invoke_production_adapter(
        _repo(tmp_path / "websocket", PROJECT_A),
        BarrierIdentity(
            family="emitter_websocket",
            project_uuid=PROJECT_A,
            attempt_id="partial-wire-seed",
            native_identity="partial-wire-event",
        ),
        outcome="delivered",
    )
    full = canonical_transport_payload(websocket)
    partial = dict(full)
    partial.pop("binding_audience")
    with pytest.raises(AssertionError):
        canonical_transport_payload(
            replace(
                websocket,
                request_bytes=json.dumps(
                    partial,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8"),
            )
        )

    with pytest.raises(PhysicalSinkPoison, match="local daemon POST"):
        invoke_production_adapter(
            _repo(tmp_path / "relay-local-poison", PROJECT_A),
            BarrierIdentity(
                family="event_relay",
                project_uuid=PROJECT_A,
                attempt_id="local-poison-seed",
                native_identity="local-poison-native",
            ),
            outcome="delivered",
            poison_relay_delegation=True,
        )
    relay = invoke_production_adapter(
        _repo(tmp_path / "relay", PROJECT_A),
        BarrierIdentity(
            family="event_relay",
            project_uuid=PROJECT_A,
            attempt_id="local-only-seed",
            native_identity="local-only-native",
        ),
        outcome="delivered",
    )
    assert relay.delegation_bytes and relay.request_bytes
    canonical_transport_payload(relay)
    with pytest.raises((AssertionError, json.JSONDecodeError)):
        canonical_transport_payload(replace(relay, request_bytes=b""))


def _protocol_digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()  # noqa: TID251 - exact transport protocol mutant


def _encode_mutant_request(
    evidence: ProductionAdapterEvidence,
    payload: dict[str, object],
) -> bytes:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    if evidence.family in {"direct_dispatcher", "final_exit_sync", "history_import"}:
        return gzip.compress(b'{"events":[' + encoded + b"]}")
    return encoded


def _forge_attempt(
    attempt: PersistedAttemptEvidence,
    *,
    payload_hash: str | None = None,
    payload_reference: str | None = None,
    metadata_updates: dict[str, object] | None = None,
) -> PersistedAttemptEvidence:
    reference = payload_reference or attempt.payload_reference
    metadata = {
        **attempt.metadata,
        "payload_reference": reference,
        **(metadata_updates or {}),
    }
    return replace(
        attempt,
        payload_hash=payload_hash or attempt.payload_hash,
        payload_reference=reference,
        metadata=metadata,
    )


_ORACLE_MUTANTS = (
    ("foreign_event_authority_ids", "emitter_websocket", "delivered"),
    ("foreign_local_commit_authority", "reconnect_local_commit", "delivered"),
    ("foreign_body_project", "body_drain", "delivered"),
    ("self_derived_foreign_history", "history_import", "delivered"),
    ("generic_http_disclosure", "generic_saas", "delivered"),
    ("tracker_http_disclosure", "tracker_hosted", "delivered"),
    ("forged_event_target", "daemon_publish", "delivered"),
    ("forged_local_commit_target", "reconnect_local_commit", "delivered"),
    ("forged_history_target", "history_import", "delivered"),
    ("truncated_relay", "event_relay", "delivered"),
    ("forged_relay_token", "event_relay", "delivered"),
    ("forged_generic_terminal", "generic_saas", "duplicate"),
    ("forged_tracker_terminal", "tracker_hosted", "duplicate"),
)


@pytest.mark.parametrize(("mutant", "family", "outcome"), _ORACLE_MUTANTS)
def test_independent_oracle_rejects_recomputed_physical_and_durable_forgery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutant: str,
    family: str,
    outcome: str,
) -> None:
    """Reviewer mutants: captured bytes can agree with forged durable metadata and still fail."""
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / mutant / "runtime"))
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    evidence = invoke_production_adapter(
        _repo(tmp_path / mutant, PROJECT_A),
        BarrierIdentity(
            family=family,
            project_uuid=PROJECT_A,
            attempt_id=f"oracle:{mutant}",
            native_identity=f"native:oracle:{mutant}",
        ),
        outcome=outcome,
    )
    genuine_payload, genuine_attempt = assert_exact_transport_evidence(evidence)
    forged_evidence = evidence
    forged_attempt = genuine_attempt

    if mutant == "foreign_event_authority_ids":
        payload = {
            **genuine_payload,
            "project_uuid": PROJECT_B,
            "event_id": "foreign-event",
            "correlation_id": "foreign-correlation",
            "spec_kitty_delivery_identity": "foreign-delivery-id",
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        reference = json.dumps(
            {"event_id": "foreign-event", "schema": "spec-kitty.dispatcher.v1", "target_id": "tgt_forged"},
            sort_keys=True,
            separators=(",", ":"),
        )
        forged_evidence = replace(evidence, request_bytes=_encode_mutant_request(evidence, payload))
        forged_attempt = _forge_attempt(
            genuine_attempt,
            payload_hash="sha256:" + _protocol_digest(raw),
            payload_reference=reference,
            metadata_updates={
                "project_uuid": PROJECT_B,
                "native_identity": "foreign-delivery-id",
            },
        )
    elif mutant == "foreign_local_commit_authority":
        payload = {
            **genuine_payload,
            "admission_generation": 99,
            "binding_audience": "private-teamspace:foreign",
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        forged_evidence = replace(evidence, request_bytes=_encode_mutant_request(evidence, payload))
        forged_attempt = _forge_attempt(
            genuine_attempt,
            payload_hash="sha256:" + _protocol_digest(raw),
            metadata_updates={
                "admission_generation": "99",
                "binding_audience": "private-teamspace:foreign",
            },
        )
    elif mutant == "foreign_body_project":
        payload = {**genuine_payload, "project_uuid": PROJECT_B}
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        forged_evidence = replace(evidence, request_bytes=_encode_mutant_request(evidence, payload))
        forged_attempt = _forge_attempt(
            genuine_attempt,
            payload_hash="sha256:" + _protocol_digest(raw),
            metadata_updates={"project_uuid": PROJECT_B},
        )
    elif mutant == "self_derived_foreign_history":
        payload = {
            **genuine_payload,
            "project_uuid": PROJECT_B,
            "admission_generation": 9,
            "binding_audience": "private-teamspace:foreign",
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        forged_hash = "sha256:" + _protocol_digest(raw)
        reference = json.loads(genuine_attempt.payload_reference)
        reference.update(
            disclosed_sha256=forged_hash,
            preview_hash=_protocol_digest(b"foreign-preview"),
            history_action_id="history-" + _protocol_digest(b"foreign-action"),
        )
        forged_evidence = replace(evidence, request_bytes=_encode_mutant_request(evidence, payload))
        forged_attempt = _forge_attempt(
            genuine_attempt,
            payload_hash=forged_hash,
            payload_reference=json.dumps(reference, sort_keys=True, separators=(",", ":")),
            metadata_updates={
                "project_uuid": PROJECT_B,
                "admission_generation": "9",
                "binding_audience": "private-teamspace:foreign",
            },
        )
    elif mutant in {"generic_http_disclosure", "tracker_http_disclosure"}:
        payload = dict(genuine_payload)
        if family == "generic_saas":
            payload.update(method="PATCH", url="https://evil.invalid/widen", json={"invited_user_ids": [999]})
            reference = json.dumps(
                {"method": payload["method"], "url": payload["url"], "json": payload["json"]},
                sort_keys=True,
                separators=(",", ":"),
            )
            forged_hash = _protocol_digest(reference.encode())
        else:
            payload.update(method="PUT", path="/api/v1/tracker/foreign/", json={"items": []})
            body = json.dumps(payload["json"], separators=(",", ":"))
            url = "https://evil.invalid/api/v1/tracker/foreign/"
            reference = json.dumps(
                {"method": "PUT", "url": url, "body": body},
                sort_keys=True,
                separators=(",", ":"),
            )
            forged_hash = _protocol_digest(f"PUT\n{url}\n{body}".encode())
        forged_evidence = replace(evidence, request_bytes=_encode_mutant_request(evidence, payload))
        forged_attempt = _forge_attempt(
            genuine_attempt,
            payload_hash=forged_hash,
            payload_reference=reference,
        )
    elif mutant.startswith("forged_") and mutant.endswith("_target"):
        reference = json.loads(genuine_attempt.payload_reference)
        reference["target_id"] = "tgt_forged_foreign_authority"
        forged_attempt = _forge_attempt(
            genuine_attempt,
            payload_reference=json.dumps(reference, sort_keys=True, separators=(",", ":")),
        )
    elif mutant == "truncated_relay":
        forged_evidence = replace(evidence, delegation_bytes=evidence.delegation_bytes[:-7])
    elif mutant == "forged_relay_token":
        delegation = json.loads(evidence.delegation_bytes)
        delegation["token"] = "foreign-loopback-token"
        forged_evidence = replace(
            evidence,
            delegation_bytes=json.dumps(delegation, sort_keys=True, separators=(",", ":")).encode(),
        )
    elif mutant == "forged_generic_terminal":
        terminal = json.loads(str(genuine_attempt.metadata["terminal_response_reference"]))
        terminal.update(
            decision_id="foreign-decision",
            audit_snapshot_id="foreign-audit",
            widened_by=999,
        )
        forged_attempt = _forge_attempt(
            genuine_attempt,
            metadata_updates={"terminal_response_reference": json.dumps(terminal, sort_keys=True, separators=(",", ":"))},
        )
    else:
        terminal = json.loads(str(genuine_attempt.metadata["terminal_response_reference"]))
        terminal["summary"] = {"total": 999, "succeeded": 0, "failed": 999}
        terminal["items"] = [{"ref": {"system": "github", "workspace": "", "id": "foreign"}, "action": "delete", "outcome": "ok"}]
        forged_attempt = _forge_attempt(
            genuine_attempt,
            metadata_updates={"terminal_response_reference": json.dumps(terminal, sort_keys=True, separators=(",", ":"))},
        )

    with pytest.raises((AssertionError, json.JSONDecodeError)):
        assert_transport_evidence_values(forged_evidence, forged_attempt)


@pytest.mark.parametrize(
    ("family", "paired_saas_test"),
    PAIRED_SAAS_REPLAY_EVIDENCE,
    ids=("tracker_hosted", "generic_saas"),
)
def test_real_duplicate_response_persists_duplicate_not_delivered(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    family: str,
    paired_saas_test: str,
) -> None:
    """T041: the c3-pinned replay evidence survives the real Core classifier."""
    assert PAIRED_SAAS_REPLAY_SHA == "c3f39217aedea94a20802f9e9f2dbdeeecec3077"
    assert paired_saas_test.startswith("apps/")
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / family / "runtime"))
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    repo_root = _repo(tmp_path / family, PROJECT_A)
    evidence = invoke_production_adapter(
        repo_root,
        BarrierIdentity(
            family=family,
            project_uuid=PROJECT_A,
            attempt_id=f"duplicate:{family}",
            native_identity=f"native:duplicate:{family}",
        ),
        outcome="duplicate",
    )
    _payload, attempt = assert_exact_transport_evidence(evidence)
    store = ProjectSyncStore(PROJECT_A)
    with store.unit_of_work() as unit:
        rows = unit.execute(
            "SELECT delivery_results.outcome FROM delivery_attempts "
            "JOIN delivery_results ON delivery_results.project_uuid = delivery_attempts.project_uuid "
            "AND delivery_results.attempt_id = delivery_attempts.attempt_id "
            "ORDER BY delivery_attempts.created_at DESC"
        ).fetchall()

    assert rows and str(rows[0][0]) == DeliveryOutcome.DUPLICATE.value
    assert attempt.result_outcome == DeliveryOutcome.DUPLICATE.value
    assert attempt.result_id == f"{attempt.attempt_id}:result"
    terminal_body = json.loads(str(attempt.metadata["terminal_response_reference"]))
    if family == "generic_saas":
        assert frozenset(terminal_body) == {
            "audit_snapshot_id",
            "decision_id",
            "idempotent",
            "invited_user_ids",
            "participation_row_ids",
            "slack_thread_status",
            "widened_at",
            "widened_by",
        }
        assert terminal_body["idempotent"] is True
    else:
        assert frozenset(terminal_body) == {
            "identity_path",
            "items",
            "status",
            "summary",
        }
        assert terminal_body["status"] == "ok"


@pytest.mark.parametrize("family", ("tracker_hosted", "generic_saas"))
@pytest.mark.parametrize("mutation", ("missing_header", "wrong_key"))
def test_hosted_replay_requires_header_and_exact_native_request_correlation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    family: str,
    mutation: str,
) -> None:
    """T041: endpoint bodies alone and cross-key replay headers are not proof."""
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / family / mutation / "runtime"))
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    repo_root = _repo(tmp_path / family / mutation, PROJECT_A)
    evidence = invoke_production_adapter(
        repo_root,
        BarrierIdentity(
            family=family,
            project_uuid=PROJECT_A,
            attempt_id=f"replay-mutant:{family}:{mutation}",
            native_identity=f"native:replay-mutant:{family}:{mutation}",
        ),
        outcome="duplicate",
        hosted_replay_mutation=mutation,
    )
    assert_exact_transport_evidence(evidence)
    store = ProjectSyncStore(PROJECT_A)
    with store.unit_of_work() as unit:
        row = unit.execute(
            "SELECT delivery_results.outcome, delivery_attempts.payload_reference "
            "FROM delivery_attempts JOIN delivery_results "
            "ON delivery_results.project_uuid = delivery_attempts.project_uuid "
            "AND delivery_results.attempt_id = delivery_attempts.attempt_id "
            "ORDER BY delivery_attempts.created_at DESC LIMIT 1"
        ).fetchone()

    assert row is not None
    assert str(row[0]) == DeliveryOutcome.DELIVERED.value
    attempt_metadata = json.loads(str(row[1]))
    body = json.loads(str(attempt_metadata["terminal_response_reference"]))
    if family == "generic_saas":
        assert body["idempotent"] is True
        assert "duplicate" not in body
    else:
        assert body["status"] == "ok"
        assert body["summary"] == {"total": 1, "succeeded": 1, "failed": 0}
        assert "duplicate" not in body


@pytest.mark.parametrize("family", TRANSPORT_FAMILIES)
def test_ordinary_timeout_result_presence_matches_each_public_adapter_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    family: str,
) -> None:
    """Ordinary timeout is not the opt-out terminalization result contract."""
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / family / "ordinary-timeout"))
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    evidence = invoke_production_adapter(
        _repo(tmp_path / family / "ordinary-timeout", PROJECT_A),
        BarrierIdentity(
            family=family,
            project_uuid=PROJECT_A,
            attempt_id=f"ordinary-timeout:{family}",
            native_identity=f"native:ordinary-timeout:{family}",
        ),
        outcome="timeout",
    )
    _payload, attempt = assert_exact_transport_evidence(evidence)
    result_bearing = family in {
        "direct_dispatcher",
        "final_exit_sync",
        "history_import",
    }
    assert evidence.result_expectation is (ResultExpectation.ORDINARY_UNKNOWN if result_bearing else ResultExpectation.ABSENT)
    assert evidence.expected_result_outcome == ("unknown" if result_bearing else None)
    if result_bearing:
        assert attempt.result_id == f"{attempt.attempt_id}:result"
        assert attempt.result_outcome == "unknown"
    else:
        assert attempt.result_id is None
        assert attempt.result_outcome is None


@pytest.mark.parametrize("family", ("emitter_websocket", "tracker_hosted", "generic_saas"))
@pytest.mark.parametrize("outcome", ("delivered", "duplicate", "refused"))
def test_completed_public_call_rejects_a_missing_durable_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    family: str,
    outcome: str,
) -> None:
    """A successful/refused return cannot pass on attempt state alone."""
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / family / outcome / "missing-result"))
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    evidence = invoke_production_adapter(
        _repo(tmp_path / family / outcome / "missing-result", PROJECT_A),
        BarrierIdentity(
            family=family,
            project_uuid=PROJECT_A,
            attempt_id=f"missing-result:{family}:{outcome}",
            native_identity=f"native:missing-result:{family}:{outcome}",
        ),
        outcome=outcome,
    )
    _payload, attempt = assert_exact_transport_evidence(evidence)
    assert evidence.result_expectation is ResultExpectation.COMPLETED
    missing = replace(
        attempt,
        result_id=None,
        result_outcome=None,
        result_epoch_id=None,
        result_target_generation=None,
        result_admission_generation=None,
    )
    with pytest.raises(AssertionError, match="result identity/outcome/authority"):
        assert_transport_evidence_values(evidence, missing)


@pytest.mark.parametrize("family", ("tracker_hosted", "generic_saas"))
@pytest.mark.parametrize("outcome", ("delivered", "duplicate"))
def test_completed_hosted_call_rejects_a_missing_terminal_response_reference(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    family: str,
    outcome: str,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / family / outcome / "missing-reference"))
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    evidence = invoke_production_adapter(
        _repo(tmp_path / family / outcome / "missing-reference", PROJECT_A),
        BarrierIdentity(
            family=family,
            project_uuid=PROJECT_A,
            attempt_id=f"missing-reference:{family}:{outcome}",
            native_identity=f"native:missing-reference:{family}:{outcome}",
        ),
        outcome=outcome,
    )
    _payload, attempt = assert_exact_transport_evidence(evidence)
    assert evidence.hosted_reference_expectation is HostedReferenceExpectation.REQUIRED
    metadata = dict(attempt.metadata)
    metadata.pop("terminal_response_reference")
    with pytest.raises(AssertionError, match="terminal response"):
        assert_transport_evidence_values(evidence, replace(attempt, metadata=metadata))


@pytest.mark.parametrize(
    ("field", "replacement"),
    (
        ("family", "event_relay"),
        ("project_uuid", PROJECT_B),
        ("attempt_id", "attempt-other"),
        ("native_identity", "native-other"),
    ),
)
def test_barrier_release_is_bound_to_every_transport_identity_field(
    tmp_path: Path,
    field: str,
    replacement: str,
) -> None:
    """T040: one mixed run cannot release another run's named window."""
    original_values = {
        "family": "direct_dispatcher",
        "project_uuid": PROJECT_A,
        "attempt_id": "attempt-original",
        "native_identity": "native-original",
    }
    other_values = {**original_values, field: replacement}
    original = ProcessTransportBarrier(
        tmp_path,
        BarrierIdentity(**original_values),
        BarrierPhase.TRANSPORT_STARTED,
    )
    other = ProcessTransportBarrier(
        tmp_path,
        BarrierIdentity(**other_values),
        BarrierPhase.TRANSPORT_STARTED,
    )

    original.controller_release()

    original.worker_wait_for_release(timeout=0.1)
    with pytest.raises(TimeoutError):
        other.worker_wait_for_release(timeout=0.02)


def _repo(tmp_path: Path, project_uuid: str) -> Path:
    root = tmp_path / f"repo-{project_uuid[0]}"
    config = root / ".kittify" / "config.yaml"
    config.parent.mkdir(parents=True)
    config.write_text(
        "\n".join(
            (
                "project:",
                f"  uuid: {project_uuid}",
                f"  slug: project-{project_uuid[0]}",
                "  node_id: node-wp09",
                "  repo_slug: private/wp09",
                "  build_id: build-wp09",
                "sync:",
                "  enabled: true",
                "",
            )
        ),
        encoding="utf-8",
    )
    return root


def _admitted_store(project_uuid: str) -> ProjectSyncStore:
    record_project_opt_in(project_uuid, actor="wp09-revocation")
    store = ProjectSyncStore(project_uuid)
    with store.unit_of_work() as unit:
        unit.execute(
            "INSERT INTO project_target_admissions "
            "(project_uuid, target_identity, account_identity, private_teamspace_id, "
            "configuration_generation, admission_state, admission_generation, binding_audience) "
            "VALUES (?, 'https://app.spec-kitty.ai', 'account-1', 'teamspace-1', 4, "
            "'admitted', '1', 'private-teamspace:teamspace-1')",
            (project_uuid,),
        )
    return store


def _spec(family: str, state: str) -> DeliveryAttemptSpec:
    return DeliveryAttemptSpec(
        attempt_id=f"{family}:{state}",
        write_kind=family,
        native_identity=f"native:{family}:{state}",
        payload_hash=f"sha256:{family}:{state}",
        payload_reference=f"payload:{family}:{state}",
        deadline_at="2999-01-01T00:00:00Z",
        reconciliation_policy="native_identity_query",
    )


def _prepare(store: ProjectSyncStore, spec: DeliveryAttemptSpec, *, unknown: bool) -> None:
    with acquire_project_transport_lease(store) as lease:
        with lease.unit_of_work() as (unit, context):
            prepare_delivery_attempt(unit, context, spec)
        if unknown:
            with lease.unit_of_work() as (unit, context):
                mark_transport_started(unit, context, spec.attempt_id)
                mark_delivery_result_unknown(
                    unit,
                    context,
                    attempt_id=spec.attempt_id,
                    reason="response_received_before_result",
                )


def _state(store: ProjectSyncStore, attempt_id: str) -> tuple[str, str | None] | None:
    with store.unit_of_work() as unit:
        row = unit.execute(
            "SELECT delivery_attempts.state, delivery_results.outcome "
            "FROM delivery_attempts LEFT JOIN delivery_results "
            "ON delivery_results.project_uuid = delivery_attempts.project_uuid "
            "AND delivery_results.attempt_id = delivery_attempts.attempt_id "
            "WHERE delivery_attempts.project_uuid = ? AND delivery_attempts.attempt_id = ? "
            "ORDER BY delivery_results.recorded_at DESC LIMIT 1",
            (store.project_uuid.storage_token, attempt_id),
        ).fetchone()
    return (str(row[0]), str(row[1]) if row[1] is not None else None) if row else None


def _production_attempt_id(store: ProjectSyncStore) -> str | None:
    with store.unit_of_work() as unit:
        row = unit.execute(
            "SELECT attempt_id FROM delivery_attempts WHERE project_uuid = ? ORDER BY created_at DESC LIMIT 1",
            (store.project_uuid.storage_token,),
        ).fetchone()
    return str(row[0]) if row is not None else None


def _assert_exact_authority(
    store: ProjectSyncStore,
    attempt_id: str,
    *,
    has_result: bool,
) -> None:
    with store.unit_of_work() as unit:
        row = unit.execute(
            "SELECT delivery_attempts.epoch_id, delivery_attempts.consent_generation, "
            "delivery_attempts.target_generation, delivery_attempts.admission_generation, "
            "delivery_attempts.binding_audience, delivery_results.epoch_id, "
            "delivery_results.target_generation, delivery_results.admission_generation "
            "FROM delivery_attempts LEFT JOIN delivery_results "
            "ON delivery_results.project_uuid = delivery_attempts.project_uuid "
            "AND delivery_results.attempt_id = delivery_attempts.attempt_id "
            "WHERE delivery_attempts.project_uuid = ? AND delivery_attempts.attempt_id = ?",
            (store.project_uuid.storage_token, attempt_id),
        ).fetchone()
    assert row is not None
    assert isinstance(row[0], int) and row[0] > 0
    assert tuple(row[1:5]) == (1, 4, "1", "private-teamspace:teamspace-1")
    assert tuple(row[5:]) == ((row[0], row[2], row[3]) if has_result else (None, None, None))


def _worker_script(
    root: Path,
    repo_root: Path,
    identity: BarrierIdentity,
    *,
    started: bool,
    outcome: str,
) -> str:
    phase = BarrierPhase.TRANSPORT_STARTED if started else BarrierPhase.AFTER_ATTEMPT_COMMIT_BEFORE_SEND
    return textwrap.dedent(
        f"""
        from pathlib import Path

        from tests.support.sync_transport_barriers import (
            BarrierIdentity,
            BarrierPhase,
            ProcessTransportBarrier,
            invoke_production_adapter,
        )

        identity = BarrierIdentity(
            family={identity.family!r},
            project_uuid={identity.project_uuid!r},
            attempt_id={identity.attempt_id!r},
            native_identity={identity.native_identity!r},
        )
        phase = BarrierPhase({phase.value!r})
        barrier = ProcessTransportBarrier(Path({str(root)!r}), identity, phase)
        invoke_production_adapter(
            Path({str(repo_root)!r}),
            identity,
            outcome={outcome!r},
            barrier=barrier,
        )
        """
    )


def _spawn_worker(
    root: Path,
    repo_root: Path,
    identity: BarrierIdentity,
    *,
    started: bool,
    outcome: str,
) -> tuple[subprocess.Popen[str], ProcessTransportBarrier]:
    phase = BarrierPhase.TRANSPORT_STARTED if started else BarrierPhase.AFTER_ATTEMPT_COMMIT_BEFORE_SEND
    barrier = ProcessTransportBarrier(root, identity, phase)
    process = subprocess.Popen(
        [
            sys.executable,
            "-c",
            _worker_script(
                root,
                repo_root,
                identity,
                started=started,
                outcome=outcome,
            ),
        ],
        cwd=Path.cwd(),
        env={**os.environ, "PYTHONPATH": str(Path.cwd())},
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    deadline = time.monotonic() + 45
    while not barrier.binding_path.exists():
        if process.poll() is not None:
            _stdout, stderr = process.communicate(timeout=5)
            raise AssertionError(f"{identity.family} worker exited before binding {phase.value}: {stderr}")
        if time.monotonic() >= deadline:
            process.kill()
            _stdout, stderr = process.communicate(timeout=5)
            raise TimeoutError(f"{identity.family} worker did not bind {phase.value}: {stderr}")
        time.sleep(0.01)
    barrier.controller_wait_for_binding(timeout=0.1)
    while not barrier.arrived_path.exists():
        if process.poll() is not None:
            _stdout, stderr = process.communicate(timeout=5)
            raise AssertionError(f"{identity.family} worker exited before {phase.value}: {stderr}")
        if time.monotonic() >= deadline:
            process.kill()
            _stdout, stderr = process.communicate(timeout=5)
            raise TimeoutError(f"{identity.family} worker did not reach {phase.value}: {stderr}")
        time.sleep(0.01)
    barrier.controller_wait_for_arrival(timeout=0.1)
    return process, barrier


def _finish(process: subprocess.Popen[str], *, success: bool) -> None:
    _stdout, stderr = process.communicate(timeout=15)
    if success:
        assert process.returncode == 0, stderr
    else:
        assert process.returncode != 0, "revoked worker unexpectedly reached transport"


def _project_b_progress(
    store: ProjectSyncStore,
    family: str,
    repo_root: Path,
) -> None:
    from unittest.mock import patch

    identity = BarrierIdentity(
        family=family,
        project_uuid=PROJECT_B,
        attempt_id=f"project-b:{family}",
        native_identity=f"project-b-native:{family}",
    )
    opened_projects: list[str] = []
    original_init = ProjectSyncStore.__init__

    def _record_open(active: ProjectSyncStore, project_uuid: object) -> None:
        opened_projects.append(str(project_uuid))
        original_init(active, project_uuid)

    with patch.object(ProjectSyncStore, "__init__", _record_open):
        evidence = invoke_production_adapter(repo_root, identity, outcome="delivered")
    assert opened_projects and set(opened_projects) == {PROJECT_B}
    assert evidence.succeeded is True
    assert evidence.request_bytes
    assert_exact_transport_evidence(evidence)
    attempt_id = _production_attempt_id(store)
    assert attempt_id is not None
    assert _state(store, attempt_id) == (
        DeliveryAttemptState.SUCCEEDED.value,
        DeliveryOutcome.DELIVERED.value,
    )
    _assert_exact_authority(store, attempt_id, has_result=True)


def test_public_opt_out_cancels_prepared_attempt_before_return(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Delegated WP07 control: public opt-out settles one canonical PREPARED row."""
    family = "canonical_settlement_control"
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / family / "runtime"))
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    store = _admitted_store(PROJECT_A)
    spec = _spec(family, "prepared")
    _prepare(store, spec, unknown=False)

    disable_checkout_sync(_repo(tmp_path / family, PROJECT_A), actor="wp09-revocation")

    assert _state(store, spec.attempt_id) == (DeliveryAttemptState.CANCELED.value, None)
    _assert_exact_authority(store, spec.attempt_id, has_result=False)


def test_public_opt_out_terminalizes_response_uncertainty_before_return(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Delegated WP07 control: public opt-out terminalizes canonical UNKNOWN."""
    family = "canonical_settlement_control"
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / family / "runtime"))
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    store = _admitted_store(PROJECT_A)
    spec = _spec(family, "unknown")
    _prepare(store, spec, unknown=True)

    disable_checkout_sync(_repo(tmp_path / family, PROJECT_A), actor="wp09-revocation")

    assert _state(store, spec.attempt_id) == (
        DeliveryAttemptState.TERMINAL_UNKNOWN.value,
        "terminal_unknown",
    )
    _assert_exact_authority(store, spec.attempt_id, has_result=True)


@pytest.mark.parametrize("family", TRANSPORT_FAMILIES)
def test_pause_before_transport_then_opt_out_is_zero_io_and_b_progresses(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    family: str,
) -> None:
    """T041 ordering one: opt-out cancels a barrier-paused durable attempt."""
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / family / "runtime"))
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    store_a = ProjectSyncStore(PROJECT_A) if family == "history_import" else _admitted_store(PROJECT_A)
    store_b = ProjectSyncStore(PROJECT_B) if family == "history_import" else _admitted_store(PROJECT_B)
    identity = BarrierIdentity(
        family=family,
        project_uuid=PROJECT_A,
        attempt_id=f"pause-before:{family}",
        native_identity=f"native:pause-before:{family}",
    )
    process, barrier = _spawn_worker(
        tmp_path / "barriers",
        _repo(tmp_path / family, PROJECT_A),
        identity,
        started=False,
        outcome="delivered",
    )
    _project_b_progress(store_b, family, _repo(tmp_path / "project-b", PROJECT_B))
    process.kill()
    _finish(process, success=False)
    disable_checkout_sync(_repo(tmp_path, PROJECT_A), actor="wp09-pause-before")
    actual_attempt_id = _production_attempt_id(store_a)
    assert actual_attempt_id is not None
    assert actual_attempt_id == barrier.identity.attempt_id

    if family == "event_relay":
        assert barrier.captured_delegation_bytes() is not None
        assert barrier.captured_bytes() is None
    else:
        assert barrier.captured_bytes() is None
    assert _state(store_a, actual_attempt_id) == (
        DeliveryAttemptState.CANCELED.value,
        None,
    )
    _assert_exact_authority(store_a, actual_attempt_id, has_result=False)


@pytest.mark.parametrize("family", TRANSPORT_FAMILIES)
@pytest.mark.parametrize("outcome", ("delivered", "duplicate", "refused", "timeout"))
def test_transport_started_then_opt_out_waits_for_genuine_result_and_b_progresses(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    family: str,
    outcome: str,
) -> None:
    """T041 ordering two: the real result lease settles before opt-out returns."""
    monkeypatch.setenv(
        "SPEC_KITTY_HOME",
        str(tmp_path / family / outcome / "runtime"),
    )
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    store_a = ProjectSyncStore(PROJECT_A) if family == "history_import" else _admitted_store(PROJECT_A)
    store_b = ProjectSyncStore(PROJECT_B) if family == "history_import" else _admitted_store(PROJECT_B)
    identity = BarrierIdentity(
        family=family,
        project_uuid=PROJECT_A,
        attempt_id=f"started:{family}:{outcome}",
        native_identity=f"native:started:{family}:{outcome}",
    )
    process, barrier = _spawn_worker(
        tmp_path / "barriers",
        _repo(tmp_path / family / outcome, PROJECT_A),
        identity,
        started=True,
        outcome=outcome,
    )
    actual_attempt_id = _production_attempt_id(store_a)
    assert actual_attempt_id is not None
    assert actual_attempt_id == barrier.identity.attempt_id
    entered = threading.Event()
    returned = threading.Event()

    def _opt_out() -> None:
        entered.set()
        disable_checkout_sync(_repo(tmp_path, PROJECT_A), actor="wp09-started")
        returned.set()

    opt_out_thread = threading.Thread(target=_opt_out, name=f"wp09-opt-out-{family}")
    opt_out_thread.start()
    assert entered.wait(5)
    assert not returned.wait(0.05), "opt-out returned while the result lease was live"
    _project_b_progress(store_b, family, _repo(tmp_path / "project-b", PROJECT_B))
    barrier.controller_release()
    _finish(process, success=True)
    opt_out_thread.join(timeout=10)
    assert returned.is_set(), "opt-out did not return after the result lease settled"

    assert barrier.captured_bytes() is not None
    expected = {
        "delivered": (DeliveryAttemptState.SUCCEEDED.value, "delivered"),
        "duplicate": (DeliveryAttemptState.SUCCEEDED.value, "duplicate"),
        "refused": (DeliveryAttemptState.REFUSED.value, "refused"),
        "timeout": (
            DeliveryAttemptState.TERMINAL_UNKNOWN.value,
            "terminal_unknown",
        ),
    }[outcome]
    assert _state(store_a, actual_attempt_id) == expected
    _assert_exact_authority(store_a, actual_attempt_id, has_result=True)
    assert_exact_transport_evidence(
        evidence_from_barrier(
            barrier,
            succeeded=True,
            outcome=outcome,
            result_expectation=(ResultExpectation.OPT_OUT_TERMINAL_UNKNOWN if outcome == "timeout" else ResultExpectation.COMPLETED),
            expected_result_outcome=("terminal_unknown" if outcome == "timeout" else outcome),
            hosted_reference_expectation=(
                HostedReferenceExpectation.REQUIRED
                if family in {"tracker_hosted", "generic_saas"} and outcome in {"delivered", "duplicate"}
                else HostedReferenceExpectation.ABSENT
            ),
        )
    )


@pytest.mark.parametrize("family", TRANSPORT_FAMILIES)
def test_public_opt_out_bounds_a_hung_live_holder_and_fences_late_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    family: str,
) -> None:
    """T041: a crashed-looking holder cannot indefinitely delay revocation."""
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / family / "runtime"))
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    store_a = ProjectSyncStore(PROJECT_A) if family == "history_import" else _admitted_store(PROJECT_A)
    store_b = ProjectSyncStore(PROJECT_B) if family == "history_import" else _admitted_store(PROJECT_B)
    identity = BarrierIdentity(
        family=family,
        project_uuid=PROJECT_A,
        attempt_id=f"hung-holder:{family}",
        native_identity=f"native:hung-holder:{family}",
    )
    process, barrier = _spawn_worker(
        tmp_path / "barriers",
        _repo(tmp_path / family, PROJECT_A),
        identity,
        started=True,
        outcome="delivered",
    )
    actual_attempt_id = _production_attempt_id(store_a)
    assert actual_attempt_id is not None
    assert actual_attempt_id == barrier.identity.attempt_id

    _project_b_progress(store_b, family, _repo(tmp_path / "project-b", PROJECT_B))
    started_at = time.monotonic()
    disable_checkout_sync(_repo(tmp_path, PROJECT_A), actor="wp09-hung-holder")
    elapsed = time.monotonic() - started_at

    assert elapsed < 8, "public opt-out exceeded its bounded lease wait"
    assert process.poll() is None, "the holder exited without controller release"
    assert _state(store_a, actual_attempt_id) == (
        DeliveryAttemptState.TERMINAL_UNKNOWN.value,
        DeliveryOutcome.TERMINAL_UNKNOWN.value,
    )
    _assert_exact_authority(store_a, actual_attempt_id, has_result=True)
    process.kill()
    _finish(process, success=False)
    barrier.controller_release()
    with (
        acquire_project_transport_lease(store_a) as lease,
        pytest.raises(ProjectStoreError),
        lease.unit_of_work() as (unit, context),
    ):
        record_delivery_result(
            unit,
            context,
            result_id=f"late-result:{actual_attempt_id}",
            attempt_id=actual_attempt_id,
            outcome=DeliveryOutcome.DELIVERED,
        )
    assert _state(store_a, actual_attempt_id) == (
        DeliveryAttemptState.TERMINAL_UNKNOWN.value,
        DeliveryOutcome.TERMINAL_UNKNOWN.value,
    )
