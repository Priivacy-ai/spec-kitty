"""Step contract executor for Phase 6 mission composition.

This executor is intentionally a composer, not a command runner or model
caller. It resolves step contract delegations through the merged DRG and then
routes each step through ``ProfileInvocationExecutor`` so the existing
governance context, trail, and glossary chokepoint behavior remains the single
invocation primitive.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from charter.pack_context import PackContext

from charter._drg_helpers import load_validated_graph
from charter.drg import (
    ArtifactKind,
    DRGGraph,
    DRGLoadError,
    NodeKind,
    OrgDRGFragment,
    OrgPackMissingError,
    OrgPackParseError,
    OrgPackSchemaError,
    ResolvedContext,
    filter_graph_by_activation,
    load_graph_or_dir,
    load_org_drg,
    load_org_pack,
    resolve_context,
    resolve_existing_org_roots,
    resolve_org_dirs,
)
from charter.mission_steps import (
    MissionStepContract,
    MissionStepContractRepository,
    MissionStepContractStep,
    MissionStepInput,
)
from specify_cli.invocation.executor import InvocationPayload, ProfileInvocationExecutor
from specify_cli.invocation.modes import ModeOfWork


logger = logging.getLogger(__name__)


_ARTIFACT_TO_NODE_KIND: dict[ArtifactKind, NodeKind] = {
    ArtifactKind.DIRECTIVE: NodeKind.DIRECTIVE,
    ArtifactKind.TACTIC: NodeKind.TACTIC,
    ArtifactKind.PARADIGM: NodeKind.PARADIGM,
    ArtifactKind.STYLEGUIDE: NodeKind.STYLEGUIDE,
    ArtifactKind.TOOLGUIDE: NodeKind.TOOLGUIDE,
    ArtifactKind.PROCEDURE: NodeKind.PROCEDURE,
    ArtifactKind.AGENT_PROFILE: NodeKind.AGENT_PROFILE,
    ArtifactKind.MISSION_STEP_CONTRACT: NodeKind.MISSION_STEP_CONTRACT,
    ArtifactKind.TEMPLATE: NodeKind.TEMPLATE,
    ArtifactKind.ASSET: NodeKind.ASSET,
    ArtifactKind.GLOSSARY_PACK: NodeKind.GLOSSARY_PACK,
}

# FR-008 / Phase 6 #505: this table is for built-in missions ONLY.
# Custom missions MUST resolve profile_hint via PromptStep.agent_profile;
# expanding this table for arbitrary custom missions is forbidden.
# See kitty-specs/local-custom-mission-loader-01KQ2VNJ/research.md §R-003.
_ACTION_PROFILE_DEFAULTS: dict[tuple[str, str], str] = {
    ("software-dev", "specify"): "researcher-robbie",
    ("software-dev", "plan"): "architect-alphonso",
    ("software-dev", "tasks"): "architect-alphonso",
    ("software-dev", "implement"): "implementer-ivan",
    ("software-dev", "review"): "reviewer-renata",
    ("research", "scoping"): "researcher-robbie",
    ("research", "methodology"): "researcher-robbie",
    ("research", "gathering"): "researcher-robbie",
    ("research", "synthesis"): "researcher-robbie",
    ("research", "output"): "reviewer-renata",
    ("documentation", "discover"): "researcher-robbie",
    ("documentation", "audit"): "researcher-robbie",
    ("documentation", "design"): "architect-alphonso",
    ("documentation", "generate"): "implementer-ivan",
    ("documentation", "validate"): "reviewer-renata",
    ("documentation", "publish"): "reviewer-renata",
    ("documentation", "accept"): "reviewer-renata",
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
    inputs: tuple[MissionStepInput, ...] = field(default_factory=tuple)
    resolved_delegations: tuple[ResolvedStepDelegation, ...] = field(default_factory=tuple)
    unresolved_candidates: tuple[str, ...] = field(default_factory=tuple)
    invocation_payload: InvocationPayload | None = None

    @property
    def invocation_id(self) -> str | None:
        """Return the underlying invocation ID when this step was invoked."""
        if self.invocation_payload is None:
            return None
        # InvocationPayload uses ``**kwargs: object`` + ``setattr`` for storage;
        # mypy --strict therefore widens attribute access to Any. The class-level
        # annotation pins it to ``str`` at runtime — narrow back explicitly so the
        # property's declared return type is honored without a blanket ignore.
        invocation_id: str = self.invocation_payload.invocation_id
        return invocation_id


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
        # #3525 Fold B: `resolve_org_dirs` (repository overlay) and this
        # executor's DRG load (`_load_graph_degrading_malformed_org_pack` ->
        # `load_validated_graph`, below) now share the SAME chain-aware,
        # later-declared-wins resolution over ALL existing org packs — the
        # C-004 first-match-only divergence this comment used to flag is
        # closed. Charter-build-time DRG callers remain intentionally
        # org-inert (see `load_validated_graph`'s docstring); this executor
        # is a runtime caller and always resolves the full chain.
        self._contracts = contract_repository or MissionStepContractRepository(
            project_dir=repo_root / ".kittify" / "doctrine" / "mission_step_contracts",
            org_dirs=resolve_org_dirs(repo_root, "mission_step_contracts"),
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
        # #3525 Fold B: resolve the FULL declaration-ordered org-pack chain
        # (mirrors charter/action_doctrine_bundle.py:_resolve_action_bundle),
        # not just the first configured pack.
        effective_org_roots = resolve_existing_org_roots(context.repo_root)
        graph = self._graph or self._load_graph_degrading_malformed_org_pack(
            context.repo_root, effective_org_roots
        )
        # FR-031, FR-033 (WP08): apply activation filter before resolving context.
        pack_context = self._resolve_pack_context(context.repo_root)
        if pack_context is not None:
            graph = filter_graph_by_activation(graph, pack_context)
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
                        inputs=tuple(step.inputs),
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
                    closed_by="agent",
                )
                raise
            else:
                # outcome describes the composition-step trail only; not host-LLM generation status.
                self._invocation_executor.complete_invocation(
                    payload.invocation_id, outcome="done", closed_by="agent"
                )

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

    @staticmethod
    def _load_graph_degrading_malformed_org_pack(
        repo_root: Path, org_roots: list[Path]
    ) -> DRGGraph:
        """Load the merged DRG, degrading any malformed root in *org_roots* to
        "no contribution from that pack" instead of letting it crash
        composition.

        Mirrors ``charter.action_doctrine_bundle._resolve_action_bundle``'s
        established handling of the same ``load_validated_graph(...,
        org_roots=...)`` call: a configured org pack whose on-disk DRG layout
        does not conform to ``load_graph_or_dir`` (no ``graph.yaml``/
        ``*.graph.yaml`` directly at its root -- this repo's own
        ``packs/internal`` is exactly this shape) must not turn every
        composition dispatch in the consuming project into a hard block.
        Before org-tier resolution was wired into this executor, such a
        misconfigured-but-registered pack was simply never exercised on this
        path, so its layout mismatch was inert; degrading here restores that
        "an optional tier being broken doesn't stop dispatch" behaviour
        without silencing the problem (D-005: WARNING, never silent --
        matches ``resolve_org_dirs``'s per-dropped-root warning and
        ``_resolve_expected_artifacts_slot``'s malformed-manifest warning,
        the same treatment already applied elsewhere in this mission for the
        same class of problem).

        #3525 Fold B — per-root degrade: each root in *org_roots* is
        independently probed (via ``load_graph_or_dir``, the same loader
        ``load_validated_graph`` uses internally for each root) BEFORE the
        chain-wide merge, so a malformed pack #2 drops ONLY pack #2 (one
        WARNING) while pack #1 -- and every other healthy root -- still
        contributes. This replaces the pre-fix all-or-nothing degrade, which
        collapsed the ENTIRE org tier the moment any single configured root
        failed to load.

        This degrade is deliberately narrow: when *org_roots* is empty (no
        org pack configured, or none exists on disk), any ``DRGLoadError``
        raised by the single ``load_validated_graph(repo_root, org_roots=[])``
        call below is a **built-in or project** layer failure and is left to
        propagate unchanged -- the no-org-pack path stays byte-identical to
        before this mission (no per-root probing runs at all). NFR-006's
        fail-closed posture for doctrine *content* correctness is untouched:
        a broken built-in graph, or a broken project overlay, still fails the
        dispatch outright. Only the optional org tier degrades, and only for
        the specific root(s) that actually failed to load.

        Do NOT drop this pre-probe on the assumption ``load_validated_graph``
        now covers it. As of PR #3534's landing that function skips a
        *graphless* root internally (a root with no root-level ``*.graph.yaml``
        -- it warns and contributes nothing), so for that specific shape this
        probe is redundant. But this probe additionally degrades a *malformed*
        root (a present-but-invalid root-level ``*.graph.yaml``), which
        ``load_validated_graph`` deliberately still lets fail loud. Removing it
        would reopen the malformed-content crash on this dispatch path.
        """
        # #3530: the org ``drg/fragment.yaml`` layer is loaded ONCE here and
        # threaded into every ``load_validated_graph`` branch below, mirroring
        # the four correct dual-callers (``review/gate_bindings.py``,
        # ``cli/commands/charter/{activate,deactivate}.py``). Without it a pack
        # shipping only a ``drg/fragment.yaml`` (this repo's own
        # ``packs/internal`` shape) is dropped on this dispatch path -- the
        # branch-named silent drop this WP closes.
        org_fragments = StepContractExecutor._load_org_fragments_degrading(repo_root)
        if not org_roots:
            return load_validated_graph(
                repo_root, org_roots=[], org_fragments=org_fragments
            )

        healthy_roots: list[Path] = []
        for root in org_roots:
            try:
                load_graph_or_dir(root)
            except DRGLoadError as exc:
                StepContractExecutor._warn_dropped_org_root(root, exc)
                continue
            healthy_roots.append(root)

        return load_validated_graph(
            repo_root, org_roots=healthy_roots, org_fragments=org_fragments
        )

    @staticmethod
    def _load_org_fragments_degrading(repo_root: Path) -> list[OrgDRGFragment]:
        """Load the org ``drg/fragment.yaml`` layer, degrading on a bad pack.

        Threads ``load_org_drg(repo_root, strict=False)`` -- the exact call the
        four correct dual-callers use -- so a fragment-shaped org pack reaches
        this composition-dispatch path. ``strict=False`` skips a pack that ships
        no ``drg/fragment.yaml`` (its root ``*.graph.yaml``, if any, is folded by
        the ``org_roots`` loop instead). A pack whose fragment is present but
        malformed raises here; catch it and degrade to an empty fragment layer
        so a broken optional org tier does not crash the whole dispatch. This is
        DEBUG rather than WARNING because the same broken root also fails the
        root-graph pre-probe below, whose per-root WARNING is the operator's
        signal that the pack was dropped (see :meth:`_warn_dropped_org_root`).
        """
        try:
            # Typed local absorbs the ``charter.drg`` facade re-export (mypy sees
            # the facade symbol as ``Any``); the annotation restores the concrete
            # return type without a suppression.
            fragments: list[OrgDRGFragment] = load_org_drg(repo_root, strict=False)
            return fragments
        except (OrgPackMissingError, OrgPackParseError, OrgPackSchemaError, NotImplementedError) as exc:
            logger.debug(
                "Org drg/fragment.yaml layer failed to load (%s: %s); composing "
                "this step without the org-fragment contribution.",
                type(exc).__name__,
                exc,
            )
            return []

    @staticmethod
    def _warn_dropped_org_root(root: Path, exc: DRGLoadError) -> None:
        """Warn (honestly) that *root* was dropped from the root-graph loop.

        #3530 warning honesty: a *fragment-shaped* org pack (a valid
        ``drg/fragment.yaml`` and no root-level ``*.graph.yaml`` -- this repo's
        own ``packs/internal`` is exactly this shape) cannot be read by
        ``load_graph_or_dir`` (root graphs only), but its content DOES arrive via
        the ``org_fragments`` layer. Emitting the "without this org pack's
        contribution" WARNING for it would misattribute a folded pack as a
        dropped one, so degrade to a DEBUG note. A root that fails to load AND
        contributes no valid fragment (a present-but-invalid root graph, or a
        root with neither a graph nor a loadable fragment) is genuinely lost and
        still WARNs.
        """
        if StepContractExecutor._org_root_folds_fragment(root):
            logger.debug(
                "Org pack DRG at %s ships a drg/fragment.yaml and no root "
                "*.graph.yaml; folding it via the org-fragment layer rather "
                "than the root-graph loop.",
                root,
            )
            return
        logger.warning(
            "Org pack DRG at %s failed to load (%s: %s); composing this "
            "step with the remaining doctrine layers, without this "
            "org pack's contribution.",
            root,
            type(exc).__name__,
            exc,
        )

    @staticmethod
    def _org_root_folds_fragment(root: Path) -> bool:
        """True iff *root* ships a ``drg/fragment.yaml`` that loads cleanly.

        Distinguishes a *folded* fragment-shaped pack (whose content reaches the
        merged graph via the org-fragment layer) from a genuinely lost root, so
        the pre-probe's degrade WARNING stays honest. The ``pack_name``/
        ``layer_index`` passed here only affect labelling, not whether the
        fragment parses, so a probe-local name and index are sufficient.
        """
        if not (root / "drg" / "fragment.yaml").is_file():
            return False
        try:
            load_org_pack(root.name, root, 1)
        except (OrgPackMissingError, OrgPackParseError, OrgPackSchemaError, NotImplementedError):
            return False
        return True

    def _resolve_pack_context(self, repo_root: Path) -> PackContext | None:
        """Construct a PackContext from project config for activation filtering.

        FR-031, FR-033 (WP08): Obtain pack_context from project config so the
        activation filter can narrow the DRG before context resolution.
        Returns ``None`` on any error so the filter is always optional.
        """
        from charter.drg import (
            OrgPackEnvVarUnsetError,
            OrgPackSubdirEscapeError,
        )

        try:
            from charter.pack_context import PackContext  # noqa: PLC0415

            return PackContext.from_config(repo_root)
        except (OrgPackEnvVarUnsetError, OrgPackSubdirEscapeError):
            # Fail closed (FR-003): an unset env var or a symlink-escape is
            # operator-actionable, not "activation filter unavailable" —
            # silently degrading here would run the mission-step DRG
            # unfiltered instead of surfacing the real config problem.
            raise
        except Exception:  # noqa: BLE001 — defensive; activation filter is optional
            return None

    def _resolve_step_delegations(
        self,
        *,
        graph: DRGGraph,
        action_context: ResolvedContext,
        step: MissionStepContractStep,
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

        matches: list[str] = [
            str(node.urn)
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
        step: MissionStepContractStep,
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
            lines.append(f"Declared command: {self._render_declared_command(step)}")
            lines.append("Command status: declared only; the host/operator owns execution.")
        elif step.inputs:
            joined = " ".join(
                self._format_step_input(input_spec) for input_spec in step.inputs
            )
            lines.append(f"Declared step inputs: {joined}")
        if resolved_delegations:
            joined = ", ".join(delegation.urn for delegation in resolved_delegations)
            lines.append(f"Resolved delegations: {joined}")
        if unresolved_candidates:
            joined = ", ".join(unresolved_candidates)
            lines.append(f"Unresolved delegation candidates: {joined}")
        if step.guidance:
            lines.append(f"Step guidance: {step.guidance}")
        return "\n".join(lines)

    def _render_declared_command(self, step: MissionStepContractStep) -> str:
        if not step.command or not step.inputs:
            return step.command or ""
        joined = " ".join(
            self._format_step_input(input_spec) for input_spec in step.inputs
        )
        return f"{step.command} {joined}"

    @staticmethod
    def _format_step_input(input_spec: MissionStepInput) -> str:
        rendered = f"{input_spec.flag} {{{input_spec.source}}}"
        if input_spec.optional:
            return f"[{rendered}]"
        return rendered


__all__ = [
    "ResolvedStepDelegation",
    "StepContractExecutionContext",
    "StepContractExecutionError",
    "StepContractExecutionResult",
    "StepContractExecutor",
    "StepContractStepResult",
]
