from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

import pytest
from spec_kitty_events.models import Event

from specify_cli.proof.events import PROOF_EVENT_TYPES
from specify_cli.sync.diagnose import diagnose_events
from specify_cli.sync.emitter import EventEmitter, VALID_EVENT_TYPES
from specify_cli.sync.queue import OfflineQueue

pytestmark = pytest.mark.fast


def _test_payload() -> dict[str, object]:
    return {
        "subject": {
            "subject_type": "work_package",
            "subject_id": "WP02",
            "mission_id": "01JTJ8M3Z3ZV4A6J3B1Q4JQ8RM",
            "mission_slug": "1223-cli-evidence-event-schema",
            "wp_id": "WP02",
        },
        "source": "pytest",
        "actor": {"actor_id": "codex", "actor_type": "llm"},
        "confidence": 0.87,
        "occurred_at": "2026-06-09T13:00:00+00:00",
        "observed_at": "2026-06-09T13:00:02+00:00",
        "artifact_refs": [
            {
                "kind": "log",
                "uri": "artifacts/proof/pytest.log",
                "sha256": "c" * 64,
            }
        ],
        "summary": {"status": "passed"},
        "test_command": "pytest tests/proof",
        "exit_code": 0,
        "status": "passed",
        "runner": "pytest",
    }


def test_proof_event_types_are_outbound_cli_types() -> None:
    assert PROOF_EVENT_TYPES <= VALID_EVENT_TYPES


def test_emit_proof_event_queues_bounded_payload(
    emitter: EventEmitter,
    temp_queue: OfflineQueue,
) -> None:
    event = emitter.emit_proof_event("TestEvidenceCaptured", _test_payload())

    assert event is not None
    assert event["event_type"] == "TestEvidenceCaptured"
    assert event["aggregate_type"] == "WorkPackage"
    assert event["aggregate_id"] == "WP02"
    assert event["timestamp"] == "2026-06-09T13:00:00Z"
    assert event["payload"]["source"] == "pytest"
    assert event["payload"]["idempotency_key"]
    assert event["payload"]["mission_id"] == "01JTJ8M3Z3ZV4A6J3B1Q4JQ8RM"
    assert event["payload"]["mission_slug"] == "1223-cli-evidence-event-schema"
    assert event["payload"]["wp_id"] == "WP02"
    assert event["payload"]["subject"]["project_uuid"]
    assert event["payload"]["subject"]["build_id"] == "test-build-id-0000-0000-000000000001"
    assert event["payload"]["subject"]["repo_slug"] == "test-org/test-repo"
    assert event["payload"]["subject"]["git_branch"] == "test-branch"
    assert event["payload"]["subject"]["head_commit_sha"] == "a" * 40
    assert temp_queue.size() == 1


def test_proof_subject_uses_cached_team_when_saas_sync_disabled(
    emitter: EventEmitter,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "0")

    def fail_if_direct_ingress_resolves(self: EventEmitter) -> str | None:
        raise AssertionError("direct-ingress team resolver should stay behind SaaS sync")

    monkeypatch.setattr(EventEmitter, "_get_team_slug", fail_if_direct_ingress_resolves)
    monkeypatch.setattr(
        "specify_cli.auth.get_token_manager",
        lambda: SimpleNamespace(
            get_current_session=lambda: SimpleNamespace(
                teams=[
                    SimpleNamespace(
                        id="private-team-id",
                        is_private_teamspace=True,
                    )
                ],
            )
        ),
    )

    event = emitter.emit_proof_event("TestEvidenceCaptured", _test_payload())

    assert event is not None
    assert event["team_slug"] is None
    assert event["payload"]["subject"]["team_slug"] == "private-team-id"


def test_emitted_proof_event_passes_queue_diagnose(
    emitter: EventEmitter,
    temp_queue: OfflineQueue,
) -> None:
    event = emitter.emit_proof_event("TestEvidenceCaptured", _test_payload())

    assert event is not None
    results = diagnose_events(temp_queue.drain_queue())
    assert len(results) == 1
    assert results[0].valid is True
    assert results[0].event_type == "TestEvidenceCaptured"


def test_malformed_proof_event_is_rejected_before_queue(
    emitter: EventEmitter,
    temp_queue: OfflineQueue,
) -> None:
    payload = _test_payload()
    payload["confidence"] = 1.8

    event = emitter.emit_proof_event("TestEvidenceCaptured", payload)

    assert event is None
    assert temp_queue.size() == 0


def test_diagnose_rejects_queued_proof_payload_missing_idempotency_key(
    emitter: EventEmitter,
) -> None:
    payload = _test_payload()
    payload.pop("test_command")
    event = Event(
        event_id=emitter.generate_causation_id(),
        event_type="TestEvidenceCaptured",
        aggregate_id="WP02",
        payload=payload,
        timestamp=datetime(2026, 6, 9, 13, 0, 0, tzinfo=UTC),
        build_id="test-build",
        node_id="test-node",
        lamport_clock=1,
        causation_id=None,
        project_uuid=UUID("550e8400-e29b-41d4-a716-446655440000"),
        correlation_id=emitter.generate_causation_id(),
    ).model_dump(mode="json")
    event["aggregate_type"] = "WorkPackage"

    result = diagnose_events([event])[0]

    assert result.valid is False
    assert any("test_command" in error for error in result.errors)
