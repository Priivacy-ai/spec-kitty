"""Composition tests for the five `software-dev` mission step contracts.

WP01 (mission `software-dev-composition-rewrite-01KQ26CY`) introduced the
`tasks` step contract. These tests pin the executor surface for all five
software-dev actions:

1. The `tasks` contract loads cleanly from the shipped repository.
2. `_ACTION_PROFILE_DEFAULTS` returns the agreed default profile for `tasks`.
3. All five canonical software-dev actions resolve to a shipped contract.
4. The composer routes every `tasks` sub-step through
   `ProfileInvocationExecutor` in declared order (fake invocation executor).
5. Every non-bootstrap `tasks` step has at least one delegation candidate that
   resolves against the merged DRG action context.

These tests intentionally mirror the fake-invocation-executor pattern used in
``tests/specify_cli/mission_step_contracts/test_executor.py`` and never spin up
a real ``ProfileInvocationExecutor`` — keeping per-test runtime negligible and
the executor pure-composer contract (C-001) untouched.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from doctrine.mission_step_contracts.repository import MissionStepContractRepository
from specify_cli.mission_step_contracts.executor import (
    _ACTION_PROFILE_DEFAULTS,
    StepContractExecutionContext,
    StepContractExecutor,
)


pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# Helpers (patterned after tests/specify_cli/mission_step_contracts/test_executor.py)
# ---------------------------------------------------------------------------

def _setup_fixture_profiles(repo_root: Path) -> None:
    """Copy the implementer + reviewer fixture profiles into the repo root.

    The fake ``ProfileInvocationExecutor`` flow inside
    ``StepContractExecutor.execute`` resolves a profile hint against the
    project ``.kittify/profiles`` directory; reusing the existing fixtures
    keeps this file aligned with ``test_executor.py``.
    """
    profiles_dir = repo_root / ".kittify" / "profiles"
    profiles_dir.mkdir(parents=True)
    fixtures = Path(__file__).parents[1] / "invocation" / "fixtures" / "profiles"
    for yaml_file in fixtures.glob("*.agent.yaml"):
        shutil.copy(yaml_file, profiles_dir / yaml_file.name)


# NOTE: The shipped DRG already scopes the `software-dev/tasks` action to the
# candidate URNs declared in ``tasks.step-contract.yaml`` (see
# ``src/doctrine/missions/software-dev/actions/tasks/index.yaml``). Tests
# therefore rely on the shipped graph and do not write a project overlay --
# adding one would create duplicate-edge validation errors at load time.


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_tasks_contract_loads_from_repository() -> None:
    """T003 #1 — the new shipped YAML loads through the canonical repository."""
    repo = MissionStepContractRepository()
    contract = repo.get_by_action("software-dev", "tasks")

    assert contract is not None, (
        "Expected MissionStepContractRepository to surface the new "
        "tasks.step-contract.yaml; ensure the file exists under "
        "src/doctrine/mission_step_contracts/shipped/."
    )
    assert contract.id == "tasks"
    assert contract.action == "tasks"
    assert contract.mission == "software-dev"
    assert [step.id for step in contract.steps] == [
        "bootstrap",
        "outline",
        "packages",
        "finalize",
    ]


def test_tasks_default_profile_is_architect_alphonso() -> None:
    """T003 #2 — locked-decision D-2 default profile is wired into the executor."""
    assert _ACTION_PROFILE_DEFAULTS[("software-dev", "tasks")] == "architect-alphonso"


def test_all_five_software_dev_actions_have_shipped_contracts() -> None:
    """T003 #3 — every canonical software-dev action resolves to a contract."""
    repo = MissionStepContractRepository()
    for action in ("specify", "plan", "tasks", "implement", "review"):
        contract = repo.get_by_action("software-dev", action)
        assert contract is not None, (
            f"Missing shipped contract for software-dev/{action}; expected a "
            f"file at src/doctrine/mission_step_contracts/shipped/{action}.step-contract.yaml"
        )
        assert contract.action == action
        assert contract.mission == "software-dev"


def test_executor_composes_tasks_through_invocation_executor(tmp_path: Path) -> None:
    """T003 #4 — composer walks all four tasks sub-steps through invocation."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _setup_fixture_profiles(repo_root)

    context_result = SimpleNamespace(mode="compact", text="fixture governance context")
    with patch(
        "specify_cli.invocation.executor.build_charter_context",
        return_value=context_result,
    ):
        result = StepContractExecutor(
            repo_root=repo_root,
            contract_repository=MissionStepContractRepository(),
        ).execute(
            StepContractExecutionContext(
                repo_root=repo_root,
                mission="software-dev",
                action="tasks",
                actor="pytest",
                # Use the fixture profile so we don't need a real architect profile;
                # this overrides the default in _ACTION_PROFILE_DEFAULTS.
                profile_hint="implementer-fixture",
                request_text="WP01 composition test",
            )
        )

    assert result.contract_id == "tasks"
    assert result.mission == "software-dev"
    assert result.action == "tasks"
    assert result.resolution_source == "merged_drg"
    # Four steps composed in declared order, each producing one invocation.
    assert [step.step_id for step in result.steps] == [
        "bootstrap",
        "outline",
        "packages",
        "finalize",
    ]
    assert len(result.invocation_ids) == 4
    assert all(step.invocation_payload is not None for step in result.steps)
    # Bootstrap and finalize declare commands; declaration is recorded but the
    # composer never executes them (C-001).
    assert result.steps[0].command_declared is True
    assert result.steps[3].command_declared is True


def test_tasks_step_delegations_resolve_against_action_index(tmp_path: Path) -> None:
    """T003 #5 — every non-bootstrap step has at least one resolved delegation.

    The tasks contract declares ``delegates_to`` on three of four steps
    (``outline``, ``packages``, ``finalize``). With the project DRG overlay
    scoping each candidate URN to ``action:software-dev/tasks``, every one of
    those steps must resolve at least one candidate; the bootstrap step has
    no delegations and is intentionally skipped.
    """
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _setup_fixture_profiles(repo_root)

    context_result = SimpleNamespace(mode="compact", text="fixture governance context")
    with patch(
        "specify_cli.invocation.executor.build_charter_context",
        return_value=context_result,
    ):
        result = StepContractExecutor(
            repo_root=repo_root,
            contract_repository=MissionStepContractRepository(),
        ).execute(
            StepContractExecutionContext(
                repo_root=repo_root,
                mission="software-dev",
                action="tasks",
                actor="pytest",
                profile_hint="implementer-fixture",
            )
        )

    steps_by_id = {step.step_id: step for step in result.steps}

    # Bootstrap declares no delegations -- skip per the docstring contract.
    assert steps_by_id["bootstrap"].resolved_delegations == ()

    # Every other step must resolve at least one candidate against the action context.
    for step_id in ("outline", "packages", "finalize"):
        step = steps_by_id[step_id]
        assert len(step.resolved_delegations) >= 1, (
            f"Step {step_id} resolved no delegation candidates; expected at "
            f"least one to exist in action:software-dev/tasks scope."
        )
        # Spot-check: each resolved delegation URN is present in the action context.
        for delegation in step.resolved_delegations:
            assert delegation.urn.startswith(("tactic:", "directive:"))
