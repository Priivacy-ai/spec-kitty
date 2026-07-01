"""C-008: software-dev-default workflow is byte-stable to hardcoded sequence.

ATDD anchor
-----------
* ``test_default_workflow_produces_byte_stable_pairs``
  covers: FR-014, C-008 — expected GREEN at: WP11 final commit
"""
from __future__ import annotations


import pytest

pytestmark = [pytest.mark.unit, pytest.mark.fast]

# The pre-Slice-F hardcoded sequence the new YAML must match:
_HARDCODED_SEQUENCE: list[tuple[str, str | None]] = [
    ("specify", "plan"),
    ("plan", "tasks"),
    ("tasks", "implement"),
    ("implement", "review"),
    ("review", "merge"),
    ("merge", None),
]


def test_default_workflow_produces_byte_stable_pairs() -> None:
    """For every (current, next) pair the hardcoded sequence produced,
    the loaded software-dev-default workflow MUST produce the same pair."""
    from specify_cli.next._internal_runtime.workflow_registry import get_workflow

    wf = get_workflow("software-dev-default")
    by_name = {a.action_name: a for a in wf.actions}
    for current, expected_next in _HARDCODED_SEQUENCE:
        action = by_name[current]
        actual_next = action.next[0] if action.next else None
        assert actual_next == expected_next, (
            f"byte-stability violation: from {current!r} expected next={expected_next!r}, "
            f"got {actual_next!r}"
        )
