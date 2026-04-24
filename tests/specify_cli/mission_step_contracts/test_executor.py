"""Tests for StepContractExecutor composition over ProfileInvocationExecutor."""

from __future__ import annotations

import shutil
from collections.abc import Mapping
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from ruamel.yaml import YAML

from doctrine.mission_step_contracts.repository import MissionStepContractRepository
from specify_cli.invocation.writer import EVENTS_DIR
from specify_cli.mission_step_contracts.executor import (
    StepContractExecutionContext,
    StepContractExecutionError,
    StepContractExecutor,
)


pytestmark = pytest.mark.fast


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
                    "urn": "directive:DIRECTIVE_030",
                    "kind": "directive",
                    "label": "Test and Typecheck Quality Gate",
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
            ],
        },
    )


def _write_fixture_contract(shipped_dir: Path) -> None:
    _write_yaml(
        shipped_dir / "fixture.step-contract.yaml",
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

    shipped_dir = tmp_path / "contracts"
    _write_fixture_contract(shipped_dir)
    contract_repo = MissionStepContractRepository(shipped_dir=shipped_dir)

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

    jsonl_files = sorted((repo_root / EVENTS_DIR).glob("*.jsonl"))
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
    shipped_dir = tmp_path / "contracts"
    _write_yaml(shipped_dir / "command.step-contract.yaml", contract)

    context_result = SimpleNamespace(mode="compact", text="fixture governance context")
    with patch("specify_cli.invocation.executor.build_charter_context", return_value=context_result):
        result = StepContractExecutor(
            repo_root=repo_root,
            contract_repository=MissionStepContractRepository(shipped_dir=shipped_dir),
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
    shipped_dir = tmp_path / "contracts"
    _write_yaml(shipped_dir / "directive.step-contract.yaml", contract)

    context_result = SimpleNamespace(mode="compact", text="fixture governance context")
    with patch("specify_cli.invocation.executor.build_charter_context", return_value=context_result):
        result = StepContractExecutor(
            repo_root=repo_root,
            contract_repository=MissionStepContractRepository(shipped_dir=shipped_dir),
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


def test_profile_hint_required_when_no_action_default_exists(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_project_graph(repo_root)
    shipped_dir = tmp_path / "contracts"
    _write_fixture_contract(shipped_dir)

    with pytest.raises(StepContractExecutionError, match="profile_hint is required"):
        StepContractExecutor(
            repo_root=repo_root,
            contract_repository=MissionStepContractRepository(shipped_dir=shipped_dir),
        ).execute(
            StepContractExecutionContext(
                repo_root=repo_root,
                mission="fixture",
                action="composer",
            )
        )
