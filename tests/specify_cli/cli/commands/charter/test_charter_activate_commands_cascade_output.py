"""Tests for WP06/T024: spec-kitty charter activate refactored command.

Split from the original `test_charter_activate_commands.py` (ci-test-topology-
performance-01KXBJRT WP05/T021, FR-005) to break the `fast-tests-cli` job's
single-worker tail: `--dist loadfile` pins every test in a file to one xdist
worker, so one heavy monolith caps the job regardless of idle workers.

This sibling covers `TestCascadeOutputAbsence` in full (measured as the
heaviest of the three siblings, ~3.6s call time per test) — the happy-path/
error tests live in the `_core` sibling and the cascade-flag-handling tests
live in the `_cascade_flags` sibling.

Covers:
- T017: cascade-output absence test (SC-005)
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
def project_root(tmp_path: Path) -> Path:
    """A minimal project with .kittify/config.yaml."""
    kittify = tmp_path / ".kittify"
    kittify.mkdir()
    (kittify / "config.yaml").write_text("# empty config\n", encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------------------
# T017 — cascade-output absence test (SC-005)
# ---------------------------------------------------------------------------


class TestCascadeOutputAbsence:
    """Verify that stale deferral warning strings are absent from --cascade output."""

    def test_activate_cascade_no_not_yet_implemented(self, project_root: Path) -> None:
        """'not yet implemented' must not appear in charter activate --cascade output."""
        result = runner.invoke(
            charter_app,
            [
                "activate",
                "--repo-root",
                str(project_root),
                "--cascade",
                "all",
                "directive",
                "001-architectural-integrity-standard",
            ],
            catch_exceptions=False,
        )
        assert result.exit_code == 0, result.output
        assert "not yet implemented" not in result.output

    def test_activate_cascade_no_deferred(self, project_root: Path) -> None:
        """'deferred' must not appear in charter activate --cascade output."""
        result = runner.invoke(
            charter_app,
            [
                "activate",
                "--repo-root",
                str(project_root),
                "--cascade",
                "all",
                "directive",
                "001-architectural-integrity-standard",
            ],
            catch_exceptions=False,
        )
        assert result.exit_code == 0, result.output
        assert "deferred" not in result.output.lower()

    def test_activate_cascade_still_activates(self, project_root: Path) -> None:
        """cascade=True still activates the target artifact (real behavior unchanged)."""
        result = runner.invoke(
            charter_app,
            [
                "activate",
                "--repo-root",
                str(project_root),
                "--cascade",
                "all",
                "directive",
                "001-architectural-integrity-standard",
            ],
            catch_exceptions=False,
        )
        assert result.exit_code == 0, result.output
        config = project_root / ".kittify" / "config.yaml"
        data = yaml.safe_load(config.read_text())
        assert "001-architectural-integrity-standard" in data["activated_directives"]
