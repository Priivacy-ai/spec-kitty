"""Init command implementation for Spec Kitty CLI."""

from __future__ import annotations

import logging
import os
import shutil
import sys
from datetime import datetime, UTC
from pathlib import Path
from collections.abc import Callable

import typer
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from ruamel.yaml import YAML

from specify_cli.cli import StepTracker, multi_select_with_arrows
from specify_cli.core import (
    AI_CHOICES,
)
from specify_cli.core.vcs import (
    is_git_available,
    VCSBackend,
)
from specify_cli.gitignore_manager import GitignoreManager
from specify_cli.core.agent_config import (
    AgentConfig,
    save_agent_config,
)
from .init_help import INIT_COMMAND_DOC
from specify_cli.template import (
    copy_charter_templates,
    copy_specify_base_from_local,
    copy_specify_base_from_package,
    get_local_repo_root,
)
from specify_cli.runtime.home import get_kittify_home, get_package_asset_root
from specify_cli.skills.installer import install_skills_for_agent
from specify_cli.skills.manifest import ManagedSkillManifest, save_manifest

# Module-level variables to hold injected dependencies
_console: Console | None = None
_show_banner: Callable[[], None] | None = None
_ensure_executable_scripts: Callable[[Path, StepTracker | None], None] | None = None


# =============================================================================
# Global runtime detection for streamlined init
# =============================================================================

_logger = logging.getLogger(__name__)
_EVENT_LOG_GITATTRIBUTES_ENTRY = "kitty-specs/**/status.events.jsonl merge=spec-kitty-event-log"


def _has_global_runtime() -> bool:
    """Check whether the global runtime (~/.kittify/) has populated missions.

    Returns True when ``~/.kittify/missions/`` exists and contains at
    least one subdirectory (indicating ``ensure_runtime()`` has run).
    """
    try:
        global_home = get_kittify_home()
        missions_dir = global_home / "missions"
        if not missions_dir.is_dir():
            return False
        # Check for at least one mission subdirectory
        return any(p.is_dir() for p in missions_dir.iterdir())
    except (RuntimeError, OSError):
        return False


def _prepare_project_minimal(project_path: Path) -> None:
    """Create the minimal project-specific .kittify/ skeleton.

    When the global runtime exists, init only needs to create the
    project-local directory structure.  Shared assets (missions,
    templates, scripts, AGENTS.md) are resolved from ~/.kittify/
    at runtime via the 4-tier resolver.

    Creates:
        - .kittify/                (project root)
        - .kittify/memory/         (project-local memory/context files)
    """
    kittify = project_path / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    (kittify / "memory").mkdir(exist_ok=True)
    _logger.debug("Minimal project skeleton created at %s", kittify)


def _ensure_event_log_merge_attributes(project_path: Path) -> bool:
    """Ensure new projects track status event logs with the semantic merge driver."""
    attributes_path = project_path / ".gitattributes"
    lines: list[str] = []
    if attributes_path.exists():
        lines = attributes_path.read_text(encoding="utf-8").splitlines()
        if _EVENT_LOG_GITATTRIBUTES_ENTRY in lines:
            return False

    lines.append(_EVENT_LOG_GITATTRIBUTES_ENTRY)
    attributes_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return True


def _get_package_templates_root() -> Path | None:
    """Return the package-bundled templates directory (read-only).

    This is the ``src/doctrine/templates/`` directory which contains
    ``command-templates/``, ``AGENTS.md``, etc.

    Returns None if the templates directory cannot be located.
    """
    try:
        pkg_root = get_package_asset_root()  # .../doctrine/missions/
        templates_dir = pkg_root.parent / "templates"
        if templates_dir.is_dir():
            return Path(templates_dir)
    except FileNotFoundError:
        pass
    return None


