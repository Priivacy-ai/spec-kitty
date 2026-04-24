"""Reusable test helpers for spec-kitty-events conformance testing.

Consumers can import these to write their own conformance assertions:
    from ..conformance.pytest_helpers import (
        assert_payload_conforms,
        assert_payload_fails,
        assert_lane_mapping,
    )
"""
from __future__ import annotations

from typing import Any, Dict

from ..conformance.validators import (
    ConformanceResult,
    validate_event,
)
from ..status import Lane, SyncLaneV1, canonical_to_sync_v1


def assert_payload_conforms(
    payload: Dict[str, Any],
    event_type: str,
    *,
    strict: bool = False,
) -> ConformanceResult:
    """Assert a payload conforms to the canonical contract."""
    result = validate_event(payload, event_type, strict=strict)
    if not result.valid:
        violations = []
        for mv in result.model_violations:
            violations.append(f"  Model: {mv.field} \u2014 {mv.message}")
        for sv in result.schema_violations:
            violations.append(f"  Schema: {sv.json_path} \u2014 {sv.message}")
        raise AssertionError(
            f"Payload for {event_type!r} failed conformance:\n"
            + "\n".join(violations)
        )
    return result


def assert_payload_fails(
    payload: Dict[str, Any],
    event_type: str,
    *,
    strict: bool = False,
) -> ConformanceResult:
    """Assert a payload DOES NOT conform (expected invalid)."""
    result = validate_event(payload, event_type, strict=strict)
    if result.valid:
        raise AssertionError(
            f"Payload for {event_type!r} was expected to fail but passed conformance."
        )
    return result


def assert_lane_mapping(
    canonical_value: str,
    expected_sync_value: str,
) -> None:
    """Assert a canonical lane maps to the expected sync lane."""
    lane = Lane(canonical_value)
    sync = canonical_to_sync_v1(lane)
    assert sync == SyncLaneV1(expected_sync_value), (
        f"Expected {canonical_value!r} \u2192 {expected_sync_value!r}, "
        f"got {sync.value!r}"
    )
