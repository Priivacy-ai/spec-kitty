"""Command-skill surface provider.

Wraps :mod:`specify_cli.skills.command_installer` as a reporting-layer
:class:`~specify_cli.tool_surface.providers.protocol.ReportingSurfaceProvider`.
The provider never reimplements the installer's hash, ref-count, or shared-root
safety logic -- it delegates every mutation to the installer and only translates
its results into surface contract types.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from specify_cli.skills import command_installer, manifest_store

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

PROVIDER_KEY = "command_skills"
_PATH_PATTERN = ".agents/skills/spec-kitty.{command}/SKILL.md"
_REPAIR_HINT = "spec-kitty doctor tool-surfaces --kind command-skill --fix"


def command_skill_definition() -> SurfaceDefinition:
    """Return the built-in command-skill :class:`SurfaceDefinition`."""
    return SurfaceDefinition(
        kind=SurfaceKind.COMMAND_SKILL,
        source_kind=SourceKind.GENERATED,
        install_scope=InstallScope.PROJECT,
        path_pattern=_PATH_PATTERN,
        required_policy=RequiredPolicy.REPAIRABLE_REQUIRED,
        activation_mode=ActivationMode.SKILLS_INVOKABLE,
        provider_key=PROVIDER_KEY,
        repair_hint=_REPAIR_HINT,
    )


def _rel_path(command: str) -> str:
    return _PATH_PATTERN.format(command=command)


class CommandSkillsProvider:
    """Provider for command-skill (``SKILL.md``) surfaces."""

    provider_key = PROVIDER_KEY

    def __init__(self, installer: object | None = None) -> None:
        # ``installer`` is accepted for dependency injection in tests; by default
        # the module-level installer functions are used directly so installer
        # invariants (hash/ref-count/shared-root safety) are never bypassed.
        self._installer = installer if installer is not None else command_installer

    def can_handle(self, definition: SurfaceDefinition) -> bool:
        return definition.kind == SurfaceKind.COMMAND_SKILL

    def expand(
        self,
        definition: SurfaceDefinition,
        tool_key: str,
        project_root: Path,
    ) -> list[SurfaceInstance]:
        """Expand into one instance per canonical command for ``tool_key``."""
        if tool_key not in command_installer.SUPPORTED_AGENTS:
            return []
        manifest = manifest_store.load(project_root)
        instances: list[SurfaceInstance] = []
        for command in command_installer.CANONICAL_COMMANDS:
            rel = _rel_path(command)
            abs_path = project_root / rel
            entry = manifest.find(rel)
            instances.append(
                SurfaceInstance(
                    definition=definition,
                    path=abs_path,
                    exists=abs_path.exists(),
                    file_hash=entry.content_hash if entry is not None else None,
                    owner=tool_key,
                )
            )
        return instances

    def probe(self, instance: SurfaceInstance) -> SurfaceStatus:
        """Re-check existence and hash and return a :class:`SurfaceStatus`."""
        path = instance.path
        if not path.exists():
            return SurfaceStatus(
                instance=instance,
                state=STATE_MISSING,
                findings=(
                    make_finding(
                        GENERATED_SURFACE_MISSING,
                        SEVERITY_ERROR,
                        f"Command skill for {instance.owner} is missing: {path}",
                        tool_key=instance.owner,
                        surface_id=_surface_id(instance),
                        path=path,
                        repair_command=_REPAIR_HINT,
                    ),
                ),
            )
        if instance.file_hash is not None:
            on_disk = manifest_store.fingerprint_file(path)
            if on_disk != instance.file_hash:
                return SurfaceStatus(
                    instance=instance,
                    state=STATE_DRIFTED,
                    findings=(
                        make_finding(
                            MANAGED_FILE_DRIFT,
                            SEVERITY_WARNING,
                            f"Command skill drifted from manifest hash: {path}",
                            tool_key=instance.owner,
                            surface_id=_surface_id(instance),
                            path=path,
                        ),
                    ),
                )
        return SurfaceStatus(instance=instance, state=STATE_PRESENT)

    def remove(self, instance: SurfaceInstance) -> bool:
        """Delegate removal of an agent's command skills to the installer.

        The instance path is ``<project_root>/.agents/skills/...``; the project
        root is recovered by stripping the canonical relative suffix so the
        installer's shared-root safety logic is preserved.
        """
        rel = _PATH_PATTERN.split("{command}", 1)[0]
        marker = rel.split("/", 1)[0]
        parts = instance.path.parts
        if marker not in parts:
            return False
        project_root = Path(*parts[: parts.index(marker)])
        report = command_installer.remove(project_root, instance.owner)
        return bool(report.deref)

    def repair(
        self,
        project_root: Path,
        statuses: Sequence[SurfaceStatus],
        *,
        dry_run: bool = False,
    ) -> RepairResult:
        """Reinstall command skills for the affected agents via the installer."""
        affected = {
            s.instance.owner
            for s in statuses
            if s.state in (STATE_MISSING, STATE_DRIFTED)
        }
        if not affected:
            return RepairResult(dry_run=dry_run)
        if dry_run:
            return RepairResult(
                repaired=tuple(_surface_id(s.instance) for s in statuses),
                dry_run=True,
            )
        repaired: list[str] = []
        failed: list[str] = []
        statuses_by_agent = _group_statuses_by_agent(statuses)
        for agent in sorted(affected):
            try:
                command_installer.install(project_root, agent)
                repaired.extend(statuses_by_agent.get(agent, ()))
            except Exception as exc:  # surfaced as a failure, never swallowed
                failed.append(f"{agent}: {exc}")
        return RepairResult(
            repaired=tuple(repaired),
            failed=tuple(failed),
            dry_run=False,
        )


def _group_statuses_by_agent(
    statuses: Sequence[SurfaceStatus],
) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for status in statuses:
        grouped.setdefault(status.instance.owner, []).append(
            _surface_id(status.instance)
        )
    return grouped
