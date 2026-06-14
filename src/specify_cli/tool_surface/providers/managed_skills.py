"""Managed doctrine-skill surface provider.

Wraps the existing managed doctrine-skill infrastructure
(:mod:`specify_cli.skills.registry` and :mod:`specify_cli.skills.verifier`) as a
reporting-layer
:class:`~specify_cli.tool_surface.providers.protocol.ReportingSurfaceProvider`.

Both probe (``verify_installed_skills``) and repair (``repair_skills``) live in
:mod:`specify_cli.skills.verifier`; the ``installer`` module only owns the
``install_*`` entry points and does **not** expose ``repair_skills``. The default
repair collaborator is therefore bound to the verifier module so the live
``--fix`` path actually invokes the real ``repair_skills``.

Doctrine skills are distinct from command skills:

* Command skills are slash-command invocations rendered to
  ``.agents/skills/spec-kitty.<command>/SKILL.md`` and tracked in
  ``.kittify/command-skills-manifest.json``.
* Doctrine skills are managed knowledge/mission-step surfaces installed by the
  skill installer and tracked in ``.kittify/skills-manifest.json``.

The provider never reimplements the installer's hash/symlink/path-traversal
safety logic or the verifier's drift detection -- it delegates every probe and
mutation to those modules and only translates their results into surface
contract types. The verifier already produces its own ``doctor skills`` report;
this provider adds the surface-contract view on top of it and must not duplicate
or conflict with that output.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Protocol

from specify_cli.skills import verifier as skill_verifier
from specify_cli.skills.manifest import (
    ManagedFileEntry,
    compute_content_hash,
    load_manifest,
)
from specify_cli.skills.registry import SkillRegistry

from ..enums import (
    ActivationMode,
    InstallScope,
    RequiredPolicy,
    SourceKind,
    SurfaceKind,
)
from ..findings import (
    GENERATED_SURFACE_MISSING,
    MANAGED_FILE_DRIFT,
    SEVERITY_ERROR,
    SEVERITY_WARNING,
    make_finding,
)
from ..model import SurfaceDefinition, SurfaceInstance
from ..repair import RepairResult
from ..status import (
    STATE_DRIFTED,
    STATE_MISSING,
    STATE_PRESENT,
    SurfaceStatus,
    _surface_id,
)

PROVIDER_KEY = "managed_skills"
_PATH_PATTERN = ".kittify/skills-manifest.json:{installed_path}"
_REPAIR_HINT = "spec-kitty doctor tool-surfaces --kind doctrine-skill --fix"


class _VerifyResultProto(Protocol):
    """Subset of ``skills.verifier.VerifyResult`` this provider relies on."""

    ok: bool


class _VerifierProto(Protocol):
    """Subset of the ``skills.verifier`` module this provider delegates to."""

    def verify_installed_skills(self, project_path: Path) -> _VerifyResultProto:
        ...


class _RepairProto(Protocol):
    """Subset of the ``skills.verifier`` module this provider delegates to.

    ``repair_skills`` is owned by :mod:`specify_cli.skills.verifier` (not the
    ``installer`` module), so the default collaborator is the verifier module.
    """

    def repair_skills(
        self,
        project_path: Path,
        verify_result: _VerifyResultProto,
        registry: _RegistryProto,
    ) -> tuple[int, int]:
        ...


class _RegistryProto(Protocol):
    """Subset of ``SkillRegistry`` needed to decide if a registry is usable."""

    def discover_skills(self) -> Sequence[object]:
        ...


def managed_skill_definition() -> SurfaceDefinition:
    """Return the built-in doctrine-skill :class:`SurfaceDefinition`."""
    return SurfaceDefinition(
        kind=SurfaceKind.DOCTRINE_SKILL,
        source_kind=SourceKind.GENERATED,
        install_scope=InstallScope.PROJECT,
        path_pattern=_PATH_PATTERN,
        required_policy=RequiredPolicy.REPAIRABLE_REQUIRED,
        activation_mode=ActivationMode.SKILLS_INVOKABLE,
        provider_key=PROVIDER_KEY,
        repair_hint=_REPAIR_HINT,
    )


class ManagedSkillsProvider:
    """Provider for managed doctrine-skill surfaces."""

    provider_key = PROVIDER_KEY

    def __init__(
        self,
        verifier: _VerifierProto | None = None,
        installer: _RepairProto | None = None,
        registry_factory: Callable[[], _RegistryProto] | None = None,
    ) -> None:
        # All collaborators are accepted for dependency injection in tests. By
        # default the module-level functions from ``skills.verifier`` are used
        # directly so the verifier invariants (hash/symlink/path-traversal
        # safety) are never bypassed or reimplemented. ``repair_skills`` lives in
        # the verifier module, so the default repair collaborator binds there --
        # the ``installer`` module does not expose it.
        self._verifier: _VerifierProto = (
            verifier if verifier is not None else skill_verifier
        )
        self._installer: _RepairProto = (
            installer if installer is not None else skill_verifier
        )
        self._registry_factory: Callable[[], _RegistryProto] = (
            registry_factory
            if registry_factory is not None
            else SkillRegistry.from_package
        )

    def can_handle(self, definition: SurfaceDefinition) -> bool:
        return definition.kind is SurfaceKind.DOCTRINE_SKILL

    def expand(
        self,
        definition: SurfaceDefinition,
        tool_key: str,
        project_root: Path,
    ) -> list[SurfaceInstance]:
        """Expand into one instance per managed doctrine skill for ``tool_key``.

        The managed-skill manifest (``.kittify/skills-manifest.json``) is the
        authority for what should exist. Each manifest entry owned by
        ``tool_key`` (``agent_key``) becomes a :class:`SurfaceInstance`.
        """
        manifest = load_manifest(project_root)
        if manifest is None:
            return []
        instances: list[SurfaceInstance] = []
        for entry in manifest.entries:
            if entry.agent_key != tool_key:
                continue
            abs_path = (project_root / entry.installed_path).resolve()
            instances.append(
                SurfaceInstance(
                    definition=definition,
                    path=abs_path,
                    exists=abs_path.exists(),
                    file_hash=entry.content_hash,
                    owner=tool_key,
                )
            )
        return instances

    def probe(self, instance: SurfaceInstance) -> SurfaceStatus:
        """Re-check existence and manifest hash via the managed-skill layer."""
        path = instance.path
        if not path.exists():
            return self._missing_status(instance)
        if instance.file_hash is not None:
            on_disk = self._content_hash(path)
            if on_disk is not None and on_disk != instance.file_hash:
                return self._drifted_status(instance)
        return SurfaceStatus(instance=instance, state=STATE_PRESENT)

    @staticmethod
    def _content_hash(path: Path) -> str | None:
        try:
            digest: str = compute_content_hash(path)
        except OSError:
            return None
        return digest

    @staticmethod
    def _missing_status(instance: SurfaceInstance) -> SurfaceStatus:
        return SurfaceStatus(
            instance=instance,
            state=STATE_MISSING,
            findings=(
                make_finding(
                    GENERATED_SURFACE_MISSING,
                    SEVERITY_ERROR,
                    f"Managed doctrine skill for {instance.owner} is missing: "
                    f"{instance.path}",
                    tool_key=instance.owner,
                    surface_id=_surface_id(instance),
                    path=instance.path,
                    repair_command=_REPAIR_HINT,
                ),
            ),
        )

    @staticmethod
    def _drifted_status(instance: SurfaceInstance) -> SurfaceStatus:
        return SurfaceStatus(
            instance=instance,
            state=STATE_DRIFTED,
            findings=(
                make_finding(
                    MANAGED_FILE_DRIFT,
                    SEVERITY_WARNING,
                    f"Managed doctrine skill drifted from manifest hash: "
                    f"{instance.path}",
                    tool_key=instance.owner,
                    surface_id=_surface_id(instance),
                    path=instance.path,
                    repair_command=_REPAIR_HINT,
                ),
            ),
        )

    def remove(self, instance: SurfaceInstance) -> bool:
        """Doctrine-skill removal is not in scope for the surface contract.

        Managed doctrine skills are removed per-agent by the dedicated skill
        installer flow (``agent config remove``/skill uninstall), which owns the
        symlink and shared-root ref-count safety logic. This provider therefore
        never deletes them as part of surface repair and returns ``False`` to
        signal that no removal was performed.
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
        """Delegate doctrine-skill repair to ``skills.verifier``.

        The verifier computes the full missing/drifted set from the manifest, and
        its ``repair_skills`` performs the safe copy/symlink restore. This
        provider never reimplements either; it only scopes repair to the statuses
        it owns and translates the outcome.
        """
        actionable = [
            s for s in statuses if s.state in (STATE_MISSING, STATE_DRIFTED)
        ]
        if not actionable:
            return RepairResult(dry_run=dry_run)
        ids = tuple(_surface_id(s.instance) for s in actionable)
        if dry_run:
            return RepairResult(repaired=ids, dry_run=True)
        return self._delegate_repair(project_root, ids)

    def _delegate_repair(
        self,
        project_root: Path,
        ids: tuple[str, ...],
    ) -> RepairResult:
        registry = self._resolve_registry()
        if registry is None:
            return RepairResult(
                failed=("managed_skills: no canonical skill registry",) + ids,
                dry_run=False,
            )
        verify_result = self._verifier.verify_installed_skills(project_root)
        if verify_result.ok:
            return RepairResult(dry_run=False)
        try:
            repaired, failed = self._installer.repair_skills(
                project_root, verify_result, registry
            )
        except OSError as exc:  # surfaced as a failure, never swallowed
            return RepairResult(
                failed=(f"managed_skills: {exc}",) + ids,
                dry_run=False,
            )
        return self._repair_outcome(ids, repaired, failed)

    @staticmethod
    def _repair_outcome(
        ids: tuple[str, ...], repaired: int, failed: int
    ) -> RepairResult:
        if failed > 0:
            return RepairResult(
                repaired=ids[:repaired],
                failed=(f"managed_skills: {failed} file(s) failed to repair",),
                dry_run=False,
            )
        return RepairResult(repaired=ids, dry_run=False)

    def _resolve_registry(self) -> _RegistryProto | None:
        registry = self._registry_factory()
        if registry.discover_skills():
            return registry
        return None


def doctrine_skill_entries(
    project_root: Path, tool_key: str
) -> list[ManagedFileEntry]:
    """Return the manifest entries owned by ``tool_key`` (helper for tests)."""
    manifest = load_manifest(project_root)
    if manifest is None:
        return []
    return [e for e in manifest.entries if e.agent_key == tool_key]
