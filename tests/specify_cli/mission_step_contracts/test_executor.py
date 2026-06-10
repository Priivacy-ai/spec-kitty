"""Tests for StepContractExecutor composition over ProfileInvocationExecutor."""

from __future__ import annotations

import importlib
import shutil
from collections.abc import Mapping
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from ruamel.yaml import YAML

from charter._drg_helpers import load_validated_graph
from charter.drg import resolve_context
from doctrine.missions.step_contracts import MissionStepContractRepository
from specify_cli.invocation.writer import EVENTS_DIR
from specify_cli.mission_step_contracts.executor import (
    StepContractExecutionContext,
    StepContractExecutionError,
    StepContractExecutor,
)


pytestmark = pytest.mark.fast


def test_charter_mission_steps_facade_reexports_step_inputs() -> None:
    """The runtime-facing facade exposes the doctrine input model by identity."""
    from doctrine.missions.step_contracts import MissionStepInput

    facade = importlib.reload(importlib.import_module("charter.mission_steps"))

    assert facade.MissionStepInput is MissionStepInput


def _write_yaml(path: Path, data: Mapping[str, object]) -> None:
    yaml = YAML()
    yaml.default_flow_style = False
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        yaml.dump(data, fh)


def _setup_fixture_profiles(repo_root: Path) -> None:
    profiles_dir = repo_root / ".kittify" / "profiles"
    profiles_dir.mkdir(parents=True)
    fixtures = Path(__file__).parents[1] / "invocation" / "fixtures" / "profiles"
    for yaml_file in fixtures.glob("*.agent.yaml"):
        shutil.copy(yaml_file, profiles_dir / yaml_file.name)


def _write_project_graph(repo_root: Path) -> None:
    _write_yaml(
        repo_root / ".kittify" / "doctrine" / "graph.yaml",
        {
            "schema_version": "1.0",
            "generated_at": "2026-04-24T00:00:00Z",
            "generated_by": "test",
            "nodes": [
                {
                    "urn": "action:fixture/composer",
                    "kind": "action",
                    "label": "Fixture composer action",
                },
                {"urn": "tactic:delegated-alpha", "kind": "tactic", "label": "Alpha"},
                {"urn": "tactic:delegated-beta", "kind": "tactic", "label": "Beta"},
                {"urn": "tactic:delegated-gamma", "kind": "tactic", "label": "Gamma"},
                {"urn": "tactic:not-selected", "kind": "tactic", "label": "Not selected"},
                {
                    "urn": "action:fixture/directive-composer",
                    "kind": "action",
                    "label": "Fixture directive composer action",
                },
                {
                    "urn": "action:fixture/contract-composer",
                    "kind": "action",
                    "label": "Fixture contract composer action",
                },
                {
                    "urn": "directive:DIRECTIVE_030",
                    "kind": "directive",
                    "label": "Test and Typecheck Quality Gate",
                },
                {
                    "urn": "mission_step_contract:child-contract",
                    "kind": "mission_step_contract",
                    "label": "Child contract",
                },
            ],
            "edges": [
                {
                    "source": "action:fixture/composer",
                    "target": "tactic:delegated-alpha",
                    "relation": "scope",
                },
                {
                    "source": "action:fixture/composer",
                    "target": "tactic:delegated-beta",
                    "relation": "scope",
                },
                {
                    "source": "action:fixture/composer",
                    "target": "tactic:delegated-gamma",
                    "relation": "scope",
                },
                {
                    "source": "action:fixture/directive-composer",
                    "target": "directive:DIRECTIVE_030",
                    "relation": "scope",
                },
                {
                    "source": "action:fixture/contract-composer",
                    "target": "mission_step_contract:child-contract",
                    "relation": "scope",
                },
            ],
        },
    )


