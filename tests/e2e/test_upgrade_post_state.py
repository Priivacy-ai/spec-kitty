"""End-to-end regression for FR-002 / #705 schema_version clobber.

This test drives the actual ``spec-kitty`` CLI via subprocess against a fresh
tmp project that carries pre-3.x metadata (no ``spec_kitty.schema_version``)
and asserts that, after ``spec-kitty upgrade --yes`` reports success:

  1. ``.kittify/metadata.yaml`` actually contains ``spec_kitty.schema_version``
     equal to the CLI's required schema version.
  2. The very next ``spec-kitty agent mission branch-context --json`` exits 0
     with ``result == "success"`` -- i.e. the schema-version gate does NOT
     trip with ``PROJECT_MIGRATION_NEEDED`` immediately after a successful
     upgrade.

This is the operator-visible promise of WP01: no manual ``schema_version: 3``
stamp should ever be required after ``spec-kitty upgrade``.
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path

import pytest
import yaml

from specify_cli.migration.schema_version import REQUIRED_SCHEMA_VERSION


def _make_pre_schema_project(root: Path) -> None:
    """Create a minimal pre-3.x Spec Kitty project at ``root``.

    The project has:
    - a git repo on ``main`` with one commit
    - a ``.kittify/metadata.yaml`` carrying ``spec_kitty.version`` but
      explicitly no ``schema_version`` field (the legacy state that the
      schema-version gate trips on).
    """
    subprocess.run(
        ["git", "init", "--initial-branch=main"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "e2e@example.com"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "E2E Test"],
        cwd=root,
        check=True,
        capture_output=True,
    )

    kittify = root / ".kittify"
    kittify.mkdir()

    # Pre-schema-version metadata: no ``schema_version`` key under spec_kitty.
    legacy_metadata = {
        "spec_kitty": {
            "version": "0.12.0",
            "initialized_at": datetime.fromisoformat("2026-01-01T00:00:00").isoformat(),
            "last_upgraded_at": None,
        },
        "environment": {
            "python_version": "",
            "platform": "",
            "platform_version": "",
        },
        "migrations": {"applied": []},
    }
    (kittify / "metadata.yaml").write_text(
        yaml.dump(legacy_metadata, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )

    subprocess.run(
        ["git", "add", "."],
        cwd=root,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Pre-3.x project state"],
        cwd=root,
        check=True,
        capture_output=True,
    )


@pytest.mark.e2e
def test_upgrade_then_branch_context_does_not_gate(
    tmp_path: Path, run_cli
) -> None:
    """Regression: after ``spec-kitty upgrade --yes``, schema_version is stamped
    AND the next gated command (``agent mission branch-context``) is allowed
    through. Reproduces the FR-002 / #705 trap.
    """
    project = tmp_path / "demo"
    project.mkdir()
    _make_pre_schema_project(project)

    # Sanity: starting state has no schema_version (otherwise the test is a no-op).
    pre = yaml.safe_load((project / ".kittify" / "metadata.yaml").read_text(encoding="utf-8"))
    assert "schema_version" not in pre.get("spec_kitty", {}), (
        "Test setup invariant violated: schema_version should be absent before upgrade"
    )

    # Act 1: spec-kitty upgrade --yes
    upgrade_result = run_cli(project, "upgrade", "--yes")
    assert upgrade_result.returncode == 0, (
        f"upgrade failed (rc={upgrade_result.returncode}):\n"
        f"stdout: {upgrade_result.stdout}\nstderr: {upgrade_result.stderr}"
    )

    # Assert intermediate: schema_version landed in metadata.yaml.
    post = yaml.safe_load((project / ".kittify" / "metadata.yaml").read_text(encoding="utf-8"))
    assert REQUIRED_SCHEMA_VERSION is not None, (
        "REQUIRED_SCHEMA_VERSION is None; this test is meaningful only when the "
        "schema-version gate is active."
    )
    assert post.get("spec_kitty", {}).get("schema_version") == REQUIRED_SCHEMA_VERSION, (
        "schema_version was not stamped after upgrade -- FR-002 regression. "
        f"Expected {REQUIRED_SCHEMA_VERSION}, got "
        f"{post.get('spec_kitty', {}).get('schema_version')!r}"
    )

    # Act 2: spec-kitty agent mission branch-context --json (the gate consumer)
    bc_result = run_cli(project, "agent", "mission", "branch-context", "--json")

    # Assert: command exits 0 (gate did not trip) and JSON result is success.
    assert bc_result.returncode == 0, (
        "branch-context gated unexpectedly after upgrade. "
        "This means the schema-version stamp was clobbered (FR-002 / #705).\n"
        f"stdout: {bc_result.stdout}\nstderr: {bc_result.stderr}"
    )
    payload = json.loads(bc_result.stdout)
    assert payload["result"] == "success", (
        f"branch-context returned non-success payload: {payload!r}"
    )
