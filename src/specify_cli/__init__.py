#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "typer",
#     "rich",
#     "platformdirs",
#     "readchar",
#     "httpx",
# ]
# ///
"""
Spec Kitty CLI - setup tooling for Spec Kitty projects.

Usage:
    spec-kitty init <project-name>
    spec-kitty init .
    spec-kitty init --here
"""

import os
import subprocess
import sys
import zipfile
import tempfile
import shutil
import shlex
import json
import re
from pathlib import Path
from typing import List, Optional, Tuple
from importlib.resources import files

import typer
import httpx
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.text import Text
from rich.live import Live
from rich.align import Align
from rich.table import Table
from rich.tree import Tree
from typer.core import TyperGroup

# For cross-platform keyboard input
import readchar
import ssl
import truststore

# Dashboard server
from specify_cli.dashboard import start_dashboard
from specify_cli.acceptance import (
    AcceptanceError,
    AcceptanceResult,
    AcceptanceSummary,
    choose_mode,
    collect_feature_summary,
    detect_feature_slug,
    perform_acceptance,
)
from specify_cli.tasks_support import LANES, find_repo_root, TaskCliError

ssl_context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
client = httpx.Client(verify=ssl_context)

def _github_token(cli_token: str | None = None) -> str | None:
    """Return sanitized GitHub token (cli arg takes precedence) or None."""
    return ((cli_token or os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN") or "").strip()) or None

def _github_auth_headers(cli_token: str | None = None) -> dict:
    """Return Authorization header dict only when a non-empty token exists."""
    token = _github_token(cli_token)
    return {"Authorization": f"Bearer {token}"} if token else {}

AI_CHOICES = {
    "copilot": "GitHub Copilot",
    "claude": "Claude Code",
    "gemini": "Gemini CLI",
    "cursor": "Cursor",
    "qwen": "Qwen Code",
    "opencode": "opencode",
    "codex": "Codex CLI",
    "windsurf": "Windsurf",
    "kilocode": "Kilo Code",
    "auggie": "Auggie CLI",
    "roo": "Roo Code",
    "q": "Amazon Q Developer CLI",
}

MISSION_CHOICES = {
    "software-dev": "Software Dev Kitty",
    "research": "Deep Research Kitty",
}

DEFAULT_MISSION_KEY = "software-dev"

AGENT_TOOL_REQUIREMENTS: dict[str, tuple[str, str]] = {
    "claude": ("claude", "https://docs.anthropic.com/en/docs/claude-code/setup"),
    "gemini": ("gemini", "https://github.com/google-gemini/gemini-cli"),
    "qwen": ("qwen", "https://github.com/QwenLM/qwen-code"),
    "opencode": ("opencode", "https://opencode.ai"),
    "codex": ("codex", "https://github.com/openai/codex"),
    "auggie": ("auggie", "https://docs.augmentcode.com/cli/setup-auggie/install-auggie-cli"),
    "q": ("q", "https://aws.amazon.com/developer/learning/q-developer-cli/"),
}

SCRIPT_TYPE_CHOICES = {"sh": "POSIX Shell (bash/zsh)", "ps": "PowerShell"}

CLAUDE_LOCAL_PATH = Path.home() / ".claude" / "local" / "claude"

DEFAULT_TEMPLATE_REPO = "spec-kitty/spec-kitty"

AGENT_COMMAND_CONFIG: dict[str, dict[str, str]] = {
    "claude": {"dir": ".claude/commands", "ext": "md", "arg_format": "$ARGUMENTS"},
    "gemini": {"dir": ".gemini/commands", "ext": "toml", "arg_format": "{{args}}"},
    "copilot": {"dir": ".github/prompts", "ext": "prompt.md", "arg_format": "$ARGUMENTS"},
    "cursor": {"dir": ".cursor/commands", "ext": "md", "arg_format": "$ARGUMENTS"},
    "qwen": {"dir": ".qwen/commands", "ext": "toml", "arg_format": "{{args}}"},
    "opencode": {"dir": ".opencode/command", "ext": "md", "arg_format": "$ARGUMENTS"},
    "windsurf": {"dir": ".windsurf/workflows", "ext": "md", "arg_format": "$ARGUMENTS"},
    "codex": {"dir": ".codex/prompts", "ext": "md", "arg_format": "$ARGUMENTS"},
    "kilocode": {"dir": ".kilocode/workflows", "ext": "md", "arg_format": "$ARGUMENTS"},
    "auggie": {"dir": ".augment/commands", "ext": "md", "arg_format": "$ARGUMENTS"},
    "roo": {"dir": ".roo/commands", "ext": "md", "arg_format": "$ARGUMENTS"},
    "q": {"dir": ".amazonq/prompts", "ext": "md", "arg_format": "$ARGUMENTS"},
}

BANNER = """
`````````````````````````````````````````````````````````

           ▄█▄_                            ╓▄█_
          ▐█ └▀█▄_                      ▄█▀▀ ╙█
          █"    `▀█▄                  ▄█▀     █▌
         ▐█        ▀█▄▄▄██████████▄▄▄█"       ▐█
         ║█          "` ╟█  ╫▌  █" '"          █
         ║█              ▀  ╚▀  ▀             J█
          █                                   █▌
          █▀   ,▄█████▄           ,▄█████▄_   █▌
         █▌  ▄█"      "██       ╓█▀      `▀█_  █▌
        ▐█__▐▌    ▄██▄  ╙█_____╒█   ▄██,   '█__'█
        █▀▀▀█M    ████   █▀╙\"\"\"██  ▐████    █▀▀"█▌
        █─  ╟█    ╙▀▀"  ██      █╕  ╙▀▀    ╓█   ║▌
   ╓▄▄▄▄█▌,_ ╙█▄_    _▄█▀╒██████ ▀█╥     ▄█▀ __,██▄▄▄▄
        ╚█'`"  `╙▀▀▀▀▀"   `▀██▀    "▀▀▀▀▀"   ""▐█
     _,▄▄███▀               █▌              ▀▀███▄▄,_
    ▀"`   ▀█_         '▀█▄▄█▀▀█▄▄█▀          ▄█"  '"▀"
           ╙██_                            ▄█▀
             └▀█▄_                      ,▓█▀
                └▀▀██▄,__        __╓▄██▀▀
                     `"▀▀▀▀▀▀▀▀▀▀▀╙"`

`````````````````````````````````````````````````````````
"""

TAGLINE = "Spec Kitty - Spec-Driven Development Toolkit (forked from GitHub Spec Kit)"
class StepTracker:
    """Track and render hierarchical steps without emojis, similar to Claude Code tree output.
    Supports live auto-refresh via an attached refresh callback.
    """
    def __init__(self, title: str):
        self.title = title
        self.steps = []  # list of dicts: {key, label, status, detail}
        self.status_order = {"pending": 0, "running": 1, "done": 2, "error": 3, "skipped": 4}
        self._refresh_cb = None  # callable to trigger UI refresh

    def attach_refresh(self, cb):
        self._refresh_cb = cb

    def add(self, key: str, label: str):
        if key not in [s["key"] for s in self.steps]:
            self.steps.append({"key": key, "label": label, "status": "pending", "detail": ""})
            self._maybe_refresh()

    def start(self, key: str, detail: str = ""):
        self._update(key, status="running", detail=detail)

    def complete(self, key: str, detail: str = ""):
        self._update(key, status="done", detail=detail)

    def error(self, key: str, detail: str = ""):
        self._update(key, status="error", detail=detail)

    def skip(self, key: str, detail: str = ""):
        self._update(key, status="skipped", detail=detail)

    def _update(self, key: str, status: str, detail: str):
        for s in self.steps:
            if s["key"] == key:
                s["status"] = status
                if detail:
                    s["detail"] = detail
                self._maybe_refresh()
                return
        # If not present, add it
        self.steps.append({"key": key, "label": key, "status": status, "detail": detail})
        self._maybe_refresh()

    def _maybe_refresh(self):
        if self._refresh_cb:
            try:
                self._refresh_cb()
            except Exception:
                pass

    def render(self):
        tree = Tree(f"[cyan]{self.title}[/cyan]", guide_style="grey50")
        for step in self.steps:
            label = step["label"]
            detail_text = step["detail"].strip() if step["detail"] else ""

            # Circles (unchanged styling)
            status = step["status"]
            if status == "done":
                symbol = "[green]●[/green]"
            elif status == "pending":
                symbol = "[green dim]○[/green dim]"
            elif status == "running":
                symbol = "[cyan]○[/cyan]"
            elif status == "error":
                symbol = "[red]●[/red]"
            elif status == "skipped":
                symbol = "[yellow]○[/yellow]"
            else:
                symbol = " "

            if status == "pending":
                # Entire line light gray (pending)
                if detail_text:
                    line = f"{symbol} [bright_black]{label} ({detail_text})[/bright_black]"
                else:
                    line = f"{symbol} [bright_black]{label}[/bright_black]"
            else:
                # Label white, detail (if any) light gray in parentheses
                if detail_text:
                    line = f"{symbol} [white]{label}[/white] [bright_black]({detail_text})[/bright_black]"
                else:
                    line = f"{symbol} [white]{label}[/white]"

            tree.add(line)
        return tree

def get_key():
    """Get a single keypress in a cross-platform way using readchar."""
    key = readchar.readkey()

    if key == readchar.key.UP or key == readchar.key.CTRL_P:
        return 'up'
    if key == readchar.key.DOWN or key == readchar.key.CTRL_N:
        return 'down'

    if key == readchar.key.ENTER:
        return 'enter'

    if key == readchar.key.ESC or key == "\x1b":
        return 'escape'

    if key == readchar.key.CTRL_C:
        raise KeyboardInterrupt

    return key

def select_with_arrows(options: dict, prompt_text: str = "Select an option", default_key: str = None) -> str:
    """
    Interactive selection using arrow keys with Rich Live display.
    
    Args:
        options: Dict with keys as option keys and values as descriptions
        prompt_text: Text to show above the options
        default_key: Default option key to start with
        
    Returns:
        Selected option key
    """
    option_keys = list(options.keys())
    if default_key and default_key in option_keys:
        selected_index = option_keys.index(default_key)
    else:
        selected_index = 0

    selected_key = None

    def create_selection_panel():
        """Create the selection panel with current selection highlighted."""
        table = Table.grid(padding=(0, 2))
        table.add_column(style="cyan", justify="left", width=3)
        table.add_column(style="white", justify="left")

        for i, key in enumerate(option_keys):
            if i == selected_index:
                table.add_row("▶", f"[cyan]{key}[/cyan] [dim]({options[key]})[/dim]")
            else:
                table.add_row(" ", f"[cyan]{key}[/cyan] [dim]({options[key]})[/dim]")

        table.add_row("", "")
        table.add_row("", "[dim]Use ↑/↓ to navigate, Enter to select, Esc to cancel[/dim]")

        return Panel(
            table,
            title=f"[bold]{prompt_text}[/bold]",
            border_style="cyan",
            padding=(1, 2)
        )

    console.print()

    def run_selection_loop():
        nonlocal selected_key, selected_index
        with Live(create_selection_panel(), console=console, transient=True, auto_refresh=False) as live:
            while True:
                try:
                    key = get_key()
                    if key == 'up':
                        selected_index = (selected_index - 1) % len(option_keys)
                    elif key == 'down':
                        selected_index = (selected_index + 1) % len(option_keys)
                    elif key == 'enter':
                        selected_key = option_keys[selected_index]
                        break
                    elif key == 'escape':
                        console.print("\n[yellow]Selection cancelled[/yellow]")
                        raise typer.Exit(1)

                    live.update(create_selection_panel(), refresh=True)

                except KeyboardInterrupt:
                    console.print("\n[yellow]Selection cancelled[/yellow]")
                    raise typer.Exit(1)

    run_selection_loop()

    if selected_key is None:
        console.print("\n[red]Selection failed.[/red]")
        raise typer.Exit(1)

    # Suppress explicit selection print; tracker / later logic will report consolidated status
    return selected_key


def multi_select_with_arrows(
    options: dict[str, str],
    prompt_text: str = "Select options",
    default_keys: list[str] | None = None,
) -> list[str]:
    """Allow selecting one or more options using arrow keys + space to toggle."""

    option_keys = list(options.keys())
    selected_indices: set[int] = set()
    if default_keys:
        for key in default_keys:
            if key in option_keys:
                selected_indices.add(option_keys.index(key))
    if not selected_indices and option_keys:
        selected_indices.add(0)

    cursor_index = next(iter(selected_indices)) if selected_indices else 0

    def build_panel():
        table = Table.grid(padding=(0, 2))
        table.add_column(style="cyan", justify="left", width=3)
        table.add_column(style="white", justify="left")

        for i, key in enumerate(option_keys):
            indicator = "[cyan]☑" if i in selected_indices else "[bright_black]☐"
            pointer = "▶" if i == cursor_index else " "
            table.add_row(pointer, f"{indicator} [cyan]{key}[/cyan] [dim]({options[key]})[/dim]")

        table.add_row("", "")
        table.add_row(
            "",
            "[dim]Use ↑/↓ to move, Space to toggle, Enter to confirm, Esc to cancel[/dim]",
        )

        return Panel(table, title=f"[bold]{prompt_text}[/bold]", border_style="cyan", padding=(1, 2))

    def normalize_selection() -> list[str]:
        # Preserve original order from option_keys
        return [option_keys[i] for i in range(len(option_keys)) if i in selected_indices]

    console.print()

    with Live(build_panel(), console=console, transient=True, auto_refresh=False) as live:
        while True:
            try:
                key = get_key()
                if key == 'up':
                    cursor_index = (cursor_index - 1) % len(option_keys)
                elif key == 'down':
                    cursor_index = (cursor_index + 1) % len(option_keys)
                elif key in (' ', readchar.key.SPACE):
                    if cursor_index in selected_indices:
                        selected_indices.remove(cursor_index)
                    else:
                        selected_indices.add(cursor_index)
                elif key == 'enter':
                    current = normalize_selection()
                    if current:
                        return current
                    # Require at least one selection; keep prompting
                elif key == 'escape':
                    console.print("\n[yellow]Selection cancelled[/yellow]")
                    raise typer.Exit(1)

                live.update(build_panel(), refresh=True)

            except KeyboardInterrupt:
                console.print("\n[yellow]Selection cancelled[/yellow]")
                raise typer.Exit(1)


def get_local_repo_root() -> Path | None:
    """Return repository root when running from a local checkout, else None."""
    env_root = os.environ.get("SPEC_KITTY_TEMPLATE_ROOT")
    if env_root:
        root_path = Path(env_root).expanduser().resolve()
        if (root_path / "templates" / "commands").exists():
            return root_path
        console.print(
            f"[yellow]SPEC_KITTY_TEMPLATE_ROOT set to {root_path}, but templates/commands not found. Ignoring.[/yellow]"
        )

    candidate = Path(__file__).resolve().parents[2]
    if (candidate / "templates" / "commands").exists():
        return candidate
    return None


def parse_repo_slug(slug: str) -> tuple[str, str]:
    parts = slug.strip().split("/")
    if len(parts) != 2 or not all(parts):
        raise ValueError(f"Invalid GitHub repo slug '{slug}'. Expected format owner/name")
    return parts[0], parts[1]


def rewrite_paths(text: str) -> str:
    import re
    patterns = {
        r'(?<!\.kittify/)scripts/': '.kittify/scripts/',
        r'(?<!\.kittify/)templates/': '.kittify/templates/',
        r'(?<!\.kittify/)memory/': '.kittify/memory/',
    }
    for pattern, replacement in patterns.items():
        text = re.sub(pattern, replacement, text)
    return text


def copy_specify_base_from_local(repo_root: Path, project_path: Path, script_type: str) -> Path:
    specify_root = project_path / ".kittify"
    specify_root.mkdir(parents=True, exist_ok=True)

    memory_src = repo_root / "memory"
    if memory_src.exists():
        memory_dest = specify_root / "memory"
        if memory_dest.exists():
            shutil.rmtree(memory_dest)
        shutil.copytree(memory_src, memory_dest)

    scripts_src = repo_root / "scripts"
    if scripts_src.exists():
        scripts_dest = specify_root / "scripts"
        if scripts_dest.exists():
            shutil.rmtree(scripts_dest)
        scripts_dest.mkdir(parents=True, exist_ok=True)
        variant = "bash" if script_type == "sh" else "powershell"
        variant_src = scripts_src / variant
        if variant_src.exists():
            shutil.copytree(variant_src, scripts_dest / variant)
        tasks_src = scripts_src / "tasks"
        if tasks_src.exists():
            shutil.copytree(tasks_src, scripts_dest / "tasks")
        for item in scripts_src.iterdir():
            if item.is_file():
                shutil.copy2(item, scripts_dest / item.name)

    templates_src = repo_root / "templates"
    if templates_src.exists():
        templates_dest = specify_root / "templates"
        if templates_dest.exists():
            shutil.rmtree(templates_dest)
        shutil.copytree(templates_src, templates_dest)

    missions_candidates = [
        repo_root / ".kittify" / "missions",
        repo_root / "src" / "specify_cli" / ".kittify" / "missions",
    ]
    for missions_src in missions_candidates:
        if missions_src.exists():
            missions_dest = specify_root / "missions"
            if missions_dest.exists():
                shutil.rmtree(missions_dest)
            shutil.copytree(missions_src, missions_dest)
            break

    return (specify_root / "templates" / "commands")


def render_command_template(
    template_path: Path,
    script_type: str,
    agent_key: str,
    arg_format: str,
    extension: str,
) -> str:
    text = template_path.read_text(encoding="utf-8").replace("\r", "")

    frontmatter_text = ""
    body_text = text
    if text.startswith("---\n"):
        closing = text.find("\n---\n", 4)
        if closing != -1:
            frontmatter_text = text[4:closing]
            body_text = text[closing + 5 :]

    description = ""
    scripts: dict[str, str] = {}
    agent_scripts: dict[str, str] = {}
    if frontmatter_text:
        current_section = None
        for line in frontmatter_text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if not line.startswith(" "):
                current_section = None
            if stripped == "scripts:":
                current_section = "scripts"
                continue
            if stripped == "agent_scripts:":
                current_section = "agent_scripts"
                continue
            if stripped.startswith("description:"):
                description = stripped[len("description:") :].strip()
                continue
            if line.startswith("  ") and current_section:
                key_value = stripped.split(":", 1)
                if len(key_value) == 2:
                    key = key_value[0].strip()
                    value = key_value[1].strip()
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    if current_section == "scripts":
                        scripts[key] = value
                    elif current_section == "agent_scripts":
                        agent_scripts[key] = value

    script_command = scripts.get(script_type, f"(Missing script command for {script_type})")
    agent_script_command = agent_scripts.get(script_type)

    if frontmatter_text:
        filtered_lines = []
        skipping = False
        for line in frontmatter_text.splitlines():
            stripped = line.strip()
            if skipping:
                if line.startswith(" ") or line.startswith("\t"):
                    continue
                skipping = False
            if stripped in {"scripts:", "agent_scripts:"}:
                skipping = True
                continue
            filtered_lines.append(line)
        if filtered_lines:
            frontmatter_clean = "---\n" + "\n".join(filtered_lines) + "\n---\n\n"
        else:
            frontmatter_clean = ""
    else:
        frontmatter_clean = ""

    body_text = body_text.replace('{SCRIPT}', script_command)
    if agent_script_command:
        body_text = body_text.replace('{AGENT_SCRIPT}', agent_script_command)
    else:
        body_text = body_text.replace('{AGENT_SCRIPT}', "")
    body_text = body_text.replace('{ARGS}', arg_format)
    body_text = body_text.replace('__AGENT__', agent_key)
    body_text = rewrite_paths(body_text)
    if frontmatter_clean:
        frontmatter_clean = rewrite_paths(frontmatter_clean)

    if extension == "toml":
        description_value = description.strip()
        if description_value.startswith('"') and description_value.endswith('"'):
            description_value = description_value[1:-1]
        description_value = description_value.replace('"', '\\"')
        if not body_text.endswith("\n"):
            body_text += "\n"
        return f'description = "{description_value}"\n\nprompt = """\n{body_text}"""\n'

    if frontmatter_clean:
        result = frontmatter_clean + body_text
    else:
        result = body_text
    if not result.endswith("\n"):
        result += "\n"
    return result


def generate_agent_assets(commands_dir: Path, project_path: Path, agent_key: str, script_type: str) -> None:
    config = AGENT_COMMAND_CONFIG[agent_key]
    output_dir = project_path / config["dir"]
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not commands_dir.exists():
        raise FileNotFoundError(f"Command templates directory not found at {commands_dir}")
    for template_path in sorted(commands_dir.glob("*.md")):
        rendered = render_command_template(
            template_path,
            script_type,
            agent_key,
            config["arg_format"],
            config["ext"],
        )
        ext = config["ext"]
        stem = template_path.stem
        if agent_key == "codex":
            stem = stem.replace('-', '_')
        filename = f"spec-kitty.{stem}.{ext}" if ext else f"spec-kitty.{stem}"
        (output_dir / filename).write_text(rendered, encoding="utf-8")

    if agent_key == "copilot":
        vscode_settings = commands_dir.parent / "vscode-settings.json"
        if vscode_settings.exists():
            vscode_dest = project_path / ".vscode"
            vscode_dest.mkdir(parents=True, exist_ok=True)
            shutil.copy2(vscode_settings, vscode_dest / "settings.json")


def copy_package_tree(resource, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)
    for child in resource.iterdir():
        target = dest / child.name
        if child.is_dir():
            copy_package_tree(child, target)
        else:
            with child.open('rb') as src, open(target, 'wb') as dst:
                shutil.copyfileobj(src, dst)


def copy_specify_base_from_package(project_path: Path, script_type: str) -> Path:
    data_root = files("specify_cli")
    specify_root = project_path / ".kittify"
    specify_root.mkdir(parents=True, exist_ok=True)

    memory_resource = data_root.joinpath("memory")
    if memory_resource.exists():
        copy_package_tree(memory_resource, specify_root / "memory")

    scripts_resource = data_root.joinpath("scripts")
    if scripts_resource.exists():
        scripts_dest = specify_root / "scripts"
        if scripts_dest.exists():
            shutil.rmtree(scripts_dest)
        scripts_dest.mkdir(parents=True, exist_ok=True)
        variant_name = "bash" if script_type == "sh" else "powershell"
        variant_resource = scripts_resource.joinpath(variant_name)
        if variant_resource.exists():
            copy_package_tree(variant_resource, scripts_dest / variant_name)
        tasks_resource = scripts_resource.joinpath("tasks")
        if tasks_resource.exists():
            copy_package_tree(tasks_resource, scripts_dest / "tasks")
        for child in scripts_resource.iterdir():
            if child.is_file():
                with child.open('rb') as src, open(scripts_dest / child.name, 'wb') as dst:
                    shutil.copyfileobj(src, dst)

    templates_resource = data_root.joinpath("templates")
    if templates_resource.exists():
        copy_package_tree(templates_resource, specify_root / "templates")

    missions_resource = data_root.joinpath(".kittify", "missions")
    if missions_resource.exists():
        copy_package_tree(missions_resource, specify_root / "missions")

    return specify_root / "templates" / "commands"


def activate_mission(project_path: Path, mission_key: str, mission_display: str, console: Console) -> str:
    """
    Persist the active mission selection and warn if mission resources are missing.
    """
    kittify_root = project_path / ".kittify"
    missions_dir = kittify_root / "missions"
    active_file = kittify_root / "active-mission"

    kittify_root.mkdir(parents=True, exist_ok=True)
    missions_dir.mkdir(parents=True, exist_ok=True)

    mission_path = missions_dir / mission_key
    status_detail = mission_display

    if not mission_path.exists():
        console.print(
            f"[yellow]Warning:[/yellow] Mission resources for [cyan]{mission_display}[/cyan] "
            f"not found at [cyan]{mission_path}[/cyan]."
        )
        console.print(
            "[yellow]Hint:[/yellow] Run [cyan]spec-kitty mission switch[/cyan] after templates are available "
            "or reinstall project templates."
        )
        status_detail = f"{mission_display} (templates missing)"

    active_file.write_text(f"{mission_key}\n", encoding="utf-8")
    return status_detail


def get_active_mission_key(project_path: Path) -> str:
    """Return the mission key stored in .kittify/active-mission, falling back to default."""
    active_file = project_path / ".kittify" / "active-mission"
    if active_file.exists():
        try:
            key = active_file.read_text(encoding="utf-8").strip()
            if key:
                return key
        except OSError:
            pass
    return DEFAULT_MISSION_KEY


def resolve_template_path(
    project_path: Path, mission_key: str, template_subpath: str | Path
) -> Optional[Path]:
    """
    Resolve a template path, preferring mission overrides, then project-level defaults.
    """
    subpath = Path(template_subpath)
    candidates = [
        project_path / ".kittify" / "missions" / mission_key / "templates" / subpath,
        project_path / ".kittify" / "templates" / subpath,
        project_path / "templates" / subpath,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


console = Console()


def _locate_project_root(start: Path | None = None) -> Optional[Path]:
    """Walk upwards to find the directory that owns .kittify."""
    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".kittify").is_dir():
            return candidate
    return None


def _get_project_root_or_exit(start: Path | None = None) -> Path:
    """Return project root or exit with a helpful error."""
    project_root = _locate_project_root(start)
    if project_root is None:
        console.print("[red]Error:[/red] Unable to locate project root (.kittify directory not found).")
        console.print("[dim]Run this command from inside a Spec Kitty project or worktree.[/dim]")
        raise typer.Exit(1)
    return project_root

class BannerGroup(TyperGroup):
    """Custom group that shows banner before help."""

    def format_help(self, ctx, formatter):
        # Show banner before help
        show_banner()
        super().format_help(ctx, formatter)


app = typer.Typer(
    name="spec-kitty",
    help="Setup tool for Spec Kitty spec-driven development projects",
    add_completion=False,
    invoke_without_command=True,
    cls=BannerGroup,
)

def show_banner():
    """Display the ASCII art banner."""
    # Create gradient effect with different colors
    banner_lines = BANNER.strip().split('\n')
    colors = ["bright_blue", "blue", "cyan", "bright_cyan", "white", "bright_white"]
    max_width = max(len(line) for line in banner_lines) if banner_lines else 0

    styled_banner = Text()
    for i, line in enumerate(banner_lines):
        color = colors[i % len(colors)]
        padded_line = line.ljust(max_width)
        styled_banner.append(padded_line + "\n", style=color)

    console.print(Align.center(styled_banner))
    console.print(Align.center(Text(TAGLINE, style="italic bright_yellow")))
    console.print()

@app.callback()
def callback(ctx: typer.Context):
    """Show banner when no subcommand is provided."""
    # Show banner only when no subcommand and no help flag
    # (help is handled by BannerGroup)
    if ctx.invoked_subcommand is None and "--help" not in sys.argv and "-h" not in sys.argv:
        show_banner()
        console.print(Align.center("[dim]Run 'spec-kitty --help' for usage information[/dim]"))
        console.print()

def run_command(cmd: list[str], check_return: bool = True, capture: bool = False, shell: bool = False) -> Optional[str]:
    """Run a shell command and optionally capture output."""
    try:
        if capture:
            result = subprocess.run(cmd, check=check_return, capture_output=True, text=True, shell=shell)
            return result.stdout.strip()
        else:
            subprocess.run(cmd, check=check_return, shell=shell)
            return None
    except subprocess.CalledProcessError as e:
        if check_return:
            console.print(f"[red]Error running command:[/red] {' '.join(cmd)}")
            console.print(f"[red]Exit code:[/red] {e.returncode}")
            if hasattr(e, 'stderr') and e.stderr:
                console.print(f"[red]Error output:[/red] {e.stderr}")
            raise
        return None

def check_tool_for_tracker(tool: str, tracker: StepTracker) -> bool:
    """Check if a tool is installed and update tracker."""
    if shutil.which(tool):
        tracker.complete(tool, "available")
        return True
    else:
        tracker.error(tool, "not found")
        return False

def check_tool(tool: str, install_hint: str) -> bool:
    """Check if a tool is installed."""
    
    # Special handling for Claude CLI after `claude migrate-installer`
    # See: https://github.com/github/spec-kit/issues/123
    # The migrate-installer command REMOVES the original executable from PATH
    # and creates an alias at ~/.claude/local/claude instead
    # This path should be prioritized over other claude executables in PATH
    if tool == "claude":
        if CLAUDE_LOCAL_PATH.exists() and CLAUDE_LOCAL_PATH.is_file():
            return True
    
    if shutil.which(tool):
        return True
    else:
        return False

def is_git_repo(path: Path = None) -> bool:
    """Check if the specified path is inside a git repository."""
    if path is None:
        path = Path.cwd()
    
    if not path.is_dir():
        return False

    try:
        # Use git command to check if inside a work tree
        subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            check=True,
            capture_output=True,
            cwd=path,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def init_git_repo(project_path: Path, quiet: bool = False) -> bool:
    """Initialize a git repository in the specified path.
    quiet: if True suppress console output (tracker handles status)
    """
    try:
        original_cwd = Path.cwd()
        os.chdir(project_path)
        if not quiet:
            console.print("[cyan]Initializing git repository...[/cyan]")
        subprocess.run(["git", "init"], check=True, capture_output=True)
        subprocess.run(["git", "add", "."], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial commit from Specify template"], check=True, capture_output=True)
        if not quiet:
            console.print("[green]✓[/green] Git repository initialized")
        return True

    except subprocess.CalledProcessError as e:
        if not quiet:
            console.print(f"[red]Error initializing git repository:[/red] {e}")
        return False
    finally:
        os.chdir(original_cwd)

def download_template_from_github(
    repo_owner: str,
    repo_name: str,
    ai_assistant: str,
    download_dir: Path,
    *,
    script_type: str = "sh",
    verbose: bool = True,
    show_progress: bool = True,
    client: httpx.Client = None,
    debug: bool = False,
    github_token: str = None,
) -> Tuple[Path, dict]:
    if client is None:
        client = httpx.Client(verify=ssl_context)

    if verbose:
        console.print("[cyan]Fetching latest release information...[/cyan]")
    api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest"

    try:
        response = client.get(
            api_url,
            timeout=30,
            follow_redirects=True,
            headers=_github_auth_headers(github_token),
        )
        status = response.status_code
        if status != 200:
            msg = f"GitHub API returned {status} for {api_url}"
            if debug:
                msg += f"\nResponse headers: {response.headers}\nBody (truncated 500): {response.text[:500]}"
            raise RuntimeError(msg)
        try:
            release_data = response.json()
        except ValueError as je:
            raise RuntimeError(f"Failed to parse release JSON: {je}\nRaw (truncated 400): {response.text[:400]}")
    except Exception as e:
        console.print(f"[red]Error fetching release information[/red]")
        console.print(Panel(str(e), title="Fetch Error", border_style="red"))
        raise typer.Exit(1)

    # Find the template asset for the specified AI assistant
    assets = release_data.get("assets", [])
    pattern = f"spec-kitty-template-{ai_assistant}-{script_type}"
    matching_assets = [
        asset for asset in assets
        if pattern in asset["name"] and asset["name"].endswith(".zip")
    ]

    asset = matching_assets[0] if matching_assets else None

    if asset is None:
        console.print(f"[red]No matching release asset found[/red] for [bold]{ai_assistant}[/bold] (expected pattern: [bold]{pattern}[/bold])")
        asset_names = [a.get('name', '?') for a in assets]
        console.print(Panel("\n".join(asset_names) or "(no assets)", title="Available Assets", border_style="yellow"))
        raise typer.Exit(1)

    download_url = asset["browser_download_url"]
    filename = asset["name"]
    file_size = asset["size"]

    if verbose:
        console.print(f"[cyan]Found template:[/cyan] {filename}")
        console.print(f"[cyan]Size:[/cyan] {file_size:,} bytes")
        console.print(f"[cyan]Release:[/cyan] {release_data['tag_name']}")

    zip_path = download_dir / filename
    if verbose:
        console.print(f"[cyan]Downloading template...[/cyan]")

    try:
        with client.stream(
            "GET",
            download_url,
            timeout=60,
            follow_redirects=True,
            headers=_github_auth_headers(github_token),
        ) as response:
            if response.status_code != 200:
                body_sample = response.text[:400]
                raise RuntimeError(f"Download failed with {response.status_code}\nHeaders: {response.headers}\nBody (truncated): {body_sample}")
            total_size = int(response.headers.get('content-length', 0))
            with open(zip_path, 'wb') as f:
                if total_size == 0:
                    for chunk in response.iter_bytes(chunk_size=8192):
                        f.write(chunk)
                else:
                    if show_progress:
                        with Progress(
                            SpinnerColumn(),
                            TextColumn("[progress.description]{task.description}"),
                            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                            console=console,
                        ) as progress:
                            task = progress.add_task("Downloading...", total=total_size)
                            downloaded = 0
                            for chunk in response.iter_bytes(chunk_size=8192):
                                f.write(chunk)
                                downloaded += len(chunk)
                                progress.update(task, completed=downloaded)
                    else:
                        for chunk in response.iter_bytes(chunk_size=8192):
                            f.write(chunk)
    except Exception as e:
        console.print(f"[red]Error downloading template[/red]")
        detail = str(e)
        if zip_path.exists():
            zip_path.unlink()
        console.print(Panel(detail, title="Download Error", border_style="red"))
        raise typer.Exit(1)
    if verbose:
        console.print(f"Downloaded: {filename}")
    metadata = {
        "filename": filename,
        "size": file_size,
        "release": release_data["tag_name"],
        "asset_url": download_url
    }
    return zip_path, metadata

def download_and_extract_template(
    project_path: Path,
    ai_assistant: str,
    script_type: str,
    is_current_dir: bool = False,
    *,
    verbose: bool = True,
    tracker: StepTracker | None = None,
    tracker_prefix: str | None = None,
    allow_existing: bool = False,
    client: httpx.Client = None,
    debug: bool = False,
    github_token: str = None,
    repo_owner: str = "spec-kitty",
    repo_name: str = "spec-kitty",
) -> Path:
    """Download the latest release and extract it to create a new project.
    Returns project_path. Uses tracker if provided (with keys: fetch, download, extract, cleanup)
    """
    current_dir = Path.cwd()

    # Step: fetch + download combined
    def tk(step: str) -> str:
        if not tracker_prefix:
            return step
        return f"{tracker_prefix}-{step}"

    if tracker:
        tracker.start(tk("fetch"), "contacting GitHub API")
    try:
        zip_path, meta = download_template_from_github(
            repo_owner,
            repo_name,
            ai_assistant,
            current_dir,
            script_type=script_type,
            verbose=verbose and tracker is None,
            show_progress=(tracker is None),
            client=client,
            debug=debug,
            github_token=github_token,
        )
        if tracker:
            tracker.complete(tk("fetch"), f"release {meta['release']} ({meta['size']:,} bytes)")
            tracker.add(tk("download"), "Download template")
            tracker.complete(tk("download"), meta['filename'])
    except Exception as e:
        if tracker:
            tracker.error(tk("fetch"), str(e))
        else:
            if verbose:
                console.print(f"[red]Error downloading template:[/red] {e}")
        raise

    if tracker:
        tracker.add(tk("extract"), "Extract template")
        tracker.start(tk("extract"))
    elif verbose:
        console.print("Extracting template...")

    try:
        # Create project directory only if not using current directory
        if not is_current_dir:
            project_path.mkdir(parents=True)

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # List all files in the ZIP for debugging
            zip_contents = zip_ref.namelist()
            if tracker:
                tracker.start(tk("zip-list"))
                tracker.complete(tk("zip-list"), f"{len(zip_contents)} entries")
            elif verbose:
                console.print(f"[cyan]ZIP contains {len(zip_contents)} items[/cyan]")

            # For current directory, extract to a temp location first
            if is_current_dir:
                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_path = Path(temp_dir)
                    zip_ref.extractall(temp_path)

                    # Check what was extracted
                    extracted_items = list(temp_path.iterdir())
                    if tracker:
                        tracker.start(tk("extracted-summary"))
                        tracker.complete(tk("extracted-summary"), f"temp {len(extracted_items)} items")
                    elif verbose:
                        console.print(f"[cyan]Extracted {len(extracted_items)} items to temp location[/cyan]")

                    # Handle GitHub-style ZIP with a single root directory
                    source_dir = temp_path
                    if len(extracted_items) == 1 and extracted_items[0].is_dir():
                        source_dir = extracted_items[0]
                        if tracker:
                            tracker.add(tk("flatten"), "Flatten nested directory")
                            tracker.complete(tk("flatten"))
                        elif verbose:
                            console.print(f"[cyan]Found nested directory structure[/cyan]")

                    # Copy contents to current directory
                    for item in source_dir.iterdir():
                        dest_path = project_path / item.name
                        if item.is_dir():
                            if dest_path.exists():
                                if verbose and not tracker:
                                    console.print(f"[yellow]Merging directory:[/yellow] {item.name}")
                                # Recursively copy directory contents
                                for sub_item in item.rglob('*'):
                                    if sub_item.is_file():
                                        rel_path = sub_item.relative_to(item)
                                        dest_file = dest_path / rel_path
                                        dest_file.parent.mkdir(parents=True, exist_ok=True)
                                        shutil.copy2(sub_item, dest_file)
                            else:
                                shutil.copytree(item, dest_path)
                        else:
                            if dest_path.exists() and verbose and not tracker:
                                console.print(f"[yellow]Overwriting file:[/yellow] {item.name}")
                            shutil.copy2(item, dest_path)
                    if verbose and not tracker:
                        console.print(f"[cyan]Template files merged into current directory[/cyan]")
            else:
                # Extract directly to project directory (original behavior)
                if allow_existing and project_path.exists():
                    with tempfile.TemporaryDirectory() as temp_dir:
                        temp_path = Path(temp_dir)
                        zip_ref.extractall(temp_path)
                        extracted_items = list(temp_path.iterdir())
                        if tracker:
                            tracker.start(tk("extracted-summary"))
                            tracker.complete(tk("extracted-summary"), f"temp {len(extracted_items)} items")
                        for item in extracted_items:
                            dest_path = project_path / item.name
                            if item.is_dir():
                                if dest_path.exists():
                                    for sub_item in item.rglob('*'):
                                        if sub_item.is_file():
                                            rel_path = sub_item.relative_to(item)
                                            dest_file = dest_path / rel_path
                                            dest_file.parent.mkdir(parents=True, exist_ok=True)
                                            shutil.copy2(sub_item, dest_file)
                                else:
                                    shutil.copytree(item, dest_path)
                            else:
                                shutil.copy2(item, dest_path)
                else:
                    zip_ref.extractall(project_path)

                # Check what was extracted
                extracted_items = list(project_path.iterdir())
                if tracker:
                    tracker.start(tk("extracted-summary"))
                    tracker.complete(tk("extracted-summary"), f"{len(extracted_items)} top-level items")
                elif verbose:
                    console.print(f"[cyan]Extracted {len(extracted_items)} items to {project_path}:[/cyan]")
                    for item in extracted_items:
                        console.print(f"  - {item.name} ({'dir' if item.is_dir() else 'file'})")

                # Handle GitHub-style ZIP with a single root directory
                if len(extracted_items) == 1 and extracted_items[0].is_dir():
                    # Move contents up one level
                    nested_dir = extracted_items[0]
                    temp_move_dir = project_path.parent / f"{project_path.name}_temp"
                    # Move the nested directory contents to temp location
                    shutil.move(str(nested_dir), str(temp_move_dir))
                    # Remove the now-empty project directory
                    project_path.rmdir()
                    # Rename temp directory to project directory
                    shutil.move(str(temp_move_dir), str(project_path))
                    if tracker:
                        tracker.add(tk("flatten"), "Flatten nested directory")
                        tracker.complete(tk("flatten"))
                    elif verbose:
                        console.print(f"[cyan]Flattened nested directory structure[/cyan]")

    except Exception as e:
        if tracker:
            tracker.error(tk("extract"), str(e))
        else:
            if verbose:
                console.print(f"[red]Error extracting template:[/red] {e}")
                if debug:
                    console.print(Panel(str(e), title="Extraction Error", border_style="red"))
        # Clean up project directory if created and not current directory
        if not is_current_dir and project_path.exists():
            shutil.rmtree(project_path)
        raise typer.Exit(1)
    else:
        if tracker:
            tracker.complete(tk("extract"))
    finally:
        if tracker:
            tracker.add(tk("cleanup"), "Remove temporary archive")
        # Clean up downloaded ZIP file
        if zip_path.exists():
            zip_path.unlink()
            if tracker:
                tracker.complete(tk("cleanup"))
            elif verbose:
                console.print(f"Cleaned up: {zip_path.name}")

    return project_path


def ensure_executable_scripts(project_path: Path, tracker: StepTracker | None = None) -> None:
    """Ensure POSIX .sh scripts under .kittify/scripts (recursively) have execute bits (no-op on Windows)."""
    if os.name == "nt":
        return  # Windows: skip silently
    scripts_root = project_path / ".kittify" / "scripts"
    if not scripts_root.is_dir():
        return
    failures: list[str] = []
    updated = 0
    for script in scripts_root.rglob("*.sh"):
        try:
            if script.is_symlink() or not script.is_file():
                continue
            try:
                with script.open("rb") as f:
                    if f.read(2) != b"#!":
                        continue
            except Exception:
                continue
            st = script.stat(); mode = st.st_mode
            if mode & 0o111:
                continue
            new_mode = mode
            if mode & 0o400: new_mode |= 0o100
            if mode & 0o040: new_mode |= 0o010
            if mode & 0o004: new_mode |= 0o001
            if not (new_mode & 0o100):
                new_mode |= 0o100
            os.chmod(script, new_mode)
            updated += 1
        except Exception as e:
            failures.append(f"{script.relative_to(scripts_root)}: {e}")
    if tracker:
        detail = f"{updated} updated" + (f", {len(failures)} failed" if failures else "")
        tracker.add("chmod", "Set script permissions recursively")
        (tracker.error if failures else tracker.complete)("chmod", detail)
    else:
        if updated:
            console.print(f"[cyan]Updated execute permissions on {updated} script(s) recursively[/cyan]")
        if failures:
            console.print("[yellow]Some scripts could not be updated:[/yellow]")
            for f in failures:
                console.print(f"  - {f}")

@app.command()
def init(
    project_name: str = typer.Argument(None, help="Name for your new project directory (optional if using --here, or use '.' for current directory)"),
    ai_assistant: str = typer.Option(None, "--ai", help="Comma-separated AI assistants (claude,codex,gemini,...)"),
    script_type: str = typer.Option(None, "--script", help="Script type to use: sh or ps"),
    mission_key: str = typer.Option(None, "--mission", help="Mission key to activate (software-dev, research, ...)"),
    ignore_agent_tools: bool = typer.Option(False, "--ignore-agent-tools", help="Skip checks for AI agent tools like Claude Code"),
    no_git: bool = typer.Option(False, "--no-git", help="Skip git repository initialization"),
    here: bool = typer.Option(False, "--here", help="Initialize project in the current directory instead of creating a new one"),
    force: bool = typer.Option(False, "--force", help="Force merge/overwrite when using --here (skip confirmation)"),
    skip_tls: bool = typer.Option(False, "--skip-tls", help="Skip SSL/TLS verification (not recommended)"),
    debug: bool = typer.Option(False, "--debug", help="Show verbose diagnostic output for network and extraction failures"),
    github_token: str = typer.Option(None, "--github-token", help="GitHub token to use for API requests (or set GH_TOKEN or GITHUB_TOKEN environment variable)"),
):
    """
    Initialize a new Specify project from the latest template.
    
    This command will:
    1. Check that required tools are installed (git is optional)
    2. Let you choose one or more AI assistants (Claude Code, Gemini CLI, GitHub Copilot, Cursor, Qwen Code, opencode, Codex CLI, Windsurf, Kilo Code, Auggie CLI, or Amazon Q Developer CLI)
    3. Pick a mission (Software Dev Kitty, Deep Research Kitty, etc.) to seed templates and guardrails
    4. Download the appropriate template from GitHub
    5. Extract the template to a new project directory or current directory
    6. Initialize a fresh git repository (if not --no-git and no existing repo)
    7. Optionally set up AI assistant commands
    
    Examples:
        spec-kitty init my-project
        spec-kitty init my-project --ai claude
        spec-kitty init my-project --ai claude,codex
        spec-kitty init my-project --mission research
        spec-kitty init my-project --ai copilot --no-git
        spec-kitty init --ignore-agent-tools my-project
        spec-kitty init . --ai claude         # Initialize in current directory
        spec-kitty init .                     # Initialize in current directory (interactive AI selection)
        spec-kitty init --here --ai claude    # Alternative syntax for current directory
        spec-kitty init --here --ai codex
        spec-kitty init --here
        spec-kitty init --here --force  # Skip confirmation when current directory not empty
    """

    show_banner()

    # Handle '.' as shorthand for current directory (equivalent to --here)
    if project_name == ".":
        here = True
        project_name = None  # Clear project_name to use existing validation logic

    if here and project_name:
        console.print("[red]Error:[/red] Cannot specify both project name and --here flag")
        raise typer.Exit(1)

    if not here and not project_name:
        console.print("[red]Error:[/red] Must specify either a project name, use '.' for current directory, or use --here flag")
        raise typer.Exit(1)

    if here:
        try:
            project_path = Path.cwd()
            project_name = project_path.name
        except (OSError, FileNotFoundError) as e:
            console.print("[red]Error:[/red] Cannot access current directory")
            console.print(f"[dim]{e}[/dim]")
            console.print("[yellow]Hint:[/yellow] Your current directory may have been deleted or is no longer accessible")
            raise typer.Exit(1)

        existing_items = list(project_path.iterdir())
        if existing_items:
            console.print(f"[yellow]Warning:[/yellow] Current directory is not empty ({len(existing_items)} items)")
            console.print("[yellow]Template files will be merged with existing content and may overwrite existing files[/yellow]")
            if force:
                console.print("[cyan]--force supplied: skipping confirmation and proceeding with merge[/cyan]")
            else:
                response = typer.confirm("Do you want to continue?")
                if not response:
                    console.print("[yellow]Operation cancelled[/yellow]")
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
            console.print()
            console.print(error_panel)
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

    console.print(Panel("\n".join(setup_lines), border_style="cyan", padding=(1, 2)))

    # Check git only if we might need it (not --no-git)
    # Only set to True if the user wants it and the tool is available
    should_init_git = False
    if not no_git:
        should_init_git = check_tool("git", "https://git-scm.com/downloads")
        if not should_init_git:
            console.print("[yellow]Git not found - will skip repository initialization[/yellow]")

    if ai_assistant:
        raw_agents = [part.strip().lower() for part in ai_assistant.replace(";", ",").split(",") if part.strip()]
        if not raw_agents:
            console.print("[red]Error:[/red] --ai flag did not contain any valid agent identifiers")
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
            console.print(
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
        console.print("[red]Error:[/red] No AI assistants selected")
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
            lines.append("Tip: Use [cyan]--ignore-agent-tools[/cyan] to skip this check")
            error_panel = Panel(
                "\n".join(lines),
                title="[red]Agent Tool(s) Missing[/red]",
                border_style="red",
                padding=(1, 2),
            )
            console.print()
            console.print(error_panel)
            raise typer.Exit(1)

    # Determine script type (explicit, interactive, or OS default)
    if script_type:
        if script_type not in SCRIPT_TYPE_CHOICES:
            console.print(f"[red]Error:[/red] Invalid script type '{script_type}'. Choose from: {', '.join(SCRIPT_TYPE_CHOICES.keys())}")
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
            console.print(f"[red]Error:[/red] Invalid mission '{mission_key}'. Choose from: {', '.join(MISSION_CHOICES.keys())}")
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
    local_repo = get_local_repo_root()
    if local_repo is not None:
        template_mode = "local"
        if debug:
            console.print(f"[cyan]Using local templates from[/cyan] {local_repo}")

    repo_owner = repo_name = None
    remote_slug_env = os.environ.get("SPECIFY_TEMPLATE_REPO")
    if remote_slug_env:
        try:
            repo_owner, repo_name = parse_repo_slug(remote_slug_env)
        except ValueError as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(1)
        template_mode = "remote"
        if debug:
            console.print(f"[cyan]Using remote templates from[/cyan] {repo_owner}/{repo_name}")
    elif template_mode == "package" and debug:
        console.print("[cyan]Using templates bundled with specify_cli package[/cyan]")

    ai_display = ", ".join(AI_CHOICES[key] for key in selected_agents)
    console.print(f"[cyan]Selected AI assistant(s):[/cyan] {ai_display}")
    console.print(f"[cyan]Selected script type:[/cyan] {selected_script}")
    console.print(f"[cyan]Selected mission:[/cyan] {mission_display}")

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

    with Live(tracker.render(), console=console, refresh_per_second=8, transient=True) as live:
        tracker.attach_refresh(lambda: live.update(tracker.render()))
        try:
            # Create a httpx client with verify based on skip_tls
            verify = not skip_tls
            local_ssl_context = ssl_context if verify else False
            local_client = httpx.Client(verify=local_ssl_context)

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
                mission_status = activate_mission(project_path, selected_mission, mission_display, console)
            except Exception as exc:
                tracker.error("mission-activate", str(exc))
                raise
            else:
                tracker.complete("mission-activate", mission_status)

            # Ensure scripts are executable (POSIX)
            ensure_executable_scripts(project_path, tracker=tracker)

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
            console.print(Panel(f"Initialization failed: {e}", title="Failure", border_style="red"))
            if debug:
                _env_pairs = [
                    ("Python", sys.version.split()[0]),
                    ("Platform", sys.platform),
                    ("CWD", str(Path.cwd())),
                ]
                _label_width = max(len(k) for k, _ in _env_pairs)
                env_lines = [f"{k.ljust(_label_width)} → [bright_black]{v}[/bright_black]" for k, v in _env_pairs]
                console.print(Panel("\n".join(env_lines), title="Debug Environment", border_style="magenta"))
            if not here and project_path.exists():
                shutil.rmtree(project_path)
            raise typer.Exit(1)
        finally:
            # Force final render
            pass

    # Final static tree (ensures finished state visible after Live context ends)
    console.print(tracker.render())
    console.print("\n[bold green]Project ready.[/bold green]")

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
        console.print()
        console.print(security_notice)

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
    console.print()
    console.print(steps_panel)

    enhancement_lines = [
        "Optional commands that you can use for your specs [bright_black](improve quality & confidence)[/bright_black]",
        "",
        f"○ [cyan]/spec-kitty.clarify[/] [bright_black](optional)[/bright_black] - Ask structured questions to de-risk ambiguous areas before planning (run before [cyan]/spec-kitty.plan[/] if used)",
        f"○ [cyan]/spec-kitty.analyze[/] [bright_black](optional)[/bright_black] - Cross-artifact consistency & alignment report (after [cyan]/spec-kitty.tasks[/], before [cyan]/spec-kitty.implement[/])",
        f"○ [cyan]/spec-kitty.checklist[/] [bright_black](optional)[/bright_black] - Generate quality checklists to validate requirements completeness, clarity, and consistency (after [cyan]/spec-kitty.plan[/])"
    ]
    enhancements_panel = Panel("\n".join(enhancement_lines), title="Enhancement Commands", border_style="cyan", padding=(1,2))
    console.print()
    console.print(enhancements_panel)

    # Start the dashboard server as detached background process
    console.print()
    try:
        port, _ = start_dashboard(project_path, background_process=True)
        dashboard_url = f"http://127.0.0.1:{port}"

        # Save dashboard URL for later retrieval
        dashboard_info_file = project_path / ".kittify" / ".dashboard"
        dashboard_info_file.write_text(f"{dashboard_url}\n{port}\n")

        dashboard_panel = Panel(
            f"[bold cyan]Dashboard URL:[/bold cyan] {dashboard_url}\n\n"
            f"[dim]The dashboard is running in the background and will continue even after\n"
            f"this command exits. It will automatically update as you work.[/dim]\n\n"
            f"[yellow]Tip:[/yellow] Run [cyan]/spec-kitty.dashboard[/cyan] or [cyan]spec-kitty dashboard[/cyan] to open it in your browser",
            title="[bold green]Spec Kitty Dashboard Started[/bold green]",
            border_style="green",
            padding=(1, 2)
        )
        console.print(dashboard_panel)
        console.print()
    except Exception as e:
        console.print(f"[yellow]Warning: Could not start dashboard: {e}[/yellow]")
        console.print("[dim]Continuing without dashboard...[/dim]")

    if "codex" in selected_agents:
        codex_path = project_path / ".codex"
        codex_str = str(codex_path)
        if os.name == "nt":
            export_line = f"setx CODEX_HOME {codex_str}"
        else:
            export_line = f"export CODEX_HOME={codex_str}"
        console.print("Now set your CODEX_HOME:")
        console.print(export_line, highlight=False)


@app.command()
def research(
    feature: Optional[str] = typer.Option(None, "--feature", help="Feature slug to target (auto-detected when omitted)"),
    force: bool = typer.Option(False, "--force", help="Overwrite existing research artifacts"),
):
    """Execute the Phase 0 research workflow: scaffold research.md, data-model.md, and CSV evidence logs."""

    show_banner()

    try:
        repo_root = find_repo_root()
    except TaskCliError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)

    project_root = _get_project_root_or_exit(repo_root)
    mission_key = get_active_mission_key(project_root)
    mission_display = MISSION_CHOICES.get(mission_key, mission_key)

    tracker = StepTracker("Research Phase Setup")
    tracker.add("project", "Locate project root")
    tracker.add("feature", "Resolve feature directory")
    tracker.add("research-md", "Ensure research.md")
    tracker.add("data-model", "Ensure data-model.md")
    tracker.add("research-csv", "Ensure research CSV stubs")
    tracker.add("summary", "Summarize outputs")
    console.print()

    tracker.start("project")
    tracker.complete("project", f"{project_root} ({mission_display})")

    tracker.start("feature")
    try:
        feature_slug = (feature or detect_feature_slug(repo_root, cwd=Path.cwd())).strip()
    except AcceptanceError as exc:
        tracker.error("feature", str(exc))
        console.print(tracker.render())
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)

    feature_dir = repo_root / "kitty-specs" / feature_slug
    if not feature_dir.exists():
        fallback_dir = project_root / "kitty-specs" / feature_slug
        if fallback_dir.exists():
            feature_dir = fallback_dir
        else:
            feature_dir.mkdir(parents=True, exist_ok=True)
    else:
        feature_dir.mkdir(parents=True, exist_ok=True)
    tracker.complete("feature", str(feature_dir))

    created_paths: list[Path] = []

    def _copy_asset(step_key: str, label: str, relative_path: Path, template_name: Path) -> None:
        tracker.start(step_key)
        dest_path = feature_dir / relative_path
        template_path = resolve_template_path(project_root, mission_key, template_name)

        dest_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            if dest_path.exists() and not force:
                tracker.complete(step_key, f"{label} already exists")
                created_paths.append(dest_path)
                return

            if template_path and template_path.is_file():
                shutil.copy2(template_path, dest_path)
                tracker.complete(step_key, f"{label} created")
            else:
                if dest_path.exists():
                    dest_path.unlink()
                dest_path.touch()
                tracker.complete(step_key, f"{label} stub created")

            created_paths.append(dest_path)
        except Exception as exc:
            tracker.error(step_key, f"{label} failed: {exc}")
            raise

    try:
        _copy_asset("research-md", "research.md", Path("research.md"), Path("research-template.md"))
    except Exception:
        console.print(tracker.render())
        raise typer.Exit(1)

    try:
        _copy_asset("data-model", "data-model.md", Path("data-model.md"), Path("data-model-template.md"))
    except Exception:
        console.print(tracker.render())
        raise typer.Exit(1)

    tracker.start("research-csv")
    csv_targets = [
        (Path("research") / "evidence-log.csv", Path("research") / "evidence-log.csv"),
        (Path("research") / "source-register.csv", Path("research") / "source-register.csv"),
    ]
    csv_errors: list[str] = []
    for dest_rel, template_rel in csv_targets:
        dest_path = feature_dir / dest_rel
        template_path = resolve_template_path(project_root, mission_key, template_rel)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            if dest_path.exists() and not force:
                created_paths.append(dest_path)
                continue
            if template_path and template_path.is_file():
                shutil.copy2(template_path, dest_path)
            else:
                if dest_path.exists():
                    dest_path.unlink()
                dest_path.touch()
            created_paths.append(dest_path)
        except Exception as exc:
            csv_errors.append(f"{dest_rel}: {exc}")

    if csv_errors:
        tracker.error("research-csv", "; ".join(csv_errors))
        console.print(tracker.render())
        raise typer.Exit(1)
    else:
        tracker.complete("research-csv", "CSV templates ready")

    tracker.start("summary")
    tracker.complete("summary", f"{len(created_paths)} artifacts ready")

    console.print(tracker.render())

    relative_paths = [
        str(path.relative_to(feature_dir)) if path.is_relative_to(feature_dir) else str(path)
        for path in created_paths
    ]
    summary_lines = "\n".join(f"- [cyan]{rel}[/cyan]" for rel in sorted(set(relative_paths)))
    console.print()
    console.print(
        Panel(
            summary_lines or "No artifacts were created (existing files kept).",
            title="Research Artifacts",
            border_style="cyan",
            padding=(1, 2),
        )
    )
    console.print()

@app.command()
def check():
    """Check that all required tools are installed."""
    show_banner()
    console.print("[bold]Checking for installed tools...[/bold]\n")

    tracker = StepTracker("Check Available Tools")

    tracker.add("git", "Git version control")
    tracker.add("claude", "Claude Code CLI")
    tracker.add("gemini", "Gemini CLI")
    tracker.add("qwen", "Qwen Code CLI")
    tracker.add("code", "Visual Studio Code")
    tracker.add("code-insiders", "Visual Studio Code Insiders")
    tracker.add("cursor-agent", "Cursor IDE agent")
    tracker.add("windsurf", "Windsurf IDE")
    tracker.add("kilocode", "Kilo Code IDE")
    tracker.add("opencode", "opencode")
    tracker.add("codex", "Codex CLI")
    tracker.add("auggie", "Auggie CLI")
    tracker.add("q", "Amazon Q Developer CLI")

    git_ok = check_tool_for_tracker("git", tracker)
    claude_ok = check_tool_for_tracker("claude", tracker)  
    gemini_ok = check_tool_for_tracker("gemini", tracker)
    qwen_ok = check_tool_for_tracker("qwen", tracker)
    code_ok = check_tool_for_tracker("code", tracker)
    code_insiders_ok = check_tool_for_tracker("code-insiders", tracker)
    cursor_ok = check_tool_for_tracker("cursor-agent", tracker)
    windsurf_ok = check_tool_for_tracker("windsurf", tracker)
    kilocode_ok = check_tool_for_tracker("kilocode", tracker)
    opencode_ok = check_tool_for_tracker("opencode", tracker)
    codex_ok = check_tool_for_tracker("codex", tracker)
    auggie_ok = check_tool_for_tracker("auggie", tracker)
    q_ok = check_tool_for_tracker("q", tracker)

    console.print(tracker.render())

    console.print("\n[bold green]Spec Kitty CLI is ready to use![/bold green]")

    if not git_ok:
        console.print("[dim]Tip: Install git for repository management[/dim]")
    if not (claude_ok or gemini_ok or cursor_ok or qwen_ok or windsurf_ok or kilocode_ok or opencode_ok or codex_ok or auggie_ok or q_ok):
        console.print("[dim]Tip: Install an AI assistant for the best experience[/dim]")

@app.command()
def dashboard():
    """Open the Spec Kitty dashboard in your browser."""
    import webbrowser
    import socket

    project_root = _get_project_root_or_exit()
    dashboard_file = project_root / '.kittify' / '.dashboard'

    if not dashboard_file.exists():
        console.print()
        console.print("[red]❌ No dashboard information found[/red]")
        console.print()
        console.print("To start the dashboard, run:")
        console.print(f"  [cyan]cd {project_root}[/cyan]")
        console.print("  [cyan]spec-kitty init .[/cyan]")
        console.print()
        raise typer.Exit(1)

    content = dashboard_file.read_text().strip().split('\n')
    dashboard_url = content[0] if content else None
    port_str = content[1] if len(content) > 1 else None

    if not dashboard_url or not port_str:
        console.print()
        console.print("[red]❌ Dashboard file is invalid or empty[/red]")
        console.print(f"   Try running from [cyan]{project_root}[/cyan]: [cyan]spec-kitty init .[/cyan]")
        console.print()
        raise typer.Exit(1)

    try:
        port = int(port_str)
    except (TypeError, ValueError):
        port = None

    is_running = False
    if port is not None:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            is_running = (result == 0)
        except Exception:
            is_running = False

    port_display = port if port is not None else port_str

    console.print()
    console.print("[bold green]Spec Kitty Dashboard[/bold green]")
    console.print("[cyan]" + "=" * 60 + "[/cyan]")
    console.print()
    console.print(f"  [bold cyan]Project Root:[/bold cyan] {project_root}")
    console.print(f"  [bold cyan]URL:[/bold cyan] {dashboard_url}")

    if is_running:
        console.print()
        console.print(f"  [green]✅ Status:[/green] Running on port {port_display}")
    else:
        console.print()
        console.print(f"  [yellow]⚠️  Status:[/yellow] Dashboard appears to be stopped")
        console.print(f"             (Port {port_display} is not responding)")

    console.print()
    console.print("[cyan]" + "=" * 60 + "[/cyan]")
    console.print()

    if is_running:
        try:
            webbrowser.open(dashboard_url)
            console.print("[green]✅ Opening dashboard in your browser...[/green]")
            console.print()
        except Exception:
            console.print("[yellow]⚠️  Could not automatically open browser[/yellow]")
            console.print(f"   Please open this URL manually: [cyan]{dashboard_url}[/cyan]")
            console.print()
    else:
        console.print("[yellow]💡 To (re)start the dashboard, run:[/yellow]")
        console.print(f"  [cyan]cd {project_root}[/cyan]")
        console.print("  [cyan]spec-kitty init .[/cyan]")
        console.print()

def _print_acceptance_summary(summary: AcceptanceSummary) -> None:
    table = Table(title="Work Packages by Lane", header_style="cyan")
    table.add_column("Lane")
    table.add_column("Count", justify="right")
    table.add_column("Work Packages", justify="left")
    for lane in LANES:
        items = summary.lanes.get(lane, [])
        display = ", ".join(items) if items else "-"
        table.add_row(lane, str(len(items)), display)
    console.print(table)

    outstanding = summary.outstanding()
    if outstanding:
        console.print("\n[bold red]Outstanding items[/bold red]")
        for key, values in outstanding.items():
            console.print(f"[red]- {key}[/red]")
            for value in values:
                console.print(f"    • {value}")
    else:
        console.print("\n[green]No outstanding acceptance issues detected.[/green]")

    if summary.optional_missing:
        console.print(
            "\n[yellow]Optional artifacts missing:[/yellow] "
            + ", ".join(summary.optional_missing)
        )


    else:
        console.print()
        console.print(f"  [green]✅ Status:[/green] Running on port {port}")

    console.print()
    console.print("[cyan]" + "=" * 60 + "[/cyan]")
    console.print()

    if is_running:
        # Try to open in browser
        try:
            webbrowser.open(dashboard_url)
            console.print("[green]✅ Opening dashboard in your browser...[/green]")
            console.print()
        except Exception as e:
            console.print("[yellow]⚠️  Could not automatically open browser[/yellow]")
            console.print(f"   Please open this URL manually: [cyan]{dashboard_url}[/cyan]")
            console.print()
    else:
        console.print("[yellow]💡 To start the dashboard, run:[/yellow] [cyan]spec-kitty init .[/cyan]")
        console.print()


def _print_acceptance_result(result: AcceptanceResult) -> None:
    console.print(
        "\n[bold]Acceptance metadata[/bold]\n"
        f"• Feature: {result.summary.feature}\n"
        f"• Accepted at: {result.accepted_at}\n"
        f"• Accepted by: {result.accepted_by}"
    )
    if result.accept_commit:
        console.print(f"• Acceptance commit: {result.accept_commit}")
    if result.parent_commit:
        console.print(f"• Parent commit: {result.parent_commit}")
    if not result.commit_created:
        console.print("• Commit status: no changes were committed (dry-run)")

    if result.instructions:
        console.print("\n[bold]Next steps[/bold]")
        for idx, instruction in enumerate(result.instructions, start=1):
            console.print(f"  {idx}. {instruction}")

    if result.cleanup_instructions:
        console.print("\n[bold]Cleanup[/bold]")
        for idx, instruction in enumerate(result.cleanup_instructions, start=1):
            console.print(f"  {idx}. {instruction}")

    if result.notes:
        console.print("\n[bold]Notes[/bold]")
        for note in result.notes:
            console.print(f"  - {note}")


@app.command()
def accept(
    feature: Optional[str] = typer.Option(None, "--feature", help="Feature slug to accept (auto-detected by default)"),
    mode: str = typer.Option("auto", "--mode", case_sensitive=False, help="Acceptance mode: auto, pr, local, or checklist"),
    actor: Optional[str] = typer.Option(None, "--actor", help="Name to record as the acceptance actor"),
    test: List[str] = typer.Option([], "--test", help="Validation command executed (repeatable)", show_default=False),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON instead of formatted text"),
    lenient: bool = typer.Option(False, "--lenient", help="Skip strict metadata validation"),
    no_commit: bool = typer.Option(False, "--no-commit", help="Skip auto-commit; report only"),
    allow_fail: bool = typer.Option(False, "--allow-fail", help="Return checklist even when issues remain"),
):
    """Run the feature acceptance workflow from the CLI."""

    show_banner()

    try:
        repo_root = find_repo_root()
    except TaskCliError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)

    tracker = StepTracker("Feature Acceptance")
    tracker.add("detect", "Identify feature slug")
    tracker.add("verify", "Run readiness checks")
    console.print()

    tracker.start("detect")
    try:
        feature_slug = (feature or detect_feature_slug(repo_root)).strip()
    except AcceptanceError as exc:
        tracker.error("detect", str(exc))
        console.print(tracker.render())
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)
    tracker.complete("detect", feature_slug)

    requested_mode = (mode or "auto").lower()
    actual_mode = choose_mode(requested_mode, repo_root)
    commit_required = actual_mode != "checklist" and not no_commit
    if commit_required:
        tracker.add("commit", "Record acceptance metadata")
    tracker.add("guide", "Share next steps")

    tracker.start("verify")
    summary = collect_feature_summary(
        repo_root,
        feature_slug,
        strict_metadata=not lenient,
    )
    tracker.complete("verify", "ready" if summary.ok else "issues found")

    if actual_mode == "checklist":
        if json_output:
            console.print(json.dumps(summary.to_dict(), indent=2))
        else:
            _print_acceptance_summary(summary)
        raise typer.Exit(0 if summary.ok else 1)

    if not summary.ok:
        if json_output:
            console.print(json.dumps(summary.to_dict(), indent=2))
        else:
            _print_acceptance_summary(summary)
        if not allow_fail:
            console.print(
                "\n[red]Outstanding acceptance issues detected. Resolve them before merging or rerun with --allow-fail for a checklist-only report.[/red]"
            )
            raise typer.Exit(1)
        raise typer.Exit(1)

    acceptance_tests = list(test)

    try:
        if commit_required:
            tracker.start("commit")
        result = perform_acceptance(
            summary,
            mode=actual_mode,
            actor=actor,
            tests=acceptance_tests,
            auto_commit=commit_required,
        )
        if commit_required:
            detail = "commit created" if result.commit_created else "no changes"
            tracker.complete("commit", detail)
    except AcceptanceError as exc:
        if commit_required:
            tracker.error("commit", str(exc))
            console.print(tracker.render())
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)

    tracker.start("guide")
    tracker.complete("guide", "instructions ready")
    console.print(tracker.render())

    if json_output:
        console.print(json.dumps(result.to_dict(), indent=2))
        return

    _print_acceptance_summary(result.summary)
    _print_acceptance_result(result)


