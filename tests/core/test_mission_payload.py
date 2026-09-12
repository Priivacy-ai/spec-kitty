"""Tests for the canonical ``MissionCreated`` payload builder (#2270).

The local lifecycle emitter and (historically) the sync emitter both build
through :mod:`specify_cli.core.mission_payload` so their wire shapes cannot
drift. These tests pin that shape directly at the builder, including the
optional 8.0.0 ``actor`` WHO field (#75).
"""

from __future__ import annotations

import pytest

from specify_cli.core.mission_payload import (
    build_mission_created_payload,
    default_mission_display_name,
    default_mission_purpose_context,
)

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def _build(**overrides):
    kwargs = {
        "mission_slug": "demo-mission",
        "target_branch": "main",
        "mission_type": "software-dev",
        "wp_count": 2,
        "mission_id": "01ULIDEXAMPLE0000000000000",
        "mission_number": None,
    }
    kwargs.update(overrides)
    return build_mission_created_payload(**kwargs)


def test_actor_absent_from_wire_shape_when_not_given() -> None:
    payload = _build()
    assert "actor" not in payload
    # The keep-none contract is untouched: pre-merge nullity survives (FR-024).
    assert payload["mission_number"] is None


def test_explicit_actor_rides_the_wire() -> None:
    payload = _build(actor="robert@example.com")
    assert payload["actor"] == "robert@example.com"
    assert payload["friendly_name"] == "demo mission"


def test_defaults_are_derived_when_optionals_omitted() -> None:
    payload = _build()
    assert payload["friendly_name"] == "demo mission"
    assert payload["purpose_tldr"] == "demo mission"
    assert payload["purpose_context"] == default_mission_purpose_context(default_mission_display_name("demo-mission"), "main")
    assert payload["created_at"]


def test_empty_actor_is_rejected_at_the_builder_boundary() -> None:
    """An empty-string actor is not a valid identity: the model rejects it.

    ``MissionCreatedPayload.actor`` carries ``min_length=1`` — the same
    producer-time validation every other field gets (#1198/#1200). The emit
    site never produces this shape (its fallback is ``"cli"``); this pins the
    builder against emitting an unrenderable WHO.
    """
    with pytest.raises(Exception, match="actor"):
        _build(actor="")
