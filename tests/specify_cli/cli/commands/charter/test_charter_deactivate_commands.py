"""Tests for WP06/T026+T029: spec-kitty charter deactivate command.

Covers FR-005, FR-006, FR-007, FR-010:
- Happy path: deactivate an activated artifact
- Unknown kind: exits 1 with "Unknown kind" in output
- None-state: exits 1 with "spec-kitty upgrade" guidance
- Cascade flag: accepted and processed
- Shared artifact protection: skipped with appropriate message
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from specify_cli.cli.commands.charter import charter_app

runner = CliRunner()

pytestmark = [pytest.mark.fast]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def project_root_with_directive(tmp_path: Path) -> Path:
    """A project with activated_directives: [some-directive] in config.yaml."""
    kittify = tmp_path / ".kittify"
    kittify.mkdir()
    config_data = "activated_directives:\n  - some-directive\n"
    (kittify / "config.yaml").write_text(config_data, encoding="utf-8")
    return tmp_path


@pytest.fixture()
def empty_project_root(tmp_path: Path) -> Path:
    """A project with empty config.yaml (no activation keys)."""
    kittify = tmp_path / ".kittify"
    kittify.mkdir()
    (kittify / "config.yaml").write_text("# empty config\n", encoding="utf-8")
    return tmp_path


def _invoke_deactivate(project_root: Path, *args: str) -> object:
    """Invoke charter deactivate with --repo-root placed before positional args."""
    return runner.invoke(
        charter_app,
        ["deactivate", "--repo-root", str(project_root), *args],
        catch_exceptions=False,
    )


# ---------------------------------------------------------------------------
# test_deactivate_happy_path
# ---------------------------------------------------------------------------


class TestDeactivateHappyPath:
    def test_deactivate_directive_removes_from_config(
        self, project_root_with_directive: Path
    ) -> None:
        """Deactivating a directive removes it from config.yaml."""
        result = _invoke_deactivate(project_root_with_directive, "directive", "some-directive")
        assert result.exit_code == 0, result.output
        config = project_root_with_directive / ".kittify" / "config.yaml"
        data = yaml.safe_load(config.read_text())
        assert "some-directive" not in (data.get("activated_directives") or [])

    def test_deactivate_happy_path_prints_deactivated(
        self, project_root_with_directive: Path
    ) -> None:
        """Successful deactivation prints 'Deactivated' in output."""
        result = _invoke_deactivate(project_root_with_directive, "directive", "some-directive")
        assert result.exit_code == 0, result.output
        assert "Deactivated" in result.output


# ---------------------------------------------------------------------------
# test_deactivate_unknown_kind_exits_1
# ---------------------------------------------------------------------------


class TestDeactivateUnknownKind:
    def test_unknown_kind_exits_1(self, empty_project_root: Path) -> None:
        """Deactivating with an unknown kind exits with code 1."""
        result = runner.invoke(
            charter_app,
            ["deactivate", "--repo-root", str(empty_project_root), "nonsense", "some-id"],
        )
        assert result.exit_code == 1
        assert "Unknown kind" in result.output


# ---------------------------------------------------------------------------
# test_deactivate_none_state_exits_1
# ---------------------------------------------------------------------------


class TestDeactivateNoneState:
    def test_none_state_exits_1_with_upgrade_guidance(self, empty_project_root: Path) -> None:
        """Deactivating from None-state (no activation key) exits 1 with upgrade guidance."""
        result = runner.invoke(
            charter_app,
            ["deactivate", "--repo-root", str(empty_project_root), "directive", "some-directive"],
        )
        assert result.exit_code == 1
        # CharterPackManager calls sys.exit(1) for None-state;
        # CLI intercepts and prints upgrade guidance.
        assert "spec-kitty upgrade" in result.output or "upgrade" in result.output.lower()


# ---------------------------------------------------------------------------
# test_deactivate_cascade
# ---------------------------------------------------------------------------


class TestDeactivateCascade:
    def test_cascade_flag_accepted(self, project_root_with_directive: Path) -> None:
        """--cascade flag is accepted without error."""
        result = runner.invoke(
            charter_app,
            [
                "deactivate",
                "--repo-root",
                str(project_root_with_directive),
                "--cascade",
                "all",
                "directive",
                "some-directive",
            ],
            catch_exceptions=False,
        )
        assert result.exit_code == 0, result.output

    def test_cascade_emits_warning(self, project_root_with_directive: Path) -> None:
        """--cascade emits the deferred-DRG warning from CharterPackManager."""
        result = runner.invoke(
            charter_app,
            [
                "deactivate",
                "--repo-root",
                str(project_root_with_directive),
                "--cascade",
                "all",
                "directive",
                "some-directive",
            ],
            catch_exceptions=False,
        )
        # DRG cascade is deferred; a warning is expected
        assert "cascade" in result.output.lower() or "Warning" in result.output


# ---------------------------------------------------------------------------
# test_deactivate_shared_artifact_skipped
# ---------------------------------------------------------------------------


class TestDeactivateSharedArtifactSkipped:
    def test_not_in_activation_set_emits_warning(
        self, project_root_with_directive: Path
    ) -> None:
        """Deactivating an artifact not in the set emits a warning and exits 0."""
        result = _invoke_deactivate(
            project_root_with_directive, "directive", "nonexistent-directive"
        )
        # Not in set → warning, exit 0
        assert result.exit_code == 0, result.output
        assert "Warning" in result.output or "not in" in result.output.lower()
