"""Slash-command (``command_file`` kind) surface provider.

Wraps the existing global slash-command directory machinery
(:data:`specify_cli.core.config.AGENT_COMMAND_CONFIG` and
:mod:`specify_cli.runtime.agent_commands`) as a reporting-layer provider. Slash
command files live in a **user-global** command directory, not in the project,
so the instance paths are absolute and findings make the global location clear.

Agents that have no command-file adapter (no ``AGENT_COMMAND_CONFIG`` entry)
yield a single ``research-gap-surface`` instance instead of being silently
treated as healthy.
"""

from __future__ import annotations

from collections.abc import Sequence
import logging
from pathlib import Path
from contextlib import AbstractContextManager
from dataclasses import replace

from ..enums import (
    ActivationMode,
    InstallScope,
    RequiredPolicy,
    SourceKind,
    ToolSurfaceKind,
)
from ..findings import (
    GENERATED_SURFACE_MISSING,
    RESEARCH_GAP_SURFACE,
    SEVERITY_ERROR,
    SEVERITY_INFO,
    SEVERITY_WARNING,
    STALE_GENERATED_SURFACE,
    make_finding,
)
from ..model import SurfaceDefinition, SurfaceInstance, SurfaceSelection
from ..operations import ApplyConsent, AssessmentInputs, Diagnostic, Disposition, InputObservation, OwnerApplyResult, OwnerAssessment
from ..repair import RepairResult
from ..status import (
    STATE_MISSING,
    STATE_NOT_APPLICABLE,
    STATE_PRESENT,
    STATE_STALE,
    STATE_UNSUPPORTED,
    SurfaceStatus,
    _surface_id,
)
from ._registry import SurfaceProviderRegistry, SurfaceRegistration

logger = logging.getLogger(__name__)

PROVIDER_KEY = "slash_commands"
_PATH_PATTERN = "<user-global>/spec-kitty.{command}"
_REPAIR_HINT = "spec-kitty doctor tool-surfaces --kind command-file --fix"
_RESEARCH_GAP_SENTINEL = "<unsupported>"


def slash_command_definition() -> SurfaceDefinition:
    """Return the built-in slash-command :class:`SurfaceDefinition`."""
    return SurfaceDefinition(
        kind=ToolSurfaceKind.COMMAND_FILE,
        source_kind=SourceKind.USER_GLOBAL,
        install_scope=InstallScope.USER_GLOBAL,
        path_pattern=_PATH_PATTERN,
        required_policy=RequiredPolicy.REPAIRABLE_REQUIRED,
        activation_mode=ActivationMode.USER_INVOKED,
        provider_key=PROVIDER_KEY,
        repair_hint=_REPAIR_HINT,
    )


