"""WP07 interactive senders consume WP06's per-project final gate."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from specify_cli.delivery.consent_gate import (
    ProjectTransportDisclosure,
    ProjectTransportRefusal,
    execute_project_transport_disclosure,
)
from specify_cli.delivery.interfaces import DeliveryTarget, TargetIdentity
from specify_cli.delivery.targets import compute_target_id
from specify_cli.migration.envelope_seam import build_teamspace_envelope
from specify_cli.sync.body_queue import BodyUploadTask
from specify_cli.sync.body_transport import push_content_with_transport_gate
from specify_cli.sync.consent import record_project_opt_in
from specify_cli.sync.emitter import EventEmitter
from specify_cli.sync.namespace import UploadStatus
from specify_cli.sync.project_context import AdmissionState
from specify_cli.sync.project_identity import CanonicalProjectUUID
from specify_cli.sync.project_store import ProjectSyncStore
from specify_cli.sync.transport_attempts import DeliveryAttemptState, DeliveryOutcome

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

@pytest.fixture(autouse=True)
def _canonical_home(canonical_home: None) -> None:
    """R1a #3121: route this module's home through the ONE canonical owner."""
    del canonical_home


PROJECT = "aaaaaaaa-0000-0000-0000-0000000000aa"
OTHER = "bbbbbbbb-0000-0000-0000-0000000000bb"


def _target(project_uuid: str = PROJECT) -> DeliveryTarget:
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
        admission_generation=9,
        binding_audience="private-teamspace:teamspace-1",
        last_error_category=None,
    )


def _seed_admitted_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, project_uuid: str = PROJECT) -> ProjectSyncStore:
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    record_project_opt_in(project_uuid, actor="tester")
    store = ProjectSyncStore(project_uuid)
    with store.unit_of_work() as unit:
        unit.execute(
            "INSERT INTO project_target_admissions "
            "(project_uuid, target_identity, account_identity, private_teamspace_id, "
            "configuration_generation, admission_state, admission_generation, binding_audience) "
            "VALUES (?, 'https://app.spec-kitty.ai', 'account-1', 'teamspace-1', 4, "
            "'admitted', '9', 'private-teamspace:teamspace-1')",
            (project_uuid,),
        )
    return store


def _disclosure(
    target: DeliveryTarget,
    *,
    attempt_id: str = "attempt-wp07",
    project_uuid: str | None = None,
) -> ProjectTransportDisclosure:
    return ProjectTransportDisclosure(
        project_uuid=project_uuid or target.project_uuid.storage_token,
        epoch_id=1,
        consent_generation=1,
        target_identity=target.target_identity,
        account_identity=target.account_identity,
        private_teamspace_id=target.private_teamspace_id,
        target_project_uuid=target.project_uuid.storage_token,
        target_generation=target.configuration_generation,
        admission_generation=str(target.admission_generation),
        binding_audience=str(target.binding_audience),
        write_kind="wp07-test",
        native_identity=f"native:{attempt_id}",
        payload_hash="sha256:payload",
        payload_reference=f"payload:{attempt_id}",
        attempt_id=attempt_id,
        deadline_at="2999-01-01T00:00:00Z",
    )


def _attempt_state(store: ProjectSyncStore, attempt_id: str) -> tuple[str, str | None, str | None]:
    with store.unit_of_work() as unit:
        row = unit.execute(
            "SELECT state, payload_hash, payload_reference FROM delivery_attempts WHERE project_uuid = ? AND attempt_id = ?",
            (store.project_uuid.storage_token, attempt_id),
        ).fetchone()
    assert row is not None
    return str(row[0]), str(row[1]), str(row[2])


def _result_outcomes(store: ProjectSyncStore, attempt_id: str) -> list[str]:
    with store.unit_of_work() as unit:
        rows = unit.execute(
            "SELECT outcome FROM delivery_results WHERE project_uuid = ? AND attempt_id = ? ORDER BY recorded_at",
            (store.project_uuid.storage_token, attempt_id),
        ).fetchall()
    return [str(row[0]) for row in rows]


