"""Unit tests for ActorIdentity and parse_agent_identity."""

from __future__ import annotations

import pytest

from specify_cli.identity import ActorIdentity, parse_agent_identity
from specify_cli.status.models import StatusEvent, Lane

pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# ActorIdentity construction
# ---------------------------------------------------------------------------


def test_from_compact_full() -> None:
    ai = ActorIdentity.from_compact("claude:opus:impl:impl")
    assert ai.tool == "claude"
    assert ai.model == "opus"
    assert ai.profile == "impl"
    assert ai.role == "impl"


def test_from_compact_partial_two() -> None:
    ai = ActorIdentity.from_compact("claude:opus")
    assert ai.tool == "claude"
    assert ai.model == "opus"
    assert ai.profile == "unknown"
    assert ai.role == "unknown"


def test_from_compact_single() -> None:
    ai = ActorIdentity.from_compact("claude")
    assert ai.tool == "claude"
    assert ai.model == "unknown"
    assert ai.profile == "unknown"
    assert ai.role == "unknown"


def test_from_compact_empty_parts_use_unknown() -> None:
    ai = ActorIdentity.from_compact("claude::impl:")
    assert ai.tool == "claude"
    assert ai.model == "unknown"
    assert ai.profile == "impl"
    assert ai.role == "unknown"


def test_from_dict_full() -> None:
    ai = ActorIdentity.from_dict({"tool": "gemini", "model": "pro", "profile": "planner", "role": "planner"})
    assert ai.tool == "gemini"
    assert ai.model == "pro"
    assert ai.profile == "planner"
    assert ai.role == "planner"


def test_from_dict_partial_defaults_to_unknown() -> None:
    ai = ActorIdentity.from_dict({"tool": "cursor"})
    assert ai.tool == "cursor"
    assert ai.model == "unknown"
    assert ai.profile == "unknown"
    assert ai.role == "unknown"


def test_from_legacy_bare_string() -> None:
    ai = ActorIdentity.from_legacy("claude")
    assert ai.tool == "claude"
    assert ai.model == "unknown"


def test_from_legacy_compound_string() -> None:
    ai = ActorIdentity.from_legacy("claude:opus:reviewer:reviewer")
    assert ai.role == "reviewer"


# ---------------------------------------------------------------------------
# Serialisation round-trip
# ---------------------------------------------------------------------------


def test_to_dict_round_trip() -> None:
    ai = ActorIdentity.from_compact("claude:opus:impl:impl")
    d = ai.to_dict()
    assert d == {"tool": "claude", "model": "opus", "profile": "impl", "role": "impl"}
    ai2 = ActorIdentity.from_dict(d)
    assert ai == ai2


def test_to_compact_round_trip() -> None:
    original = "claude:opus:impl:impl"
    ai = ActorIdentity.from_compact(original)
    assert ai.to_compact() == original


# ---------------------------------------------------------------------------
# Frozen dataclass (immutability)
# ---------------------------------------------------------------------------


def test_actor_identity_is_frozen() -> None:
    ai = ActorIdentity.from_compact("claude")
    with pytest.raises((AttributeError, TypeError)):
        ai.tool = "mutated"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# StatusEvent backwards compatibility
# ---------------------------------------------------------------------------


def _make_event(**overrides: object) -> StatusEvent:
    defaults: dict[str, object] = {
        "event_id": "01JXXXXXXXXXXXXXXXXXXX0001",
        "mission_slug": "048-test",
        "wp_id": "WP01",
        "from_lane": Lane.PLANNED,
        "to_lane": Lane.CLAIMED,
        "at": "2026-03-08T00:00:00+00:00",
        "actor": ActorIdentity.from_compact("claude"),
        "force": False,
        "execution_mode": "worktree",
    }
    defaults.update(overrides)
    return StatusEvent(**defaults)  # type: ignore[arg-type]


def test_status_event_actor_is_actor_identity() -> None:
    event = _make_event(actor=ActorIdentity.from_compact("claude:opus"))
    assert isinstance(event.actor, ActorIdentity)
    assert event.actor.tool == "claude"


def test_status_event_coerces_legacy_string_actor() -> None:
    event = _make_event(actor="claude")
    assert isinstance(event.actor, ActorIdentity)
    assert event.actor.tool == "claude"


def test_status_event_to_dict_emits_actor_as_dict() -> None:
    event = _make_event(actor=ActorIdentity.from_compact("claude:opus:impl:impl"))
    d = event.to_dict()
    assert isinstance(d["actor"], dict)
    assert d["actor"]["tool"] == "claude"
    assert d["actor"]["model"] == "opus"


def test_status_event_from_dict_structured_actor() -> None:
    event = _make_event(actor=ActorIdentity.from_compact("claude:opus:impl:impl"))
    d = event.to_dict()
    event2 = StatusEvent.from_dict(d)
    assert event2.actor == event.actor


def test_status_event_from_dict_legacy_string_actor() -> None:
    event = _make_event(actor=ActorIdentity.from_compact("claude"))
    d = event.to_dict()
    # Simulate a legacy JSONL line with bare-string actor
    d["actor"] = "claude"
    event2 = StatusEvent.from_dict(d)
    assert isinstance(event2.actor, ActorIdentity)
    assert event2.actor.tool == "claude"


def test_status_event_round_trip_preserves_all_fields() -> None:
    ai = ActorIdentity.from_compact("claude:opus:impl:impl")
    event = _make_event(actor=ai)
    d = event.to_dict()
    event2 = StatusEvent.from_dict(d)
    assert event2.actor.tool == "claude"
    assert event2.actor.model == "opus"
    assert event2.actor.profile == "impl"
    assert event2.actor.role == "impl"


# ---------------------------------------------------------------------------
# parse_agent_identity
# ---------------------------------------------------------------------------


def test_parse_agent_identity_none_when_no_flags() -> None:
    assert parse_agent_identity() is None


def test_parse_agent_identity_from_compound_agent() -> None:
    ai = parse_agent_identity(agent="claude:opus:impl:impl")
    assert ai is not None
    assert ai.tool == "claude"
    assert ai.role == "impl"


def test_parse_agent_identity_from_individual_flags() -> None:
    ai = parse_agent_identity(tool="claude", model="opus")
    assert ai is not None
    assert ai.tool == "claude"
    assert ai.model == "opus"
    assert ai.profile == "unknown"


def test_parse_agent_identity_compact_four_part_string() -> None:
    """Compact --agent string is split into the four identity fields.

    Verifies the real-world pattern used in WP frontmatter and CLI invocations:
      --agent claude:opus-4-6:python-implementer:implementer
    """
    ai = parse_agent_identity(agent="claude:opus-4-6:python-implementer:implementer")
    assert ai is not None
    assert ai.tool == "claude"
    assert ai.model == "opus-4-6"
    assert ai.profile == "python-implementer"
    assert ai.role == "implementer"


def test_parse_agent_identity_mutual_exclusion_raises() -> None:
    import typer

    with pytest.raises(typer.BadParameter, match="mutually exclusive"):
        parse_agent_identity(agent="claude", tool="claude")
