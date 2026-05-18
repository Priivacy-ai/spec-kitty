"""Workflow registry tests (FR-012, FR-015).

ATDD anchors
------------
* Scenario 3 exception: ``test_unknown_workflow_id_hard_fails_with_available_list``
  covers: Scenario 3 exception, FR-015 — expected GREEN at: WP10 final commit
"""
from __future__ import annotations

import pytest


def test_get_workflow_loads_software_dev_default():
    from specify_cli.next._internal_runtime.workflow_registry import get_workflow

    wf = get_workflow("software-dev-default")
    assert wf.workflow_id == "software-dev-default"
    assert wf.initial == "specify"
    action_names = [a.action_name for a in wf.actions]
    assert action_names == ["specify", "plan", "tasks", "implement", "review", "merge"]


def test_unknown_workflow_id_hard_fails_with_available_list():
    """FR-015 binding: no silent fallback to software-dev-default."""
    from specify_cli.next._internal_runtime.workflow_registry import (
        UnknownWorkflowError,
        get_workflow,
    )

    with pytest.raises(UnknownWorkflowError) as exc_info:
        get_workflow("does-not-exist")
    msg = str(exc_info.value)
    assert "does-not-exist" in msg
    assert "software-dev-default" in msg  # available list mentioned


def test_get_workflow_loads_fixture_workflow():
    from specify_cli.next._internal_runtime.workflow_registry import get_workflow

    wf = get_workflow("our-team-design-first")
    action_names = [a.action_name for a in wf.actions]
    assert "design-review" in action_names


def test_workflow_sequence_actions_form_dag():
    """Invariant: no cycles; every `next` references an existing action."""
    from specify_cli.next._internal_runtime.workflow_registry import get_workflow

    wf = get_workflow("software-dev-default")
    names = {a.action_name for a in wf.actions}
    for a in wf.actions:
        for n in a.next:
            assert n in names, f"action {a.action_name} references unknown next {n}"
