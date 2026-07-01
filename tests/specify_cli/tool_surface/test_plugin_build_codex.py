"""Tests for the CodexBundleProjector plugin build command (WP06).

Covers:
    - T024: --target codex path exists; .codex-plugin/plugin.json generated
    - T025: "hooks" and "agents" keys absent; all required interface fields present
    - T026: skills/ populated with >= MIN_SKILL_COUNT canonical command skills
    - T027: marketplace.json generated with correct schema
    - _validate_manifest raises BuildError on forbidden keys and missing fields
    - Build is idempotent (second run produces identical output)
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from specify_cli.skills.command_installer import CANONICAL_COMMANDS
from specify_cli.tool_surface.bundles._builder import MIN_SKILL_COUNT, BuildError
from specify_cli.tool_surface.bundles.codex import CodexBundleProjector

pytestmark = [pytest.mark.unit, pytest.mark.fast]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_build(tmp_path: Path, *, skip_validate: bool = True) -> Path:
    """Build a Codex bundle and return the bundle directory."""
    result = CodexBundleProjector(tmp_path / "dist").build(skip_validate=skip_validate)
    return Path(result)


def _read_manifest(bundle_dir: Path) -> dict[str, object]:
    manifest_path = bundle_dir / ".codex-plugin" / "plugin.json"
    return json.loads(manifest_path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# T024 — .codex-plugin/plugin.json generated with correct schema
# ---------------------------------------------------------------------------


class TestPluginJson:
    def test_manifest_dir_exists(self, tmp_path: Path) -> None:
        bundle_dir = _run_build(tmp_path)
        assert (bundle_dir / ".codex-plugin").is_dir()

    def test_plugin_json_exists(self, tmp_path: Path) -> None:
        bundle_dir = _run_build(tmp_path)
        assert (bundle_dir / ".codex-plugin" / "plugin.json").is_file(), (
            "plugin.json must exist under .codex-plugin/"
        )

    def test_plugin_json_has_real_version(self, tmp_path: Path) -> None:
        bundle_dir = _run_build(tmp_path)
        payload = _read_manifest(bundle_dir)
        version = payload["version"]
        assert version != "0.0.0", (
            "plugin.json version must come from importlib.metadata, not the placeholder"
        )
        assert re.match(r"\d+\.\d+", str(version)), (
            f"version {version!r} does not look like a version string"
        )

    def test_plugin_json_name(self, tmp_path: Path) -> None:
        bundle_dir = _run_build(tmp_path)
        payload = _read_manifest(bundle_dir)
        assert payload["name"] == "spec-kitty"

    def test_plugin_json_skills_pointer(self, tmp_path: Path) -> None:
        bundle_dir = _run_build(tmp_path)
        payload = _read_manifest(bundle_dir)
        assert payload["skills"] == "skills/"

    def test_plugin_json_description_present(self, tmp_path: Path) -> None:
        bundle_dir = _run_build(tmp_path)
        payload = _read_manifest(bundle_dir)
        assert payload.get("description"), "description must be a non-empty string"

    def test_plugin_json_author_name(self, tmp_path: Path) -> None:
        bundle_dir = _run_build(tmp_path)
        payload = _read_manifest(bundle_dir)
        author = payload.get("author")
        assert isinstance(author, dict), "author must be a dict"
        assert author.get("name") == "Priivacy AI"

    def test_plugin_json_interface_display_name(self, tmp_path: Path) -> None:
        bundle_dir = _run_build(tmp_path)
        payload = _read_manifest(bundle_dir)
        iface = payload.get("interface")
        assert isinstance(iface, dict), "interface must be a dict"
        assert iface.get("displayName") == "Spec Kitty"

    def test_plugin_json_interface_short_description(self, tmp_path: Path) -> None:
        bundle_dir = _run_build(tmp_path)
        payload = _read_manifest(bundle_dir)
        iface = payload.get("interface", {})
        assert isinstance(iface, dict)
        short_desc = iface.get("shortDescription", "")
        assert isinstance(short_desc, str) and short_desc, (
            "interface.shortDescription must be a non-empty string"
        )
        assert len(short_desc) <= 120, (
            f"interface.shortDescription must be <= 120 chars, got {len(short_desc)}"
        )


# ---------------------------------------------------------------------------
# T025 — "hooks" and "agents" keys absent from manifest
# ---------------------------------------------------------------------------


class TestForbiddenKeys:
    def test_hooks_key_absent(self, tmp_path: Path) -> None:
        """'hooks' MUST NOT appear at the top level of Codex plugin.json."""
        bundle_dir = _run_build(tmp_path)
        payload = _read_manifest(bundle_dir)
        assert "hooks" not in payload, (
            "Codex plugin.json must NOT contain a 'hooks' key "
            "(hooks are discovered by filesystem presence only)"
        )

    def test_agents_key_absent(self, tmp_path: Path) -> None:
        """'agents' MUST NOT appear at the top level of Codex plugin.json."""
        bundle_dir = _run_build(tmp_path)
        payload = _read_manifest(bundle_dir)
        assert "agents" not in payload, (
            "Codex plugin.json must NOT contain an 'agents' key"
        )

    def test_validate_manifest_raises_on_hooks_key(self, tmp_path: Path) -> None:
        projector = CodexBundleProjector(tmp_path / "dist")
        bad_manifest: dict[str, object] = {
            "name": "spec-kitty",
            "version": "1.0.0",
            "description": "test",
            "author": {"name": "Priivacy AI"},
            "interface": {
                "displayName": "Spec Kitty",
                "shortDescription": "short",
            },
            "hooks": "hooks/",  # forbidden
        }
        with pytest.raises(BuildError, match="hooks"):
            projector._validate_manifest(bad_manifest)

    def test_validate_manifest_raises_on_agents_key(self, tmp_path: Path) -> None:
        projector = CodexBundleProjector(tmp_path / "dist")
        bad_manifest: dict[str, object] = {
            "name": "spec-kitty",
            "version": "1.0.0",
            "description": "test",
            "author": {"name": "Priivacy AI"},
            "interface": {
                "displayName": "Spec Kitty",
                "shortDescription": "short",
            },
            "agents": "agents/",  # forbidden
        }
        with pytest.raises(BuildError, match="agents"):
            projector._validate_manifest(bad_manifest)

    def test_validate_manifest_raises_on_missing_name(self, tmp_path: Path) -> None:
        projector = CodexBundleProjector(tmp_path / "dist")
        bad_manifest: dict[str, object] = {
            "version": "1.0.0",
            "description": "test",
            "author": {"name": "Priivacy AI"},
            "interface": {
                "displayName": "Spec Kitty",
                "shortDescription": "short",
            },
        }
        with pytest.raises(BuildError, match="'name'"):
            projector._validate_manifest(bad_manifest)

    def test_validate_manifest_raises_on_missing_author_name(
        self, tmp_path: Path
    ) -> None:
        projector = CodexBundleProjector(tmp_path / "dist")
        bad_manifest: dict[str, object] = {
            "name": "spec-kitty",
            "version": "1.0.0",
            "description": "test",
            "author": {},  # missing "name"
            "interface": {
                "displayName": "Spec Kitty",
                "shortDescription": "short",
            },
        }
        with pytest.raises(BuildError, match="author.name"):
            projector._validate_manifest(bad_manifest)

    def test_validate_manifest_raises_on_missing_interface_display_name(
        self, tmp_path: Path
    ) -> None:
        projector = CodexBundleProjector(tmp_path / "dist")
        bad_manifest: dict[str, object] = {
            "name": "spec-kitty",
            "version": "1.0.0",
            "description": "test",
            "author": {"name": "Priivacy AI"},
            "interface": {
                "shortDescription": "short",
                # "displayName" missing
            },
        }
        with pytest.raises(BuildError, match="interface.displayName"):
            projector._validate_manifest(bad_manifest)

    def test_validate_manifest_raises_on_missing_interface_short_description(
        self, tmp_path: Path
    ) -> None:
        projector = CodexBundleProjector(tmp_path / "dist")
        bad_manifest: dict[str, object] = {
            "name": "spec-kitty",
            "version": "1.0.0",
            "description": "test",
            "author": {"name": "Priivacy AI"},
            "interface": {
                "displayName": "Spec Kitty",
                # "shortDescription" missing
            },
        }
        with pytest.raises(BuildError, match="interface.shortDescription"):
            projector._validate_manifest(bad_manifest)

    def test_validate_manifest_raises_on_short_description_too_long(
        self, tmp_path: Path
    ) -> None:
        projector = CodexBundleProjector(tmp_path / "dist")
        bad_manifest: dict[str, object] = {
            "name": "spec-kitty",
            "version": "1.0.0",
            "description": "test",
            "author": {"name": "Priivacy AI"},
            "interface": {
                "displayName": "Spec Kitty",
                "shortDescription": "x" * 121,  # exceeds 120-char limit
            },
        }
        with pytest.raises(BuildError, match="shortDescription"):
            projector._validate_manifest(bad_manifest)

    def test_validate_manifest_passes_on_valid_manifest(
        self, tmp_path: Path
    ) -> None:
        projector = CodexBundleProjector(tmp_path / "dist")
        valid_manifest: dict[str, object] = {
            "name": "spec-kitty",
            "version": "3.2.0",
            "description": "Spec-Driven Development toolkit.",
            "author": {"name": "Priivacy AI"},
            "interface": {
                "displayName": "Spec Kitty",
                "shortDescription": "Spec-Driven Development for teams.",
            },
            "skills": "skills/",
        }
        # Must not raise.
        projector._validate_manifest(valid_manifest)


# ---------------------------------------------------------------------------
# T026 — skills/ populated from canonical command-skill set
# ---------------------------------------------------------------------------


class TestSkillsCopy:
    def test_skills_dir_populated(self, tmp_path: Path) -> None:
        bundle_dir = _run_build(tmp_path)
        skills_dir = bundle_dir / "skills"
        assert skills_dir.is_dir(), "skills/ directory must be created"
        skill_files = list(skills_dir.glob("*/SKILL.md"))
        assert len(skill_files) >= MIN_SKILL_COUNT, (
            f"Expected at least {MIN_SKILL_COUNT} skills, found {len(skill_files)}"
        )

    def test_all_canonical_commands_present(self, tmp_path: Path) -> None:
        bundle_dir = _run_build(tmp_path)
        for command in CANONICAL_COMMANDS:
            skill_file = bundle_dir / "skills" / f"spec-kitty.{command}" / "SKILL.md"
            assert skill_file.is_file(), (
                f"Missing SKILL.md for canonical command: {command}"
            )

    def test_skill_files_have_frontmatter(self, tmp_path: Path) -> None:
        """Each SKILL.md must start with YAML frontmatter."""
        bundle_dir = _run_build(tmp_path)
        for skill_md in sorted((bundle_dir / "skills").glob("*/SKILL.md")):
            content = skill_md.read_text(encoding="utf-8")
            assert content.startswith("---"), (
                f"{skill_md.name} does not start with YAML frontmatter"
            )

    def test_skills_dir_uses_spec_kitty_prefix(self, tmp_path: Path) -> None:
        """All skill subdirectories must follow the spec-kitty.<cmd> naming."""
        bundle_dir = _run_build(tmp_path)
        for skill_dir in (bundle_dir / "skills").iterdir():
            if skill_dir.is_dir():
                assert skill_dir.name.startswith("spec-kitty."), (
                    f"Skill directory {skill_dir.name!r} must start with 'spec-kitty.'"
                )


# ---------------------------------------------------------------------------
# T027 — marketplace.json generated
# ---------------------------------------------------------------------------


class TestMarketplaceJson:
    def test_marketplace_json_exists(self, tmp_path: Path) -> None:
        bundle_dir = _run_build(tmp_path)
        assert (bundle_dir / "marketplace.json").is_file()

    def test_marketplace_json_schema(self, tmp_path: Path) -> None:
        bundle_dir = _run_build(tmp_path)
        payload = json.loads(
            (bundle_dir / "marketplace.json").read_text(encoding="utf-8")
        )
        assert payload.get("name") == "spec-kitty-plugins"
        assert isinstance(payload.get("plugins"), list)
        assert len(payload["plugins"]) >= 1

    def test_marketplace_plugin_entry(self, tmp_path: Path) -> None:
        bundle_dir = _run_build(tmp_path)
        payload = json.loads(
            (bundle_dir / "marketplace.json").read_text(encoding="utf-8")
        )
        plugin_entry = payload["plugins"][0]
        assert plugin_entry.get("name") == "spec-kitty"
        source = plugin_entry.get("source", {})
        assert source.get("source") == "local"
        assert "path" in source

    def test_marketplace_json_not_written_to_agents_dir(
        self, tmp_path: Path
    ) -> None:
        """marketplace.json must NOT be written outside output_dir (C-006)."""
        _run_build(tmp_path)
        # Should not pollute .agents/plugins/ in the project tree.
        assert not (tmp_path / ".agents" / "plugins" / "marketplace.json").exists()

    def test_marketplace_json_interface_display_name(self, tmp_path: Path) -> None:
        bundle_dir = _run_build(tmp_path)
        payload = json.loads(
            (bundle_dir / "marketplace.json").read_text(encoding="utf-8")
        )
        iface = payload.get("interface", {})
        assert isinstance(iface, dict)
        assert iface.get("displayName")


# ---------------------------------------------------------------------------
# FR-027 — .mcp.json companion projected "when applicable"
# ---------------------------------------------------------------------------


class TestMcpCompanion:
    """The Codex bundle carries ``.mcp.json`` + ``mcpServers`` pointer only when
    a canonical MCP source exists ("when applicable", FR-027 /
    plugin-manifest-codex-01)."""

    def test_no_mcp_json_when_no_source(self, tmp_path: Path) -> None:
        """Absent MCP source: no companion file and no manifest pointer.

        This is the current canonical behavior (no MCP source ships in
        doctrine today) and must stay a guarded no-op, not a silent gap.
        """
        bundle_dir = _run_build(tmp_path)
        assert not (bundle_dir / ".mcp.json").exists(), (
            ".mcp.json must NOT be written when no MCP source is present"
        )
        payload = _read_manifest(bundle_dir)
        assert "mcpServers" not in payload, (
            "mcpServers pointer must be absent when there is no .mcp.json"
        )

    def test_mcp_json_projected_when_source_present(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Present MCP source: companion copied and ``mcpServers`` pointer set.

        Drives the two MCP-aware units directly (``_copy_mcp_if_present`` then
        ``_generate_plugin_json``) so the doctrine-root monkeypatch only
        affects the MCP companion lookup and not the unrelated skill renderer.
        """
        import doctrine

        # Point the doctrine root at a fake package dir carrying a .mcp.json.
        fake_doctrine_root = tmp_path / "fake_doctrine"
        fake_doctrine_root.mkdir()
        mcp_payload = '{"mcpServers": {"demo": {"command": "echo"}}}\n'
        (fake_doctrine_root / ".mcp.json").write_text(
            mcp_payload, encoding="utf-8"
        )
        monkeypatch.setattr(
            doctrine, "__file__", str(fake_doctrine_root / "__init__.py")
        )

        projector = CodexBundleProjector(tmp_path / "dist")
        projector.bundle_dir.mkdir(parents=True, exist_ok=True)
        projector._copy_mcp_if_present()
        projector._generate_plugin_json("3.2.0")

        staged = projector.bundle_dir / ".mcp.json"
        assert staged.is_file(), ".mcp.json must be staged when a source is present"
        assert staged.read_text(encoding="utf-8") == mcp_payload, (
            ".mcp.json contents must be copied verbatim"
        )
        payload = _read_manifest(projector.bundle_dir)
        assert payload.get("mcpServers") == "./.mcp.json", (
            "manifest must advertise mcpServers -> ./.mcp.json when companion present"
        )


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


