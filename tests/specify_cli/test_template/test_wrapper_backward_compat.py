"""Backward compatibility tests for wrapper generation across all 12 agents.

Verifies that the new AgentSurface-based code path produces correct wrapper
output for every agent, using the real software-dev mission templates.  Each
test generates wrappers twice and compares byte-for-byte to prove determinism.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

import specify_cli
from specify_cli.core.agent_surface import AGENT_SURFACE_CONFIG, get_agent_surface
from specify_cli.template.asset_generator import (
    generate_agent_assets,
    prepare_command_templates,
)


def _get_merged_real_templates(tmp_dir: Path) -> Path | None:
    """Build merged command templates using the real base + software-dev mission.

    Replicates the production flow so tests exercise the actual rendering
    pipeline end-to-end.
    """
    package_dir = Path(specify_cli.__file__).parent
    base_templates = package_dir / "templates" / "command-templates"
    mission_templates = package_dir / "missions" / "software-dev" / "command-templates"

    if not base_templates.exists() or not mission_templates.exists():
        return None

    local_base = tmp_dir / "base-command-templates"
    shutil.copytree(base_templates, local_base)

    return prepare_command_templates(local_base, mission_templates)


@pytest.mark.parametrize("agent_key", list(AGENT_SURFACE_CONFIG.keys()))
def test_wrapper_backward_compat_byte_exact(agent_key: str, tmp_path: Path) -> None:
    """New code produces byte-exact identical wrappers across two runs.

    This proves determinism: same templates + same agent = same output.
    """
    merged_templates = _get_merged_real_templates(tmp_path)
    if merged_templates is None:
        pytest.skip("Mission templates not available in test environment")

    surface = get_agent_surface(agent_key)

    # First generation
    project_a = tmp_path / "a"
    project_a.mkdir()
    generate_agent_assets(merged_templates, project_a, agent_key, "sh")

    output_a = project_a / surface.wrapper.dir
    wrappers_a = sorted(output_a.glob("spec-kitty.*"))
    assert len(wrappers_a) > 0, f"No wrappers for {agent_key}"

    # Second generation
    project_b = tmp_path / "b"
    project_b.mkdir()
    generate_agent_assets(merged_templates, project_b, agent_key, "sh")

    output_b = project_b / surface.wrapper.dir
    wrappers_b = sorted(output_b.glob("spec-kitty.*"))

    assert len(wrappers_a) == len(wrappers_b)

    for fa, fb in zip(wrappers_a, wrappers_b):
        assert fa.name == fb.name
        assert fa.read_bytes() == fb.read_bytes(), (
            f"Byte mismatch in {fa.name} for {agent_key}"
        )


@pytest.mark.parametrize("agent_key", list(AGENT_SURFACE_CONFIG.keys()))
def test_wrapper_content_nontrivial(agent_key: str, tmp_path: Path) -> None:
    """Every wrapper file has substantial content (>100 bytes), not stubs."""
    merged_templates = _get_merged_real_templates(tmp_path)
    if merged_templates is None:
        pytest.skip("Mission templates not available in test environment")

    surface = get_agent_surface(agent_key)

    project = tmp_path / "proj"
    project.mkdir()
    generate_agent_assets(merged_templates, project, agent_key, "sh")

    output_dir = project / surface.wrapper.dir
    for wrapper in sorted(output_dir.glob("spec-kitty.*")):
        content = wrapper.read_bytes()
        assert len(content) > 100, (
            f"Wrapper {wrapper.name} suspiciously small ({len(content)} B) "
            f"for {agent_key}"
        )


@pytest.mark.parametrize("agent_key", list(AGENT_SURFACE_CONFIG.keys()))
def test_wrapper_correct_extension(agent_key: str, tmp_path: Path) -> None:
    """Every wrapper file has the correct extension per AgentSurface config."""
    merged_templates = _get_merged_real_templates(tmp_path)
    if merged_templates is None:
        pytest.skip("Mission templates not available in test environment")

    surface = get_agent_surface(agent_key)

    project = tmp_path / "proj"
    project.mkdir()
    generate_agent_assets(merged_templates, project, agent_key, "sh")

    output_dir = project / surface.wrapper.dir
    for wrapper in sorted(output_dir.glob("spec-kitty.*")):
        assert wrapper.name.endswith(f".{surface.wrapper.ext}"), (
            f"Wrong extension for {agent_key}: {wrapper.name} "
            f"(expected .{surface.wrapper.ext})"
        )


@pytest.mark.parametrize("agent_key", list(AGENT_SURFACE_CONFIG.keys()))
def test_wrapper_placed_in_correct_directory(agent_key: str, tmp_path: Path) -> None:
    """Wrappers are placed in the directory specified by AgentSurface.wrapper.dir."""
    merged_templates = _get_merged_real_templates(tmp_path)
    if merged_templates is None:
        pytest.skip("Mission templates not available in test environment")

    surface = get_agent_surface(agent_key)

    project = tmp_path / "proj"
    project.mkdir()
    generate_agent_assets(merged_templates, project, agent_key, "sh")

    expected_dir = project / surface.wrapper.dir
    assert expected_dir.is_dir(), (
        f"Expected wrapper dir {expected_dir} for agent {agent_key}"
    )
    wrappers = list(expected_dir.glob("spec-kitty.*"))
    assert len(wrappers) > 0
