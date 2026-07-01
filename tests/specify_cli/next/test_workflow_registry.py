"""Workflow registry tests (FR-012, FR-015).

ATDD anchors
------------
* Scenario 3 exception: ``test_unknown_workflow_id_hard_fails_with_available_list``
  covers: Scenario 3 exception, FR-015 — expected GREEN at: WP10 final commit
"""
from __future__ import annotations

from pathlib import Path

import pytest


pytestmark = [pytest.mark.unit, pytest.mark.fast]

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


def test_get_workflow_loads_project_override_yaml(tmp_path: Path):
    from specify_cli.next._internal_runtime.workflow_registry import get_workflow

    workflow_dir = tmp_path / ".kittify" / "overrides" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "github-pr.yaml").write_text(
        """
workflow_id: github-pr
description: Project-authored GitHub PR workflow.
version: 1
initial: specify
integrations:
  vcs:
    provider: github_pr
    target_branch: main
actions:
  - action_name: specify
    description: Create a mission specification
    next: [submit]
  - action_name: submit
    description: Open a pull request
    integration: vcs.open_pr
    next: [accept]
  - action_name: accept
    description: Accept the merged mission
    terminal: true
""".lstrip(),
        encoding="utf-8",
    )

    get_workflow.cache_clear()
    wf = get_workflow("github-pr", project_root=tmp_path)

    assert wf.workflow_id == "github-pr"
    assert wf.integrations["vcs"]["provider"] == "github_pr"
    assert [a.action_name for a in wf.actions] == ["specify", "submit", "accept"]
    assert wf.actions[1].integration == "vcs.open_pr"


def test_project_override_precedes_builtin_workflow(tmp_path: Path):
    from specify_cli.next._internal_runtime.workflow_registry import get_workflow

    workflow_dir = tmp_path / ".kittify" / "overrides" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "software-dev-default.workflow.yaml").write_text(
        """
workflow_id: software-dev-default
description: Project-specific default override.
version: 1
initial: specify
actions:
  - action_name: specify
    description: Create a mission specification
    next: [accept]
  - action_name: accept
    description: Accept directly
    terminal: true
""".lstrip(),
        encoding="utf-8",
    )

    get_workflow.cache_clear()
    wf = get_workflow("software-dev-default", project_root=tmp_path)

    assert [a.action_name for a in wf.actions] == ["specify", "accept"]


def test_workflow_file_id_must_match_requested_slug(tmp_path: Path):
    from specify_cli.next._internal_runtime.workflow_registry import (
        UnknownWorkflowError,
        get_workflow,
    )

    workflow_dir = tmp_path / ".kittify" / "overrides" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "github-pr.yaml").write_text(
        """
workflow_id: different-id
description: Mismatched workflow identity.
version: 1
initial: specify
actions:
  - action_name: specify
    description: Create a mission specification
    terminal: true
""".lstrip(),
        encoding="utf-8",
    )

    get_workflow.cache_clear()
    with pytest.raises(UnknownWorkflowError, match="declares workflow_id"):
        get_workflow("github-pr", project_root=tmp_path)


def test_project_workflow_reload_reflects_file_changes(tmp_path: Path):
    from specify_cli.next._internal_runtime.workflow_registry import get_workflow

    workflow_dir = tmp_path / ".kittify" / "overrides" / "workflows"
    workflow_dir.mkdir(parents=True)
    workflow_path = workflow_dir / "solo-fast.yaml"
    workflow_path.write_text(
        """
workflow_id: solo-fast
description: Mutable project workflow.
version: 1
initial: plan
actions:
  - action_name: plan
    description: Plan next
    next: [implement]
  - action_name: implement
    description: Implement
    terminal: true
""".lstrip(),
        encoding="utf-8",
    )

    first = get_workflow("solo-fast", project_root=tmp_path)
    workflow_path.write_text(
        """
workflow_id: solo-fast
description: Mutable project workflow.
version: 1
initial: plan
actions:
  - action_name: plan
    description: Plan next
    next: [accept]
  - action_name: accept
    description: Accept
    terminal: true
""".lstrip(),
        encoding="utf-8",
    )
    second = get_workflow("solo-fast", project_root=tmp_path)

    assert first.actions[0].next == ["implement"]
    assert second.actions[0].next == ["accept"]


def test_list_available_workflows_omits_invalid_project_files(tmp_path: Path):
    from specify_cli.next._internal_runtime.workflow_registry import list_available_workflows

    workflow_dir = tmp_path / ".kittify" / "overrides" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "bad name.yaml").write_text(
        """
workflow_id: bad name
description: Invalid slug.
version: 1
initial: specify
actions:
  - action_name: specify
    description: Create a mission specification
    terminal: true
""".lstrip(),
        encoding="utf-8",
    )
    (workflow_dir / "mismatch.yaml").write_text(
        """
workflow_id: different
description: Mismatched file slug.
version: 1
initial: specify
actions:
  - action_name: specify
    description: Create a mission specification
    terminal: true
""".lstrip(),
        encoding="utf-8",
    )
    (workflow_dir / "valid.yaml").write_text(
        """
workflow_id: valid
description: Valid project workflow.
version: 1
initial: specify
actions:
  - action_name: specify
    description: Create a mission specification
    terminal: true
""".lstrip(),
        encoding="utf-8",
    )

    available = list_available_workflows(project_root=tmp_path)

    assert "valid" in available
    assert "bad name" not in available
    assert "mismatch" not in available


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


def test_workflow_sequence_rejects_unreachable_cycle():
    """A hidden island cycle must not validate just because initial cannot reach it."""
    import pydantic

    from specify_cli.next._internal_runtime.workflow_schema import WorkflowSequence

    with pytest.raises(pydantic.ValidationError, match="unreachable|cycle"):
        WorkflowSequence.model_validate(
            {
                "workflow_id": "test",
                "description": "x",
                "version": 1,
                "initial": "start",
                "actions": [
                    {
                        "action_name": "start",
                        "description": "x",
                        "terminal": True,
                    },
                    {"action_name": "a", "description": "x", "next": ["b"]},
                    {"action_name": "b", "description": "x", "next": ["a"]},
                ],
            }
        )


def test_workflow_sequence_rejects_unreachable_action():
    """Orphan actions are almost certainly authoring mistakes."""
    import pydantic

    from specify_cli.next._internal_runtime.workflow_schema import WorkflowSequence

    with pytest.raises(pydantic.ValidationError, match="unreachable"):
        WorkflowSequence.model_validate(
            {
                "workflow_id": "test",
                "description": "x",
                "version": 1,
                "initial": "start",
                "actions": [
                    {
                        "action_name": "start",
                        "description": "x",
                        "terminal": True,
                    },
                    {
                        "action_name": "orphan",
                        "description": "x",
                        "terminal": True,
                    },
                ],
            }
        )


def test_workflow_sequence_rejects_branching_next_actions():
    """Issue #682 v1 workflows stay linear: one current action has one successor."""
    import pydantic

    from specify_cli.next._internal_runtime.workflow_schema import WorkflowSequence

    with pytest.raises(pydantic.ValidationError, match="linear"):
        WorkflowSequence.model_validate(
            {
                "workflow_id": "test",
                "description": "x",
                "version": 1,
                "initial": "start",
                "actions": [
                    {
                        "action_name": "start",
                        "description": "x",
                        "next": ["a", "b"],
                    },
                    {
                        "action_name": "a",
                        "description": "x",
                        "terminal": True,
                    },
                    {
                        "action_name": "b",
                        "description": "x",
                        "terminal": True,
                    },
                ],
            }
        )
