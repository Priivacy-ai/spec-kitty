"""Integration tests for ``spec-kitty config --show-origin``.

Covers:
- T027: Verify tier labels match actual resolution behavior (1A-14, 1A-15)
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.runtime.show_origin import collect_origins


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_file(path: Path, content: str = "placeholder") -> Path:
    """Create a file (and any missing parent dirs), return its path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


# ---------------------------------------------------------------------------
# T027 -- Integration: tier labels match actual resolution
# ---------------------------------------------------------------------------


class TestShowOriginLabelsMatchResolution:
    """Each tier label corresponds to actual resolved file (1A-14, 1A-15)."""

    def test_override_and_global_tiers_together(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Override and global tiers coexist correctly in one run."""
        project = tmp_path / "project"
        global_home = tmp_path / "global"
        monkeypatch.setenv("SPEC_KITTY_HOME", str(global_home))

        # Place spec-template.md at override tier
        override_path = _create_file(
            project / ".kittify" / "overrides" / "templates" / "spec-template.md",
            content="override",
        )

        # Place plan-template.md at global tier
        global_path = _create_file(
            global_home / "missions" / "software-dev" / "templates" / "plan-template.md",
            content="global",
        )

        with patch(
            "specify_cli.runtime.resolver.get_package_asset_root",
            side_effect=FileNotFoundError("no pkg"),
        ):
            entries = collect_origins(project)

        spec_entry = next(e for e in entries if e.name == "spec-template.md")
        assert spec_entry.tier == "override"
        assert spec_entry.resolved_path == override_path

        plan_entry = next(e for e in entries if e.name == "plan-template.md")
        assert plan_entry.tier == "global"
        assert plan_entry.resolved_path == global_path

    def test_package_default_tier(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Package-default tier resolves when no higher tiers provide the asset."""
        project = tmp_path / "project"
        (project / ".kittify").mkdir(parents=True)
        global_home = tmp_path / "global"
        monkeypatch.setenv("SPEC_KITTY_HOME", str(global_home))

        pkg_root = tmp_path / "pkg"
        pkg_path = _create_file(
            pkg_root / "software-dev" / "templates" / "spec-template.md",
        )

        with patch(
            "specify_cli.runtime.resolver.get_package_asset_root",
            return_value=pkg_root,
        ):
            entries = collect_origins(project)

        spec_entry = next(e for e in entries if e.name == "spec-template.md")
        assert spec_entry.tier == "package_default"
        assert spec_entry.resolved_path == pkg_path

    def test_not_found_entries(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Assets not found at any tier have None path and tier, with error message."""
        project = tmp_path / "project"
        (project / ".kittify").mkdir(parents=True)
        global_home = tmp_path / "global"
        monkeypatch.setenv("SPEC_KITTY_HOME", str(global_home))

        with patch(
            "specify_cli.runtime.resolver.get_package_asset_root",
            side_effect=FileNotFoundError("no pkg"),
        ):
            entries = collect_origins(project)

        # All entries should be not found since we created nothing
        for entry in entries:
            assert entry.resolved_path is None
            assert entry.tier is None
            assert entry.error is not None
            assert "not found" in entry.error.lower()
