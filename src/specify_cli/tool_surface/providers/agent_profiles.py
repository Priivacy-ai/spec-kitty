"""Native agent profile surface provider.

Wires :class:`~specify_cli.tool_surface.profiles.projection.ProfileProjector`
and :class:`~specify_cli.tool_surface.profiles.manifest.ProfileManifest` into a
reporting-layer provider for :data:`ToolSurfaceKind.AGENT_PROFILE`.

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
    ToolSurfaceKind,
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
from ._registry import SurfaceProviderRegistry, SurfaceRegistration

PROVIDER_KEY = "agent_profiles"
_PATH_PATTERN = ".claude/agents/{profile_id}.md"
_REPAIR_HINT = "spec-kitty doctor tool-surfaces --kind agent-profile --fix"
# Sentinel paths used to route probe() without holding real filesystem paths.
_RESEARCH_GAP_SENTINEL = "<unsupported>"
_NOT_APPLICABLE_SENTINEL = "<not-applicable>"
# Synthetic instance path that routes ``probe`` to the projection diagnostics
# (the #1940 finding codes from :meth:`ProfileProjector.diagnose`). Carries no
# file on disk; it exists only to flow ``diagnose`` findings through the standard
# ``collect`` path into ``doctor tool-surfaces --json`` output.
_DIAGNOSTICS_SENTINEL = "<profile-diagnostics>"


def agent_profile_definition() -> SurfaceDefinition:
    """Return the built-in agent-profile :class:`SurfaceDefinition`."""
    return SurfaceDefinition(
        kind=ToolSurfaceKind.AGENT_PROFILE,
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
        return bool(definition.kind == ToolSurfaceKind.AGENT_PROFILE)

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

        For projectable tools a synthetic diagnostics instance is appended so
        that :meth:`ProfileProjector.diagnose`'s #1940 finding codes flow through
        the standard ``collect`` path and reach ``doctor tool-surfaces --json``.
        ``not_applicable`` harnesses (no native primitive) return early; tools
        with no projection emit only the research-gap instance.
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
        instances = [
            self._instance_from_projection(definition, native, manifest)
            for native in projected
        ]
        instances.append(
            self._diagnostics_instance(definition, tool_key, project_root)
        )
        return instances

    @staticmethod
    def _diagnostics_instance(
        definition: SurfaceDefinition,
        tool_key: str,
        project_root: Path,
    ) -> SurfaceInstance:
        # ``path`` carries ``project_root`` so ``probe`` can rebuild a projector
        # for the project overlay layer; ``surface_id`` marks it as the
        # diagnostics sentinel and ``owner`` carries the tool key.
        return SurfaceInstance(
            definition=definition,
            path=project_root,
            exists=False,
            file_hash=None,
            owner=tool_key,
            surface_id=f"{tool_key}.{definition.kind}.{_DIAGNOSTICS_SENTINEL}",
        )

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
        """Probe one projected profile (or a sentinel instance).

        The diagnostics sentinel delegates to :meth:`ProfileProjector.diagnose`
        so the #1940 finding codes are surfaced; the not-applicable and
        research-gap sentinels and normal projected files keep their existing
        semantics.
        """
        if self._is_diagnostics_instance(instance):
            return self._diagnostics_status(instance)
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
    def _is_diagnostics_instance(instance: SurfaceInstance) -> bool:
        surface_id = instance.surface_id
        if surface_id is None:
            return False
        return bool(surface_id.endswith(_DIAGNOSTICS_SENTINEL))

    def _diagnostics_status(self, instance: SurfaceInstance) -> SurfaceStatus:
        # ``path`` is the ``project_root`` recorded at expand time (see
        # ``_diagnostics_instance``); rebuild the projector for it so the project
        # overlay layer participates in diagnosis.
        project_root = instance.path
        projector = self._projector_for(project_root)
        findings = tuple(projector.diagnose(instance.owner, project_root))
        return SurfaceStatus(
            instance=instance,
            state=STATE_NOT_APPLICABLE,
            findings=findings,
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
        """Re-project missing/drifted profiles and prune de-activated orphans.

        Beyond writing missing/drifted files, the ``--fix`` path reconciles the
        managed surface with the current **activation-admitted** projection set:
        any manifest-tracked, project-local file whose profile is no longer
        admitted (de-activated or removed) is deleted and its manifest entry
        dropped (R8). Pruning runs even when nothing is missing/drifted, since a
        de-activated profile produces no status at all.
        """
        actionable = [
            s for s in statuses if s.state in (STATE_MISSING, STATE_DRIFTED)
        ]
        skipped = tuple(
            _surface_id(s.instance)
            for s in statuses
            if s.state in (STATE_NOT_APPLICABLE, STATE_UNSUPPORTED)
        )
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
        pruned = self._prune_orphans(projector, project_root, manifest)
        # Preserve the historical no-op contract: only touch the manifest on
        # disk when something was actually written or pruned.
        if actionable or pruned:
            manifest.save()
        return RepairResult(
            repaired=tuple(repaired),
            skipped=skipped,
            failed=tuple(failed),
            dry_run=False,
        )

    @staticmethod
    def _prune_orphans(
        projector: ProfileProjector,
        project_root: Path,
        manifest: ProfileManifest,
    ) -> list[str]:
        """Delete manifest-tracked files no longer in the admitted projection set.

        The admitted set is recomputed per tracked tool key via
        :meth:`ProfileProjector.project`, which applies the charter activation
        gate (``default_profile_repository``). Any project-local manifest entry
        whose output path is absent from that set is an orphan: its file is
        deleted and the entry dropped. Only manifest-tracked entries are
        touched — unrelated user files under ``.claude/agents/`` are never
        removed. User-global (Amazon Q) entries are not project-managed and are
        left untouched.
        """
        tracked = [
            e for e in manifest.all_entries() if e.format != FORMAT_AMAZON_Q_AGENT
        ]
        if not tracked:
            return []
        admitted: set[str] = set()
        for tool_key in sorted({e.tool_key for e in tracked}):
            for native in projector.project(tool_key, project_root):
                admitted.add(str(native.output_path))
        pruned: list[str] = []
        for entry in tracked:
            output = str(entry.output_path)
            if output in admitted:
                continue
            path = entry.output_path
            try:
                if path.exists():
                    path.unlink()
            except OSError:
                # Keep the entry consistent with the on-disk file: if the file
                # cannot be removed, leave the manifest entry recorded.
                continue
            manifest.remove(path)
            pruned.append(output)
        return pruned

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


# ---------------------------------------------------------------------------
# Self-registration (fires at import time via providers._discovery)
# ---------------------------------------------------------------------------
SurfaceProviderRegistry.register(
    SurfaceRegistration(
        provider_class=AgentProfilesProvider,
        definitions=(agent_profile_definition(),),
        kind_tokens={"agent-profile": ToolSurfaceKind.AGENT_PROFILE},
        order=50,
    )
)
