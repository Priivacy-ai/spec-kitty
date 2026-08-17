"""Tests for StepContractExecutor composition over ProfileInvocationExecutor."""

from __future__ import annotations

import importlib
import logging
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


# ---------------------------------------------------------------------------
# T008/SC-003 — shared synthetic org-pack fixture (FR-001, FR-002, FR-005)
#
# Reused verbatim by this module's own T008/T009 tests below,
# ``tests/review/test_gate_bindings.py`` (T010, FR-005), and (per SC-003)
# WP03's FR-006/FR-006a tests in ``tests/runtime/`` and
# ``tests/unit/mission_loader/`` — imported directly from this module
# (established cross-test-module precedent in this repo, e.g.
# ``tests/specify_cli/acceptance/test_trio_read_seam_migration.py`` importing
# fixtures from ``tests.specify_cli._read_seam_migration_fixtures``) rather
# than re-authored per test file, so the five lockstep-adjacent consumers
# cannot silently drift onto independently-authored fixtures.
# ---------------------------------------------------------------------------

ORG_FIXTURE_MISSION = "org-fixture-mission"
ORG_FIXTURE_ACTION = "review"
ORG_FIXTURE_CONTRACT_ID = "org-fixture-review"
ORG_FIXTURE_DIRECTIVE_STEM = "org-tier-fixture-directive"
ORG_FIXTURE_DIRECTIVE_URN = f"directive:{ORG_FIXTURE_DIRECTIVE_STEM}"
ORG_FIXTURE_GATE_EDGE = "in_progress->for_review"
ORG_FIXTURE_GATE_HANDLER = "spec-kitty-pre-review"
ORG_FIXTURE_PACK_NAME = "org-fixture-pack"
ORG_FIXTURE_ACTION_URN = f"action:{ORG_FIXTURE_MISSION}/{ORG_FIXTURE_ACTION}"


def write_org_tier_step_contract_fixture(
    org_root: Path,
    *,
    include_gates: bool = True,
    include_drg_fragment: bool = True,
) -> None:
    """Build a flat-layout org pack: one step contract + one DRG fragment.

    Mirrors ``_write_org_directive_fixture``'s shape
    (``tests/charter/test_org_scan_dirs_activation_regression.py:62``): a
    ``directives/<stem>.directive.yaml`` artifact file (read by
    ``resolve_artifact_urn`` for activation-stem resolution, T009) plus a
    root-level ``<stem>.graph.yaml`` DRG fragment (read by
    ``load_validated_graph``/``filter_graph_by_activation``). Additionally
    ships ``mission_step_contracts/<id>.step-contract.yaml`` (FR-001's
    ``org_dirs`` target) declaring one step whose ``delegates_to`` cites the
    directive, plus a ``gates:`` block on that same action (FR-005/User
    Story 3) — one fixture, every FR-001/FR-002/FR-005 observable.

    ``include_drg_fragment=False`` drops the DRG fragment only (Acceptance
    Scenario 3: the same delegation candidate becomes unresolved, not
    resolved, when the org pack's DRG contribution is removed).
    ``include_gates=False`` drops the ``gates:`` block only.
    """
    directives_dir = org_root / "directives"
    directives_dir.mkdir(parents=True, exist_ok=True)
    (directives_dir / f"{ORG_FIXTURE_DIRECTIVE_STEM}.directive.yaml").write_text(
        f"id: {ORG_FIXTURE_DIRECTIVE_STEM}\n",
        encoding="utf-8",
    )

    gates: list[dict[str, object]] = (
        [
            {
                "on_transition": ORG_FIXTURE_GATE_EDGE,
                "handler": ORG_FIXTURE_GATE_HANDLER,
                "handler_kind": "mission_step_contract",
                "schema_version": "1.0",
            }
        ]
        if include_gates
        else []
    )
    _write_yaml(
        org_root / "mission_step_contracts" / f"{ORG_FIXTURE_CONTRACT_ID}.step-contract.yaml",
        {
            "schema_version": "1.0",
            "id": ORG_FIXTURE_CONTRACT_ID,
            "mission": ORG_FIXTURE_MISSION,
            "action": ORG_FIXTURE_ACTION,
            "steps": [
                {
                    "id": "review_gate",
                    "description": "Run the org-tier review gate",
                    "delegates_to": {
                        "kind": "directive",
                        "candidates": [ORG_FIXTURE_DIRECTIVE_STEM],
                    },
                }
            ],
            "gates": gates,
        },
    )

    # ``load_graph_or_dir`` raises ``DRGLoadError`` for a directory containing
    # zero ``*.graph.yaml`` files (it does not treat "no fragment" as "empty
    # graph"), so the "fragment absent" arm still writes a *valid, empty*
    # fragment -- proving the candidate goes unresolved because the directive
    # node is gone, not because the org root failed to load at all.
    _write_yaml(
        org_root / f"{ORG_FIXTURE_DIRECTIVE_STEM}.graph.yaml",
        {
            "schema_version": "1.0",
            "generated_at": "2026-08-16T00:00:00Z",
            "generated_by": "test",
            "nodes": (
                [
                    {
                        "urn": ORG_FIXTURE_ACTION_URN,
                        "kind": "action",
                        "label": "Org fixture review action",
                    },
                    {
                        "urn": ORG_FIXTURE_DIRECTIVE_URN,
                        "kind": "directive",
                        "label": "Org tier fixture directive",
                    },
                ]
                if include_drg_fragment
                else []
            ),
            "edges": (
                [
                    {
                        "source": ORG_FIXTURE_ACTION_URN,
                        "target": ORG_FIXTURE_DIRECTIVE_URN,
                        "relation": "scope",
                    }
                ]
                if include_drg_fragment
                else []
            ),
        },
    )


