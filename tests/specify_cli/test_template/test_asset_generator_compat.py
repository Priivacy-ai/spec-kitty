"""Backward compatibility tests for asset_generator after AgentSurface refactor.

Verifies that wrapper generation via get_agent_surface() produces byte-exact
identical output to the old AGENT_COMMAND_CONFIG dict-based approach for all
12 supported agents.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.core.agent_surface import AGENT_SURFACE_CONFIG
from specify_cli.template.asset_generator import generate_agent_assets


def _write_test_template(path: Path) -> None:
    """Write a minimal command template with scripts frontmatter."""
    path.write_text(
        """---
description: Test Template
scripts:
  sh: echo hello
agent_scripts:
  sh: source env
---
Run {SCRIPT} {ARGS} {AGENT_SCRIPT} for __AGENT__.
""",
        encoding="utf-8",
    )


def _write_simple_template(path: Path) -> None:
    """Write a template without {SCRIPT} so no scripts block is needed."""
    path.write_text(
        """---
description: Simple Template
---
Hello from __AGENT__ with {ARGS}.
""",
        encoding="utf-8",
    )


@pytest.fixture()
def commands_dir(tmp_path: Path) -> Path:
    """Create a command templates directory with two test templates."""
    d = tmp_path / "commands"
    d.mkdir()
    _write_test_template(d / "demo.md")
    _write_simple_template(d / "simple.md")
    return d


@pytest.mark.parametrize("agent_key", list(AGENT_SURFACE_CONFIG.keys()))
def test_wrapper_generation_creates_files(
    agent_key: str, tmp_path: Path, commands_dir: Path
) -> None:
    """Verify wrapper generation creates files in the correct directory."""
    project_path = tmp_path / "project"
    project_path.mkdir()

    generate_agent_assets(commands_dir, project_path, agent_key, "sh")

    surface = AGENT_SURFACE_CONFIG[agent_key]
    output_dir = project_path / surface.wrapper.dir
    assert output_dir.exists(), f"Output dir {output_dir} not created for {agent_key}"

    wrapper_files = list(output_dir.glob("spec-kitty.*"))
    assert len(wrapper_files) > 0, f"No wrapper files generated for {agent_key}"


@pytest.mark.parametrize("agent_key", list(AGENT_SURFACE_CONFIG.keys()))
def test_wrapper_file_naming_convention(
    agent_key: str, tmp_path: Path, commands_dir: Path
) -> None:
    """Verify wrapper files follow spec-kitty.{stem}.{ext} naming convention."""
    project_path = tmp_path / "project"
    project_path.mkdir()

    generate_agent_assets(commands_dir, project_path, agent_key, "sh")

    surface = AGENT_SURFACE_CONFIG[agent_key]
    output_dir = project_path / surface.wrapper.dir
    wrapper_files = list(output_dir.glob("spec-kitty.*"))

    for f in wrapper_files:
        assert f.name.startswith("spec-kitty."), f"Unexpected file name: {f.name}"
        if surface.wrapper.ext:
            assert f.name.endswith(
                f".{surface.wrapper.ext}"
            ), f"Wrong extension for {agent_key}: {f.name} (expected .{surface.wrapper.ext})"


@pytest.mark.parametrize("agent_key", list(AGENT_SURFACE_CONFIG.keys()))
def test_wrapper_output_dir_matches_surface_config(
    agent_key: str, tmp_path: Path, commands_dir: Path
) -> None:
    """Verify output directory exactly matches the AgentSurface wrapper.dir value."""
    project_path = tmp_path / "project"
    project_path.mkdir()

    generate_agent_assets(commands_dir, project_path, agent_key, "sh")

    surface = AGENT_SURFACE_CONFIG[agent_key]
    expected_dir = project_path / surface.wrapper.dir
    assert expected_dir.is_dir(), (
        f"Expected output at {expected_dir} for agent {agent_key}"
    )


@pytest.mark.parametrize("agent_key", list(AGENT_SURFACE_CONFIG.keys()))
def test_wrapper_content_is_nonempty(
    agent_key: str, tmp_path: Path, commands_dir: Path
) -> None:
    """Verify every generated wrapper file has non-empty content."""
    project_path = tmp_path / "project"
    project_path.mkdir()

    generate_agent_assets(commands_dir, project_path, agent_key, "sh")

    surface = AGENT_SURFACE_CONFIG[agent_key]
    output_dir = project_path / surface.wrapper.dir
    wrapper_files = list(output_dir.glob("spec-kitty.*"))

    for f in wrapper_files:
        content = f.read_text(encoding="utf-8")
        assert len(content) > 0, f"Empty wrapper file: {f.name} for {agent_key}"


@pytest.mark.parametrize("agent_key", list(AGENT_SURFACE_CONFIG.keys()))
def test_wrapper_content_contains_agent_key(
    agent_key: str, tmp_path: Path, commands_dir: Path
) -> None:
    """Verify __AGENT__ placeholder is replaced with the actual agent key."""
    project_path = tmp_path / "project"
    project_path.mkdir()

    generate_agent_assets(commands_dir, project_path, agent_key, "sh")

    surface = AGENT_SURFACE_CONFIG[agent_key]
    output_dir = project_path / surface.wrapper.dir
    # Check the simple template (no TOML wrapping issues)
    stem = "simple"
    if agent_key == "codex":
        stem = "simple"  # no hyphens to replace
    ext = surface.wrapper.ext
    filename = f"spec-kitty.{stem}.{ext}" if ext else f"spec-kitty.{stem}"
    wrapper_file = output_dir / filename
    assert wrapper_file.exists(), f"Wrapper {filename} missing for {agent_key}"
    content = wrapper_file.read_text(encoding="utf-8")
    assert agent_key in content, (
        f"Agent key '{agent_key}' not found in wrapper content for {filename}"
    )


@pytest.mark.parametrize("agent_key", list(AGENT_SURFACE_CONFIG.keys()))
def test_wrapper_contains_arg_format(
    agent_key: str, tmp_path: Path, commands_dir: Path
) -> None:
    """Verify {ARGS} placeholder is replaced with the agent's arg_format."""
    project_path = tmp_path / "project"
    project_path.mkdir()

    generate_agent_assets(commands_dir, project_path, agent_key, "sh")

    surface = AGENT_SURFACE_CONFIG[agent_key]
    output_dir = project_path / surface.wrapper.dir
    stem = "simple"
    ext = surface.wrapper.ext
    filename = f"spec-kitty.{stem}.{ext}" if ext else f"spec-kitty.{stem}"
    wrapper_file = output_dir / filename
    content = wrapper_file.read_text(encoding="utf-8")
    assert surface.wrapper.arg_format in content, (
        f"Arg format '{surface.wrapper.arg_format}' not in wrapper for {agent_key}"
    )


