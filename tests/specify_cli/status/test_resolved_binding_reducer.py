"""Resolved-binding vocabulary + reducer tests (WP09 / FR-013 / INV-8).

Covers the IC-08 resolved-binding half — vocabulary + reducer only (the
dispatch->claim sourcing is WP10):

* **Latest-wins reduction** (FR-013 / INV-8): a second ``InnerStateChanged``
  annotation replaces the resolved slots with the most-recent actuals; unset
  fields persist their last non-None value. Folded over *real* events (never a
  mocked reducer).
* **Carry-forward across a lane transition** (``_RUNTIME_SLOTS``): a transition
  preserves previously-folded resolved slots — the precise pin for
  ``_RUNTIME_SLOTS`` membership (drop a slot -> this test fails).
* **Delta round-trip** (``to_dict``/``from_dict``) with the five resolved
  fields, and the absent-leaves-slot-untouched wire contract.
* **``is_empty``** correctness with the new fields (dataclass-fields-driven, so
  a future field is covered automatically).
* **Tidy-first parity** (T033 + T034 behaviour-preservation): the collapse of
  ``WPInnerStateDelta``'s triple-enumeration and the extraction of
  ``_apply_annotation_delta``'s if-chain into ``_REPLACE_SLOTS`` are observable
  no-ops for the pre-existing fields — including the ``note``->``notes`` mapping
  and ``tracker_refs_replace`` precedence.

Pure-unit proofs: no CLI, git, or SaaS surface is exercised.
"""

from __future__ import annotations

import pytest

from specify_cli.status.models import (
    InnerStateChanged,
    Lane,
    ReviewOverride,
    StatusEvent,
    WPInnerStateDelta,
)
from specify_cli.status.reducer import (
    _REPLACE_SLOTS,
    _RUNTIME_SLOTS,
    _apply_annotation_delta,
    _wp_state_from_event,
    reduce,
)
from specify_cli.status.resolved_binding import ResolvedBinding

pytestmark = [pytest.mark.unit, pytest.mark.fast]

_MISSION_SLUG = "wp09-resolved-binding"
_RESOLVED_FIELDS = (
    "role",
    "agent_profile",
    "agent_profile_version",
    "model",
    "provider",
)


def _ulid(suffix: str) -> str:
    """A syntactically valid 26-char ULID from a short suffix."""
    return ("01KX" + suffix).ljust(26, "0")[:26]


def _transition(
    event_id: str,
    from_lane: Lane,
    to_lane: Lane,
    at: str,
    wp_id: str = "WP01",
) -> StatusEvent:
    return StatusEvent(
        event_id=event_id,
        mission_slug=_MISSION_SLUG,
        wp_id=wp_id,
        from_lane=from_lane,
        to_lane=to_lane,
        at=at,
        actor="claude",
        force=False,
        execution_mode="worktree",
    )


def _annotation(
    event_id: str,
    at: str,
    delta: WPInnerStateDelta,
    wp_id: str = "WP01",
) -> InnerStateChanged:
    return InnerStateChanged(
        event_id=event_id,
        wp_id=wp_id,
        at=at,
        actor="claude",
        delta=delta,
    )


# ---------------------------------------------------------------------------
# T035/T036.1 — latest-wins reduction (the headline, FR-013 / INV-8)
# ---------------------------------------------------------------------------


def test_resolved_binding_folds_latest_wins() -> None:
    """A second resolved-binding annotation replaces set slots; unset fields
    retain their last non-None fold (latest-wins across the lifecycle)."""
    ann1 = _annotation(
        _ulid("A1"),
        "2026-07-20T00:00:01+00:00",
        WPInnerStateDelta(
            role="implementer",
            agent_profile="P1",
            agent_profile_version="v1",
            model="M1",
            provider="prov1",
        ),
    )
    # The review-claim: role + profile + model swap; version/provider unset.
    ann2 = _annotation(
        _ulid("A2"),
        "2026-07-20T00:00:02+00:00",
        WPInnerStateDelta(role="reviewer", agent_profile="P2", model="M2"),
    )

    wp = reduce([], [ann1, ann2]).work_packages["WP01"]

    # Most-recent actuals win.
    assert wp["role"] == "reviewer"
    assert wp["agent_profile"] == "P2"
    assert wp["model"] == "M2"
    # Fields the latest annotation left unset persist their prior fold.
    assert wp["agent_profile_version"] == "v1"
    assert wp["provider"] == "prov1"


def test_explicit_absence_clears_prior_profile_version_and_provider() -> None:
    """A later bare pickup must not retain the previous actor's binding slots."""
    prior = _annotation(
        _ulid("AA1"),
        "2026-07-20T00:00:01+00:00",
        ResolvedBinding(
            agent_profile="python-pedro",
            agent_profile_version="1",
            model="claude-opus-4-6",
            provider="anthropic",
        ).to_delta(role="implementer"),
    )
    bare_review = _annotation(
        _ulid("AA2"),
        "2026-07-20T00:00:02+00:00",
        ResolvedBinding().to_delta(role="reviewer"),
    )

    wp = reduce([], [prior, bare_review]).work_packages["WP01"]

    assert wp["role"] == "reviewer"
    assert wp["agent_profile"] != "python-pedro"
    assert wp["agent_profile_version"] != "1"
    assert wp["provider"] != "anthropic"


