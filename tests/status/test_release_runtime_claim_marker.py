"""Partition-authority residuals (#2960 follow-up, WP10 regression) —
``WPInnerStateDelta.release_runtime_claim`` is the explicit claim-release
signal, DISTINCT from a bare ``agent=""`` corruption no-op.

Regression context: #2960 (FR-014) taught ``WPInnerStateDelta.__post_init__``
to normalize an empty-string scalar (e.g. ``agent=""``) to ``None`` at the
write boundary, and taught the reducer's replace-slot fold to no-op on a
blank that slips through anyway — both exist so a corrupted/blanking delta
can never clobber real recorded attribution. That protection is correctly
indiscriminate: it also silently swallowed the *legitimate* claim release
that ``move-task --to planned`` emits on rollback (a rolled-back WP kept a
stale ``agent``/``shell_pid`` claim — the reduced snapshot never went
falsy). ``release_runtime_claim`` (a dedicated ``bool`` field, not a per-field
string sentinel — the claim group is mixed-type, ``shell_pid`` is
``int | None``) is the fix: an explicit, first-class part of the delta
vocabulary that the reducer honors as a real *clear* of the claim triple
(``agent``/``shell_pid``/``shell_pid_created_at``) regardless of which
transition (or none) accompanies the annotation, while a bare ``agent=""``
with the marker absent/``False`` remains the #2960 no-op.

This module proves the discriminating pair in isolation (no CLI/coordination
fixture) — see
``tests/specify_cli/cli/commands/agent/test_move_task_rollback_clears_claim.py``
for the end-to-end ``move-task`` drive of the same fix.
"""

from __future__ import annotations

import pytest

from specify_cli.status.models import InnerStateChanged, Lane, WPInnerStateDelta
from spec_kitty_events.diary import _apply_annotation_delta
from specify_cli.status.reducer import reduce

pytestmark = [pytest.mark.fast]


def _annotation(event_id: str, at: str, delta: WPInnerStateDelta) -> InnerStateChanged:
    return InnerStateChanged(
        event_id=event_id, wp_id="WP01", at=at, actor="claude", delta=delta
    )


def _ulid(suffix: str) -> str:
    return ("01M03" + suffix).ljust(26, "0")[:26]


# ---------------------------------------------------------------------------
# The discriminating pair: release marker clears; bare "" stays a no-op.
# ---------------------------------------------------------------------------


def test_release_marker_clears_agent_and_shell_pid_over_a_live_claim() -> None:
    """A ``release_runtime_claim=True`` delta clears a real, live claim."""
    state: dict[str, object] = {
        "lane": str(Lane.IN_PROGRESS),
        "agent": "claude-code",
        "shell_pid": 41417,
        "shell_pid_created_at": "2026-08-15T00:00:00+00:00",
    }

    _apply_annotation_delta(state, WPInnerStateDelta(release_runtime_claim=True))

    assert state["agent"] is None
    assert state["shell_pid"] is None
    assert state["shell_pid_created_at"] is None


def test_bare_empty_agent_delta_remains_a_noop_over_a_live_claim() -> None:
    """The discriminating control: a bare ``agent=""`` delta (marker absent)
    is STILL a no-op over a real recorded claim — the #2960 protection is
    untouched by this fix."""
    state: dict[str, object] = {"lane": str(Lane.IN_PROGRESS), "agent": "claude-code"}
    # Bypass the write-boundary normalization (mirrors the legacy-log defense
    # in test_2960_blanked_runtime_slot.py) to exercise the reducer's own
    # no-op guard directly, independent of __post_init__.
    legacy = WPInnerStateDelta.from_dict({"agent": ""})
    object.__setattr__(legacy, "agent", "")

    _apply_annotation_delta(state, legacy)

    assert state["agent"] == "claude-code"
    assert legacy.release_runtime_claim is False


