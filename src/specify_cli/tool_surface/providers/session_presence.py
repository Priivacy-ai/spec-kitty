"""Session-presence surface provider.

Wraps :mod:`specify_cli.session_presence.writers.registry` as a reporting-layer
:class:`~specify_cli.tool_surface.providers.protocol.ReportingSurfaceProvider`.

``session_presence`` is a *provider name*, not a :class:`ToolSurfaceKind`. The
provider expands a tool's session-presence writer into one
:class:`SurfaceInstance` per managed artefact, tagging each with the distinct
:class:`ToolSurfaceKind` it represents:

* :data:`ToolSurfaceKind.CONTEXT_FILE` -- always-on orientation files
  (``.claude/CLAUDE.md``, ``AGENTS.md``, ``GEMINI.md``, copilot instructions).
* :data:`ToolSurfaceKind.RULE` -- path/glob-activated rules and steering files
  (``.cursor/rules/spec-kitty.mdc``, ``.kiro/steering/spec-kitty.md``).
* :data:`ToolSurfaceKind.HOOK` -- tool lifecycle event handlers
  (``.claude/settings.json`` ``SessionStart`` / ``Stop`` entries).

The provider never reimplements writer logic: ``expand`` asks the writer which
paths it manages, ``probe`` checks them, and ``repair`` delegates back to the
writer via :class:`SessionPresenceManager`. Harnesses with a ``NullWriter`` (no
known orientation mechanism) yield a single ``research-gap-surface`` finding --
never a hard failure and never a silent OK.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from specify_cli.session_presence.content import (
    SECTION_OPEN,
    SessionPresenceContent,
)
from specify_cli.session_presence.hooks.claude_code_hook import (
    SESSION_START_EVENT,
    STOP_EVENT,
    ClaudeCodeHookRegistrar,
)
from specify_cli.session_presence.writers.claude_code import (
    SESSION_START_CMD,
    SESSION_STOP_CMD,
    ClaudeCodeWriter,
)
from specify_cli.session_presence.writers.markdown_rules import MarkdownRulesWriter
from specify_cli.session_presence.writers.null_writer import NullWriter
from specify_cli.session_presence.writers.registry import get_writer

from ..enums import (
    ActivationMode,
    InstallScope,
    RequiredPolicy,
    SourceKind,
    ToolSurfaceKind,
)
from ..findings import (
    CONTEXT_FILE_MISSING,
    RESEARCH_GAP_SURFACE,
    SESSION_PRESENCE_INCOMPLETE,
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

PROVIDER_KEY = "session_presence"
_REPAIR_HINT = "spec-kitty doctor tool-surfaces --kind context_file --fix"
_HOOK_REPAIR_HINT = "spec-kitty doctor tool-surfaces --kind hook --fix"
_RESEARCH_GAP_SENTINEL = "<unsupported>"

# The provider expands into these distinct kinds. ``session_presence`` itself is
# a provider name and is deliberately absent from this set.
_SESSION_PRESENCE_KINDS = frozenset(
    {
        ToolSurfaceKind.CONTEXT_FILE,
        ToolSurfaceKind.HOOK,
        ToolSurfaceKind.RULE,
    }
)

# Path fragments that mark a writer's target as a path/glob-activated *rule*
# rather than an always-on context file. Anything else a MarkdownRulesWriter
# manages is treated as a CONTEXT_FILE.
_RULE_PATH_MARKERS = ("/rules/", "/steering/", ".mdc")


def _definition_for(kind: ToolSurfaceKind) -> SurfaceDefinition:
    """Return the session-presence :class:`SurfaceDefinition` for ``kind``."""
    activation = (
        ActivationMode.EVENT
        if kind == ToolSurfaceKind.HOOK
        else ActivationMode.GLOB
        if kind == ToolSurfaceKind.RULE
        else ActivationMode.ALWAYS
    )
    repair_hint = _HOOK_REPAIR_HINT if kind == ToolSurfaceKind.HOOK else _REPAIR_HINT
    return SurfaceDefinition(
        kind=kind,
        source_kind=SourceKind.GENERATED,
        install_scope=InstallScope.PROJECT,
        path_pattern="<session-presence>",
        required_policy=RequiredPolicy.REPAIRABLE_REQUIRED,
        activation_mode=activation,
        provider_key=PROVIDER_KEY,
        repair_hint=repair_hint,
    )


def context_file_definition() -> SurfaceDefinition:
    """Return the built-in ``context_file`` :class:`SurfaceDefinition`."""
    return _definition_for(ToolSurfaceKind.CONTEXT_FILE)


def hook_definition() -> SurfaceDefinition:
    """Return the built-in ``hook`` :class:`SurfaceDefinition`."""
    return _definition_for(ToolSurfaceKind.HOOK)


def rule_definition() -> SurfaceDefinition:
    """Return the built-in ``rule`` :class:`SurfaceDefinition`."""
    return _definition_for(ToolSurfaceKind.RULE)


def _markdown_kind(rules_path: str) -> ToolSurfaceKind:
    """Classify a MarkdownRulesWriter target as ``RULE`` or ``CONTEXT_FILE``."""
    lowered = rules_path.lower()
    if any(marker in lowered for marker in _RULE_PATH_MARKERS):
        return ToolSurfaceKind.RULE
    return ToolSurfaceKind.CONTEXT_FILE


class SessionPresenceProvider:
    """Provider for session-presence surfaces (context files, hooks, rules)."""

    provider_key = PROVIDER_KEY

    def can_handle(self, definition: SurfaceDefinition) -> bool:
        # ``session_presence`` is a PROVIDER NAME, not a ToolSurfaceKind. This
        # provider handles the context_file, hook, and rule kinds it expands to.
        return definition.kind in _SESSION_PRESENCE_KINDS

    def expand(
        self,
        definition: SurfaceDefinition,
        tool_key: str,
        project_root: Path,
    ) -> list[SurfaceInstance]:
        """Expand into one instance per artefact the tool's writer manages.

        ``definition`` only carries the requested kind; the concrete kind of each
        emitted instance comes from the writer's metadata, never from a hardcoded
        path. Instances whose kind does not match ``definition.kind`` are filtered
        so ``--kind`` selection stays exact.
        """
        writer = get_writer(tool_key)
        if isinstance(writer, NullWriter):
            return [self._research_gap_instance(tool_key)]
        managed = _managed_surfaces(writer, project_root)
        instances: list[SurfaceInstance] = []
        for path, kind in managed:
            if kind != definition.kind:
                continue
            instances.append(
                SurfaceInstance(
                    definition=_definition_for(kind),
                    path=path,
                    exists=_artefact_present(writer, path, kind, project_root),
                    file_hash=None,
                    owner=tool_key,
                )
            )
        return instances

    @staticmethod
    def _research_gap_instance(tool_key: str) -> SurfaceInstance:
        return SurfaceInstance(
            definition=context_file_definition(),
            path=Path(_RESEARCH_GAP_SENTINEL),
            exists=False,
            file_hash=None,
            owner=tool_key,
        )

    def probe(self, instance: SurfaceInstance) -> SurfaceStatus:
        """Re-check presence of a session-presence artefact against disk.

        Presence is recomputed live (not read from the instance snapshot) so a
        post-repair re-probe reflects the just-written artefact.
        """
        if str(instance.path) == _RESEARCH_GAP_SENTINEL:
            return self._research_gap_status(instance)
        if _instance_present(instance):
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
                    f"No known session-presence mechanism for {instance.owner}.",
                    tool_key=instance.owner,
                    surface_id=_surface_id(instance),
                ),
            ),
        )

    @staticmethod
    def _missing_status(instance: SurfaceInstance) -> SurfaceStatus:
        kind = instance.definition.kind
        if kind == ToolSurfaceKind.CONTEXT_FILE:
            code = CONTEXT_FILE_MISSING
            message = f"Always-on context file missing for {instance.owner}: {instance.path}"
            hint = _REPAIR_HINT
        else:
            code = SESSION_PRESENCE_INCOMPLETE
            label = "hook entry" if kind == ToolSurfaceKind.HOOK else "rule file"
            message = f"Session-presence {label} missing for {instance.owner}: {instance.path}"
            hint = _HOOK_REPAIR_HINT if kind == ToolSurfaceKind.HOOK else _REPAIR_HINT
        return SurfaceStatus(
            instance=instance,
            state=STATE_MISSING,
            findings=(
                make_finding(
                    code,
                    SEVERITY_ERROR,
                    message,
                    tool_key=instance.owner,
                    surface_id=_surface_id(instance),
                    path=instance.path,
                    repair_command=hint,
                ),
            ),
        )

    def remove(self, instance: SurfaceInstance) -> bool:
        """Delegate removal to the owning writer.

        Returns ``False`` for research-gap sentinels (nothing to remove).
        """
        if str(instance.path) == _RESEARCH_GAP_SENTINEL:
            return False
        project_root, writer = _resolve_writer_for_instance(instance)
        if writer is None or project_root is None:
            return False
        writer.remove(project_root)
        return True

    def repair(
        self,
        project_root: Path,
        statuses: Sequence[SurfaceStatus],
        *,
        dry_run: bool = False,
    ) -> RepairResult:
        """Rewrite session presence for affected tools via their writers."""
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
        return self._rewrite(project_root, actionable, skipped)

    @staticmethod
    def _rewrite(
        project_root: Path,
        actionable: Sequence[SurfaceStatus],
        skipped: tuple[str, ...],
    ) -> RepairResult:
        content = _orientation_content(project_root)
        repaired: list[str] = []
        failed: list[str] = []
        owners = sorted({s.instance.owner for s in actionable})
        writers = {owner: get_writer(owner) for owner in owners}
        for owner in owners:
            writer = writers[owner]
            try:
                writer.write(project_root, content)
                repaired.extend(
                    _surface_id(s.instance)
                    for s in actionable
                    if s.instance.owner == owner
                )
            except Exception as exc:  # surfaced as a failure, never swallowed
                failed.append(f"{owner}: {exc}")
        return RepairResult(
            repaired=tuple(repaired),
            skipped=skipped,
            failed=tuple(failed),
            dry_run=False,
        )


def _managed_surfaces(
    writer: object, project_root: Path
) -> list[tuple[Path, ToolSurfaceKind]]:
    """Return the ``(absolute_path, kind)`` artefacts ``writer`` manages.

    Knowledge of which writer manages which artefacts lives here rather than in
    the writers themselves (the writers predate the surface contract). Claude's
    writer manages a context file plus two ``settings.json`` hook entries; the
    Markdown-family writers manage a single context-or-rule file classified by
    its target path.
    """
    surfaces: list[tuple[Path, ToolSurfaceKind]] = []
    if isinstance(writer, ClaudeCodeWriter):
        surfaces.append(
            (project_root / writer.rules_path, ToolSurfaceKind.CONTEXT_FILE)
        )
        settings = project_root / ".claude" / "settings.json"
        surfaces.append((settings, ToolSurfaceKind.HOOK))
        surfaces.append((settings, ToolSurfaceKind.HOOK))
        return surfaces
    if isinstance(writer, MarkdownRulesWriter):
        surfaces.append(
            (project_root / writer.rules_path, _markdown_kind(writer.rules_path))
        )
    return surfaces


def _instance_present(instance: SurfaceInstance) -> bool:
    """Recompute live presence for an instance from disk.

    The project root is recovered from the instance path by stripping the
    artefact's relative suffix; the writer is looked up by owner so the correct
    per-kind presence check runs.
    """
    writer = get_writer(instance.owner)
    kind = instance.definition.kind
    if kind == ToolSurfaceKind.HOOK and isinstance(writer, ClaudeCodeWriter):
        root = _project_root_from(instance.path, Path(".claude/settings.json"))
        return root is not None and _claude_hooks_present(root)
    if isinstance(writer, MarkdownRulesWriter):
        return _orientation_section_present(instance.path)
    return instance.path.exists()


def _project_root_from(path: Path, rel: Path) -> Path | None:
    """Strip ``rel`` from the tail of ``path`` to recover the project root."""
    parts = path.parts
    rel_parts = rel.parts
    if len(parts) < len(rel_parts) or parts[-len(rel_parts):] != rel_parts:
        return None
    return Path(*parts[: len(parts) - len(rel_parts)])


def _artefact_present(
    writer: object,
    path: Path,
    kind: ToolSurfaceKind,
    project_root: Path,
) -> bool:
    """Return whether the specific artefact at ``path`` is currently installed.

    Each artefact is checked in isolation -- the context file by its orientation
    marker, the hooks by their registrar. ``ClaudeCodeWriter.has_presence`` is a
    *composite* (file AND both hooks), so it is deliberately not used here: a
    ``--kind context_file`` probe must report the file's own state regardless of
    whether the sibling hooks happen to be present.
    """
    if kind == ToolSurfaceKind.HOOK and isinstance(writer, ClaudeCodeWriter):
        return _claude_hooks_present(project_root)
    if isinstance(writer, MarkdownRulesWriter):
        return _orientation_section_present(project_root / writer.rules_path)
    return path.exists()


def _orientation_section_present(target: Path) -> bool:
    """Return whether ``target`` exists and contains the orientation marker."""
    if not target.exists():
        return False
    try:
        return SECTION_OPEN in target.read_text(encoding="utf-8")
    except OSError:
        return False


def _claude_hooks_present(project_root: Path) -> bool:
    """Return whether both Claude session hooks are registered."""
    start = ClaudeCodeHookRegistrar(SESSION_START_EVENT).is_registered(
        project_root, SESSION_START_CMD
    )
    stop = ClaudeCodeHookRegistrar(STOP_EVENT).is_registered(
        project_root, SESSION_STOP_CMD
    )
    return bool(start) and bool(stop)


def _resolve_writer_for_instance(
    instance: SurfaceInstance,
) -> tuple[Path | None, MarkdownRulesWriter | None]:
    """Recover ``(project_root, writer)`` for an instance, if resolvable.

    The project root is the parent of the artefact's harness directory; for the
    Markdown family the relative ``rules_path`` is stripped from the instance
    path. Returns ``(None, None)`` when the writer is not a known mutating type.
    """
    writer = get_writer(instance.owner)
    if not isinstance(writer, MarkdownRulesWriter):
        return None, None
    project_root = _project_root_from(instance.path, Path(writer.rules_path))
    if project_root is None:
        return None, None
    return project_root, writer


def _orientation_content(project_root: Path) -> SessionPresenceContent:
    """Build orientation content, falling back to a minimal healthy block.

    Repair must not depend on agent config or network state; when the richer
    :class:`SessionPresenceManager` content cannot be built the writer still
    receives a valid, healthy orientation block.
    """
    try:
        from importlib.metadata import version

        return SessionPresenceContent(
            version=version("spec-kitty-cli"),
            project_slug=project_root.name or "unknown",
            health="healthy",
            available_version=None,
        )
    except Exception:  # never block repair on version lookup
        return SessionPresenceContent(
            version="unknown",
            project_slug=project_root.name or "unknown",
            health="healthy",
            available_version=None,
        )


# ---------------------------------------------------------------------------
# Self-registration (fires at import time via providers._discovery)
# ---------------------------------------------------------------------------
SurfaceProviderRegistry.register(
    SurfaceRegistration(
        provider_class=SessionPresenceProvider,
        definitions=(
            context_file_definition(),
            hook_definition(),
            rule_definition(),
        ),
        kind_tokens={
            "context-file": ToolSurfaceKind.CONTEXT_FILE,
            "context_file": ToolSurfaceKind.CONTEXT_FILE,
            "hook": ToolSurfaceKind.HOOK,
            "rule": ToolSurfaceKind.RULE,
        },
        order=20,
    )
)
