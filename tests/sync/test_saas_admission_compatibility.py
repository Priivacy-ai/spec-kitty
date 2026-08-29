"""Compatibility tests for the narrow SaaS-owned admission HTTP shapes."""

from __future__ import annotations

import pytest

from specify_cli.saas_client.admission import (
    AdmissionHttpRequest,
    AdmissionHttpResponse,
    AdmissionResponse,
    ProjectNotAdmitted,
    ProjectWriteAdmissionProof,
    SaasAdmissionClient,
    attach_admission_proof,
    parse_project_not_admitted,
)

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

PROJECT = "aaaaaaaa-0000-0000-0000-000000000001"
KEY = "operation-key-00000000000000000001"


class RecordingTransport:
    def __init__(self, response: AdmissionHttpResponse) -> None:
        self.response = response
        self.requests: list[AdmissionHttpRequest] = []

    def send(self, request: AdmissionHttpRequest) -> AdmissionHttpResponse:
        self.requests.append(request)
        return self.response


def _client(response: AdmissionHttpResponse) -> tuple[SaasAdmissionClient, RecordingTransport]:
    transport = RecordingTransport(response)
    return SaasAdmissionClient(transport), transport


def test_admit_and_readmit_use_put_idempotency_and_optional_cas() -> None:
    client, transport = _client(
        AdmissionHttpResponse(
            status_code=200,
            json_body={
                "source_project_uuid": PROJECT,
                "state": "admitted",
                "generation": 2,
                "binding_audience": "opaque",
            },
        )
    )

    response = client.admit(
        source_project_uuid=PROJECT,
        operation_key=KEY,
        expected_generation=1,
        project_slug="display-only",
    )

    request = transport.requests[0]
    assert request.method == "PUT"
    assert request.path == f"/api/v1/sync/projects/{PROJECT}/sync-admission/"
    assert request.headers == {
        "Idempotency-Key": KEY,
        "If-Match-Admission-Generation": "1",
    }
    assert request.json_body == {"project_slug": "display-only"}
    assert response == AdmissionResponse(
        source_project_uuid=PROJECT,
        state="admitted",
        generation=2,
        binding_audience="opaque",
    )


def test_revoke_uses_delete_and_requires_expected_generation() -> None:
    client, transport = _client(
        AdmissionHttpResponse(
            status_code=200,
            json_body={
                "source_project_uuid": PROJECT,
                "state": "revoked",
                "generation": 3,
                "binding_audience": "opaque",
            },
        )
    )

    client.revoke(
        source_project_uuid=PROJECT,
        operation_key=KEY,
        expected_generation=2,
    )

    request = transport.requests[0]
    assert request.method == "DELETE"
    assert request.headers["Idempotency-Key"] == KEY
    assert request.headers["If-Match-Admission-Generation"] == "2"
    assert request.json_body is None
    with pytest.raises(ValueError):
        client.revoke(
            source_project_uuid=PROJECT,
            operation_key=KEY,
            expected_generation=0,
        )


@pytest.mark.parametrize(
    ("status", "category"),
    (
        (400, "invalid_admission_request"),
        (401, "authentication_required"),
        (403, "admission_mutation_forbidden"),
        (404, "project_sync_admission_not_found"),
        (409, "admission_generation_conflict"),
        (409, "admission_operation_conflict"),
        (409, "project_tombstoned"),
    ),
)
def test_typed_refusals_are_nonretryable(status: int, category: str) -> None:
    client, _transport = _client(
        AdmissionHttpResponse(
            status_code=status,
            json_body={"error_category": category, "retryable": False, "current_generation": 7},
        )
    )

    response = client.admit(source_project_uuid=PROJECT, operation_key=KEY)

    assert response.error_category == category
    assert response.retryable is False
    assert response.current_generation == 7


def test_each_project_bearing_write_gets_its_own_proof() -> None:
    proof = ProjectWriteAdmissionProof(
        project_uuid=PROJECT,
        admission_generation=7,
        binding_audience="opaque-binding",
    )
    payloads = {
        "event": {"event_id": "event-1", "payload": {}},
        "mixed_batch_item": {"event_id": "event-2", "payload": {}},
        "websocket_event": {"type": "event", "event_id": "event-3", "payload": {}},
        "local_commit": {"type": "LocalCommit", "git_hash": "abc"},
        "dossier_body": {"artifact_path": "spec.md", "content_hash": "def"},
        "history_preflight_event": {"event_id": "event-4", "payload": {}},
    }

    proved = {name: attach_admission_proof(payload, proof) for name, payload in payloads.items()}

    for item in proved.values():
        assert item["project_uuid"] == PROJECT
        assert item["admission_generation"] == 7
        assert item["binding_audience"] == "opaque-binding"
    assert len({id(item) for item in proved.values()}) == len(proved)


@pytest.mark.parametrize(
    ("kind", "payload", "correlation"),
    (
        ("event", {"event_id": "e1"}, ("event_id",)),
        ("mixed_batch_item", {"event_id": "e2"}, ("event_id",)),
        ("websocket_event", {"type": "error", "event_id": "e3"}, ("event_id",)),
        ("local_commit", {"type": "LocalCommitAck", "git_hash": "g1"}, ("git_hash",)),
        ("dossier_body", {"artifact_path": "spec.md", "content_hash": "h1"}, ("artifact_path", "content_hash")),
        ("history_preflight_event", {"event_id": "e4"}, ("event_id",)),
    ),
)
def test_project_not_admitted_is_correlated_terminal_and_payload_free(
    kind: str,
    payload: dict[str, object],
    correlation: tuple[str, ...],
) -> None:
    refusal_payload = {
        **payload,
        "status": "rejected",
        "error_category": "project_not_admitted",
        "retryable": False,
    }

    refusal = parse_project_not_admitted(kind, refusal_payload, correlation)

    assert refusal == ProjectNotAdmitted(
        write_kind=kind,
        correlation=tuple((field, str(payload[field])) for field in correlation),
    )
    assert "payload" not in repr(refusal)


def test_websocket_auth_is_header_only() -> None:
    proof = ProjectWriteAdmissionProof(PROJECT, 1, "opaque")
    message = attach_admission_proof({"type": "event", "event_id": "e1"}, proof)
    headers = SaasAdmissionClient.websocket_headers("secret-token", protocol="2")

    assert headers == {
        "Authorization": "Bearer secret-token",
        "X-Spec-Kitty-Sync-Protocol": "2",
    }
    assert "token" not in message
    assert "query" not in message
