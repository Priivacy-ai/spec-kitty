"""Integration tests for --skills flag in spec-kitty init command.

Covers all four modes (auto, native, shared, wrappers-only) with various
agent combinations: all 12 agents, single native, single wrapper-only,
mixed native + shared, etc.
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from rich.console import Console
from typer import Typer
from typer.testing import CliRunner

from specify_cli.cli.commands import init as init_module
from specify_cli.cli.commands.init import register_init_command
from specify_cli.core.agent_surface import AGENT_SURFACE_CONFIG, DistributionClass
from specify_cli.skills.manifest import MANIFEST_PATH, compute_file_hash, load_manifest


@pytest.fixture()
def cli_app(monkeypatch: pytest.MonkeyPatch) -> tuple[Typer, Console, list[str]]:
    """Create a CLI app with mocked dependencies for testing."""
    console = Console(file=io.StringIO(), force_terminal=False)
    outputs: list[str] = []
    app = Typer()

    def fake_show_banner():
        outputs.append("banner")

    def fake_activate(project_path: Path, mission_key: str, mission_display: str, _console: Console) -> str:
        outputs.append(f"activate:{mission_key}")
        return mission_display

    def fake_ensure_scripts(path: Path, tracker=None):
        outputs.append(f"scripts:{path}")

    register_init_command(
        app,
        console=console,
        show_banner=fake_show_banner,
        activate_mission=fake_activate,
        ensure_executable_scripts=fake_ensure_scripts,
    )
    monkeypatch.setattr(init_module, "ensure_dashboard_running", lambda project: ("http://localhost", 1111, True))
    monkeypatch.setattr(init_module, "check_tool", lambda *args, **kwargs: True)
    return app, console, outputs


def _make_fake_assets():
    """Create a fake generate_agent_assets that produces spec-kitty.* wrappers."""
    created: list[Path] = []

    def fake_assets(commands_dir: Path, project_path: Path, agent_key: str, script: str):
        surface = AGENT_SURFACE_CONFIG[agent_key]
        wrapper_dir = project_path / surface.wrapper.dir
        wrapper_dir.mkdir(parents=True, exist_ok=True)
        wrapper_file = wrapper_dir / f"spec-kitty.implement.{surface.wrapper.ext}"
        wrapper_file.write_text(f"# stub wrapper for {agent_key}", encoding="utf-8")
        created.append(wrapper_file)

    return fake_assets, created


def _setup_local_mocks(monkeypatch, tmp_path):
    """Wire up local-mode template mocks so init does not fetch from network."""
    monkeypatch.setattr(
        init_module,
        "get_local_repo_root",
        lambda override_path=None: override_path or tmp_path / "templates",
    )

    def fake_copy(local_repo: Path, project_path: Path, script: str):
        commands_dir = project_path / ".templates"
        commands_dir.mkdir(parents=True, exist_ok=True)
        return commands_dir

    monkeypatch.setattr(init_module, "copy_specify_base_from_local", fake_copy)

    fake_assets, created = _make_fake_assets()
    monkeypatch.setattr(init_module, "generate_agent_assets", fake_assets)
    return created


def test_init_auto_mode_creates_skill_roots(cli_app, monkeypatch, tmp_path):
    """Auto mode should create shared + native roots depending on agents."""
    app, console, outputs = cli_app
    monkeypatch.chdir(tmp_path)
    _setup_local_mocks(monkeypatch, tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "init", "proj-auto",
            "--ai", "claude,codex",
            "--script", "sh",
            "--no-git",
            "--non-interactive",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output

    project_path = tmp_path / "proj-auto"

    # claude is NATIVE_ROOT_REQUIRED -> .claude/skills/
    assert (project_path / ".claude" / "skills").is_dir()
    assert (project_path / ".claude" / "skills" / ".gitkeep").exists()

    # codex is SHARED_ROOT_CAPABLE -> .agents/skills/
    assert (project_path / ".agents" / "skills").is_dir()
    assert (project_path / ".agents" / "skills" / ".gitkeep").exists()


def test_init_wrappers_only_creates_no_skill_roots(cli_app, monkeypatch, tmp_path):
    """wrappers-only mode should produce ZERO new skill root directories."""
    app, console, outputs = cli_app
    monkeypatch.chdir(tmp_path)
    _setup_local_mocks(monkeypatch, tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "init", "proj-wrap",
            "--ai", "claude,codex",
            "--script", "sh",
            "--no-git",
            "--non-interactive",
            "--skills", "wrappers-only",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output

    project_path = tmp_path / "proj-wrap"

    # No skill root directories should exist
    assert not (project_path / ".claude" / "skills").exists()
    assert not (project_path / ".agents" / "skills").exists()

    # Manifest should still be written
    manifest = load_manifest(project_path)
    assert manifest is not None
    assert manifest.installed_skill_roots == []
    assert manifest.skills_mode == "wrappers-only"


def test_init_invalid_skills_mode_rejected(cli_app, monkeypatch, tmp_path):
    """Invalid --skills value should cause exit code 1."""
    app, console, outputs = cli_app
    monkeypatch.chdir(tmp_path)
    _setup_local_mocks(monkeypatch, tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "init", "proj-bad",
            "--ai", "claude",
            "--script", "sh",
            "--no-git",
            "--non-interactive",
            "--skills", "invalid-mode",
        ],
    )
    assert result.exit_code == 1
    # Error message goes to Rich console, not CliRunner stdout
    console.file.seek(0)
    console_output = console.file.read()
    assert "Invalid --skills value" in console_output


def test_init_manifest_is_written(cli_app, monkeypatch, tmp_path):
    """Manifest file should be created with correct metadata."""
    app, console, outputs = cli_app
    monkeypatch.chdir(tmp_path)
    _setup_local_mocks(monkeypatch, tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "init", "proj-manifest",
            "--ai", "claude",
            "--script", "sh",
            "--no-git",
            "--non-interactive",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output

    project_path = tmp_path / "proj-manifest"
    manifest = load_manifest(project_path)

    assert manifest is not None
    assert manifest.skills_mode == "auto"
    assert "claude" in manifest.selected_agents
    assert len(manifest.managed_files) > 0

    # Should have both wrapper and skill_root_marker file types
    file_types = {mf.file_type for mf in manifest.managed_files}
    assert "wrapper" in file_types
    assert "skill_root_marker" in file_types

    # Skill root should be listed
    assert ".claude/skills/" in manifest.installed_skill_roots


def test_init_native_mode_prefers_vendor_roots(cli_app, monkeypatch, tmp_path):
    """Native mode should use vendor-native roots instead of shared root."""
    app, console, outputs = cli_app
    monkeypatch.chdir(tmp_path)
    _setup_local_mocks(monkeypatch, tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "init", "proj-native",
            "--ai", "copilot",
            "--script", "sh",
            "--no-git",
            "--non-interactive",
            "--skills", "native",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output

    project_path = tmp_path / "proj-native"

    # copilot in native mode should get .github/skills/ (vendor-native)
    assert (project_path / ".github" / "skills").is_dir()
    # Should NOT get .agents/skills/ (shared root)
    assert not (project_path / ".agents" / "skills").exists()


# ---------------------------------------------------------------------------
# T040 – Extended integration tests
# ---------------------------------------------------------------------------


def _invoke_init(
    app,
    monkeypatch,
    tmp_path,
    name: str,
    agents: str,
    skills_mode: str = "auto",
) -> Path:
    """Helper: run init and return project path."""
    _setup_local_mocks(monkeypatch, tmp_path)
    runner = CliRunner()
    args = [
        "init", name,
        "--ai", agents,
        "--script", "sh",
        "--no-git",
        "--non-interactive",
    ]
    if skills_mode != "auto":
        args.extend(["--skills", skills_mode])
    result = runner.invoke(app, args, catch_exceptions=False)
    assert result.exit_code == 0, result.output
    return tmp_path / name


def test_init_all_12_agents_auto(cli_app, monkeypatch, tmp_path):
    """Auto mode with all 12 agents creates shared + native roots."""
    app, console, outputs = cli_app
    monkeypatch.chdir(tmp_path)

    all_keys = ",".join(AGENT_SURFACE_CONFIG.keys())
    project_path = _invoke_init(app, monkeypatch, tmp_path, "all12", all_keys)

    # Shared root must exist (copilot, gemini, cursor, ... are SHARED_ROOT_CAPABLE)
    assert (project_path / ".agents" / "skills").is_dir()

    # Native roots must exist for NATIVE_ROOT_REQUIRED agents
    for key, surface in AGENT_SURFACE_CONFIG.items():
        if surface.distribution_class == DistributionClass.NATIVE_ROOT_REQUIRED:
            assert (project_path / surface.skill_roots[0]).is_dir(), (
                f"Missing native root for {key}"
            )

    # Manifest must list every agent
    manifest = load_manifest(project_path)
    assert manifest is not None
    assert set(manifest.selected_agents) == set(AGENT_SURFACE_CONFIG.keys())
    assert len(manifest.installed_skill_roots) > 0


def test_init_wrapper_only_agent_q_auto(cli_app, monkeypatch, tmp_path):
    """Auto mode with only wrapper-only agent 'q' produces no skill roots."""
    app, console, outputs = cli_app
    monkeypatch.chdir(tmp_path)

    project_path = _invoke_init(app, monkeypatch, tmp_path, "q-only", "q")

    # No skill root directories should exist
    assert not (project_path / ".agents" / "skills").exists()
    assert not (project_path / ".amazonq" / "skills").exists()

    manifest = load_manifest(project_path)
    assert manifest is not None
    assert manifest.installed_skill_roots == []
    assert manifest.selected_agents == ["q"]
    assert manifest.skills_mode == "auto"

    # Wrappers should still be tracked
    wrapper_paths = [mf.path for mf in manifest.managed_files if mf.file_type == "wrapper"]
    assert len(wrapper_paths) > 0


def test_init_single_native_agent(cli_app, monkeypatch, tmp_path):
    """Auto mode with single native agent creates only that agent's root."""
    app, console, outputs = cli_app
    monkeypatch.chdir(tmp_path)

    project_path = _invoke_init(app, monkeypatch, tmp_path, "qwen-only", "qwen")

    # qwen is NATIVE_ROOT_REQUIRED -> .qwen/skills/
    assert (project_path / ".qwen" / "skills").is_dir()
    assert (project_path / ".qwen" / "skills" / ".gitkeep").exists()
    # No shared root
    assert not (project_path / ".agents" / "skills").exists()

    manifest = load_manifest(project_path)
    assert manifest is not None
    assert manifest.installed_skill_roots == [".qwen/skills/"]


