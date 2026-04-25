"""Step contract executor for Phase 6 mission composition.

This executor is intentionally a composer, not a command runner or model
caller. It resolves step contract delegations through the merged DRG and then
routes each step through ``ProfileInvocationExecutor`` so the existing
governance context, trail, and glossary chokepoint behavior remains the single
invocation primitive.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from charter._drg_helpers import load_validated_graph
from doctrine.artifact_kinds import ArtifactKind
from doctrine.drg.models import DRGGraph, NodeKind
from doctrine.drg.query import ResolvedContext, resolve_context
from doctrine.mission_step_contracts.models import MissionStep, MissionStepContract
from doctrine.mission_step_contracts.repository import MissionStepContractRepository
from specify_cli.invocation.executor import InvocationPayload, ProfileInvocationExecutor
from specify_cli.invocation.modes import ModeOfWork


_ARTIFACT_TO_NODE_KIND: dict[ArtifactKind, NodeKind] = {
    ArtifactKind.DIRECTIVE: NodeKind.DIRECTIVE,
    ArtifactKind.TACTIC: NodeKind.TACTIC,
    ArtifactKind.PARADIGM: NodeKind.PARADIGM,
    ArtifactKind.STYLEGUIDE: NodeKind.STYLEGUIDE,
    ArtifactKind.TOOLGUIDE: NodeKind.TOOLGUIDE,
    ArtifactKind.PROCEDURE: NodeKind.PROCEDURE,
    ArtifactKind.AGENT_PROFILE: NodeKind.AGENT_PROFILE,
}

_ACTION_PROFILE_DEFAULTS: dict[tuple[str, str], str] = {
    ("software-dev", "specify"): "researcher-robbie",
    ("software-dev", "plan"): "architect-alphonso",
    ("software-dev", "tasks"): "architect-alphonso",
    ("software-dev", "implement"): "implementer-ivan",
    ("software-dev", "review"): "reviewer-renata",
}


class StepContractExecutionError(RuntimeError):
    """Raised when a step contract run cannot be composed."""


@dataclass(frozen=True)
class StepContractExecutionContext:
    """Minimal context needed to execute a mission step contract."""

    repo_root: Path
    mission: str
    action: str
    actor: str = "unknown"
    profile_hint: str | None = None
    request_text: str | None = None
    mode_of_work: ModeOfWork | None = None
    resolution_depth: int = 2


@dataclass(frozen=True)
class ResolvedStepDelegation:
    """A delegation candidate selected through merged DRG resolution."""

    kind: ArtifactKind
    candidate: str
    urn: str
    label: str | None = None


@dataclass(frozen=True)
class StepContractStepResult:
    """Structured result for one composed step invocation."""

    step_id: str
    sequence: int
    description: str
    command: str | None
    command_declared: bool
    guidance: str | None
    resolved_delegations: tuple[ResolvedStepDelegation, ...] = field(default_factory=tuple)
    unresolved_candidates: tuple[str, ...] = field(default_factory=tuple)
    invocation_payload: InvocationPayload | None = None

    @property
    def invocation_id(self) -> str | None:
        """Return the underlying invocation ID when this step was invoked."""
        if self.invocation_payload is None:
            return None
        return self.invocation_payload.invocation_id


@dataclass(frozen=True)
class StepContractExecutionResult:
    """Structured result for a complete step contract run."""

    contract_id: str
    mission: str
    action: str
    profile_hint: str
    resolution_source: str
    steps: tuple[StepContractStepResult, ...]

    @property
    def invocation_ids(self) -> tuple[str, ...]:
        """Return all invocation IDs emitted by the composed run."""
        ids: list[str] = []
        for step in self.steps:
            invocation_id = step.invocation_id
            if invocation_id is not None:
                ids.append(invocation_id)
        return tuple(ids)


class StepContractExecutor:
    """Execute mission step contracts by composing profile invocations."""

    def __init__(
        self,
        *,
        repo_root: Path,
        contract_repository: MissionStepContractRepository | None = None,
        invocation_executor: ProfileInvocationExecutor | None = None,
        graph: DRGGraph | None = None,
    ) -> None:
        self._repo_root = repo_root
        self._contracts = contract_repository or MissionStepContractRepository(
            project_dir=repo_root / ".kittify" / "doctrine" / "mission_step_contracts"
        )
        self._invocation_executor = invocation_executor or ProfileInvocationExecutor(repo_root)
        self._graph = graph

    def execute(
        self,
        context: StepContractExecutionContext,
        contract: MissionStepContract | None = None,
    ) -> StepContractExecutionResult:
        """Execute a contract's steps in order through ``ProfileInvocationExecutor``."""
        selected_contract = contract or self._contracts.get_by_action(context.mission, context.action)
        if selected_contract is None:
            raise StepContractExecutionError(
                f"No step contract found for mission/action {context.mission}/{context.action}"
            )

        profile_hint = self._resolve_profile_hint(context, selected_contract)
        graph = self._graph or load_validated_graph(context.repo_root)
        action_urn = f"action:{selected_contract.mission}/{selected_contract.action}"
        action_context = resolve_context(graph, action_urn, depth=context.resolution_depth)

        step_results: list[StepContractStepResult] = []
        for sequence, step in enumerate(selected_contract.steps, start=1):
            resolved, unresolved = self._resolve_step_delegations(
                graph=graph,
                action_context=action_context,
                step=step,
            )
            payload = self._invocation_executor.invoke(
                self._build_request_text(
                    contract=selected_contract,
                    context=context,
                    step=step,
                    resolved_delegations=resolved,
                    unresolved_candidates=unresolved,
                ),
                profile_hint=profile_hint,
                actor=context.actor,
                mode_of_work=context.mode_of_work,
                action_hint=selected_contract.action,
            )
            try:
                step_results.append(
                    StepContractStepResult(
                        step_id=step.id,
                        sequence=sequence,
                        description=step.description,
                        command=step.command,
                        command_declared=step.command is not None,
                        guidance=step.guidance,
                        resolved_delegations=tuple(resolved),
                        unresolved_candidates=tuple(unresolved),
                        invocation_payload=payload,
                    )
                )
            except Exception:
                self._invocation_executor.complete_invocation(
                    payload.invocation_id,
                    outcome="failed",
                )
                raise
            else:
                # outcome describes the composition-step trail only; not host-LLM generation status.
                self._invocation_executor.complete_invocation(payload.invocation_id, outcome="done")

        return StepContractExecutionResult(
            contract_id=selected_contract.id,
            mission=selected_contract.mission,
            action=selected_contract.action,
            profile_hint=profile_hint,
            resolution_source="merged_drg",
            steps=tuple(step_results),
        )

    def _resolve_profile_hint(
        self,
        context: StepContractExecutionContext,
        contract: MissionStepContract,
    ) -> str:
        if context.profile_hint:
            return context.profile_hint
        default = _ACTION_PROFILE_DEFAULTS.get((contract.mission, contract.action))
        if default is not None:
            return default
        raise StepContractExecutionError(
            "profile_hint is required when no action default exists for "
            f"{contract.mission}/{contract.action}"
        )

    def _resolve_step_delegations(
        self,
        *,
        graph: DRGGraph,
        action_context: ResolvedContext,
        step: MissionStep,
    ) -> tuple[list[ResolvedStepDelegation], list[str]]:
        if step.delegates_to is None:
            return [], []

        kind = step.delegates_to.kind
        resolved: list[ResolvedStepDelegation] = []
        unresolved: list[str] = []
        selected_urns = action_context.artifact_urns

        for candidate in step.delegates_to.candidates:
            urn = self._candidate_urn(graph, kind, candidate)
            if urn is None or urn not in selected_urns:
                unresolved.append(candidate)
                continue
            node = graph.get_node(urn)
            resolved.append(
                ResolvedStepDelegation(
                    kind=kind,
                    candidate=candidate,
                    urn=urn,
                    label=node.label if node is not None else None,
                )
            )
        return resolved, unresolved

    def _candidate_urn(
        self,
        graph: DRGGraph,
        kind: ArtifactKind,
        candidate: str,
    ) -> str | None:
        node_kind = _ARTIFACT_TO_NODE_KIND.get(kind)
        if node_kind is None:
            return None

        direct = f"{kind.value}:{candidate}"
        direct_node = graph.get_node(direct)
        if direct_node is not None and direct_node.kind == node_kind:
            return direct

        directive_urn = self._directive_candidate_urn(candidate) if kind == ArtifactKind.DIRECTIVE else None
        if directive_urn is not None:
            directive_node = graph.get_node(directive_urn)
            if directive_node is not None and directive_node.kind == node_kind:
                return directive_urn

        matches = [
            node.urn
            for node in graph.nodes
            if node.kind == node_kind and node.urn.split(":", 1)[1] == candidate
        ]
        if len(matches) == 1:
            return matches[0]
        return None

    @staticmethod
    def _directive_candidate_urn(candidate: str) -> str | None:
        numeric = ""
        for char in candidate:
            if not char.isdigit():
                break
            numeric += char
        if not numeric:
            return None
        return f"directive:DIRECTIVE_{numeric.zfill(3)}"

    def _build_request_text(
        self,
        *,
        contract: MissionStepContract,
        context: StepContractExecutionContext,
        step: MissionStep,
        resolved_delegations: list[ResolvedStepDelegation],
        unresolved_candidates: list[str],
    ) -> str:
        lines = [
            f"Execute mission step contract {contract.id} ({contract.mission}/{contract.action}).",
            f"Step {step.id}: {step.description}",
        ]
        if context.request_text:
            lines.append(f"Run request: {context.request_text}")
        if step.command:
            lines.append(f"Declared command: {step.command}")
            lines.append("Command status: declared only; the host/operator owns execution.")
        if resolved_delegations:
            joined = ", ".join(delegation.urn for delegation in resolved_delegations)
            lines.append(f"Resolved delegations: {joined}")
        if unresolved_candidates:
            joined = ", ".join(unresolved_candidates)
            lines.append(f"Unresolved delegation candidates: {joined}")
        if step.guidance:
            lines.append(f"Step guidance: {step.guidance}")
        return "\n".join(lines)


__all__ = [
    "ResolvedStepDelegation",
    "StepContractExecutionContext",
    "StepContractExecutionError",
    "StepContractExecutionResult",
    "StepContractExecutor",
    "StepContractStepResult",
]
