"""Tests for ``specify_cli.doctrine.config`` and the ``doctrine fetch`` CLI.

Covers the matrix from WP05 T026:

* Load: multi-pack, legacy single, absent key, no file, duplicate names,
  tilde expansion.
* Save: new block, merge with existing ``vcs``/``agents`` keys.
* Fetch CLI: all packs, ``--pack`` flag, unknown pack, empty registry.
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Any

import pytest
import typer
import yaml
from typer.testing import CliRunner

from specify_cli.doctrine.config import (
    OrgPackConfig,
    PackRegistry,
    load_pack_registry,
    resolve_org_roots,
    save_pack_registry,
)
from specify_cli.doctrine.sources.protocol import FetchResult


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

pytestmark = [pytest.mark.unit, pytest.mark.fast]

def _write_config(repo_root: Path, body: str) -> Path:
    config_dir = repo_root / ".kittify"
    config_dir.mkdir(parents=True, exist_ok=True)
    path = config_dir / "config.yaml"
    path.write_text(textwrap.dedent(body), encoding="utf-8")
    return path


# ----------------------------------------------------------------------
# load_pack_registry
# ----------------------------------------------------------------------
class TestLoadPackRegistry:
    def test_load_packs_list(self, tmp_path: Path) -> None:
        _write_config(
            tmp_path,
            """
            doctrine:
              org:
                packs:
                  - name: security
                    local_path: /opt/sec
                    source_type: git
                    url: git@example.com:sec/doctrine.git
                    ref: v1.0.0
                  - name: architecture
                    local_path: /opt/arch
            """,
        )
        registry = load_pack_registry(tmp_path)
        assert registry.names() == ["security", "architecture"]
        security = registry.get("security")
        assert security is not None
        assert security.source_type == "git"
        assert security.ref == "v1.0.0"

    def test_load_legacy_single_pack(self, tmp_path: Path) -> None:
        _write_config(
            tmp_path,
            """
            doctrine:
              org:
                local_path: /opt/legacy
                source_type: https
                url: https://example.com/bundle.tar.gz
            """,
        )
        registry = load_pack_registry(tmp_path)
        assert len(registry.packs) == 1
        only = registry.packs[0]
        assert only.name == "default"
        assert only.local_path == Path("/opt/legacy")
        assert only.source_type == "https"

    def test_load_config_absent_key(self, tmp_path: Path) -> None:
        _write_config(
            tmp_path,
            """
            agents:
              available: [claude]
            """,
        )
        registry = load_pack_registry(tmp_path)
        assert registry.packs == []

    def test_load_config_no_file(self, tmp_path: Path) -> None:
        registry = load_pack_registry(tmp_path)
        assert registry.packs == []

    def test_duplicate_pack_names(self, tmp_path: Path) -> None:
        _write_config(
            tmp_path,
            """
            doctrine:
              org:
                packs:
                  - name: security
                    local_path: /opt/sec1
                  - name: security
                    local_path: /opt/sec2
            """,
        )
        with pytest.warns(UserWarning, match="Duplicate pack names"):
            registry = load_pack_registry(tmp_path)
        assert registry.packs == []

    def test_tilde_expansion(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        monkeypatch.setenv("HOME", str(fake_home))
        _write_config(
            tmp_path,
            """
            doctrine:
              org:
                packs:
                  - name: security
                    local_path: "~/.kittify/org/security/"
            """,
        )
        registry = load_pack_registry(tmp_path)
        pack = registry.packs[0]
        assert "~" not in str(pack.local_path)
        assert str(pack.local_path).startswith(str(fake_home))

    def test_empty_file_returns_empty_registry(self, tmp_path: Path) -> None:
        _write_config(tmp_path, "")
        registry = load_pack_registry(tmp_path)
        assert registry.packs == []

    def test_unexpected_extra_field_yields_empty_registry(self, tmp_path: Path) -> None:
        _write_config(
            tmp_path,
            """
            doctrine:
              org:
                packs:
                  - name: sec
                    local_path: /opt/sec
                    bogus_field: oops
            """,
        )
        with pytest.warns(UserWarning, match="Invalid doctrine.org"):
            registry = load_pack_registry(tmp_path)
        assert registry.packs == []

    def test_canonical_config_visible_to_all_org_pack_consumers(
        self, tmp_path: Path
    ) -> None:
        """One canonical config shape must drive registry, DRG, and context paths."""
        from charter.context import _enumerate_org_pack_paths
        from charter.drg import load_org_drg

        pack_dir = tmp_path / "acme"
        (pack_dir / "drg").mkdir(parents=True)
        (pack_dir / "drg" / "fragment.yaml").write_text(
            "nodes: []\nedges: []\n",
            encoding="utf-8",
        )
        _write_config(
            tmp_path,
            f"""
            doctrine:
              org:
                packs:
                  - name: acme
                    local_path: {pack_dir}
            """,
        )

        assert [pack.name for pack in load_pack_registry(tmp_path).packs] == ["acme"]
        assert [fragment.pack_name for fragment in load_org_drg(tmp_path)] == ["acme"]
        assert [name for name, _path in _enumerate_org_pack_paths(tmp_path)] == ["acme"]

    def test_legacy_top_level_config_visible_to_all_org_pack_consumers(
        self, tmp_path: Path
    ) -> None:
        """Legacy ``organisation_packs`` is read through the same shared parser."""
        from charter.context import _enumerate_org_pack_paths
        from charter.drg import load_org_drg

        pack_dir = tmp_path / "legacy-acme"
        (pack_dir / "drg").mkdir(parents=True)
        (pack_dir / "drg" / "fragment.yaml").write_text(
            "nodes: []\nedges: []\n",
            encoding="utf-8",
        )
        _write_config(
            tmp_path,
            f"""
            organisation_packs:
              - name: acme
                source: local_path
                path: {pack_dir}
            """,
        )

        with pytest.warns(DeprecationWarning, match="organisation_packs"):
            assert [pack.name for pack in load_pack_registry(tmp_path).packs] == ["acme"]
        with pytest.warns(DeprecationWarning, match="organisation_packs"):
            assert [fragment.pack_name for fragment in load_org_drg(tmp_path)] == ["acme"]
        with pytest.warns(DeprecationWarning, match="organisation_packs"):
            assert [name for name, _path in _enumerate_org_pack_paths(tmp_path)] == ["acme"]


# ----------------------------------------------------------------------
# save_pack_registry
# ----------------------------------------------------------------------
class TestSavePackRegistry:
    def test_save_config_new_block(self, tmp_path: Path) -> None:
        registry = PackRegistry(
            packs=[
                OrgPackConfig(
                    name="security",
                    local_path=Path("/opt/sec"),
                    source_type="git",
                    url="git@example.com:sec.git",
                ),
            ]
        )
        save_pack_registry(tmp_path, registry)

        data = yaml.safe_load((tmp_path / ".kittify" / "config.yaml").read_text())
        assert data["doctrine"]["org"]["packs"] == [
            {
                "name": "security",
                "local_path": "/opt/sec",
                "source_type": "git",
                "url": "git@example.com:sec.git",
            }
        ]

    def test_save_config_merge(self, tmp_path: Path) -> None:
        _write_config(
            tmp_path,
            """
            vcs:
              provider: github
            agents:
              available: [claude, codex]
            doctrine:
              other_setting: keep_me
            """,
        )
        registry = PackRegistry(
            packs=[OrgPackConfig(name="security", local_path=Path("/opt/sec"))]
        )
        save_pack_registry(tmp_path, registry)

        data: dict[str, Any] = yaml.safe_load(
            (tmp_path / ".kittify" / "config.yaml").read_text()
        )
        assert data["vcs"] == {"provider": "github"}
        assert data["agents"] == {"available": ["claude", "codex"]}
        assert data["doctrine"]["other_setting"] == "keep_me"
        assert data["doctrine"]["org"]["packs"][0]["name"] == "security"

    def test_round_trip(self, tmp_path: Path) -> None:
        original = PackRegistry(
            packs=[
                OrgPackConfig(name="a", local_path=Path("/opt/a"), source_type="git", url="git@x:a.git"),
                OrgPackConfig(name="b", local_path=Path("/opt/b")),
            ]
        )
        save_pack_registry(tmp_path, original)
        reloaded = load_pack_registry(tmp_path)
        assert reloaded.names() == ["a", "b"]
        assert reloaded.get("a").source_type == "git"
        assert reloaded.get("b").source_type is None


# ----------------------------------------------------------------------
# resolve_org_roots
# ----------------------------------------------------------------------
class TestResolveOrgRoots:
    def test_returns_ordered_paths(self, tmp_path: Path) -> None:
        _write_config(
            tmp_path,
            """
            doctrine:
              org:
                packs:
                  - name: a
                    local_path: /opt/a
                  - name: b
                    local_path: /opt/b
            """,
        )
        roots = resolve_org_roots(tmp_path)
        assert roots == [Path("/opt/a"), Path("/opt/b")]

    def test_empty_when_unconfigured(self, tmp_path: Path) -> None:
        assert resolve_org_roots(tmp_path) == []


# ----------------------------------------------------------------------
# doctrine fetch CLI
# ----------------------------------------------------------------------
@pytest.fixture
def fetch_app(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> typer.Typer:
    """Build a small Typer app that just hosts the doctrine subcommands.

    Patching ``locate_project_root`` lets us bypass the real .kittify
    discovery and point fetch at ``tmp_path``.
    """
    import specify_cli.cli.commands.doctrine as doctrine_module

    monkeypatch.setattr(
        "specify_cli.core.paths.locate_project_root",
        lambda start=None: tmp_path,
    )
    return doctrine_module.app


class TestDoctrineFetchCLI:
    def test_fetch_no_config(self, fetch_app: typer.Typer, tmp_path: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(fetch_app, ["fetch"])
        assert result.exit_code == 1
        assert "No org doctrine packs configured" in result.stdout

    def test_fetch_unknown_pack_flag(self, fetch_app: typer.Typer, tmp_path: Path) -> None:
        _write_config(
            tmp_path,
            """
            doctrine:
              org:
                packs:
                  - name: security
                    local_path: /opt/sec
            """,
        )
        runner = CliRunner()
        result = runner.invoke(fetch_app, ["fetch", "--pack", "nonexistent"])
        assert result.exit_code == 1
        assert "nonexistent" in result.stdout
        assert "security" in result.stdout

    def test_fetch_all_packs(
        self,
        fetch_app: typer.Typer,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _write_config(
            tmp_path,
            """
            doctrine:
              org:
                packs:
                  - name: security
                    local_path: /opt/sec
                    source_type: git
                    url: git@example.com:sec/doctrine.git
                  - name: architecture
                    local_path: /opt/arch
                    source_type: git
                    url: git@example.com:arch/doctrine.git
            """,
        )
        fetched_names: list[str] = []

        def fake_fetch_pack(pack: OrgPackConfig, repo_root: Path) -> FetchResult:
            fetched_names.append(pack.name)
            assert isinstance(3, int)  # artifacts_written must be int (FR-007)
            return FetchResult(
                ok=True, artifacts_written=3, pack_version="v1.0.0"
            )

        monkeypatch.setattr(
            "specify_cli.doctrine.snapshot.fetch_pack", fake_fetch_pack
        )

        runner = CliRunner()
        result = runner.invoke(fetch_app, ["fetch"])
        assert result.exit_code == 0, result.stdout
        assert fetched_names == ["security", "architecture"]
        assert "security" in result.stdout
        assert "architecture" in result.stdout

    def test_fetch_single_pack_flag(
        self,
        fetch_app: typer.Typer,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _write_config(
            tmp_path,
            """
            doctrine:
              org:
                packs:
                  - name: security
                    local_path: /opt/sec
                    source_type: git
                    url: git@example.com:sec/doctrine.git
                  - name: architecture
                    local_path: /opt/arch
                    source_type: git
                    url: git@example.com:arch/doctrine.git
            """,
        )
        fetched_names: list[str] = []
        monkeypatch.setattr(
            "specify_cli.doctrine.snapshot.fetch_pack",
            lambda pack, repo_root: (
                fetched_names.append(pack.name)
                or FetchResult(ok=True, artifacts_written=1, pack_version=None)
            ),
        )
        runner = CliRunner()
        result = runner.invoke(fetch_app, ["fetch", "--pack", "security"])
        assert result.exit_code == 0, result.stdout
        assert fetched_names == ["security"]

    def test_fetch_dry_run(self, fetch_app: typer.Typer, tmp_path: Path) -> None:
        _write_config(
            tmp_path,
            """
            doctrine:
              org:
                packs:
                  - name: security
                    local_path: /opt/sec
                    source_type: git
                    url: git@example.com:sec/doctrine.git
            """,
        )
        runner = CliRunner()
        result = runner.invoke(fetch_app, ["fetch", "--dry-run"])
        assert result.exit_code == 0
        assert "Would fetch" in result.stdout
        assert "security" in result.stdout

    def test_fetch_reports_failures(
        self,
        fetch_app: typer.Typer,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _write_config(
            tmp_path,
            """
            doctrine:
              org:
                packs:
                  - name: security
                    local_path: /opt/sec
                    source_type: git
                    url: git@example.com:sec/doctrine.git
            """,
        )
        monkeypatch.setattr(
            "specify_cli.doctrine.snapshot.fetch_pack",
            lambda pack, repo_root: FetchResult(
                ok=False, artifacts_written=0, pack_version=None,
                errors=["network unreachable"],
            ),
        )
        runner = CliRunner()
        result = runner.invoke(fetch_app, ["fetch"])
        assert result.exit_code == 1
        assert "failed" in result.stdout
        assert "network unreachable" in result.stdout


# ----------------------------------------------------------------------
# pack validate / assemble — live implementation wiring (WP06)
# ----------------------------------------------------------------------
class TestDoctrinePackCommands:
    def test_pack_validate_missing_dir_exits_nonzero(
        self, fetch_app: typer.Typer, tmp_path: Path
    ) -> None:
        runner = CliRunner()
        result = runner.invoke(
            fetch_app, ["pack", "validate", str(tmp_path / "pack")]
        )
        # Missing pack directory is a validation error → exit 1.
        assert result.exit_code == 1

    def test_pack_validate_empty_pack_exits_zero(
        self, fetch_app: typer.Typer, tmp_path: Path
    ) -> None:
        # An empty directory is a structurally valid (no-op) pack.
        empty_pack = tmp_path / "empty-pack"
        empty_pack.mkdir()
        runner = CliRunner()
        result = runner.invoke(
            fetch_app, ["pack", "validate", str(empty_pack)]
        )
        assert result.exit_code == 0, result.stdout

    def test_pack_assemble_missing_inputs_exits_nonzero(
        self, fetch_app: typer.Typer, tmp_path: Path
    ) -> None:
        runner = CliRunner()
        result = runner.invoke(
            fetch_app,
            ["pack", "assemble", str(tmp_path / "out"), str(tmp_path / "in")],
        )
        assert result.exit_code == 1
