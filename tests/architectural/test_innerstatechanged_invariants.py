"""Architectural invariants for the InnerStateChanged annotation (WP01 / FR-001).

Pins the "annotation is never a lane transition" contract:
- an ``InnerStateChanged`` can never mutate ``lane`` / ``force_count`` (never
  reduced as a transition);
- ``is_non_lane_event`` surfaces an annotation (never skip-and-drops it), even
  one bearing a stray ``event_type`` key;
- ``StatusEvent.from_dict`` is never invoked on an annotation dict on the store
  read path;
- the sanctioned ``annotate()`` seam neither imports nor references
  ``validate_transition`` (it adds zero FSM edges, C-004).

The final test mutation-checks the invariant so it is provably non-vacuous.
"""

from __future__ import annotations

import ast
import inspect
import json
import textwrap
from pathlib import Path

import pytest

from specify_cli.status import wp_state as wp_state_mod
from specify_cli.status.models import (
    InnerStateChanged,
    Lane,
    StatusEvent,
)
from specify_cli.status.reducer import reduce
from specify_cli.status.store import (
    is_non_lane_event,
    read_event_stream,
)

pytestmark = pytest.mark.architectural


def _ulid(suffix: str) -> str:
    return ("01KX" + suffix).ljust(26, "0")[:26]


def _transition(event_id: str, from_lane: str, to_lane: str, at: str) -> StatusEvent:
    return StatusEvent(
        event_id=event_id,
        mission_slug="001-mission",
        wp_id="WP01",
        from_lane=Lane(from_lane),
        to_lane=Lane(to_lane),
        at=at,
        actor="alice",
        force=False,
        execution_mode="worktree",
    )


def _annotation_dict(event_id: str = _ulid("A01")) -> dict:
    return {
        "event_id": event_id,
        "kind": "annotation",
        "wp_id": "WP01",
        "at": "2026-01-01T00:01:00Z",
        "actor": "alice",
        "delta": {"shell_pid": 4242},
    }


def test_annotation_never_mutates_lane_or_force_count() -> None:
    """Feeding an annotation through reduce() leaves lane + force_count of the
    transition-established state untouched — it is never a lane transition."""
    t1 = _transition(_ulid("T01"), "genesis", "planned", "2026-01-01T00:00:00Z")
    ann = InnerStateChanged.from_dict(_annotation_dict())

    baseline = reduce([t1], []).work_packages["WP01"]
    with_annotation = reduce([t1], [ann]).work_packages["WP01"]

    assert with_annotation["lane"] == baseline["lane"] == "planned"
    assert with_annotation["force_count"] == baseline["force_count"] == 0
    # The annotation only wrote its off-axis slot.
    assert with_annotation["shell_pid"] == 4242


def test_is_non_lane_event_surfaces_annotation_even_with_event_type() -> None:
    """An annotation is surfaced (not skipped) — and stays surfaced even if the
    envelope ever grows a stray ``event_type`` key."""
    assert is_non_lane_event(_annotation_dict()) is False

    with_event_type = {**_annotation_dict(), "event_type": "SomethingElse"}
    assert is_non_lane_event(with_event_type) is False

    # A genuine lane transition and a retrospective event classify as before.
    transition_dict = _transition(_ulid("T01"), "genesis", "planned", "2026-01-01T00:00:00Z").to_dict()
    assert is_non_lane_event(transition_dict) is False
    assert is_non_lane_event({"event_type": "DecisionPointOpened"}) is True
    assert is_non_lane_event({"event_name": "retrospective.requested"}) is True


def test_statusevent_from_dict_never_invoked_on_annotation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """On the store read path, an annotation dict is decoded by
    InnerStateChanged.from_dict, never routed through StatusEvent.from_dict
    (which hard-requires from_lane/to_lane and would KeyError)."""
    events_file = tmp_path / "status.events.jsonl"
    transition = _transition(_ulid("T01"), "genesis", "planned", "2026-01-01T00:00:00Z")
    events_file.write_text(
        json.dumps(transition.to_dict()) + "\n" + json.dumps(_annotation_dict()) + "\n",
        encoding="utf-8",
    )

    seen: list[dict] = []
    real_from_dict = StatusEvent.from_dict.__func__  # type: ignore[attr-defined]

    def _spy_from_dict(cls: type[StatusEvent], data: dict) -> StatusEvent:
        seen.append(data)
        if data.get("kind") == "annotation":
            raise AssertionError("StatusEvent.from_dict was called on an annotation dict")
        return real_from_dict(cls, data)

    monkeypatch.setattr(StatusEvent, "from_dict", classmethod(_spy_from_dict))

    stream = read_event_stream(tmp_path)

    # The transition is routed to transitions and the annotation to annotations —
    # partitioned by exact identity, nothing dropped/duplicated/misrouted.
    assert [t.event_id for t in stream.transitions] == [transition.event_id]
    assert [a.event_id for a in stream.annotations] == [_ulid("A01")]
    assert stream.annotations[0].delta.shell_pid == 4242
    # from_dict saw only the transition dict, never the annotation.
    assert all(d.get("kind") != "annotation" for d in seen)


def _referenced_names(source: str) -> set[str]:
    """Return every identifier referenced in *source* as code (Name ids +
    Attribute attrs), excluding docstrings/comments/string literals."""
    tree = ast.parse(textwrap.dedent(source))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
    return names


def test_annotate_seam_does_not_reference_validate_transition() -> None:
    """The sanctioned annotate() seam adds zero FSM edges: it neither imports
    nor references validate_transition in CODE (C-004). Prose mentions in the
    docstring are fine — the AST scan ignores string literals."""
    assert "validate_transition" not in _referenced_names(inspect.getsource(wp_state_mod.annotate))

    # The FSM-free discipline holds at module scope too: wp_state never imports
    # validate_transition into its namespace.
    assert not hasattr(wp_state_mod, "validate_transition")

    module_tree = ast.parse(inspect.getsource(wp_state_mod))
    imported: set[str] = set()
    for node in ast.walk(module_tree):
        if isinstance(node, (ast.ImportFrom, ast.Import)):
            imported.update(alias.asname or alias.name for alias in node.names)
    assert "validate_transition" not in imported


def test_invariant_is_non_vacuous_naive_transition_fold_would_fail() -> None:
    """Mutation check: a naive reducer that folded an annotation dict as a lane
    transition would KeyError on the missing from_lane/to_lane — proving the
    invariant (annotations are never lane transitions) is real, not vacuous."""
    annotation_dict = _annotation_dict()

    with pytest.raises(KeyError):
        # This is exactly the failure the distinct annotation decode path avoids.
        StatusEvent.from_dict(annotation_dict)

    # And the sanctioned path decodes it cleanly instead.
    decoded = InnerStateChanged.from_dict(annotation_dict)
    assert isinstance(decoded, InnerStateChanged)
    assert decoded.delta.shell_pid == 4242