def test_final_gate_commits_attempt_before_io_and_records_result(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = _seed_admitted_project(tmp_path, monkeypatch)
    calls = 0

    def _send() -> object:
        nonlocal calls
        calls += 1
        state, payload_hash, _payload_reference = _attempt_state(store, "attempt-wp07")
        assert state == DeliveryAttemptState.IN_FLIGHT.value
        assert payload_hash == "sha256:payload"
        return "sent"

    result = execute_project_transport_disclosure(
        _disclosure(_target()),
        send=_send,
        classify=lambda _value: (DeliveryOutcome.DELIVERED.value, None),
    )

    assert result == "sent"
    assert calls == 1
    assert _attempt_state(store, "attempt-wp07")[0] == DeliveryAttemptState.SUCCEEDED.value
    assert _result_outcomes(store, "attempt-wp07") == [DeliveryOutcome.DELIVERED.value]


def test_cross_paired_target_context_refuses_before_io(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _seed_admitted_project(tmp_path, monkeypatch)
    mismatched = DeliveryTarget(
        target_id="target-other",
        identity=TargetIdentity(
            target_identity="https://evil.example.test",
            account_identity="account-1",
            private_teamspace_id="teamspace-1",
            project_uuid=CanonicalProjectUUID.parse(PROJECT),
            configuration_generation=4,
        ),
        admission_state=AdmissionState.ADMITTED,
        admission_generation=9,
        binding_audience="private-teamspace:teamspace-1",
        last_error_category=None,
    )
    sent = False

    def _send() -> object:
        nonlocal sent
        sent = True
        return "sent"

    result = execute_project_transport_disclosure(
        _disclosure(mismatched, attempt_id="attempt-cross-pair"),
        send=_send,
        classify=lambda _value: (DeliveryOutcome.DELIVERED.value, None),
    )

    assert isinstance(result, ProjectTransportRefusal)
    assert result.category == "project_not_admitted"
    assert "target audience mismatch" in result.diagnostic
    assert sent is False


def test_cross_project_target_context_refuses_even_when_audience_strings_match(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _seed_admitted_project(tmp_path, monkeypatch)
    other_target = _target(OTHER)
    sent = False

    def _send() -> object:
        nonlocal sent
        sent = True
        return "sent"

    result = execute_project_transport_disclosure(
        _disclosure(other_target, attempt_id="attempt-target-project", project_uuid=PROJECT),
        send=_send,
        classify=lambda _value: (DeliveryOutcome.DELIVERED.value, None),
    )

    assert isinstance(result, ProjectTransportRefusal)
    assert "target audience mismatch for target_project_uuid" in result.diagnostic
    assert sent is False


def test_connected_websocket_cannot_bypass_canonical_transport_gate() -> None:
    """Local capture succeeds while the retired raw WebSocket path stays unreachable."""
    queue = MagicMock()
    queue.queue_event.return_value = True
    ws_client = MagicMock()
    ws_client.connected = True
    emitter = EventEmitter(queue=queue)  # type: ignore[arg-type]
    emitter.ws_client = ws_client
    event: dict[str, Any] = build_teamspace_envelope(
        event_id="01JWP07DIRECTWSBYPASS00000",
        event_type="WPStatusChanged",
        aggregate_id="WP01",
        aggregate_type="WorkPackage",
        payload={
            "wp_id": "WP01",
            "from_lane": "planned",
            "to_lane": "in_progress",
        },
        timestamp="2026-02-04T12:00:00+00:00",
        build_id="test-build-id",
        node_id="test-node-id",
        lamport_clock=1,
        causation_id=None,
        project_uuid=PROJECT,
        project_slug="private-engagement",
        repo_slug="private/project",
        correlation_id="01JWP07DIRECTWSBYPASS00000",
    ).model_dump()
    event["team_slug"] = "test-team"

    assert emitter._route_event(event) is True
    queue.queue_event.assert_called_once_with(event)
    ws_client.send_event.assert_not_called()


def test_send_exception_leaves_original_attempt_unknown_without_fresh_identity(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = _seed_admitted_project(tmp_path, monkeypatch)

    with pytest.raises(RuntimeError, match="network died"):
        execute_project_transport_disclosure(
            _disclosure(_target(), attempt_id="attempt-exception"),
            send=lambda: (_ for _ in ()).throw(RuntimeError("network died")),
            classify=lambda _value: (DeliveryOutcome.DELIVERED.value, None),
        )

    assert _attempt_state(store, "attempt-exception")[0] == DeliveryAttemptState.UNKNOWN.value
    assert _result_outcomes(store, "attempt-exception") == []
    with store.unit_of_work() as unit:
        rows = unit.execute(
            "SELECT attempt_id FROM delivery_attempts WHERE project_uuid = ?",
            (PROJECT,),
        ).fetchall()
    assert [str(row[0]) for row in rows] == ["attempt-exception"]


def _body_task(project_uuid: str = PROJECT) -> BodyUploadTask:
    return BodyUploadTask(
        row_id="body-row-1",
        project_uuid=project_uuid,
        epoch_id=7,
        capture_sequence=1,
        mission_slug="mission",
        target_branch="develop",
        mission_type="software-dev",
        manifest_version="1",
        artifact_path="spec.md",
        content_hash="abc123",
        hash_algorithm="sha256",
        content_body="# Spec",
        size_bytes=6,
        retry_count=0,
        next_attempt_at=0,
        created_at=0,
        last_error=None,
    )


def test_body_transport_gate_uses_stable_project_attempt_and_no_http_on_denial(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = _seed_admitted_project(tmp_path, monkeypatch)
    posts: list[dict[str, Any]] = []

    def _post(url: str, *, data: bytes, headers: dict[str, str], timeout: float) -> Any:
        body = json.loads(data)
        posts.append({"url": url, "body": body, "raw": data, "headers": headers, "timeout": timeout})
        return SimpleNamespace(
            status_code=201,
            json=lambda: {
                "artifact_path": body["artifact_path"],
                "content_hash": body["content_hash"],
                "status": "stored",
            },
        )

    monkeypatch.setattr(
        "specify_cli.sync.body_transport.requests",
        SimpleNamespace(post=_post, ConnectionError=ConnectionError, Timeout=TimeoutError),
    )

    outcome = push_content_with_transport_gate(
        _body_task(),
        "token",
        _target(),
        "https://app.spec-kitty.ai",
    )

    assert outcome.status.value == "uploaded"
    assert posts[0]["body"]["project_uuid"] == PROJECT
    assert posts[0]["body"]["admission_generation"] == 9
    assert posts[0]["body"]["binding_audience"] == "private-teamspace:teamspace-1"
    assert posts[0]["headers"]["X-Spec-Kitty-Sync-Protocol"] == "2.0"
    with store.unit_of_work() as unit:
        rows = unit.execute(
            "SELECT state, admission_generation, binding_audience FROM delivery_attempts WHERE project_uuid = ?",
            (PROJECT,),
        ).fetchall()
    assert rows == [("succeeded", "9", "private-teamspace:teamspace-1")]

    denied = push_content_with_transport_gate(
        _body_task(OTHER),
        "token",
        _target(OTHER),
        "https://app.spec-kitty.ai",
    )
    assert denied.retryable is False
    assert "project_not_admitted" in denied.reason
    assert len(posts) == 1


def test_body_transport_gate_rejects_stale_admission_generation_before_http(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _seed_admitted_project(tmp_path, monkeypatch)
    current = _target()
    stale = DeliveryTarget(
        target_id=current.target_id,
        identity=current.identity,
        admission_state=current.admission_state,
        admission_generation=current.admission_generation + 1,
        binding_audience=current.binding_audience,
        last_error_category=None,
    )
    calls = 0

    def _post(*args: object, **kwargs: object) -> object:
        del args, kwargs
        nonlocal calls
        calls += 1
        raise AssertionError("stale admission authority must fail before HTTP")

    monkeypatch.setattr(
        "specify_cli.sync.body_transport.requests",
        SimpleNamespace(post=_post, ConnectionError=ConnectionError, Timeout=TimeoutError),
    )

    outcome = push_content_with_transport_gate(
        _body_task(),
        "token",
        stale,
        "https://app.spec-kitty.ai",
        context=store.create_context(),
    )

    assert outcome.status is UploadStatus.FAILED
    assert outcome.retryable is False
    assert "project_not_admitted" in outcome.reason
    assert calls == 0


def test_body_transport_gate_rejects_cross_target_server_before_attempt_or_http(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _seed_admitted_project(tmp_path, monkeypatch)
    calls = 0

    def _post(*args: object, **kwargs: object) -> object:
        del args, kwargs
        nonlocal calls
        calls += 1
        raise AssertionError("cross-target URL must fail before HTTP")

    monkeypatch.setattr(
        "specify_cli.sync.body_transport.requests",
        SimpleNamespace(post=_post, ConnectionError=ConnectionError, Timeout=TimeoutError),
    )

    outcome = push_content_with_transport_gate(
        _body_task(),
        "token",
        _target(),
        "https://other.example.test",
        context=store.create_context(),
    )

    assert outcome.status is UploadStatus.FAILED
    assert outcome.retryable is False
    assert "server URL does not match" in outcome.reason
    assert calls == 0
    with store.unit_of_work() as unit:
        attempts = unit.execute(
            "SELECT attempt_id FROM delivery_attempts WHERE project_uuid = ?",
            (PROJECT,),
        ).fetchall()
    assert attempts == []


@pytest.mark.parametrize(
    ("status_code", "response_status", "category_field", "expected_status"),
    [
        (201, "stored", None, UploadStatus.UPLOADED),
        (200, "already_exists", None, UploadStatus.ALREADY_EXISTS),
        (403, "rejected", "category", UploadStatus.FAILED),
    ],
)
def test_body_terminal_rerun_projects_exact_result_without_http(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    status_code: int,
    response_status: str,
    category_field: str | None,
    expected_status: UploadStatus,
) -> None:
    store = _seed_admitted_project(tmp_path, monkeypatch)
    posts = 0

    def _post(url: str, *, data: bytes, headers: dict[str, str], timeout: float) -> object:
        del url, headers, timeout
        nonlocal posts
        posts += 1
        body = json.loads(data)
        payload: dict[str, object] = {
            "artifact_path": body["artifact_path"],
            "content_hash": body["content_hash"],
            "status": response_status,
        }
        if category_field is not None:
            payload[category_field] = "project_not_admitted"
        return SimpleNamespace(status_code=status_code, json=lambda: payload)

    monkeypatch.setattr(
        "specify_cli.sync.body_transport.requests",
        SimpleNamespace(post=_post, ConnectionError=ConnectionError, Timeout=TimeoutError),
    )

    first = push_content_with_transport_gate(_body_task(), "token", _target(), "https://app.spec-kitty.ai")
    second = push_content_with_transport_gate(_body_task(), "token", _target(), "https://APP.spec-kitty.ai/")

    assert first.status is expected_status
    assert second.status is expected_status
    if expected_status is UploadStatus.FAILED:
        assert first.reason == second.reason == "project_not_admitted"
        assert second.retryable is False
    assert posts == 1
    with store.unit_of_work() as unit:
        attempt_count = unit.execute(
            "SELECT COUNT(*) FROM delivery_attempts WHERE project_uuid = ?",
            (PROJECT,),
        ).fetchone()
    assert attempt_count is not None and int(attempt_count[0]) == 1


def test_body_retryable_no_effect_restarts_same_attempt_but_unknown_does_not(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _seed_admitted_project(tmp_path, monkeypatch)
    responses = [
        SimpleNamespace(status_code=429, json=lambda: {"error": "rate_limited"}),
        SimpleNamespace(
            status_code=201,
            json=lambda: {
                "artifact_path": "spec.md",
                "content_hash": "abc123",
                "status": "stored",
            },
        ),
    ]
    posts = 0

    def _post(*args: object, **kwargs: object) -> object:
        del args, kwargs
        nonlocal posts
        posts += 1
        return responses.pop(0)

    monkeypatch.setattr(
        "specify_cli.sync.body_transport.requests",
        SimpleNamespace(post=_post, ConnectionError=ConnectionError, Timeout=TimeoutError),
    )

    first = push_content_with_transport_gate(_body_task(), "token", _target(), "https://app.spec-kitty.ai")
    with store.unit_of_work() as unit:
        first_row = unit.execute(
            "SELECT attempt_id, state FROM delivery_attempts WHERE project_uuid = ?",
            (PROJECT,),
        ).fetchone()
    assert first.status is UploadStatus.FAILED and first.reason == "rate_limited"
    assert first_row is not None and first_row[1] == DeliveryAttemptState.RETRYABLE_NO_EFFECT.value

    second = push_content_with_transport_gate(_body_task(), "token", _target(), "https://app.spec-kitty.ai")
    with store.unit_of_work() as unit:
        second_row = unit.execute(
            "SELECT attempt_id, state FROM delivery_attempts WHERE project_uuid = ?",
            (PROJECT,),
        ).fetchone()
    assert second.status is UploadStatus.UPLOADED
    assert second_row is not None and second_row[0] == first_row[0]
    assert second_row[1] == DeliveryAttemptState.SUCCEEDED.value
    assert posts == 2

    unknown_task = replace(
        _body_task(),
        row_id="body-row-unknown",
        artifact_path="plan.md",
        content_hash="def456",
    )
    responses.append(SimpleNamespace(status_code=500, json=lambda: {}))
    ambiguous = push_content_with_transport_gate(unknown_task, "token", _target(), "https://app.spec-kitty.ai")
    no_replay = push_content_with_transport_gate(unknown_task, "token", _target(), "https://app.spec-kitty.ai")
    assert ambiguous.status is UploadStatus.FAILED and ambiguous.retryable is True
    assert no_replay.status is UploadStatus.FAILED and no_replay.retryable is False
    assert "delivery_attempt_recovery_required" in no_replay.reason
    assert posts == 3
