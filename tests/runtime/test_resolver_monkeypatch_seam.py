"""Regression guard: `patch("runtime.discovery.resolver.get_kittify_home", ...)` must intercept every resolver call after WP02 delegation.

This test asserts the Option A seam-preservation strategy: runtime.discovery.resolver
has its own module-level bindings for get_kittify_home and get_package_asset_root.
Its resolve_* functions pass those names as provider keyword arguments at each call,
so patching the module's local attribute rebinds the value Python evaluates at the
call site.

If this test fails, the resolver was collapsed to a pure re-export (forbidden by
plan.md §Architecture & Design R1).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

import runtime.discovery.resolver as resolver_mod
from runtime.discovery.resolver import ResolutionTier, resolve_template


class TestMonkeypatchSeamSurvivesDelegation:
    def test_patch_get_kittify_home_intercepts_resolve_template(self, tmp_path: Path) -> None:
        fake_home = tmp_path / "fake-kittify-home"
        fake_home.mkdir()
        pkg_stub = fake_home / "missions" / "software-dev" / "templates" / "spec.md"
        pkg_stub.parent.mkdir(parents=True)
        pkg_stub.write_text("stub")

        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch.object(resolver_mod, "get_kittify_home", return_value=fake_home):
            result = resolve_template("spec.md", project_dir)

        assert result.tier is ResolutionTier.GLOBAL_MISSION
        assert result.path == pkg_stub

    def test_patch_get_package_asset_root_intercepts_fallback(self, tmp_path: Path) -> None:
        fake_asset_root = tmp_path / "fake-pkg-root"
        pkg_stub = fake_asset_root / "software-dev" / "templates" / "spec.md"
        pkg_stub.parent.mkdir(parents=True)
        pkg_stub.write_text("stub")

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        empty_home = tmp_path / "empty-home"
        empty_home.mkdir()

        with (
            patch.object(resolver_mod, "get_kittify_home", return_value=empty_home),
            patch.object(resolver_mod, "get_package_asset_root", return_value=fake_asset_root),
        ):
            result = resolve_template("spec.md", project_dir)

        assert result.tier is ResolutionTier.PACKAGE_DEFAULT
        assert result.path == pkg_stub

    def test_patch_string_form_also_intercepts(self, tmp_path: Path) -> None:
        """String-based patch on the dotted attribute path must also work."""
        fake_home = tmp_path / "string-fake-home"
        fake_home.mkdir()
        stub = fake_home / "missions" / "software-dev" / "command-templates" / "plan.md"
        stub.parent.mkdir(parents=True)
        stub.write_text("stub")

        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch("runtime.discovery.resolver.get_kittify_home", return_value=fake_home):
            from runtime.discovery.resolver import resolve_command

            result = resolve_command("plan.md", project_dir)

        assert result.tier is ResolutionTier.GLOBAL_MISSION
        assert result.path == stub


class TestReExportedSymbolsStillAvailable:
    def test_resolution_result_importable(self) -> None:
        from runtime.discovery.resolver import ResolutionResult

        assert ResolutionResult is not None

    def test_resolution_tier_importable(self) -> None:
        from runtime.discovery.resolver import ResolutionTier as Tier

        assert Tier.OVERRIDE.value == "override"


class TestFileNotFoundPropagates:
    def test_missing_asset_raises(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        empty_home = tmp_path / "empty"
        empty_home.mkdir()
        empty_pkg = tmp_path / "empty-pkg"
        empty_pkg.mkdir()

        with (
            patch.object(resolver_mod, "get_kittify_home", return_value=empty_home),
            patch.object(resolver_mod, "get_package_asset_root", return_value=empty_pkg),
        ):
            with pytest.raises(FileNotFoundError):
                resolve_template("nonexistent.md", project_dir)
