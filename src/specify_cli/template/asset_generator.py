"""Agent-specific asset rendering helpers."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Dict, Mapping

from specify_cli.core.config import AGENT_COMMAND_CONFIG
from specify_cli.template.renderer import render_template, rewrite_paths


def generate_agent_assets(commands_dir: Path, project_path: Path, agent_key: str, script_type: str) -> None:
    """Render every command template for the selected agent."""
    config = AGENT_COMMAND_CONFIG[agent_key]
    output_dir = project_path / config["dir"]
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not commands_dir.exists():
        _raise_template_discovery_error(commands_dir)

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
            stem = stem.replace("-", "_")
        filename = f"spec-kitty.{stem}.{ext}" if ext else f"spec-kitty.{stem}"
        (output_dir / filename).write_text(rendered, encoding="utf-8")

    if agent_key == "copilot":
        vscode_settings = commands_dir.parent / "vscode-settings.json"
        if vscode_settings.exists():
            vscode_dest = project_path / ".vscode"
            vscode_dest.mkdir(parents=True, exist_ok=True)
            shutil.copy2(vscode_settings, vscode_dest / "settings.json")


def render_command_template(
    template_path: Path,
    script_type: str,
    agent_key: str,
    arg_format: str,
    extension: str,
) -> str:
    """Render a single command template for an agent."""

    def build_variables(metadata: Dict[str, object]) -> Mapping[str, str]:
        scripts = metadata.get("scripts") or {}
        agent_scripts = metadata.get("agent_scripts") or {}
        if not isinstance(scripts, dict):
            scripts = {}
        if not isinstance(agent_scripts, dict):
            agent_scripts = {}
        script_command = scripts.get(
            script_type, f"(Missing script command for {script_type})"
        )
        agent_script_command = agent_scripts.get(script_type)
        return {
            "{SCRIPT}": script_command,
            "{AGENT_SCRIPT}": agent_script_command or "",
            "{ARGS}": arg_format,
            "__AGENT__": agent_key,
        }

    metadata, rendered_body, raw_frontmatter = render_template(
        template_path, variables=build_variables
    )
    description = str(metadata.get("description", "")).strip()

    frontmatter_clean = _filter_frontmatter(raw_frontmatter)
    if frontmatter_clean:
        frontmatter_clean = rewrite_paths(frontmatter_clean)

    if extension == "toml":
        # Convert Markdown variable syntax to TOML/Gemini variable syntax
        # Gemini CLI uses {{args}} instead of $ARGUMENTS
        # See: https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/custom-commands.md
        rendered_body = _convert_markdown_syntax_to_format(rendered_body, "toml")

        description_value = description
        if description_value.startswith('"') and description_value.endswith('"'):
            description_value = description_value[1:-1]
        description_value = description_value.replace('"', '\\"')
        body_text = rendered_body
        if not body_text.endswith("\n"):
            body_text += "\n"
        return f'description = "{description_value}"\n\nprompt = """\n{body_text}"""\n'

    if frontmatter_clean:
        result = f"---\n{frontmatter_clean}\n---\n\n{rendered_body}"
    else:
        result = rendered_body
    return result if result.endswith("\n") else result + "\n"


def _convert_markdown_syntax_to_format(content: str, target_format: str) -> str:
    """Convert Markdown variable syntax to target format syntax.

    Args:
        content: Rendered template content in Markdown syntax
        target_format: Target format (e.g., "toml" for Gemini)

    Returns:
        Content with variable syntax converted to target format

    Conversion rules:
    - Markdown (Claude/Codex): $ARGUMENTS, $AGENT_SCRIPT
    - TOML (Gemini): {{args}} (per https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/custom-commands.md)
    """
    if target_format == "toml":
        # Convert Claude/Codex Markdown variable syntax to Gemini TOML syntax
        # $ARGUMENTS → {{args}}
        content = content.replace("$ARGUMENTS", "{{args}}")
        return content

    # For other formats, return unchanged
    return content


def _filter_frontmatter(frontmatter_text: str) -> str:
    filtered_lines: list[str] = []
    skipping_block = False
    for line in frontmatter_text.splitlines():
        stripped = line.strip()
        if skipping_block:
            if line.startswith((" ", "\t")):
                continue
            skipping_block = False
        if stripped in {"scripts:", "agent_scripts:"}:
            skipping_block = True
            continue
        filtered_lines.append(line)
    return "\n".join(filtered_lines)


def _raise_template_discovery_error(commands_dir: Path) -> None:
    """Raise an informative error about template discovery failure."""
    env_root = os.environ.get("SPEC_KITTY_TEMPLATE_ROOT")
    remote_repo = os.environ.get("SPECIFY_TEMPLATE_REPO")

    error_msg = (
        "Templates could not be found in any of the expected locations:\n\n"
        "Checked paths (in order):\n"
        f"  ✗ Packaged resources (bundled with CLI)\n"
        f"  ✗ Environment variable SPEC_KITTY_TEMPLATE_ROOT" +
        (f" = {env_root}" if env_root else " (not set)") + "\n" +
        f"  ✗ Remote repository SPECIFY_TEMPLATE_REPO" +
        (f" = {remote_repo}" if remote_repo else " (not configured)") + "\n\n"
        "To fix this, try one of these approaches:\n\n"
        "1. Reinstall from PyPI (recommended for end users):\n"
        "   pip install --upgrade spec-kitty-cli\n\n"
        "2. Use --template-root flag (for development):\n"
        "   spec-kitty init . --template-root=/path/to/spec-kitty\n\n"
        "3. Set environment variable (for development):\n"
        "   export SPEC_KITTY_TEMPLATE_ROOT=/path/to/spec-kitty\n"
        "   spec-kitty init .\n\n"
        "4. Configure remote repository:\n"
        "   export SPECIFY_TEMPLATE_REPO=owner/repo\n"
        "   spec-kitty init .\n\n"
        "For development installs from source, use:\n"
        "   export SPEC_KITTY_TEMPLATE_ROOT=$(git rev-parse --show-toplevel)\n"
        "   spec-kitty init . --ai=claude"
    )

    raise FileNotFoundError(error_msg)


__all__ = [
    "generate_agent_assets",
    "render_command_template",
    "_convert_markdown_syntax_to_format",
]
