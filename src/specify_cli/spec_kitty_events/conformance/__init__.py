"""Conformance test suite for spec-kitty-events.

Run: pytest --pyargs spec_kitty_events.conformance
"""
from ..conformance.loader import (
    FixtureCase,
    load_fixtures,
    load_replay_stream,
)
from ..conformance.pytest_helpers import (
    assert_lane_mapping,
    assert_payload_conforms,
    assert_payload_fails,
)
from ..conformance.validators import (
    ConformanceResult,
    ModelViolation,
    SchemaViolation,
    validate_event,
)

__all__ = [
    "ConformanceResult",
    "FixtureCase",
    "ModelViolation",
    "SchemaViolation",
    "assert_lane_mapping",
    "assert_payload_conforms",
    "assert_payload_fails",
    "load_fixtures",
    "load_replay_stream",
    "validate_event",
]
