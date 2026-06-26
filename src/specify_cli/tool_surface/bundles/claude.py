"""Claude Code plugin bundle projection and validation.

Projects the canonical tool surfaces into Claude Code's plugin bundle layout
(``.claude-plugin/``) and validates the result before publication. The bundle
includes command skills, doctrine skills, agent profiles, hooks, and MCP config;
it deliberately **excludes** session-presence files (CLAUDE.md, AGENTS.md, rules
/ steering files), which are project-install surfaces, not bundle components.

**Scope guard (FR-016, C-006):** :meth:`ClaudeCodeBundleProjector.project`
writes only the staging files under the caller-supplied ``output_dir`` and
returns an inert :class:`PluginBundle` descriptor. It never installs, registers,
enables, or publishes the bundle to any marketplace.

:class:`ClaudeBundleProjector` (WP04) is the CLI-driven build projector that
calls :func:`~specify_cli.skills.command_installer._render_command_skill` to
generate SKILL.md files and :class:`ClaudeCodeProfileRenderer` to render agent
profiles; it is distinct from :class:`ClaudeCodeBundleProjector` (plan-level
projector used by the WP09 surface-plan pipeline).
"""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from pathlib import Path

import typer

from ..enums import SurfaceKind
from ..findings import (
    BUNDLE_COMPONENT_MISSING,
    SEVERITY_ERROR,
    SurfaceFinding,
    make_finding,
)
from ..model import SurfacePlan
from .model import (
    TARGET_CLAUDE_CODE,
    BundleValidationResult,
    PluginBundle,
)
from .projection import (
    BUNDLE_SURFACE_KINDS,
    bundle_entries_for_plans,
    plugin_manifest_payload,
    write_bundle,
)
from ._builder import (
    MIN_SKILL_COUNT,
    BuildError,
    get_cli_version,
    is_semver,
    write_json,
)
from .claude_wrapper import write_wrappers

# Claude Code plugin layout: manifest lives under ``.claude-plugin/``; hooks and
# MCP config use ``hooks/hooks.json`` and ``.mcp.json`` (NEVER ``settings.json``).
_MANIFEST_DIR = ".claude-plugin"
_MANIFEST_NAME = "plugin.json"

# Per-kind destination prefix inside the Claude Code bundle package.
_CLAUDE_LAYOUT: dict[SurfaceKind, str] = {
    SurfaceKind.COMMAND_SKILL: "skills",
    SurfaceKind.DOCTRINE_SKILL: "skills",
    SurfaceKind.AGENT_PROFILE: "agents",
    SurfaceKind.HOOK: "hooks",
    SurfaceKind.NATIVE_CONFIG: "",
}

# Required surface kinds a complete Claude Code bundle must carry.
_REQUIRED_KINDS: frozenset[SurfaceKind] = frozenset(
    {
        SurfaceKind.COMMAND_SKILL,
        SurfaceKind.DOCTRINE_SKILL,
        SurfaceKind.AGENT_PROFILE,
    }
)


def _agent_filename(profile_id: str) -> str:
    """Claude Code uses plain ``<profile-id>.md`` agent files."""
    return f"{profile_id}.md"


class ClaudeCodeBundleProjector:
    """Project + validate Claude Code plugin bundles (staging only)."""

    distribution_target = TARGET_CLAUDE_CODE
    # Manifest sits under ``.claude-plugin/`` for this target.
    manifest_relative_path = f"{_MANIFEST_DIR}/{_MANIFEST_NAME}"

    def project(
        self,
        plan: Sequence[SurfacePlan],
        project_root: Path,
        output_dir: Path,
    ) -> PluginBundle:
        """Project all bundleable surfaces into the Claude Code layout.

        Writes staging files under ``output_dir`` and returns an inert
        :class:`PluginBundle` descriptor. No install/publish side effect occurs.
        """
        entries = bundle_entries_for_plans(
            plan,
            project_root,
            layout=_CLAUDE_LAYOUT,
            agent_filename=_agent_filename,
            bundle_kinds=BUNDLE_SURFACE_KINDS,
        )
        manifest_rel = self.manifest_relative_path
        manifest = plugin_manifest_payload(self.distribution_target)
        write_bundle(output_dir, entries, manifest_rel, manifest)
        return PluginBundle(
            distribution_target=self.distribution_target,
            entries=entries,
            manifest_path=output_dir / manifest_rel,
        )

    def validate(
        self,
        bundle: PluginBundle,
        required_surface_kinds: set[SurfaceKind] | None = None,
    ) -> BundleValidationResult:
        """Validate that every required surface kind is present in ``bundle``."""
        required = (
            frozenset(required_surface_kinds)
            if required_surface_kinds is not None
            else _REQUIRED_KINDS
        )
        return _validate_bundle(bundle, required)