def test_resolved_binding_first_annotation_would_lose_if_first_wins() -> None:
    """Non-vacuity guard: order matters. Reversing the fold order (older last)
    would flip ``model`` to M1 — this asserts the timestamp-sorted latest wins."""
    ann_old = _annotation(
        _ulid("B1"),
        "2026-07-20T00:00:01+00:00",
        WPInnerStateDelta(model="M1"),
    )
    ann_new = _annotation(
        _ulid("B2"),
        "2026-07-20T00:00:09+00:00",
        WPInnerStateDelta(model="M2"),
    )

    # Feed out of timestamp order — the reducer sorts by (at, event_id).
    wp = reduce([], [ann_new, ann_old]).work_packages["WP01"]
    assert wp["model"] == "M2"


def test_only_model_swap_leaves_other_resolved_slots_intact() -> None:
    """A mid-cycle model swap (only ``model`` set) replaces just that slot."""
    ann_full = _annotation(
        _ulid("C1"),
        "2026-07-20T00:00:01+00:00",
        WPInnerStateDelta(role="implementer", agent_profile="P1", model="M1"),
    )
    ann_model = _annotation(
        _ulid("C2"),
        "2026-07-20T00:00:02+00:00",
        WPInnerStateDelta(model="M2"),
    )

    wp = reduce([], [ann_full, ann_model]).work_packages["WP01"]
    assert wp["model"] == "M2"
    assert wp["role"] == "implementer"
    assert wp["agent_profile"] == "P1"


def test_resolved_binding_absent_on_never_reclaimed_wp() -> None:
    """A WP that received no resolved-binding annotation has no resolved slots
    (absence is valid — the fields stay absent, never masqueraded)."""
    t1 = _transition(_ulid("T1"), Lane.GENESIS, Lane.PLANNED, "2026-07-20T00:00:00+00:00")
    wp = reduce([t1], []).work_packages["WP01"]
    for field_name in _RESOLVED_FIELDS:
        assert field_name not in wp


# ---------------------------------------------------------------------------
# T035/T036.1 — carry-forward across a lane transition (_RUNTIME_SLOTS pin)
# ---------------------------------------------------------------------------


def test_resolved_slots_carry_forward_across_transition() -> None:
    """``_wp_state_from_event`` preserves already-folded resolved slots across a
    lane transition (per-field independence). This is the precise pin for
    ``_RUNTIME_SLOTS`` membership: dropping a resolved slot fails here."""
    previous = {
        "lane": str(Lane.CLAIMED),
        "actor": "claude",
        "last_transition_at": "2026-07-20T00:00:01+00:00",
        "last_event_id": _ulid("P0"),
        "force_count": 0,
        "role": "implementer",
        "agent_profile": "P1",
        "agent_profile_version": "v1",
        "model": "M1",
        "provider": "prov1",
    }
    transition = _transition(
        _ulid("T2"), Lane.CLAIMED, Lane.IN_PROGRESS, "2026-07-20T00:00:02+00:00"
    )

    new_state = _wp_state_from_event(transition, previous)

    assert new_state["lane"] == str(Lane.IN_PROGRESS)
    for field_name in _RESOLVED_FIELDS:
        assert new_state[field_name] == previous[field_name]


def test_resolved_binding_present_after_transition_in_full_reduce() -> None:
    """End-to-end: an annotation's resolved binding is present in the final
    snapshot even alongside lane transitions."""
    t1 = _transition(_ulid("D1"), Lane.GENESIS, Lane.PLANNED, "2026-07-20T00:00:00+00:00")
    t2 = _transition(_ulid("D2"), Lane.PLANNED, Lane.CLAIMED, "2026-07-20T00:00:02+00:00")
    ann = _annotation(
        _ulid("D3"),
        "2026-07-20T00:00:03+00:00",
        WPInnerStateDelta(role="implementer", agent_profile="P1", model="M1"),
    )

    wp = reduce([t1, t2], [ann]).work_packages["WP01"]
    assert wp["lane"] == str(Lane.CLAIMED)
    assert wp["role"] == "implementer"
    assert wp["agent_profile"] == "P1"
    assert wp["model"] == "M1"


def test_runtime_and_replace_tables_carry_all_resolved_slots() -> None:
    """Structural pin: every resolved field is a carry-forward slot AND a
    data-driven replace slot (so no per-field ``if`` branch was added)."""
    for field_name in _RESOLVED_FIELDS:
        assert field_name in _RUNTIME_SLOTS
        assert field_name in _REPLACE_SLOTS


