"""Native agent profile surface provider.

Wires :class:`~specify_cli.tool_surface.profiles.projection.ProfileProjector`
and :class:`~specify_cli.tool_surface.profiles.manifest.ProfileManifest` into a
reporting-layer provider for :data:`SurfaceKind.AGENT_PROFILE`.

Behavioural contract (FR-012/013/014):

* Tools with a native named-agent primitive (Claude Code, Copilot/VS Code,
  Codex, Augment, Amazon Q) expand to one instance per projected profile and
  are repairable.  Amazon Q profiles are user-global (not manifest-tracked);
  their presence is checked via filesystem inspection.
* Tools assessed as having no native primitive (e.g. Windsurf, Cursor) expand
  to a single ``not_applicable`` instance whose finding is
  ``profile-projection-unsupported`` at severity ``info`` -- the top-level
  ``ok`` stays ``true`` because no ``error`` finding is produced.
* Tools that have not yet been formally assessed yield a ``research_gap``
  instance with finding ``research-gap-surface`` at severity ``info``.
* A projected file that is configured but missing is an ``error``
  (``native-agent-profile-missing``); a file whose content no longer matches the
  manifest hash is a ``warning`` (``native-agent-profile-drift``).
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from ..enums import (
    ActivationMode,
    InstallScope,
    RequiredPolicy,
    SourceKind,
    SurfaceKind,
)
from ..findings import (
    NATIVE_AGENT_PROFILE_DRIFT,
    NATIVE_AGENT_PROFILE_MISSING,
    PROFILE_PROJECTION_UNSUPPORTED,
    RESEARCH_GAP_SURFACE,
    SEVERITY_ERROR,
    SEVERITY_INFO,
    SEVERITY_WARNING,
    make_finding,
)
from ..model import NativeAgentProfile, SurfaceDefinition, SurfaceInstance
from ..profiles.amazon_q_renderer import FORMAT_AMAZON_Q_AGENT
from ..profiles.capability_matrix import HARNESS_CAPABILITY_MATRIX, is_research_gap
from ..profiles.manifest import ProfileManifest, hash_content, hash_file
from ..profiles.projection import ProfileProjector, default_profile_repository
from ..repair import RepairResult
from ..status import (
    STATE_DRIFTED,
    STATE_MISSING,
    STATE_NOT_APPLICABLE,
    STATE_PRESENT,
    STATE_UNSUPPORTED,
    SurfaceStatus,
    _surface_id,
)

PROVIDER_KEY = "agent_profiles"
_PATH_PATTERN = ".claude/agents/{profile_id}.md"
_REPAIR_HINT = "spec-kitty doctor tool-surfaces --kind agent-profile --fix"
# Sentinel paths used to route probe() without holding real filesystem paths.
_RESEARCH_GAP_SENTINEL = "<unsupported>"
_NOT_APPLICABLE_SENTINEL = "<not-applicable>"


def agent_profile_definition() -> SurfaceDefinition:
    """Return the built-in agent-profile :class:`SurfaceDefinition`."""
    return SurfaceDefinition(
        kind=SurfaceKind.AGENT_PROFILE,
        source_kind=SourceKind.GENERATED,
        install_scope=InstallScope.PROJECT,
        path_pattern=_PATH_PATTERN,
        required_policy=RequiredPolicy.REPAIRABLE_REQUIRED,
        activation_mode=ActivationMode.USER_INVOKED,
        provider_key=PROVIDER_KEY,
        repair_hint=_REPAIR_HINT,
    )


def _build_projector(project_root: Path) -> ProfileProjector:
    return ProfileProjector(default_profile_repository(project_root))


class AgentProfilesProvider:
    """Provider for projected native agent profile surfaces."""

    provider_key = PROVIDER_KEY

    def __init__(
        self,
        projector: ProfileProjector | None = None,
        manifest: ProfileManifest | None = None,
    ) -> None:
        # ``projector``/``manifest`` are injectable for tests; in production they
        # are built per ``project_root`` inside ``expand``/``repair`` so the
        # provider stays usable as a stateless singleton in the service wiring.
        self._projector = projector
        self._manifest = manifest

    def can_handle(self, definition: SurfaceDefinition) -> bool:
        return definition.kind == SurfaceKind.AGENT_PROFILE

    def _projector_for(self, project_root: Path) -> ProfileProjector:
        return self._projector or _build_projector(project_root)

    def _manifest_for(self, project_root: Path) -> ProfileManifest:
        return self._manifest or ProfileManifest.load(project_root)

    def expand(
        self,
        definition: SurfaceDefinition,
        tool_key: str,
        project_root: Path,
    ) -> list[SurfaceInstance]:
        """Expand into one instance per projected profile for ``tool_key``.

        Uses :data:`~.profiles.capability_matrix.HARNESS_CAPABILITY_MATRIX` to
        distinguish ``not_applicable`` (assessed, no native primitive) from
        ``research_gap`` (not yet assessed) before attempting projection.
        """
        record = HARNESS_CAPABILITY_MATRIX.get(tool_key)
        if record is not None and not record.has_native_agent_primitive:
            return [self._not_applicable_instance(definition, tool_key)]
        projector = self._projector_for(project_root)
        projected = projector.project(tool_key, project_root)
        if not projected:
            # Tool is assessed as capable but the projector returned nothing —
            # this occurs when no renderer is registered yet, which is a
            # research gap (the capability matrix may be ahead of the renderer
            # registry).
            if is_research_gap(tool_key):
                return [self._research_gap_instance(definition, tool_key)]
            return [self._research_gap_instance(definition, tool_key)]
        manifest = self._manifest_for(project_root)
        return [
            self._instance_from_projection(definition, native, manifest)
            for native in projected
        ]

    @staticmethod
    def _not_applicable_instance(
        definition: SurfaceDefinition, tool_key: str
    ) -> SurfaceInstance:
        """Return a sentinel instance representing a ``not_applicable`` harness."""
        return SurfaceInstance(
            definition=definition,
            path=Path(_NOT_APPLICABLE_SENTINEL),
            exists=False,
            file_hash=None,
            owner=tool_key,
        )

    @staticmethod
    def _research_gap_instance(
        definition: SurfaceDefinition, tool_key: str
    ) -> SurfaceInstance:
        return SurfaceInstance(
            definition=definition,
            path=Path(_RESEARCH_GAP_SENTINEL),
            exists=False,
            file_hash=None,
            owner=tool_key,
        )

    @staticmethod
    def _instance_from_projection(
        definition: SurfaceDefinition,
        native: NativeAgentProfile,
        manifest: ProfileManifest,
    ) -> SurfaceInstance:
        path = native.output_path
        return SurfaceInstance(
            definition=definition,
            path=path,
            exists=path.exists(),
            file_hash=manifest.get_hash(path),
            owner=native.tool_key,
        )

    def probe(self, instance: SurfaceInstance) -> SurfaceStatus:
        """Probe one projected profile (or a sentinel instance)."""
        path_str = str(instance.path)
        if path_str == _NOT_APPLICABLE_SENTINEL:
            return self._not_applicable_status(instance)
        if path_str == _RESEARCH_GAP_SENTINEL:
            return self._research_gap_status(instance)
        if not instance.path.exists():
            return self._missing_status(instance)
        if instance.file_hash is not None and hash_file(instance.path) != instance.file_hash:
            return self._drift_status(instance)
        return SurfaceStatus(instance=instance, state=STATE_PRESENT)

    @staticmethod
    def _not_applicable_status(instance: SurfaceInstance) -> SurfaceStatus:
        """Build a ``not_applicable`` status for an assessed non-capable harness."""
        record = HARNESS_CAPABILITY_MATRIX.get(instance.owner)
        reason = record.reason if record is not None else "No native agent primitive."
        return SurfaceStatus(
            instance=instance,
            state=STATE_NOT_APPLICABLE,
            findings=(
                make_finding(
                    PROFILE_PROJECTION_UNSUPPORTED,
                    SEVERITY_INFO,
                    (
                        f"{instance.owner} does not support native agent profile "
                        "projection; profiles are exposed through other surfaces "
                        f"instead. Reason: {reason}"
                    ),
                    tool_key=instance.owner,
                    surface_id=_surface_id(instance),
                    details={"status": "not_applicable", "reason": reason},
                ),
            ),
        )

    @staticmethod
    def _research_gap_status(instance: SurfaceInstance) -> SurfaceStatus:
        return SurfaceStatus(
            instance=instance,
            state=STATE_NOT_APPLICABLE,
            findings=(
                make_finding(
                    RESEARCH_GAP_SURFACE,
                    SEVERITY_INFO,
                    (
                        "No verified native agent-profile primitive for "
                        f"{instance.owner}; profiles are not projected."
                    ),
                    tool_key=instance.owner,
                    surface_id=_surface_id(instance),
                    details={"status": "research_gap"},
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
                    NATIVE_AGENT_PROFILE_MISSING,
                    SEVERITY_ERROR,
                    f"Native agent profile is missing: {instance.path}",
                    tool_key=instance.owner,
                    surface_id=_surface_id(instance),
                    path=instance.path,
                    repair_command=_REPAIR_HINT,
                ),
            ),
        )

    @staticmethod
    def _drift_status(instance: SurfaceInstance) -> SurfaceStatus:
        return SurfaceStatus(
            instance=instance,
            state=STATE_DRIFTED,
            findings=(
                make_finding(
                    NATIVE_AGENT_PROFILE_DRIFT,
                    SEVERITY_WARNING,
                    f"Native agent profile drifted from manifest hash: {instance.path}",
                    tool_key=instance.owner,
                    surface_id=_surface_id(instance),
                    path=instance.path,
                    repair_command=_REPAIR_HINT,
                ),
            ),
        )

    def repair(
        self,
        project_root: Path,
        statuses: Sequence[SurfaceStatus],
        *,
        dry_run: bool = False,
    ) -> RepairResult:
        """Re-project and write files for missing/drifted statuses."""
        actionable = [
            s for s in statuses if s.state in (STATE_MISSING, STATE_DRIFTED)
        ]
        skipped = tuple(
            _surface_id(s.instance)
            for s in statuses
            if s.state in (STATE_NOT_APPLICABLE, STATE_UNSUPPORTED)
        )
        if not actionable:
            return RepairResult(skipped=skipped, dry_run=dry_run)
        if dry_run:
            return RepairResult(
                repaired=tuple(_surface_id(s.instance) for s in actionable),
                skipped=skipped,
                dry_run=True,
            )
        return self._write_all(project_root, actionable, skipped)

    def _write_all(
        self,
        project_root: Path,
        actionable: Sequence[SurfaceStatus],
        skipped: tuple[str, ...],
    ) -> RepairResult:
        projector = self._projector_for(project_root)
        manifest = self._manifest_for(project_root)
        index = self._project_index(projector, project_root, actionable)
        repaired: list[str] = []
        failed: list[str] = []
        for status in actionable:
            self._repair_one(status, projector, index, manifest, repaired, failed)
        manifest.save()
        return RepairResult(
            repaired=tuple(repaired),
            skipped=skipped,
            failed=tuple(failed),
            dry_run=False,
        )

    @staticmethod
    def _project_index(
        projector: ProfileProjector,
        project_root: Path,
        actionable: Sequence[SurfaceStatus],
    ) -> dict[str, NativeAgentProfile]:
        """Map output-path -> NativeAgentProfile for every affected tool key."""
        index: dict[str, NativeAgentProfile] = {}
        for tool_key in sorted({s.instance.owner for s in actionable}):
            for native in projector.project(tool_key, project_root):
                index[str(native.output_path)] = native
        return index

    @staticmethod
    def _repair_one(
        status: SurfaceStatus,
        projector: ProfileProjector,
        index: dict[str, NativeAgentProfile],
        manifest: ProfileManifest,
        repaired: list[str],
        failed: list[str],
    ) -> None:
        from dataclasses import replace

        instance = status.instance
        surface_id = _surface_id(instance)
        native = index.get(str(instance.path))
        if native is None:
            failed.append(f"{surface_id}: no projection for {instance.path}")
            return
        body = projector.render(native.tool_key, native.profile_urn)
        if body is None:
            failed.append(f"{surface_id}: unable to render {native.profile_urn}")
            return
        try:
            instance.path.parent.mkdir(parents=True, exist_ok=True)
            instance.path.write_text(body, encoding="utf-8")
        except OSError as exc:  # surfaced as a failure, never swallowed
            failed.append(f"{surface_id}: {exc}")
            return
        # User-global renderers (e.g. Amazon Q) write outside the project tree
        # and must NOT be recorded in the project manifest.
        if native.format != FORMAT_AMAZON_Q_AGENT:
            manifest.record(replace(native, file_hash=hash_content(body)))
        repaired.append(surface_id)