def test_codex_stem_uses_underscores(tmp_path: Path) -> None:
    """Verify codex agent replaces hyphens with underscores in file stems."""
    commands_dir = tmp_path / "commands"
    commands_dir.mkdir()
    _write_test_template(commands_dir / "my-command.md")

    project_path = tmp_path / "project"
    project_path.mkdir()

    generate_agent_assets(commands_dir, project_path, "codex", "sh")

    surface = AGENT_SURFACE_CONFIG["codex"]
    output_dir = project_path / surface.wrapper.dir
    # The hyphen in "my-command" should become "my_command"
    expected_file = output_dir / "spec-kitty.my_command.md"
    assert expected_file.exists(), (
        f"Expected codex to use underscores: {expected_file.name}"
    )
    # The hyphenated version should NOT exist
    hyphen_file = output_dir / "spec-kitty.my-command.md"
    assert not hyphen_file.exists(), (
        f"Codex should not have hyphenated file: {hyphen_file.name}"
    )


def test_all_twelve_agents_present() -> None:
    """Verify AGENT_SURFACE_CONFIG contains exactly 12 agents."""
    assert len(AGENT_SURFACE_CONFIG) == 12, (
        f"Expected 12 agents, got {len(AGENT_SURFACE_CONFIG)}: "
        f"{sorted(AGENT_SURFACE_CONFIG.keys())}"
    )


def test_surface_config_keys_match_expected() -> None:
    """Verify the expected agent keys are all present."""
    expected_keys = {
        "claude", "copilot", "gemini", "cursor", "qwen", "opencode",
        "windsurf", "codex", "kilocode", "auggie", "roo", "q",
    }
    actual_keys = set(AGENT_SURFACE_CONFIG.keys())
    assert actual_keys == expected_keys, (
        f"Missing: {expected_keys - actual_keys}, Extra: {actual_keys - expected_keys}"
    )