def test_init_shared_mode_behaves_like_auto(cli_app, monkeypatch, tmp_path):
    """Shared mode produces identical roots to auto mode."""
    app, console, outputs = cli_app
    monkeypatch.chdir(tmp_path)

    project_shared = _invoke_init(
        app, monkeypatch, tmp_path, "shared-test", "claude,codex", skills_mode="shared"
    )
    manifest_shared = load_manifest(project_shared)
    assert manifest_shared is not None
    assert manifest_shared.skills_mode == "shared"
    # Same roots as auto: .agents/skills/ (codex) + .claude/skills/ (claude)
    assert ".agents/skills/" in manifest_shared.installed_skill_roots
    assert ".claude/skills/" in manifest_shared.installed_skill_roots


def test_init_native_mode_copilot_and_claude(cli_app, monkeypatch, tmp_path):
    """Native mode with copilot and claude creates vendor-specific roots."""
    app, console, outputs = cli_app
    monkeypatch.chdir(tmp_path)

    project_path = _invoke_init(
        app, monkeypatch, tmp_path, "native-duo", "copilot,claude", skills_mode="native"
    )

    # copilot native -> .github/skills/
    assert (project_path / ".github" / "skills").is_dir()
    # claude native -> .claude/skills/
    assert (project_path / ".claude" / "skills").is_dir()
    # No shared root in native mode
    assert not (project_path / ".agents" / "skills").exists()

    manifest = load_manifest(project_path)
    assert manifest is not None
    assert manifest.skills_mode == "native"
    assert ".github/skills/" in manifest.installed_skill_roots
    assert ".claude/skills/" in manifest.installed_skill_roots
    assert ".agents/skills/" not in manifest.installed_skill_roots


