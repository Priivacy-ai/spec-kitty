"""Agent-specific asset rendering helpers."""

from __future__ import annotations

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


__all__ = [
    "generate_agent_assets",
    "render_command_template",
]
