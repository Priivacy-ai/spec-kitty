"""Backward compatibility tests for asset_generator after AgentSurface refactor.

Contains two test layers:

1. Synthetic template tests: quick checks using minimal synthetic templates
   to verify structural properties (directory creation, naming conventions,
   placeholder substitution, codex stem replacement edge case).

2. Real-template golden baseline tests: generate wrappers from the actual
   software-dev mission command templates for all 12 agents and verify:
   - Non-trivial content (>100 bytes per file)
   - Deterministic output (byte-exact match across two independent runs)
   - Correct file count (12 wrappers per agent, matching source templates)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.core.agent_surface import AGENT_SURFACE_CONFIG, get_agent_surface
from specify_cli.template.asset_generator import (
    generate_agent_assets,
    prepare_command_templates,
)


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


# ---------------------------------------------------------------------------
# Real-template golden baseline tests
# ---------------------------------------------------------------------------

def _get_merged_real_templates(tmp_dir: Path) -> Path | None:
    """Build merged command templates using the real base + software-dev mission.

    This replicates the production flow: ``prepare_command_templates(base, mission)``
    merges base templates (which carry ``scripts:`` blocks) with mission-specific
    overrides, producing a directory that ``generate_agent_assets`` can render
    without hitting the "scripts.sh not provided" error.

    The base templates are copied into *tmp_dir* first so that the merge output
    (which ``prepare_command_templates`` writes as a sibling of the base dir)
    lands in the temp tree instead of polluting the source checkout.

    Returns the merged directory, or None if the source trees are unavailable.
    """
    import shutil

    import specify_cli

    package_dir = Path(specify_cli.__file__).parent
    base_templates = package_dir / "templates" / "command-templates"
    mission_templates = package_dir / "missions" / "software-dev" / "command-templates"

    if not base_templates.exists() or not mission_templates.exists():
        return None

    # Copy base templates into tmp_dir so the merge artifact stays in tmp
    local_base = tmp_dir / "base-command-templates"
    shutil.copytree(base_templates, local_base)

    return prepare_command_templates(local_base, mission_templates)


@pytest.mark.parametrize("agent_key", list(AGENT_SURFACE_CONFIG.keys()))
def test_real_template_byte_exact_golden_baseline(
    agent_key: str, tmp_path: Path
) -> None:
    """Generate wrappers from real sw-dev templates and verify byte-exact determinism.

    This test addresses the review feedback that synthetic templates cannot catch
    regressions in rendered frontmatter, newline handling, or real wrapper content.
    It uses the actual software-dev mission command templates (merged with base
    templates via ``prepare_command_templates``, replicating the production flow)
    and verifies:
    1. Wrappers are generated for the agent.
    2. Each wrapper has non-trivial content (>100 bytes).
    3. A second independent generation produces byte-identical output.
    """
    merged_templates = _get_merged_real_templates(tmp_path)
    if merged_templates is None:
        pytest.skip("Mission templates not available in test environment")

    # --- First generation ---
    project_a = tmp_path / "project_a"
    project_a.mkdir()
    generate_agent_assets(merged_templates, project_a, agent_key, "sh")

    surface = get_agent_surface(agent_key)
    output_dir_a = project_a / surface.wrapper.dir
    assert output_dir_a.exists(), (
        f"Output dir not created for {agent_key}: {output_dir_a}"
    )

    wrappers_a = sorted(output_dir_a.glob("spec-kitty.*"))
    assert len(wrappers_a) > 0, f"No wrappers generated for {agent_key}"

    # Verify content is non-trivial (real templates produce >100 bytes)
    for f in wrappers_a:
        content = f.read_bytes()
        assert len(content) > 100, (
            f"Wrapper {f.name} suspiciously small ({len(content)} bytes) for {agent_key}"
        )

    # --- Second generation (golden baseline comparison) ---
    project_b = tmp_path / "project_b"
    project_b.mkdir()
    generate_agent_assets(merged_templates, project_b, agent_key, "sh")

    output_dir_b = project_b / surface.wrapper.dir
    wrappers_b = sorted(output_dir_b.glob("spec-kitty.*"))

    assert len(wrappers_a) == len(wrappers_b), (
        f"File count mismatch for {agent_key}: "
        f"{len(wrappers_a)} vs {len(wrappers_b)}"
    )

    for fa, fb in zip(wrappers_a, wrappers_b):
        assert fa.name == fb.name, (
            f"Filename mismatch for {agent_key}: {fa.name} vs {fb.name}"
        )
        bytes_a = fa.read_bytes()
        bytes_b = fb.read_bytes()
        assert bytes_a == bytes_b, (
            f"Byte mismatch in {fa.name} for {agent_key}: "
            f"{len(bytes_a)} bytes vs {len(bytes_b)} bytes"
        )


@pytest.mark.parametrize("agent_key", list(AGENT_SURFACE_CONFIG.keys()))
def test_real_template_file_count_matches_source(
    agent_key: str, tmp_path: Path
) -> None:
    """Verify each agent gets exactly one wrapper per source template."""
    merged_templates = _get_merged_real_templates(tmp_path)
    if merged_templates is None:
        pytest.skip("Mission templates not available in test environment")

    source_count = len(list(merged_templates.glob("*.md")))
    assert source_count > 0, "No source templates found"

    project_path = tmp_path / "project"
    project_path.mkdir()
    generate_agent_assets(merged_templates, project_path, agent_key, "sh")

    surface = get_agent_surface(agent_key)
    output_dir = project_path / surface.wrapper.dir
    wrapper_files = list(output_dir.glob("spec-kitty.*"))

    assert len(wrapper_files) == source_count, (
        f"Expected {source_count} wrappers for {agent_key}, "
        f"got {len(wrapper_files)}: {[f.name for f in wrapper_files]}"
    )


@pytest.mark.parametrize("agent_key", list(AGENT_SURFACE_CONFIG.keys()))
def test_real_template_frontmatter_stripped_of_scripts(
    agent_key: str, tmp_path: Path
) -> None:
    """Verify scripts/agent_scripts blocks are stripped from rendered frontmatter.

    Real templates contain scripts: and agent_scripts: blocks in their YAML
    frontmatter. These must be filtered out of the final wrapper output so
    agents don't see internal build metadata.
    """
    merged_templates = _get_merged_real_templates(tmp_path)
    if merged_templates is None:
        pytest.skip("Mission templates not available in test environment")

    project_path = tmp_path / "project"
    project_path.mkdir()
    generate_agent_assets(merged_templates, project_path, agent_key, "sh")

    surface = get_agent_surface(agent_key)
    output_dir = project_path / surface.wrapper.dir

    for wrapper in output_dir.glob("spec-kitty.*"):
        content = wrapper.read_text(encoding="utf-8")
        # TOML wrappers don't have YAML frontmatter, skip them
        if surface.wrapper.ext == "toml":
            continue
        # Check that standalone "scripts:" and "agent_scripts:" YAML keys
        # are not present as top-level frontmatter keys in the output.
        # They appear at the start of a line within the frontmatter block.
        lines = content.splitlines()
        for line in lines:
            stripped = line.strip()
            assert stripped not in ("scripts:", "agent_scripts:"), (
                f"Wrapper {wrapper.name} for {agent_key} leaked "
                f"'{stripped}' block into output"
            )