def test_init_manifest_reflects_filesystem(cli_app, monkeypatch, tmp_path):
    """Every managed_file entry and installed_skill_root corresponds to real files."""
    app, console, outputs = cli_app
    monkeypatch.chdir(tmp_path)

    project_path = _invoke_init(app, monkeypatch, tmp_path, "fs-check", "claude,codex")

    manifest = load_manifest(project_path)
    assert manifest is not None

    # Every installed skill root must exist on disk
    for root in manifest.installed_skill_roots:
        assert (project_path / root).is_dir(), f"Root {root} does not exist"

    # Every managed file must exist on disk
    for mf in manifest.managed_files:
        file_path = project_path / mf.path
        assert file_path.exists(), f"Managed file {mf.path} does not exist"

    # Skill root markers (.gitkeep files) should have correct hashes
    for mf in manifest.managed_files:
        if mf.file_type == "skill_root_marker":
            actual_hash = compute_file_hash(project_path / mf.path)
            assert actual_hash == mf.sha256, (
                f"Hash mismatch for {mf.path}: expected {mf.sha256}, got {actual_hash}"
            )


def test_init_manifest_file_location(cli_app, monkeypatch, tmp_path):
    """Manifest file is written to .kittify/agent-surfaces/skills-manifest.yaml."""
    app, console, outputs = cli_app
    monkeypatch.chdir(tmp_path)

    project_path = _invoke_init(app, monkeypatch, tmp_path, "manifest-loc", "claude")

    manifest_file = project_path / MANIFEST_PATH
    assert manifest_file.exists()
    assert manifest_file.parent.name == "agent-surfaces"
