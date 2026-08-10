"""WP07 interactive senders consume WP06's per-project final gate."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from specify_cli.delivery.consent_gate import (
    ProjectTransportDisclosure,
    ProjectTransportRefusal,
    execute_project_transport_disclosure,
)
from specify_cli.delivery.interfaces import DeliveryTarget, TargetIdentity
from specify_cli.delivery.targets import compute_target_id
from specify_cli.sync.body_queue import BodyUploadTask
from specify_cli.sync.body_transport import push_content_with_transport_gate
from specify_cli.sync.consent import record_project_opt_in
from specify_cli.sync.project_context import AdmissionState
from specify_cli.sync.project_identity import CanonicalProjectUUID
from specify_cli.sync.project_store import ProjectSyncStore
from specify_cli.sync.transport_attempts import DeliveryAttemptState, DeliveryOutcome

pytestmark = pytest.mark.fast

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
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "home"))
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
    _seed_admitted_project(tmp_path, monkeypatch)
    posts: list[dict[str, Any]] = []

    def _post(url: str, *, json: dict[str, Any], headers: dict[str, str], timeout: float) -> Any:
        posts.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        return SimpleNamespace(status_code=201, json=lambda: {})

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
    assert posts[0]["json"]["project_uuid"] == PROJECT

    denied = push_content_with_transport_gate(
        _body_task(OTHER),
        "token",
        _target(OTHER),
        "https://app.spec-kitty.ai",
    )
    assert denied.retryable is False
    assert "project_not_admitted" in denied.reason
    assert len(posts) == 1