def _resolve_mission_command_templates_dir(
    project_path: Path,
    mission: str,
    *,
    scratch_parent: Path | None = None,
) -> Path:
    """Materialize the resolved command templates for one mission into scratch space.

    Each template file is resolved independently through the runtime's 5-tier
    precedence chain so mixed-tier command sets still produce the correct
    effective directory for init-time consumers.
    """
    from specify_cli.runtime.resolver import resolve_command

    candidate_dirs: list[Path] = [
        project_path / ".kittify" / "overrides" / "command-templates",
        project_path / ".kittify" / "command-templates",
    ]

    try:
        global_home = get_kittify_home()
    except RuntimeError:
        global_home = None
    if global_home is not None:
        candidate_dirs.extend(
            [
                global_home / "missions" / mission / "command-templates",
                global_home / "command-templates",
            ]
        )

    try:
        package_root = get_package_asset_root()
    except FileNotFoundError:
        package_root = None
    if package_root is not None:
        candidate_dirs.append(package_root / mission / "command-templates")

    template_names: set[str] = set()
    for candidate_dir in candidate_dirs:
        if not candidate_dir.is_dir():
            continue
        template_names.update(
            path.name for path in candidate_dir.glob("*.md") if path.is_file()
        )

    scratch_base = scratch_parent or (project_path / ".kittify")
    resolved_dir = scratch_base / f".resolved-command-templates-{mission}"
    if resolved_dir.exists():
        shutil.rmtree(resolved_dir)
    resolved_dir.mkdir(parents=True, exist_ok=True)

    for template_name in sorted(template_names):
        try:
            resolved = resolve_command(template_name, project_path, mission)
        except FileNotFoundError:
            continue
        shutil.copy2(resolved.path, resolved_dir / template_name)

    return resolved_dir








# =============================================================================
# VCS Detection and Configuration
# =============================================================================


class VCSNotFoundError(Exception):
    """Raised when no VCS tools are available."""

    pass


