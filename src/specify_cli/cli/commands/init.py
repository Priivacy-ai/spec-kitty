"""Init command implementation for Spec Kitty CLI."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Callable

import httpx
import typer
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from ruamel.yaml import YAML

from specify_cli.cli import StepTracker, select_with_arrows, multi_select_with_arrows
from specify_cli.core import (
    AGENT_TOOL_REQUIREMENTS,
    AI_CHOICES,
    DEFAULT_MISSION_KEY,
    DEFAULT_TEMPLATE_REPO,
    MISSION_CHOICES,
    SCRIPT_TYPE_CHOICES,
    check_tool,
    init_git_repo,
    is_git_repo,
)
from specify_cli.core.git_ops import exclude_from_git_index
from specify_cli.core.vcs import (
    is_git_available,
    VCSBackend,
)
from specify_cli.dashboard import ensure_dashboard_running
from specify_cli.gitignore_manager import GitignoreManager, ProtectionResult
from specify_cli.orchestrator.agent_config import (
    AgentConfig,
    AgentSelectionConfig,
    SelectionStrategy,
    save_agent_config,
)
from .init_help import INIT_COMMAND_DOC
from specify_cli.template import (
    GitHubClientError,
    SSL_CONTEXT,
    build_http_client,
    copy_specify_base_from_local,
    copy_specify_base_from_package,
    download_and_extract_template,
    generate_agent_assets,
    get_local_repo_root,
    parse_repo_slug,
    prepare_command_templates,
)

# Module-level variables to hold injected dependencies
_console: Console | None = None
_show_banner: Callable[[], None] | None = None
_activate_mission: Callable[[Path, str, str, Console], str] | None = None
_ensure_executable_scripts: Callable[[Path, StepTracker | None], None] | None = None


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


def _resolve_non_interactive_strategy(
    selected_agents: list[str],
    agent_strategy: str | None,
    preferred_implementer: str | None,
    preferred_reviewer: str | None,
) -> tuple[str, str | None, str | None]:
    if not selected_agents:
        raise ValueError("At least one agent must be selected")

    resolved_strategy = (agent_strategy or "preferred").strip().lower()
    if resolved_strategy not in ("preferred", "random"):
        raise ValueError("Invalid agent strategy. Choose from: preferred, random")

    if resolved_strategy == "random":
        if preferred_implementer or preferred_reviewer:
            raise ValueError("--preferred-implementer/--preferred-reviewer require --agent-strategy preferred")
        return resolved_strategy, None, None

    if preferred_implementer and preferred_implementer not in selected_agents:
        raise ValueError("Preferred implementer must be one of the selected agents")
    if preferred_reviewer and preferred_reviewer not in selected_agents:
        raise ValueError("Preferred reviewer must be one of the selected agents")

    if not preferred_implementer:
        preferred_implementer = selected_agents[0]
    if not preferred_reviewer:
        if len(selected_agents) > 1:
            preferred_reviewer = next(
                agent for agent in selected_agents if agent != preferred_implementer
            )
        else:
            preferred_reviewer = preferred_implementer

    return resolved_strategy, preferred_implementer, preferred_reviewer


def _detect_default_vcs() -> VCSBackend:
    """Detect the default VCS based on tool availability.

    Returns VCSBackend.GIT if git is available.
    Raises VCSNotFoundError if git is not available.

    Note: jj support removed due to sparse checkout incompatibility.
    """
    if is_git_available():
        return VCSBackend.GIT
    else:
        raise VCSNotFoundError("git is not available. Please install git.")


def _display_vcs_info(detected_vcs: VCSBackend, console: Console) -> None:
    """Display informational message about VCS selection.

    Args:
        detected_vcs: The detected/selected VCS backend (always GIT)
        console: Rich console for output
    """
    console.print("[green]✓ git detected[/green] - will be used for version control")


def _save_vcs_config(config_path: Path, detected_vcs: VCSBackend) -> None:
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
        with open(config_file, "r") as f:
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


def _install_git_hooks(project_path: Path, templates_root: Path | None = None, tracker: StepTracker | None = None) -> None:
    """Install git hooks from templates to .git/hooks directory.

    Args:
        project_path: Path to the project root
        templates_root: Path to the templates directory (if available)
        tracker: Optional progress tracker
    """
    git_hooks_dir = project_path / ".git" / "hooks"
    # Use templates_root if available, otherwise fall back to user project (for backwards compat)
    if templates_root:
        template_hooks_dir = templates_root / "git-hooks"
    else:
        template_hooks_dir = project_path / ".kittify" / "templates" / "git-hooks"

    if not git_hooks_dir.exists():
        if tracker:
            tracker.skip("git-hooks", ".git/hooks directory not found")
        return

    if not template_hooks_dir.exists():
        if tracker:
            tracker.skip("git-hooks", "no hook templates found")
        return

    installed_count = 0
    for hook_template in template_hooks_dir.iterdir():
        if hook_template.is_file() and not hook_template.name.startswith('.'):
            hook_dest = git_hooks_dir / hook_template.name
            shutil.copy2(hook_template, hook_dest)
            # Make executable on POSIX systems
            if os.name != "nt":
                hook_dest.chmod(0o755)
            installed_count += 1

    if tracker:
        if installed_count > 0:
            tracker.complete("git-hooks", f"{installed_count} hook(s) installed")
        else:
            tracker.skip("git-hooks", "no hooks to install")


def init(
    project_name: str = typer.Argument(None, help="Name for your new project directory (optional if using --here, or use '.' for current directory)"),
    ai_assistant: str = typer.Option(None, "--ai", help="Comma-separated AI assistants (claude,codex,gemini,...)", rich_help_panel="Selection"),
    script_type: str = typer.Option(None, "--script", help="Script type to use: sh or ps", rich_help_panel="Selection"),
    agent_strategy: str = typer.Option(None, "--agent-strategy", help="Agent selection strategy: preferred or random", rich_help_panel="Selection"),
    preferred_implementer: str = typer.Option(None, "--preferred-implementer", help="Preferred agent for implementation", rich_help_panel="Selection"),
    preferred_reviewer: str = typer.Option(None, "--preferred-reviewer", help="Preferred agent for review", rich_help_panel="Selection"),
    mission_key: str = typer.Option(None, "--mission", hidden=True, help="[DEPRECATED] Mission selection moved to /spec-kitty.specify"),
    ignore_agent_tools: bool = typer.Option(False, "--ignore-agent-tools", help="Skip checks for AI agent tools like Claude Code"),
    no_git: bool = typer.Option(False, "--no-git", help="Skip git repository initialization"),
    here: bool = typer.Option(False, "--here", help="Initialize project in the current directory instead of creating a new one"),
    force: bool = typer.Option(False, "--force", help="Force merge/overwrite when using --here (skip confirmation)"),
    non_interactive: bool = typer.Option(False, "--non-interactive", "--yes", help="Run without interactive prompts (suitable for CI/CD)"),
    skip_tls: bool = typer.Option(False, "--skip-tls", help="Skip SSL/TLS verification (not recommended)"),
    debug: bool = typer.Option(False, "--debug", help="Show verbose diagnostic output for network and extraction failures"),
    github_token: str = typer.Option(None, "--github-token", help="GitHub token to use for API requests (or set GH_TOKEN or GITHUB_TOKEN environment variable)"),
    template_root: str = typer.Option(None, "--template-root", help="Override default template location (useful for development mode)"),
):
    """Initialize a new Spec Kitty project."""
    # Use the injected dependencies
    assert _console is not None
    assert _show_banner is not None
    assert _activate_mission is not None
    assert _ensure_executable_scripts is not None

    _show_banner()
    non_interactive = _is_non_interactive_mode(non_interactive)

    # Handle '.' as shorthand for current directory (equivalent to --here)
    if project_name == ".":
        here = True
        project_name = None  # Clear project_name to use existing validation logic

    if here and project_name:
        _console.print("[red]Error:[/red] Cannot specify both project name and --here flag")
        raise typer.Exit(1)

    if not here and not project_name:
        _console.print("[red]Error:[/red] Must specify either a project name, use '.' for current directory, or use --here flag")
        raise typer.Exit(1)

    if here:
        try:
            project_path = Path.cwd()
            project_name = project_path.name
        except (OSError, FileNotFoundError) as e:
            _console.print("[red]Error:[/red] Cannot access current directory")
            _console.print(f"[dim]{e}[/dim]")
            _console.print("[yellow]Hint:[/yellow] Your current directory may have been deleted or is no longer accessible")
            raise typer.Exit(1)

        existing_items = list(project_path.iterdir())
        if existing_items:
            _console.print(f"[yellow]Warning:[/yellow] Current directory is not empty ({len(existing_items)} items)")
            _console.print("[yellow]Template files will be merged with existing content and may overwrite existing files[/yellow]")
            if force:
                _console.print("[cyan]--force supplied: skipping confirmation and proceeding with merge[/cyan]")
            else:
                if non_interactive:
                    _console.print("[red]Error:[/red] Non-interactive mode requires --force when using --here in a non-empty directory")
                    raise typer.Exit(1)
                response = typer.confirm("Do you want to continue?")
                if not response:
                    _console.print("[yellow]Operation cancelled[/yellow]")
                    raise typer.Exit(0)
    else:
        project_path = Path(project_name).resolve()
        if project_path.exists():
            error_panel = Panel(
                f"Directory '[cyan]{project_name}[/cyan]' already exists\n"
                "Please choose a different project name or remove the existing directory.",
                title="[red]Directory Conflict[/red]",
                border_style="red",
                padding=(1, 2)
            )
            _console.print()
            _console.print(error_panel)
            raise typer.Exit(1)

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

    # Check git only if we might need it (not --no-git)
    # Only set to True if the user wants it and the tool is available
    should_init_git = False
    if not no_git:
        should_init_git = check_tool("git", "https://git-scm.com/downloads")
        if not should_init_git:
            _console.print("[yellow]Git not found - will skip repository initialization[/yellow]")

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
            _console.print(
                f"[red]Error:[/red] Invalid AI assistant(s): {', '.join(invalid_agents)}. "
                f"Choose from: {', '.join(AI_CHOICES.keys())}"
            )
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

    # Check agent tools unless ignored
    if not ignore_agent_tools:
        missing_agents: list[tuple[str, str, str]] = []  # (agent key, display, url)
        for agent_key in selected_agents:
            requirement = AGENT_TOOL_REQUIREMENTS.get(agent_key)
            if not requirement:
                continue
            tool_name, url = requirement
            if not check_tool(tool_name, url, agent_name=agent_key):
                missing_agents.append((agent_key, AI_CHOICES[agent_key], url))

        if missing_agents:
            lines = []
            for agent_key, display_name, url in missing_agents:
                lines.append(f"[cyan]{display_name}[/cyan] ({agent_key}) → install: [cyan]{url}[/cyan]")
            lines.append("")
            lines.append("These tools are optional. You can install them later to enable additional features.")
            warning_panel = Panel(
                "\n".join(lines),
                title="[yellow]Optional Agent Tool(s) Not Found[/yellow]",
                border_style="yellow",
                padding=(1, 2),
            )
            _console.print()
            _console.print(warning_panel)
            # Continue with init instead of blocking

    # ==========================================================================
    # Agent Selection Strategy (for orchestrator)
    # ==========================================================================
    _console.print()
    _console.print("[cyan]Agent Selection Strategy[/cyan]")
    _console.print("[dim]This determines how agents are chosen for implementation and review tasks.[/dim]")
    _console.print()

    strategy_choices = {
        "preferred": "Preferred Agents - You choose which agent implements and which reviews",
        "random": "Random - Randomly select from available agents each time",
    }
    selected_strategy: str
    if agent_strategy:
        selected_strategy = agent_strategy.strip().lower()
        if selected_strategy not in strategy_choices:
            _console.print("[red]Error:[/red] Invalid --agent-strategy. Choose from: preferred, random")
            raise typer.Exit(1)
    elif preferred_implementer or preferred_reviewer:
        selected_strategy = "preferred"
    elif non_interactive:
        selected_strategy = "preferred"
    else:
        selected_strategy = select_with_arrows(
            strategy_choices,
            "How should agents be selected for tasks?",
            default_key="preferred",
        )

    preferred_implementer_value: str | None = preferred_implementer
    preferred_reviewer_value: str | None = preferred_reviewer
    preferred_implementer: str | None = None
    preferred_reviewer: str | None = None

    if selected_strategy == "preferred":
        # Ask for preferred implementer
        agent_display_map = {key: AI_CHOICES[key] for key in selected_agents}

        _console.print()
        if preferred_implementer_value:
            if preferred_implementer_value not in selected_agents:
                _console.print("[red]Error:[/red] --preferred-implementer must be one of the selected agents")
                raise typer.Exit(1)
            preferred_implementer = preferred_implementer_value
        elif non_interactive:
            preferred_implementer = selected_agents[0]
        else:
            preferred_implementer = select_with_arrows(
                agent_display_map,
                "Which agent should be the preferred IMPLEMENTER?",
                default_key=selected_agents[0],
            )

        # Ask for preferred reviewer (prefer different from implementer)
        _console.print()
        if len(selected_agents) > 1:
            # Default to a different agent for review
            default_reviewer = next((a for a in selected_agents if a != preferred_implementer), selected_agents[0])
            if preferred_reviewer_value:
                if preferred_reviewer_value not in selected_agents:
                    _console.print("[red]Error:[/red] --preferred-reviewer must be one of the selected agents")
                    raise typer.Exit(1)
                preferred_reviewer = preferred_reviewer_value
            elif non_interactive:
                preferred_reviewer = default_reviewer
            else:
                preferred_reviewer = select_with_arrows(
                    agent_display_map,
                    "Which agent should be the preferred REVIEWER?",
                    default_key=default_reviewer,
                )
            if preferred_reviewer == preferred_implementer and len(selected_agents) > 1:
                _console.print("[yellow]Note:[/yellow] Same agent for implementation and review (cross-review disabled)")
        else:
            # Only one agent - same for both
            preferred_reviewer = preferred_implementer
            _console.print(f"[dim]Single agent mode: {AI_CHOICES[preferred_implementer]} will do both implementation and review[/dim]")
    else:
        if preferred_implementer_value or preferred_reviewer_value:
            _console.print("[red]Error:[/red] --preferred-implementer/--preferred-reviewer require --agent-strategy preferred")
            raise typer.Exit(1)

    if non_interactive:
        try:
            resolved_strategy, resolved_impl, resolved_rev = _resolve_non_interactive_strategy(
                selected_agents,
                selected_strategy,
                preferred_implementer_value,
                preferred_reviewer_value,
            )
        except ValueError as exc:
            _console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(1)
        selected_strategy = resolved_strategy
        if selected_strategy == "preferred":
            preferred_implementer = resolved_impl
            preferred_reviewer = resolved_rev

    # Build agent config to save later
    agent_config = AgentConfig(
        available=selected_agents,
        selection=AgentSelectionConfig(
            strategy=SelectionStrategy(selected_strategy),
            preferred_implementer=preferred_implementer,
            preferred_reviewer=preferred_reviewer,
        ),
    )

    # Determine script type (explicit or auto-detect)
    if script_type:
        if script_type not in SCRIPT_TYPE_CHOICES:
            _console.print(f"[red]Error:[/red] Invalid script type '{script_type}'. Choose from: {', '.join(SCRIPT_TYPE_CHOICES.keys())}")
            raise typer.Exit(1)
        selected_script = script_type
    else:
        # Auto-detect based on platform
        selected_script = "ps" if os.name == "nt" else "sh"
        _console.print(f"[dim]Auto-detected script type:[/dim] [cyan]{SCRIPT_TYPE_CHOICES[selected_script]}[/cyan]")

    # Mission selection deprecated - missions are now per-feature
    if mission_key:
        _console.print("[yellow]Warning:[/yellow] The --mission flag is deprecated. Missions are now selected per-feature during /spec-kitty.specify")
        _console.print("[dim]Ignoring --mission flag and continuing with initialization...[/dim]")
        _console.print()

    # No longer select a project-level mission - just use software-dev for initial setup
    selected_mission = DEFAULT_MISSION_KEY
    mission_display = MISSION_CHOICES.get(selected_mission, "Software Dev Kitty")

    template_mode = "package"
    local_repo = get_local_repo_root(override_path=template_root)
    if local_repo is not None:
        template_mode = "local"
        if debug:
            _console.print(f"[cyan]Using local templates from[/cyan] {local_repo}")

    repo_owner = repo_name = None
    remote_slug_env = os.environ.get("SPECIFY_TEMPLATE_REPO")
    if remote_slug_env:
        try:
            repo_owner, repo_name = parse_repo_slug(remote_slug_env)
        except ValueError as exc:
            _console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(1)
        template_mode = "remote"
        if debug:
            _console.print(f"[cyan]Using remote templates from[/cyan] {repo_owner}/{repo_name}")
    elif template_mode == "package" and debug:
        _console.print("[cyan]Using templates bundled with specify_cli package[/cyan]")

    ai_display = ", ".join(AI_CHOICES[key] for key in selected_agents)
    _console.print(f"[cyan]Selected AI assistant(s):[/cyan] {ai_display}")
    _console.print(f"[cyan]Selected script type:[/cyan] {selected_script}")
    _console.print(f"[cyan]Selected mission:[/cyan] {mission_display}")

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
    tracker.add("script-select", "Select script type")
    tracker.complete("script-select", selected_script)
    tracker.add("mission-select", "Select mission")
    tracker.complete("mission-select", mission_display)
    tracker.add("mission-activate", "Activate mission")
    for agent_key in selected_agents:
        label = AI_CHOICES[agent_key]
        tracker.add(f"{agent_key}-fetch", f"{label}: fetch latest release")
        tracker.add(f"{agent_key}-download", f"{label}: download template")
        tracker.add(f"{agent_key}-extract", f"{label}: extract template")
        tracker.add(f"{agent_key}-zip-list", f"{label}: archive contents")
        tracker.add(f"{agent_key}-extracted-summary", f"{label}: extraction summary")
        tracker.add(f"{agent_key}-cleanup", f"{label}: cleanup")
    for key, label in [
        ("chmod", "Ensure scripts executable"),
        ("git", "Initialize git repository"),
        ("final", "Finalize"),
    ]:
        tracker.add(key, label)

    if template_mode in ("local", "package") and not here and not project_path.exists():
        project_path.mkdir(parents=True)

    command_templates_dir: Path | None = None
    render_templates_dir: Path | None = None
    templates_root: Path | None = None  # Track template source for later use
    base_prepared = False
    if template_mode == "remote" and (repo_owner is None or repo_name is None):
        repo_owner, repo_name = parse_repo_slug(DEFAULT_TEMPLATE_REPO)

    with Live(tracker.render(), console=_console, refresh_per_second=8, transient=True) as live:
        tracker.attach_refresh(lambda: live.update(tracker.render()))
        try:
            # Create a httpx client with verify based on skip_tls
            local_client = build_http_client(skip_tls=skip_tls)

            for index, agent_key in enumerate(selected_agents):
                if template_mode in ("local", "package"):
                    source_detail = "local checkout" if template_mode == "local" else "packaged data"
                    tracker.start(f"{agent_key}-fetch")
                    tracker.complete(f"{agent_key}-fetch", source_detail)
                    tracker.start(f"{agent_key}-download")
                    tracker.complete(f"{agent_key}-download", "local files")
                    tracker.start(f"{agent_key}-extract")
                    try:
                        if not base_prepared:
                            if template_mode == "local":
                                command_templates_dir = copy_specify_base_from_local(local_repo, project_path, selected_script)
                            else:
                                command_templates_dir = copy_specify_base_from_package(project_path, selected_script)
                            base_prepared = True
                            # Track templates root for later use (AGENTS.md, .claudeignore, git-hooks)
                            if command_templates_dir:
                                templates_root = command_templates_dir.parent
                        if command_templates_dir is None:
                            raise RuntimeError("Command templates directory was not prepared")
                        if render_templates_dir is None:
                            mission_templates_dir = (
                                project_path
                                / ".kittify"
                                / "missions"
                                / selected_mission
                                / "command-templates"
                            )
                            render_templates_dir = prepare_command_templates(
                                command_templates_dir,
                                mission_templates_dir,
                            )
                        generate_agent_assets(render_templates_dir, project_path, agent_key, selected_script)
                    except Exception as exc:
                        tracker.error(f"{agent_key}-extract", str(exc))
                        raise
                    else:
                        tracker.complete(f"{agent_key}-extract", "commands generated")
                        tracker.start(f"{agent_key}-zip-list")
                        tracker.complete(f"{agent_key}-zip-list", "templates ready")
                        tracker.start(f"{agent_key}-extracted-summary")
                        tracker.complete(f"{agent_key}-extracted-summary", "commands ready")
                        tracker.start(f"{agent_key}-cleanup")
                        tracker.complete(f"{agent_key}-cleanup", "done")
                else:
                    is_current_dir_flag = here if index == 0 else True
                    allow_existing_flag = index > 0
                    download_and_extract_template(
                        project_path,
                        agent_key,
                        selected_script,
                        is_current_dir_flag,
                        verbose=False,
                        tracker=tracker,
                        tracker_prefix=agent_key,
                        allow_existing=allow_existing_flag,
                        client=local_client,
                        debug=debug,
                        github_token=github_token,
                        repo_owner=repo_owner,
                        repo_name=repo_name,
                    )

            tracker.start("mission-activate")
            try:
                mission_status = _activate_mission(project_path, selected_mission, mission_display, _console)
            except Exception as exc:
                tracker.error("mission-activate", str(exc))
                raise
            else:
                tracker.complete("mission-activate", mission_status)

            # Ensure scripts are executable (POSIX)
            _ensure_executable_scripts(project_path, tracker=tracker)

            # Git step - must happen BEFORE hook installation
            if not no_git:
                tracker.start("git")
                if is_git_repo(project_path):
                    tracker.complete("git", "existing repo detected")
                elif should_init_git:
                    if init_git_repo(project_path, quiet=True):
                        tracker.complete("git", "initialized")
                    else:
                        tracker.error("git", "init failed")
                        raise RuntimeError("Git repository initialization failed")
                else:
                    tracker.skip("git", "git not available")
            else:
                tracker.skip("git", "--no-git flag")

            # Exclude .worktrees/ from git index (defensive protection)
            if not no_git and is_git_repo(project_path):
                exclude_from_git_index(project_path, [".worktrees/"])

            # Install git hooks AFTER git is initialized
            if not no_git and is_git_repo(project_path):
                tracker.add("git-hooks", "Install git hooks")
                tracker.start("git-hooks")
                _install_git_hooks(project_path, templates_root=templates_root, tracker=tracker)

            tracker.complete("final", "project ready")
        except Exception as e:
            tracker.error("final", str(e))
            _console.print(Panel(f"Initialization failed: {e}", title="Failure", border_style="red"))
            if debug:
                _env_pairs = [
                    ("Python", sys.version.split()[0]),
                    ("Platform", sys.platform),
                    ("CWD", str(Path.cwd())),
                ]
                _label_width = max(len(k) for k, _ in _env_pairs)
                env_lines = [f"{k.ljust(_label_width)} → [bright_black]{v}[/bright_black]" for k, v in _env_pairs]
                _console.print(Panel("\n".join(env_lines), title="Debug Environment", border_style="magenta"))
            if not here and project_path.exists():
                shutil.rmtree(project_path)
            raise typer.Exit(1)
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
        "windsurf": ".windsurf/",
        "kilocode": ".kilocode/",
        "auggie": ".augment/",
        "copilot": ".github/",
        "roo": ".roo/",
        "q": ".amazonq/"
    }

    notice_entries = []
    for agent_key in selected_agents:
        folder = agent_folder_map.get(agent_key)
        if folder:
            notice_entries.append((AI_CHOICES[agent_key], folder))

    if notice_entries:
        body_lines = [
            "Some agents may store credentials, auth tokens, or other identifying and private artifacts in the agent folder within your project.",
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

    steps_lines.append(f"{step_num}. Available missions: [cyan]software-dev[/cyan], [cyan]research[/cyan] (selected per-feature during [cyan]/spec-kitty.specify[/cyan])")
    step_num += 1

    steps_lines.append(f"{step_num}. Start using slash commands with your AI agent (in workflow order):")
    step_num += 1

    steps_lines.append("   - [cyan]/spec-kitty.dashboard[/] - Open the real-time kanban dashboard")
    steps_lines.append("   - [cyan]/spec-kitty.constitution[/] - Establish project principles")
    steps_lines.append("   - [cyan]/spec-kitty.specify[/] - Create baseline specification")
    steps_lines.append("   - [cyan]/spec-kitty.plan[/] - Create implementation plan")
    steps_lines.append("   - [cyan]/spec-kitty.research[/] - Run mission-specific Phase 0 research scaffolding")
    steps_lines.append("   - [cyan]/spec-kitty.tasks[/] - Generate tasks and kanban-ready prompt files")
    steps_lines.append("   - [cyan]/spec-kitty.implement[/] - Execute implementation from /tasks/doing/")
    steps_lines.append("   - [cyan]/spec-kitty.review[/] - Review prompts and move them to /tasks/done/")
    steps_lines.append("   - [cyan]/spec-kitty.accept[/] - Run acceptance checks and verify feature complete")
    steps_lines.append("   - [cyan]/spec-kitty.merge[/] - Merge feature into main and cleanup worktree")

    steps_panel = Panel("\n".join(steps_lines), title="Next Steps", border_style="cyan", padding=(1,2))
    _console.print()
    _console.print(steps_panel)

    enhancement_lines = [
        "Optional commands that you can use for your specs [bright_black](improve quality & confidence)[/bright_black]",
        "",
        f"○ [cyan]/spec-kitty.clarify[/] [bright_black](optional)[/bright_black] - Ask structured questions to de-risk ambiguous areas before planning (run before [cyan]/spec-kitty.plan[/] if used)",
        f"○ [cyan]/spec-kitty.analyze[/] [bright_black](optional)[/bright_black] - Cross-artifact consistency & alignment report (after [cyan]/spec-kitty.tasks[/], before [cyan]/spec-kitty.implement[/])",
        f"○ [cyan]/spec-kitty.checklist[/] [bright_black](optional)[/bright_black] - Generate quality checklists to validate requirements completeness, clarity, and consistency (after [cyan]/spec-kitty.plan[/])"
    ]
    enhancements_panel = Panel("\n".join(enhancement_lines), title="Enhancement Commands", border_style="cyan", padding=(1,2))
    _console.print()
    _console.print(enhancements_panel)

    # Start or reconnect to the dashboard server as a detached background process
    _console.print()
    try:
        dashboard_url, port, started = ensure_dashboard_running(project_path)

        title = "[bold green]Spec Kitty Dashboard Started[/bold green]" if started else "[bold green]Spec Kitty Dashboard Ready[/bold green]"
        status_line = (
            "[dim]The dashboard is running in the background and will continue even after\n"
            "this command exits. It will automatically update as you work.[/dim]"
            if started
            else "[dim]An existing dashboard instance is running and ready.[/dim]"
        )

        dashboard_panel = Panel(
            f"[bold cyan]Dashboard URL:[/bold cyan] {dashboard_url}\n"
            f"[bold cyan]Port:[/bold cyan] {port}\n\n"
            f"{status_line}\n\n"
            f"[yellow]Tip:[/yellow] Run [cyan]/spec-kitty.dashboard[/cyan] or [cyan]spec-kitty dashboard[/cyan] to open it in your browser",
            title=title,
            border_style="green",
            padding=(1, 2)
        )
        _console.print(dashboard_panel)
        _console.print()
    except Exception as e:
        _console.print(f"[yellow]Warning: Could not start dashboard: {e}[/yellow]")
        _console.print("[dim]Continuing without dashboard...[/dim]")

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

    # Copy AGENTS.md from template source (not user project)
    if templates_root:
        agents_target = project_path / ".kittify" / "AGENTS.md"
        agents_template = templates_root / "AGENTS.md"
        if not agents_target.exists() and agents_template.exists():
            shutil.copy2(agents_template, agents_target)

        # Generate .claudeignore from template source
        claudeignore_template = templates_root / "claudeignore-template"
        claudeignore_dest = project_path / ".claudeignore"
        if claudeignore_template.exists() and not claudeignore_dest.exists():
            shutil.copy2(claudeignore_template, claudeignore_dest)
            _console.print("[dim]Created .claudeignore to optimize AI assistant scanning[/dim]")

    # Create project metadata for upgrade tracking
    try:
        from datetime import datetime
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
        _console.print(f"[dim]Saved agent configuration ({selected_strategy} strategy)[/dim]")
    except Exception as e:
        # Don't fail init if agent config creation fails
        _console.print(f"[dim]Note: Could not save agent config: {e}[/dim]")

    # Clean up templates directory - it's only needed during init
    # User projects should only have the generated agent commands, not the source templates
    templates_dir = project_path / ".kittify" / "templates"
    if templates_dir.exists():
        try:
            shutil.rmtree(templates_dir)
        except PermissionError:
            _console.print("[dim]Note: Could not remove .kittify/templates/ (permission denied)[/dim]")
        except Exception as e:
            # Log but don't fail init if cleanup fails
            _console.print(f"[dim]Note: Could not remove .kittify/templates/: {e}[/dim]")


def register_init_command(
    app: typer.Typer,
    *,
    console: Console,
    show_banner: Callable[[], None],
    activate_mission: Callable[[Path, str, str, Console], str],
    ensure_executable_scripts: Callable[[Path, StepTracker | None], None],
) -> None:
    """Register the init command with injected dependencies."""
    global _console, _show_banner, _activate_mission, _ensure_executable_scripts

    # Store the dependencies
    _console = console
    _show_banner = show_banner
    _activate_mission = activate_mission
    _ensure_executable_scripts = ensure_executable_scripts

    # Set the docstring
    init.__doc__ = INIT_COMMAND_DOC

    # Ensure app is in multi-command mode by checking if there are existing commands
    # If not, add a hidden dummy command to force subcommand mode
    if not hasattr(app, 'registered_commands') or not getattr(app, 'registered_commands'):
        @app.command("__force_multi_command_mode__", hidden=True)
        def _dummy():
            pass

    # Register the command with explicit name to ensure it's always a subcommand
    app.command("init")(init)
