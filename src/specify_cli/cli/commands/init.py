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
from specify_cli.dashboard import ensure_dashboard_running
from specify_cli.gitignore_manager import GitignoreManager, ProtectionResult
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
)

# Module-level variables to hold injected dependencies
_console: Console | None = None
_show_banner: Callable[[], None] | None = None
_activate_mission: Callable[[Path, str, str, Console], str] | None = None
_ensure_executable_scripts: Callable[[Path, StepTracker | None], None] | None = None


def init(
    project_name: str = typer.Argument(None, help="Name for your new project directory (optional if using --here, or use '.' for current directory)"),
    ai_assistant: str = typer.Option(None, "--ai", help="Comma-separated AI assistants (claude,codex,gemini,...)", rich_help_panel="Selection"),
    script_type: str = typer.Option(None, "--script", help="Script type to use: sh or ps", rich_help_panel="Selection"),
    mission_key: str = typer.Option(None, "--mission", help="Mission key to activate (software-dev, research, ...)", rich_help_panel="Selection"),
    ignore_agent_tools: bool = typer.Option(False, "--ignore-agent-tools", help="Skip checks for AI agent tools like Claude Code"),
    no_git: bool = typer.Option(False, "--no-git", help="Skip git repository initialization"),
    here: bool = typer.Option(False, "--here", help="Initialize project in the current directory instead of creating a new one"),
    force: bool = typer.Option(False, "--force", help="Force merge/overwrite when using --here (skip confirmation)"),
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
            if not check_tool(tool_name, url):
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

    # Determine script type (explicit, interactive, or OS default)
    if script_type:
        if script_type not in SCRIPT_TYPE_CHOICES:
            _console.print(f"[red]Error:[/red] Invalid script type '{script_type}'. Choose from: {', '.join(SCRIPT_TYPE_CHOICES.keys())}")
            raise typer.Exit(1)
        selected_script = script_type
    else:
        # Auto-detect default
        default_script = "ps" if os.name == "nt" else "sh"
        # Provide interactive selection similar to AI if stdin is a TTY
        if sys.stdin.isatty():
            selected_script = select_with_arrows(SCRIPT_TYPE_CHOICES, "Choose script type (or press Enter)", default_script)
        else:
            selected_script = default_script

    # Determine mission selection (explicit, interactive, or default)
    if mission_key:
        mission_key = mission_key.strip().lower()
        if mission_key not in MISSION_CHOICES:
            _console.print(f"[red]Error:[/red] Invalid mission '{mission_key}'. Choose from: {', '.join(MISSION_CHOICES.keys())}")
            raise typer.Exit(1)
        selected_mission = mission_key
    else:
        default_mission = DEFAULT_MISSION_KEY if DEFAULT_MISSION_KEY in MISSION_CHOICES else next(iter(MISSION_CHOICES))
        if sys.stdin.isatty():
            selected_mission = select_with_arrows(MISSION_CHOICES, "Choose mission (or press Enter)", default_mission)
        else:
            selected_mission = default_mission

    mission_display = MISSION_CHOICES[selected_mission]

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

    commands_dir: Path | None = None
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
                                commands_dir = copy_specify_base_from_local(local_repo, project_path, selected_script)
                            else:
                                commands_dir = copy_specify_base_from_package(project_path, selected_script)
                            base_prepared = True
                        if commands_dir is None:
                            raise RuntimeError("Command templates directory was not prepared")
                        generate_agent_assets(commands_dir, project_path, agent_key, selected_script)
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

            # Git step
            if not no_git:
                tracker.start("git")
                if is_git_repo(project_path):
                    tracker.complete("git", "existing repo detected")
                elif should_init_git:
                    if init_git_repo(project_path, quiet=True):
                        tracker.complete("git", "initialized")
                    else:
                        tracker.error("git", "init failed")
                else:
                    tracker.skip("git", "git not available")
            else:
                tracker.skip("git", "--no-git flag")

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

    steps_lines.append(f"{step_num}. Active mission: [cyan]{mission_display}[/cyan] (change later with [cyan]spec-kitty mission switch[/cyan])")
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

    agents_target = project_path / ".kittify" / "AGENTS.md"
    agents_template = project_path / ".kittify" / "templates" / "AGENTS.md"
    if not agents_target.exists() and agents_template.exists():
        shutil.copy2(agents_template, agents_target)


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
