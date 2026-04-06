"""Tests for outbound contract compatibility validation."""

from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path
from time import perf_counter

import pytest

from specify_cli.core.contract_gate import ContractViolationError, validate_outbound_payload

pytestmark = pytest.mark.fast


def _valid_envelope() -> dict[str, object]:
    return {
        "schema_version": "3.0.0",
        "build_id": "build-123",
        "aggregate_type": "Mission",
        "event_type": "mission.started",
    }


def _valid_body_sync() -> dict[str, object]:
    return {
        "project_uuid": "proj-123",
        "mission_slug": "064-complete-mission-identity-cutover",
        "target_branch": "main",
        "mission_type": "software-dev",
        "manifest_version": "3.0.0",
    }


def _valid_tracker_bind() -> dict[str, object]:
    return {
        "uuid": "tracker-uuid",
        "slug": "wp01",
        "node_id": "node-1",
        "repo_slug": "priivacy-ai/spec-kitty",
        "build_id": "build-123",
    }


def _valid_orchestrator_api() -> dict[str, object]:
    return {
        "mission_slug": "064-complete-mission-identity-cutover",
        "commands": "mission-state",
        "error_codes": "MISSION_NOT_FOUND",
        "cli_flags": "--mission",
    }


def test_vendored_contract_matches_planning_artifact() -> None:
    planning_artifact = Path(__file__).resolve().parents[3] / "kitty-specs" / "064-complete-mission-identity-cutover" / "contracts" / "upstream-3.0.0-shape.json"
    vendored_artifact = files("specify_cli.core").joinpath("upstream_contract.json")

    assert json.loads(vendored_artifact.read_text(encoding="utf-8")) == json.loads(planning_artifact.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    ("payload", "field", "message"),
    [
        ({**_valid_envelope(), "feature_slug": "064-complete-mission-identity-cutover"}, "feature_slug", "forbidden field 'feature_slug' present"),
        ({**_valid_envelope(), "feature_number": "064"}, "feature_number", "forbidden field 'feature_number' present"),
        ({"build_id": "build-123", "aggregate_type": "Mission", "event_type": "mission.started"}, "schema_version", "required field 'schema_version' missing"),
        ({"schema_version": "3.0.0", "aggregate_type": "Mission", "event_type": "mission.started"}, "build_id", "required field 'build_id' missing"),
        ({**_valid_envelope(), "aggregate_type": "Feature"}, "aggregate_type", "must be one of"),
    ],
)
def test_envelope_rejects_invalid_payloads(payload: dict[str, object], field: str, message: str) -> None:
    with pytest.raises(ContractViolationError, match=message) as exc_info:
        validate_outbound_payload(payload, "envelope")

    assert exc_info.value.field == field
    assert exc_info.value.context == "envelope"


@pytest.mark.parametrize(
    ("payload", "field", "message"),
    [
        ({**_valid_body_sync(), "feature_slug": "064-complete-mission-identity-cutover"}, "feature_slug", "forbidden field 'feature_slug' present"),
        ({**_valid_body_sync(), "mission_key": "legacy-key"}, "mission_key", "forbidden field 'mission_key' present"),
        (
            {"project_uuid": "proj-123", "target_branch": "main", "mission_type": "software-dev", "manifest_version": "3.0.0"},
            "mission_slug",
            "required field 'mission_slug' missing",
        ),
    ],
)
def test_body_sync_rejects_invalid_payloads(payload: dict[str, object], field: str, message: str) -> None:
    with pytest.raises(ContractViolationError, match=message) as exc_info:
        validate_outbound_payload(payload, "body_sync")

    assert exc_info.value.field == field
    assert exc_info.value.context == "body_sync"


def test_tracker_bind_requires_build_id() -> None:
    payload = {
        "uuid": "tracker-uuid",
        "slug": "wp01",
        "node_id": "node-1",
        "repo_slug": "priivacy-ai/spec-kitty",
    }

    with pytest.raises(ContractViolationError, match="required field 'build_id' missing") as exc_info:
        validate_outbound_payload(payload, "tracker_bind")

    assert exc_info.value.field == "build_id"
    assert exc_info.value.context == "tracker_bind"


@pytest.mark.parametrize(
    ("payload", "field", "message"),
    [
        ({**_valid_orchestrator_api(), "feature_slug": "064-complete-mission-identity-cutover"}, "feature_slug", "forbidden field 'feature_slug' present"),
        ({"commands": "mission-state", "error_codes": "MISSION_NOT_FOUND", "cli_flags": "--mission"}, "mission_slug", "required field 'mission_slug' missing"),
    ],
)
def test_orchestrator_api_rejects_invalid_payloads(payload: dict[str, object], field: str, message: str) -> None:
    with pytest.raises(ContractViolationError, match=message) as exc_info:
        validate_outbound_payload(payload, "orchestrator_api")

    assert exc_info.value.field == field
    assert exc_info.value.context == "orchestrator_api"


def test_valid_envelope_passes_without_mutation() -> None:
    payload = _valid_envelope()
    original = dict(payload)

    assert validate_outbound_payload(payload, "envelope") is None
    assert payload == original


def test_valid_body_sync_passes() -> None:
    payload = _valid_body_sync()

    assert validate_outbound_payload(payload, "body_sync") is None


def test_valid_tracker_bind_passes() -> None:
    payload = _valid_tracker_bind()

    assert validate_outbound_payload(payload, "tracker_bind") is None


def test_unknown_context_is_noop() -> None:
    payload = {"feature_slug": "legacy-value"}
    original = dict(payload)

    assert validate_outbound_payload(payload, "future_surface") is None
    assert payload == original


def test_gate_validates_quickly() -> None:
    payload = _valid_envelope()

    validate_outbound_payload(payload, "envelope")

    started_at = perf_counter()
    for _ in range(1000):
        validate_outbound_payload(payload, "envelope")
    elapsed = perf_counter() - started_at

    assert elapsed < 0.05