class TestIdempotency:
    def test_second_build_produces_same_output(self, tmp_path: Path) -> None:
        """Running build twice must produce byte-identical output."""
        projector = CodexBundleProjector(tmp_path / "dist")
        bundle_dir_1 = projector.build(skip_validate=True)

        snapshot_1: dict[str, bytes] = {}
        for f in sorted(bundle_dir_1.rglob("*")):
            if f.is_file():
                snapshot_1[str(f.relative_to(bundle_dir_1))] = f.read_bytes()

        bundle_dir_2 = projector.build(skip_validate=True)
        assert bundle_dir_1 == bundle_dir_2

        snapshot_2: dict[str, bytes] = {}
        for f in sorted(bundle_dir_2.rglob("*")):
            if f.is_file():
                snapshot_2[str(f.relative_to(bundle_dir_2))] = f.read_bytes()

        assert snapshot_1 == snapshot_2, (
            "Build is not idempotent: second run produced different files"
        )


# ---------------------------------------------------------------------------
# CLI dispatch integration
# ---------------------------------------------------------------------------


class TestCliDispatch:
    def test_plugin_build_codex_via_cli(self, tmp_path: Path) -> None:
        """spec-kitty plugin build --target codex must complete without error.

        The CliRunner is invoked against ``plugin_app`` directly; typer
        maps ``plugin_app`` to its single registered sub-command (``build``)
        when invoked without a sub-command name prefix.
        """
        from typer.testing import CliRunner

        from specify_cli.cli.commands.plugin import plugin_app

        runner = CliRunner()
        result = runner.invoke(
            plugin_app,
            ["--target", "codex", "--output-dir", str(tmp_path / "dist")],
        )
        assert result.exit_code == 0, (
            f"CLI exited with {result.exit_code}:\n{result.output}"
        )
        assert (
            tmp_path / "dist" / "codex" / ".codex-plugin" / "plugin.json"
        ).is_file()

    def test_plugin_build_unknown_target_via_cli(self, tmp_path: Path) -> None:
        """Unknown --target must produce a non-zero exit."""
        from typer.testing import CliRunner

        from specify_cli.cli.commands.plugin import plugin_app

        runner = CliRunner()
        result = runner.invoke(
            plugin_app,
            ["--target", "unknown-target"],
        )
        assert result.exit_code != 0
