"""Native-config surface provider.

Handles tool-specific config *glue* -- the entries that wire a harness up to
discover Spec Kitty's shared skills, distinct from the orientation/context files
owned by :mod:`session_presence`. These are :data:`ToolSurfaceKind.NATIVE_CONFIG`
surfaces.

Currently the only verified native-config glue is Mistral Vibe's ``skill_paths``
entry in ``.vibe/config.toml`` (see
:mod:`specify_cli.skills.vibe_config`). The provider expands one instance per
tool that needs glue, probes whether the glue is present and current, and
delegates repair back to the owning helper -- it never reimplements the TOML
merge logic.

Harnesses with no known native-config glue yield a single
``research-gap-surface`` finding rather than being treated as healthy.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
import tomllib

from specify_cli.skills.vibe_config import VIBE_SKILL_PATH, ensure_project_skill_path

from ..enums import (
    ActivationMode,
    InstallScope,
    RequiredPolicy,
    SourceKind,
    ToolSurfaceKind,
)
from ..findings import (
    NATIVE_CONFIG_MISSING,
    RESEARCH_GAP_SURFACE,
    SEVERITY_ERROR,
    SEVERITY_INFO,
    make_finding,
)
from ..model import SurfaceDefinition, SurfaceInstance
from ..repair import RepairResult
from ..status import (
    STATE_MISSING,
    STATE_NOT_APPLICABLE,
    STATE_PRESENT,
    SurfaceStatus,
    _surface_id,
)
from ._registry import SurfaceProviderRegistry, SurfaceRegistration

PROVIDER_KEY = "native_config"
_REPAIR_HINT = "spec-kitty doctor tool-surfaces --kind native_config --fix"
_RESEARCH_GAP_SENTINEL = "<unsupported>"
_VIBE_CONFIG_REL = ".vibe/config.toml"

# Tools whose skills are discovered only after a native-config glue entry is
# written. ``vibe`` needs the ``skill_paths`` entry in ``.vibe/config.toml``.
_VIBE_TOOL_KEY = "vibe"


def native_config_definition() -> SurfaceDefinition:
    """Return the built-in ``native_config`` :class:`SurfaceDefinition`."""
    return SurfaceDefinition(
        kind=ToolSurfaceKind.NATIVE_CONFIG,
        source_kind=SourceKind.GENERATED,
        install_scope=InstallScope.PROJECT,
        path_pattern=_VIBE_CONFIG_REL,
        required_policy=RequiredPolicy.REPAIRABLE_REQUIRED,
        activation_mode=ActivationMode.ALWAYS,
        provider_key=PROVIDER_KEY,
        repair_hint=_REPAIR_HINT,
    )


class NativeConfigProvider:
    """Provider for tool-specific native config glue (e.g. vibe skill paths)."""

    provider_key = PROVIDER_KEY

    def can_handle(self, definition: SurfaceDefinition) -> bool:
        return definition.kind == ToolSurfaceKind.NATIVE_CONFIG

    def expand(
        self,
        definition: SurfaceDefinition,
        tool_key: str,
        project_root: Path,
    ) -> list[SurfaceInstance]:
        """Expand into the glue instance(s) for ``tool_key``.

        Only Vibe currently has verified native-config glue. Any other tool
        yields a research-gap instance so the gap is reported, not hidden.
        """
        if tool_key != _VIBE_TOOL_KEY:
            return [self._research_gap_instance(definition, tool_key)]
        path = project_root / _VIBE_CONFIG_REL
        return [
            SurfaceInstance(
                definition=definition,
                path=path,
                exists=_vibe_skill_path_present(path),
                file_hash=None,
                owner=tool_key,
            )
        ]

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

    def probe(self, instance: SurfaceInstance) -> SurfaceStatus:
        """Re-check whether the native-config glue entry is present."""
        if str(instance.path) == _RESEARCH_GAP_SENTINEL:
            return self._research_gap_status(instance)
        if _vibe_skill_path_present(instance.path):
            return SurfaceStatus(instance=instance, state=STATE_PRESENT)
        return self._missing_status(instance)

    @staticmethod
    def _research_gap_status(instance: SurfaceInstance) -> SurfaceStatus:
        return SurfaceStatus(
            instance=instance,
            state=STATE_NOT_APPLICABLE,
            findings=(
                make_finding(
                    RESEARCH_GAP_SURFACE,
                    SEVERITY_INFO,
                    f"No known native-config glue for {instance.owner}.",
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
                    NATIVE_CONFIG_MISSING,
                    SEVERITY_ERROR,
                    f"Native-config glue missing for {instance.owner}: "
                    f"{instance.path}",
                    tool_key=instance.owner,
                    surface_id=_surface_id(instance),
                    path=instance.path,
                    repair_command=_REPAIR_HINT,
                ),
            ),
        )

    def remove(self, instance: SurfaceInstance) -> bool:
        """Native-config glue is shared with user config; never auto-removed."""
        _ = instance
        return False

    def repair(
        self,
        project_root: Path,
        statuses: Sequence[SurfaceStatus],
        *,
        dry_run: bool = False,
    ) -> RepairResult:
        """Write the missing native-config glue via the owning helper."""
        actionable = [s for s in statuses if s.state == STATE_MISSING]
        skipped = tuple(
            _surface_id(s.instance)
            for s in statuses
            if s.state == STATE_NOT_APPLICABLE
        )
        if not actionable:
            return RepairResult(skipped=skipped, dry_run=dry_run)
        if dry_run:
            return RepairResult(
                repaired=tuple(_surface_id(s.instance) for s in actionable),
                skipped=skipped,
                dry_run=True,
            )
        return self._apply(project_root, actionable, skipped)

    @staticmethod
    def _apply(
        project_root: Path,
        actionable: Sequence[SurfaceStatus],
        skipped: tuple[str, ...],
    ) -> RepairResult:
        repaired: list[str] = []
        failed: list[str] = []
        for status in actionable:
            try:
                ensure_project_skill_path(project_root)
                repaired.append(_surface_id(status.instance))
            except Exception as exc:  # surfaced as a failure, never swallowed
                failed.append(f"{status.instance.owner}: {exc}")
        return RepairResult(
            repaired=tuple(repaired),
            skipped=skipped,
            failed=tuple(failed),
            dry_run=False,
        )


def _vibe_skill_path_present(config_path: Path) -> bool:
    """Return whether ``.vibe/config.toml`` lists the shared skills path."""
    if not config_path.exists():
        return False
    try:
        raw = config_path.read_text(encoding="utf-8")
    except OSError:
        return False
    if not raw.strip():
        return False
    try:
        data = tomllib.loads(raw)
    except tomllib.TOMLDecodeError:
        return False
    skill_paths = data.get("skill_paths")
    if isinstance(skill_paths, str):
        return bool(skill_paths == VIBE_SKILL_PATH)
    if isinstance(skill_paths, list):
        return VIBE_SKILL_PATH in [str(value) for value in skill_paths]
    return False


# ---------------------------------------------------------------------------
# Self-registration (fires at import time via providers._discovery)
# ---------------------------------------------------------------------------
SurfaceProviderRegistry.register(
    SurfaceRegistration(
        provider_class=NativeConfigProvider,
        definitions=(native_config_definition(),),
        kind_tokens={
            "native-config": ToolSurfaceKind.NATIVE_CONFIG,
            "native_config": ToolSurfaceKind.NATIVE_CONFIG,
        },
        order=30,
    )
)
