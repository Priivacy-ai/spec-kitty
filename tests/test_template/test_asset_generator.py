from __future__ import annotations

from pathlib import Path

from specify_cli.template.asset_generator import (
    generate_agent_assets,
    render_command_template,
)


def _write_template(path: Path, with_agent_script: bool = True) -> None:
    agent_block = "agent_scripts:\n  sh: source env\n" if with_agent_script else ""
    path.write_text(
        f"""---
description: Demo Template
scripts:
  sh: echo hi
{agent_block}---
Run {{SCRIPT}} {{ARGS}} {{AGENT_SCRIPT}} for __AGENT__.
""",
        encoding="utf-8",
    )


def test_render_command_template_generates_markdown(tmp_path: Path) -> None:
    template_path = tmp_path / "demo.md"
    _write_template(template_path)

    output = render_command_template(
        template_path,
        script_type="sh",
        agent_key="codex",
        arg_format="$ARGUMENTS",
        extension="md",
    )

    assert "scripts:" not in output
    assert "Run echo hi $ARGUMENTS source env for codex." in output


def test_render_command_template_handles_toml_extension(tmp_path: Path) -> None:
    template_path = tmp_path / "demo.md"
    _write_template(template_path, with_agent_script=False)

    output = render_command_template(
        template_path,
        script_type="sh",
        agent_key="gemini",
        arg_format="{{args}}",
        extension="toml",
    )

    assert output.startswith('description = "Demo Template"')
    assert 'prompt = """\nRun echo hi {{args}}  for gemini.\n"""' in output


def test_generate_agent_assets_creates_expected_files(tmp_path: Path) -> None:
    commands_dir = tmp_path / "commands"
    commands_dir.mkdir()
    _write_template(commands_dir / "demo.md")

    project_path = tmp_path / "project"
    project_path.mkdir()

    generate_agent_assets(commands_dir, project_path, "codex", "sh")

    output_file = project_path / ".codex" / "prompts" / "spec-kitty.demo.md"
    assert output_file.exists()
    content = output_file.read_text(encoding="utf-8")
    assert "Run echo hi $ARGUMENTS source env for codex." in content
