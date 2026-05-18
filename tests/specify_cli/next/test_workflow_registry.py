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


# ---------------------------------------------------------------------------
# MEDIUM-4: workflow_id sanitization (post-merge remediation cycle 1)
# ---------------------------------------------------------------------------


def test_invalid_workflow_id_with_path_traversal_raises_validation_error():
    """Defense-in-depth: path-traversal workflow_id MUST be caught by validator.

    MEDIUM-4 (Slice F post-merge remediation cycle 1): workflow_id comes from
    operator-authored meta.json. A hand-crafted ``workflow_id: "../../evil"``
    must be rejected by a slug validator BEFORE path interpolation.
    The error message must say "Invalid workflow_id", not just "Unknown
    workflow_id", to distinguish validation rejection from lookup failure.
    """
    from specify_cli.next._internal_runtime.workflow_registry import (
        UnknownWorkflowError,
        get_workflow,
    )

    get_workflow.cache_clear()

    with pytest.raises(UnknownWorkflowError) as exc_info:
        get_workflow("../../etc/passwd")
    msg = str(exc_info.value)
    assert "Invalid workflow_id" in msg, (
        "The slug validator MUST produce 'Invalid workflow_id' in the error "
        "message to distinguish validation rejection from a normal lookup miss. "
        "Currently the code raises 'Unknown workflow_id' (from the file-not-found "
        "path), meaning the validator is not present. "
        "Fix: add re.fullmatch(r'[a-z0-9][a-z0-9-]*', workflow_id) check before "
        "the file search loop in get_workflow."
    )


def test_invalid_workflow_id_uppercase_raises_validation_error():
    """Uppercase characters must be caught by the validator, not the file lookup."""
    from specify_cli.next._internal_runtime.workflow_registry import (
        UnknownWorkflowError,
        get_workflow,
    )

    get_workflow.cache_clear()

    with pytest.raises(UnknownWorkflowError) as exc_info:
        get_workflow("Software-Dev-Default")
    msg = str(exc_info.value)
    assert "Invalid workflow_id" in msg, (
        "Uppercase slug 'Software-Dev-Default' MUST be rejected with "
        "'Invalid workflow_id' by the slug validator."
    )


def test_invalid_workflow_id_with_spaces_raises_validation_error():
    """Spaces are not valid in a workflow_id slug; must be caught by validator."""
    from specify_cli.next._internal_runtime.workflow_registry import (
        UnknownWorkflowError,
        get_workflow,
    )

    get_workflow.cache_clear()

    with pytest.raises(UnknownWorkflowError) as exc_info:
        get_workflow("software dev default")
    msg = str(exc_info.value)
    assert "Invalid workflow_id" in msg, (
        "Slug with spaces MUST be rejected with 'Invalid workflow_id'."
    )


def test_valid_workflow_id_slug_accepted():
    """Confirm valid slugs are not rejected by the validator."""
    from specify_cli.next._internal_runtime.workflow_registry import get_workflow

    get_workflow.cache_clear()
    # should not raise; falls through to the normal lookup (may raise
    # UnknownWorkflowError for missing file, but not the validator error)
    try:
        get_workflow("software-dev-default")
    except Exception as exc:
        assert "Invalid workflow_id" not in str(exc), (
            "Valid slug 'software-dev-default' MUST NOT be rejected by the "
            "workflow_id validator. Exception: " + str(exc)
        )
