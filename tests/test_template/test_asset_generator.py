from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.template.asset_generator import (
    generate_agent_assets,
    prepare_command_templates,
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


def _write_template_with_body(path: Path, body: str) -> None:
    path.write_text(
        f"""---
description: Demo Template
scripts:
  sh: echo hi
---
{body}
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
    # Version marker is embedded inside the prompt block for TOML output
    assert 'prompt = """' in output
    assert 'Run echo hi {{args}}  for gemini.' in output
    assert '<!-- spec-kitty-command-version:' in output


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


def test_render_command_template_injects_agent_placeholder(tmp_path: Path) -> None:
    template_path = tmp_path / "workflow.md"
    template_path.write_text(
        """---
description: Workflow Example
scripts:
  sh: echo hi
---
spec-kitty agent action implement WP01 --agent __AGENT__
""",
        encoding="utf-8",
    )

    output = render_command_template(
        template_path,
        script_type="sh",
        agent_key="codex",
        arg_format="$ARGUMENTS",
        extension="md",
    )

    assert "spec-kitty agent action implement WP01 --agent codex" in output


def test_prepare_command_templates_overlays_mission(tmp_path: Path) -> None:
    base_dir = tmp_path / "base"
    mission_dir = tmp_path / "missions" / "software-dev" / "command-templates"
    base_dir.mkdir(parents=True)
    mission_dir.mkdir(parents=True)

    _write_template_with_body(base_dir / "demo.md", "Base content for __AGENT__.")
    _write_template_with_body(base_dir / "baseonly.md", "Base-only template.")
    _write_template_with_body(mission_dir / "demo.md", "Mission override for __AGENT__.")

    merged_dir = prepare_command_templates(base_dir, mission_dir)

    project_path = tmp_path / "project"
    project_path.mkdir()
    generate_agent_assets(merged_dir, project_path, "codex", "sh")

    demo_output = project_path / ".codex" / "prompts" / "spec-kitty.demo.md"
    base_output = project_path / ".codex" / "prompts" / "spec-kitty.baseonly.md"

    assert demo_output.exists()
    assert base_output.exists()
    assert "Mission override for codex." in demo_output.read_text(encoding="utf-8")
    assert "Base-only template." in base_output.read_text(encoding="utf-8")


def test_prepare_command_templates_inherits_scripts_from_base(tmp_path: Path) -> None:
    base_dir = tmp_path / "base"
    mission_dir = tmp_path / "missions" / "software-dev" / "command-templates"
    base_dir.mkdir(parents=True)
    mission_dir.mkdir(parents=True)

    (base_dir / "analyze.md").write_text(
        """---
description: Base
scripts:
  sh: spec-kitty agent mission check-prerequisites --json --include-tasks
---
Run {SCRIPT}
""",
        encoding="utf-8",
    )
    (mission_dir / "analyze.md").write_text(
        """---
description: Mission
---
Mission body uses {SCRIPT}
""",
        encoding="utf-8",
    )

    merged_dir = prepare_command_templates(base_dir, mission_dir)
    rendered = render_command_template(
        merged_dir / "analyze.md",
        script_type="sh",
        agent_key="codex",
        arg_format="$ARGUMENTS",
        extension="md",
    )
    assert "spec-kitty agent mission check-prerequisites" in rendered


def test_prepare_command_templates_inherits_agent_scripts_from_base(tmp_path: Path) -> None:
    base_dir = tmp_path / "base"
    mission_dir = tmp_path / "missions" / "software-dev" / "command-templates"
    base_dir.mkdir(parents=True)
    mission_dir.mkdir(parents=True)

    (base_dir / "analyze.md").write_text(
        """---
description: Base
scripts:
  sh: spec-kitty run
agent_scripts:
  sh: source .kittify/env.sh
---
Run {SCRIPT} {AGENT_SCRIPT}
""",
        encoding="utf-8",
    )
    (mission_dir / "analyze.md").write_text(
        """---
description: Mission
scripts:
  sh: spec-kitty run
---
Mission body uses {SCRIPT} {AGENT_SCRIPT}
""",
        encoding="utf-8",
    )

    merged_dir = prepare_command_templates(base_dir, mission_dir)
    rendered = render_command_template(
        merged_dir / "analyze.md",
        script_type="sh",
        agent_key="codex",
        arg_format="$ARGUMENTS",
        extension="md",
    )
    assert "source .kittify/env.sh" in rendered


def test_prepare_command_templates_handles_non_dict_frontmatter(tmp_path: Path) -> None:
    base_dir = tmp_path / "base"
    mission_dir = tmp_path / "missions" / "software-dev" / "command-templates"
    base_dir.mkdir(parents=True)
    mission_dir.mkdir(parents=True)

    (base_dir / "demo.md").write_text(
        """---
- not-a-dict
---
Base body should be ignored.
""",
        encoding="utf-8",
    )
    (mission_dir / "demo.md").write_text(
        """---
- also-not-a-dict
---
Mission-only body.
""",
        encoding="utf-8",
    )

    merged_dir = prepare_command_templates(base_dir, mission_dir)
    merged_text = (merged_dir / "demo.md").read_text(encoding="utf-8")
    assert merged_text.strip() == "Mission-only body."


def test_render_command_template_markdown_starts_with_yaml_frontmatter(tmp_path: Path) -> None:
    """Markdown output must open with ``---`` so slash-command pickers parse the description."""
    template_path = tmp_path / "demo.md"
    _write_template(template_path)

    output = render_command_template(
        template_path,
        script_type="sh",
        agent_key="claude",
        arg_format="$ARGUMENTS",
        extension="md",
    )

    lines = output.splitlines()
    assert lines[0] == "---", f"first line was {lines[0]!r}, not ---"
    assert "description: Demo Template" in lines, "description not preserved in frontmatter"
    # The closing --- comes before the version marker
    closing_index = next(i for i in range(1, len(lines)) if lines[i] == "---")
    assert lines[closing_index + 1].startswith("<!-- spec-kitty-command-version:"), (
        "Version marker must immediately follow the closing --- of the frontmatter"
    )


def test_render_command_template_markdown_marker_not_on_line_zero(tmp_path: Path) -> None:
    """Regression: the version marker must not displace the YAML frontmatter from line 1."""
    template_path = tmp_path / "demo.md"
    _write_template(template_path)

    output = render_command_template(
        template_path,
        script_type="sh",
        agent_key="claude",
        arg_format="$ARGUMENTS",
        extension="md",
    )

    assert not output.splitlines()[0].startswith("<!-- spec-kitty-command-version:"), (
        "Marker on line 0 would break Claude Code's frontmatter parsing — "
        "this is the bug the fix addresses."
    )


def test_render_command_template_markdown_preserves_body(tmp_path: Path) -> None:
    template_path = tmp_path / "demo.md"
    _write_template(template_path)

    output = render_command_template(
        template_path,
        script_type="sh",
        agent_key="claude",
        arg_format="$ARGUMENTS",
        extension="md",
    )

    assert "Run echo hi $ARGUMENTS source env for claude." in output


def test_render_command_template_markdown_without_frontmatter_still_emits_marker(tmp_path: Path) -> None:
    """Templates without YAML frontmatter still receive a version marker (legacy fallback)."""
    template_path = tmp_path / "no_frontmatter.md"
    template_path.write_text("Body content for __AGENT__.\n", encoding="utf-8")

    output = render_command_template(
        template_path,
        script_type="sh",
        agent_key="claude",
        arg_format="$ARGUMENTS",
        extension="md",
    )

    # Without frontmatter, the marker is the first line (no description to preserve).
    assert output.splitlines()[0].startswith("<!-- spec-kitty-command-version:")
    assert "Body content for claude." in output


def test_bundled_software_dev_templates_have_descriptions(tmp_path: Path) -> None:
    """Every shipped command-template must declare a description in its frontmatter."""
    from specify_cli.template.renderer import parse_frontmatter

    repo_root = Path(__file__).resolve().parents[2]
    templates_dir = repo_root / "src" / "specify_cli" / "missions" / "software-dev" / "command-templates"
    assert templates_dir.is_dir(), f"templates dir missing: {templates_dir}"

    template_files = sorted(templates_dir.glob("*.md"))
    assert template_files, "no command templates discovered — fixture is wrong"

    for template_file in template_files:
        meta, _body, _raw = parse_frontmatter(template_file.read_text(encoding="utf-8"))
        description = str(meta.get("description", "")).strip()
        assert description, (
            f"{template_file.name} missing 'description' in YAML frontmatter — "
            f"slash-command pickers will show garbage"
        )


def test_render_command_template_fails_when_script_missing_and_required(tmp_path: Path) -> None:
    template_path = tmp_path / "broken.md"
    template_path.write_text(
        """---
description: Broken
---
Run {SCRIPT}
""",
        encoding="utf-8",
    )

    try:
        render_command_template(
            template_path,
            script_type="sh",
            agent_key="codex",
            arg_format="$ARGUMENTS",
            extension="md",
        )
    except ValueError as exc:
        assert "requires scripts.sh" in str(exc)
    else:
        raise AssertionError("Expected ValueError for missing scripts.sh")
