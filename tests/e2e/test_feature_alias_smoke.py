"""Regression smoke for FR-006 (#790): the legacy ``--feature`` alias must
continue to ROUTE to ``--mission`` semantics on commands that historically
accept it.

Hidden does not mean removed. Many third-party scripts and existing user
workflows still pass ``--feature``; the alias must keep working byte-for-
byte identically to ``--mission``.

Strategy: drive ``spec-kitty agent tasks status --json`` (a read-only
subcommand) twice — once with ``--mission <slug>`` and once with
``--feature <slug>`` — against an in-process CliRunner pointed at the
CURRENT source tree, and assert the two JSON payloads are equal modulo
volatile fields.

Why in-process CliRunner instead of subprocess:
The WP07 contract explicitly requires testing the CURRENT source, not an
installed CLI version. Importing ``specify_cli.cli.commands.agent.app``
directly and exercising it with ``typer.testing.CliRunner`` guarantees
that — no version-skew risk, no PATH risk.

Why a hand-rolled project setup instead of the e2e_project fixture:
The e2e_project fixture in ``tests/e2e/conftest.py`` is paired with the
``run_cli`` subprocess helper. Mirroring its setup steps in-process
keeps this test self-contained and avoids the subprocess hop.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from specify_cli.cli.commands.agent import app as agent_app


REPO_ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Volatile fields stripped before equality assertion.
# ---------------------------------------------------------------------------
# ``tasks status --json`` returns deterministic structure for a freshly
# created mission with one WP, but we strip a few defensively listed keys
# that may carry timestamps or environment-derived values in the future.
_VOLATILE_KEYS = (
    "now_utc_iso",
    "NOW_UTC_ISO",
    "generated_at",
    "scanned_at",
)


def _strip_volatile(payload: object) -> object:
    """Recursively remove volatile keys from a JSON-shaped payload."""
    if isinstance(payload, dict):
        return {k: _strip_volatile(v) for k, v in payload.items() if k not in _VOLATILE_KEYS}
    if isinstance(payload, list):
        return [_strip_volatile(v) for v in payload]
    return payload


def _build_e2e_project(tmp_path: Path) -> Path:
    """Replicate the ``e2e_project`` fixture setup in-process.

    Creates a tmp project with .kittify scaffold copied from the repo,
    initializes git, and aligns metadata version. Returns the project
    directory.
    """
    project = tmp_path / "demo"
    project.mkdir()

    shutil.copytree(
        REPO_ROOT / ".kittify",
        project / ".kittify",
        symlinks=True,
    )

    missions_src = REPO_ROOT / "src" / "specify_cli" / "missions"
    missions_dest = project / ".kittify" / "missions"
    if missions_src.exists() and not missions_dest.exists():
        shutil.copytree(missions_src, missions_dest)

    (project / ".gitignore").write_text(
        "__pycache__/\n.worktrees/\n",
        encoding="utf-8",
    )

    subprocess.run(
        ["git", "init", "-b", "main"],
        cwd=project,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "alias-smoke@example.com"],
        cwd=project,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Alias Smoke"],
        cwd=project,
        check=True,
        capture_output=True,
    )
    subprocess.run(["git", "add", "."], cwd=project, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial project"],
        cwd=project,
        check=True,
        capture_output=True,
    )

    # Align metadata version with source so version-mismatch guards stay quiet.
    metadata_file = project / ".kittify" / "metadata.yaml"
    if metadata_file.exists():
        with open(metadata_file, encoding="utf-8") as f:
            metadata = yaml.safe_load(f) or {}
        with open(REPO_ROOT / "pyproject.toml", "rb") as f:
            pyproject = tomllib.load(f)
        current_version = pyproject["project"]["version"] or "unknown"
        metadata.setdefault("spec_kitty", {})["version"] = current_version
        with open(metadata_file, "w", encoding="utf-8") as f:
            yaml.dump(metadata, f, default_flow_style=False, sort_keys=False)
        subprocess.run(
            ["git", "add", "."],
            cwd=project,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Align metadata version"],
            cwd=project,
            check=True,
            capture_output=True,
        )

    return project


def _seed_minimal_wp(feature_dir: Path) -> None:
    """Drop a single minimal WP file so ``tasks status`` returns full JSON
    instead of the empty-tasks early-return path."""
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    (tasks_dir / "WP01.md").write_text(
        "---\nwork_package_id: WP01\ntitle: Smoke WP\nphase: 1\nagent: claude\nexecution_mode: code_change\n---\n\n# WP01\n",
        encoding="utf-8",
    )


@pytest.mark.e2e
def test_feature_alias_routes_to_mission(tmp_path: Path) -> None:
    """Both --mission and --feature must succeed and produce equal JSON."""
    project = _build_e2e_project(tmp_path)
    runner = CliRunner()

    old_cwd = os.getcwd()
    try:
        os.chdir(project)

        # 1. Create a mission so tasks status has something to report.
        create_result = runner.invoke(
            agent_app,
            ["mission", "create", "smoke", "--json"],
            catch_exceptions=False,
        )
        assert create_result.exit_code == 0, create_result.output

        # ``mission create --json`` may emit non-JSON status lines first
        # (e.g. "Not authenticated, skipping sync") followed by the JSON
        # payload on its own line. Find the JSON line.
        json_line = next(
            (line for line in create_result.output.splitlines() if line.strip().startswith("{")),
            None,
        )
        assert json_line is not None, f"could not find JSON in mission-create output:\n{create_result.output}"
        create_payload = json.loads(json_line)
        slug = create_payload["mission_slug"]
        feature_dir = project / "kitty-specs" / slug
        assert feature_dir.exists()

        # 2. Seed one WP so the JSON branch is exercised.
        _seed_minimal_wp(feature_dir)

        # 3. Drive tasks status with both flags.
        mission_result = runner.invoke(
            agent_app,
            ["tasks", "status", "--mission", slug, "--json"],
            catch_exceptions=False,
        )
        feature_result = runner.invoke(
            agent_app,
            ["tasks", "status", "--feature", slug, "--json"],
            catch_exceptions=False,
        )

        assert mission_result.exit_code == 0, f"--mission invocation failed:\n{mission_result.output}"
        assert feature_result.exit_code == 0, f"--feature invocation failed:\n{feature_result.output}"

        # 4. Extract JSON from each and compare modulo volatile fields.
        def _extract_json(out: str) -> object:
            # tasks status --json prints a single JSON object spanning
            # multiple lines (indent=2). Find the first '{' and JSON-decode
            # from there to the matching close.
            start = out.find("{")
            assert start != -1, f"no JSON found in output:\n{out}"
            decoder = json.JSONDecoder()
            obj, _ = decoder.raw_decode(out[start:])
            return obj

        mission_payload = _strip_volatile(_extract_json(mission_result.output))
        feature_payload = _strip_volatile(_extract_json(feature_result.output))

        assert mission_payload == feature_payload, (
            "FR-006 regression: --feature alias produced a different JSON "
            "payload than --mission for `agent tasks status`.\n"
            f"--mission: {mission_payload}\n"
            f"--feature: {feature_payload}"
        )
    finally:
        os.chdir(old_cwd)
