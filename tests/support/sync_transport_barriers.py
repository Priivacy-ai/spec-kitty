"""Deterministic, identity-bound process barriers for the WP09 matrices.

The barrier protocol uses controller-owned release files and worker-owned arrival
files.  Every filename is rooted below a digest of the complete transport
identity, while the full identity is repeated in the JSON marker.  A worker can
therefore neither release nor satisfy a barrier belonging to another project,
attempt, native correlation, or adapter family.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import time
from contextlib import ExitStack, contextmanager
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, cast

from charter.hasher import hash_content
from specify_cli.migration.envelope_seam import build_teamspace_envelope


class BarrierPhase(StrEnum):
    BEFORE_ATTEMPT_COMMIT = "before_attempt_commit"
    AFTER_ATTEMPT_COMMIT_BEFORE_SEND = "after_attempt_commit_before_send"
    TRANSPORT_STARTED = "transport_started"
    RESPONSE_RECEIVED_BEFORE_RESULT = "response_received_before_result"
    RESULT_COMMITTED = "result_committed"


class ResultExpectation(StrEnum):
    ABSENT = "absent"
    COMPLETED = "completed"
    ORDINARY_UNKNOWN = "ordinary_unknown"
    OPT_OUT_TERMINAL_UNKNOWN = "opt_out_terminal_unknown"


class HostedReferenceExpectation(StrEnum):
    ABSENT = "absent"
    REQUIRED = "required"


TRANSPORT_FAMILIES: tuple[str, ...] = (
    "direct_dispatcher",
    "emitter_websocket",
    "daemon_publish",
    "event_relay",
    "body_drain",
    "final_exit_sync",
    "reconnect_local_commit",
    "history_import",
    "tracker_hosted",
    "generic_saas",
)

# These loopback responses mirror the exact reviewed SaaS endpoint behavior at
# this immutable paired revision.  The cited endpoint tests were also executed
# directly against that revision with an isolated Django test database.  WP11,
# rather than this Core-only matrix, owns the live cross-repository deployment
# witness.
PAIRED_SAAS_REPLAY_SHA = "c3f39217aedea94a20802f9e9f2dbdeeecec3077"
PAIRED_SAAS_REPLAY_TREE = "e7f740319b8032a3b7991f590d289096eecdf5b9"
PAIRED_SAAS_SOURCE_BLOBS: tuple[tuple[str, str], ...] = (
    ("apps/connectors/runtime_push.py", "6473848a8137025e8bc66b0d6f62f5abe47f786b"),
    ("apps/connectors/tests/test_runtime_push.py", "15a0d9ee50c3405b11f1ca2e13dcb7be08664bce"),
    ("apps/collaboration/views.py", "b63eeee02999727fc1031d22d32ea2e127814eb3"),
    ("apps/collaboration/tests/test_widen_endpoint.py", "46c085b8c8eed5df3c5f1b5ca1b6fb2e98bd97be"),
)
PAIRED_SAAS_REPLAY_EVIDENCE: tuple[tuple[str, str], ...] = (
    (
        "tracker_hosted",
        "apps/connectors/tests/test_runtime_push.py::TrackerPushContractTests::test_duplicate_replay_returns_original_result",
    ),
    (
        "generic_saas",
        "apps/collaboration/tests/test_widen_endpoint.py::test_widen_view_200_idempotent_repeat",
    ),
)


@dataclass(frozen=True, slots=True)
class ProductionAdapterContract:
    family: str
    entrypoint: str
    physical_sink: str
    recovery_entrypoint: str
    delegation_sink: str | None = None


PRODUCTION_ADAPTER_CONTRACTS: tuple[ProductionAdapterContract, ...] = (
    ProductionAdapterContract(
        "direct_dispatcher",
        "specify_cli.delivery.dispatcher.dispatch",
        "specify_cli.delivery.receivers._HttpReceiver._attempt_batch_send",
        "specify_cli.delivery.dispatcher.dispatch",
    ),
    ProductionAdapterContract(
        "emitter_websocket",
        "specify_cli.sync.client.WebSocketClient.send_event",
        "specify_cli.sync.client.WebSocketClient._send_wire",
        "specify_cli.sync.client.WebSocketClient.send_event",
    ),
    ProductionAdapterContract(
        "daemon_publish",
        "specify_cli.sync.runtime.SyncRuntime.publish_event",
        "specify_cli.sync.client.WebSocketClient._send_wire",
        "specify_cli.sync.runtime.SyncRuntime.publish_event",
    ),
    ProductionAdapterContract(
        "event_relay",
        "specify_cli.sync.events.emit_wp_status_changed",
        "specify_cli.sync.client.WebSocketClient._send_wire",
        "specify_cli.sync.client.WebSocketClient._flush_pending_project_events",
        "urllib.request.urlopen",
    ),
    ProductionAdapterContract(
        "body_drain",
        "specify_cli.sync.body_transport.push_content_with_transport_gate",
        "specify_cli.sync.body_transport._send_content_request",
        "specify_cli.sync.body_transport.push_content_with_transport_gate",
    ),
    ProductionAdapterContract(
        "final_exit_sync",
        "specify_cli.cli.commands.sync._run_dispatch_batches",
        "specify_cli.delivery.receivers._HttpReceiver._attempt_batch_send",
        "specify_cli.cli.commands.sync._run_dispatch_batches",
    ),
    ProductionAdapterContract(
        "reconnect_local_commit",
        "specify_cli.sync.client.WebSocketClient.send_local_commit",
        "specify_cli.sync.client.WebSocketClient._send_wire",
        "specify_cli.sync.client.WebSocketClient.send_local_commit",
    ),
    ProductionAdapterContract(
        "history_import",
        "specify_cli.sync.history_import.upload.upload_envelopes",
        "specify_cli.delivery.receivers._HttpReceiver._attempt_batch_send",
        "specify_cli.sync.history_import.upload.upload_envelopes",
    ),
    ProductionAdapterContract(
        "tracker_hosted",
        "specify_cli.tracker.saas_client.SaaSTrackerClient.push",
        "specify_cli.tracker.saas_client.SaaSTrackerClient._physical_request_with_retry",
        "specify_cli.tracker.saas_client.SaaSTrackerClient.push",
    ),
    ProductionAdapterContract(
        "generic_saas",
        "specify_cli.saas_client.client.SaasClient.post_widen",
        "httpx.Client.post",
        "specify_cli.saas_client.client.SaasClient.post_widen",
    ),
)


class PhysicalSinkPoison(RuntimeError):
    """Raised only after one real public adapter reaches its physical sink."""


@dataclass(frozen=True, slots=True)
class ProductionAdapterEvidence:
    family: str
    entrypoint: str
    physical_sink: str
    seed_identity: BarrierIdentity
    actual_identity: BarrierIdentity
    request_bytes: bytes
    delegation_bytes: bytes
    succeeded: bool
    requested_outcome: str
    expected_attempt_present: bool
    result_expectation: ResultExpectation
    expected_result_outcome: str | None
    hosted_reference_expectation: HostedReferenceExpectation


@dataclass(frozen=True, slots=True)
class PersistedAttemptEvidence:
    attempt_id: str
    project_uuid: str
    epoch_id: int
    consent_generation: int
    target_generation: int
    admission_generation: str
    binding_audience: str
    payload_hash: str
    payload_reference: str
    reconciliation_policy: str
    state: str
    metadata: dict[str, Any]
    result_id: str | None
    result_outcome: str | None
    result_epoch_id: int | None
    result_target_generation: int | None
    result_admission_generation: str | None


def read_persisted_attempt(evidence: ProductionAdapterEvidence) -> PersistedAttemptEvidence:
    """Read exactly the row bound into the physical evidence, never latest-row."""
    from specify_cli.sync.project_store import ProjectSyncStore

    identity = evidence.actual_identity
    store = ProjectSyncStore(identity.project_uuid)
    with store.unit_of_work() as unit:
        row = unit.execute(
            "SELECT delivery_attempts.attempt_id, delivery_attempts.project_uuid, "
            "delivery_attempts.epoch_id, delivery_attempts.consent_generation, "
            "delivery_attempts.target_generation, delivery_attempts.admission_generation, "
            "delivery_attempts.binding_audience, delivery_attempts.payload_hash, "
            "delivery_attempts.payload_reference, delivery_attempts.reconciliation_policy, "
            "delivery_attempts.state, delivery_results.result_id, delivery_results.outcome, "
            "delivery_results.epoch_id, delivery_results.target_generation, "
            "delivery_results.admission_generation FROM delivery_attempts "
            "LEFT JOIN delivery_results ON delivery_results.project_uuid = delivery_attempts.project_uuid "
            "AND delivery_results.attempt_id = delivery_attempts.attempt_id "
            "WHERE delivery_attempts.project_uuid = ? AND delivery_attempts.attempt_id = ? "
            "ORDER BY delivery_results.recorded_at DESC LIMIT 1",
            (identity.project_uuid, identity.attempt_id),
        ).fetchone()
    if row is None:
        raise AssertionError("physical evidence does not name a durable attempt row")
    metadata = json.loads(str(row[8]))
    if not isinstance(metadata, dict):
        raise AssertionError("durable attempt metadata is not an object")
    return PersistedAttemptEvidence(
        attempt_id=str(row[0]),
        project_uuid=str(row[1]),
        epoch_id=int(row[2]),
        consent_generation=int(row[3]),
        target_generation=int(row[4]),
        admission_generation=str(row[5]),
        binding_audience=str(row[6]),
        payload_hash=str(row[7]),
        payload_reference=str(metadata.get("payload_reference") or ""),
        reconciliation_policy=str(row[9]),
        state=str(row[10]),
        metadata=cast("dict[str, Any]", metadata),
        result_id=str(row[11]) if row[11] is not None else None,
        result_outcome=str(row[12]) if row[12] is not None else None,
        result_epoch_id=int(row[13]) if row[13] is not None else None,
        result_target_generation=int(row[14]) if row[14] is not None else None,
        result_admission_generation=str(row[15]) if row[15] is not None else None,
    )


_EVENT_WIRE_KEYS = frozenset(
    {
        "admission_generation",
        "aggregate_id",
        "aggregate_type",
        "binding_audience",
        "build_id",
        "causation_id",
        "correlation_id",
        "drain_blocked_reason",
        "event_id",
        "event_type",
        "git_branch",
        "head_commit_sha",
        "lamport_clock",
        "node_id",
        "payload",
        "project_slug",
        "project_uuid",
        "repo_slug",
        "schema_version",
        "spec_kitty_delivery_identity",
        "team_slug",
        "timestamp",
        "type",
    }
)
_HISTORY_EVENT_WIRE_KEYS = _EVENT_WIRE_KEYS - {
    "spec_kitty_delivery_identity",
    "type",
}
_LOCAL_COMMIT_WIRE_KEYS = frozenset(
    {
        "admission_generation",
        "binding_audience",
        "build_id",
        "changed_files",
        "committed_at",
        "git_hash",
        "mission_id",
        "project_uuid",
        "spec_kitty_delivery_identity",
        "type",
    }
)
_BODY_WIRE_KEYS = frozenset(
    {
        "admission_generation",
        "artifact_path",
        "binding_audience",
        "content_body",
        "content_hash",
        "hash_algorithm",
        "manifest_version",
        "mission_slug",
        "mission_type",
        "project_uuid",
        "target_branch",
    }
)


def _strict_json_object(raw: bytes, expected_keys: frozenset[str]) -> dict[str, Any]:
    value = json.loads(raw)
    if not isinstance(value, dict) or frozenset(value) != expected_keys:
        raise AssertionError(
            f"transport object keys differ: expected {sorted(expected_keys)}, observed {sorted(value) if isinstance(value, dict) else type(value).__name__}"
        )
    return cast("dict[str, Any]", value)


def canonical_transport_payload(evidence: ProductionAdapterEvidence) -> dict[str, Any]:
    """Strictly decode one physical request, rejecting partial-byte witnesses."""
    family = evidence.family
    if family in {"direct_dispatcher", "final_exit_sync", "history_import"}:
        batch = _strict_json_object(gzip.decompress(evidence.request_bytes), frozenset({"events"}))
        events = batch["events"]
        if not isinstance(events, list) or len(events) != 1 or not isinstance(events[0], dict):
            raise AssertionError("receiver request must contain exactly one event")
        event = cast("dict[str, Any]", events[0])
        expected_event_keys = _HISTORY_EVENT_WIRE_KEYS if family == "history_import" else _EVENT_WIRE_KEYS
        if frozenset(event) != expected_event_keys:
            raise AssertionError(f"receiver event is not the exact closed wire envelope: {sorted(event)}")
        return event
    if family in {"emitter_websocket", "daemon_publish", "event_relay"}:
        event = _strict_json_object(evidence.request_bytes, _EVENT_WIRE_KEYS)
        if family == "event_relay":
            delegated = _strict_json_object(
                evidence.delegation_bytes,
                frozenset({"event", "token"}),
            )
            local_event = delegated["event"]
            if not isinstance(local_event, dict):
                raise AssertionError("relay delegation omitted its Event")
            if event["event_id"] != local_event.get("event_id"):
                raise AssertionError("relay downstream Event differs from local delegation")
        return event
    if family == "reconnect_local_commit":
        return _strict_json_object(evidence.request_bytes, _LOCAL_COMMIT_WIRE_KEYS)
    if family == "body_drain":
        return _strict_json_object(evidence.request_bytes, _BODY_WIRE_KEYS)
    if family == "generic_saas":
        return _strict_json_object(
            evidence.request_bytes,
            frozenset({"json", "method", "native_identity", "url"}),
        )
    if family == "tracker_hosted":
        request = _strict_json_object(
            evidence.request_bytes,
            frozenset({"headers", "json", "method", "path"}),
        )
        headers = request["headers"]
        if not isinstance(headers, dict) or frozenset(headers) != {"Idempotency-Key"}:
            raise AssertionError("tracker physical request omitted exact native header")
        return request
    raise AssertionError(f"unclassified production adapter family: {family}")


def _raw_sha256(raw: bytes) -> str:
    """Mirror protocol SHA-256 over exact bytes, without charter normalization."""
    return hashlib.sha256(raw).hexdigest()  # noqa: TID251 - transport protocol digest


def _stable_id(*parts: object) -> str:
    return _raw_sha256("\x1f".join(str(part) for part in parts).encode("utf-8"))


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _current_expected_target(project_uuid: str) -> Any:
    """Read the admitted target independently from the attempt under review."""
    from specify_cli.delivery.targets import ProjectDeliveryTargetRegistry
    from specify_cli.sync.project_store import ProjectSyncStore

    store = ProjectSyncStore(project_uuid)
    with store.unit_of_work() as unit:
        target = ProjectDeliveryTargetRegistry(store).get_current(unit)
    if target is None:
        raise AssertionError("independent expectation found no project target")
    exact_authority = (
        target.target_identity,
        target.account_identity,
        target.private_teamspace_id,
        target.project_uuid.storage_token,
        target.configuration_generation,
        target.admission_generation,
        target.binding_audience,
    )
    if exact_authority != (
        "https://app.spec-kitty.ai",
        "account-1",
        "teamspace-1",
        project_uuid,
        4,
        1,
        "private-teamspace:teamspace-1",
    ):
        raise AssertionError(f"independent target authority drifted: {exact_authority!r}")
    return target


def _event_wire(base: dict[str, Any]) -> dict[str, Any]:
    event_id = str(base["event_id"])
    return {
        **base,
        "project_uuid": str(base["project_uuid"]),
        "type": "event",
        "spec_kitty_delivery_identity": event_id,
        "admission_generation": 1,
        "binding_audience": "private-teamspace:teamspace-1",
    }


def _relay_event_id(seed: BarrierIdentity) -> str:
    material = _canonical_json(asdict(seed)).encode("utf-8")
    return "01" + _raw_sha256(material).upper()[:24]


def _relay_event(seed: BarrierIdentity) -> dict[str, Any]:
    event_id = _relay_event_id(seed)
    event: dict[str, Any] = build_teamspace_envelope(
        event_id=event_id,
        event_type="WPStatusChanged",
        aggregate_id="WP09",
        aggregate_type="WorkPackage",
        build_id="build-wp09",
        payload={
            "actor": "wp09-adapter-matrix",
            "execution_mode": "direct_repo",
            "force": False,
            "from_lane": "in_progress",
            "mission_slug": "unknown-mission",
            "to_lane": "for_review",
            "wp_id": "WP09",
        },
        node_id="node-wp09",
        lamport_clock=1,
        causation_id=None,
        correlation_id=event_id,
        timestamp="2026-08-11T20:00:00+00:00",
        project_uuid=seed.project_uuid,
        project_slug="project-a",
        repo_slug="private/wp09",
    ).model_dump()
    event.update(
        team_slug="teamspace-1",
        git_branch="develop",
        head_commit_sha="a" * 40,
        drain_blocked_reason=None,
    )
    return event


def _history_expectation(
    evidence: ProductionAdapterEvidence,
    *,
    target_id: str,
) -> tuple[dict[str, Any], str, str, str]:
    base = _event_frame(evidence.actual_identity)
    payload = {
        **base,
        "admission_generation": 1,
        "binding_audience": "private-teamspace:teamspace-1",
    }
    stored = _canonical_json(base)
    content_hash = _raw_sha256(stored.encode("utf-8"))
    preview_hash = _raw_sha256(_canonical_json([{"content_hash": content_hash, "row_id": evidence.actual_identity.native_identity}]).encode("ascii"))
    action_id = "history-" + _raw_sha256(f"{evidence.actual_identity.project_uuid}\0history:{evidence.actual_identity.native_identity}".encode())
    payload_hash = "sha256:" + _raw_sha256(_canonical_json(payload).encode("utf-8"))
    reference = _canonical_json(
        {
            "history_action_id": action_id,
            "preview_hash": preview_hash,
            "native_identity": evidence.actual_identity.native_identity,
            "disclosed_sha256": payload_hash,
            "sink": "history_upload",
            "target_id": target_id,
        }
    )
    attempt_id = "history_upload:" + _stable_id(
        action_id,
        target_id,
        evidence.actual_identity.native_identity,
        payload_hash,
    )
    return payload, payload_hash, reference, attempt_id


def _hosted_terminal_response(evidence: ProductionAdapterEvidence) -> dict[str, Any]:
    if evidence.family == "generic_saas":
        return {
            "decision_id": "decision-wp09",
            "widened_at": "2026-08-11T20:00:00Z",
            "widened_by": 1,
            "invited_user_ids": [1],
            "idempotent": evidence.requested_outcome == "duplicate",
            "participation_row_ids": ["participation-wp09"],
            "audit_snapshot_id": "snapshot-wp09",
            "slack_thread_status": None,
        }
    return {
        "status": "ok",
        "summary": {"total": 1, "succeeded": 1, "failed": 0},
        "items": [
            {
                "ref": {
                    "system": "github",
                    "workspace": "",
                    "id": evidence.seed_identity.native_identity,
                },
                "action": "update",
                "outcome": "ok",
            }
        ],
        "identity_path": {"kind": "user_link"},
    }


def paired_saas_contract_snapshot() -> dict[str, Any]:
    """Closed c3 endpoint evidence whose literal digest is reviewed in Core."""
    seed = BarrierIdentity("tracker_hosted", "{project_uuid}", "{attempt_id}", "{caller_item_id}")
    tracker = ProductionAdapterEvidence(
        family="tracker_hosted",
        entrypoint="",
        physical_sink="",
        seed_identity=seed,
        actual_identity=seed,
        request_bytes=b"",
        delegation_bytes=b"",
        succeeded=True,
        requested_outcome="duplicate",
        expected_attempt_present=True,
        result_expectation=ResultExpectation.COMPLETED,
        expected_result_outcome="duplicate",
        hosted_reference_expectation=HostedReferenceExpectation.REQUIRED,
    )
    generic_seed = BarrierIdentity("generic_saas", "{project_uuid}", "{attempt_id}", "{native_identity}")
    generic = ProductionAdapterEvidence(
        family="generic_saas",
        entrypoint="",
        physical_sink="",
        seed_identity=generic_seed,
        actual_identity=generic_seed,
        request_bytes=b"",
        delegation_bytes=b"",
        succeeded=True,
        requested_outcome="duplicate",
        expected_attempt_present=True,
        result_expectation=ResultExpectation.COMPLETED,
        expected_result_outcome="duplicate",
        hosted_reference_expectation=HostedReferenceExpectation.REQUIRED,
    )
    return {
        "commit": PAIRED_SAAS_REPLAY_SHA,
        "tree": PAIRED_SAAS_REPLAY_TREE,
        "source_blobs": dict(PAIRED_SAAS_SOURCE_BLOBS),
        "generic_saas": {
            "method": "POST",
            "url": "https://app.spec-kitty.ai/a/teamspace-1/collaboration/decision-points/decision-wp09/widen",
            "request": {"invited_user_ids": [1]},
            "duplicate_response": _hosted_terminal_response(generic),
            "replay_header": {"Idempotency-Replayed": "true"},
        },
        "tracker_hosted": {
            "method": "POST",
            "url": "https://app.spec-kitty.ai/api/v1/tracker/push/",
            "request": {
                "provider": "github",
                "project_slug": "project-wp09",
                "items": [{"id": "{caller_item_id}"}],
            },
            "duplicate_response": _hosted_terminal_response(tracker),
            "replay_header": {"Idempotency-Replayed": "true"},
        },
    }


PAIRED_SAAS_CONTRACT_DIGEST = "ed34b5a65e0969f9039de1e5547ada73db039bfde2f71a1c6a04430ac7b29762"


def paired_saas_contract_digest() -> str:
    return _raw_sha256(_canonical_json(paired_saas_contract_snapshot()).encode("utf-8"))


def _independent_expectation(  # noqa: C901 - ten closed transport contracts are intentionally explicit.
    evidence: ProductionAdapterEvidence,
) -> tuple[dict[str, Any], str, str, str, str]:
    identity = evidence.actual_identity
    target = _current_expected_target(identity.project_uuid)
    target_id = str(target.target_id)
    family = evidence.family
    if family in {
        "direct_dispatcher",
        "emitter_websocket",
        "daemon_publish",
        "final_exit_sync",
    }:
        payload = _event_wire(_event_frame(identity))
        native_identity = identity.native_identity
        payload_hash = "sha256:" + _raw_sha256(_canonical_json(payload).encode("utf-8"))
        reference = _canonical_json({"event_id": native_identity, "schema": "spec-kitty.dispatcher.v1", "target_id": target_id})
        attempt_id = "event:" + _stable_id("attempt", identity.project_uuid, target_id, native_identity)
    elif family == "event_relay":
        local_event = _relay_event(evidence.seed_identity)
        payload = _event_wire(local_event)
        native_identity = str(local_event["event_id"])
        payload_hash = "sha256:" + _raw_sha256(_canonical_json(payload).encode("utf-8"))
        reference = _canonical_json({"event_id": native_identity, "schema": "spec-kitty.dispatcher.v1", "target_id": target_id})
        attempt_id = "event:" + _stable_id("attempt", identity.project_uuid, target_id, native_identity)
        delegated = _strict_json_object(evidence.delegation_bytes, frozenset({"event", "token"}))
        if delegated != {"event": local_event, "token": "wp09-loopback-token"}:
            raise AssertionError(f"relay local delegation differs from its exact public call: observed={delegated!r}, expected_event={local_event!r}")
    elif family == "reconnect_local_commit":
        native_identity = f"local-commit:{target_id}:build-wp09:{'a' * 40}"
        payload = {
            "type": "LocalCommit",
            "git_hash": "a" * 40,
            "mission_id": "01KZWP09MISSION0000000001",
            "build_id": "build-wp09",
            "changed_files": ["kitty-specs/wp09/spec.md"],
            "committed_at": "2026-08-11T20:00:00Z",
            "spec_kitty_delivery_identity": native_identity,
            "project_uuid": identity.project_uuid,
            "admission_generation": 1,
            "binding_audience": "private-teamspace:teamspace-1",
        }
        payload_hash = "sha256:" + _raw_sha256(_canonical_json(payload).encode("utf-8"))
        reference = _canonical_json(
            {
                "schema": "spec-kitty.local-commit.v1",
                "project_uuid": identity.project_uuid,
                "build_id": "build-wp09",
                "git_hash": "a" * 40,
                "target_id": target_id,
            }
        )
        attempt_id = "local-commit:" + _stable_id("attempt", identity.project_uuid, target_id, "build-wp09", "a" * 40)
    elif family == "body_drain":
        native_identity = "body-upload:" + _stable_id(identity.project_uuid, target_id, "kitty-specs/wp09/spec.md", "abc123")
        payload = {
            "admission_generation": 1,
            "artifact_path": "kitty-specs/wp09/spec.md",
            "binding_audience": "private-teamspace:teamspace-1",
            "content_body": "# WP09",
            "content_hash": "abc123",
            "hash_algorithm": "sha256",
            "manifest_version": "1",
            "mission_slug": "wp09",
            "mission_type": "software-dev",
            "project_uuid": identity.project_uuid,
            "target_branch": "develop",
        }
        payload_hash = "sha256:" + _raw_sha256(_canonical_json(payload).encode("utf-8"))
        reference = _canonical_json(
            {
                "admission_generation": 1,
                "artifact_path": "kitty-specs/wp09/spec.md",
                "binding_audience": "private-teamspace:teamspace-1",
                "content_hash": "abc123",
            }
        )
        attempt_id = "body-upload:" + _stable_id("attempt", identity.project_uuid, target_id, "kitty-specs/wp09/spec.md", "abc123")
    elif family == "history_import":
        native_identity = identity.native_identity
        payload, payload_hash, reference, attempt_id = _history_expectation(evidence, target_id=target_id)
    elif family == "generic_saas":
        payload = {
            "method": "POST",
            "url": "https://app.spec-kitty.ai/a/teamspace-1/collaboration/decision-points/decision-wp09/widen",
            "json": {"invited_user_ids": [1]},
            "native_identity": identity.native_identity,
        }
        reference = _canonical_json({"method": payload["method"], "url": payload["url"], "json": payload["json"]})
        payload_hash = _raw_sha256(reference.encode("utf-8"))
        semantic_key = f"POST:{payload['url']}:payload:{payload_hash}"
        attempt_id = "logical-operation:write:" + _stable_id(
            identity.project_uuid,
            "generic_saas_post",
            semantic_key,
            "idempotent_write",
        )
        native_identity = attempt_id
    else:
        tracker_body = {
            "provider": "github",
            "project_slug": "project-wp09",
            "items": [{"id": evidence.seed_identity.native_identity}],
        }
        tracker_url = "https://app.spec-kitty.ai/api/v1/tracker/push/"
        tracker_path = "/api/v1/tracker/push/"
        body = json.dumps(tracker_body, separators=(",", ":"))
        payload = {
            "headers": {"Idempotency-Key": identity.native_identity},
            "json": tracker_body,
            "method": "POST",
            "path": tracker_path,
        }
        reference = _canonical_json({"method": "POST", "url": tracker_url, "body": body})
        payload_hash = _raw_sha256(f"POST\n{tracker_url}\n{body}".encode())
        semantic_key = "\x1f".join(("POST", tracker_path, tracker_url, f"payload:{payload_hash}"))
        attempt_id = "logical-operation:write:" + _stable_id(
            identity.project_uuid,
            "tracker_hosted_push",
            semantic_key,
            "idempotent_write",
        )
        native_identity = attempt_id
    return payload, payload_hash, reference, attempt_id, native_identity


def assert_transport_evidence_values(  # noqa: C901 - exact closed result/reference contracts differ by family.
    evidence: ProductionAdapterEvidence,
    attempt: PersistedAttemptEvidence,
) -> tuple[dict[str, Any], PersistedAttemptEvidence]:
    """Compare physical and durable evidence to an independently built contract."""
    if not evidence.expected_attempt_present:
        raise AssertionError("physical transport evidence cannot claim an absent attempt")
    payload = canonical_transport_payload(evidence)
    expected_payload, expected_hash, expected_reference, expected_attempt_id, expected_native = _independent_expectation(evidence)
    if payload != expected_payload:
        raise AssertionError("physical request differs from independent public-call expectation")
    identity = evidence.actual_identity
    if identity != BarrierIdentity(evidence.family, identity.project_uuid, expected_attempt_id, expected_native):
        raise AssertionError("production identity differs from independent native/attempt derivation")
    expected_write_kind = {
        "direct_dispatcher": "event",
        "emitter_websocket": "event",
        "daemon_publish": "event",
        "event_relay": "event",
        "body_drain": "body_upload",
        "final_exit_sync": "event",
        "reconnect_local_commit": "local_commit",
        "history_import": "history_upload",
        "tracker_hosted": "tracker_hosted_push",
        "generic_saas": "generic_saas_post",
    }[evidence.family]
    expected_epoch = 2 if evidence.family == "history_import" else 1
    exact_metadata = {
        "account_identity": "account-1",
        "admission_generation": "1",
        "binding_audience": "private-teamspace:teamspace-1",
        "consent_generation": "1",
        "epoch_id": str(expected_epoch),
        "native_identity": expected_native,
        "payload_reference": expected_reference,
        "private_teamspace_id": "teamspace-1",
        "project_uuid": identity.project_uuid,
        "target_generation": "4",
        "target_identity": "https://app.spec-kitty.ai",
        "write_kind": expected_write_kind,
    }
    for key, expected in exact_metadata.items():
        if attempt.metadata.get(key) != expected:
            raise AssertionError(f"durable {key} differs from independent disclosure: {attempt.metadata.get(key)!r} != {expected!r}")
    expected_policy = "terminalized:explicit_opt_out" if attempt.state == "terminal_unknown" else attempt.metadata.get("reconciliation_policy")
    if (
        attempt.attempt_id != expected_attempt_id
        or attempt.project_uuid != identity.project_uuid
        or attempt.epoch_id != expected_epoch
        or attempt.consent_generation != 1
        or attempt.target_generation != 4
        or attempt.admission_generation != "1"
        or attempt.binding_audience != "private-teamspace:teamspace-1"
        or attempt.payload_hash != expected_hash
        or attempt.payload_reference != expected_reference
        or attempt.reconciliation_policy != expected_policy
    ):
        raise AssertionError("durable attempt columns differ from independent authority")
    if evidence.result_expectation is ResultExpectation.ABSENT:
        if any(
            value is not None
            for value in (
                attempt.result_id,
                attempt.result_outcome,
                attempt.result_epoch_id,
                attempt.result_target_generation,
                attempt.result_admission_generation,
            )
        ):
            raise AssertionError("scenario requires no durable result")
        expected_result_id = None
    else:
        if evidence.expected_result_outcome is None:
            raise AssertionError("result-bearing scenario omitted its expected outcome")
        suffix = ":terminal-unknown" if evidence.result_expectation is ResultExpectation.OPT_OUT_TERMINAL_UNKNOWN else ":result"
        expected_result_id = expected_attempt_id + suffix
    if evidence.result_expectation is not ResultExpectation.ABSENT and (
        attempt.result_id != expected_result_id
        or attempt.result_outcome != evidence.expected_result_outcome
        or attempt.result_epoch_id != expected_epoch
        or attempt.result_target_generation != 4
        or attempt.result_admission_generation != "1"
    ):
        raise AssertionError(
            "result identity/outcome/authority differs from public-call expectation: "
            f"id={attempt.result_id!r}/{expected_result_id!r}, "
            f"outcome={attempt.result_outcome!r}/{evidence.expected_result_outcome!r}, "
            f"epoch={attempt.result_epoch_id!r}/{expected_epoch!r}, "
            f"target={attempt.result_target_generation!r}/4, "
            f"admission={attempt.result_admission_generation!r}/'1'"
        )
    terminal_reference = attempt.metadata.get("terminal_response_reference")
    if evidence.hosted_reference_expectation is HostedReferenceExpectation.REQUIRED:
        if evidence.family not in {"generic_saas", "tracker_hosted"}:
            raise AssertionError("non-hosted scenario requested a hosted terminal reference")
        expected_terminal = _canonical_json(_hosted_terminal_response(evidence))
        if terminal_reference != expected_terminal:
            raise AssertionError("hosted terminal response differs from pinned c3 value contract")
    elif terminal_reference is not None:
        raise AssertionError("non-hosted or non-success result invented a terminal response reference")
    return payload, attempt


def assert_exact_transport_evidence(
    evidence: ProductionAdapterEvidence,
) -> tuple[dict[str, Any], PersistedAttemptEvidence]:
    """Read the exact durable row, then apply the independent value oracle."""
    return assert_transport_evidence_values(evidence, read_persisted_attempt(evidence))


def _contract(family: str) -> ProductionAdapterContract:
    for contract in PRODUCTION_ADAPTER_CONTRACTS:
        if contract.family == family:
            return contract
    raise ValueError(f"unknown production adapter family: {family}")


def evidence_from_barrier(
    barrier: ProcessTransportBarrier,
    *,
    succeeded: bool = False,
    outcome: str = "delivered",
    result_expectation: ResultExpectation,
    expected_result_outcome: str | None,
    hosted_reference_expectation: HostedReferenceExpectation = HostedReferenceExpectation.ABSENT,
) -> ProductionAdapterEvidence:
    """Rehydrate subprocess evidence only after production identity binding."""
    request_bytes = barrier.captured_bytes()
    if request_bytes is None:
        raise AssertionError("barrier has no physical transport capture")
    contract = _contract(barrier.identity.family)
    return ProductionAdapterEvidence(
        family=contract.family,
        entrypoint=contract.entrypoint,
        physical_sink=contract.physical_sink,
        seed_identity=barrier.seed_identity,
        actual_identity=barrier.identity,
        request_bytes=request_bytes,
        delegation_bytes=barrier.captured_delegation_bytes() or b"",
        succeeded=succeeded,
        requested_outcome=outcome,
        expected_attempt_present=True,
        result_expectation=result_expectation,
        expected_result_outcome=expected_result_outcome,
        hosted_reference_expectation=hosted_reference_expectation,
    )


@dataclass(frozen=True)
class BarrierIdentity:
    family: str
    project_uuid: str
    attempt_id: str
    native_identity: str

    def __post_init__(self) -> None:
        values = asdict(self)
        if self.family not in TRANSPORT_FAMILIES:
            raise ValueError(f"unknown transport family: {self.family}")
        if any(not value.strip() for value in values.values()):
            raise ValueError("barrier identity fields must be non-empty")

    @property
    def token(self) -> str:
        encoded = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return cast("str", hash_content(encoded)).removeprefix("sha256:")


class ProcessTransportBarrier:
    """A reusable exact barrier that negotiates production-minted identity.

    ``identity`` is only the caller's rendezvous seed until the production
    attempt hook supplies the durable attempt/native tuple.  Arrival, capture,
    and release files are always rooted under that bound production identity;
    the seed is never accepted as transport correlation by itself.
    """

    def __init__(self, root: Path, identity: BarrierIdentity, phase: BarrierPhase) -> None:
        self._base_root = root
        self.seed_identity = identity
        self.root = root / identity.token
        self.identity = identity
        self.phase = phase

    @property
    def binding_path(self) -> Path:
        return self._base_root / self.seed_identity.token / f"{self.phase.value}.bound.json"

    def bind_production_identity(self, identity: BarrierIdentity) -> None:
        """Bind this rendezvous to one exact persisted production attempt."""
        if identity.family != self.seed_identity.family:
            raise AssertionError("production barrier family drift")
        if identity.project_uuid != self.seed_identity.project_uuid:
            raise AssertionError("production barrier project drift")
        payload = {
            "seed": asdict(self.seed_identity),
            "actual": asdict(identity),
            "phase": self.phase.value,
        }
        self.binding_path.parent.mkdir(parents=True, exist_ok=True)
        if self.binding_path.exists():
            if json.loads(self.binding_path.read_text(encoding="utf-8")) != payload:
                raise AssertionError("production barrier rebound to a different attempt")
        else:
            temporary = self.binding_path.with_suffix(f".tmp-{os.getpid()}")
            temporary.write_text(
                json.dumps(payload, sort_keys=True, separators=(",", ":")),
                encoding="utf-8",
            )
            temporary.replace(self.binding_path)
        self.identity = identity
        self.root = self._base_root / identity.token

    def controller_wait_for_binding(self, *, timeout: float = 10.0) -> BarrierIdentity:
        """Resolve the production tuple before waiting on its actual barrier."""
        deadline = time.monotonic() + timeout
        while not self.binding_path.exists():
            if time.monotonic() >= deadline:
                raise TimeoutError("timed out waiting for production barrier identity")
            time.sleep(0.005)
        payload = json.loads(self.binding_path.read_text(encoding="utf-8"))
        expected_seed = asdict(self.seed_identity)
        if payload.get("seed") != expected_seed or payload.get("phase") != self.phase.value:
            raise AssertionError("production barrier binding does not match its rendezvous")
        actual = payload.get("actual")
        if not isinstance(actual, dict):
            raise AssertionError("production barrier binding omitted actual identity")
        identity = BarrierIdentity(**actual)
        self.bind_production_identity(identity)
        return identity

    @property
    def arrived_path(self) -> Path:
        return self.root / f"{self.phase.value}.arrived.json"

    @property
    def release_path(self) -> Path:
        return self.root / f"{self.phase.value}.release.json"

    @property
    def capture_path(self) -> Path:
        return self.root / f"{self.phase.value}.transport.bin"

    @property
    def delegation_capture_path(self) -> Path:
        return self._base_root / self.seed_identity.token / f"{self.phase.value}.delegation.bin"

    def worker_arrive(self) -> None:
        self._write_marker(self.arrived_path, actor="worker")

    def controller_release(self) -> None:
        self._write_marker(self.release_path, actor="controller")

    def worker_wait_for_release(self, *, timeout: float = 10.0) -> None:
        self._wait_for(self.release_path, actor="controller", timeout=timeout)

    def controller_wait_for_arrival(self, *, timeout: float = 10.0) -> None:
        self._wait_for(self.arrived_path, actor="worker", timeout=timeout)

    def arrive_and_wait(self, *, timeout: float = 10.0) -> None:
        self.worker_arrive()
        self.worker_wait_for_release(timeout=timeout)

    def capture(self, payload: bytes) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        temporary = self.capture_path.with_suffix(f".tmp-{os.getpid()}")
        temporary.write_bytes(payload)
        temporary.replace(self.capture_path)

    def captured_bytes(self) -> bytes | None:
        return self.capture_path.read_bytes() if self.capture_path.exists() else None

    def capture_delegation(self, payload: bytes) -> None:
        self.delegation_capture_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.delegation_capture_path.with_suffix(f".tmp-{os.getpid()}")
        temporary.write_bytes(payload)
        temporary.replace(self.delegation_capture_path)

    def captured_delegation_bytes(self) -> bytes | None:
        return self.delegation_capture_path.read_bytes() if self.delegation_capture_path.exists() else None

    def _payload(self, actor: str) -> dict[str, str]:
        return {
            **asdict(self.identity),
            "actor": actor,
            "phase": self.phase.value,
            "token": self.identity.token,
        }

    def _write_marker(self, path: Path, *, actor: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(f".tmp-{os.getpid()}")
        temporary.write_text(
            json.dumps(self._payload(actor), sort_keys=True, separators=(",", ":")),
            encoding="utf-8",
        )
        temporary.replace(path)

    def _wait_for(self, path: Path, *, actor: str, timeout: float) -> None:
        deadline = time.monotonic() + timeout
        while True:
            if path.exists():
                observed = json.loads(path.read_text(encoding="utf-8"))
                if observed != self._payload(actor):
                    raise AssertionError(f"cross-identity barrier marker at {path}")
                return
            if time.monotonic() >= deadline:
                raise TimeoutError(f"timed out waiting for {path.name}")
            time.sleep(0.005)


def _delivery_target(project_uuid: str) -> Any:
    from specify_cli.delivery.interfaces import DeliveryTarget, TargetIdentity
    from specify_cli.delivery.targets import compute_target_id
    from specify_cli.sync.project_context import AdmissionState
    from specify_cli.sync.project_identity import CanonicalProjectUUID

    identity = TargetIdentity(
        target_identity="https://app.spec-kitty.ai",
        account_identity="account-1",
        private_teamspace_id="teamspace-1",
        project_uuid=CanonicalProjectUUID.parse(project_uuid),
        configuration_generation=4,
    )
    return DeliveryTarget(
        target_id=compute_target_id(
            target_identity=identity.target_identity,
            account_identity=identity.account_identity,
            private_teamspace_id=identity.private_teamspace_id,
            project_uuid=identity.project_uuid,
            configuration_generation=identity.configuration_generation,
        ),
        identity=identity,
        admission_state=AdmissionState.ADMITTED,
        admission_generation=1,
        binding_audience="private-teamspace:teamspace-1",
        last_error_category=None,
    )


def _event_frame(identity: BarrierIdentity) -> dict[str, Any]:
    event: dict[str, Any] = build_teamspace_envelope(
        event_id=identity.native_identity,
        event_type="WPStatusChanged",
        aggregate_id="WP09",
        aggregate_type="WorkPackage",
        build_id="build-wp09",
        payload={
            "wp_id": "WP09",
            "from_lane": "in_progress",
            "to_lane": "for_review",
            "actor": "wp09-adapter-matrix",
        },
        node_id="node-wp09",
        lamport_clock=1,
        causation_id=None,
        correlation_id=identity.native_identity,
        timestamp="2026-08-11T20:00:00+00:00",
        project_uuid=identity.project_uuid,
        project_slug="project-a",
        repo_slug="private/wp09",
    ).model_dump()
    event.update(
        team_slug="teamspace-1",
        git_branch="develop",
        head_commit_sha="a" * 40,
        drain_blocked_reason=None,
    )
    return event


def _ensure_admitted_project(project_uuid: str) -> Any:
    from specify_cli.sync.consent import record_project_opt_in
    from specify_cli.sync.project_context import AdmissionState, ConsentState
    from specify_cli.sync.project_store import ProjectSyncStore

    store = ProjectSyncStore(project_uuid)
    authority = store.layout_generation()
    from specify_cli.sync.layout_generation import LayoutMode

    layout_state = authority.read_state()
    if layout_state.mode is LayoutMode.LEGACY:
        authority.begin_cutover("wp09-production-adapter")
        authority.publish_project_only(
            "wp09-production-adapter",
            verify_exact=lambda: True,
        )
    elif layout_state.mode is LayoutMode.CUTOVER_PENDING:
        if layout_state.migration_id != "wp09-production-adapter":
            raise RuntimeError("WP09 adapter fixture found a foreign layout migration")
        authority.publish_project_only(
            "wp09-production-adapter",
            verify_exact=lambda: True,
        )
    context = store.create_context()
    if context.consent_state is not ConsentState.GRANTED:
        record_project_opt_in(project_uuid, actor="wp09-production-adapter")
    with store.unit_of_work() as unit:
        current = unit.execute(
            "SELECT admission_state FROM project_target_admissions WHERE project_uuid = ?",
            (project_uuid,),
        ).fetchone()
        if current is None:
            unit.execute(
                "INSERT INTO project_target_admissions "
                "(project_uuid, target_identity, account_identity, private_teamspace_id, "
                "configuration_generation, admission_state, admission_generation, binding_audience) "
                "VALUES (?, 'https://app.spec-kitty.ai', 'account-1', 'teamspace-1', 4, "
                "'admitted', '1', 'private-teamspace:teamspace-1')",
                (project_uuid,),
            )
        elif str(current[0]) != AdmissionState.ADMITTED.value:
            raise RuntimeError("WP09 adapter fixture found a non-admitted project")
    return store


@dataclass
class _PhysicalProbe:
    contract: ProductionAdapterContract
    seed_identity: BarrierIdentity
    poison: bool
    barrier: ProcessTransportBarrier | None
    poison_relay_delegation: bool = False
    calls: int = 0
    delegation_calls: int = 0
    request_bytes: bytes = b""
    delegation_bytes: bytes = b""
    delegation_poisoned: bool = False
    actual_identity: BarrierIdentity | None = None

    def _bind(self, identity: BarrierIdentity) -> None:
        if self.actual_identity is not None and self.actual_identity != identity:
            raise AssertionError("one adapter invocation crossed production attempt identities")
        self.actual_identity = identity
        if self.barrier is not None:
            self.barrier.bind_production_identity(identity)

    def bind_attempt(
        self,
        *,
        project_uuid: str,
        native_identity: str | None = None,
    ) -> BarrierIdentity:
        """Resolve the exact durable row produced by this public invocation."""
        from specify_cli.sync.project_store import ProjectSyncStore

        store = ProjectSyncStore(project_uuid)
        with store.unit_of_work() as unit:
            rows = unit.execute(
                "SELECT attempt_id, payload_reference FROM delivery_attempts WHERE project_uuid = ? ORDER BY created_at DESC, attempt_id DESC",
                (project_uuid,),
            ).fetchall()
        matches: list[BarrierIdentity] = []
        for attempt_id, payload_reference in rows:
            metadata = json.loads(str(payload_reference))
            persisted_native = metadata.get("native_identity")
            persisted_project = metadata.get("project_uuid")
            if not isinstance(persisted_native, str) or not persisted_native:
                continue
            if persisted_project != project_uuid:
                raise AssertionError("durable attempt metadata crossed project authority")
            if native_identity is not None and persisted_native != native_identity:
                continue
            matches.append(
                BarrierIdentity(
                    family=self.contract.family,
                    project_uuid=project_uuid,
                    attempt_id=str(attempt_id),
                    native_identity=persisted_native,
                )
            )
        if not matches:
            raise AssertionError("physical sink had no exact durable attempt identity")
        identity = matches[0]
        self._bind(identity)
        return identity

    def hit(
        self,
        request_bytes: bytes,
        *,
        project_uuid: str,
        native_identity: str | None = None,
    ) -> None:
        self.bind_attempt(
            project_uuid=project_uuid,
            native_identity=native_identity,
        )
        self.calls += 1
        self.request_bytes = request_bytes
        if self.barrier is not None:
            self.barrier.capture(request_bytes)
            if self.barrier.phase is BarrierPhase.TRANSPORT_STARTED:
                self.barrier.arrive_and_wait(timeout=60)
        if self.poison:
            raise PhysicalSinkPoison(f"{self.contract.entrypoint} reached {self.contract.physical_sink}")

    def hit_relay_delegation(self, request_bytes: bytes) -> None:
        """Record the local relay POST without treating it as a hosted ACK."""
        self.delegation_calls += 1
        self.delegation_bytes = request_bytes
        if self.barrier is not None:
            self.barrier.capture_delegation(request_bytes)
        if self.poison_relay_delegation:
            self.delegation_poisoned = True
            raise PhysicalSinkPoison("event relay reached its local daemon POST")


@contextmanager
def _phase_barrier_context(  # noqa: C901 - phase hooks patch every live alias together.
    barrier: ProcessTransportBarrier | None,
) -> Any:
    """Pause the real WP06 transition at the requested durable boundary."""
    if barrier is None or barrier.phase in {
        BarrierPhase.TRANSPORT_STARTED,
        BarrierPhase.RESULT_COMMITTED,
    }:
        yield
        return

    from unittest.mock import patch

    from specify_cli.saas_client import client as generic_module
    from specify_cli.sync import transport_attempts
    from specify_cli.tracker import saas_client as tracker_module

    def _hook_identity(args: tuple[Any, ...], kwargs: dict[str, Any]) -> BarrierIdentity:
        from specify_cli.sync.transport_attempts import (
            DeliveryAttemptSpec,
            get_delivery_attempt_record,
        )

        if len(args) < 2:
            raise AssertionError("transport transition hook omitted unit/context")
        unit, context = args[:2]
        spec = args[2] if len(args) > 2 and isinstance(args[2], DeliveryAttemptSpec) else None
        if spec is not None:
            attempt_id = spec.attempt_id
            native_identity = spec.native_identity
        else:
            raw_attempt_id = kwargs.get("attempt_id", args[2] if len(args) > 2 else None)
            if not isinstance(raw_attempt_id, str) or not raw_attempt_id:
                raise AssertionError("transport transition hook omitted attempt identity")
            record = get_delivery_attempt_record(unit, attempt_id=raw_attempt_id)
            if record is None or record.native_identity is None:
                raise AssertionError("transport transition hook did not name a durable attempt")
            attempt_id = record.attempt_id
            native_identity = record.native_identity
        project_uuid = context.project_uuid.storage_token
        return BarrierIdentity(
            family=barrier.seed_identity.family,
            project_uuid=project_uuid,
            attempt_id=attempt_id,
            native_identity=native_identity,
        )

    def _pause(identity: BarrierIdentity) -> None:
        barrier.bind_production_identity(identity)
        barrier.arrive_and_wait(timeout=60)

    with ExitStack() as stack:
        if barrier.phase is BarrierPhase.BEFORE_ATTEMPT_COMMIT:
            original_prepare = transport_attempts.prepare_delivery_attempt

            def _prepare(*args: Any, **kwargs: Any) -> Any:
                value = original_prepare(*args, **kwargs)
                _pause(_hook_identity(args, kwargs))
                return value

            stack.enter_context(patch.object(transport_attempts, "prepare_delivery_attempt", _prepare))
        elif barrier.phase is BarrierPhase.AFTER_ATTEMPT_COMMIT_BEFORE_SEND:
            original_mark = transport_attempts.mark_transport_started

            def _mark(*args: Any, **kwargs: Any) -> Any:
                _pause(_hook_identity(args, kwargs))
                return original_mark(*args, **kwargs)

            stack.enter_context(patch.object(transport_attempts, "mark_transport_started", _mark))
            stack.enter_context(patch.object(generic_module, "mark_transport_started", _mark))
            stack.enter_context(patch.object(tracker_module, "mark_transport_started", _mark))
        elif barrier.phase is BarrierPhase.RESPONSE_RECEIVED_BEFORE_RESULT:
            original_result = transport_attempts.record_delivery_result
            original_generic_result = generic_module.record_logical_operation_result
            original_tracker_result = tracker_module.record_logical_operation_result

            def _result(*args: Any, **kwargs: Any) -> Any:
                _pause(_hook_identity(args, kwargs))
                return original_result(*args, **kwargs)

            def _generic_result(*args: Any, **kwargs: Any) -> Any:
                _pause(_hook_identity(args, kwargs))
                return original_generic_result(*args, **kwargs)

            def _tracker_result(*args: Any, **kwargs: Any) -> Any:
                _pause(_hook_identity(args, kwargs))
                return original_tracker_result(*args, **kwargs)

            stack.enter_context(patch.object(transport_attempts, "record_delivery_result", _result))
            stack.enter_context(
                patch.object(
                    generic_module,
                    "record_logical_operation_result",
                    _generic_result,
                )
            )
            stack.enter_context(
                patch.object(
                    tracker_module,
                    "record_logical_operation_result",
                    _tracker_result,
                )
            )
        yield


def _result_response(outcome: str, event_id: str) -> tuple[int, dict[str, Any]]:
    if outcome == "delivered":
        return 200, {"results": [{"event_id": event_id, "status": "success"}]}
    if outcome == "duplicate":
        return 200, {"results": [{"event_id": event_id, "status": "duplicate"}]}
    if outcome == "refused":
        return 200, {
            "results": [
                {
                    "event_id": event_id,
                    "status": "rejected",
                    "error_category": "project_not_admitted",
                    "error": "project not admitted",
                }
            ]
        }
    raise TimeoutError("adapter loopback timed out after remote acceptance")


def _invoke_websocket(
    repo_root: Path,
    identity: BarrierIdentity,
    outcome: str,
    probe: _PhysicalProbe,
    *,
    local_commit: bool,
) -> bool:
    import asyncio
    from unittest.mock import patch

    from specify_cli.sync.client import WebSocketClient

    client = WebSocketClient(repo_root=repo_root)
    client.connected = True
    client.ACK_TIMEOUT_SECONDS = 0.01

    class _LoopbackWebSocket:
        async def send(self, raw: str) -> None:
            frame = json.loads(raw)
            if outcome == "timeout":
                return
            if local_commit:
                response: dict[str, Any] = {
                    "type": "LocalCommitAck",
                    "git_hash": frame["git_hash"],
                    "build_id": frame["build_id"],
                    "project_uuid": frame["project_uuid"],
                    "admission_generation": frame["admission_generation"],
                    "binding_audience": frame["binding_audience"],
                    "status": ("accepted" if outcome == "delivered" else "duplicate" if outcome == "duplicate" else "rejected"),
                }
                if outcome in {"delivered", "duplicate"}:
                    response["received_at"] = "2026-08-11T20:00:01Z"
                else:
                    response.update(
                        error_category="project_not_admitted",
                        retryable=False,
                    )
            elif outcome == "refused":
                response = {
                    "type": "error",
                    "event_id": frame["event_id"],
                    "status": "rejected",
                    "error_category": "project_not_admitted",
                    "retryable": False,
                }
            else:
                response = {
                    "type": "ack",
                    "event_id": frame["event_id"],
                    "status": "accepted" if outcome == "delivered" else "duplicate",
                }
            await client._handle_message(response)

    client.ws = cast("Any", _LoopbackWebSocket())
    original_send = WebSocketClient._send_wire

    async def _observed_send(active: WebSocketClient, wire: dict[str, Any]) -> None:
        encoded = json.dumps(
            wire,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        probe.hit(
            encoded,
            project_uuid=identity.project_uuid,
            native_identity=str(wire["spec_kitty_delivery_identity"]),
        )
        await original_send(active, wire)

    with patch.object(WebSocketClient, "_send_wire", _observed_send):
        try:
            if local_commit:
                from specify_cli.sync.local_commit import SyncState, save_sync_state

                frame = {
                    "type": "LocalCommit",
                    "git_hash": "a" * 40,
                    "mission_id": "01KZWP09MISSION0000000001",
                    "build_id": "build-wp09",
                    "project_uuid": identity.project_uuid,
                    "changed_files": ["kitty-specs/wp09/spec.md"],
                    "committed_at": "2026-08-11T20:00:00Z",
                }
                save_sync_state(
                    repo_root,
                    SyncState(pending_local_commits=[frame]),
                )
                return bool(asyncio.run(client.send_local_commit(frame)))
            return bool(asyncio.run(client.send_event(_event_frame(identity))))
        except PhysicalSinkPoison:
            raise
        except Exception:
            return False


def _invoke_body(
    identity: BarrierIdentity,
    outcome: str,
    probe: _PhysicalProbe,
) -> bool:
    from unittest.mock import patch

    from specify_cli.sync import body_transport
    from specify_cli.sync.body_queue import BodyUploadTask
    from specify_cli.sync.namespace import UploadOutcome, UploadStatus

    task = BodyUploadTask(
        row_id=f"body:{identity.native_identity}",
        project_uuid=identity.project_uuid,
        epoch_id=1,
        capture_sequence=1,
        mission_slug="wp09",
        target_branch="develop",
        mission_type="software-dev",
        manifest_version="1",
        artifact_path="kitty-specs/wp09/spec.md",
        content_hash="abc123",
        hash_algorithm="sha256",
        content_body="# WP09",
        size_bytes=6,
        retry_count=0,
        next_attempt_at=0,
        created_at=0,
        last_error=None,
    )
    original = body_transport._send_content_request

    def _observed_send(*args: Any, **kwargs: Any) -> UploadOutcome:
        del args
        request_body = cast("bytes", kwargs["request_body"])
        probe.hit(request_body, project_uuid=identity.project_uuid)
        if outcome == "timeout":
            raise TimeoutError("body loopback timed out after remote acceptance")
        status = {
            "delivered": UploadStatus.UPLOADED,
            "duplicate": UploadStatus.ALREADY_EXISTS,
            "refused": UploadStatus.FAILED,
        }[outcome]
        return UploadOutcome(
            artifact_path=task.artifact_path,
            status=status,
            reason=("project_not_admitted" if outcome == "refused" else None),
            content_hash=task.content_hash,
            retryable=False,
        )

    with patch.object(body_transport, "_send_content_request", _observed_send):
        try:
            result = body_transport.push_content_with_transport_gate(
                task,
                "token",
                _delivery_target(identity.project_uuid),
                "https://app.spec-kitty.ai",
            )
        except PhysicalSinkPoison:
            raise
        except Exception:
            return False
    del original
    return bool(result.status in {UploadStatus.UPLOADED, UploadStatus.ALREADY_EXISTS})


def _invoke_dispatcher(
    identity: BarrierIdentity,
    outcome: str,
    probe: _PhysicalProbe,
    *,
    final_sync: bool,
) -> bool:
    import gzip
    from types import SimpleNamespace
    from unittest.mock import patch

    import requests

    from specify_cli.delivery import receivers
    from specify_cli.delivery.dispatcher import dispatch
    from specify_cli.delivery.receivers import TeamspaceReceiver
    from specify_cli.event_journal.journal import EventJournal
    from specify_cli.event_journal.models import Event
    from specify_cli.sync.project_store import ProjectSyncStore

    store = ProjectSyncStore(identity.project_uuid)
    payload = json.dumps(_event_frame(identity), sort_keys=True).encode("utf-8")
    with store.unit_of_work() as unit:
        journal = EventJournal(unit, store.layout_generation())
        journal.append(
            Event(
                event_id=identity.native_identity,
                event_type="WPStatusChanged",
                payload=payload,
                occurred_at="2026-08-11T20:00:00+00:00",
                created_at="2026-08-11T20:00:00+00:00",
                project_uuid=identity.project_uuid,
                project_slug="project-a",
                repo_slug="private/wp09",
            )
        )

    class _Response:
        def __init__(self, status_code: int, body: dict[str, Any]) -> None:
            self.status_code = status_code
            self._body = body

        def json(self) -> dict[str, Any]:
            return self._body

    def _poster(
        _url: str,
        *,
        data: bytes,
        headers: Any,
        timeout: float,
    ) -> _Response:
        del data, headers, timeout
        if outcome == "timeout":
            raise requests.Timeout("dispatcher loopback timed out")
        status, body = _result_response(outcome, identity.native_identity)
        return _Response(status, body)

    receiver = TeamspaceReceiver(
        resolved_server_url="https://app.spec-kitty.ai",
        auth_token="token",
        poster=_poster,
    )
    original = receivers._HttpReceiver._attempt_batch_send

    def _observed_send(active: Any, events: Any) -> Any:
        raw = gzip.compress(receivers._build_payload(events))
        probe.hit(
            raw,
            project_uuid=identity.project_uuid,
            native_identity=identity.native_identity,
        )
        return original(active, events)

    target = _delivery_target(identity.project_uuid)
    context = store.create_context()
    with patch.object(
        receivers._HttpReceiver,
        "_attempt_batch_send",
        _observed_send,
    ):
        try:
            if final_sync:
                from specify_cli.cli.commands.sync import _run_dispatch_batches

                summary = _run_dispatch_batches(
                    SimpleNamespace(store=store, context=context),
                    receiver,
                    target,
                )
            else:
                summary = dispatch(
                    store=store,
                    receiver=receiver,
                    target=target,
                    context=context,
                )
        except PhysicalSinkPoison:
            raise
        except Exception:
            return False
    return bool(summary.delivered + summary.duplicate)


def _history_authority(identity: BarrierIdentity) -> tuple[Any, Any, Any, dict[str, Any]]:
    from specify_cli.sync.consent import allocate_capture_sequence, record_project_opt_in
    from specify_cli.sync.history_disclosure import (
        confirm_history_disclosure,
        preview_sealed_history,
    )
    from specify_cli.sync.layout_generation import LayoutMode
    from specify_cli.sync.project_context import ConsentState
    from specify_cli.sync.project_store import ProjectSyncStore

    store = ProjectSyncStore(identity.project_uuid)
    authority = store.layout_generation()
    layout_state = authority.read_state()
    if layout_state.mode is LayoutMode.LEGACY:
        authority.begin_cutover("wp09-production-adapter")
        authority.publish_project_only(
            "wp09-production-adapter",
            verify_exact=lambda: True,
        )
    envelope = _event_frame(identity)
    context = store.create_context()
    if context.consent_state is not ConsentState.GRANTED:
        with store.unit_of_work() as unit:
            assignment = allocate_capture_sequence(unit)
            unit.execute(
                "INSERT INTO journal_entries (entry_id, project_uuid, epoch_id, capture_sequence, payload_json) VALUES (?, ?, ?, ?, ?)",
                (
                    identity.native_identity,
                    identity.project_uuid,
                    assignment.epoch_id,
                    assignment.capture_sequence,
                    json.dumps(envelope, sort_keys=True, separators=(",", ":")),
                ),
            )
        record_project_opt_in(
            identity.project_uuid,
            actor="wp09-history-adapter",
        )
    with store.unit_of_work() as unit:
        admission = unit.execute(
            "SELECT 1 FROM project_target_admissions WHERE project_uuid = ?",
            (identity.project_uuid,),
        ).fetchone()
        if admission is None:
            unit.execute(
                "INSERT INTO project_target_admissions "
                "(project_uuid, target_identity, account_identity, private_teamspace_id, "
                "configuration_generation, admission_state, admission_generation, binding_audience) "
                "VALUES (?, 'https://app.spec-kitty.ai', 'account-1', 'teamspace-1', 4, "
                "'admitted', '1', 'private-teamspace:teamspace-1')",
                (identity.project_uuid,),
            )
    context = store.create_context()
    capability = confirm_history_disclosure(
        store,
        preview_sealed_history(store),
        actor="wp09-history-adapter",
        idempotency_key=f"history:{identity.native_identity}",
        context=context,
    )
    return store, context, capability, envelope


def _invoke_history(
    identity: BarrierIdentity,
    outcome: str,
    probe: _PhysicalProbe,
    *,
    recovery_without_authority: bool = False,
) -> bool:
    import gzip
    from unittest.mock import patch

    import requests

    from specify_cli.delivery import receivers
    from specify_cli.delivery.receivers import TeamspaceReceiver
    from specify_cli.sync.history_import import upload

    if recovery_without_authority:
        from specify_cli.sync.project_store import ProjectSyncStore

        context = ProjectSyncStore(identity.project_uuid).create_context()
        capability = None
        envelope = _event_frame(identity)
    else:
        _store, context, capability, envelope = _history_authority(identity)

    class _Response:
        status_code = 200

        def json(self) -> dict[str, Any]:
            _status, body = _result_response(outcome, identity.native_identity)
            return body

    def _poster(
        _url: str,
        *,
        data: bytes,
        headers: Any,
        timeout: float,
    ) -> _Response:
        del data, headers, timeout
        if outcome == "timeout":
            raise requests.Timeout("history loopback timed out")
        return _Response()

    receiver = TeamspaceReceiver(
        resolved_server_url="https://app.spec-kitty.ai",
        auth_token="token",
        poster=_poster,
    )
    original = receivers._HttpReceiver._attempt_batch_send

    def _observed_delivery(active: Any, events: Any) -> Any:
        probe.hit(
            gzip.compress(receivers._build_payload(events)),
            project_uuid=identity.project_uuid,
            native_identity=identity.native_identity,
        )
        return original(active, events)

    with patch.object(
        receivers._HttpReceiver,
        "_attempt_batch_send",
        _observed_delivery,
    ):
        try:
            report = upload.upload_envelopes(
                [envelope],
                receiver=receiver,
                project_context=context,
                target=_delivery_target(identity.project_uuid),
                history_capability=capability,
            )
        except PhysicalSinkPoison:
            raise
        except Exception:
            return False
    return bool(report.success + report.duplicate)


def _invoke_generic_saas(
    repo_root: Path,
    identity: BarrierIdentity,
    outcome: str,
    probe: _PhysicalProbe,
    hosted_replay_mutation: str | None,
) -> bool:
    from unittest.mock import patch

    import httpx

    from specify_cli.saas_client import client as module
    from specify_cli.saas_client.client import SaasClient

    class _Http:
        def get(self, url: str, *, timeout: float) -> httpx.Response:
            del timeout
            return httpx.Response(
                200,
                json={"integrations": ["github"]},
                request=httpx.Request("GET", url),
            )

        def post(
            self,
            url: str,
            *,
            json: object,
            headers: dict[str, str],
            timeout: float,
        ) -> httpx.Response:
            import json as json_module

            del timeout
            native = headers["Idempotency-Key"]
            probe.hit(
                json_module.dumps(
                    {
                        "method": "POST",
                        "url": url,
                        "json": json,
                        "native_identity": native,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8"),
                project_uuid=identity.project_uuid,
                native_identity=native,
            )
            if outcome == "timeout":
                raise httpx.ReadTimeout(
                    "generic SaaS loopback timed out",
                    request=httpx.Request("POST", url),
                )
            if outcome == "refused":
                return httpx.Response(
                    403,
                    json={
                        "error_category": "project_not_admitted",
                        "idempotency_key": native,
                        "status": "rejected",
                        "retryable": False,
                    },
                    request=httpx.Request("POST", url),
                )
            replay_headers = {"Idempotency-Replayed": "true"} if outcome == "duplicate" and hosted_replay_mutation != "missing_header" else None
            request_native = "wrong-native-identity" if hosted_replay_mutation == "wrong_key" else native
            return httpx.Response(
                200,
                json={
                    "decision_id": "decision-wp09",
                    "widened_at": "2026-08-11T20:00:00Z",
                    "widened_by": 1,
                    "invited_user_ids": [1],
                    "idempotent": outcome == "duplicate",
                    "participation_row_ids": ["participation-wp09"],
                    "audit_snapshot_id": "snapshot-wp09",
                    "slack_thread_status": None,
                },
                headers=replay_headers,
                request=httpx.Request(
                    "POST",
                    url,
                    headers={"Idempotency-Key": request_native},
                ),
            )

    client = SaasClient(
        "https://app.spec-kitty.ai",
        "token",
        team_slug="teamspace-1",
        project_root=repo_root,
        _http=cast("Any", _Http()),
    )
    with (
        patch.object(
            module,
            "_authenticated_authority_for_token",
            lambda _token: ("account-1", "teamspace-1", "teamspace-1"),
        ),
    ):
        try:
            client.post_widen(
                "decision-wp09",
                [1],
                team_slug="teamspace-1",
            )
        except PhysicalSinkPoison:
            raise
        except Exception:
            return False
    return True


def _invoke_tracker(
    repo_root: Path,
    identity: BarrierIdentity,
    outcome: str,
    probe: _PhysicalProbe,
    hosted_replay_mutation: str | None,
) -> bool:
    from types import SimpleNamespace
    from unittest.mock import patch

    import httpx

    from specify_cli.tracker import saas_client as module
    from specify_cli.tracker.saas_client import (
        SaaSTrackerClient,
        SaaSTrackerClientError,
    )

    def _observed_request(
        active: SaaSTrackerClient,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> httpx.Response:
        del active
        headers = dict(kwargs.get("headers") or {})
        native = headers.get("Idempotency-Key", "")
        request_bytes = json.dumps(
            {
                "headers": {"Idempotency-Key": native},
                "json": kwargs.get("json"),
                "method": method,
                "path": path,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        probe.hit(
            request_bytes,
            project_uuid=identity.project_uuid,
            native_identity=native,
        )
        if outcome == "timeout":
            raise SaaSTrackerClientError(
                "tracker loopback timed out",
                details={"effect_certainty": "unknown"},
            )
        if outcome == "refused":
            raise SaaSTrackerClientError(
                "project not admitted",
                error_code="project_not_admitted",
                status_code=403,
                details={
                    "error_category": "project_not_admitted",
                    "idempotency_key": native,
                    "status": "rejected",
                    "retryable": False,
                },
                user_action_required=True,
            )
        replay_headers = {"Idempotency-Replayed": "true"} if outcome == "duplicate" and hosted_replay_mutation != "missing_header" else None
        request_native = "wrong-native-identity" if hosted_replay_mutation == "wrong_key" else native
        return httpx.Response(
            200,
            json={
                "status": "ok",
                "summary": {"total": 1, "succeeded": 1, "failed": 0},
                "items": [
                    {
                        "ref": {"system": "github", "workspace": "", "id": identity.native_identity},
                        "action": "update",
                        "outcome": "ok",
                    }
                ],
                "identity_path": {"kind": "user_link"},
            },
            headers=replay_headers,
            request=httpx.Request(
                "POST",
                "https://app.spec-kitty.ai/api/v1/tracker/push/",
                headers={"Idempotency-Key": request_native},
            ),
        )

    config = SimpleNamespace(resolve_runtime_target=lambda: SimpleNamespace(resolved_server_url="https://app.spec-kitty.ai"))
    client = SaaSTrackerClient(
        sync_config=cast("Any", config),
        project_root=repo_root,
    )
    client._sleep = lambda _delay: None
    authority = module._HostedTrackerAuthority(
        account_identity="account-1",
        private_teamspace_id="teamspace-1",
        collaborative_team_slug="teamspace-1",
    )
    with (
        patch.object(module, "_fetch_access_token_sync", lambda: "token"),
        patch.object(module, "_hosted_authority_for_token", lambda _token: authority),
        patch.object(
            SaaSTrackerClient,
            "_physical_request_with_retry",
            _observed_request,
        ),
    ):
        try:
            client.push(
                "github",
                "project-wp09",
                [{"id": identity.native_identity}],
            )
        except PhysicalSinkPoison:
            raise
        except Exception:
            return False
    return True


def _invoke_daemon(
    repo_root: Path,
    identity: BarrierIdentity,
    outcome: str,
    probe: _PhysicalProbe,
    *,
    event: dict[str, Any] | None = None,
) -> bool:
    import asyncio
    from unittest.mock import patch

    from specify_cli.sync.client import WebSocketClient
    from specify_cli.sync.runtime import SyncRuntime

    client = WebSocketClient(repo_root=repo_root)
    client.connected = True
    client.ACK_TIMEOUT_SECONDS = 0.05

    class _LoopbackWebSocket:
        async def send(self, raw: str) -> None:
            frame = json.loads(raw)
            if outcome == "timeout":
                return
            if outcome == "refused":
                response = {
                    "type": "error",
                    "event_id": frame["event_id"],
                    "status": "rejected",
                    "error_category": "project_not_admitted",
                    "retryable": False,
                }
            else:
                response = {
                    "type": "ack",
                    "event_id": frame["event_id"],
                    "status": "accepted" if outcome == "delivered" else "duplicate",
                }
            await client._handle_message(response)

    client.ws = cast("Any", _LoopbackWebSocket())
    runtime = SyncRuntime()
    runtime._ensure_async_loop()
    runtime.ws_client = client
    runtime.started = True
    original_send = WebSocketClient._send_wire

    async def _observed_send(
        active: WebSocketClient,
        wire: dict[str, Any],
    ) -> None:
        probe.hit(
            json.dumps(
                wire,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8"),
            project_uuid=identity.project_uuid,
            native_identity=str(wire["spec_kitty_delivery_identity"]),
        )
        await original_send(active, wire)

    try:
        with (
            patch.object(WebSocketClient, "_send_wire", _observed_send),
            patch.object(
                runtime,
                "_current_event_delivery_target",
                lambda _project_uuid: _delivery_target(identity.project_uuid),
            ),
        ):
            return bool(runtime.publish_event(event or _event_frame(identity)))
    except PhysicalSinkPoison:
        raise
    except Exception:
        return False
    finally:
        loop = runtime._async_loop
        thread = runtime._async_loop_thread
        if loop is not None:
            asyncio.run_coroutine_threadsafe(loop.shutdown_default_executor(), loop).result(timeout=5.0)
            loop.call_soon_threadsafe(loop.stop)
        if thread is not None:
            thread.join(timeout=5.0)
            if thread.is_alive():
                raise AssertionError("test daemon event loop did not stop")
        if loop is not None:
            loop.close()
        runtime._async_loop = None
        runtime._async_loop_thread = None
        runtime.ws_client = None
        runtime.started = False


def _invoke_relay(
    repo_root: Path,
    identity: BarrierIdentity,
    outcome: str,
    probe: _PhysicalProbe,
) -> bool:
    from types import SimpleNamespace
    from unittest.mock import patch

    from specify_cli.sync import emitter as emitter_module
    from specify_cli.sync import events

    from uuid import UUID

    from specify_cli.identity.project import ProjectIdentity
    from specify_cli.sync.clock import LamportClock
    from specify_cli.sync.emitter import EventEmitter

    class _GitResolver:
        def resolve(self) -> Any:
            return SimpleNamespace(
                git_branch="develop",
                head_commit_sha="a" * 40,
                repo_slug="private/wp09",
            )

    emitter = EventEmitter(
        clock=LamportClock(
            node_id="node-wp09",
            _storage_path=repo_root / ".kittify" / "wp09-relay-clock.json",
        ),
        _identity=ProjectIdentity(
            project_uuid=UUID(identity.project_uuid),
            project_slug="project-a",
            node_id="node-wp09",
            repo_slug="private/wp09",
            build_id="build-wp09",
        ),
        _git_resolver=cast("Any", _GitResolver()),
    )

    class _Response:
        status = 202

        def __enter__(self) -> _Response:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

    def _urlopen(request: Any, *, timeout: float) -> _Response:
        del timeout
        data = getattr(request, "data", None)
        if not isinstance(data, bytes):
            raise AssertionError("relay did not issue its publish POST")
        probe.hit_relay_delegation(data)
        relay_body = json.loads(data)
        relayed_event = relay_body.get("event")
        if not isinstance(relayed_event, dict):
            raise AssertionError("relay POST omitted its event envelope")
        if not _invoke_daemon(
            repo_root,
            identity,
            outcome,
            probe,
            event=relayed_event,
        ):
            raise RuntimeError("loopback daemon did not converge the relayed event")
        return _Response()

    status = SimpleNamespace(
        healthy=True,
        url="http://127.0.0.1:3030",
        token="wp09-loopback-token",
    )
    try:
        with (
            patch.object(events, "get_emitter", lambda: emitter),
            patch.object(
                emitter_module,
                "_generate_ulid",
                lambda: _relay_event_id(identity),
            ),
            patch.object(EventEmitter, "_current_team_slug", lambda _self: "teamspace-1"),
            patch.object(EventEmitter, "_is_authenticated", lambda _self: True),
            patch.object(
                events,
                "_ensure_dashboard_sync_daemon_for_active_project",
                lambda **_kwargs: repo_root,
            ),
            patch.object(events, "_request_dashboard_sync", lambda _root: None),
            patch("specify_cli.sync.daemon.get_sync_daemon_status", lambda **_kwargs: status),
            patch.object(events.urllib.request, "urlopen", _urlopen),
        ):
            # ``occurred_at`` now travels inside ``metadata=WPStatusChangeMetadata``
            # (main's S107 wrapper refactor); the flat kwarg raises TypeError.
            from specify_cli.status import WPStatusChangeMetadata

            emitted = events.emit_wp_status_changed(
                "WP09",
                "in_progress",
                "for_review",
                actor="wp09-adapter-matrix",
                metadata=WPStatusChangeMetadata(occurred_at="2026-08-11T20:00:00+00:00"),
            )
    except PhysicalSinkPoison:
        raise
    except Exception:
        return False
    return isinstance(emitted, dict) and emitted.get("event_type") == "WPStatusChanged"


def _public_call_result_contract(
    family: str,
    outcome: str,
    hosted_replay_mutation: str | None,
) -> tuple[ResultExpectation, str | None, HostedReferenceExpectation]:
    """Declare result presence from the public scenario, never observed storage."""
    if outcome == "timeout":
        if family in {"direct_dispatcher", "final_exit_sync", "history_import"}:
            return (
                ResultExpectation.ORDINARY_UNKNOWN,
                "unknown",
                HostedReferenceExpectation.ABSENT,
            )
        return (
            ResultExpectation.ABSENT,
            None,
            HostedReferenceExpectation.ABSENT,
        )
    expected_outcome = outcome
    if outcome == "duplicate" and hosted_replay_mutation is not None:
        expected_outcome = "delivered"
    hosted_reference = (
        HostedReferenceExpectation.REQUIRED
        if family in {"generic_saas", "tracker_hosted"} and expected_outcome in {"delivered", "duplicate"}
        else HostedReferenceExpectation.ABSENT
    )
    return ResultExpectation.COMPLETED, expected_outcome, hosted_reference


def invoke_production_adapter(  # noqa: C901 - explicit dispatch is executable census evidence.
    repo_root: Path,
    identity: BarrierIdentity,
    *,
    outcome: str,
    poison_sink: bool = False,
    barrier: ProcessTransportBarrier | None = None,
    ensure_authority: bool = True,
    expected_sink_calls: int = 1,
    hosted_replay_mutation: str | None = None,
    poison_relay_delegation: bool = False,
    expected_actual_identity: BarrierIdentity | None = None,
) -> ProductionAdapterEvidence:
    """Invoke one census row through its public entry and observed physical sink."""
    contract = _contract(identity.family)
    if ensure_authority and identity.family != "history_import":
        _ensure_admitted_project(identity.project_uuid)
    probe = _PhysicalProbe(
        contract=contract,
        seed_identity=identity,
        poison=poison_sink,
        barrier=barrier,
        poison_relay_delegation=poison_relay_delegation,
    )
    if expected_actual_identity is not None:
        probe._bind(expected_actual_identity)
    with _phase_barrier_context(barrier):
        if identity.family == "direct_dispatcher":
            succeeded = _invoke_dispatcher(identity, outcome, probe, final_sync=False)
        elif identity.family == "final_exit_sync":
            succeeded = _invoke_dispatcher(identity, outcome, probe, final_sync=True)
        elif identity.family == "emitter_websocket":
            succeeded = _invoke_websocket(repo_root, identity, outcome, probe, local_commit=False)
        elif identity.family == "reconnect_local_commit":
            succeeded = _invoke_websocket(repo_root, identity, outcome, probe, local_commit=True)
        elif identity.family == "daemon_publish":
            succeeded = _invoke_daemon(repo_root, identity, outcome, probe)
        elif identity.family == "event_relay":
            succeeded = _invoke_relay(repo_root, identity, outcome, probe)
        elif identity.family == "body_drain":
            succeeded = _invoke_body(identity, outcome, probe)
        elif identity.family == "history_import":
            succeeded = _invoke_history(
                identity,
                outcome,
                probe,
                recovery_without_authority=not ensure_authority,
            )
        elif identity.family == "tracker_hosted":
            succeeded = _invoke_tracker(
                repo_root,
                identity,
                outcome,
                probe,
                hosted_replay_mutation,
            )
        elif identity.family == "generic_saas":
            succeeded = _invoke_generic_saas(
                repo_root,
                identity,
                outcome,
                probe,
                hosted_replay_mutation,
            )
        else:  # pragma: no cover - _contract validates the closed census first.
            raise AssertionError(identity.family)
    if probe.delegation_poisoned:
        raise PhysicalSinkPoison("event relay reached its local daemon POST")
    if barrier is not None and barrier.phase is BarrierPhase.RESULT_COMMITTED:
        barrier.arrive_and_wait(timeout=60)
    if poison_sink and probe.calls:
        raise PhysicalSinkPoison(f"{contract.entrypoint} reached {contract.physical_sink}")
    if probe.calls != expected_sink_calls:
        raise AssertionError(f"{identity.family} invoked {probe.calls} physical sinks; expected {expected_sink_calls}")
    if identity.family == "event_relay" and probe.delegation_calls != 1:
        raise AssertionError("event relay must issue one local delegation POST")
    if probe.actual_identity is None:
        raise AssertionError("adapter returned without binding a production attempt identity")
    result_expectation, expected_result_outcome, hosted_reference_expectation = _public_call_result_contract(identity.family, outcome, hosted_replay_mutation)
    return ProductionAdapterEvidence(
        family=contract.family,
        entrypoint=contract.entrypoint,
        physical_sink=contract.physical_sink,
        seed_identity=identity,
        actual_identity=probe.actual_identity,
        request_bytes=probe.request_bytes,
        delegation_bytes=probe.delegation_bytes,
        succeeded=succeeded,
        requested_outcome=outcome,
        expected_attempt_present=True,
        result_expectation=result_expectation,
        expected_result_outcome=expected_result_outcome,
        hosted_reference_expectation=hosted_reference_expectation,
    )


def recover_production_adapter(
    repo_root: Path,
    seed_identity: BarrierIdentity,
    actual_identity: BarrierIdentity,
    *,
    poison_sink: bool,
) -> ProductionAdapterEvidence:
    """Re-enter the exact persisted operation through its production recovery path."""
    if seed_identity.family != "event_relay":
        return invoke_production_adapter(
            repo_root,
            seed_identity,
            outcome="delivered",
            poison_sink=poison_sink,
            expected_sink_calls=0,
            expected_actual_identity=actual_identity,
        )

    import asyncio

    from specify_cli.identity.project import resolve_identity
    from specify_cli.sync.client import WebSocketClient

    class _PoisonWebSocket:
        async def send(self, _raw: str) -> None:
            raise PhysicalSinkPoison("relay recovery resent its terminalized Event")

    client = WebSocketClient(
        project_identity=resolve_identity(repo_root),
        repo_root=repo_root,
    )
    client.connected = True
    client.ws = cast("Any", _PoisonWebSocket())
    asyncio.run(client._flush_pending_project_events())
    contract = _contract(seed_identity.family)
    return ProductionAdapterEvidence(
        family=contract.family,
        entrypoint=contract.entrypoint,
        physical_sink=contract.physical_sink,
        seed_identity=seed_identity,
        actual_identity=actual_identity,
        request_bytes=b"",
        delegation_bytes=b"",
        succeeded=False,
        requested_outcome="delivered",
        expected_attempt_present=True,
        result_expectation=ResultExpectation.OPT_OUT_TERMINAL_UNKNOWN,
        expected_result_outcome="terminal_unknown",
        hosted_reference_expectation=HostedReferenceExpectation.ABSENT,
    )


__all__ = [
    "PAIRED_SAAS_CONTRACT_DIGEST",
    "PAIRED_SAAS_REPLAY_EVIDENCE",
    "PAIRED_SAAS_REPLAY_SHA",
    "PAIRED_SAAS_REPLAY_TREE",
    "PAIRED_SAAS_SOURCE_BLOBS",
    "PRODUCTION_ADAPTER_CONTRACTS",
    "BarrierIdentity",
    "BarrierPhase",
    "HostedReferenceExpectation",
    "PhysicalSinkPoison",
    "PersistedAttemptEvidence",
    "ProcessTransportBarrier",
    "ProductionAdapterContract",
    "ProductionAdapterEvidence",
    "ResultExpectation",
    "TRANSPORT_FAMILIES",
    "assert_exact_transport_evidence",
    "assert_transport_evidence_values",
    "canonical_transport_payload",
    "evidence_from_barrier",
    "invoke_production_adapter",
    "paired_saas_contract_digest",
    "read_persisted_attempt",
    "recover_production_adapter",
]