@app.command()
def merge(
    strategy: str = typer.Option("merge", "--strategy", help="Merge strategy: merge, squash, or rebase"),
    delete_branch: bool = typer.Option(True, "--delete-branch/--keep-branch", help="Delete feature branch after merge"),
    remove_worktree: bool = typer.Option(True, "--remove-worktree/--keep-worktree", help="Remove feature worktree after merge"),
    push: bool = typer.Option(False, "--push", help="Push to origin after merge"),
    target_branch: str = typer.Option("main", "--target", help="Target branch to merge into"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done without executing"),
):
    """Merge a feature branch into the target branch and clean up worktree."""

    show_banner()

    tracker = StepTracker("Feature Merge")
    tracker.add("detect", "Detect current feature and branch")
    tracker.add("verify", "Verify merge readiness")
    tracker.add("checkout", f"Switch to {target_branch}")
    tracker.add("pull", f"Update {target_branch}")
    tracker.add("merge", "Merge feature branch")
    if push:
        tracker.add("push", "Push to origin")
    if remove_worktree:
        tracker.add("worktree", "Remove feature worktree")
    if delete_branch:
        tracker.add("branch", "Delete feature branch")

    console.print()

    try:
        repo_root = find_repo_root()
    except TaskCliError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)

    # Detect current branch and worktree
    feature_worktree_path = repo_root
    merge_root = repo_root
    tracker.start("detect")
    try:
        current_branch = run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture=True)
        if current_branch == target_branch:
            tracker.error("detect", f"already on {target_branch}")
            console.print(tracker.render())
            console.print(f"\n[red]Error:[/red] Already on {target_branch} branch. Switch to a feature branch first.")
            raise typer.Exit(1)

        # Check if we're in a worktree
        git_dir_output = run_command(["git", "rev-parse", "--git-dir"], capture=True)
        git_dir_path = Path(git_dir_output).resolve()
        in_worktree = "worktrees" in git_dir_path.parts
        if in_worktree:
            try:
                merge_root = git_dir_path.parents[2]
            except IndexError:
                raise RuntimeError("Unable to determine primary repository for merge operations.")
            if not merge_root.exists():
                raise RuntimeError(f"Primary repository path not found: {merge_root}")
        tracker.complete(
            "detect",
            f"on {current_branch}" + (f" (worktree → operating from {merge_root})" if in_worktree else ""),
        )
    except Exception as e:
        tracker.error("detect", str(e))
        console.print(tracker.render())
        raise typer.Exit(1)

    # Verify clean working directory
    tracker.start("verify")
    try:
        status_output = run_command(["git", "status", "--porcelain"], capture=True)
        if status_output.strip():
            tracker.error("verify", "uncommitted changes")
            console.print(tracker.render())
            console.print(f"\n[red]Error:[/red] Working directory has uncommitted changes.")
            console.print("Commit or stash your changes before merging.")
            raise typer.Exit(1)
        tracker.complete("verify", "clean working directory")
    except Exception as e:
        tracker.error("verify", str(e))
        console.print(tracker.render())
        raise typer.Exit(1)

    merge_root = merge_root.resolve()
    feature_worktree_path = feature_worktree_path.resolve()

    if dry_run:
        console.print(tracker.render())
        console.print(f"\n[cyan]Dry run - would execute:[/cyan]")
        step_num = 1
        if in_worktree:
            console.print(f"  {step_num}. (from {merge_root}) git checkout {target_branch}")
        else:
            console.print(f"  {step_num}. git checkout {target_branch}")
        step_num += 1
        console.print(f"  {step_num}. git pull --ff-only")
        step_num += 1
        if strategy == "squash":
            console.print(f"  {step_num}. git merge --squash {current_branch}")
            step_num += 1
            console.print(f"  {step_num}. git commit -m 'Merge feature {current_branch}'")
        elif strategy == "rebase":
            console.print(f"  {step_num}. git merge --ff-only {current_branch} (after rebase)")
        else:
            console.print(f"  {step_num}. git merge --no-ff {current_branch}")
        step_num += 1
        if push:
            console.print(f"  {step_num}. git push origin {target_branch}")
            step_num += 1
        if in_worktree and remove_worktree:
            console.print(f"  {step_num}. git worktree remove {feature_worktree_path}")
            step_num += 1
        if delete_branch:
            console.print(f"  {step_num}. git branch -d {current_branch}")
        return

    # Switch to target branch
    tracker.start("checkout")
    try:
        if in_worktree:
            console.print(f"[cyan]Detected worktree. Merge operations will run from {merge_root}[/cyan]")
        os.chdir(merge_root)
        target_status = run_command(["git", "status", "--porcelain"], capture=True)
        if target_status.strip():
            raise RuntimeError(f"Target repository at {merge_root} has uncommitted changes.")
        run_command(["git", "checkout", target_branch])
        tracker.complete("checkout", f"using {merge_root}")
    except Exception as e:
        tracker.error("checkout", str(e))
        console.print(tracker.render())
        raise typer.Exit(1)

    # Pull latest
    tracker.start("pull")
    try:
        run_command(["git", "pull", "--ff-only"])
        tracker.complete("pull")
    except Exception as e:
        tracker.error("pull", str(e))
        console.print(tracker.render())
        console.print(f"\n[yellow]Warning:[/yellow] Could not fast-forward {target_branch}.")
        console.print("You may need to resolve conflicts manually.")
        raise typer.Exit(1)

    # Perform merge
    tracker.start("merge")
    try:
        if strategy == "squash":
            run_command(["git", "merge", "--squash", current_branch])
            run_command(["git", "commit", "-m", f"Merge feature {current_branch}"])
            tracker.complete("merge", "squashed")
        elif strategy == "rebase":
            console.print(f"\n[yellow]Note:[/yellow] Rebase strategy requires manual intervention.")
            console.print(f"Please run: git checkout {current_branch} && git rebase {target_branch}")
            tracker.skip("merge", "requires manual rebase")
            console.print(tracker.render())
            raise typer.Exit(0)
        else:  # merge
            run_command(["git", "merge", "--no-ff", current_branch, "-m", f"Merge feature {current_branch}"])
            tracker.complete("merge", "merged with merge commit")
    except Exception as e:
        tracker.error("merge", str(e))
        console.print(tracker.render())
        console.print(f"\n[red]Merge failed.[/red] You may need to resolve conflicts.")
        raise typer.Exit(1)

    # Push if requested
    if push:
        tracker.start("push")
        try:
            run_command(["git", "push", "origin", target_branch])
            tracker.complete("push")
        except Exception as e:
            tracker.error("push", str(e))
            console.print(tracker.render())
            console.print(f"\n[yellow]Warning:[/yellow] Merge succeeded but push failed.")
            console.print(f"Run manually: git push origin {target_branch}")

    # Remove worktree if we were in one
    if in_worktree and remove_worktree:
        tracker.start("worktree")
        try:
            run_command(["git", "worktree", "remove", str(feature_worktree_path), "--force"])
            tracker.complete("worktree", f"removed {feature_worktree_path}")
        except Exception as e:
            tracker.error("worktree", str(e))
            console.print(tracker.render())
            console.print(f"\n[yellow]Warning:[/yellow] Could not remove worktree.")
            console.print(f"Run manually: git worktree remove {feature_worktree_path}")

    # Delete feature branch
    if delete_branch:
        tracker.start("branch")
        try:
            run_command(["git", "branch", "-d", current_branch])
            tracker.complete("branch", f"deleted {current_branch}")
        except Exception as e:
            # Try force delete if regular delete fails
            try:
                run_command(["git", "branch", "-D", current_branch])
                tracker.complete("branch", f"force deleted {current_branch}")
            except:
                tracker.error("branch", str(e))
                console.print(tracker.render())
                console.print(f"\n[yellow]Warning:[/yellow] Could not delete branch {current_branch}.")
                console.print(f"Run manually: git branch -d {current_branch}")

    console.print(tracker.render())
    console.print(f"\n[bold green]✓ Feature {current_branch} successfully merged into {target_branch}[/bold green]")


def main():
    app()

if __name__ == "__main__":
    main()