def _is_truthy_env(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _is_non_interactive_mode(flag: bool) -> bool:
    if flag:
        return True
    if _is_truthy_env(os.environ.get("SPEC_KITTY_NON_INTERACTIVE")):
        return True
    return not sys.stdin.isatty()



def _detect_default_vcs() -> VCSBackend:
    """Detect the default VCS based on tool availability.

    Returns VCSBackend.GIT if git is available.
    Raises VCSNotFoundError if git is not available.

    Note: Only git is supported.
    """
    if is_git_available():
        return VCSBackend.GIT
    else:
        raise VCSNotFoundError("git is not available. Please install git.")


def _display_vcs_info(_detected_vcs: VCSBackend, console: Console) -> None:
    """Display informational message about VCS selection.

    Args:
        detected_vcs: The detected/selected VCS backend (always GIT)
        console: Rich console for output
    """
    console.print("[green]✓ git detected[/green] - will be used for version control")


def _save_vcs_config(config_path: Path, _detected_vcs: VCSBackend) -> None:
    """Save VCS preference to config.yaml.

    Args:
        config_path: Path to .kittify directory
        detected_vcs: The detected/selected VCS backend (always GIT)
    """
    config_file = config_path / "config.yaml"

    yaml = YAML()
    yaml.preserve_quotes = True

    # Load existing config or create new
    if config_file.exists():
        with open(config_file) as f:
            config = yaml.load(f) or {}
    else:
        config = {}
        config_path.mkdir(parents=True, exist_ok=True)

    # Add/update vcs section (git only)
    config["vcs"] = {
        "type": "git",
    }

    # Write back
    with open(config_file, "w") as f:
        yaml.dump(config, f)


def init(  # noqa: C901
    project_name: str | None = typer.Argument(
        None,
        help="Name for your new project directory (omit to initialize current directory)",
    ),
    ai_assistant: str | None = typer.Option(None, "--ai", help="Comma-separated AI assistants (claude,codex,gemini,...)", rich_help_panel="Selection"),
    non_interactive: bool = typer.Option(False, "--non-interactive", "--yes", help="Run without interactive prompts (suitable for CI/CD)"),
) -> None:
    """Initialize a new Spec Kitty project."""
    # Use the injected dependencies
    assert _console is not None
    assert _show_banner is not None
    assert _ensure_executable_scripts is not None

    _show_banner()
    non_interactive = _is_non_interactive_mode(non_interactive)

    # Handle '.' as shorthand for current directory
    if project_name == ".":
        project_name = None

    # Default behavior: no positional argument initializes in the current directory.
    here = project_name is None

    if here:
        try:
            project_path = Path.cwd()
            project_name = project_path.name
        except (OSError, FileNotFoundError) as e:
            _console.print("[red]Error:[/red] Cannot access current directory")
            _console.print(f"[dim]{e}[/dim]")
            _console.print("[yellow]Hint:[/yellow] Your current directory may have been deleted or is no longer accessible")
            raise typer.Exit(1) from e
    else:
        assert project_name is not None
        project_path = Path(project_name).resolve()
        if project_path.exists():
            error_panel = Panel(
                f"Directory '[cyan]{project_name}[/cyan]' already exists\nPlease choose a different project name or remove the existing directory.",
                title="[red]Directory Conflict[/red]",
                border_style="red",
                padding=(1, 2),
            )
            _console.print()
            _console.print(error_panel)
            raise typer.Exit(1)

    # T004 — Idempotency check: exit 0 cleanly if already initialized.
    # This prevents silent re-init and makes CI-driven init safe to re-run.
    _config_yaml = project_path / ".kittify" / "config.yaml"
    if _config_yaml.exists():
        _console.print(
            Panel(
                "[yellow]Already initialized.[/yellow]\n"
                "Run [cyan]spec-kitty upgrade[/cyan] to migrate to the latest version.",
                title="[yellow]Already Initialized[/yellow]",
                border_style="yellow",
                padding=(1, 2),
            )
        )
        raise typer.Exit(0)

    current_dir = Path.cwd()

    setup_lines = [
        "[cyan]Specify Project Setup[/cyan]",
        "",
        f"{'Project':<15} [green]{project_path.name}[/green]",
        f"{'Working Path':<15} [dim]{current_dir}[/dim]",
    ]

    # Add target path only if different from working dir
    if not here:
        setup_lines.append(f"{'Target Path':<15} [dim]{project_path}[/dim]")

    _console.print(Panel("\n".join(setup_lines), border_style="cyan", padding=(1, 2)))

    # Detect VCS (git only, jj support removed)
    selected_vcs: VCSBackend | None = None
    try:
        selected_vcs = _detect_default_vcs()
        _console.print()
        _display_vcs_info(selected_vcs, _console)
        _console.print()
    except VCSNotFoundError:
        # git not available - not an error, just informational
        selected_vcs = None
        _console.print("[yellow]ℹ git not detected[/yellow] - install git for version control")

    if ai_assistant:
        raw_agents = [part.strip().lower() for part in ai_assistant.replace(";", ",").split(",") if part.strip()]
        if not raw_agents:
            _console.print("[red]Error:[/red] --ai flag did not contain any valid agent identifiers")
            raise typer.Exit(1)
        selected_agents: list[str] = []
        seen_agents: set[str] = set()
        invalid_agents: list[str] = []
        for key in raw_agents:
            if key not in AI_CHOICES:
                invalid_agents.append(key)
                continue
            if key not in seen_agents:
                selected_agents.append(key)
                seen_agents.add(key)
        if invalid_agents:
            _console.print(f"[red]Error:[/red] Invalid AI assistant(s): {', '.join(invalid_agents)}. Choose from: {', '.join(AI_CHOICES.keys())}")
            raise typer.Exit(1)
    else:
        if non_interactive:
            _console.print("[red]Error:[/red] --ai is required in non-interactive mode")
            raise typer.Exit(1)
        selected_agents = multi_select_with_arrows(
            AI_CHOICES,
            "Choose your AI assistant(s):",
            default_keys=["copilot"],
        )

    if not selected_agents:
        _console.print("[red]Error:[/red] No AI assistants selected")
        raise typer.Exit(1)

    # Build agent config to save later
    agent_config = AgentConfig(
        available=selected_agents,
        auto_commit=True,
    )

    template_mode = "package"
    local_repo = get_local_repo_root()
    if local_repo is not None:
        template_mode = "local"

    ai_display = ", ".join(AI_CHOICES[key] for key in selected_agents)
    _console.print(f"[cyan]Selected AI assistant(s):[/cyan] {ai_display}")

    # Download and set up project
    # New tree-based progress (no emojis); include earlier substeps
    tracker = StepTracker("Initialize Specify Project")
    # Flag to allow suppressing legacy headings
    sys._specify_tracker_active = True
    # Pre steps recorded as completed before live rendering
    tracker.add("precheck", "Check required tools")
    tracker.complete("precheck", "ok")
    tracker.add("ai-select", "Select AI assistant(s)")
    tracker.complete("ai-select", ai_display)
    tracker.add("runtime", "Bootstrap global runtime")
    tracker.add("skills", "Install skills globally")
    for agent_key in selected_agents:
        label = AI_CHOICES[agent_key]
        tracker.add(f"{agent_key}-fetch", f"{label}: fetch latest release")
        tracker.add(f"{agent_key}-download", f"{label}: download template")
        tracker.add(f"{agent_key}-extract", f"{label}: extract template")
        tracker.add(f"{agent_key}-zip-list", f"{label}: archive contents")
        tracker.add(f"{agent_key}-extracted-summary", f"{label}: extraction summary")
        tracker.add(f"{agent_key}-cleanup", f"{label}: cleanup")
        tracker.add(f"{agent_key}-skills", f"{label}: install skill pack")
    for key, label in [
        ("chmod", "Ensure scripts executable"),
        ("final", "Finalize"),
    ]:
        tracker.add(key, label)

    if not here and not project_path.exists():
        project_path.mkdir(parents=True)

    templates_root: Path | None = None  # Track template source for later use
    base_prepared = False

    with Live(tracker.render(), console=_console, refresh_per_second=8, transient=True) as live:
        tracker.attach_refresh(lambda: live.update(tracker.render()))
        try:
            # Bootstrap global runtime — hard fail on error (FR-003)
            tracker.start("runtime")
            try:
                from specify_cli.runtime.bootstrap import ensure_runtime

                ensure_runtime()
                tracker.complete("runtime", "ok")
            except Exception as exc:
                tracker.error("runtime", str(exc))
                _console.print(f"[red]Error:[/red] Failed to bootstrap global runtime: {exc}")
                raise typer.Exit(1) from exc

            # Install skills globally (FR-007)
            tracker.start("skills")
            try:
                from specify_cli.skills.registry import SkillRegistry
                from specify_cli.skills.paths import iter_installable_agents
                from specify_cli.skills.installer import _sync_global_skill

                skill_registry = SkillRegistry.from_package()
                skills = skill_registry.discover_skills()
                for skill in skills:
                    for agent_key in iter_installable_agents():
                        from specify_cli.skills.paths import get_primary_global_skill_root
                        global_root = get_primary_global_skill_root(agent_key)
                        if global_root is not None:
                            _sync_global_skill(skill, global_root)
                tracker.complete("skills", f"{len(skills)} skills installed globally")
            except Exception as exc:
                tracker.error("skills", str(exc))
                _console.print(f"[yellow]Warning:[/yellow] Skill installation incomplete: {exc}")
                # Non-fatal: skills can be re-installed on next upgrade

            # Skill pack installation state
            from specify_cli import __version__ as _sk_version

            _now_iso = datetime.now(UTC).isoformat()
            skill_manifest = ManagedSkillManifest(
                created_at=_now_iso,
                updated_at=_now_iso,
                spec_kitty_version=_sk_version,
            )
            skill_registry_per_agent: SkillRegistry | None = None
            shared_root_installed: set[str] = set()

            for agent_key in selected_agents:
                source_detail = "local checkout" if template_mode == "local" else "packaged data"
                tracker.start(f"{agent_key}-fetch")
                tracker.complete(f"{agent_key}-fetch", source_detail)
                tracker.start(f"{agent_key}-download")
                tracker.complete(f"{agent_key}-download", "local files")
                tracker.start(f"{agent_key}-extract")
                try:
                    if not base_prepared:
                        # Global runtime was bootstrapped above; use minimal project setup
                        use_global = _has_global_runtime() and template_mode == "package"
                        if use_global:
                            _prepare_project_minimal(project_path)
                            copy_charter_templates(project_path)
                            pkg_templates = _get_package_templates_root()
                            if pkg_templates is not None:
                                templates_root = pkg_templates
                            else:
                                # Package templates not found -- fall back to full copy
                                use_global = False
                        if not use_global:
                            if template_mode == "local":
                                assert local_repo is not None
                                copy_specify_base_from_local(local_repo, project_path)
                            else:
                                copy_specify_base_from_package(project_path)
                            # Track templates root for later use (AGENTS.md, .claudeignore)
                            pkg_templates = _get_package_templates_root()
                            if pkg_templates is not None:
                                templates_root = pkg_templates
                        base_prepared = True
                except Exception as exc:
                    tracker.error(f"{agent_key}-extract", str(exc))
                    raise
                else:
                    tracker.complete(f"{agent_key}-extract", "agent configured (commands managed globally)")
                    tracker.start(f"{agent_key}-zip-list")
                    tracker.complete(f"{agent_key}-zip-list", "templates ready")
                    tracker.start(f"{agent_key}-extracted-summary")
                    tracker.complete(f"{agent_key}-extracted-summary", "commands ready")
                    tracker.start(f"{agent_key}-cleanup")
                    tracker.complete(f"{agent_key}-cleanup", "done")

                # Install skill pack for this agent (non-fatal).
                # T002: Only NATIVE-class agents install into per-agent directories
                # (e.g. .claude/skills/, .qwen/skills/).  SHARED-class agents
                # previously installed into .agents/skills/ — that shared root is
                # intentionally NOT seeded during init (FR-003).
                tracker.start(f"{agent_key}-skills")
                try:
                    from specify_cli.core.config import AGENT_SKILL_CONFIG, SKILL_CLASS_SHARED, SKILL_CLASS_WRAPPER

                    agent_skill_class = (AGENT_SKILL_CONFIG.get(agent_key) or {}).get("class", "")
                    if agent_skill_class == SKILL_CLASS_WRAPPER:
                        # WRAPPER agents have no installable root.
                        tracker.complete(f"{agent_key}-skills", "skipped (wrapper)")
                    elif agent_key in ("codex", "vibe"):
                        # Codex and Vibe receive Spec Kitty's slash commands as
                        # Agent Skills packages rendered into .agents/skills/.
                        from specify_cli.skills import command_installer  # noqa: PLC0415
                        from specify_cli.skills.vibe_config import ensure_project_skill_path  # noqa: PLC0415

                        report = command_installer.install(project_path, agent_key)
                        if agent_key == "vibe":
                            ensure_project_skill_path(project_path)
                        installed = len(report.added) + len(report.reused_shared)
                        tracker.complete(
                            f"{agent_key}-skills",
                            f"{installed} command skills installed",
                        )
                    elif agent_skill_class == SKILL_CLASS_SHARED:
                        # Other SHARED-class agents install their canonical skills
                        # via the legacy installer path below (doctrine/tactic
                        # skills), not command-skills.
                        tracker.complete(f"{agent_key}-skills", "skipped (global runtime)")
                    else:
                        if skill_registry_per_agent is None:
                            if template_mode == "local" and local_repo is not None:
                                skill_registry_per_agent = SkillRegistry.from_local_repo(local_repo)
                            else:
                                skill_registry_per_agent = SkillRegistry.from_package()
                        agent_skills = skill_registry_per_agent.discover_skills()
                        if agent_skills:
                            entries = install_skills_for_agent(
                                project_path,
                                agent_key,
                                agent_skills,
                                shared_root_installed=shared_root_installed,
                            )
                            for entry in entries:
                                skill_manifest.add_entry(entry)
                            tracker.complete(f"{agent_key}-skills", f"{len(agent_skills)} skills installed")
                        else:
                            tracker.complete(f"{agent_key}-skills", "no skills found")
                except Exception as exc:
                    tracker.error(f"{agent_key}-skills", str(exc))
                    _logger.warning("Skill installation failed for %s: %s", agent_key, exc)
                    # Non-fatal: wrappers are already installed

            # Save managed skill manifest
            if skill_manifest.entries:
                save_manifest(skill_manifest, project_path)

            # Ensure scripts are executable (POSIX)
            _ensure_executable_scripts(project_path, tracker)

            # T001: No git initialization. init is file-creation-only.
            # Git management is the user's responsibility. Running init inside
            # an existing repo leaves the repo untouched.

            tracker.complete("final", "project ready")
        except typer.Exit:
            raise
        except Exception as e:
            tracker.error("final", str(e))
            _console.print(Panel(f"Initialization failed: {e}", title="Failure", border_style="red"))
            if not here and project_path.exists():
                shutil.rmtree(project_path)
            raise typer.Exit(1) from e
        finally:
            # Force final render
            pass

    # Final static tree (ensures finished state visible after Live context ends)
    _console.print(tracker.render())
    _console.print("\n[bold green]Project ready.[/bold green]")

    # Agent folder security notice
    agent_folder_map = {
        "claude": ".claude/",
        "gemini": ".gemini/",
        "cursor": ".cursor/",
        "qwen": ".qwen/",
        "opencode": ".opencode/",
        "codex": ".codex/",
        "vibe": ".vibe/",
        "windsurf": ".windsurf/",
        "kilocode": ".kilocode/",
        "auggie": ".augment/",
        "copilot": ".github/",
        "antigravity": ".agent/",
        "roo": ".roo/",
        "q": ".amazonq/",
        "kiro": ".kiro/",
    }

    notice_entries = []
    for agent_key in selected_agents:
        folder = agent_folder_map.get(agent_key)
        if folder:
            notice_entries.append((AI_CHOICES[agent_key], folder))

    if notice_entries:
        body_lines = [
            "Some agents may store credentials, auth tokens, or other identifying and private artifacts in the agent folder within your project.",  # noqa: E501
            "Consider adding the following folders (or subsets) to [cyan].gitignore[/cyan]:",
            "",
        ]
        body_lines.extend(f"- {display}: [cyan]{folder}[/cyan]" for display, folder in notice_entries)
        security_notice = Panel(
            "\n".join(body_lines),
            title="[yellow]Agent Folder Security[/yellow]",
            border_style="yellow",
            padding=(1, 2),
        )
        _console.print()
        _console.print(security_notice)

    # Boxed "Next steps" section
    steps_lines = []
    step_num = 1
    if not here:
        steps_lines.append(f"{step_num}. Go to the project folder: [cyan]cd {project_name}[/cyan]")
    else:
        steps_lines.append(f"{step_num}. You're already in the project directory!")
    step_num += 1

    steps_lines.append(
        f"{step_num}. Available missions: [cyan]software-dev[/cyan], [cyan]research[/cyan] (selected per-mission during [cyan]/spec-kitty.specify[/cyan])"  # noqa: E501
    )
    step_num += 1

    steps_lines.append(f"{step_num}. Build your specification with slash commands (in workflow order):")
    step_num += 1

    steps_lines.append("   - [cyan]/spec-kitty.dashboard[/] - Open the real-time kanban dashboard")
    steps_lines.append("   - [cyan]/spec-kitty.charter[/]   - Establish project principles")
    steps_lines.append("   - [cyan]/spec-kitty.specify[/]   - Create baseline specification")
    steps_lines.append("   - [cyan]/spec-kitty.plan[/]      - Create implementation plan")
    steps_lines.append("   - [cyan]/spec-kitty.research[/]  - Run mission-specific Phase 0 research scaffolding")
    steps_lines.append("   - [cyan]/spec-kitty.tasks[/]     - Generate work packages")
    steps_lines.append("   - [cyan]/spec-kitty.review[/]    - Review prompts and move them to /tasks/done/")
    steps_lines.append("   - [cyan]/spec-kitty.accept[/]    - Run acceptance checks and verify mission complete")
    steps_lines.append("   - [cyan]/spec-kitty.merge[/]     - Merge mission into target branch and cleanup worktree")
    step_num += 1

    # T003: Canonical post-#555 agent loop path
    steps_lines.append(f"{step_num}. Run your agent loop (canonical workflow):")
    steps_lines.append("   [dim]Enter the mission loop:[/dim]")
    steps_lines.append("     [cyan]spec-kitty next --agent <agent> --mission <slug>[/cyan]")
    steps_lines.append("")
    steps_lines.append("   [dim]Your agent will call per-WP actions:[/dim]")
    steps_lines.append("     [cyan]spec-kitty agent action implement <WP> --agent <name>[/cyan]  [dim](implement a work package)[/dim]")  # noqa: E501
    steps_lines.append("     [cyan]spec-kitty agent action review    <WP> --agent <name>[/cyan]  [dim](review a work package)[/dim]")  # noqa: E501

    steps_panel = Panel("\n".join(steps_lines), title="Next Steps", border_style="cyan", padding=(1, 2))
    _console.print()
    _console.print(steps_panel)

    # Vibe-specific next steps (shown when vibe is among selected agents)
    if "vibe" in selected_agents:
        vibe_steps_lines = [
            "1. Install Vibe if you haven't already:",
            "     [cyan]curl -LsSf https://mistral.ai/vibe/install.sh | bash[/cyan]",
            "   or",
            "     [cyan]uv tool install mistral-vibe[/cyan]",
            "2. Launch Vibe in this project:",
            "     [cyan]vibe[/cyan]",
            "3. Inside Vibe, invoke your first workflow:",
            "     [cyan]/spec-kitty.specify <describe what you want to build>[/cyan]",
        ]
        vibe_panel = Panel(
            "\n".join(vibe_steps_lines),
            title="Next Steps for Mistral Vibe",
            border_style="cyan",
            padding=(1, 2),
        )
        _console.print()
        _console.print(vibe_panel)

    enhancement_lines = [
        "Optional commands that you can use for your specs [bright_black](improve quality & confidence)[/bright_black]",
        "",
        "○ [cyan]/spec-kitty.analyze[/] [bright_black](optional)[/bright_black] - Cross-artifact consistency & alignment report (after [cyan]/spec-kitty.tasks[/])",  # noqa: E501
        "○ [cyan]/spec-kitty.checklist[/] [bright_black](optional)[/bright_black] - Generate quality checklists to validate requirements completeness, clarity, and consistency (after [cyan]/spec-kitty.plan[/])",  # noqa: E501
    ]
    enhancements_panel = Panel("\n".join(enhancement_lines), title="Enhancement Commands", border_style="cyan", padding=(1, 2))
    _console.print()
    _console.print(enhancements_panel)

    # Protect ALL agent directories in .gitignore
    manager = GitignoreManager(project_path)
    result = manager.protect_all_agents()  # Note: ALL agents, not just selected

    # Display results to user
    if result.modified:
        _console.print("[cyan]Updated .gitignore to exclude AI agent directories:[/cyan]")
        for entry in result.entries_added:
            _console.print(f"  • {entry}")
        if result.entries_skipped:
            _console.print(f"  ({len(result.entries_skipped)} already protected)")
    elif result.entries_skipped:
        _console.print(f"[dim]All {len(result.entries_skipped)} agent directories already in .gitignore[/dim]")

    # Show warnings (especially for .github/)
    for warning in result.warnings:
        _console.print(f"[yellow]⚠️  {warning}[/yellow]")

    # Show errors if any
    for error in result.errors:
        _console.print(f"[red]❌ {error}[/red]")

    if _ensure_event_log_merge_attributes(project_path):
        _console.print("[dim]Updated .gitattributes to semantically merge status.events.jsonl[/dim]")

    # Copy AGENTS.md from template source (not user project)
    # In global runtime mode, AGENTS.md resolves from ~/.kittify/ so skip copying.
    if templates_root and not _has_global_runtime():
        agents_target = project_path / ".kittify" / "AGENTS.md"
        agents_template = templates_root / "AGENTS.md"
        if not agents_target.exists() and agents_template.exists():
            shutil.copy2(agents_template, agents_target)

    # Generate .claudeignore from template source (always -- project-specific)
    if templates_root:
        claudeignore_template = templates_root / "claudeignore-template"
        claudeignore_dest = project_path / ".claudeignore"
        if claudeignore_template.exists() and not claudeignore_dest.exists():
            shutil.copy2(claudeignore_template, claudeignore_dest)
            _console.print("[dim]Created .claudeignore to optimize AI assistant scanning[/dim]")

    # Create project metadata for upgrade tracking
    try:
        import platform as plat
        import sys as system
        from specify_cli import __version__
        from specify_cli.upgrade.metadata import ProjectMetadata

        metadata = ProjectMetadata(
            version=__version__,
            initialized_at=datetime.now(),
            python_version=plat.python_version(),
            platform=system.platform,
            platform_version=plat.platform(),
        )
        metadata.save(project_path / ".kittify")
    except Exception as e:
        # Don't fail init if metadata creation fails
        _console.print(f"[dim]Note: Could not create project metadata: {e}[/dim]")

    # Save VCS preference to config.yaml
    if selected_vcs:
        try:
            _save_vcs_config(project_path / ".kittify", selected_vcs)
        except Exception as e:
            # Don't fail init if VCS config creation fails
            _console.print(f"[dim]Note: Could not save VCS config: {e}[/dim]")

    # Save agent configuration to config.yaml
    try:
        save_agent_config(project_path, agent_config)
        _console.print("[dim]Saved agent configuration[/dim]")
    except Exception as e:
        # Don't fail init if agent config creation fails
        _console.print(f"[dim]Note: Could not save agent config: {e}[/dim]")

    # Clean up temporary directories used during init.
    # In full-copy mode: .kittify/templates/ holds the copied base templates.
    # In global-runtime mode: .kittify/.scratch/ holds base command templates
    # and .kittify/.resolved-* / .kittify/.merged-* hold resolver output.
    # User projects should only have the generated agent commands, not the sources.
    for cleanup_name in ("templates", "command-templates", ".scratch"):
        cleanup_dir = project_path / ".kittify" / cleanup_name
        if cleanup_dir.exists():
            try:
                shutil.rmtree(cleanup_dir)
            except PermissionError:
                _console.print(f"[dim]Note: Could not remove .kittify/{cleanup_name}/ (permission denied)[/dim]")
            except Exception as e:
                _console.print(f"[dim]Note: Could not remove .kittify/{cleanup_name}/: {e}[/dim]")
    # Also clean up resolver scratch dirs (.resolved-* and .merged-*)
    kittify_dir = project_path / ".kittify"
    if kittify_dir.is_dir():
        for scratch in kittify_dir.iterdir():
            if scratch.is_dir() and (scratch.name.startswith(".resolved-") or scratch.name.startswith(".merged-")):
                try:  # noqa: SIM105
                    shutil.rmtree(scratch)
                except Exception:  # noqa: S110
                    pass  # best-effort cleanup



def register_init_command(
    app: typer.Typer,
    *,
    console: Console,
    show_banner: Callable[[], None],
    activate_mission: Callable[[Path, str, str, Console], str] | None = None,
    ensure_executable_scripts: Callable[[Path, StepTracker | None], None],
) -> None:
    """Register the init command with injected dependencies."""
    global _console, _show_banner, _ensure_executable_scripts

    # Store the dependencies
    _console = console
    _show_banner = show_banner
    _ensure_executable_scripts = ensure_executable_scripts

    # Set the docstring
    init.__doc__ = INIT_COMMAND_DOC

    # Ensure app is in multi-command mode by checking if there are existing commands
    # If not, add a hidden dummy command to force subcommand mode
    if not hasattr(app, "registered_commands") or not app.registered_commands:

        @app.command("__force_multi_command_mode__", hidden=True)
        def _dummy() -> None:
            pass

    # Register the command with explicit name to ensure it's always a subcommand
    app.command("init")(init)