class SlashCommandsProvider:
    """Provider for user-global slash-command files."""

    provider_key = PROVIDER_KEY

    def assess(
        self,
        inputs: AssessmentInputs,
        statuses: Sequence[SurfaceStatus],
        *,
        selections: tuple[SurfaceSelection, ...],
    ) -> OwnerAssessment:
        """Delegate canonical selection, including empty expansion, to runtime."""
        from specify_cli.core.config import AGENT_COMMAND_CONFIG
        from specify_cli.runtime.agent_commands import assess_global_agent_commands

        enabled = tuple(s for s in selections if s.definition.activation_mode != ActivationMode.DISABLED)
        keys = sorted({s.tool_key for s in enabled if s.tool_key in AGENT_COMMAND_CONFIG})
        if not keys:
            return OwnerAssessment(
                PROVIDER_KEY,
                inputs.root,
                dispositions=(Disposition(PROVIDER_KEY, inputs.root.root_id, None, "not_applicable", "No enabled command-file adapter selected"),),
            )
        assessment = assess_global_agent_commands(agent_keys=keys, consent=inputs.consent)
        effects = tuple(
            replace(effect, surface_ids=tuple(_surface_id(s.instance) for s in statuses if s.instance.owner in effect.logical_owners))
            for effect in assessment.effects
        )
        return replace(
            assessment,
            root=inputs.root,
            effects=effects,
            inputs_fingerprint=assessment.inputs_fingerprint
            + (
                InputObservation("caller_inputs", inputs),
                InputObservation("selections", selections),
                InputObservation("provider_instances", tuple((s.instance, s.state) for s in statuses)),
            ),
        )

    def recheck(self, assessment: OwnerAssessment) -> AbstractContextManager[tuple[Diagnostic, ...]]:
        """Hold the runtime owner's lock over whole-batch validation and apply."""
        from specify_cli.runtime.asset_preparation import recheck_assets

        return recheck_assets(assessment)

    def apply(self, assessment: OwnerAssessment, explicit_consent: ApplyConsent) -> OwnerApplyResult:
        """Apply retained global bytes, converging on a concurrent peer's own materialization.

        #4174 landing-pass: dispatched through ``tool_surface/repair.py``'s
        generic ``_apply_assessment`` (via ``SurfaceRepairService``), which
        calls ``recheck()`` then this method on the SAME stale *assessment*
        -- there was no re-assess seam here either, so two independent,
        concurrent repair-service invocations racing the same cold home
        reproduced the identical residual symptom the other #4174 external
        callers had: a ``global_asset_write_failed: File exists`` when the
        winner already materialized the tree.

        The rebuild is derived purely from *assessment*'s OWN effects
        (``logical_owners``, set by ``assess()`` from the selected agent
        keys) -- this method never receives the original ``inputs`` /
        ``selections`` ``assess()`` used, so it cannot call that directly.
        """
        from specify_cli.runtime.agent_commands import assess_global_agent_commands
        from specify_cli.runtime.asset_preparation import apply_assets, apply_with_reassess

        if not assessment.effects:
            return apply_assets(assessment, explicit_consent)
        keys = sorted({owner for effect in assessment.effects for owner in effect.logical_owners})

        def _rebuild() -> OwnerAssessment:
            return assess_global_agent_commands(agent_keys=keys, consent=assessment.consent)

        result = apply_with_reassess(
            assessment,
            _rebuild,
            explicit_consent,
            converged_log_message="global slash commands already materialized by a concurrent peer; nothing applied.",
            logger=logger,
        )
        if result.outcome == "skipped":
            # asset_preparation.apply_with_reassess's converged-no-op branch
            # reports no ids at all (fine for the ensure_*() owners it was
            # extracted from). repair.py's _apply_assessment enforces a
            # stricter contract than those direct-call owners: every id in
            # the ORIGINAL assessment's effects must be reported in the
            # OwnerApplyResult, or it downgrades to a failed
            # "unreported_effects" diagnostic. Remap the converged result to
            # report those original ids as skipped.
            return replace(result, skipped=tuple(effect.id for effect in assessment.effects))
        return result

    def can_handle(self, definition: SurfaceDefinition) -> bool:
        return bool(definition.kind == ToolSurfaceKind.COMMAND_FILE)

    def expand(
        self,
        definition: SurfaceDefinition,
        tool_key: str,
        project_root: Path,
    ) -> list[SurfaceInstance]:
        """Expand into one instance per command for a slash-command agent."""
        from specify_cli.core.config import AGENT_COMMAND_CONFIG

        _ = project_root  # slash commands are user-global; project root unused
        if AGENT_COMMAND_CONFIG.get(tool_key) is None:
            return [self._research_gap_instance(definition, tool_key)]
        return self._command_instances(definition, tool_key)

    @staticmethod
    def _research_gap_instance(definition: SurfaceDefinition, tool_key: str) -> SurfaceInstance:
        return SurfaceInstance(
            definition=definition,
            path=Path(_RESEARCH_GAP_SENTINEL),
            exists=False,
            file_hash=None,
            owner=tool_key,
        )

    @staticmethod
    def _command_instances(definition: SurfaceDefinition, tool_key: str) -> list[SurfaceInstance]:
        from specify_cli.runtime.agent_commands import (
            _compute_output_filename,
            get_global_command_dir,
        )
        from specify_cli.shims.registry import (
            CLI_DRIVEN_COMMANDS,
            PROMPT_DRIVEN_COMMANDS,
        )

        cmd_dir = get_global_command_dir(tool_key)
        instances: list[SurfaceInstance] = []
        for command in sorted(PROMPT_DRIVEN_COMMANDS | CLI_DRIVEN_COMMANDS):
            path = cmd_dir / _compute_output_filename(command, tool_key)
            instances.append(
                SurfaceInstance(
                    definition=definition,
                    path=path,
                    exists=path.exists(),
                    file_hash=None,
                    owner=tool_key,
                )
            )
        return instances

    def probe(self, instance: SurfaceInstance) -> SurfaceStatus:
        """Probe a slash-command file against the current version marker."""
        if str(instance.path) == _RESEARCH_GAP_SENTINEL:
            return self._research_gap_status(instance)
        if not instance.path.exists():
            return self._missing_status(instance)
        if self._is_stale(instance.path):
            return self._stale_status(instance)
        return SurfaceStatus(instance=instance, state=STATE_PRESENT)

    @staticmethod
    def _is_stale(path: Path) -> bool:
        from specify_cli.runtime.agent_commands import (
            _VERSION_MARKER_HEAD_LINES,
            _VERSION_MARKER_PREFIX,
        )
        from specify_cli.runtime.bootstrap import _get_cli_version

        try:
            head = "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[:_VERSION_MARKER_HEAD_LINES])
        except OSError:
            return False
        return f"{_VERSION_MARKER_PREFIX} {_get_cli_version()}" not in head

    @staticmethod
    def _research_gap_status(instance: SurfaceInstance) -> SurfaceStatus:
        return SurfaceStatus(
            instance=instance,
            state=STATE_NOT_APPLICABLE,
            findings=(
                make_finding(
                    RESEARCH_GAP_SURFACE,
                    SEVERITY_INFO,
                    f"No known slash-command implementation for {instance.owner}.",
                    tool_key=instance.owner,
                    surface_id=_surface_id(instance),
                ),
            ),
        )

    @staticmethod
    def _missing_status(instance: SurfaceInstance) -> SurfaceStatus:
        return SurfaceStatus(
            instance=instance,
            state=STATE_MISSING,
            findings=(
                make_finding(
                    GENERATED_SURFACE_MISSING,
                    SEVERITY_ERROR,
                    f"User-global slash command missing: {instance.path}",
                    tool_key=instance.owner,
                    surface_id=_surface_id(instance),
                    path=instance.path,
                    repair_command=_REPAIR_HINT,
                ),
            ),
        )

    @staticmethod
    def _stale_status(instance: SurfaceInstance) -> SurfaceStatus:
        return SurfaceStatus(
            instance=instance,
            state=STATE_STALE,
            findings=(
                make_finding(
                    STALE_GENERATED_SURFACE,
                    SEVERITY_WARNING,
                    f"User-global slash command is stale: {instance.path}",
                    tool_key=instance.owner,
                    surface_id=_surface_id(instance),
                    path=instance.path,
                    repair_command=_REPAIR_HINT,
                ),
            ),
        )

    def remove(self, instance: SurfaceInstance) -> bool:
        """Removal of user-global slash commands is not in scope for repair.

        User-global command files are shared across projects, so this provider
        never deletes them as part of the surface contract. Returns ``False``
        to signal that no removal was performed.
        """
        _ = instance
        return False

    def repair(
        self,
        project_root: Path,
        statuses: Sequence[SurfaceStatus],
        *,
        dry_run: bool = False,
    ) -> RepairResult:
        """Regenerate user-global slash commands for affected agents."""
        _ = project_root  # slash commands are user-global; project root unused
        actionable = [s for s in statuses if s.state in (STATE_MISSING, STATE_STALE)]
        if not actionable:
            return RepairResult(dry_run=dry_run)
        skipped = tuple(_surface_id(s.instance) for s in statuses if s.state == STATE_UNSUPPORTED)
        if dry_run:
            return RepairResult(
                repaired=tuple(_surface_id(s.instance) for s in actionable),
                skipped=skipped,
                dry_run=True,
            )
        return self._regenerate(actionable, skipped)

    @staticmethod
    def _regenerate(
        actionable: Sequence[SurfaceStatus],
        skipped: tuple[str, ...],
    ) -> RepairResult:
        from specify_cli.runtime.agent_commands import ensure_global_agent_commands

        repaired: list[str] = []
        failed: list[str] = []
        agents = sorted({s.instance.owner for s in actionable})
        for agent in agents:
            try:
                ensure_global_agent_commands(agent_keys=[agent])
                repaired.extend(_surface_id(s.instance) for s in actionable if s.instance.owner == agent)
            except Exception as exc:  # surfaced as a failure, never swallowed
                failed.append(f"{agent}: {exc}")
        return RepairResult(
            repaired=tuple(repaired),
            skipped=skipped,
            failed=tuple(failed),
            dry_run=False,
        )


# ---------------------------------------------------------------------------
# Self-registration (fires at import time via providers._discovery)
# ---------------------------------------------------------------------------
SurfaceProviderRegistry.register(
    SurfaceRegistration(
        provider_class=SlashCommandsProvider,
        definitions=(slash_command_definition(),),
        kind_tokens={"command-file": ToolSurfaceKind.COMMAND_FILE},
        order=10,
    )
)