def _validate_bundle(
    bundle: PluginBundle,
    required: frozenset[SurfaceKind],
) -> BundleValidationResult:
    """Shared validation: report a finding for every missing required kind."""
    present = bundle.kinds()
    missing: list[SurfaceFinding] = []
    warnings: list[str] = []
    for kind in sorted(required - present, key=str):
        missing.append(
            make_finding(
                BUNDLE_COMPONENT_MISSING,
                SEVERITY_ERROR,
                (
                    f"Plugin bundle for {bundle.distribution_target} is missing "
                    f"required surface kind: {kind}"
                ),
                surface_id=f"{bundle.distribution_target}.{kind}",
                details={"distribution_target": bundle.distribution_target},
            )
        )
    if bundle.manifest_path is None:
        warnings.append(
            f"Bundle for {bundle.distribution_target} has no manifest path."
        )
    return BundleValidationResult(
        passed=not missing,
        missing_surfaces=tuple(missing),
        warnings=tuple(warnings),
        distribution_target=bundle.distribution_target,
    )


class ClaudeBundleProjector:
    """CLI-driven build projector for Claude Code plugin bundles (WP04).

    Produces a complete, ``claude plugin validate --strict``-ready bundle at
    ``<output_dir>/claude-code/`` containing:

    * ``.claude-plugin/plugin.json`` — manifest with real version from
      ``importlib.metadata``.
    * ``skills/<name>/SKILL.md`` — all canonical command skills rendered via
      the shared ``command_installer`` infrastructure.
    * ``agents/<profile-id>.md`` — built-in agent profiles rendered via
      :class:`ClaudeCodeProfileRenderer`.
    * ``hooks/hooks.json`` — empty placeholder (non-trivial hooks added later).
    * ``bin/spec-kitty-wrapper`` — bash runtime bootstrap with uvx fallback.
    * ``bin/spec-kitty-wrapper.cmd`` — Windows CMD equivalent.
    * ``marketplace.json`` — git-based distribution catalog (written alongside
      the bundle under ``<output_dir>/marketplace.json``).

    **Scope guard (FR-016, C-006):** :meth:`build` writes staging files only
    under the caller-supplied ``output_dir``.  It never installs, registers,
    enables, or publishes the bundle.
    """

    def __init__(self, output_dir: Path) -> None:
        self._output_dir = output_dir

    def build(self, *, skip_validate: bool = False) -> Path:
        """Build the Claude Code plugin bundle.

        Returns the bundle directory path.

        Raises
        ------
        BuildError
            When a required build step fails (e.g. no profiles found, too
            few skills).
        typer.Exit
            When ``claude plugin validate --strict`` exits non-zero.
        """
        bundle_dir = self._output_dir / "claude-code"
        bundle_dir.mkdir(parents=True, exist_ok=True)

        version = get_cli_version()
        if not is_semver(version):
            typer.echo(
                f"Warning: version {version!r} is not a clean semver "
                "string; the validator may reject it.",
                err=True,
            )

        # Step 1: render and install canonical command skills.
        skill_count = self._copy_skills(bundle_dir, version)
        typer.echo(f"Skills: {skill_count} written to {bundle_dir / 'skills'}")

        # Step 2: render built-in agent profiles and hooks placeholder.
        agent_count = self._copy_agents(bundle_dir)
        typer.echo(f"Agents: {agent_count} written to {bundle_dir / 'agents'}")

        # Step 3: write the plugin manifest after components exist so Claude's
        # validator can resolve explicit component paths.
        self._generate_plugin_json(bundle_dir, version)

        # Step 4: generate runtime bootstrap wrappers (bash + Windows CMD).
        write_wrappers(bundle_dir, version)
        typer.echo(f"Wrappers: bin/spec-kitty-wrapper written to {bundle_dir / 'bin'}")

        # Step 5: generate marketplace.json alongside the bundle.
        self._write_marketplace_json(self._output_dir, version)
        typer.echo(f"Marketplace: marketplace.json written to {self._output_dir}")

        # Step 6: run the Claude CLI validator (optional).
        self._validate(bundle_dir, skip=skip_validate)

        return bundle_dir

    def _generate_plugin_json(self, bundle_dir: Path, version: str) -> None:
        """Write ``.claude-plugin/plugin.json`` with real version metadata."""
        skills = _skill_manifest_paths(bundle_dir)
        agents = _agent_manifest_paths(bundle_dir)
        if not skills:
            raise BuildError("Claude plugin manifest has no skills to declare.")
        if not agents:
            raise BuildError("Claude plugin manifest has no agents to declare.")

        manifest: dict[str, object] = {
            "name": "spec-kitty",
            "displayName": "Spec Kitty",
            "version": version,
            "description": (
                "Spec-Driven Development toolkit — spec, plan, implement, review, merge."
            ),
            "author": {
                "name": "Priivacy AI",
                "url": "https://github.com/Priivacy-ai/spec-kitty",
            },
            "skills": skills,
            "agents": agents,
        }
        if _has_non_trivial_hooks(bundle_dir):
            manifest["hooks"] = "hooks/hooks.json"
        write_json(bundle_dir / ".claude-plugin" / "plugin.json", manifest)

    def _copy_skills(self, bundle_dir: Path, version: str) -> int:
        """Render canonical command skills into ``bundle_dir/skills/``.

        Returns the number of skill files written.
        """
        from specify_cli.skills.command_installer import (
            CANONICAL_COMMANDS,
            _render_command_skill,
        )

        skills_dst = bundle_dir / "skills"
        skills_dst.mkdir(parents=True, exist_ok=True)

        # The shared command renderer supports codex/vibe/pi/letta agent keys;
        # the plugin bundle uses "codex" to produce an identical SKILL.md body
        # (the body and frontmatter shape are agent-invariant per the renderer's
        # single-body invariant — only the skill name prefix differs, and that
        # is always "spec-kitty.<command>" regardless of agent key).
        render_key = "codex"

        count = 0
        for command in CANONICAL_COMMANDS:
            skill_bytes = _render_command_skill(Path("/"), command, render_key, version)
            skill_dir = skills_dst / f"spec-kitty.{command}"
            skill_dir.mkdir(parents=True, exist_ok=True)
            (skill_dir / "SKILL.md").write_bytes(skill_bytes)
            count += 1

        if count < MIN_SKILL_COUNT:
            raise BuildError(
                f"Expected at least {MIN_SKILL_COUNT} skills, found {count}. "
                "Check CANONICAL_COMMANDS in command_installer."
            )
        return count

    def _copy_agents(self, bundle_dir: Path) -> int:
        """Render built-in agent profiles into ``bundle_dir/agents/``.

        Returns the number of profile files written.

        Raises
        ------
        BuildError
            When no built-in profiles are found (FR-020).
        """
        import yaml
        from doctrine.agent_profiles.profile import AgentProfile
        from specify_cli.tool_surface.profiles.renderers import ClaudeCodeProfileRenderer

        agents_dst = bundle_dir / "agents"
        agents_dst.mkdir(parents=True, exist_ok=True)

        # Also create the hooks placeholder so the bundle layout is complete.
        hooks_dir = bundle_dir / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        hooks_json = hooks_dir / "hooks.json"
        if not hooks_json.exists():
            write_json(hooks_json, {"hooks": {}})

        profiles_src = _built_in_profiles_dir()
        renderer = ClaudeCodeProfileRenderer()
        count = 0
        for yaml_file in sorted(profiles_src.glob("*.agent.yaml")):
            data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
            profile = AgentProfile.model_validate(data)
            rendered = renderer.render(profile)
            (agents_dst / f"{profile.profile_id}.md").write_text(
                rendered, encoding="utf-8"
            )
            count += 1

        if count == 0:
            raise BuildError(
                f"No built-in agent profiles found under {profiles_src}. "
                "Bundle must include profiles per FR-020. "
                "Check package data configuration."
            )
        return count

    def _write_marketplace_json(self, output_dir: Path, version: str) -> None:
        """Write ``marketplace.json`` alongside the bundle in *output_dir*.

        The marketplace catalog enables ``claude plugin marketplace add <repo-url>``
        for git-based plugin installs.  The file is a build artefact (excluded
        from the source repository via ``.gitignore``).

        Parameters
        ----------
        output_dir:
            The root output directory (e.g. ``dist/spec-kitty-plugins/``).
            ``marketplace.json`` is written here, not inside the bundle subdir.
        version:
            The resolved package version string; embedded in the catalog for
            informational purposes.
        """
        catalog: dict[str, object] = {
            "name": "spec-kitty-plugins",
            "version": version,
            "interface": {"displayName": "Spec Kitty Plugins"},
            "plugins": [
                {
                    "name": "spec-kitty",
                    "source": {
                        "source": "git-subdir",
                        "url": "https://github.com/Priivacy-ai/spec-kitty.git",
                        "path": "dist/spec-kitty-plugins/claude-code",
                    },
                    "policy": {
                        "installation": "AVAILABLE",
                        "authentication": "ON_INSTALL",
                    },
                    "category": "Developer Tools",
                },
            ],
        }
        write_json(output_dir / "marketplace.json", catalog)

    def _validate(self, bundle_dir: Path, *, skip: bool) -> None:
        """Run ``claude plugin validate --strict`` against the bundle.

        Skips gracefully when the ``claude`` CLI is not on PATH; surfaces
        errors and exits non-zero on validation failure.
        """
        if skip:
            typer.echo(
                "Warning: Skipping claude plugin validate (--skip-validate passed).",
                err=True,
            )
            return
        try:
            result = subprocess.run(
                ["claude", "plugin", "validate", "--strict", str(bundle_dir)],
                capture_output=True,
                text=True,
                timeout=30,
            )
        except FileNotFoundError:
            typer.echo(
                "Warning: claude CLI not found — skipping validation. "
                "Install claude CLI to validate.",
                err=True,
            )
            return
        if result.returncode != 0:
            typer.echo("claude plugin validate --strict FAILED:", err=True)
            if result.stdout:
                typer.echo(result.stdout, err=True)
            if result.stderr:
                typer.echo(result.stderr, err=True)
            raise typer.Exit(code=1)
        typer.echo("claude plugin validate --strict passed.")


