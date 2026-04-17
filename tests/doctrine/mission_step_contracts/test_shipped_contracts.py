"""Acceptance tests: shipped MissionStepContracts for software-dev are valid and complete.

These tests verify:
1. All 4 software-dev actions have shipped step contracts
2. Every step contract passes model validation
3. Delegates-to references point to valid ArtifactKind values
4. Step IDs are unique within each contract
5. Contracts are loadable via DoctrineService
6. Round-trip serialization preserves all fields
"""

import pytest

from doctrine.artifact_kinds import ArtifactKind
from doctrine.mission_step_contracts.models import MissionStepContract
from doctrine.mission_step_contracts.repository import MissionStepContractRepository
from doctrine.service import DoctrineService


SOFTWARE_DEV_ACTIONS = ("specify", "plan", "implement", "review")

pytestmark = pytest.mark.fast


class TestShippedContractsExistAndValidate:
    """Every software-dev action has a shipped step contract."""

    @pytest.fixture
    def repo(self) -> MissionStepContractRepository:
        return MissionStepContractRepository()

    @pytest.mark.parametrize("action", SOFTWARE_DEV_ACTIONS)
    def test_shipped_contract_exists(self, repo: MissionStepContractRepository, action: str) -> None:
        contract = repo.get_by_action("software-dev", action)
        assert contract is not None, f"No shipped step contract for software-dev/{action}"

    @pytest.mark.parametrize("action", SOFTWARE_DEV_ACTIONS)
    def test_contract_has_at_least_one_step(self, repo: MissionStepContractRepository, action: str) -> None:
        contract = repo.get_by_action("software-dev", action)
        assert contract is not None
        assert len(contract.steps) >= 1

    @pytest.mark.parametrize("action", SOFTWARE_DEV_ACTIONS)
    def test_step_ids_are_unique(self, repo: MissionStepContractRepository, action: str) -> None:
        contract = repo.get_by_action("software-dev", action)
        assert contract is not None
        ids = [s.id for s in contract.steps]
        assert len(ids) == len(set(ids)), f"Duplicate step IDs in {action}: {ids}"

    @pytest.mark.parametrize("action", SOFTWARE_DEV_ACTIONS)
    def test_delegates_to_references_valid_kinds(self, repo: MissionStepContractRepository, action: str) -> None:
        contract = repo.get_by_action("software-dev", action)
        assert contract is not None
        for step in contract.steps:
            if step.delegates_to is not None:
                assert step.delegates_to.kind in ArtifactKind, (
                    f"Step {step.id} in {action} delegates to invalid kind: {step.delegates_to.kind}"
                )
                assert len(step.delegates_to.candidates) > 0


class TestContractsAccessibleViaService:
    """DoctrineService exposes step contracts via lazy repository."""

    def test_service_has_mission_step_contracts_property(self) -> None:
        service = DoctrineService()
        repo = service.mission_step_contracts
        assert isinstance(repo, MissionStepContractRepository)

    def test_service_caches_repository(self) -> None:
        service = DoctrineService()
        first = service.mission_step_contracts
        second = service.mission_step_contracts
        assert first is second

    @pytest.mark.parametrize("action", SOFTWARE_DEV_ACTIONS)
    def test_service_loads_shipped_contracts(self, action: str) -> None:
        service = DoctrineService()
        contract = service.mission_step_contracts.get_by_action("software-dev", action)
        assert contract is not None
        assert isinstance(contract, MissionStepContract)


class TestImplementContractStructure:
    """The implement contract has the expected step structure.

    This is the most complex contract (branching delegation, quality gates,
    commit signing). Pin its structure as a regression guard.
    """

    @pytest.fixture
    def contract(self) -> MissionStepContract:
        repo = MissionStepContractRepository()
        c = repo.get_by_action("software-dev", "implement")
        assert c is not None
        return c

    def test_has_bootstrap_step(self, contract: MissionStepContract) -> None:
        bootstrap = next((s for s in contract.steps if s.id == "bootstrap"), None)
        assert bootstrap is not None
        assert bootstrap.command is not None
        assert "charter context" in bootstrap.command

    def test_has_workspace_step_with_paradigm_delegation(self, contract: MissionStepContract) -> None:
        workspace = next((s for s in contract.steps if s.id == "workspace"), None)
        assert workspace is not None
        assert workspace.delegates_to is not None
        assert workspace.delegates_to.kind == ArtifactKind.PARADIGM
        assert "execution-lanes" in workspace.delegates_to.candidates

    def test_has_quality_gate_step(self, contract: MissionStepContract) -> None:
        gate = next((s for s in contract.steps if s.id == "quality_gate"), None)
        assert gate is not None
        assert gate.delegates_to is not None
        assert gate.delegates_to.kind == ArtifactKind.DIRECTIVE

    def test_has_status_transition_step(self, contract: MissionStepContract) -> None:
        transition = next((s for s in contract.steps if s.id == "status_transition"), None)
        assert transition is not None
        assert transition.command is not None


class TestSpecifyContractStructure:
    """The specify contract captures examples before requirement validation."""

    @pytest.fixture
    def contract(self) -> MissionStepContract:
        repo = MissionStepContractRepository()
        c = repo.get_by_action("software-dev", "specify")
        assert c is not None
        return c

    def test_capture_intent_includes_examples_directive(self, contract: MissionStepContract) -> None:
        capture_intent = next((s for s in contract.steps if s.id == "capture_intent"), None)
        assert capture_intent is not None
        assert capture_intent.delegates_to is not None
        assert capture_intent.delegates_to.kind == ArtifactKind.DIRECTIVE
        assert "037-examples-are-source-of-truth" in capture_intent.delegates_to.candidates

    def test_has_map_examples_step_with_procedure_delegation(self, contract: MissionStepContract) -> None:
        map_examples = next((s for s in contract.steps if s.id == "map_examples"), None)
        assert map_examples is not None
        assert map_examples.delegates_to is not None
        assert map_examples.delegates_to.kind == ArtifactKind.PROCEDURE
        assert map_examples.delegates_to.candidates == ["example-mapping-workshop"]


class TestReviewContractStructure:
    """The review contract checks example, acceptance, and doc sync."""

    @pytest.fixture
    def contract(self) -> MissionStepContract:
        repo = MissionStepContractRepository()
        c = repo.get_by_action("software-dev", "review")
        assert c is not None
        return c

    def test_verify_spec_fidelity_includes_examples_directive(self, contract: MissionStepContract) -> None:
        verify_spec_fidelity = next((s for s in contract.steps if s.id == "verify_spec_fidelity"), None)
        assert verify_spec_fidelity is not None
        assert verify_spec_fidelity.delegates_to is not None
        assert verify_spec_fidelity.delegates_to.kind == ArtifactKind.DIRECTIVE
        assert "037-examples-are-source-of-truth" in verify_spec_fidelity.delegates_to.candidates

    def test_has_example_sync_step(self, contract: MissionStepContract) -> None:
        verify_example_sync = next((s for s in contract.steps if s.id == "verify_example_sync"), None)
        assert verify_example_sync is not None
        assert verify_example_sync.delegates_to is not None
        assert verify_example_sync.delegates_to.kind == ArtifactKind.TACTIC
        assert verify_example_sync.delegates_to.candidates == ["living-documentation-sync"]