def test_release_marker_via_reduce_end_to_end() -> None:
    """Same discriminating pair, driven through the public ``reduce()`` seam
    (annotation fold) rather than the private ``_apply_annotation_delta``."""
    claimed = _annotation(
        _ulid("A1"),
        "2026-08-15T00:00:01+00:00",
        WPInnerStateDelta(agent="claude-code", shell_pid=41417),
    )
    released = _annotation(
        _ulid("A2"),
        "2026-08-15T00:00:02+00:00",
        WPInnerStateDelta(release_runtime_claim=True),
    )

    wp = reduce([], [claimed, released]).work_packages["WP01"]

    assert not wp.get("agent")
    assert not wp.get("shell_pid")


def test_same_delta_concrete_override_wins_over_release() -> None:
    """A concrete value present in the SAME delta as the release marker (an
    explicit re-plant, e.g. ``move-task --to planned --agent fresh-claimer``)
    overrides the release — the reducer applies the clear BEFORE the
    replace-slot loop, so the loop's present value wins."""
    state: dict[str, object] = {"lane": str(Lane.IN_PROGRESS), "agent": "claude-code"}

    _apply_annotation_delta(
        state, WPInnerStateDelta(release_runtime_claim=True, agent="fresh-claimer")
    )

    assert state["agent"] == "fresh-claimer"


def test_release_marker_does_not_touch_assignee_or_resolved_binding() -> None:
    """The release marker clears only the claim triple — ``assignee`` and the
    resolved-binding actuals are NOT part of "the claim" and survive."""
    state: dict[str, object] = {
        "lane": str(Lane.IN_PROGRESS),
        "agent": "claude-code",
        "assignee": "alice",
        "role": "implementer",
        "model": "claude-opus",
    }

    _apply_annotation_delta(state, WPInnerStateDelta(release_runtime_claim=True))

    assert state["assignee"] == "alice"
    assert state["role"] == "implementer"
    assert state["model"] == "claude-opus"


# ---------------------------------------------------------------------------
# Delta-contract mechanics: is_empty / to_dict / from_dict round-trip.
# ---------------------------------------------------------------------------


def test_release_marker_alone_makes_delta_non_empty() -> None:
    """A delta carrying ONLY the release marker is non-empty (must actually
    be emitted, never dropped as a vacuous no-op)."""
    delta = WPInnerStateDelta(release_runtime_claim=True)
    assert delta.is_empty() is False


def test_default_delta_without_marker_is_still_empty() -> None:
    """Non-vacuity guard: the marker's default (``False``) never manufactures
    a non-empty delta on its own."""
    assert WPInnerStateDelta().is_empty() is True


def test_release_marker_round_trips_through_to_dict_from_dict() -> None:
    """The marker survives the wire encode/decode (append-only event-log
    persistence): ``to_dict`` emits it only when ``True``; ``from_dict``
    defaults a missing key to ``False``."""
    delta = WPInnerStateDelta(release_runtime_claim=True)
    wire = delta.to_dict()
    assert wire == {"release_runtime_claim": True}

    restored = WPInnerStateDelta.from_dict(wire)
    assert restored.release_runtime_claim is True

    # A legacy/unmarked wire dict decodes to the safe default.
    assert WPInnerStateDelta.from_dict({}).release_runtime_claim is False


def test_release_marker_false_is_omitted_from_wire() -> None:
    """The default ``False`` is not serialized (keeps old logs/readers that
    predate this field byte-compatible with a no-release delta)."""
    delta = WPInnerStateDelta(agent="claude")
    assert "release_runtime_claim" not in delta.to_dict()


def test_reduced_snapshot_from_persisted_release_event_clears_claim() -> None:
    """A reduced snapshot built from a persisted (wire round-tripped) release
    annotation clears the claim — proves the marker survives the full
    encode -> decode -> reduce path, not just the in-memory dataclass."""
    claimed_delta = WPInnerStateDelta.from_dict(
        WPInnerStateDelta(agent="claude-code", shell_pid=41417).to_dict()
    )
    released_delta = WPInnerStateDelta.from_dict(
        WPInnerStateDelta(release_runtime_claim=True).to_dict()
    )
    claimed = _annotation(_ulid("B1"), "2026-08-15T00:01:01+00:00", claimed_delta)
    released = _annotation(_ulid("B2"), "2026-08-15T00:01:02+00:00", released_delta)

    wp = reduce([], [claimed, released]).work_packages["WP01"]

    assert not wp.get("agent")
    assert not wp.get("shell_pid")