def _write_fixture_contract(built_in_dir: Path) -> None:
    _write_yaml(
        built_in_dir / "fixture.step-contract.yaml",
        {
            "schema_version": "1.0",
            "id": "fixture-composer",
            "mission": "fixture",
            "action": "composer",
            "steps": [
                {
                    "id": "alpha",
                    "description": "Run alpha delegation",
                    "delegates_to": {
                        "kind": "tactic",
                        "candidates": ["delegated-alpha", "not-selected"],
                    },
                },
                {
                    "id": "beta",
                    "description": "Run beta delegation",
                    "delegates_to": {
                        "kind": "tactic",
                        "candidates": ["delegated-beta"],
                    },
                },
                {
                    "id": "gamma",
                    "description": "Run gamma delegation",
                    "delegates_to": {
                        "kind": "tactic",
                        "candidates": ["delegated-gamma"],
                    },
                },
            ],
        },
    )


def test_three_delegated_steps_execute_end_to_end_via_profile_invocation_executor(
    tmp_path: Path,
) -> None:
    """Acceptance: three delegated steps compose through invocation and merged DRG."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _setup_fixture_profiles(repo_root)
    _write_project_graph(repo_root)

    built_in_dir = tmp_path / "contracts"
    _write_fixture_contract(built_in_dir)
    contract_repo = MissionStepContractRepository(built_in_dir=built_in_dir)

    context_result = SimpleNamespace(mode="compact", text="fixture governance context")
    with patch("specify_cli.invocation.executor.build_charter_context", return_value=context_result):
        result = StepContractExecutor(
            repo_root=repo_root,
            contract_repository=contract_repo,
        ).execute(
            StepContractExecutionContext(
                repo_root=repo_root,
                mission="fixture",
                action="composer",
                actor="pytest",
                profile_hint="implementer-fixture",
                request_text="issue #501 fixture run",
            )
        )

    assert result.contract_id == "fixture-composer"
    assert result.resolution_source == "merged_drg"
    assert len(result.steps) == 3
    assert len(result.invocation_ids) == 3

    assert [step.step_id for step in result.steps] == ["alpha", "beta", "gamma"]
    assert [step.resolved_delegations[0].urn for step in result.steps] == [
        "tactic:delegated-alpha",
        "tactic:delegated-beta",
        "tactic:delegated-gamma",
    ]
    assert result.steps[0].unresolved_candidates == ("not-selected",)
    assert all(step.invocation_payload is not None for step in result.steps)

    jsonl_files = sorted(
        path
        for path in (repo_root / EVENTS_DIR).glob("*.jsonl")
        if "index" not in path.name  # exclude the ops-index file (lives in EVENTS_DIR since #1714)
    )
    assert len(jsonl_files) == 3


def test_command_step_is_declared_not_shell_executed(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _setup_fixture_profiles(repo_root)
    _write_project_graph(repo_root)

    contract = {
        "schema_version": "1.0",
        "id": "command-contract",
        "mission": "fixture",
        "action": "composer",
        "steps": [
            {
                "id": "status_transition",
                "description": "Move status",
                "command": "spec-kitty agent tasks move-task WP1 --to for_review",
            }
        ],
    }
    built_in_dir = tmp_path / "contracts"
    _write_yaml(built_in_dir / "command.step-contract.yaml", contract)

    context_result = SimpleNamespace(mode="compact", text="fixture governance context")
    with patch("specify_cli.invocation.executor.build_charter_context", return_value=context_result):
        result = StepContractExecutor(
            repo_root=repo_root,
            contract_repository=MissionStepContractRepository(built_in_dir=built_in_dir),
        ).execute(
            StepContractExecutionContext(
                repo_root=repo_root,
                mission="fixture",
                action="composer",
                actor="pytest",
                profile_hint="implementer-fixture",
            )
        )

    step = result.steps[0]
    assert step.command_declared is True
    assert step.command == "spec-kitty agent tasks move-task WP1 --to for_review"
    assert step.resolved_delegations == ()
    assert len(result.invocation_ids) == 1


def test_command_step_inputs_are_rendered_into_runtime_request_text(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_project_graph(repo_root)

    contract = {
        "schema_version": "1.0",
        "id": "command-inputs-contract",
        "mission": "fixture",
        "action": "composer",
        "steps": [
            {
                "id": "bootstrap",
                "description": "Load context",
                "command": "spec-kitty charter context --action composer --json",
                "inputs": [
                    {
                        "flag": "--profile",
                        "source": "wp.agent_profile",
                        "optional": True,
                    },
                    {
                        "flag": "--tool",
                        "source": "env.agent_tool",
                        "optional": True,
                    },
                ],
            }
        ],
    }
    built_in_dir = tmp_path / "contracts"
    _write_yaml(built_in_dir / "command-inputs.step-contract.yaml", contract)

    class FakeInvocationExecutor:
        def __init__(self) -> None:
            self.request_texts: list[str] = []

        def invoke(self, request_text: str, **_kwargs: object) -> object:
            self.request_texts.append(request_text)
            return SimpleNamespace(invocation_id="inv-1")

        def complete_invocation(self, _invocation_id: str, *, outcome: str, closed_by: str) -> None:
            assert outcome == "done"
            assert closed_by == "agent"

    fake_invocations = FakeInvocationExecutor()
    result = StepContractExecutor(
        repo_root=repo_root,
        contract_repository=MissionStepContractRepository(built_in_dir=built_in_dir),
        invocation_executor=fake_invocations,  # type: ignore[arg-type]
    ).execute(
        StepContractExecutionContext(
            repo_root=repo_root,
            mission="fixture",
            action="composer",
            actor="pytest",
            profile_hint="implementer-fixture",
        )
    )

    assert result.steps[0].command_declared is True
    assert [input.flag for input in result.steps[0].inputs] == ["--profile", "--tool"]
    assert [input.source for input in result.steps[0].inputs] == [
        "wp.agent_profile",
        "env.agent_tool",
    ]
    assert fake_invocations.request_texts == [
        "\n".join(
            [
                "Execute mission step contract command-inputs-contract (fixture/composer).",
                "Step bootstrap: Load context",
                "Declared command: spec-kitty charter context --action composer --json [--profile {wp.agent_profile}] [--tool {env.agent_tool}]",
                "Command status: declared only; the host/operator owns execution.",
            ]
        )
    ]


def test_input_only_step_renders_required_inputs_into_runtime_request_text(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_project_graph(repo_root)

    contract = {
        "schema_version": "1.0",
        "id": "input-only-contract",
        "mission": "fixture",
        "action": "composer",
        "steps": [
            {
                "id": "collect",
                "description": "Collect required context",
                "inputs": [
                    {
                        "flag": "--profile",
                        "source": "wp.agent_profile",
                    },
                ],
            }
        ],
    }
    built_in_dir = tmp_path / "contracts"
    _write_yaml(built_in_dir / "input-only.step-contract.yaml", contract)

    class FakeInvocationExecutor:
        def __init__(self) -> None:
            self.request_texts: list[str] = []

        def invoke(self, request_text: str, **_kwargs: object) -> object:
            self.request_texts.append(request_text)
            return SimpleNamespace(invocation_id="inv-1")

        def complete_invocation(self, _invocation_id: str, *, outcome: str, closed_by: str) -> None:
            assert outcome == "done"
            assert closed_by == "agent"

    fake_invocations = FakeInvocationExecutor()
    result = StepContractExecutor(
        repo_root=repo_root,
        contract_repository=MissionStepContractRepository(built_in_dir=built_in_dir),
        invocation_executor=fake_invocations,  # type: ignore[arg-type]
    ).execute(
        StepContractExecutionContext(
            repo_root=repo_root,
            mission="fixture",
            action="composer",
            actor="pytest",
            profile_hint="implementer-fixture",
        )
    )

    assert result.steps[0].inputs[0].optional is False
    assert fake_invocations.request_texts == [
        "\n".join(
            [
                "Execute mission step contract input-only-contract (fixture/composer).",
                "Step collect: Collect required context",
                "Declared step inputs: --profile {wp.agent_profile}",
            ]
        )
    ]


def test_directive_slug_candidate_resolves_to_drg_urn(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _setup_fixture_profiles(repo_root)
    _write_project_graph(repo_root)

    contract = {
        "schema_version": "1.0",
        "id": "directive-contract",
        "mission": "fixture",
        "action": "directive-composer",
        "steps": [
            {
                "id": "quality_gate",
                "description": "Run quality gate",
                "delegates_to": {
                    "kind": "directive",
                    "candidates": ["030-test-and-typecheck-quality-gate"],
                },
            }
        ],
    }
    built_in_dir = tmp_path / "contracts"
    _write_yaml(built_in_dir / "directive.step-contract.yaml", contract)

    context_result = SimpleNamespace(mode="compact", text="fixture governance context")
    with patch("specify_cli.invocation.executor.build_charter_context", return_value=context_result):
        result = StepContractExecutor(
            repo_root=repo_root,
            contract_repository=MissionStepContractRepository(built_in_dir=built_in_dir),
        ).execute(
            StepContractExecutionContext(
                repo_root=repo_root,
                mission="fixture",
                action="directive-composer",
                actor="pytest",
                profile_hint="implementer-fixture",
            )
        )

    assert result.steps[0].resolved_delegations[0].urn == "directive:DIRECTIVE_030"
    assert result.steps[0].unresolved_candidates == ()


def test_shipped_implement_workspace_paradigms_resolve_through_built_in_drg(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    graph = load_validated_graph(repo_root)
    contract = MissionStepContractRepository().get_by_action("software-dev", "implement")
    assert contract is not None
    workspace = next(step for step in contract.steps if step.id == "workspace")

    resolved, unresolved = StepContractExecutor(
        repo_root=repo_root,
        graph=graph,
    )._resolve_step_delegations(
        graph=graph,
        action_context=resolve_context(graph, "action:software-dev/implement"),
        step=workspace,
    )

    assert unresolved == []
    assert [delegation.candidate for delegation in resolved] == [
        "execution-lanes",
        "shared-branch-ci",
        "git-flow",
        "trunk-based",
    ]
    assert [delegation.urn for delegation in resolved] == [
        "paradigm:execution-lanes",
        "paradigm:shared-branch-ci",
        "paradigm:git-flow",
        "paradigm:trunk-based",
    ]


def test_mission_step_contract_candidate_resolves_to_drg_urn(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _setup_fixture_profiles(repo_root)
    _write_project_graph(repo_root)

    contract = {
        "schema_version": "1.0",
        "id": "contract-delegation",
        "mission": "fixture",
        "action": "contract-composer",
        "steps": [
            {
                "id": "child",
                "description": "Run child contract",
                "delegates_to": {
                    "kind": "mission_step_contract",
                    "candidates": ["child-contract"],
                },
            }
        ],
    }
    built_in_dir = tmp_path / "contracts"
    _write_yaml(built_in_dir / "contract.step-contract.yaml", contract)

    context_result = SimpleNamespace(mode="compact", text="fixture governance context")
    with patch("specify_cli.invocation.executor.build_charter_context", return_value=context_result):
        result = StepContractExecutor(
            repo_root=repo_root,
            contract_repository=MissionStepContractRepository(built_in_dir=built_in_dir),
        ).execute(
            StepContractExecutionContext(
                repo_root=repo_root,
                mission="fixture",
                action="contract-composer",
                actor="pytest",
                profile_hint="implementer-fixture",
            )
        )

    assert (
        result.steps[0].resolved_delegations[0].urn
        == "mission_step_contract:child-contract"
    )
    assert result.steps[0].unresolved_candidates == ()


def test_profile_hint_required_when_no_action_default_exists(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_project_graph(repo_root)
    built_in_dir = tmp_path / "contracts"
    _write_fixture_contract(built_in_dir)

    with pytest.raises(StepContractExecutionError, match="profile_hint is required"):
        StepContractExecutor(
            repo_root=repo_root,
            contract_repository=MissionStepContractRepository(built_in_dir=built_in_dir),
        ).execute(
            StepContractExecutionContext(
                repo_root=repo_root,
                mission="fixture",
                action="composer",
            )
        )
