"""Tests for outbound contract compatibility validation."""

from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path
from time import perf_counter

import pytest

from specify_cli.core.contract_gate import ContractViolationError, validate_outbound_payload
from tests.architectural.test_archive_root_byte_identical import _ARCHIVE_ROOTS

pytestmark = pytest.mark.fast

# Repo-relative location of the live contract-shape pin target (SK-154). Kept
# as a module constant so the class guard below (which must never regress to
# an archive-root path — see NFR-002 vs. this test's contradiction) checks the
# actual value in force, not a hand-duplicated copy of it.
_PLANNING_ARTIFACT_RELATIVE = Path("docs") / "contracts" / "upstream-3.0.0-shape.json"


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
        "admission_generation": 7,
        "binding_audience": "private-teamspace:teamspace-1",
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
    # Pin target is docs/contracts/upstream-3.0.0-shape.json, NOT the mission
    # 064 archive copy at kitty-specs/064-complete-mission-identity-cutover/
    # contracts/upstream-3.0.0-shape.json (SK-154). The archived copy is a
    # byte-frozen admission snapshot: tests/architectural/
    # test_archive_root_byte_identical.py (NFR-002) forbids any non-ADD change
    # to a file that already existed under kitty-specs/ at a mission's base
    # rev. This contract shape is a must-track-forever pin that later missions
    # legitimately extend (new verbs/error codes) as the upstream surface
    # grows, which directly contradicts a byte-freeze — the two gates cannot
    # both hold if the pin target lives inside an archive root. Repointing at
    # a live, non-archived copy resolves the contradiction without weakening
    # either gate: docs/contracts/ already hosts the repo's other living,
    # cross-mission contract artifacts (contract-registry.yaml). Do not point
    # this back at the mission 064 archive copy; that reopens SK-154.
    planning_artifact = Path(__file__).resolve().parents[3] / _PLANNING_ARTIFACT_RELATIVE
    vendored_artifact = files("specify_cli.core").joinpath("upstream_contract.json")

    vendored = json.loads(vendored_artifact.read_text(encoding="utf-8"))
    assert vendored == json.loads(planning_artifact.read_text(encoding="utf-8"))
    assert vendored["_source_saas_admission_commit"] == "29cc20c6ca5d61784af6f8b973a36131e69103af"
    assert vendored["_source_saas_admission_contract_sha256"] == "fe3a9f8d2563e3a9df386cd911ea858fd6a48913eb14c5b39d579b26bf3a4b35"


def test_planning_artifact_pin_target_is_outside_every_archive_root() -> None:
    """Class guard for SK-154: a must-track-forever pin target must never sit
    under a byte-frozen archive root (tests/architectural/
    test_archive_root_byte_identical.py, NFR-002), or the two gates
    contradict each other again the next time this contract shape grows.

    Non-vacuous: flip ``_PLANNING_ARTIFACT_RELATIVE`` back to a
    ``kitty-specs/...`` path (as SK-154 originally had it) and this fails.
    """
    pin_target = _PLANNING_ARTIFACT_RELATIVE.as_posix() + "/"
    violating_roots = [root for root in _ARCHIVE_ROOTS if pin_target.startswith(root)]
    assert not violating_roots, (
        f"contract pin target {_PLANNING_ARTIFACT_RELATIVE.as_posix()!r} lives under archive root(s) {violating_roots!r} — this reopens SK-154"
    )


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
            {
                "project_uuid": "proj-123",
                "target_branch": "main",
                "mission_type": "software-dev",
                "manifest_version": "3.0.0",
                "admission_generation": 7,
                "binding_audience": "private-teamspace:teamspace-1",
            },
            "mission_slug",
            "required field 'mission_slug' missing",
        ),
        (
            {key: value for key, value in _valid_body_sync().items() if key != "admission_generation"},
            "admission_generation",
            "required field 'admission_generation' missing",
        ),
        (
            {key: value for key, value in _valid_body_sync().items() if key != "binding_audience"},
            "binding_audience",
            "required field 'binding_audience' missing",
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
    payload = {"mission_slug": "legacy-value"}
    original = dict(payload)

    assert validate_outbound_payload(payload, "future_surface") is None
    assert payload == original


def test_payload_context_rejects_forbidden_fields() -> None:
    """Nested payload.mission_scoped rules must be enforced."""
    bad = {"feature_slug": "064-leaky", "mission_slug": "064-ok", "mission_number": "064", "mission_type": "software-dev"}
    with pytest.raises(ContractViolationError) as exc_info:
        validate_outbound_payload(bad, "payload")
    assert "feature_slug" in str(exc_info.value)


def test_payload_context_requires_mission_fields() -> None:
    """Nested payload.mission_scoped required fields must be checked."""
    incomplete = {"mission_slug": "064-ok"}  # missing mission_number, mission_type
    with pytest.raises(ContractViolationError) as exc_info:
        validate_outbound_payload(incomplete, "payload")
    assert "mission_number" in str(exc_info.value) or "mission_type" in str(exc_info.value)


def test_payload_context_passes_valid() -> None:
    valid = {"mission_slug": "064-ok", "mission_number": "064", "mission_type": "software-dev"}
    validate_outbound_payload(valid, "payload")  # should not raise


def test_gate_validates_quickly() -> None:
    payload = _valid_envelope()

    validate_outbound_payload(payload, "envelope")

    started_at = perf_counter()
    for _ in range(1000):
        validate_outbound_payload(payload, "envelope")
    elapsed = perf_counter() - started_at

    assert elapsed < 0.05