# ---------------------------------------------------------------------------
# T036.2 — delta round-trip (to_dict / from_dict)
# ---------------------------------------------------------------------------


def test_resolved_fields_round_trip() -> None:
    """A delta populated with the five resolved fields (plus a mix of existing
    scalar fields) satisfies ``from_dict(to_dict(x)) == x``."""
    delta = WPInnerStateDelta(
        shell_pid=4242,
        agent="claude",
        assignee="alice",
        role="reviewer",
        agent_profile="P2",
        agent_profile_version="v3",
        model="M2",
        provider="anthropic",
    )
    assert WPInnerStateDelta.from_dict(delta.to_dict()) == delta


def test_resolved_fields_absent_omitted_from_wire() -> None:
    """Absent resolved fields are omitted from ``to_dict`` (absent-leaves-slot-
    untouched wire contract) — only ``model`` is present here."""
    delta = WPInnerStateDelta(model="M9")
    wire = delta.to_dict()
    assert wire == {"model": "M9"}
    for field_name in ("role", "agent_profile", "agent_profile_version", "provider"):
        assert field_name not in wire


# ---------------------------------------------------------------------------
# T036.3 — is_empty correctness with the new fields
# ---------------------------------------------------------------------------


def test_is_empty_all_none() -> None:
    assert WPInnerStateDelta().is_empty() is True


@pytest.mark.parametrize("field_name", _RESOLVED_FIELDS)
def test_is_empty_false_for_single_resolved_field(field_name: str) -> None:
    """A delta carrying only one resolved field is not empty (dataclass-fields-
    driven ``is_empty`` covers each new field automatically)."""
    delta = WPInnerStateDelta(**{field_name: "x"})
    assert delta.is_empty() is False


# ---------------------------------------------------------------------------
# T036.4 — tidy-first parity (behaviour-preservation of T033 + T034)
# ---------------------------------------------------------------------------


def test_parity_is_empty_existing_fields() -> None:
    """T033 collapse is a no-op for the pre-existing fields' ``is_empty``."""
    assert WPInnerStateDelta().is_empty() is True
    assert WPInnerStateDelta(shell_pid=1).is_empty() is False
    assert WPInnerStateDelta(note="x").is_empty() is False
    assert WPInnerStateDelta(agent="claude").is_empty() is False
    assert WPInnerStateDelta(tracker_refs=["#1"]).is_empty() is False


def test_parity_roundtrip_existing_fields() -> None:
    """T033 collapse preserves the round-trip of every pre-existing field,
    including the special decoders (``subtasks``/``review``/``tracker_refs*``)."""
    delta = WPInnerStateDelta(
        shell_pid=9001,
        shell_pid_created_at="1784571018.28",
        subtasks={"T001": Lane.DONE, "T002": Lane.PLANNED},
        note="a note",
        tracker_refs=["#1", "#2"],
        tracker_refs_replace=["#9"],
        agent="claude",
        assignee="alice",
        review=ReviewOverride(
            at="2026-07-20T00:00:00+00:00", actor="bob", wp_id="WP01", reason="rework"
        ),
    )
    assert WPInnerStateDelta.from_dict(delta.to_dict()) == delta


def test_parity_apply_annotation_delta_all_existing_slots() -> None:
    """T034 extraction is behaviour-preserving: folding a delta that touches
    every pre-existing slot yields the known-good pre-refactor shape — pinning
    the ``note``->``notes`` mapping and ``tracker_refs_replace`` precedence."""
    state: dict[str, object] = {
        "lane": str(Lane.IN_PROGRESS),
        "actor": "claude",
        "notes": ["old"],
        "tracker_refs": ["#1"],
        "subtasks": {"T001": "planned"},
    }
    delta = WPInnerStateDelta(
        shell_pid=999,
        shell_pid_created_at="123.45",
        subtasks={"T002": Lane.DONE},
        note="new note",
        tracker_refs=["#2", "#3"],
        tracker_refs_replace=["#9", "#9", "#8"],
        agent="claude",
        assignee="alice",
        review=ReviewOverride(
            at="2026-07-20T00:00:00+00:00", actor="bob", wp_id="WP01", reason="rework"
        ),
    )

    _apply_annotation_delta(state, delta)

    assert state == {
        "lane": str(Lane.IN_PROGRESS),
        "actor": "claude",
        "shell_pid": 999,
        "shell_pid_created_at": "123.45",
        # per-subtask merge (existing T001 retained, T002 added)
        "subtasks": {"T001": "planned", "T002": "done"},
        # note appended to the notes list (name mismatch: note -> notes)
        "notes": ["old", "new note"],
        # replace channel wins over both the existing slot and the additive
        # channel, dedup-preserving order (never resurrects #1/#2/#3)
        "tracker_refs": ["#9", "#8"],
        "agent": "claude",
        "assignee": "alice",
        "review": {
            "at": "2026-07-20T00:00:00+00:00",
            "actor": "bob",
            "wp_id": "WP01",
            "reason": "rework",
        },
    }