def write_org_pack_config(repo_root: Path, org_root: Path, *, pack_name: str = ORG_FIXTURE_PACK_NAME) -> None:
    """Register *org_root* as a configured org pack in ``.kittify/config.yaml``.

    Single registration serves both resolution shapes this mission threads:
    ``resolve_org_dirs`` (FR-001/FR-005, list-shaped, joins ``subdir`` onto
    this root) and ``_enumerate_org_pack_paths`` (FR-002, single-path,
    first-match on this same root) — both read the identical
    ``doctrine.org.packs`` config this helper writes.
    """
    config_dir = repo_root / ".kittify"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "config.yaml").write_text(
        "\n".join(
            [
                "doctrine:",
                "  org:",
                "    packs:",
                f"      - name: {pack_name}",
                f"        local_path: {org_root}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


class _FakeInvocationExecutor:
    """Stub ``ProfileInvocationExecutor`` avoiding the real invocation/writer
    stack, which is orthogonal to org-tier resolution (T008/T009's concern).
    """

    def invoke(self, _request_text: str, **_kwargs: object) -> object:
        return SimpleNamespace(invocation_id="inv-org-fixture-1")

    def complete_invocation(self, _invocation_id: str, *, outcome: str, closed_by: str) -> None:
        assert outcome == "done"
        assert closed_by == "agent"


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


def test_resolve_pack_context_propagates_org_pack_env_var_unset_error(
    tmp_path: Path,
) -> None:
    """``OrgPackEnvVarUnsetError`` must propagate out of ``_resolve_pack_context``.

    The narrowed ``except (OrgPackEnvVarUnsetError, OrgPackSubdirEscapeError): raise``
    block in ``_resolve_pack_context`` guarantees the error is never swallowed
    into a ``None`` return.  This test kills the mutation that would widen the
    handler back to a bare ``except Exception: return None``.
    """
    from doctrine.drg.org_pack_config import OrgPackEnvVarUnsetError  # noqa: PLC0415

    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    error = OrgPackEnvVarUnsetError(
        "test-pack", "${MISSING_VAR}/pack", "${MISSING_VAR}"
    )

    executor = StepContractExecutor(repo_root=repo_root)
    with patch("charter.pack_context.PackContext.from_config", side_effect=error), pytest.raises(OrgPackEnvVarUnsetError):
        executor._resolve_pack_context(repo_root)


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


# ---------------------------------------------------------------------------
# T008 — FR-001/FR-002 red-first regression (SC-001, SC-002, User Story 1)
# ---------------------------------------------------------------------------


def test_org_only_step_contract_becomes_discoverable_and_delegation_resolves(
    tmp_path: Path,
) -> None:
    """FR-001 (SC-002) + FR-002 (User Story 1 Acceptance Scenarios 1 & 2).

    An org-tier step contract with no project-tier duplicate is invisible to
    a project-dir-only ``MissionStepContractRepository`` construction (the
    pre-fix shape); ``StepContractExecutor``'s own default construction
    (FR-001) makes it discoverable, and its ``delegates_to`` candidate
    resolves to the org-tier DRG directive's URN (FR-002) -- not merely "no
    exception raised".

    Red-first: on the pre-fix commit, ``StepContractExecutor(repo_root=...)``
    constructs a project-dir-only repository, ``get_by_action`` returns
    ``None``, and ``.execute(...)`` raises ``StepContractExecutionError:
    No step contract found for mission/action org-fixture-mission/review``.
    """
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    org_root = tmp_path / "org-pack"
    write_org_tier_step_contract_fixture(org_root)
    write_org_pack_config(repo_root, org_root)

    executor = StepContractExecutor(
        repo_root=repo_root,
        invocation_executor=_FakeInvocationExecutor(),
    )

    # SC-002 (True/False mechanism): FR-001 makes the org-only contract
    # discoverable via the executor's own repository construction -- no
    # ``contract_repository`` override is passed above, so this exercises
    # the real fix, not an injected fixture.
    assert executor._contracts.get_by_action(ORG_FIXTURE_MISSION, ORG_FIXTURE_ACTION) is not None

    result = executor.execute(
        StepContractExecutionContext(
            repo_root=repo_root,
            mission=ORG_FIXTURE_MISSION,
            action=ORG_FIXTURE_ACTION,
            actor="pytest",
            profile_hint="implementer-fixture",
        )
    )

    assert result.contract_id == ORG_FIXTURE_CONTRACT_ID
    assert [d.urn for d in result.steps[0].resolved_delegations] == [ORG_FIXTURE_DIRECTIVE_URN]
    assert result.steps[0].unresolved_candidates == ()


def test_org_only_step_contract_delegation_unresolved_when_drg_fragment_absent(
    tmp_path: Path,
) -> None:
    """User Story 1 Acceptance Scenario 3: the before/after contrast that
    proves FR-002, not merely "the call doesn't crash". Same org-only
    contract as above, but the org pack's DRG fragment is removed -- the
    same candidate must appear in ``unresolved_candidates`` instead of
    ``resolved_delegations``.
    """
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    org_root = tmp_path / "org-pack"
    write_org_tier_step_contract_fixture(org_root, include_drg_fragment=False)
    write_org_pack_config(repo_root, org_root)

    result = StepContractExecutor(
        repo_root=repo_root,
        invocation_executor=_FakeInvocationExecutor(),
    ).execute(
        StepContractExecutionContext(
            repo_root=repo_root,
            mission=ORG_FIXTURE_MISSION,
            action=ORG_FIXTURE_ACTION,
            actor="pytest",
            profile_hint="implementer-fixture",
        )
    )

    assert result.steps[0].resolved_delegations == ()
    assert result.steps[0].unresolved_candidates == (ORG_FIXTURE_DIRECTIVE_STEM,)


def test_load_validated_graph_node_count_increases_by_one_with_org_root(
    tmp_path: Path,
) -> None:
    """SC-001: DRG node-count delta from ``load_validated_graph`` when a
    resolved ``org_root`` is supplied (FR-002's exact mechanism).

    The reproducible number in this checkout is 347 -> 348 (one synthetic
    org directive node added, D-000(4)) -- asserted here as a DELTA
    (``with_org - without_org == 1``), not either literal absolute baseline,
    since the built-in graph's node count may drift by the time this runs
    (per WP02's explicit instruction: assert the mechanism, not a hardcoded
    magic number).
    """
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    org_root = tmp_path / "org-directive-only-pack"
    minimal_directive_urn = "directive:sc-001-node-count-probe-directive"
    _write_yaml(
        org_root / "sc-001-node-count-probe-directive.graph.yaml",
        {
            "schema_version": "1.0",
            "generated_at": "2026-08-16T00:00:00Z",
            "generated_by": "test",
            "nodes": [
                {
                    "urn": minimal_directive_urn,
                    "kind": "directive",
                    "label": "SC-001 node-count probe directive",
                },
            ],
            "edges": [],
        },
    )

    without_org = load_validated_graph(repo_root)
    with_org = load_validated_graph(repo_root, org_root=org_root)

    without_urns = {str(node.urn) for node in without_org.nodes}
    with_urns = {str(node.urn) for node in with_org.nodes}

    assert len(with_org.nodes) - len(without_org.nodes) == 1
    assert minimal_directive_urn not in without_urns
    assert minimal_directive_urn in with_urns


# ---------------------------------------------------------------------------
# Landing fold — malformed org-pack DRG must degrade with a WARNING, not
# crash composition (regression for #3520's e2e-cross-cutting break).
# ---------------------------------------------------------------------------


def test_malformed_org_pack_drg_degrades_with_warning_instead_of_crashing(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """A registered org pack whose ``drg/`` fragment is recognised (a
    ``*.graph.yaml`` file the loader's glob matches) but genuinely malformed
    (not a YAML mapping at the top level) must not turn a previously-working
    composition into a hard block.

    ``StepContractExecutor``'s org-root resolution comment claims to mirror
    ``charter.action_doctrine_bundle._resolve_action_bundle``'s graceful
    degrade (catch ``DRGLoadError``/``OrgDRGFragmentError``, warn, continue
    with built-in + project doctrine only) -- this pins that the executor
    actually does that for its own ``load_validated_graph`` call, not just
    cites the precedent.

    Landing fold (#3401 x #3525) note: this fixture used to be a
    ``drg/fragment.yaml`` file (a name the DRG loader's ``*.graph.yaml`` glob
    does NOT match -- this repo's own ``packs/internal`` is exactly that
    shape, see ``test_org_pack_with_no_recognised_drg_content_degrades_silently``
    below). Under the pre-landing-fold executor, the pre-probe used bare
    ``load_graph_or_dir(org_root)`` (root-level only), which raised
    ``DRGLoadError`` for ANY org root lacking a root-level graph file --
    including that shape -- so this test coincidentally passed by exercising
    a false positive, not a real malformed-content case. Now that the
    pre-probe mirrors ``_load_org_layer`` (root graph AND ``drg/``,
    #3401 x #3525's fix), that shape is correctly recognised as "no org DRG
    layer" (a legitimate, silent no-op -- see the sibling test below), so
    this fixture was updated to a ``*.graph.yaml``-named fragment with
    genuinely invalid content, which both the pre- and post-fix loader treat
    as malformed.
    """
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _setup_fixture_profiles(repo_root)
    _write_project_graph(repo_root)

    built_in_dir = tmp_path / "contracts"
    _write_fixture_contract(built_in_dir)

    # Org pack registered, directory exists, its `drg/` fragment has a
    # recognised `*.graph.yaml` name but a non-mapping top-level document --
    # genuinely malformed, not merely absent.
    org_root = tmp_path / "malformed-org-pack"
    (org_root / "drg").mkdir(parents=True)
    (org_root / "drg" / "broken.graph.yaml").write_text(
        "- not\n- a\n- mapping\n", encoding="utf-8"
    )
    write_org_pack_config(repo_root, org_root)

    context_result = SimpleNamespace(mode="compact", text="fixture governance context")
    with (
        patch(
            "specify_cli.invocation.executor.build_charter_context",
            return_value=context_result,
        ),
        caplog.at_level(
            logging.WARNING, logger="specify_cli.mission_step_contracts.executor"
        ),
    ):
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

    # Composition still succeeds -- identical three-step outcome to the
    # no-org-pack baseline (test_three_delegated_steps_...).
    assert [step.step_id for step in result.steps] == ["alpha", "beta", "gamma"]

    warnings = [record for record in caplog.records if record.levelno == logging.WARNING]
    assert len(warnings) == 1, [record.getMessage() for record in caplog.records]
    message = warnings[0].getMessage()
    assert str(org_root) in message
    assert "OrgDRGFragmentError" in message


def test_org_pack_with_no_recognised_drg_content_degrades_silently(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """An org pack that ships content in a schema the DRG loader doesn't
    recognise at all (no ``graph.yaml``/``*.graph.yaml`` anywhere -- this
    repo's own ``packs/internal``, whose ``drg/fragment.yaml`` uses an
    unrelated org-fragment schema, is exactly this shape) is legitimately
    "no org DRG layer" per ``_load_org_layer``'s own documented contract, not
    a malformed pack -- it must degrade SILENTLY (zero warnings), the same
    outcome ``load_validated_graph`` already produces for this shape when
    called directly (no pre-probe involved).

    Landing fold (#3401 x #3525): before this fold, the executor's pre-probe
    used bare ``load_graph_or_dir(org_root)`` (root-level only), which
    disagreed with ``_load_org_layer`` on this exact shape -- it raised
    ``DRGLoadError`` and produced a false-positive "org pack DRG failed to
    load" WARNING on every single dispatch in THIS repository (every
    mission-step composition here has ``packs/internal`` registered). Now
    that the pre-probe mirrors ``_load_org_layer`` exactly, that noise is
    gone.
    """
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _setup_fixture_profiles(repo_root)
    _write_project_graph(repo_root)

    built_in_dir = tmp_path / "contracts"
    _write_fixture_contract(built_in_dir)

    # Same shape as `packs/internal`: a `drg/fragment.yaml` file whose name
    # the loader's `*.graph.yaml` glob does not match, and no root-level
    # graph file either -- "no org DRG layer" per `_load_org_layer`, not a
    # load failure.
    org_root = tmp_path / "no-drg-content-org-pack"
    (org_root / "drg").mkdir(parents=True)
    (org_root / "drg" / "fragment.yaml").write_text("kind: directives\n", encoding="utf-8")
    write_org_pack_config(repo_root, org_root)

    context_result = SimpleNamespace(mode="compact", text="fixture governance context")
    with (
        patch(
            "specify_cli.invocation.executor.build_charter_context",
            return_value=context_result,
        ),
        caplog.at_level(
            logging.WARNING, logger="specify_cli.mission_step_contracts.executor"
        ),
    ):
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

    assert [step.step_id for step in result.steps] == ["alpha", "beta", "gamma"]
    assert not [record for record in caplog.records if record.levelno == logging.WARNING]


def test_well_formed_org_pack_drg_contributes_without_warning(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Negative case for the malformed-org-pack degrade above: a conformant
    org pack (a real ``*.graph.yaml`` directly at its root) must load and
    contribute normally with no degradation warning -- proving the fix
    doesn't unconditionally warn regardless of whether org loading actually
    failed.
    """
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _setup_fixture_profiles(repo_root)
    _write_project_graph(repo_root)

    built_in_dir = tmp_path / "contracts"
    _write_fixture_contract(built_in_dir)

    org_root = tmp_path / "well-formed-org-pack"
    _write_yaml(
        org_root / "org-probe.graph.yaml",
        {
            "schema_version": "1.0",
            "generated_at": "2026-08-17T00:00:00Z",
            "generated_by": "test",
            "nodes": [
                {
                    "urn": "directive:org-probe-directive",
                    "kind": "directive",
                    "label": "Org probe directive",
                }
            ],
            "edges": [],
        },
    )
    write_org_pack_config(repo_root, org_root)

    context_result = SimpleNamespace(mode="compact", text="fixture governance context")
    with (
        patch(
            "specify_cli.invocation.executor.build_charter_context",
            return_value=context_result,
        ),
        caplog.at_level(
            logging.WARNING, logger="specify_cli.mission_step_contracts.executor"
        ),
    ):
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

    assert [step.step_id for step in result.steps] == ["alpha", "beta", "gamma"]
    assert not [record for record in caplog.records if record.levelno == logging.WARNING]


# ---------------------------------------------------------------------------
# #3525 Fold B — the load-bearing chain fix (N=2 org packs, not just pack #1)
# ---------------------------------------------------------------------------
#
# The problem: org-tier doctrine resolution already worked for a CHAIN of N
# org packs at every seam EXCEPT the DRG graph merge, which took only pack #1
# (first-match-wins). Pack #2's ``mission_step_contract`` loaded into the
# repository (chain-correct overlay) but its graph nodes / ``delegates_to``
# edges were absent from the DRG (first-only) -- the executor even disagreed
# with itself: repo half sees pack #2's contract, DRG half doesn't know its
# delegation target exists. This section proves the fix at the executor
# level (the primitive-level proof lives in
# ``tests/charter/test_org_pack_chain_drg_merge.py``).

PACK_B_ACTION = "plan"
PACK_B_CONTRACT_ID = "org-fixture-plan"
PACK_B_DIRECTIVE_STEM = "org-tier-fixture-directive-b"
PACK_B_DIRECTIVE_URN = f"directive:{PACK_B_DIRECTIVE_STEM}"
PACK_B_ACTION_URN = f"action:{ORG_FIXTURE_MISSION}/{PACK_B_ACTION}"
PACK_B_PACK_NAME = "org-fixture-pack-b"


def write_second_org_pack_fixture(org_root_b: Path) -> None:
    """Second org pack (#3525 chain fixture): a DISTINCT ``(mission, action)``
    step contract + DRG fragment, registered as pack #2 in declaration order.

    Mirrors :func:`write_org_tier_step_contract_fixture`'s shape but targets
    a different action than pack A's fixture so both packs' contributions
    are independently observable -- neither shadows the other at the
    repository layer, and (pre-fix) only pack A's DRG contribution was ever
    visible to the executor.
    """
    directives_dir = org_root_b / "directives"
    directives_dir.mkdir(parents=True, exist_ok=True)
    (directives_dir / f"{PACK_B_DIRECTIVE_STEM}.directive.yaml").write_text(
        f"id: {PACK_B_DIRECTIVE_STEM}\n",
        encoding="utf-8",
    )
    _write_yaml(
        org_root_b / "mission_step_contracts" / f"{PACK_B_CONTRACT_ID}.step-contract.yaml",
        {
            "schema_version": "1.0",
            "id": PACK_B_CONTRACT_ID,
            "mission": ORG_FIXTURE_MISSION,
            "action": PACK_B_ACTION,
            "steps": [
                {
                    "id": "plan_gate",
                    "description": "Run the pack-B plan gate",
                    "delegates_to": {
                        "kind": "directive",
                        "candidates": [PACK_B_DIRECTIVE_STEM],
                    },
                }
            ],
            "gates": [],
        },
    )
    _write_yaml(
        org_root_b / f"{PACK_B_DIRECTIVE_STEM}.graph.yaml",
        {
            "schema_version": "1.0",
            "generated_at": "2026-08-17T00:00:00Z",
            "generated_by": "test",
            "nodes": [
                {
                    "urn": PACK_B_ACTION_URN,
                    "kind": "action",
                    "label": "Pack B plan action",
                },
                {
                    "urn": PACK_B_DIRECTIVE_URN,
                    "kind": "directive",
                    "label": "Pack B fixture directive",
                },
            ],
            "edges": [
                {
                    "source": PACK_B_ACTION_URN,
                    "target": PACK_B_DIRECTIVE_URN,
                    "relation": "scope",
                }
            ],
        },
    )


def write_two_pack_org_config(
    repo_root: Path,
    org_root_a: Path,
    org_root_b: Path,
    *,
    pack_a_name: str = ORG_FIXTURE_PACK_NAME,
    pack_b_name: str = PACK_B_PACK_NAME,
) -> None:
    """Register TWO org packs, in declaration order A then B (#3525 chain fixture)."""
    config_dir = repo_root / ".kittify"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "config.yaml").write_text(
        "\n".join(
            [
                "doctrine:",
                "  org:",
                "    packs:",
                f"      - name: {pack_a_name}",
                f"        local_path: {org_root_a}",
                f"      - name: {pack_b_name}",
                f"        local_path: {org_root_b}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def test_chain_two_org_packs_executor_self_consistency(tmp_path: Path) -> None:
    """Executor self-consistency (#3525 Fold B): repo loads pack #2's
    contract AND its ``delegates_to`` target resolves in the DRG.

    Red-first: on the pre-fix executor, ``_enumerate_org_pack_paths`` break-
    on-first picks pack A (declared first) as the sole DRG ``org_root``, so
    pack B's DRG fragment (its ``plan`` action node + directive) never loads.
    The repository half still discovers pack B's contract fine (chain-
    correct overlay), so pre-fix this assertion set fails specifically on
    ``resolved_delegations`` / ``unresolved_candidates`` -- not on contract
    discovery -- which is the exact "executor disagrees with itself" shape
    described by the fold.
    """
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    org_root_a = tmp_path / "org-pack-a"
    org_root_b = tmp_path / "org-pack-b"
    write_org_tier_step_contract_fixture(org_root_a)
    write_second_org_pack_fixture(org_root_b)
    write_two_pack_org_config(repo_root, org_root_a, org_root_b)

    executor = StepContractExecutor(
        repo_root=repo_root,
        invocation_executor=_FakeInvocationExecutor(),
    )

    # Repository half: both packs' contracts are discoverable -- already
    # chain-correct pre-fix (repository overlay is later-declared-wins
    # across N packs). This assertion documents the baseline; it is not the
    # regression this test exists to catch.
    assert executor._contracts.get_by_action(ORG_FIXTURE_MISSION, ORG_FIXTURE_ACTION) is not None
    assert executor._contracts.get_by_action(ORG_FIXTURE_MISSION, PACK_B_ACTION) is not None

    # DRG half: pack #2's contribution. This is the load-bearing assertion
    # that was broken pre-fix (first-match-wins dropped pack B's DRG
    # fragment entirely, so its delegation candidate could never resolve).
    result = executor.execute(
        StepContractExecutionContext(
            repo_root=repo_root,
            mission=ORG_FIXTURE_MISSION,
            action=PACK_B_ACTION,
            actor="pytest",
            profile_hint="implementer-fixture",
        )
    )
    assert result.contract_id == PACK_B_CONTRACT_ID
    assert [d.urn for d in result.steps[0].resolved_delegations] == [PACK_B_DIRECTIVE_URN]
    assert result.steps[0].unresolved_candidates == ()


def test_chain_per_root_degrade_pack_a_survives_malformed_pack_b(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Per-root degrade (#3525 Fold B): a malformed pack #2 drops ONLY pack
    #2 (WARNING) -- pack #1's DRG contribution must still be present.

    Before this fold, ``_load_graph_degrading_malformed_org_pack`` degraded
    all-or-nothing on a single ``org_root``: with two packs configured and
    only the SECOND malformed, the pre-fix code (which resolves only the
    first existing root as ``org_root``) never even attempts to load pack
    B's DRG, so this specific failure mode was structurally untestable
    pre-fix -- the fix is what makes "attempt both, isolate the bad one"
    possible at all.

    Landing fold (#3401 x #3525) note: pack B's fixture was updated from a
    ``drg/fragment.yaml`` file (a name the loader's ``*.graph.yaml`` glob
    does not match) to a recognised-but-invalid ``*.graph.yaml`` fragment.
    The former shape is ``_load_org_layer``'s legitimate "no org DRG layer"
    no-op (see
    ``test_org_pack_with_no_recognised_drg_content_degrades_silently`` in
    this module) once the pre-probe mirrors ``_load_org_layer`` instead of
    calling ``load_graph_or_dir`` directly at the root -- it no longer
    produces a warning, so it stopped exercising this test's "malformed
    pack drops out with a WARNING" claim.
    """
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    org_root_a = tmp_path / "org-pack-a"
    write_org_tier_step_contract_fixture(org_root_a)

    # Pack B: registered, directory exists, `drg/` fragment has a recognised
    # `*.graph.yaml` name but genuinely invalid (non-mapping) content.
    org_root_b = tmp_path / "malformed-org-pack-b"
    (org_root_b / "drg").mkdir(parents=True)
    (org_root_b / "drg" / "broken.graph.yaml").write_text(
        "- not\n- a\n- mapping\n", encoding="utf-8"
    )

    write_two_pack_org_config(repo_root, org_root_a, org_root_b)

    with caplog.at_level(
        logging.WARNING, logger="specify_cli.mission_step_contracts.executor"
    ):
        result = StepContractExecutor(
            repo_root=repo_root,
            invocation_executor=_FakeInvocationExecutor(),
        ).execute(
            StepContractExecutionContext(
                repo_root=repo_root,
                mission=ORG_FIXTURE_MISSION,
                action=ORG_FIXTURE_ACTION,
                actor="pytest",
                profile_hint="implementer-fixture",
            )
        )

    # Pack A still contributes despite pack B being malformed.
    assert [d.urn for d in result.steps[0].resolved_delegations] == [ORG_FIXTURE_DIRECTIVE_URN]
    assert result.steps[0].unresolved_candidates == ()

    warnings = [record for record in caplog.records if record.levelno == logging.WARNING]
    assert len(warnings) == 1, [record.getMessage() for record in caplog.records]
    message = warnings[0].getMessage()
    assert str(org_root_b) in message
    assert "OrgDRGFragmentError" in message


# ---------------------------------------------------------------------------
# Landing fold (#3401 x #3525) — the executor's per-root pre-probe must
# mirror ``_load_org_layer`` semantics (root graph AND drg/ fragment), not
# just the root level, or it misclassifies both a "valid root + malformed
# drg/" pack (isolation regression, MAJOR) and a "drg/-only" pack (#3384's
# fix delivering zero doctrine on this path, MINOR).
# ---------------------------------------------------------------------------


def _write_drg_only_org_pack_fixture(org_root: Path) -> None:
    """A guide-compliant org pack whose DRG content lives ONLY under
    ``drg/`` -- no root-level ``graph.yaml``/``*.graph.yaml`` (the #3384
    shape). Reuses the shared ``ORG_FIXTURE_*`` constants so assertions can
    check the same directive URN resolves as
    :func:`write_org_tier_step_contract_fixture`'s root-graph shape.
    """
    directives_dir = org_root / "directives"
    directives_dir.mkdir(parents=True, exist_ok=True)
    (directives_dir / f"{ORG_FIXTURE_DIRECTIVE_STEM}.directive.yaml").write_text(
        f"id: {ORG_FIXTURE_DIRECTIVE_STEM}\n",
        encoding="utf-8",
    )
    _write_yaml(
        org_root / "mission_step_contracts" / f"{ORG_FIXTURE_CONTRACT_ID}.step-contract.yaml",
        {
            "schema_version": "1.0",
            "id": ORG_FIXTURE_CONTRACT_ID,
            "mission": ORG_FIXTURE_MISSION,
            "action": ORG_FIXTURE_ACTION,
            "steps": [
                {
                    "id": "review_gate",
                    "description": "Run the org-tier review gate",
                    "delegates_to": {
                        "kind": "directive",
                        "candidates": [ORG_FIXTURE_DIRECTIVE_STEM],
                    },
                }
            ],
            "gates": [],
        },
    )
    _write_yaml(
        org_root / "drg" / f"{ORG_FIXTURE_DIRECTIVE_STEM}.graph.yaml",
        {
            "schema_version": "1.0",
            "generated_at": "2026-08-17T00:00:00Z",
            "generated_by": "test",
            "nodes": [
                {
                    "urn": ORG_FIXTURE_ACTION_URN,
                    "kind": "action",
                    "label": "Org fixture review action",
                },
                {
                    "urn": ORG_FIXTURE_DIRECTIVE_URN,
                    "kind": "directive",
                    "label": "Org tier fixture directive",
                },
            ],
            "edges": [
                {
                    "source": ORG_FIXTURE_ACTION_URN,
                    "target": ORG_FIXTURE_DIRECTIVE_URN,
                    "relation": "scope",
                }
            ],
        },
    )


def test_chain_pack_a_malformed_drg_fragment_survives_pack_b_contributes(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """MAJOR: a root-level-only pre-probe can mark a pack "healthy" when its
    root graph is valid but its sibling ``drg/`` fragment is malformed --
    ``_load_org_layer`` (the real loader ``load_validated_graph`` uses) still
    raises ``OrgDRGFragmentError`` when it later loads that same root's
    ``drg/`` fragment during the real merge.

    Pre-fix, the executor's pre-probe (``load_graph_or_dir(root)``,
    non-recursive) never looks at ``drg/`` at all, so pack A above is wrongly
    classified healthy; the executor then calls ``load_validated_graph``
    unwrapped (it imports only ``load_validated_graph``, never
    ``OrgDRGFragmentError``) and the exception propagates UNCAUGHT out of
    ``execute()``, hard-aborting the ENTIRE dispatch -- erasing pack B's
    healthy contribution too. This is a true regression of #3525's
    per-root-isolation promise: before #3520 wired ``drg/`` support into the
    org loader at all, a malformed ``drg/`` fragment was inert on this path.

    Red-first: on the pre-fix executor this raises
    ``charter._drg_helpers.OrgDRGFragmentError`` uncaught out of
    ``execute()`` instead of degrading pack A alone and letting pack B's
    doctrine reach composition.
    """
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    org_root_a = tmp_path / "org-pack-a"
    write_org_tier_step_contract_fixture(org_root_a)  # valid ROOT graph
    # Malformed drg/ fragment sitting ALONGSIDE the valid root graph -- a
    # non-mapping top-level document, which `load_graph` rejects outright.
    (org_root_a / "drg").mkdir(parents=True)
    (org_root_a / "drg" / "broken.graph.yaml").write_text(
        "- not\n- a\n- mapping\n", encoding="utf-8"
    )

    org_root_b = tmp_path / "org-pack-b"
    write_second_org_pack_fixture(org_root_b)  # fully valid

    write_two_pack_org_config(repo_root, org_root_a, org_root_b)

    with caplog.at_level(
        logging.WARNING, logger="specify_cli.mission_step_contracts.executor"
    ):
        result = StepContractExecutor(
            repo_root=repo_root,
            invocation_executor=_FakeInvocationExecutor(),
        ).execute(
            StepContractExecutionContext(
                repo_root=repo_root,
                mission=ORG_FIXTURE_MISSION,
                action=PACK_B_ACTION,
                actor="pytest",
                profile_hint="implementer-fixture",
            )
        )

    # Pack B's contribution reaches composition despite pack A's malformed
    # drg/ fragment -- dispatch must SUCCEED, not hard-abort.
    assert result.contract_id == PACK_B_CONTRACT_ID
    assert [d.urn for d in result.steps[0].resolved_delegations] == [PACK_B_DIRECTIVE_URN]
    assert result.steps[0].unresolved_candidates == ()

    # Exactly one WARNING, naming pack A -- pack B is never mentioned as
    # dropped.
    warnings = [record for record in caplog.records if record.levelno == logging.WARNING]
    assert len(warnings) == 1, [record.getMessage() for record in caplog.records]
    message = warnings[0].getMessage()
    assert str(org_root_a) in message


def test_drg_only_org_pack_no_root_graph_classified_healthy_and_contributes(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """MINOR: a guide-compliant org pack whose DRG content lives ONLY under
    ``drg/`` (no root-level ``graph.yaml``/``*.graph.yaml`` -- the #3384
    shape) must be classified healthy by the executor's pre-probe and
    contribute its doctrine, not be dropped as "unhealthy" merely because
    the pre-probe only reads the pack root.

    Red-first: on the pre-fix executor, ``load_graph_or_dir(org_root)``
    (root-level only) raises ``DRGLoadError: No DRG graph files found`` for
    this pack, so it is dropped with a misleading WARNING and never even
    reaches ``_load_org_layer`` -- #3384's drg/-only fix contributes zero
    doctrine on this dispatch path even though the pack itself is perfectly
    valid.
    """
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    org_root = tmp_path / "drg-only-org-pack"
    _write_drg_only_org_pack_fixture(org_root)
    write_org_pack_config(repo_root, org_root)

    with caplog.at_level(
        logging.WARNING, logger="specify_cli.mission_step_contracts.executor"
    ):
        result = StepContractExecutor(
            repo_root=repo_root,
            invocation_executor=_FakeInvocationExecutor(),
        ).execute(
            StepContractExecutionContext(
                repo_root=repo_root,
                mission=ORG_FIXTURE_MISSION,
                action=ORG_FIXTURE_ACTION,
                actor="pytest",
                profile_hint="implementer-fixture",
            )
        )

    assert result.contract_id == ORG_FIXTURE_CONTRACT_ID
    assert [d.urn for d in result.steps[0].resolved_delegations] == [ORG_FIXTURE_DIRECTIVE_URN]
    assert result.steps[0].unresolved_candidates == ()

    # Healthy pack -- must not be dropped, so no degrade warning is logged.
    warnings = [record for record in caplog.records if record.levelno == logging.WARNING]
    assert not warnings, [record.getMessage() for record in caplog.records]
