"""Conformance test suite for spec-kitty-events.

Run: pytest --pyargs spec_kitty_events.conformance
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pytest

from ..conformance.pytest_helpers import (
    assert_lane_mapping,
    assert_payload_conforms,
    assert_payload_fails,
)
from ..conformance.validators import validate_event
from ..schemas import list_schemas, load_schema
from ..status import Lane, SyncLaneV1, CANONICAL_TO_SYNC_V1


# --- Manifest-driven fixture tests ---

_FIXTURES_DIR = Path(__file__).parent / "fixtures"
_MANIFEST: Dict[str, Any] = json.loads(
    (_FIXTURES_DIR / "manifest.json").read_text(encoding="utf-8")
)


def _event_fixture_entries() -> List[Dict[str, Any]]:
    """Return manifest entries that are event-type fixtures (not LaneMapping, replay streams, or reducer outputs)."""
    return [
        f for f in _MANIFEST["fixtures"]
        if f["event_type"] != "LaneMapping"
        and f.get("fixture_type") not in ("replay_stream", "reducer_output")
    ]


def _event_fixture_ids() -> List[str]:
    return [f["id"] for f in _event_fixture_entries()]


def _event_fixture_params() -> List[Dict[str, Any]]:
    params: List[Dict[str, Any]] = []
    for entry in _event_fixture_entries():
        fixture_path = _FIXTURES_DIR / entry["path"]
        payload: Any = json.loads(fixture_path.read_text(encoding="utf-8"))
        params.append({**entry, "payload": payload})
    return params


def _lane_mapping_fixture_entries() -> List[Dict[str, Any]]:
    """Return manifest entries for lane mapping fixtures."""
    return [f for f in _MANIFEST["fixtures"] if f["event_type"] == "LaneMapping"]


def _lane_mapping_fixture_ids() -> List[str]:
    return [f["id"] for f in _lane_mapping_fixture_entries()]


def _lane_mapping_fixture_params() -> List[Dict[str, Any]]:
    params: List[Dict[str, Any]] = []
    for entry in _lane_mapping_fixture_entries():
        fixture_path = _FIXTURES_DIR / entry["path"]
        payload: Any = json.loads(fixture_path.read_text(encoding="utf-8"))
        params.append({**entry, "payload": payload})
    return params


# --- Event fixture conformance tests ---


@pytest.mark.parametrize("case", _event_fixture_params(), ids=_event_fixture_ids())
def test_fixture_conformance(case: Dict[str, Any]) -> None:
    """Validate each event fixture against its expected result.

    Uses dual-layer validation. For expected-valid fixtures the Pydantic
    model layer must pass; schema-only violations (e.g. alias values
    that Pydantic normalises but JSON Schema rejects) are permitted.
    For expected-invalid fixtures both layers are checked.
    """
    result = validate_event(case["payload"], case["event_type"])
    if case["expected_result"] == "valid":
        # Pydantic model layer must accept the payload
        if result.model_violations:
            violations = [
                f"  Model: {v.field} \u2014 {v.message}"
                for v in result.model_violations
            ]
            raise AssertionError(
                f"Payload for {case['event_type']!r} (fixture {case['id']}) "
                f"failed model conformance:\n" + "\n".join(violations)
            )
    else:
        # At least one layer must reject the payload
        if result.valid:
            raise AssertionError(
                f"Payload for {case['event_type']!r} (fixture {case['id']}) "
                f"was expected to fail but passed conformance."
            )


# --- Lane mapping fixture conformance tests ---


@pytest.mark.parametrize(
    "case", _lane_mapping_fixture_params(), ids=_lane_mapping_fixture_ids()
)
def test_lane_mapping_fixture_conformance(case: Dict[str, Any]) -> None:
    """Validate lane mapping fixtures against expected results."""
    mappings: Any = case["payload"]
    assert isinstance(mappings, list), (
        f"Lane mapping fixture {case['id']} payload must be a list"
    )
    if case["expected_result"] == "valid":
        for mapping in mappings:
            assert_lane_mapping(mapping["canonical"], mapping["expected_sync"])
    else:
        # Invalid lane mapping: at least one entry should fail
        failures = 0
        for mapping in mappings:
            try:
                Lane(mapping["canonical"])
            except ValueError:
                failures += 1
        assert failures > 0, (
            f"Lane mapping fixture {case['id']} expected invalid entries "
            f"but all passed Lane construction"
        )


# --- Lane mapping completeness tests ---


def test_lane_mapping_v1_completeness() -> None:
    """All canonical lanes have a sync mapping."""
    assert set(CANONICAL_TO_SYNC_V1.keys()) == set(Lane)


def test_lane_mapping_v1_output_type() -> None:
    """All mapping outputs are SyncLaneV1 members."""
    for sync_lane in CANONICAL_TO_SYNC_V1.values():
        assert isinstance(sync_lane, SyncLaneV1)


@pytest.mark.parametrize("lane", list(Lane), ids=[l.value for l in Lane])
def test_lane_mapping_v1_each_lane(lane: Lane) -> None:
    """Each canonical lane maps to a SyncLaneV1."""
    result = CANONICAL_TO_SYNC_V1[lane]
    assert isinstance(result, SyncLaneV1)


# --- Schema integrity tests ---


def test_all_schemas_present() -> None:
    """All expected schemas exist."""
    schemas = list_schemas()
    assert len(schemas) >= 11


@pytest.mark.parametrize("name", list_schemas())
def test_schema_is_valid_json_schema(name: str) -> None:
    """Each schema file is a valid JSON Schema document."""
    schema = load_schema(name)
    assert "$schema" in schema
    assert "$id" in schema


# --- Round-trip serialization tests ---


def test_event_round_trip() -> None:
    """Event model round-trips through JSON."""
    from datetime import datetime, timezone
    from uuid import UUID

    from ..models import Event

    event = Event(
        event_id="01JMXXXXXXXXXXXXXXXXXXXXXX",
        event_type="TestEvent",
        aggregate_id="agg-001",
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        build_id="build-test-conformance",
        node_id="node-1",
        lamport_clock=1,
        causation_id=None,
        project_uuid=UUID("550e8400-e29b-41d4-a716-446655440000"),
        project_slug=None,
        correlation_id="01JMYYYYYYYYYYYYYYYYYYYYYY",
    )
    data = event.model_dump(mode="json")
    restored = Event.model_validate(data)
    assert restored == event