def _built_in_profiles_dir() -> Path:
    """Return the path to the built-in agent profiles source directory."""
    import doctrine  # noqa: PLC0415 — deferred to avoid import-time side effects

    return Path(doctrine.__file__).parent / "agent_profiles" / "built-in"


def _plugin_relative_path(path: Path, bundle_dir: Path) -> str:
    """Return Claude plugin manifest path syntax for *path* under *bundle_dir*."""
    return f"./{path.relative_to(bundle_dir).as_posix()}"


def _skill_manifest_paths(bundle_dir: Path) -> list[str]:
    """Return explicit Claude plugin manifest entries for staged skill dirs."""
    return sorted(
        _plugin_relative_path(skill_file.parent, bundle_dir)
        for skill_file in (bundle_dir / "skills").glob("*/SKILL.md")
    )


def _agent_manifest_paths(bundle_dir: Path) -> list[str]:
    """Return explicit Claude plugin manifest entries for staged agent files."""
    return sorted(
        _plugin_relative_path(agent_file, bundle_dir)
        for agent_file in (bundle_dir / "agents").glob("*.md")
    )


def _has_non_trivial_hooks(bundle_dir: Path) -> bool:
    """Return ``True`` when ``hooks/hooks.json`` contains non-empty content.

    The placeholder written by :meth:`ClaudeBundleProjector._copy_agents` is
    ``{"hooks": {}}``.  A ``hooks.json`` with only an empty hooks record is not
    considered non-trivial; the ``"hooks"`` pointer is omitted from the manifest
    in that case so repeated builds produce byte-identical manifests.
    """
    import json as _json  # noqa: PLC0415

    hooks_json = bundle_dir / "hooks" / "hooks.json"
    if not hooks_json.exists():
        return False
    try:
        data = _json.loads(hooks_json.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return False
    if isinstance(data, dict) and set(data) == {"hooks"} and not data["hooks"]:
        return False
    return bool(data)  # non-empty dict / list counts as non-trivial


# Re-export so ``copilot``/``vscode`` projectors can share validation logic.
__all__ = [
    "ClaudeCodeBundleProjector",
    "ClaudeBundleProjector",
    # BuildError: demoted — re-exported from _builder; no cross-module src/
    # from-import callers of this module (WP01 harden-dead-symbol-gate-01KW0RJR).
    "_validate_bundle",
]
